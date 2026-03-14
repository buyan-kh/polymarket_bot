"""
Backtesting engine - replay a user's trading strategy against historical data.

If backtest data is available (cached trades, price history), this engine:
- Replays the user's trades in chronological order
- Tracks portfolio value over time
- Calculates drawdowns, Sharpe ratio, and other risk metrics
- Compares against baseline strategies (buy-and-hold, random)
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .fetcher import Trade
from .patterns import _parse_ts, _median, _stddev


@dataclass
class PortfolioSnapshot:
    """Portfolio state at a point in time."""
    timestamp: str
    cash: float
    positions_value: float  # estimated value of open positions
    total_value: float
    trade_count: int


@dataclass
class BacktestResult:
    """Results of a backtest run."""
    initial_capital: float
    final_value: float
    total_return_pct: float
    total_pnl: float
    max_drawdown_pct: float
    max_drawdown_value: float
    peak_value: float
    num_trades: int
    num_winning_trades: int
    num_losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float  # gross wins / gross losses
    sharpe_ratio: float
    sortino_ratio: float
    avg_trade_pnl: float
    largest_win: float
    largest_loss: float
    portfolio_snapshots: list[PortfolioSnapshot]
    market_results: dict  # condition_id -> pnl
    daily_returns: list[float]


@dataclass
class Position:
    """An open position in a market outcome."""
    condition_id: str
    outcome: str
    title: str
    quantity: float = 0.0
    cost_basis: float = 0.0  # total USDC spent
    avg_entry: float = 0.0


def run_backtest(
    trades: list[Trade],
    initial_capital: float = 10000.0,
    settlement_prices: Optional[dict] = None,
) -> BacktestResult:
    """
    Replay trades chronologically and track portfolio performance.

    Args:
        trades: List of trades to replay
        initial_capital: Starting capital in USDC
        settlement_prices: Optional dict of {condition_id: {outcome: price}}
            e.g. {"0xabc": {"Over": 1.0, "Under": 0.0}}.
            Positions in resolved markets are settled at outcome-specific payouts.
    """
    settlement_prices = settlement_prices or {}

    # Sort by timestamp
    sorted_trades = sorted(trades, key=lambda t: t.timestamp)

    cash = initial_capital
    positions: dict[str, Position] = {}  # key = condition_id:outcome
    snapshots: list[PortfolioSnapshot] = []
    market_pnl: dict[str, float] = {}
    trade_pnls: list[float] = []
    daily_values: dict[str, float] = {}  # date -> end-of-day value

    peak_value = initial_capital
    max_drawdown = 0.0
    max_drawdown_value = 0.0

    for i, trade in enumerate(sorted_trades):
        key = f"{trade.condition_id}:{trade.outcome}"
        cost = trade.size * trade.price

        if trade.side == "BUY":
            cash -= cost
            if key not in positions:
                positions[key] = Position(
                    condition_id=trade.condition_id,
                    outcome=trade.outcome,
                    title=trade.title,
                )
            pos = positions[key]
            pos.cost_basis += cost
            pos.quantity += trade.size
            pos.avg_entry = pos.cost_basis / pos.quantity if pos.quantity > 0 else 0

        elif trade.side == "SELL":
            revenue = cost  # size * price
            cash += revenue
            if key in positions:
                pos = positions[key]
                # PnL for this sell
                sell_cost_basis = pos.avg_entry * trade.size
                pnl = revenue - sell_cost_basis
                trade_pnls.append(pnl)
                market_pnl[trade.condition_id] = market_pnl.get(trade.condition_id, 0) + pnl
                pos.quantity -= trade.size
                pos.cost_basis = max(0, pos.cost_basis - sell_cost_basis)
                if pos.quantity <= 0.001:
                    del positions[key]
            else:
                # Short sell or untracked position
                trade_pnls.append(0)

        # Estimate current portfolio value — use settlement for resolved
        # markets, otherwise value at avg_entry (cost basis as conservative estimate)
        positions_value = 0.0
        for p in positions.values():
            cid = p.condition_id
            if cid in settlement_prices:
                outcome_prices = settlement_prices[cid]
                payout = outcome_prices.get(p.outcome, 0.0)
                positions_value += p.quantity * payout
            else:
                positions_value += p.quantity * p.avg_entry
        total_value = cash + positions_value

        # Track peak and drawdown
        if total_value > peak_value:
            peak_value = total_value
        drawdown = (peak_value - total_value)
        if drawdown > max_drawdown_value:
            max_drawdown_value = drawdown
            max_drawdown = drawdown / peak_value * 100 if peak_value > 0 else 0

        # Snapshot every 100 trades or on last trade
        if i % 100 == 0 or i == len(sorted_trades) - 1:
            snapshots.append(PortfolioSnapshot(
                timestamp=trade.timestamp,
                cash=cash,
                positions_value=positions_value,
                total_value=total_value,
                trade_count=i + 1,
            ))

        # Daily value tracking
        ts = _parse_ts(trade.timestamp)
        if ts:
            date_str = ts.strftime("%Y-%m-%d")
            daily_values[date_str] = total_value

    # Settle all resolved positions
    for key, pos in list(positions.items()):
        cid = pos.condition_id
        if cid in settlement_prices:
            outcome_prices = settlement_prices[cid]
            payout_per_share = outcome_prices.get(pos.outcome, 0.0)
            revenue = pos.quantity * payout_per_share
            pnl = revenue - pos.cost_basis
            trade_pnls.append(pnl)
            market_pnl[cid] = market_pnl.get(cid, 0) + pnl
            cash += revenue
            del positions[key]

    # Final value — remaining positions are unresolved, value at cost basis
    remaining_positions = sum(p.quantity * p.avg_entry for p in positions.values())
    final_value = cash + remaining_positions

    # Compute daily returns
    daily_vals = sorted(daily_values.items())
    daily_returns = []
    for i in range(1, len(daily_vals)):
        prev = daily_vals[i - 1][1]
        curr = daily_vals[i][1]
        if prev > 0:
            daily_returns.append((curr - prev) / prev)

    # Win/loss stats
    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p < 0]

    gross_wins = sum(wins) if wins else 0
    gross_losses = abs(sum(losses)) if losses else 1

    # Sharpe ratio (annualized, assuming daily returns)
    if daily_returns and len(daily_returns) > 1:
        avg_ret = sum(daily_returns) / len(daily_returns)
        std_ret = _stddev(daily_returns)
        sharpe = (avg_ret / std_ret) * (252 ** 0.5) if std_ret > 0 else 0
        # Sortino (only downside deviation)
        downside = [r for r in daily_returns if r < 0]
        downside_std = _stddev(downside) if len(downside) > 1 else 1
        sortino = (avg_ret / downside_std) * (252 ** 0.5) if downside_std > 0 else 0
    else:
        sharpe = 0
        sortino = 0

    total_return = ((final_value - initial_capital) / initial_capital) * 100

    return BacktestResult(
        initial_capital=initial_capital,
        final_value=round(final_value, 2),
        total_return_pct=round(total_return, 2),
        total_pnl=round(final_value - initial_capital, 2),
        max_drawdown_pct=round(max_drawdown, 2),
        max_drawdown_value=round(max_drawdown_value, 2),
        peak_value=round(peak_value, 2),
        num_trades=len(sorted_trades),
        num_winning_trades=len(wins),
        num_losing_trades=len(losses),
        win_rate=round(len(wins) / max(len(trade_pnls), 1) * 100, 2),
        avg_win=round(sum(wins) / len(wins), 2) if wins else 0,
        avg_loss=round(sum(losses) / len(losses), 2) if losses else 0,
        profit_factor=round(gross_wins / gross_losses, 2) if gross_losses > 0 else float('inf'),
        sharpe_ratio=round(sharpe, 2),
        sortino_ratio=round(sortino, 2),
        avg_trade_pnl=round(sum(trade_pnls) / len(trade_pnls), 2) if trade_pnls else 0,
        largest_win=round(max(wins), 2) if wins else 0,
        largest_loss=round(min(losses), 2) if losses else 0,
        portfolio_snapshots=snapshots,
        market_results=market_pnl,
        daily_returns=daily_returns,
    )


def compare_to_baseline(
    trades: list[Trade],
    backtest_result: BacktestResult,
) -> dict:
    """
    Compare the user's actual performance to simple baseline strategies.
    """
    # Baseline 1: "Always buy Yes at market price, sell at same time as user"
    # Baseline 2: "Inverse of user" (buy when they sell, sell when they buy)

    sorted_trades = sorted(trades, key=lambda t: t.timestamp)

    # Calculate user's average return per trade
    user_avg = backtest_result.avg_trade_pnl

    # Inverse strategy
    inverse_pnls = []
    for t in sorted_trades:
        if t.side == "BUY":
            # In inverse, this is a sell (we'd need to already own it)
            inverse_pnls.append(-t.usdc_size * 0.01)  # rough estimate
        elif t.side == "SELL":
            inverse_pnls.append(t.usdc_size * 0.01)

    # Random baseline (50/50 on each market, avg 0 return minus fees)
    random_expected = -len(sorted_trades) * 0.005  # ~0.5% fee per trade

    return {
        "user_total_pnl": backtest_result.total_pnl,
        "user_return_pct": backtest_result.total_return_pct,
        "inverse_estimated_pnl": round(sum(inverse_pnls), 2),
        "random_baseline_pnl": round(random_expected, 2),
        "beats_random": backtest_result.total_pnl > random_expected,
        "edge_vs_random": round(backtest_result.total_pnl - random_expected, 2),
    }
