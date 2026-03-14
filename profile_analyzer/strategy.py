"""
Strategy reverse-engineering engine.

Analyzes a trader's trade history to classify their strategy type,
identify edges, detect position management patterns, and generate
actionable replication tips.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from .fetcher import Trade
from .patterns import AnalysisResult, MarketSummary, _parse_ts
from .backtest import BacktestResult


# Reuse the same category classification keywords from patterns.py
CATEGORY_KEYWORDS = {
    "Crypto": ["bitcoin", "btc", "crypto", "eth", "ethereum", "solana", "sol"],
    "Politics": ["trump", "biden", "president", "election", "congress", "senate", "governor"],
    "Sports": ["nfl", "nba", "mlb", "sports", "game", "match", "score", "super bowl"],
    "Economics": ["fed", "cpi", "gdp", "inflation", "rate", "economy", "jobs", "unemployment"],
    "Weather": ["weather", "hurricane", "earthquake", "temperature"],
    "Price Prediction": ["up or down", "above", "below", "price"],
}


def _classify_category(title: str) -> str:
    """Classify a market title into a category."""
    title_lower = (title or "").lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(w in title_lower for w in keywords):
            return cat
    return "Other"


@dataclass
class StrategyProfile:
    """Reverse-engineered strategy profile."""
    strategy_type: str  # e.g. "Contrarian Value", "Momentum", "Scalper", "Event-Driven", "Market Maker"
    confidence: float  # 0-1 how confident we are in the classification

    # Entry patterns
    avg_entry_price: float
    entry_price_distribution: dict  # histogram of entry prices
    prefers_underdogs: bool  # buys mostly < 0.50
    prefers_favorites: bool  # buys mostly > 0.50

    # Timing patterns
    avg_time_in_market: float  # average hours between first buy and last sell in same market
    quick_flipper: bool  # flips within hours
    long_holder: bool  # holds for days+

    # Edge analysis
    edge_by_category: dict  # category -> {trades, pnl, win_rate}
    edge_by_price_range: dict  # price range -> {trades, pnl, win_rate}
    best_category: str
    worst_category: str

    # Market selection patterns
    market_entry_timing: str  # "early", "late", "mixed"
    avg_market_age_at_entry: float  # estimated days

    # Position management
    scales_in: bool  # makes multiple buys in same market over time
    scales_out: bool  # makes multiple sells over time
    avg_trades_per_market: float
    uses_both_sides: bool  # trades both Yes and No in same market

    # Profitability patterns
    profitable_patterns: list  # human-readable descriptions
    unprofitable_patterns: list

    # Strategy summary
    summary: str  # 2-3 sentence plain English summary
    key_edges: list  # bullet points of main edges
    weaknesses: list  # bullet points of exploitable weaknesses
    replication_tips: list  # how to replicate


def analyze_strategy(
    trades: list[Trade],
    analysis: AnalysisResult,
    backtest: Optional[BacktestResult] = None,
) -> StrategyProfile:
    """
    Reverse-engineer a trader's strategy from their trade history.

    Uses the trades list, the pattern analysis result, and optionally
    the backtest result to classify the strategy and identify edges.
    """
    if not trades:
        raise ValueError("No trades to analyze")

    # ------------------------------------------------------------------ #
    # 1. Entry price analysis
    # ------------------------------------------------------------------ #
    buy_trades = [t for t in trades if t.side == "BUY" and t.price > 0]
    sell_trades = [t for t in trades if t.side == "SELL" and t.price > 0]
    buy_prices = [t.price for t in buy_trades]

    avg_entry = sum(buy_prices) / len(buy_prices) if buy_prices else 0.0

    # Price distribution histogram
    price_bins = {
        "0.00-0.10": 0, "0.10-0.20": 0, "0.20-0.30": 0,
        "0.30-0.40": 0, "0.40-0.50": 0, "0.50-0.60": 0,
        "0.60-0.70": 0, "0.70-0.80": 0, "0.80-0.90": 0,
        "0.90-1.00": 0,
    }
    for p in buy_prices:
        if p < 0.10:
            price_bins["0.00-0.10"] += 1
        elif p < 0.20:
            price_bins["0.10-0.20"] += 1
        elif p < 0.30:
            price_bins["0.20-0.30"] += 1
        elif p < 0.40:
            price_bins["0.30-0.40"] += 1
        elif p < 0.50:
            price_bins["0.40-0.50"] += 1
        elif p < 0.60:
            price_bins["0.50-0.60"] += 1
        elif p < 0.70:
            price_bins["0.60-0.70"] += 1
        elif p < 0.80:
            price_bins["0.70-0.80"] += 1
        elif p < 0.90:
            price_bins["0.80-0.90"] += 1
        else:
            price_bins["0.90-1.00"] += 1

    total_buys = len(buy_prices) or 1
    pct_below_50 = sum(1 for p in buy_prices if p < 0.50) / total_buys
    pct_above_50 = sum(1 for p in buy_prices if p >= 0.50) / total_buys
    pct_below_40 = sum(1 for p in buy_prices if p < 0.40) / total_buys
    pct_above_60 = sum(1 for p in buy_prices if p >= 0.60) / total_buys

    prefers_underdogs = pct_below_50 > 0.60
    prefers_favorites = pct_above_50 > 0.60

    # ------------------------------------------------------------------ #
    # 2. Group trades by market
    # ------------------------------------------------------------------ #
    market_trades: dict[str, list[Trade]] = defaultdict(list)
    for t in trades:
        key = t.condition_id or t.slug
        if key:
            market_trades[key].append(t)

    # ------------------------------------------------------------------ #
    # 3. Hold time analysis
    # ------------------------------------------------------------------ #
    hold_times_hours: list[float] = []
    for mkey, mtrades in market_trades.items():
        if len(mtrades) < 2:
            continue
        timestamps = [_parse_ts(t.timestamp) for t in mtrades]
        valid = [ts for ts in timestamps if ts is not None]
        if len(valid) < 2:
            continue
        first = min(valid)
        last = max(valid)
        diff_hours = (last - first).total_seconds() / 3600.0
        hold_times_hours.append(diff_hours)

    avg_hold_hours = sum(hold_times_hours) / len(hold_times_hours) if hold_times_hours else 0.0
    quick_flipper = avg_hold_hours < 24.0
    long_holder = avg_hold_hours > 168.0  # 7 days

    # ------------------------------------------------------------------ #
    # 4. Scaling detection
    # ------------------------------------------------------------------ #
    scales_in_count = 0
    scales_out_count = 0
    for mkey, mtrades in market_trades.items():
        buy_ts = set()
        sell_ts = set()
        for t in mtrades:
            ts = _parse_ts(t.timestamp)
            if ts is None:
                continue
            if t.side == "BUY":
                buy_ts.add(ts)
            else:
                sell_ts.add(ts)
        if len(buy_ts) >= 3:
            scales_in_count += 1
        if len(sell_ts) >= 3:
            scales_out_count += 1

    total_markets = len(market_trades) or 1
    scales_in = scales_in_count / total_markets > 0.10  # >10% of markets
    scales_out = scales_out_count / total_markets > 0.10

    # ------------------------------------------------------------------ #
    # 5. Both-sides detection
    # ------------------------------------------------------------------ #
    both_sides_count = 0
    for mkey, mtrades in market_trades.items():
        outcomes = set(t.outcome for t in mtrades if t.outcome)
        if len(outcomes) >= 2:
            both_sides_count += 1
    uses_both_sides = both_sides_count / total_markets > 0.05

    # ------------------------------------------------------------------ #
    # 6. Edge by category
    # ------------------------------------------------------------------ #
    # Build per-market pnl from analysis market_summaries
    # Only include markets with known PnL (resolved or has sells)
    per_market_pnl: dict[str, float] = {}
    known_pnl_markets: set[str] = set()
    for ms in analysis.market_summaries:
        key = ms.condition_id or ms.slug
        if ms.is_resolved or ms.sell_count > 0:
            per_market_pnl[key] = ms.estimated_pnl
            known_pnl_markets.add(key)

    # Map market -> category, accumulate stats (only for known-PnL markets)
    cat_stats: dict[str, dict] = defaultdict(lambda: {"trades": 0, "pnl": 0.0, "wins": 0, "total_markets": 0})
    market_categories: dict[str, str] = {}
    for mkey, mtrades in market_trades.items():
        title = mtrades[0].title if mtrades else ""
        cat = _classify_category(title)
        market_categories[mkey] = cat
        if mkey not in known_pnl_markets:
            continue  # skip markets with unknown PnL (open, no sells)
        pnl = per_market_pnl.get(mkey, 0.0)
        cs = cat_stats[cat]
        cs["trades"] += len(mtrades)
        cs["pnl"] += pnl
        cs["total_markets"] += 1
        if pnl > 0:
            cs["wins"] += 1

    edge_by_category: dict[str, dict] = {}
    for cat, stats in cat_stats.items():
        win_rate = (stats["wins"] / stats["total_markets"] * 100) if stats["total_markets"] > 0 else 0.0
        edge_by_category[cat] = {
            "trades": stats["trades"],
            "pnl": round(stats["pnl"], 2),
            "win_rate": round(win_rate, 1),
        }

    # Best / worst category
    if edge_by_category:
        best_category = max(edge_by_category, key=lambda c: edge_by_category[c]["pnl"])
        worst_category = min(edge_by_category, key=lambda c: edge_by_category[c]["pnl"])
    else:
        best_category = "Unknown"
        worst_category = "Unknown"

    # ------------------------------------------------------------------ #
    # 7. Edge by price range
    # ------------------------------------------------------------------ #
    price_range_labels = [
        ("0.00-0.20", 0.0, 0.20),
        ("0.20-0.40", 0.20, 0.40),
        ("0.40-0.60", 0.40, 0.60),
        ("0.60-0.80", 0.60, 0.80),
        ("0.80-1.00", 0.80, 1.01),
    ]

    # For each buy trade, bucket by price and track if the market was profitable
    pr_stats: dict[str, dict] = {
        label: {"trades": 0, "pnl": 0.0, "wins": 0, "total_markets": 0}
        for label, _, _ in price_range_labels
    }

    # Group buy trades by market and price range (only known-PnL markets for PnL)
    market_pr_seen: dict[str, set] = defaultdict(set)  # market -> set of price ranges seen
    for t in buy_trades:
        mkey = t.condition_id or t.slug
        for label, lo, hi in price_range_labels:
            if lo <= t.price < hi:
                pr_stats[label]["trades"] += 1
                if mkey in known_pnl_markets and label not in market_pr_seen[mkey]:
                    market_pr_seen[mkey].add(label)
                    # Attribute a proportional share of market pnl
                    pnl = per_market_pnl.get(mkey, 0.0)
                    # Count total price ranges this market spans
                    all_ranges = set()
                    for mt in market_trades.get(mkey, []):
                        if mt.side == "BUY":
                            for l2, lo2, hi2 in price_range_labels:
                                if lo2 <= mt.price < hi2:
                                    all_ranges.add(l2)
                    share = 1.0 / len(all_ranges) if all_ranges else 1.0
                    pr_stats[label]["pnl"] += pnl * share
                    pr_stats[label]["total_markets"] += 1
                    if pnl > 0:
                        pr_stats[label]["wins"] += 1
                break

    edge_by_price_range: dict[str, dict] = {}
    for label, _, _ in price_range_labels:
        stats = pr_stats[label]
        win_rate = (stats["wins"] / stats["total_markets"] * 100) if stats["total_markets"] > 0 else 0.0
        edge_by_price_range[label] = {
            "trades": stats["trades"],
            "pnl": round(stats["pnl"], 2),
            "win_rate": round(win_rate, 1),
        }

    # ------------------------------------------------------------------ #
    # 8. Market entry timing estimation
    # ------------------------------------------------------------------ #
    # We don't have market creation dates, so estimate based on the
    # relative position of the trader's first trade vs all trades we see
    # in the dataset.  For now, use a heuristic: if the trader's first
    # trade in a market is among the earliest 20% of all observed trades,
    # classify as "early".
    if hold_times_hours:
        median_hold = sorted(hold_times_hours)[len(hold_times_hours) // 2]
    else:
        median_hold = 0.0

    # Simple heuristic for entry timing
    if median_hold > 168:  # > 7 days avg hold = entering early
        market_entry_timing = "early"
    elif median_hold < 24:  # < 1 day = entering late / close to resolution
        market_entry_timing = "late"
    else:
        market_entry_timing = "mixed"

    avg_market_age_at_entry = median_hold / 24.0  # rough proxy in days

    # ------------------------------------------------------------------ #
    # 9. Strategy classification via scoring
    # ------------------------------------------------------------------ #
    scores = {
        "Contrarian Value": 0.0,
        "Momentum": 0.0,
        "Scalper": 0.0,
        "Event-Driven": 0.0,
        "Market Maker": 0.0,
    }

    # Contrarian Value: buys mostly < 0.40, profitable, low frequency
    if pct_below_40 > 0.50:
        scores["Contrarian Value"] += 3.0
    if pct_below_40 > 0.30:
        scores["Contrarian Value"] += 1.0
    if prefers_underdogs:
        scores["Contrarian Value"] += 2.0
    total_pnl = sum(per_market_pnl.values())
    if total_pnl > 0:
        scores["Contrarian Value"] += 1.0
    if analysis.timing.avg_trades_per_day < 10:
        scores["Contrarian Value"] += 1.0

    # Momentum: buys mostly > 0.60, rides winners
    if pct_above_60 > 0.50:
        scores["Momentum"] += 3.0
    if pct_above_60 > 0.30:
        scores["Momentum"] += 1.0
    if prefers_favorites:
        scores["Momentum"] += 2.0
    if long_holder:
        scores["Momentum"] += 1.0

    # Scalper: high frequency, small positions, quick flips
    if quick_flipper:
        scores["Scalper"] += 3.0
    if analysis.timing.avg_trades_per_day > 20:
        scores["Scalper"] += 2.0
    if analysis.sizing.avg_trade_size_usdc < 50:
        scores["Scalper"] += 1.0
    if analysis.avg_trades_per_market > 5:
        scores["Scalper"] += 1.0
    buy_sell_ratio = analysis.buy_sell_ratio
    if 0.7 < buy_sell_ratio < 1.5:
        scores["Scalper"] += 1.0

    # Event-Driven: concentrated in specific categories
    if analysis.category_breakdown:
        top_cat_count = max(analysis.category_breakdown.values())
        top_cat_pct = top_cat_count / analysis.total_trades
        if top_cat_pct > 0.60:
            scores["Event-Driven"] += 3.0
        if top_cat_pct > 0.40:
            scores["Event-Driven"] += 1.0
        # Check if top category is not "Other"
        top_cat_name = max(analysis.category_breakdown, key=analysis.category_breakdown.get)
        if top_cat_name != "Other" and top_cat_pct > 0.40:
            scores["Event-Driven"] += 2.0

    # Market Maker: both sides, balanced buy/sell, trades many markets
    if uses_both_sides:
        scores["Market Maker"] += 3.0
    if 0.8 < buy_sell_ratio < 1.3:
        scores["Market Maker"] += 2.0
    if analysis.unique_markets > 50:
        scores["Market Maker"] += 1.0
    if both_sides_count / total_markets > 0.15:
        scores["Market Maker"] += 2.0

    # Pick the highest-scoring strategy
    max_score = max(scores.values()) if scores else 0
    strategy_type = max(scores, key=scores.get) if max_score > 0 else "Mixed"

    # Confidence: normalize the score
    total_possible = 8.0  # approximate max for any strategy
    confidence = min(max_score / total_possible, 1.0)

    # If no clear winner (top two are close), lower confidence
    sorted_scores = sorted(scores.values(), reverse=True)
    if len(sorted_scores) >= 2 and sorted_scores[0] - sorted_scores[1] <= 1:
        confidence *= 0.7

    # ------------------------------------------------------------------ #
    # 10. Generate human-readable patterns
    # ------------------------------------------------------------------ #
    profitable_patterns: list[str] = []
    unprofitable_patterns: list[str] = []

    # Category-based patterns
    for cat, stats in edge_by_category.items():
        pnl = stats["pnl"]
        wr = stats["win_rate"]
        tc = stats["trades"]
        if tc < 5:
            continue
        if pnl > 0 and wr > 50:
            profitable_patterns.append(
                f"Strong edge in {cat} markets ({wr:.0f}% win rate, {'+' if pnl > 0 else ''}${pnl:,.0f} PnL, {tc} trades)"
            )
        elif pnl < 0:
            unprofitable_patterns.append(
                f"Loses money on {cat} markets ({wr:.0f}% win rate, ${pnl:,.0f} PnL, {tc} trades)"
            )

    # Price range patterns
    for label, stats in edge_by_price_range.items():
        pnl = stats["pnl"]
        wr = stats["win_rate"]
        tc = stats["trades"]
        if tc < 5:
            continue
        if pnl > 0 and wr > 50:
            profitable_patterns.append(
                f"Profitable buying at ${label} ({wr:.0f}% win rate, +${pnl:,.0f})"
            )
        elif pnl < -100:
            unprofitable_patterns.append(
                f"Unprofitable buying at ${label} ({wr:.0f}% win rate, ${pnl:,.0f})"
            )

    # Position management patterns
    if scales_in:
        profitable_patterns.append("Scales into positions over multiple entries (disciplined averaging)")
    if long_holder and total_pnl > 0:
        profitable_patterns.append("Patient holder -- lets winning positions run for days or longer")
    if quick_flipper and total_pnl < 0:
        unprofitable_patterns.append("Quick flipping may incur excessive fees relative to edge")

    # Ensure we always have at least one entry
    if not profitable_patterns:
        if total_pnl > 0:
            profitable_patterns.append(f"Net profitable overall (+${total_pnl:,.0f})")
        else:
            profitable_patterns.append("No clearly profitable patterns identified -- limited data or mixed results")
    if not unprofitable_patterns:
        if total_pnl < 0:
            unprofitable_patterns.append(f"Net unprofitable overall (${total_pnl:,.0f})")
        else:
            unprofitable_patterns.append("No major weaknesses identified from available data")

    # ------------------------------------------------------------------ #
    # 11. Generate summary, edges, weaknesses, tips
    # ------------------------------------------------------------------ #
    # Summary
    hold_desc = "quick flips" if quick_flipper else ("long holds" if long_holder else "medium-term holds")
    price_desc = "underdog" if prefers_underdogs else ("favorite" if prefers_favorites else "balanced")

    summary_parts = [
        f"This trader employs a {strategy_type} strategy (confidence: {confidence:.0%}), "
        f"primarily buying {price_desc} outcomes at an average entry price of ${avg_entry:.2f}. "
    ]
    if best_category != worst_category:
        summary_parts.append(
            f"Their strongest edge is in {best_category} markets, while {worst_category} is their weakest area. "
        )
    summary_parts.append(
        f"Typical hold style: {hold_desc}, with an average of {analysis.avg_trades_per_market:.1f} trades per market."
    )
    summary = "".join(summary_parts)

    # Key edges
    key_edges: list[str] = []
    if edge_by_category.get(best_category, {}).get("pnl", 0) > 0:
        bc_stats = edge_by_category[best_category]
        key_edges.append(
            f"Strong edge in {best_category} ({bc_stats['win_rate']:.0f}% win rate, +${bc_stats['pnl']:,.0f})"
        )
    if prefers_underdogs and avg_entry < 0.40:
        key_edges.append(f"Finds value in underdog positions (avg entry ${avg_entry:.2f})")
    if scales_in:
        key_edges.append("Disciplined scaling -- enters positions gradually across multiple buys")
    if backtest and backtest.profit_factor > 1.5:
        key_edges.append(f"Strong profit factor of {backtest.profit_factor:.2f}")
    if backtest and backtest.win_rate > 55:
        key_edges.append(f"Above-average win rate of {backtest.win_rate:.1f}%")
    if not key_edges:
        key_edges.append("No standout edge identified -- strategy may rely on volume or specific market conditions")

    # Weaknesses
    weakness_list: list[str] = []
    if edge_by_category.get(worst_category, {}).get("pnl", 0) < 0:
        wc_stats = edge_by_category[worst_category]
        weakness_list.append(
            f"Loses money in {worst_category} markets (${wc_stats['pnl']:,.0f})"
        )
    if prefers_favorites and avg_entry > 0.70:
        weakness_list.append("Buying high-priced favorites limits upside and increases risk of loss")
    if analysis.market_concentration > 0.20:
        weakness_list.append("Highly concentrated in few markets -- large single-market risk")
    if backtest and backtest.max_drawdown_pct > 40:
        weakness_list.append(f"Large max drawdown of {backtest.max_drawdown_pct:.1f}%")
    if not weakness_list:
        weakness_list.append("No major weaknesses identified from available data")

    # Replication tips
    replication_tips: list[str] = []
    if edge_by_category.get(best_category, {}).get("pnl", 0) > 0:
        replication_tips.append(f"Focus on {best_category} markets -- that is where this trader has the most edge")
    if prefers_underdogs:
        replication_tips.append(f"Look for underdog positions priced below ${avg_entry:.2f}")
    if prefers_favorites:
        replication_tips.append("Target high-probability outcomes, but be selective -- only take favorites with strong conviction")
    if scales_in:
        replication_tips.append("Enter positions gradually over time rather than one large buy")
    if long_holder:
        replication_tips.append("Be patient -- hold positions for days or longer, do not rush to exit")
    if quick_flipper:
        replication_tips.append("Move fast -- enter and exit within hours, focus on liquid markets")
    if edge_by_category.get(worst_category, {}).get("pnl", 0) < 0:
        replication_tips.append(f"Avoid {worst_category} markets -- this trader loses money there too")

    # Find best price range
    best_pr = max(edge_by_price_range, key=lambda k: edge_by_price_range[k]["pnl"]) if edge_by_price_range else None
    if best_pr and edge_by_price_range[best_pr]["pnl"] > 0:
        replication_tips.append(
            f"Target entry prices in the ${best_pr} range for best results"
        )

    if not replication_tips:
        replication_tips.append("Insufficient data to generate specific replication tips")

    # ------------------------------------------------------------------ #
    # Build and return StrategyProfile
    # ------------------------------------------------------------------ #
    return StrategyProfile(
        strategy_type=strategy_type,
        confidence=round(confidence, 3),
        avg_entry_price=round(avg_entry, 4),
        entry_price_distribution=price_bins,
        prefers_underdogs=prefers_underdogs,
        prefers_favorites=prefers_favorites,
        avg_time_in_market=round(avg_hold_hours, 2),
        quick_flipper=quick_flipper,
        long_holder=long_holder,
        edge_by_category=edge_by_category,
        edge_by_price_range=edge_by_price_range,
        best_category=best_category,
        worst_category=worst_category,
        market_entry_timing=market_entry_timing,
        avg_market_age_at_entry=round(avg_market_age_at_entry, 2),
        scales_in=scales_in,
        scales_out=scales_out,
        avg_trades_per_market=round(analysis.avg_trades_per_market, 2),
        uses_both_sides=uses_both_sides,
        profitable_patterns=profitable_patterns,
        unprofitable_patterns=unprofitable_patterns,
        summary=summary,
        key_edges=key_edges,
        weaknesses=weakness_list,
        replication_tips=replication_tips,
    )
