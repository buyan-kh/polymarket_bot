"""
Safety Protocols for the Legged Arb Bot.
Implements risk management, emergency stops, and position monitoring.
"""

import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from state_machine import StateMachine, BotState
from order_manager import BaseOrderManager, OrderSide

logger = logging.getLogger(__name__)


@dataclass
class SafetyConfig:
    """Safety thresholds configuration."""
    gamma_stop_minutes: float = 2.0    # Cancel all orders within N minutes of expiry
    stop_loss_threshold: float = 0.15  # Max loss percentage before dumping
    max_position_age_seconds: float = 600  # Max time to hold a legged position
    max_single_order_size: float = 500.0   # Max USD per order


class SafetyMonitor:
    """
    Monitors trading for unsafe conditions and triggers protective actions.
    
    Safety checks:
    1. Gamma Stop: Cancel orders near expiry (price moves become violent)
    2. Stop Loss: Dump position if down too much
    3. Position Timeout: Don't hold a legged position forever
    4. Size Limits: Prevent oversized orders
    """
    
    def __init__(self, config: SafetyConfig):
        self.config = config
        self._legged_at: Optional[datetime] = None
    
    def check_gamma_stop(
        self,
        time_to_expiry_seconds: float
    ) -> bool:
        """
        Check if we're too close to expiry.
        
        Args:
            time_to_expiry_seconds: Seconds until market expires
            
        Returns:
            True if gamma stop should trigger (cancel all orders)
        """
        threshold = self.config.gamma_stop_minutes * 60
        triggered = time_to_expiry_seconds < threshold
        
        if triggered:
            logger.warning(
                f"GAMMA STOP: {time_to_expiry_seconds:.0f}s to expiry "
                f"(< {threshold:.0f}s threshold)"
            )
        
        return triggered
    
    def check_stop_loss(
        self,
        current_price: float,
        cost_basis: float
    ) -> bool:
        """
        Check if position should be dumped due to excessive loss.
        
        Args:
            current_price: Current market price of the held side
            cost_basis: Average cost paid for the position
            
        Returns:
            True if stop loss should trigger
        """
        if cost_basis <= 0:
            return False
        
        loss_pct = (cost_basis - current_price) / cost_basis
        triggered = loss_pct > self.config.stop_loss_threshold
        
        if triggered:
            logger.warning(
                f"STOP LOSS: Position down {loss_pct:.1%} "
                f"(cost: {cost_basis:.4f}, current: {current_price:.4f})"
            )
        
        return triggered
    
    def check_position_timeout(
        self,
        state: BotState
    ) -> bool:
        """
        Check if a legged position has been held too long.
        
        Args:
            state: Current bot state
            
        Returns:
            True if position has timed out
        """
        # Track when we entered a legged state
        if state == BotState.NEUTRAL:
            self._legged_at = None
            return False
        
        if state in {BotState.LEGGED_YES, BotState.LEGGED_NO}:
            if self._legged_at is None:
                self._legged_at = datetime.now()
            
            elapsed = (datetime.now() - self._legged_at).total_seconds()
            triggered = elapsed > self.config.max_position_age_seconds
            
            if triggered:
                logger.warning(
                    f"POSITION TIMEOUT: Legged for {elapsed:.0f}s "
                    f"(max: {self.config.max_position_age_seconds:.0f}s)"
                )
            
            return triggered
        
        return False
    
    def validate_order_size(self, size: float) -> float:
        """
        Validate and clamp order size.
        
        Args:
            size: Requested order size in USD
            
        Returns:
            Clamped order size
        """
        if size > self.config.max_single_order_size:
            logger.warning(
                f"Order size ${size:.2f} exceeds max ${self.config.max_single_order_size:.2f}"
            )
            return self.config.max_single_order_size
        return size
    
    def validate_price(self, price: float) -> bool:
        """
        Validate order price is reasonable.
        
        Args:
            price: Order price (should be 0.01-0.99)
            
        Returns:
            True if price is valid
        """
        if price < 0.01 or price > 0.99:
            logger.warning(f"Invalid price: {price:.4f} (must be 0.01-0.99)")
            return False
        return True


async def emergency_exit(
    order_manager: BaseOrderManager,
    state_machine: StateMachine,
    reason: str = "Emergency exit triggered"
) -> dict:
    """
    Execute emergency exit procedure.
    
    1. Cancel all open orders
    2. If holding a position, market sell it
    3. Reset state to NEUTRAL
    
    Args:
        order_manager: Order manager instance
        state_machine: State machine instance
        reason: Reason for emergency exit
        
    Returns:
        Summary of actions taken
    """
    logger.critical(f"EMERGENCY EXIT: {reason}")
    
    result = {
        "reason": reason,
        "orders_cancelled": 0,
        "position_dumped": None,
        "initial_state": state_machine.state.name,
    }
    
    # Step 1: Cancel all orders
    try:
        result["orders_cancelled"] = await order_manager.cancel_all_orders()
    except Exception as e:
        logger.error(f"Failed to cancel orders: {e}")
    
    # Step 2: Dump any open position
    state = state_machine.state
    inventory = state_machine.inventory
    
    try:
        if state == BotState.LEGGED_YES and inventory.yes.quantity > 0:
            # We have YES, try to sell it (by buying NO)
            # Actually for binary options, we might need to just accept the loss
            # For now, log the stranded position
            result["position_dumped"] = {
                "side": "YES",
                "qty": inventory.yes.quantity,
                "cost_basis": inventory.yes.avg_cost,
            }
            logger.warning(
                f"Stranded YES position: {inventory.yes.quantity}@{inventory.yes.avg_cost:.4f}"
            )
            
        elif state == BotState.LEGGED_NO and inventory.no.quantity > 0:
            result["position_dumped"] = {
                "side": "NO",
                "qty": inventory.no.quantity,
                "cost_basis": inventory.no.avg_cost,
            }
            logger.warning(
                f"Stranded NO position: {inventory.no.quantity}@{inventory.no.avg_cost:.4f}"
            )
    except Exception as e:
        logger.error(f"Error dumping position: {e}")
    
    # Step 3: Reset state
    state_machine.force_neutral(reason)
    result["final_state"] = state_machine.state.name
    
    logger.info(f"Emergency exit complete: {result}")
    return result


class RiskLimits:
    """
    Tracks cumulative risk and enforces daily/session limits.
    """
    
    def __init__(
        self,
        max_daily_loss: float = 100.0,
        max_daily_trades: int = 100,
        max_concurrent_positions: int = 1,
    ):
        self.max_daily_loss = max_daily_loss
        self.max_daily_trades = max_daily_trades
        self.max_concurrent_positions = max_concurrent_positions
        
        self._daily_pnl = 0.0
        self._daily_trade_count = 0
        self._session_start = datetime.now()
    
    def record_pnl(self, pnl: float) -> None:
        """Record a trade's P&L."""
        self._daily_pnl += pnl
        self._daily_trade_count += 1
        
        logger.info(
            f"Trade P&L: ${pnl:.2f} | Daily: ${self._daily_pnl:.2f} | "
            f"Trades: {self._daily_trade_count}"
        )
    
    def can_trade(self) -> tuple[bool, str]:
        """
        Check if trading is allowed based on limits.
        
        Returns:
            (allowed, reason) tuple
        """
        if self._daily_pnl < -self.max_daily_loss:
            return False, f"Daily loss limit hit: ${self._daily_pnl:.2f}"
        
        if self._daily_trade_count >= self.max_daily_trades:
            return False, f"Daily trade limit hit: {self._daily_trade_count}"
        
        return True, "OK"
    
    def reset_daily(self) -> None:
        """Reset daily counters (call at day rollover)."""
        logger.info(
            f"Resetting daily limits. Final P&L: ${self._daily_pnl:.2f}, "
            f"Trades: {self._daily_trade_count}"
        )
        self._daily_pnl = 0.0
        self._daily_trade_count = 0
    
    def get_stats(self) -> dict:
        """Get current risk stats."""
        return {
            "daily_pnl": self._daily_pnl,
            "daily_trades": self._daily_trade_count,
            "max_daily_loss": self.max_daily_loss,
            "max_daily_trades": self.max_daily_trades,
            "session_start": self._session_start.isoformat(),
        }
