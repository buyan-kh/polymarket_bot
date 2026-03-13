"""
Pattern analyzer - finds trading patterns from a user's Polymarket trades.

Analyzes:
- Market category preferences
- Timing patterns (time of day, day of week)
- Position sizing habits
- Win/loss patterns
- Market concentration vs diversification
- Buy vs sell ratios
- Average hold times
- Favorite price ranges
- Contrarian vs momentum behavior
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

from .fetcher import Trade


@dataclass
class MarketSummary:
    """Summary of activity in a single market."""
    title: str
    slug: str
    condition_id: str
    total_trades: int = 0
    buy_count: int = 0
    sell_count: int = 0
    total_volume: float = 0.0
    avg_buy_price: float = 0.0
    avg_sell_price: float = 0.0
    net_position: float = 0.0  # positive = net long
    estimated_pnl: float = 0.0
    first_trade: Optional[str] = None
    last_trade: Optional[str] = None
    outcomes_traded: list = field(default_factory=list)


@dataclass
class TimingPattern:
    """When the user tends to trade."""
    most_active_hours: list  # list of (hour, count)
    most_active_days: list  # list of (weekday_name, count)
    avg_trades_per_day: float
    busiest_date: str
    busiest_date_count: int
    trading_streak_days: int  # longest consecutive days of trading


@dataclass
class SizingPattern:
    """How the user sizes positions."""
    avg_trade_size_usdc: float
    median_trade_size_usdc: float
    max_trade_size_usdc: float
    min_trade_size_usdc: float
    stddev_trade_size: float
    size_buckets: dict  # e.g. {"<$10": 50, "$10-100": 200, ...}


@dataclass
class PricePattern:
    """Price entry preferences."""
    avg_buy_price: float
    median_buy_price: float
    pct_buying_below_50c: float  # percentage of buys at < $0.50
    pct_buying_above_50c: float
    avg_sell_price: float
    favorite_price_ranges: list  # list of (range_str, count)


@dataclass
class AnalysisResult:
    """Complete pattern analysis result."""
    username: str
    wallet: str
    total_trades: int
    total_volume_usdc: float
    unique_markets: int
    date_range: tuple  # (first_trade, last_trade)
    market_summaries: list[MarketSummary]
    timing: TimingPattern
    sizing: SizingPattern
    pricing: PricePattern
    buy_sell_ratio: float
    top_markets_by_volume: list  # top 10
    top_markets_by_trades: list  # top 10
    category_breakdown: dict  # category -> count
    outcome_preference: dict  # Yes/No -> count
    avg_trades_per_market: float
    market_concentration: float  # Herfindahl index (0-1, higher = more concentrated)


def _parse_ts(ts_str: str) -> Optional[datetime]:
    """Parse a timestamp string to datetime."""
    if not ts_str:
        return None
    try:
        # Try ISO format
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        pass
    try:
        # Try unix timestamp
        return datetime.fromtimestamp(float(ts_str), tz=timezone.utc)
    except (ValueError, OSError):
        pass
    return None


def _median(values: list[float]) -> float:
    """Compute median."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    if n % 2 == 0:
        return (s[n // 2 - 1] + s[n // 2]) / 2
    return s[n // 2]


def _stddev(values: list[float]) -> float:
    """Compute standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance ** 0.5


def analyze_patterns(trades: list[Trade], username: str = "", wallet: str = "") -> AnalysisResult:
    """
    Run full pattern analysis on a list of trades.
    """
    if not trades:
        raise ValueError("No trades to analyze")

    # --- Market-level summaries ---
    markets: dict[str, MarketSummary] = {}
    for t in trades:
        key = t.condition_id or t.slug
        if key not in markets:
            markets[key] = MarketSummary(
                title=t.title, slug=t.slug, condition_id=t.condition_id
            )
        m = markets[key]
        m.total_trades += 1
        m.total_volume += t.usdc_size

        if t.side == "BUY":
            m.buy_count += 1
            m.net_position += t.size
        else:
            m.sell_count += 1
            m.net_position -= t.size

        if t.outcome and t.outcome not in m.outcomes_traded:
            m.outcomes_traded.append(t.outcome)

        if not m.first_trade or t.timestamp < m.first_trade:
            m.first_trade = t.timestamp
        if not m.last_trade or t.timestamp > m.last_trade:
            m.last_trade = t.timestamp

    # Compute per-market averages
    for m in markets.values():
        buy_trades = [t for t in trades if (t.condition_id or t.slug) == (m.condition_id or m.slug) and t.side == "BUY"]
        sell_trades = [t for t in trades if (t.condition_id or t.slug) == (m.condition_id or m.slug) and t.side == "SELL"]
        if buy_trades:
            m.avg_buy_price = sum(t.price for t in buy_trades) / len(buy_trades)
        if sell_trades:
            m.avg_sell_price = sum(t.price for t in sell_trades) / len(sell_trades)
        # Rough PnL: sells - buys (in USDC)
        m.estimated_pnl = sum(t.usdc_size for t in sell_trades) - sum(t.usdc_size for t in buy_trades)

    market_list = sorted(markets.values(), key=lambda m: m.total_volume, reverse=True)

    # --- Timing patterns ---
    timestamps = [_parse_ts(t.timestamp) for t in trades]
    valid_ts = [ts for ts in timestamps if ts is not None]

    hour_counts = Counter(ts.hour for ts in valid_ts)
    day_counts = Counter(ts.strftime("%A") for ts in valid_ts)
    date_counts = Counter(ts.strftime("%Y-%m-%d") for ts in valid_ts)

    most_active_hours = hour_counts.most_common(5)
    most_active_days = day_counts.most_common(7)
    busiest_date, busiest_count = date_counts.most_common(1)[0] if date_counts else ("N/A", 0)

    # Trading streak
    trade_dates = sorted(set(ts.date() for ts in valid_ts))
    max_streak = 1
    current_streak = 1
    for i in range(1, len(trade_dates)):
        if (trade_dates[i] - trade_dates[i - 1]).days == 1:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 1

    num_days = (trade_dates[-1] - trade_dates[0]).days + 1 if len(trade_dates) > 1 else 1

    timing = TimingPattern(
        most_active_hours=most_active_hours,
        most_active_days=most_active_days,
        avg_trades_per_day=len(trades) / max(num_days, 1),
        busiest_date=busiest_date,
        busiest_date_count=busiest_count,
        trading_streak_days=max_streak,
    )

    # --- Sizing patterns ---
    sizes = [t.usdc_size for t in trades if t.usdc_size > 0]
    if not sizes:
        sizes = [t.size * t.price for t in trades if t.size > 0]

    size_buckets = {"<$10": 0, "$10-$100": 0, "$100-$1K": 0, "$1K-$10K": 0, ">$10K": 0}
    for s in sizes:
        if s < 10:
            size_buckets["<$10"] += 1
        elif s < 100:
            size_buckets["$10-$100"] += 1
        elif s < 1000:
            size_buckets["$100-$1K"] += 1
        elif s < 10000:
            size_buckets["$1K-$10K"] += 1
        else:
            size_buckets[">$10K"] += 1

    sizing = SizingPattern(
        avg_trade_size_usdc=sum(sizes) / len(sizes) if sizes else 0,
        median_trade_size_usdc=_median(sizes),
        max_trade_size_usdc=max(sizes) if sizes else 0,
        min_trade_size_usdc=min(sizes) if sizes else 0,
        stddev_trade_size=_stddev(sizes),
        size_buckets=size_buckets,
    )

    # --- Price patterns ---
    buy_prices = [t.price for t in trades if t.side == "BUY" and t.price > 0]
    sell_prices = [t.price for t in trades if t.side == "SELL" and t.price > 0]

    price_ranges = Counter()
    for p in buy_prices:
        if p < 0.10:
            price_ranges["$0.00-$0.10"] += 1
        elif p < 0.20:
            price_ranges["$0.10-$0.20"] += 1
        elif p < 0.30:
            price_ranges["$0.20-$0.30"] += 1
        elif p < 0.40:
            price_ranges["$0.30-$0.40"] += 1
        elif p < 0.50:
            price_ranges["$0.40-$0.50"] += 1
        elif p < 0.60:
            price_ranges["$0.50-$0.60"] += 1
        elif p < 0.70:
            price_ranges["$0.60-$0.70"] += 1
        elif p < 0.80:
            price_ranges["$0.70-$0.80"] += 1
        elif p < 0.90:
            price_ranges["$0.80-$0.90"] += 1
        else:
            price_ranges["$0.90-$1.00"] += 1

    below_50 = len([p for p in buy_prices if p < 0.50])
    above_50 = len([p for p in buy_prices if p >= 0.50])
    total_buy = len(buy_prices) or 1

    pricing = PricePattern(
        avg_buy_price=sum(buy_prices) / len(buy_prices) if buy_prices else 0,
        median_buy_price=_median(buy_prices),
        pct_buying_below_50c=below_50 / total_buy * 100,
        pct_buying_above_50c=above_50 / total_buy * 100,
        avg_sell_price=sum(sell_prices) / len(sell_prices) if sell_prices else 0,
        favorite_price_ranges=price_ranges.most_common(5),
    )

    # --- Outcome preference ---
    outcome_counts = Counter(t.outcome for t in trades if t.outcome)

    # --- Category breakdown (from market titles) ---
    categories = Counter()
    for t in trades:
        title = (t.title or "").lower()
        if any(w in title for w in ["bitcoin", "btc", "crypto", "eth", "ethereum", "solana", "sol"]):
            categories["Crypto"] += 1
        elif any(w in title for w in ["trump", "biden", "president", "election", "congress", "senate", "governor"]):
            categories["Politics"] += 1
        elif any(w in title for w in ["nfl", "nba", "mlb", "sports", "game", "match", "score", "super bowl"]):
            categories["Sports"] += 1
        elif any(w in title for w in ["fed", "cpi", "gdp", "inflation", "rate", "economy", "jobs", "unemployment"]):
            categories["Economics"] += 1
        elif any(w in title for w in ["weather", "hurricane", "earthquake", "temperature"]):
            categories["Weather"] += 1
        elif any(w in title for w in ["up or down", "above", "below", "price"]):
            categories["Price Prediction"] += 1
        else:
            categories["Other"] += 1

    # --- Concentration (Herfindahl index) ---
    total_vol = sum(m.total_volume for m in market_list)
    if total_vol > 0:
        shares = [(m.total_volume / total_vol) ** 2 for m in market_list]
        hhi = sum(shares)
    else:
        hhi = 0

    # --- Buy/sell ratio ---
    total_buys = sum(1 for t in trades if t.side == "BUY")
    total_sells = sum(1 for t in trades if t.side == "SELL")
    buy_sell_ratio = total_buys / max(total_sells, 1)

    # --- Date range ---
    sorted_ts = sorted(valid_ts)
    date_range = (
        sorted_ts[0].isoformat() if sorted_ts else "N/A",
        sorted_ts[-1].isoformat() if sorted_ts else "N/A",
    )

    return AnalysisResult(
        username=username,
        wallet=wallet,
        total_trades=len(trades),
        total_volume_usdc=sum(t.usdc_size for t in trades),
        unique_markets=len(markets),
        date_range=date_range,
        market_summaries=market_list,
        timing=timing,
        sizing=sizing,
        pricing=pricing,
        buy_sell_ratio=buy_sell_ratio,
        top_markets_by_volume=[(m.title, m.total_volume) for m in market_list[:10]],
        top_markets_by_trades=sorted(
            [(m.title, m.total_trades) for m in market_list],
            key=lambda x: x[1], reverse=True
        )[:10],
        category_breakdown=dict(categories.most_common()),
        outcome_preference=dict(outcome_counts.most_common()),
        avg_trades_per_market=len(trades) / max(len(markets), 1),
        market_concentration=hhi,
    )
