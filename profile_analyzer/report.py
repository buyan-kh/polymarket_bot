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

    # --- SAMPLE SIZE CHECK ---
    if analysis.total_trades < 50:
        cons.append(ProCon(
            category="Data Quality",
            observation="Small sample size",
            detail=f"Only {analysis.total_trades} trades — all pattern insights below have low confidence. Need 50+ trades for reliable signals.",
            severity="warning",
        ))

    # ===================================================================
    #  1. BUY/SELL SPREAD EDGE — the single most important alpha signal
    # ===================================================================
    spread = analysis.buy_sell_spread
    avg_entry = analysis.avg_entry_price
    avg_exit = analysis.avg_exit_price

    if avg_entry > 0 and avg_exit > 0:
        if spread > 0.05:
            pros.append(ProCon(
                category="Alpha",
                observation=f"Buy/sell spread edge: +{spread:.3f}",
                detail=(
                    f"Avg buy @ ${avg_entry:.3f}, avg sell @ ${avg_exit:.3f}. "
                    f"Consistently selling higher than buying by ${spread:.3f} per share — "
                    f"this is the core of their edge. Replicable if you can match their entry timing."
                ),
            ))
        elif spread > 0.02:
            pros.append(ProCon(
                category="Alpha",
                observation=f"Modest buy/sell spread: +{spread:.3f}",
                detail=(
                    f"Avg buy @ ${avg_entry:.3f}, avg sell @ ${avg_exit:.3f}. "
                    f"Positive spread indicates they generally exit at better prices than entry, but the margin is thin."
                ),
            ))
        elif spread < -0.02:
            cons.append(ProCon(
                category="Alpha",
                observation=f"Negative buy/sell spread: {spread:.3f}",
                detail=(
                    f"Avg buy @ ${avg_entry:.3f}, avg sell @ ${avg_exit:.3f}. "
                    f"Selling lower than buying on average — either cutting losses (disciplined) or buying tops and panic selling."
                ),
                severity="warning",
            ))

    # ===================================================================
    #  2. CHEAP ENTRY EDGE — buys cheap, profits from resolution
    # ===================================================================
    if avg_entry > 0 and avg_entry < 0.35:
        pros.append(ProCon(
            category="Alpha",
            observation=f"Cheap entry specialist (avg ${avg_entry:.3f})",
            detail=(
                f"Average entry price ${avg_entry:.3f} is well below the 50c midpoint. "
                f"This trader hunts for underpriced outcomes — if these resolve to $1.00, the upside is "
                f"{((1.0 - avg_entry) / avg_entry) * 100:.0f}% per position. Classic contrarian/value edge."
            ),
        ))
    elif avg_entry > 0 and avg_entry < 0.45:
        pros.append(ProCon(
            category="Alpha",
            observation=f"Below-midpoint entries (avg ${avg_entry:.3f})",
            detail=(
                f"Average entry below 50c suggests value-oriented approach. "
                f"Potential upside of {((1.0 - avg_entry) / avg_entry) * 100:.0f}% if positions resolve correctly."
            ),
        ))
    elif avg_entry > 0.85:
        cons.append(ProCon(
            category="Strategy",
            observation=f"Expensive entries (avg ${avg_entry:.3f})",
            detail=(
                f"Average buy price ${avg_entry:.2f} leaves only ${1.0 - avg_entry:.2f} of upside "
                f"vs ${avg_entry:.2f} of downside per share. Requires very high hit rate to be profitable."
            ),
            severity="warning",
        ))

    # ===================================================================
    #  3. MARKET TIMING — contrarian/extreme price entries
    # ===================================================================
    if analysis.pct_extreme_buys > 30:
        # Check if extreme buys are profitable
        extreme_pnl = sum(pnl for _, pnl, _ in analysis.extreme_buy_markets)
        if extreme_pnl > 0:
            pros.append(ProCon(
                category="Alpha",
                observation=f"Contrarian edge ({analysis.pct_extreme_buys:.0f}% extreme-price entries)",
                detail=(
                    f"{analysis.pct_extreme_buys:.0f}% of buys at extreme prices (<$0.20 or >$0.80). "
                    f"These extreme-entry markets generated est. ${extreme_pnl:,.0f} profit. "
                    f"This trader has conviction to act when the market is at extremes and is right often enough to profit."
                ),
            ))
        else:
            cons.append(ProCon(
                category="Strategy",
                observation=f"Unprofitable contrarian bets ({analysis.pct_extreme_buys:.0f}% extreme entries)",
                detail=(
                    f"{analysis.pct_extreme_buys:.0f}% of buys at extreme prices, but these markets lost "
                    f"est. ${abs(extreme_pnl):,.0f}. Catching falling knives or overpaying for near-certainties."
                ),
                severity="warning",
            ))
            recommendations.append("Review extreme-price entries: contrarian conviction is only valuable if you're right more often than the market price implies.")

    # ===================================================================
    #  4. POSITION SIZING DISCIPLINE
    # ===================================================================
    cv = analysis.sizing_cv
    if cv > 0:
        if cv < 0.5:
            pros.append(ProCon(
                category="Risk Management",
                observation=f"Disciplined position sizing (CV={cv:.2f})",
                detail=(
                    f"Position size coefficient of variation is {cv:.2f} (std/mean). "
                    f"Low variance in bet sizes suggests systematic sizing — likely using a fixed fraction "
                    f"or Kelly-based approach. This is a hallmark of professional risk management."
                ),
            ))
        elif cv > 2.0:
            cons.append(ProCon(
                category="Risk Management",
                observation=f"Erratic position sizing (CV={cv:.2f})",
                detail=(
                    f"Coefficient of variation {cv:.2f} means position sizes swing wildly. "
                    f"Avg ${analysis.sizing.avg_trade_size_usdc:,.0f} but std dev ${analysis.sizing.stddev_trade_size:,.0f}. "
                    f"A few oversized bets could dominate returns, making the edge fragile and hard to replicate."
                ),
                severity="warning",
            ))
            recommendations.append("Normalize position sizes. High CV means a few outsized trades dominate your P&L — this is not a scalable edge.")

    if analysis.sizing.max_trade_size_usdc > analysis.sizing.avg_trade_size_usdc * 20:
        cons.append(ProCon(
            category="Risk Management",
            observation="Outsized max trade",
            detail=(
                f"Max trade (${analysis.sizing.max_trade_size_usdc:,.0f}) is "
                f"{analysis.sizing.max_trade_size_usdc / max(analysis.sizing.avg_trade_size_usdc, 1):.0f}x the average. "
                f"If this single trade had gone wrong, it could wipe out many winning trades."
            ),
            severity="critical",
        ))

    # ===================================================================
    #  5. PROFIT-TAKING DISCIPLINE
    # ===================================================================
    if 0.8 < analysis.buy_sell_ratio < 1.5:
        pnl_positive = analysis.total_estimated_pnl > 0
        if pnl_positive:
            pros.append(ProCon(
                category="Alpha",
                observation="Active profit-taking with positive P&L",
                detail=(
                    f"Buy/sell ratio of {analysis.buy_sell_ratio:.2f} with est. P&L ${analysis.total_estimated_pnl:,.0f}. "
                    f"Balanced entries and exits combined with profitability = this trader knows when to take money off the table. "
                    f"Key behavior to replicate: they don't just buy and hold to expiry."
                ),
            ))
        else:
            pros.append(ProCon(
                category="Risk Management",
                observation="Active position management",
                detail=(
                    f"Buy/sell ratio of {analysis.buy_sell_ratio:.2f} shows they actively manage exits, "
                    f"even though overall est. P&L is ${analysis.total_estimated_pnl:,.0f}. "
                    f"They're cutting losses rather than holding losers to zero."
                ),
            ))
    elif analysis.buy_sell_ratio > 3:
        cons.append(ProCon(
            category="Risk Management",
            observation=f"Heavy buy bias (ratio: {analysis.buy_sell_ratio:.1f}x)",
            detail=(
                f"Buy/sell ratio of {analysis.buy_sell_ratio:.1f} — buying {analysis.buy_sell_ratio:.0f}x more than selling. "
                f"Either holding positions to binary resolution (high variance) or accumulating unrealized risk. "
                f"Hard to replicate because exits aren't market-timed — they rely on event outcomes."
            ),
            severity="warning",
        ))
        recommendations.append("High buy/sell ratio means profits depend on event outcomes, not trade timing. Consider taking partial profits before resolution.")

    # ===================================================================
    #  6. TOP MARKET HIT RATE — market selection skill
    # ===================================================================
    if analysis.top_market_results:
        win_rate = analysis.top_market_win_rate
        profitable_mkts = [t for t in analysis.top_market_results if t[1] > 0]
        losing_mkts = [t for t in analysis.top_market_results if t[1] < 0]

        if win_rate >= 70:
            best_market = max(analysis.top_market_results, key=lambda x: x[1])
            pros.append(ProCon(
                category="Alpha",
                observation=f"Excellent market selection ({win_rate:.0f}% hit rate on top 10)",
                detail=(
                    f"{len(profitable_mkts)}/{len(analysis.top_market_results)} of their largest markets by volume are profitable. "
                    f"Best market: \"{best_market[0][:50]}\" (${best_market[1]:,.0f} est. P&L). "
                    f"Strong market-picking is a real, replicable edge — study which markets they choose."
                ),
            ))
        elif win_rate <= 30 and len(analysis.top_market_results) >= 5:
            worst_market = min(analysis.top_market_results, key=lambda x: x[1])
            cons.append(ProCon(
                category="Strategy",
                observation=f"Poor market selection ({win_rate:.0f}% hit rate on top 10)",
                detail=(
                    f"Only {len(profitable_mkts)}/{len(analysis.top_market_results)} of their biggest markets are profitable. "
                    f"Worst market: \"{worst_market[0][:50]}\" (${worst_market[1]:,.0f} est. P&L). "
                    f"They're putting the most capital into losing markets — the market selection is a weakness, not an edge."
                ),
                severity="warning",
            ))
            recommendations.append("Review market selection process. The largest positions are consistently unprofitable — consider sizing down until conviction is validated.")

    # ===================================================================
    #  7. CONCENTRATION + PROFITABILITY — focused specialist vs unfocused
    # ===================================================================
    hhi = analysis.market_concentration
    conc_pnl = analysis.concentrated_market_pnl
    total_pnl = analysis.total_estimated_pnl

    if hhi > 0.15:
        # Concentrated
        if conc_pnl > 0:
            pros.append(ProCon(
                category="Alpha",
                observation="Focused specialist (concentrated + profitable)",
                detail=(
                    f"HHI of {hhi:.3f} — volume concentrated in few markets, and those top markets made "
                    f"est. ${conc_pnl:,.0f}. This trader knows their niche and sizes up when they have conviction. "
                    f"Concentration is a feature, not a bug, when the concentrated bets win."
                ),
            ))
        else:
            cons.append(ProCon(
                category="Risk Management",
                observation="Concentrated and losing",
                detail=(
                    f"HHI of {hhi:.3f} — heavily concentrated, and the top 3 markets lost est. ${abs(conc_pnl):,.0f}. "
                    f"Big bets on wrong markets. Concentration amplifies losses when market selection is poor."
                ),
                severity="critical",
            ))
            recommendations.append("Reduce concentration until market selection improves. Diversifying across more markets would limit damage from wrong calls.")
    elif hhi < 0.03:
        if total_pnl > 0:
            pros.append(ProCon(
                category="Strategy",
                observation="Profitable diversifier",
                detail=(
                    f"Spread across {analysis.unique_markets} markets (HHI {hhi:.3f}) with positive est. P&L ${total_pnl:,.0f}. "
                    f"Edge is not in any single market but in consistent small wins across many — a scalable approach."
                ),
            ))
        elif total_pnl < 0:
            cons.append(ProCon(
                category="Strategy",
                observation="Scattered without edge",
                detail=(
                    f"Widely diversified (HHI {hhi:.3f}, {analysis.unique_markets} markets) but losing est. ${abs(total_pnl):,.0f}. "
                    f"Spreading thin across many markets without a clear edge in any. Consider focusing on fewer markets where you have information advantage."
                ),
                severity="info",
            ))

    # ===================================================================
    #  8. CATEGORY DOMAIN EXPERTISE
    # ===================================================================
    cat_pnl = analysis.category_pnl
    cats = analysis.category_breakdown
    if cat_pnl and cats:
        # Find profitable categories with meaningful volume
        profitable_cats = [(cat, pnl) for cat, pnl in cat_pnl.items() if pnl > 0 and cats.get(cat, 0) >= 10]
        losing_cats = [(cat, pnl) for cat, pnl in cat_pnl.items() if pnl < 0 and cats.get(cat, 0) >= 10]

        if profitable_cats:
            profitable_cats.sort(key=lambda x: x[1], reverse=True)
            best_cat, best_pnl = profitable_cats[0]
            best_count = cats.get(best_cat, 0)
            pros.append(ProCon(
                category="Alpha",
                observation=f"Domain expertise: {best_cat}",
                detail=(
                    f"Profitable in {best_cat} ({best_count} trades, est. +${best_pnl:,.0f}). "
                    + (f"Also profitable in: {', '.join(c for c, _ in profitable_cats[1:3])}. " if len(profitable_cats) > 1 else "")
                    + f"Domain-specific knowledge is a durable edge — this trader likely has an informational advantage in {best_cat} markets."
                ),
            ))

        if losing_cats:
            losing_cats.sort(key=lambda x: x[1])
            worst_cat, worst_pnl = losing_cats[0]
            worst_count = cats.get(worst_cat, 0)
            cons.append(ProCon(
                category="Strategy",
                observation=f"Weak category: {worst_cat}",
                detail=(
                    f"Losing est. ${abs(worst_pnl):,.0f} in {worst_cat} across {worst_count} trades. "
                    f"This is a category to avoid or study more before trading. "
                    f"The edge present in other categories does not transfer here."
                ),
                severity="info",
            ))
            recommendations.append(f"Consider reducing or eliminating {worst_cat} trades — P&L is negative and dragging down overall performance.")

    # ===================================================================
    #  9. PRICING BEHAVIOR
    # ===================================================================
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
            detail=(
                f"{analysis.pricing.pct_buying_above_50c:.0f}% of buys at > $0.50 — primarily buying favorites. "
                f"Expected value is lower because you pay more for outcomes the market already expects."
            ),
            severity="info",
        ))
        recommendations.append("Buying favorites at >50c offers asymmetric downside. Look for value in less popular outcomes where the market may be wrong.")

    # ===================================================================
    #  10. OVERTRADING CHECK
    # ===================================================================
    if analysis.timing.avg_trades_per_day > 100:
        cons.append(ProCon(
            category="Overtrading",
            observation="Very high frequency",
            detail=(
                f"{analysis.timing.avg_trades_per_day:.0f} trades/day average — likely algorithmic or bot-driven. "
                f"If manual, this frequency usually degrades edge through impulsive decisions and fee drag."
            ),
            severity="warning",
        ))
        recommendations.append("If trading manually at 100+ trades/day, review whether frequency adds value or just generates fees.")

    # ===================================================================
    #  BACKTEST RESULTS (kept as-is — these are already good)
    # ===================================================================
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
        "avg_entry_price": f"${analysis.avg_entry_price:.3f}",
        "avg_exit_price": f"${analysis.avg_exit_price:.3f}",
        "buy_sell_spread": f"${analysis.buy_sell_spread:+.3f}",
        "buy_sell_ratio": f"{analysis.buy_sell_ratio:.2f}",
        "top_market_win_rate": f"{analysis.top_market_win_rate:.0f}%",
        "market_concentration": f"{analysis.market_concentration:.4f}",
        "est_total_pnl": f"${analysis.total_estimated_pnl:,.0f}",
        "avg_trades_per_day": f"{analysis.timing.avg_trades_per_day:.1f}",
        "trading_streak": f"{analysis.timing.trading_streak_days} days",
        "date_range": f"{analysis.date_range[0][:10]} to {analysis.date_range[1][:10]}",
    }

    # --- SUMMARY ---
    summary_parts = [
        f"Analyzed {analysis.total_trades:,} trades across {analysis.unique_markets} markets.",
        f"Total volume: ${analysis.total_volume_usdc:,.0f}.",
        f"Entry/exit spread: ${analysis.buy_sell_spread:+.3f}.",
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
