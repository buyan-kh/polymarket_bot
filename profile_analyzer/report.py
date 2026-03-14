"""
Report generator - produces pros/cons analysis and formatted reports.

Takes pattern analysis and backtest results, generates actionable insights.
"""

from dataclasses import dataclass
from typing import Optional

from .patterns import AnalysisResult
from .backtest import BacktestResult


@dataclass
class ProCon:
    """A single pro or con observation."""
    category: str  # e.g. "Risk Management", "Timing", "Sizing"
    observation: str
    detail: str
    severity: str = "info"  # info, warning, critical (for cons)


@dataclass
class Report:
    """Complete analysis report."""
    username: str
    wallet: str
    summary: str
    pros: list[ProCon]
    cons: list[ProCon]
    key_stats: dict
    recommendations: list[str]
    backtest_summary: Optional[dict] = None


def generate_report(
    analysis: AnalysisResult,
    backtest: Optional[BacktestResult] = None,
) -> Report:
    """Generate a comprehensive pros/cons report from analysis results."""

    pros: list[ProCon] = []
    cons: list[ProCon] = []
    recommendations: list[str] = []

    # --- VOLUME & EXPERIENCE ---
    if analysis.total_trades > 1000:
        pros.append(ProCon(
            category="Experience",
            observation="High trade count",
            detail=f"{analysis.total_trades:,} total trades shows significant experience and commitment.",
        ))
    elif analysis.total_trades < 50:
        cons.append(ProCon(
            category="Experience",
            observation="Low trade count",
            detail=f"Only {analysis.total_trades} trades — limited data for pattern analysis.",
            severity="warning",
        ))

    if analysis.total_volume_usdc > 1_000_000:
        pros.append(ProCon(
            category="Scale",
            observation="High volume trader",
            detail=f"${analysis.total_volume_usdc:,.0f} total volume indicates serious capital deployment.",
        ))

    # --- DIVERSIFICATION ---
    if analysis.market_concentration < 0.05:
        pros.append(ProCon(
            category="Diversification",
            observation="Well-diversified",
            detail=f"Herfindahl index of {analysis.market_concentration:.4f} shows good diversification across {analysis.unique_markets} markets.",
        ))
    elif analysis.market_concentration > 0.20:
        cons.append(ProCon(
            category="Diversification",
            observation="Highly concentrated",
            detail=f"Herfindahl index of {analysis.market_concentration:.4f} — volume concentrated in few markets. High single-market risk.",
            severity="warning",
        ))
        recommendations.append("Consider spreading volume across more markets to reduce concentration risk.")

    # --- TIMING ---
    if analysis.timing.trading_streak_days > 30:
        pros.append(ProCon(
            category="Consistency",
            observation="Consistent trading habit",
            detail=f"Longest trading streak: {analysis.timing.trading_streak_days} consecutive days.",
        ))

    if analysis.timing.avg_trades_per_day > 100:
        cons.append(ProCon(
            category="Overtrading",
            observation="Very high frequency",
            detail=f"{analysis.timing.avg_trades_per_day:.0f} trades/day average may indicate overtrading or bot activity.",
            severity="warning",
        ))
        recommendations.append("Review if high trade frequency is adding value or just generating fees.")
    elif analysis.timing.avg_trades_per_day > 20:
        pros.append(ProCon(
            category="Activity",
            observation="Active trader",
            detail=f"{analysis.timing.avg_trades_per_day:.1f} trades/day shows engaged market participation.",
        ))

    # --- SIZING ---
    if analysis.sizing.stddev_trade_size > analysis.sizing.avg_trade_size_usdc * 2:
        cons.append(ProCon(
            category="Risk Management",
            observation="Inconsistent sizing",
            detail=f"Trade size std dev (${analysis.sizing.stddev_trade_size:,.0f}) is >2x the average (${analysis.sizing.avg_trade_size_usdc:,.0f}). Erratic position sizing.",
            severity="warning",
        ))
        recommendations.append("Adopt more consistent position sizing. Consider fixed fractional sizing or Kelly criterion.")

    if analysis.sizing.max_trade_size_usdc > analysis.sizing.avg_trade_size_usdc * 20:
        cons.append(ProCon(
            category="Risk Management",
            observation="Outsized max trade",
            detail=f"Max trade (${analysis.sizing.max_trade_size_usdc:,.0f}) is {analysis.sizing.max_trade_size_usdc / max(analysis.sizing.avg_trade_size_usdc, 1):.0f}x the average. Potential risk of ruin.",
            severity="critical",
        ))

    # --- PRICING BEHAVIOR ---
    if analysis.pricing.pct_buying_below_50c > 70:
        pros.append(ProCon(
            category="Strategy",
            observation="Value buyer",
            detail=f"{analysis.pricing.pct_buying_below_50c:.0f}% of buys at < $0.50 — seeks undervalued outcomes (contrarian/value approach).",
        ))
    elif analysis.pricing.pct_buying_above_50c > 70:
        cons.append(ProCon(
            category="Strategy",
            observation="Consensus buyer",
            detail=f"{analysis.pricing.pct_buying_above_50c:.0f}% of buys at > $0.50 — primarily buying favorites. Lower expected value.",
            severity="info",
        ))
        recommendations.append("Consider looking for value in less popular outcomes. Buying favorites offers lower edge.")

    if analysis.pricing.avg_buy_price > 0.85:
        cons.append(ProCon(
            category="Strategy",
            observation="Very high-priced entries",
            detail=f"Average buy price ${analysis.pricing.avg_buy_price:.2f} — buying at very high conviction levels. Limited upside vs downside risk.",
            severity="warning",
        ))

    # --- BUY/SELL BALANCE ---
    if analysis.buy_sell_ratio > 3:
        cons.append(ProCon(
            category="Risk Management",
            observation="Heavy buy bias",
            detail=f"Buy/sell ratio of {analysis.buy_sell_ratio:.1f} — significantly more buys than sells. May be holding too long or not taking profits.",
            severity="warning",
        ))
        recommendations.append("Consider taking profits more actively. A high buy/sell ratio may indicate positions held to expiry without exit management.")
    elif 0.8 < analysis.buy_sell_ratio < 1.5:
        pros.append(ProCon(
            category="Risk Management",
            observation="Balanced buy/sell",
            detail=f"Buy/sell ratio of {analysis.buy_sell_ratio:.1f} indicates active position management with regular profit-taking.",
        ))

    # --- CATEGORY FOCUS ---
    cats = analysis.category_breakdown
    if cats:
        top_cat = max(cats, key=cats.get)
        top_pct = cats[top_cat] / max(analysis.total_trades, 1) * 100
        if top_pct > 80:
            cons.append(ProCon(
                category="Diversification",
                observation=f"Single-category focus: {top_cat}",
                detail=f"{top_pct:.0f}% of trades in {top_cat}. High exposure to category-specific risks.",
                severity="info",
            ))
        elif len(cats) >= 3:
            pros.append(ProCon(
                category="Diversification",
                observation="Multi-category trader",
                detail=f"Active across {len(cats)} categories: {', '.join(cats.keys())}.",
            ))

    # --- BACKTEST RESULTS ---
    bt_summary = None
    if backtest:
        bt_summary = {
            "initial_capital": backtest.initial_capital,
            "final_value": backtest.final_value,
            "total_return_pct": backtest.total_return_pct,
            "max_drawdown_pct": backtest.max_drawdown_pct,
            "sharpe_ratio": backtest.sharpe_ratio,
            "sortino_ratio": backtest.sortino_ratio,
            "win_rate": backtest.win_rate,
            "profit_factor": backtest.profit_factor,
            "largest_win": backtest.largest_win,
            "largest_loss": backtest.largest_loss,
        }

        if backtest.win_rate > 55:
            pros.append(ProCon(
                category="Performance",
                observation="Above-average win rate",
                detail=f"Win rate of {backtest.win_rate:.1f}% (>55% threshold). Demonstrates edge in trade selection.",
            ))
        elif backtest.win_rate < 40:
            cons.append(ProCon(
                category="Performance",
                observation="Low win rate",
                detail=f"Win rate of {backtest.win_rate:.1f}%. May need better entry criteria or market selection.",
                severity="warning",
            ))

        if backtest.profit_factor > 1.5:
            pros.append(ProCon(
                category="Performance",
                observation="Strong profit factor",
                detail=f"Profit factor of {backtest.profit_factor:.2f} — wins significantly outweigh losses.",
            ))
        elif backtest.profit_factor < 1.0:
            cons.append(ProCon(
                category="Performance",
                observation="Negative profit factor",
                detail=f"Profit factor of {backtest.profit_factor:.2f} — losses outweigh wins on aggregate.",
                severity="critical",
            ))

        if backtest.max_drawdown_pct > 50:
            cons.append(ProCon(
                category="Risk",
                observation="Severe max drawdown",
                detail=f"Max drawdown of {backtest.max_drawdown_pct:.1f}%. Extreme risk of ruin.",
                severity="critical",
            ))
            recommendations.append("Implement stricter drawdown limits. A 50%+ drawdown requires 100%+ gain to recover.")
        elif backtest.max_drawdown_pct < 20:
            pros.append(ProCon(
                category="Risk",
                observation="Controlled drawdowns",
                detail=f"Max drawdown of {backtest.max_drawdown_pct:.1f}% shows good risk management.",
            ))

        if backtest.sharpe_ratio > 1.0:
            pros.append(ProCon(
                category="Performance",
                observation="Good risk-adjusted returns",
                detail=f"Sharpe ratio of {backtest.sharpe_ratio:.2f} indicates returns well above the risk taken.",
            ))

        if backtest.largest_loss and abs(backtest.largest_loss) > backtest.largest_win * 2:
            cons.append(ProCon(
                category="Risk Management",
                observation="Asymmetric loss",
                detail=f"Largest loss (${abs(backtest.largest_loss):,.0f}) is >2x largest win (${backtest.largest_win:,.0f}). Need tighter stop-losses.",
                severity="warning",
            ))

    # --- KEY STATS ---
    key_stats = {
        "total_trades": analysis.total_trades,
        "total_volume": f"${analysis.total_volume_usdc:,.0f}",
        "unique_markets": analysis.unique_markets,
        "avg_trade_size": f"${analysis.sizing.avg_trade_size_usdc:,.2f}",
        "avg_buy_price": f"${analysis.pricing.avg_buy_price:.3f}",
        "buy_sell_ratio": f"{analysis.buy_sell_ratio:.2f}",
        "market_concentration": f"{analysis.market_concentration:.4f}",
        "avg_trades_per_day": f"{analysis.timing.avg_trades_per_day:.1f}",
        "trading_streak": f"{analysis.timing.trading_streak_days} days",
        "date_range": f"{analysis.date_range[0][:10]} to {analysis.date_range[1][:10]}",
    }

    # --- SUMMARY ---
    summary_parts = [
        f"Analyzed {analysis.total_trades:,} trades across {analysis.unique_markets} markets.",
        f"Total volume: ${analysis.total_volume_usdc:,.0f}.",
    ]
    if backtest:
        summary_parts.append(f"Backtest return: {backtest.total_return_pct:.1f}%, Sharpe: {backtest.sharpe_ratio:.2f}.")
    summary = " ".join(summary_parts)

    return Report(
        username=analysis.username,
        wallet=analysis.wallet,
        summary=summary,
        pros=pros,
        cons=cons,
        key_stats=key_stats,
        recommendations=recommendations,
        backtest_summary=bt_summary,
    )


def format_report(report: Report) -> str:
    """Format the report as a readable text output."""
    lines = []
    sep = "=" * 70

    lines.append(sep)
    lines.append(f"  POLYMARKET TRADE ANALYSIS: @{report.username or report.wallet[:10]}")
    lines.append(sep)
    lines.append("")
    lines.append(report.summary)
    lines.append("")

    # Key Stats
    lines.append("-" * 40)
    lines.append("  KEY STATISTICS")
    lines.append("-" * 40)
    for k, v in report.key_stats.items():
        label = k.replace("_", " ").title()
        lines.append(f"  {label:<25} {v}")
    lines.append("")

    # Backtest Summary
    if report.backtest_summary:
        lines.append("-" * 40)
        lines.append("  BACKTEST RESULTS")
        lines.append("-" * 40)
        bt = report.backtest_summary
        lines.append(f"  Initial Capital:         ${bt['initial_capital']:,.0f}")
        lines.append(f"  Final Value:             ${bt['final_value']:,.0f}")
        lines.append(f"  Total Return:            {bt['total_return_pct']:.1f}%")
        lines.append(f"  Max Drawdown:            {bt['max_drawdown_pct']:.1f}%")
        lines.append(f"  Sharpe Ratio:            {bt['sharpe_ratio']:.2f}")
        lines.append(f"  Sortino Ratio:           {bt['sortino_ratio']:.2f}")
        lines.append(f"  Win Rate:                {bt['win_rate']:.1f}%")
        lines.append(f"  Profit Factor:           {bt['profit_factor']:.2f}")
        lines.append(f"  Largest Win:             ${bt['largest_win']:,.0f}")
        lines.append(f"  Largest Loss:            ${bt['largest_loss']:,.0f}")
        lines.append("")

    # Pros
    lines.append("-" * 40)
    lines.append(f"  STRENGTHS ({len(report.pros)})")
    lines.append("-" * 40)
    for i, p in enumerate(report.pros, 1):
        lines.append(f"  {i}. [{p.category}] {p.observation}")
        lines.append(f"     {p.detail}")
        lines.append("")

    # Cons
    lines.append("-" * 40)
    severity_icon = {"info": "~", "warning": "!", "critical": "X"}
    lines.append(f"  WEAKNESSES ({len(report.cons)})")
    lines.append("-" * 40)
    for i, c in enumerate(report.cons, 1):
        icon = severity_icon.get(c.severity, "~")
        lines.append(f"  {i}. [{icon}] [{c.category}] {c.observation}")
        lines.append(f"     {c.detail}")
        lines.append("")

    # Recommendations
    if report.recommendations:
        lines.append("-" * 40)
        lines.append("  RECOMMENDATIONS")
        lines.append("-" * 40)
        for i, r in enumerate(report.recommendations, 1):
            lines.append(f"  {i}. {r}")
        lines.append("")

    lines.append(sep)
    return "\n".join(lines)
