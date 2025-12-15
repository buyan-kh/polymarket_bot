"""
State Machine for the Legged Arb Bot.
Manages the trading state transitions and position tracking.

States:
- NEUTRAL: No position, placing bids on both sides
- LEGGED_YES: Holding YES, seeking NO to complete arb
- LEGGED_NO: Holding NO, seeking YES to complete arb  
- LOCKED: Both sides acquired, waiting for settlement
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BotState(Enum):
    """Trading states for the arbitrage bot."""
    NEUTRAL = auto()      # No position
    LEGGED_YES = auto()   # Long YES, need NO
    LEGGED_NO = auto()    # Long NO, need YES
    LOCKED = auto()       # Both sides acquired, profit locked


@dataclass
class Position:
    """
    Tracks inventory and cost basis for a single side.
    """
    quantity: float = 0.0
    total_cost: float = 0.0
    
    @property
    def avg_cost(self) -> float:
        """Average cost per share."""
        if self.quantity == 0:
            return 0.0
        return self.total_cost / self.quantity
    
    def add(self, qty: float, price: float) -> None:
        """Add shares to position."""
        cost = qty * price
        self.quantity += qty
        self.total_cost += cost
        logger.debug(f"Added {qty}@{price:.4f}, new avg: {self.avg_cost:.4f}")
    
    def reset(self) -> None:
        """Clear position."""
        self.quantity = 0.0
        self.total_cost = 0.0


@dataclass
class Inventory:
    """
    Tracks positions for both YES and NO sides.
    """
    yes: Position = field(default_factory=Position)
    no: Position = field(default_factory=Position)
    
    @property
    def total_cost(self) -> float:
        """Total cost basis across both sides."""
        return self.yes.total_cost + self.no.total_cost
    
    @property
    def locked_profit(self) -> float:
        """
        Profit if both sides are held to settlement.
        Settlement pays $1.00 per pair.
        """
        min_qty = min(self.yes.quantity, self.no.quantity)
        if min_qty <= 0:
            return 0.0
        
        # Cost for the matched pairs
        matched_cost = (self.yes.avg_cost + self.no.avg_cost) * min_qty
        payout = min_qty * 1.0
        return payout - matched_cost
    
    def reset(self) -> None:
        """Clear all positions."""
        self.yes.reset()
        self.no.reset()


class StateMachine:
    """
    Manages state transitions for the legged arbitrage strategy.
    
    Valid transitions:
    - NEUTRAL → LEGGED_YES (YES bid filled)
    - NEUTRAL → LEGGED_NO (NO bid filled)
    - LEGGED_YES → LOCKED (NO acquired)
    - LEGGED_NO → LOCKED (YES acquired)
    - LEGGED_YES → NEUTRAL (stop-loss)
    - LEGGED_NO → NEUTRAL (stop-loss)
    - LOCKED → NEUTRAL (settlement/reset)
    """
    
    VALID_TRANSITIONS = {
        BotState.NEUTRAL: {BotState.LEGGED_YES, BotState.LEGGED_NO},
        BotState.LEGGED_YES: {BotState.LOCKED, BotState.NEUTRAL},
        BotState.LEGGED_NO: {BotState.LOCKED, BotState.NEUTRAL},
        BotState.LOCKED: {BotState.NEUTRAL},
    }
    
    def __init__(self):
        self._state = BotState.NEUTRAL
        self.inventory = Inventory()
        self._transition_count = 0
    
    @property
    def state(self) -> BotState:
        return self._state
    
    def can_transition(self, new_state: BotState) -> bool:
        """Check if transition to new_state is valid."""
        valid_next = self.VALID_TRANSITIONS.get(self._state, set())
        return new_state in valid_next
    
    def transition(self, new_state: BotState, reason: str = "") -> bool:
        """
        Attempt to transition to a new state.
        
        Args:
            new_state: Target state
            reason: Optional reason for logging
            
        Returns:
            True if transition succeeded, False otherwise
        """
        if not self.can_transition(new_state):
            logger.warning(
                f"Invalid transition: {self._state.name} → {new_state.name}"
            )
            return False
        
        old_state = self._state
        self._state = new_state
        self._transition_count += 1
        
        logger.info(
            f"State: {old_state.name} → {new_state.name}"
            + (f" ({reason})" if reason else "")
        )
        
        return True
    
    def on_fill(self, side: str, price: float, qty: float) -> BotState:
        """
        Process a fill event and update state accordingly.
        
        Args:
            side: "YES" or "NO"
            price: Fill price
            qty: Fill quantity
            
        Returns:
            New state after processing the fill
        """
        side = side.upper()
        
        # Update inventory
        if side == "YES":
            self.inventory.yes.add(qty, price)
        elif side == "NO":
            self.inventory.no.add(qty, price)
        else:
            raise ValueError(f"Invalid side: {side}")
        
        # Determine state transition
        if self._state == BotState.NEUTRAL:
            # First leg filled
            if side == "YES":
                self.transition(BotState.LEGGED_YES, f"YES filled @ {price:.4f}")
            else:
                self.transition(BotState.LEGGED_NO, f"NO filled @ {price:.4f}")
                
        elif self._state == BotState.LEGGED_YES and side == "NO":
            # Second leg completed
            self.transition(BotState.LOCKED, f"NO filled @ {price:.4f}")
            
        elif self._state == BotState.LEGGED_NO and side == "YES":
            # Second leg completed
            self.transition(BotState.LOCKED, f"YES filled @ {price:.4f}")
        
        return self._state
    
    def force_neutral(self, reason: str = "manual reset") -> None:
        """Force reset to NEUTRAL state (for stop-loss or errors)."""
        logger.warning(f"Forcing NEUTRAL state: {reason}")
        self._state = BotState.NEUTRAL
        self.inventory.reset()
    
    def get_summary(self) -> dict:
        """Get current state summary."""
        return {
            "state": self._state.name,
            "yes_qty": self.inventory.yes.quantity,
            "yes_avg_cost": self.inventory.yes.avg_cost,
            "no_qty": self.inventory.no.quantity,
            "no_avg_cost": self.inventory.no.avg_cost,
            "total_cost": self.inventory.total_cost,
            "locked_profit": self.inventory.locked_profit,
            "transitions": self._transition_count,
        }
