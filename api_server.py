"""
FastAPI server wrapping the Polymarket Profile Analyzer.

Run:
    pip install fastapi uvicorn
    uvicorn api_server:app --reload --port 8000
"""

import asyncio
from dataclasses import asdict
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from profile_analyzer.fetcher import fetch_and_cache, load_trades
from profile_analyzer.patterns import analyze_patterns
from profile_analyzer.backtest import run_backtest, compare_to_baseline
from profile_analyzer.report import generate_report

app = FastAPI(title="Polymarket Trade Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    profile: str
    backtest: bool = True
    max_trades: Optional[int] = None
    capital: float = 10000.0


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    try:
        profile, trades, cache_path, trades_capped = await fetch_and_cache(
            req.profile,
            max_trades=req.max_trades,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not trades:
        raise HTTPException(status_code=404, detail="No trades found for this profile")

    analysis = analyze_patterns(
        trades,
        username=profile.username,
        wallet=profile.wallet_address,
        trades_capped=trades_capped,
    )

    backtest_result = None
    baseline = None
    if req.backtest:
        backtest_result = run_backtest(trades, initial_capital=req.capital)
        baseline = compare_to_baseline(trades, backtest_result)

    report = generate_report(analysis, backtest=backtest_result)

    # Serialize market summaries (top 20)
    market_summaries = []
    for m in analysis.market_summaries[:20]:
        market_summaries.append({
            "title": m.title,
            "slug": m.slug,
            "total_trades": m.total_trades,
            "buy_count": m.buy_count,
            "sell_count": m.sell_count,
            "total_volume": m.total_volume,
            "avg_buy_price": m.avg_buy_price,
            "avg_sell_price": m.avg_sell_price,
            "estimated_pnl": m.estimated_pnl,
            "outcomes_traded": m.outcomes_traded,
        })

    # Serialize backtest snapshots
    snapshots = []
    if backtest_result:
        for s in backtest_result.portfolio_snapshots:
            snapshots.append({
                "timestamp": s.timestamp,
                "cash": s.cash,
                "positions_value": s.positions_value,
                "total_value": s.total_value,
                "trade_count": s.trade_count,
            })

    return {
        "profile": {
            "username": profile.username,
            "wallet": profile.wallet_address,
        },
        "analysis": {
            "total_trades": analysis.total_trades,
            "trades_capped": trades_capped,
            "total_volume_usdc": analysis.total_volume_usdc,
            "unique_markets": analysis.unique_markets,
            "date_range": list(analysis.date_range),
            "buy_sell_ratio": analysis.buy_sell_ratio,
            "market_concentration": analysis.market_concentration,
            "avg_trades_per_market": analysis.avg_trades_per_market,
            "timing": {
                "most_active_hours": analysis.timing.most_active_hours,
                "most_active_days": analysis.timing.most_active_days,
                "avg_trades_per_day": analysis.timing.avg_trades_per_day,
                "busiest_date": analysis.timing.busiest_date,
                "busiest_date_count": analysis.timing.busiest_date_count,
                "trading_streak_days": analysis.timing.trading_streak_days,
            },
            "sizing": {
                "avg_trade_size_usdc": analysis.sizing.avg_trade_size_usdc,
                "median_trade_size_usdc": analysis.sizing.median_trade_size_usdc,
                "max_trade_size_usdc": analysis.sizing.max_trade_size_usdc,
                "min_trade_size_usdc": analysis.sizing.min_trade_size_usdc,
                "stddev_trade_size": analysis.sizing.stddev_trade_size,
                "size_buckets": analysis.sizing.size_buckets,
            },
            "pricing": {
                "avg_buy_price": analysis.pricing.avg_buy_price,
                "median_buy_price": analysis.pricing.median_buy_price,
                "pct_buying_below_50c": analysis.pricing.pct_buying_below_50c,
                "pct_buying_above_50c": analysis.pricing.pct_buying_above_50c,
                "avg_sell_price": analysis.pricing.avg_sell_price,
                "favorite_price_ranges": analysis.pricing.favorite_price_ranges,
            },
            "category_breakdown": analysis.category_breakdown,
            "outcome_preference": analysis.outcome_preference,
            "top_markets_by_volume": analysis.top_markets_by_volume,
            "top_markets_by_trades": analysis.top_markets_by_trades,
            "market_summaries": market_summaries,
        },
        "backtest": {
            "initial_capital": backtest_result.initial_capital,
            "final_value": backtest_result.final_value,
            "total_return_pct": backtest_result.total_return_pct,
            "total_pnl": backtest_result.total_pnl,
            "max_drawdown_pct": backtest_result.max_drawdown_pct,
            "peak_value": backtest_result.peak_value,
            "num_trades": backtest_result.num_trades,
            "num_winning_trades": backtest_result.num_winning_trades,
            "num_losing_trades": backtest_result.num_losing_trades,
            "win_rate": backtest_result.win_rate,
            "avg_win": backtest_result.avg_win,
            "avg_loss": backtest_result.avg_loss,
            "profit_factor": backtest_result.profit_factor,
            "sharpe_ratio": backtest_result.sharpe_ratio,
            "sortino_ratio": backtest_result.sortino_ratio,
            "avg_trade_pnl": backtest_result.avg_trade_pnl,
            "largest_win": backtest_result.largest_win,
            "largest_loss": backtest_result.largest_loss,
            "snapshots": snapshots,
            "daily_returns": backtest_result.daily_returns,
        } if backtest_result else None,
        "baseline": baseline,
        "report": {
            "summary": report.summary,
            "pros": [
                {"category": p.category, "observation": p.observation, "detail": p.detail, "severity": p.severity}
                for p in report.pros
            ],
            "cons": [
                {"category": c.category, "observation": c.observation, "detail": c.detail, "severity": c.severity}
                for c in report.cons
            ],
            "key_stats": report.key_stats,
            "recommendations": report.recommendations,
        },
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}
