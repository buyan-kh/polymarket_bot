"""
CLI entry point for the Polymarket Profile Trade Analyzer.

Usage:
    # Full analysis from a profile URL
    python -m profile_analyzer.cli https://polymarket.com/@Sharky6999

    # From username
    python -m profile_analyzer.cli @Sharky6999

    # From wallet address
    python -m profile_analyzer.cli 0x751a2b86cab503496efd325c8344e10159349ea1

    # Load from cached data
    python -m profile_analyzer.cli --load trade_data/Sharky6999_20260313_120000.json

    # With backtest
    python -m profile_analyzer.cli @Sharky6999 --backtest

    # Limit trades fetched
    python -m profile_analyzer.cli @Sharky6999 --max-trades 5000

    # Export report to file
    python -m profile_analyzer.cli @Sharky6999 --output report.txt
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import aiohttp

from .fetcher import fetch_and_cache, load_trades, fetch_market_resolutions, Trade
from .patterns import analyze_patterns
from .backtest import run_backtest, compare_to_baseline
from .report import generate_report, format_report


def print_progress(msg: str):
    """Print progress messages to stderr."""
    print(f"  >> {msg}", file=sys.stderr)


def run_analysis(
    trades: list[Trade],
    username: str = "",
    wallet: str = "",
    run_backtest_flag: bool = False,
    initial_capital: float = 10000.0,
    settlements: Optional[dict] = None,
) -> str:
    """Run full analysis pipeline and return formatted report."""
    print_progress(f"Analyzing {len(trades)} trades...")

    settlements = settlements or {}

    # Pattern analysis
    analysis = analyze_patterns(trades, username=username, wallet=wallet, settlements=settlements)

    # Backtest (if requested)
    backtest_result = None
    if run_backtest_flag:
        print_progress("Running backtest...")
        backtest_result = run_backtest(trades, initial_capital=initial_capital, settlement_prices=settlements)
        baseline = compare_to_baseline(trades, backtest_result)
        print_progress(
            f"Backtest complete: {backtest_result.total_return_pct:.1f}% return, "
            f"Sharpe {backtest_result.sharpe_ratio:.2f}"
        )

    # Generate report
    print_progress("Generating report...")
    report = generate_report(analysis, backtest=backtest_result)
    formatted = format_report(report)

    # Also print top markets
    formatted += "\n"
    formatted += "-" * 40 + "\n"
    formatted += "  TOP 10 MARKETS BY VOLUME\n"
    formatted += "-" * 40 + "\n"
    for i, (title, vol) in enumerate(analysis.top_markets_by_volume[:10], 1):
        display_title = (title[:50] + "...") if len(title) > 50 else title
        formatted += f"  {i:>2}. ${vol:>12,.0f}  {display_title}\n"

    formatted += "\n"
    formatted += "-" * 40 + "\n"
    formatted += "  TOP 10 MARKETS BY TRADE COUNT\n"
    formatted += "-" * 40 + "\n"
    for i, (title, count) in enumerate(analysis.top_markets_by_trades[:10], 1):
        display_title = (title[:50] + "...") if len(title) > 50 else title
        formatted += f"  {i:>2}. {count:>6,} trades  {display_title}\n"

    formatted += "\n"
    formatted += "-" * 40 + "\n"
    formatted += "  TIMING PATTERNS\n"
    formatted += "-" * 40 + "\n"
    formatted += "  Most active hours (UTC):\n"
    for hour, count in analysis.timing.most_active_hours:
        bar = "#" * min(count // max(analysis.total_trades // 200, 1), 40)
        formatted += f"    {hour:02d}:00  {count:>6,}  {bar}\n"
    formatted += "\n  Most active days:\n"
    for day, count in analysis.timing.most_active_days:
        bar = "#" * min(count // max(analysis.total_trades // 200, 1), 40)
        formatted += f"    {day:<10} {count:>6,}  {bar}\n"

    formatted += "\n"
    formatted += "-" * 40 + "\n"
    formatted += "  CATEGORY BREAKDOWN\n"
    formatted += "-" * 40 + "\n"
    for cat, count in sorted(analysis.category_breakdown.items(), key=lambda x: -x[1]):
        pct = count / max(analysis.total_trades, 1) * 100
        bar = "#" * int(pct / 2)
        formatted += f"  {cat:<20} {count:>6,} ({pct:>5.1f}%)  {bar}\n"

    formatted += "\n"
    formatted += "-" * 40 + "\n"
    formatted += "  PRICE DISTRIBUTION (buys)\n"
    formatted += "-" * 40 + "\n"
    for rng, count in analysis.pricing.favorite_price_ranges:
        pct = count / max(analysis.total_trades, 1) * 100
        bar = "#" * int(pct / 2)
        formatted += f"  {rng:<15} {count:>6,} ({pct:>5.1f}%)  {bar}\n"

    formatted += "\n"
    formatted += "-" * 40 + "\n"
    formatted += "  TRADE SIZE DISTRIBUTION\n"
    formatted += "-" * 40 + "\n"
    for bucket, count in analysis.sizing.size_buckets.items():
        pct = count / max(analysis.total_trades, 1) * 100
        bar = "#" * int(pct / 2)
        formatted += f"  {bucket:<12} {count:>6,} ({pct:>5.1f}%)  {bar}\n"

    formatted += "\n" + "=" * 70 + "\n"

    return formatted


async def async_main(args):
    """Async main entry point."""
    trades = []
    username = ""
    wallet = ""

    if args.load:
        # Load from cached file
        print_progress(f"Loading trades from {args.load}...")
        trades = load_trades(args.load)
        # Try to extract username from filename
        filename = Path(args.load).stem
        username = filename.split("_")[0] if "_" in filename else ""
    else:
        # Fetch from Polymarket
        profile, trades, cache_path, trades_capped = await fetch_and_cache(
            args.profile,
            max_trades=args.max_trades,
            progress_callback=print_progress,
        )
        username = profile.username
        wallet = profile.wallet_address
        print_progress(f"Cached {len(trades)} trades to {cache_path}")

    if not trades:
        print("No trades found for this profile.", file=sys.stderr)
        sys.exit(1)

    # Fetch market resolution data for correct PnL
    condition_ids = list(set(t.condition_id for t in trades if t.condition_id))
    settlements = {}
    try:
        print_progress("Fetching market resolution data...")
        timeout = aiohttp.ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            settlements = await fetch_market_resolutions(condition_ids, session, progress_callback=print_progress)
    except Exception as e:
        print_progress(f"Warning: Could not fetch resolutions ({e}), PnL may be inaccurate")

    # Run analysis
    output = run_analysis(
        trades,
        username=username,
        wallet=wallet,
        run_backtest_flag=args.backtest,
        initial_capital=args.capital,
        settlements=settlements,
    )

    # Output
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print_progress(f"Report saved to {args.output}")
    else:
        print(output)


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Profile Trade Analyzer",
        epilog="Examples:\n"
               "  python -m profile_analyzer.cli https://polymarket.com/@Sharky6999\n"
               "  python -m profile_analyzer.cli @Sharky6999 --backtest\n"
               "  python -m profile_analyzer.cli --load trade_data/Sharky6999.json\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "profile",
        nargs="?",
        help="Polymarket profile URL, @username, or 0x wallet address",
    )
    parser.add_argument(
        "--load",
        help="Load trades from a cached JSON file instead of fetching",
    )
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run backtest analysis on the trades",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=10000.0,
        help="Initial capital for backtest (default: $10,000)",
    )
    parser.add_argument(
        "--max-trades",
        type=int,
        default=None,
        help="Maximum number of trades to fetch",
    )
    parser.add_argument(
        "--output", "-o",
        help="Save report to file instead of printing",
    )

    args = parser.parse_args()

    if not args.profile and not args.load:
        parser.error("Either provide a profile or use --load to load cached data")

    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
