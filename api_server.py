"""
FastAPI server wrapping the Polymarket Profile Analyzer.

Run:
    pip install fastapi uvicorn
    uvicorn api_server:app --reload --port 8000
"""

import asyncio
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from profile_analyzer.fetcher import fetch_and_cache, load_trades, fetch_market_resolutions
import aiohttp
from profile_analyzer.patterns import analyze_patterns
from profile_analyzer.report import generate_report
from profile_analyzer.strategy import analyze_strategy

DB_PATH = "profile_history.db"


def _weighted_win_rate(edge_by_price_range: dict) -> float:
    """Weighted average win rate across price ranges, weighted by trade count."""
    total_trades = 0
    weighted_sum = 0.0
    for stats in edge_by_price_range.values():
        t = stats.get("trades", 0)
        wr = stats.get("win_rate", 0)
        if t > 0:
            weighted_sum += wr * t
            total_trades += t
    return round(weighted_sum / total_trades, 1) if total_trades > 0 else 0.0

app = FastAPI(title="Polymarket Trade Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profile_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                wallet TEXT UNIQUE,
                total_trades INTEGER,
                total_volume REAL,
                total_return_pct REAL,
                win_rate REAL,
                sharpe_ratio REAL,
                analyzed_at TEXT,
                notes TEXT,
                pinned INTEGER DEFAULT 0
            )
        """)
        # Add pinned column if missing (migration for existing DBs)
        try:
            conn.execute("ALTER TABLE profile_history ADD COLUMN pinned INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # column already exists
        conn.commit()


@contextmanager
def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _upsert_profile(
    username: str,
    wallet: str,
    total_trades: int,
    total_volume: float,
    total_return_pct: Optional[float],
    win_rate: Optional[float],
    sharpe_ratio: Optional[float],
):
    now = datetime.now(timezone.utc).isoformat()
    with _get_db() as conn:
        conn.execute(
            """
            INSERT INTO profile_history
                (username, wallet, total_trades, total_volume,
                 total_return_pct, win_rate, sharpe_ratio, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(wallet) DO UPDATE SET
                username = excluded.username,
                total_trades = excluded.total_trades,
                total_volume = excluded.total_volume,
                total_return_pct = excluded.total_return_pct,
                win_rate = excluded.win_rate,
                sharpe_ratio = excluded.sharpe_ratio,
                analyzed_at = excluded.analyzed_at
            """,
            (username, wallet, total_trades, total_volume,
             total_return_pct, win_rate, sharpe_ratio, now),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    profile: str
    max_trades: Optional[int] = None


class SaveHistoryRequest(BaseModel):
    username: str
    wallet: str
    total_trades: int
    total_volume: float
    total_return_pct: Optional[float] = None
    win_rate: Optional[float] = None
    sharpe_ratio: Optional[float] = None


class UpdateNotesRequest(BaseModel):
    notes: str


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    _init_db()


# ---------------------------------------------------------------------------
# Analyze endpoint (existing, with auto-save)
# ---------------------------------------------------------------------------

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

    # Fetch market resolution data to correctly compute PnL
    try:
        timeout = aiohttp.ClientTimeout(total=120)
        headers = {"Accept-Encoding": "gzip, deflate"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            settlements = await fetch_market_resolutions(trades, session)
    except Exception:
        settlements = {}  # Graceful degradation — use old method if resolution lookup fails

    analysis = analyze_patterns(
        trades,
        username=profile.username,
        wallet=profile.wallet_address,
        trades_capped=trades_capped,
        settlements=settlements,
    )

    report = generate_report(analysis)

    # Strategy analysis
    strategy_profile = analyze_strategy(trades, analysis)

    # Auto-save to history
    _upsert_profile(
        username=profile.username or "",
        wallet=profile.wallet_address,
        total_trades=analysis.total_trades,
        total_volume=analysis.total_volume_usdc,
        total_return_pct=None,
        win_rate=None,
        sharpe_ratio=None,
    )

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
            "is_resolved": m.is_resolved,
            "outcomes_traded": m.outcomes_traded,
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
                "daily_hours": analysis.timing.daily_hours,
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
            "top_market_win_rate": analysis.top_market_win_rate,
            "resolved_market_count": analysis.resolved_market_count,
            "weighted_win_rate": _weighted_win_rate(strategy_profile.edge_by_price_range),
        },
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
        "strategy": {
            "strategy_type": strategy_profile.strategy_type,
            "confidence": strategy_profile.confidence,
            "avg_entry_price": strategy_profile.avg_entry_price,
            "entry_price_distribution": strategy_profile.entry_price_distribution,
            "prefers_underdogs": strategy_profile.prefers_underdogs,
            "prefers_favorites": strategy_profile.prefers_favorites,
            "avg_time_in_market": strategy_profile.avg_time_in_market,
            "quick_flipper": strategy_profile.quick_flipper,
            "long_holder": strategy_profile.long_holder,
            "edge_by_category": strategy_profile.edge_by_category,
            "edge_by_price_range": strategy_profile.edge_by_price_range,
            "best_category": strategy_profile.best_category,
            "worst_category": strategy_profile.worst_category,
            "market_entry_timing": strategy_profile.market_entry_timing,
            "avg_market_age_at_entry": strategy_profile.avg_market_age_at_entry,
            "scales_in": strategy_profile.scales_in,
            "scales_out": strategy_profile.scales_out,
            "avg_trades_per_market": strategy_profile.avg_trades_per_market,
            "uses_both_sides": strategy_profile.uses_both_sides,
            "profitable_patterns": strategy_profile.profitable_patterns,
            "unprofitable_patterns": strategy_profile.unprofitable_patterns,
            "summary": strategy_profile.summary,
            "key_edges": strategy_profile.key_edges,
            "weaknesses": strategy_profile.weaknesses,
            "replication_tips": strategy_profile.replication_tips,
        },
    }


# ---------------------------------------------------------------------------
# History endpoints
# ---------------------------------------------------------------------------

@app.get("/api/history")
async def get_history():
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM profile_history ORDER BY analyzed_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/history")
async def save_history(req: SaveHistoryRequest):
    _upsert_profile(
        username=req.username,
        wallet=req.wallet,
        total_trades=req.total_trades,
        total_volume=req.total_volume,
        total_return_pct=req.total_return_pct,
        win_rate=req.win_rate,
        sharpe_ratio=req.sharpe_ratio,
    )
    return {"status": "saved"}


@app.delete("/api/history/{profile_id}")
async def delete_history(profile_id: int):
    with _get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM profile_history WHERE id = ?", (profile_id,)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Profile not found")
    return {"status": "deleted"}


@app.patch("/api/history/{profile_id}/notes")
async def update_notes(profile_id: int, req: UpdateNotesRequest):
    with _get_db() as conn:
        cursor = conn.execute(
            "UPDATE profile_history SET notes = ? WHERE id = ?",
            (req.notes, profile_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Profile not found")
    return {"status": "updated"}


@app.patch("/api/history/{profile_id}/pin")
async def toggle_pin(profile_id: int):
    with _get_db() as conn:
        row = conn.execute(
            "SELECT pinned FROM profile_history WHERE id = ?", (profile_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Profile not found")
        new_val = 0 if row["pinned"] else 1
        conn.execute(
            "UPDATE profile_history SET pinned = ? WHERE id = ?",
            (new_val, profile_id),
        )
        conn.commit()
    return {"status": "pinned" if new_val else "unpinned", "pinned": bool(new_val)}


@app.get("/api/pinned")
async def get_pinned():
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM profile_history WHERE pinned = 1 ORDER BY analyzed_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/health")
async def health():
    return {"status": "ok"}
