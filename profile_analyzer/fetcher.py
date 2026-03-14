"""
Trade fetcher - downloads all trades for a Polymarket user profile.

Supports:
- Resolving profile URL or username to wallet address
- Paginated fetching of all trades from the Data API
- Caching fetched data to JSON for reuse
"""

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import aiohttp
import asyncio


DATA_API_BASE = "https://data-api.polymarket.com"
GAMMA_API_BASE = "https://gamma-api.polymarket.com"
PROFILE_API_BASE = "https://polymarket.com/api/profile"
CACHE_DIR = Path(__file__).parent.parent / "trade_data"


@dataclass
class Trade:
    """A single trade record."""
    timestamp: str
    side: str  # BUY or SELL
    price: float
    size: float
    usdc_size: float
    condition_id: str
    asset: str  # token ID
    outcome: str  # e.g. "Yes", "No"
    title: str  # market title
    slug: str
    event_slug: str
    transaction_hash: str
    proxy_wallet: str


@dataclass
class UserProfile:
    """Resolved user profile info."""
    username: str
    wallet_address: str
    profile_id: Optional[int] = None
    total_volume: Optional[float] = None
    pnl: Optional[float] = None
    markets_traded: Optional[int] = None


async def resolve_profile(profile_input: str, session: aiohttp.ClientSession) -> UserProfile:
    """
    Resolve a Polymarket profile URL or username to wallet address.

    Accepts:
      - https://polymarket.com/@Username
      - @Username
      - Username
      - 0x... (direct wallet address)
    """
    profile_input = profile_input.strip()

    # Direct wallet address
    if re.match(r"^0x[a-fA-F0-9]{40}$", profile_input):
        return UserProfile(username="", wallet_address=profile_input.lower())

    # Extract username from URL or @-prefix
    if "polymarket.com/@" in profile_input:
        parsed = urlparse(profile_input)
        username = parsed.path.split("@")[-1].strip("/")
    elif profile_input.startswith("@"):
        username = profile_input[1:]
    else:
        username = profile_input

    # Fetch profile page and extract wallet from __NEXT_DATA__ JSON
    url = f"https://polymarket.com/@{username}"
    async with session.get(url) as resp:
        if resp.status != 200:
            raise ValueError(f"Could not fetch profile page for '{username}' (HTTP {resp.status})")
        html = await resp.text()

    # Parse __NEXT_DATA__ script tag which contains the user's profile data
    next_data_match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
    )
    if next_data_match:
        try:
            next_data = json.loads(next_data_match.group(1))
            # Walk through dehydrated queries to find the profile query
            queries = (
                next_data.get("props", {})
                .get("pageProps", {})
                .get("dehydratedState", {})
                .get("queries", [])
            )
            for query in queries:
                data = query.get("state", {}).get("data", {})
                if isinstance(data, dict):
                    # Profile query returns a dict with wallet fields
                    for key in ("proxyWallet", "primaryAddress", "baseAddress", "user"):
                        addr = data.get(key, "")
                        if re.match(r"^0x[a-fA-F0-9]{40}$", addr):
                            return UserProfile(
                                username=username, wallet_address=addr.lower()
                            )
        except (json.JSONDecodeError, TypeError):
            pass

    # Fallback: search for known wallet-address keys in the raw HTML
    for pattern in [
        r'"proxyWallet":"(0x[a-fA-F0-9]{40})"',
        r'"primaryAddress":"(0x[a-fA-F0-9]{40})"',
        r'"user":"(0x[a-fA-F0-9]{40})"',
    ]:
        wallet_match = re.search(pattern, html)
        if wallet_match:
            return UserProfile(
                username=username, wallet_address=wallet_match.group(1).lower()
            )

    raise ValueError(
        f"Could not find wallet address for '{username}'. "
        "Try providing the wallet address directly (0x...)."
    )


async def fetch_all_trades(
    wallet_address: str,
    session: aiohttp.ClientSession,
    limit: int = 1000,
    max_trades: Optional[int] = None,
    progress_callback=None,
) -> tuple[list[dict], bool]:
    """
    Fetch all trades for a wallet address from the Polymarket Data API.
    Uses offset-based pagination.

    Returns (trades, trades_capped) where trades_capped is True if the API
    pagination limit was hit and there may be more trades.
    """
    all_trades = []
    offset = 0
    batch_size = min(limit, 10000)
    trades_capped = False

    while True:
        params = {
            "user": wallet_address,
            "limit": batch_size,
            "offset": offset,
            "takerOnly": "true",
        }

        retry_count = 0
        while retry_count < 4:
            try:
                async with session.get(f"{DATA_API_BASE}/trades", params=params) as resp:
                    if resp.status == 429:
                        wait = 2 ** (retry_count + 1)
                        if progress_callback:
                            progress_callback(f"Rate limited, waiting {wait}s...")
                        await asyncio.sleep(wait)
                        retry_count += 1
                        continue
                    if resp.status == 400:
                        # API returns 400 at high offsets; treat as end of data
                        if progress_callback:
                            progress_callback(f"Reached API pagination limit at offset {offset}")
                        trades_capped = True
                        return all_trades, trades_capped
                    if resp.status != 200:
                        raise Exception(f"API error: HTTP {resp.status}")
                    data = await resp.json()
                    break
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                retry_count += 1
                if retry_count >= 4:
                    raise Exception(f"Failed after 4 retries: {e}")
                await asyncio.sleep(2 ** retry_count)

        if not data:
            break

        all_trades.extend(data)

        if progress_callback:
            progress_callback(f"Fetched {len(all_trades)} trades...")

        if len(data) < batch_size:
            break  # Last page

        if max_trades and len(all_trades) >= max_trades:
            all_trades = all_trades[:max_trades]
            break

        offset += batch_size

        # Be polite to the API
        await asyncio.sleep(0.3)

    return all_trades, trades_capped


def parse_trades(raw_trades: list[dict]) -> list[Trade]:
    """Parse raw API trade dicts into Trade objects."""
    trades = []
    for t in raw_trades:
        try:
            trades.append(Trade(
                timestamp=t.get("timestamp", t.get("matchTime", "")),
                side=t.get("side", "UNKNOWN"),
                price=float(t.get("price", 0)),
                size=float(t.get("size", 0)),
                usdc_size=float(t.get("usdcSize", 0) or t.get("size", 0) * t.get("price", 0)),
                condition_id=t.get("conditionId", t.get("market", "")),
                asset=t.get("asset", t.get("assetId", "")),
                outcome=t.get("outcome", ""),
                title=t.get("title", t.get("question", "")),
                slug=t.get("slug", ""),
                event_slug=t.get("eventSlug", ""),
                transaction_hash=t.get("transactionHash", t.get("txHash", "")),
                proxy_wallet=t.get("proxyWallet", ""),
            ))
        except (ValueError, TypeError):
            continue  # Skip malformed trades
    return trades


def save_trades(trades: list[Trade], username: str) -> Path:
    """Save trades to a JSON cache file."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{username or 'unknown'}_{timestamp}.json"
    filepath = CACHE_DIR / filename
    with open(filepath, "w") as f:
        json.dump([asdict(t) for t in trades], f, indent=2)
    return filepath


def load_trades(filepath: str | Path) -> list[Trade]:
    """Load trades from a cached JSON file."""
    with open(filepath) as f:
        data = json.load(f)
    return [Trade(**t) for t in data]


async def fetch_market_resolutions(
    trades: list[Trade],
    session: aiohttp.ClientSession,
    progress_callback=None,
) -> dict[str, dict[str, float]]:
    """
    Look up settlement prices for markets via the Gamma API.

    Returns a dict of:
        {condition_id: {outcome_name: settlement_price, ...}}

    For example, a resolved Over/Under market where Over won:
        {"0xabc...": {"Over": 1.0, "Under": 0.0}}

    Only resolved (closed) markets are included.
    Uses slug-based lookup since condition_id queries are unreliable.
    """
    # Build slug -> condition_id mapping from trades
    slug_to_cid: dict[str, str] = {}
    for t in trades:
        if t.slug and t.condition_id:
            slug_to_cid[t.slug] = t.condition_id

    unique_slugs = list(slug_to_cid.keys())
    settlements: dict[str, dict[str, float]] = {}

    if progress_callback:
        progress_callback(f"Looking up resolution status for {len(unique_slugs)} markets...")

    batch_size = 20
    for i in range(0, len(unique_slugs), batch_size):
        batch = unique_slugs[i:i + batch_size]
        tasks = [_fetch_single_resolution(slug, session) for slug in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for slug, result in zip(batch, results):
            if isinstance(result, dict) and result:
                cid = slug_to_cid[slug]
                settlements[cid] = result

        if progress_callback and (i + batch_size) % 100 == 0:
            progress_callback(f"Checked {min(i + batch_size, len(unique_slugs))}/{len(unique_slugs)} markets...")

        # Rate limit
        await asyncio.sleep(0.15)

    if progress_callback:
        progress_callback(f"Found {len(settlements)} resolved markets out of {len(unique_slugs)} total")

    return settlements


async def _fetch_single_resolution(
    slug: str,
    session: aiohttp.ClientSession,
) -> Optional[dict[str, float]]:
    """
    Fetch resolution for a single market by slug from Gamma API.

    Returns {outcome_name: settlement_price} or None if not resolved.
    """
    try:
        url = f"{GAMMA_API_BASE}/markets"
        params = {"slug": slug}
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

        if not data:
            return None

        market = data[0] if isinstance(data, list) else data

        # Must be closed
        if not market.get("closed", False):
            return None

        # Get outcomes list and their settlement prices
        # outcomes: ["Over", "Under"] or ["Yes", "No"]
        # outcomePrices: ["1", "0"] — maps 1:1 with outcomes
        outcomes = market.get("outcomes")
        outcome_prices_raw = market.get("outcomePrices")

        if not outcomes or not outcome_prices_raw:
            return None

        # Parse outcomes (could be JSON string or list)
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        if isinstance(outcome_prices_raw, str):
            outcome_prices_raw = json.loads(outcome_prices_raw)

        if not isinstance(outcomes, list) or not isinstance(outcome_prices_raw, list):
            return None
        if len(outcomes) != len(outcome_prices_raw):
            return None

        # Parse prices
        try:
            prices = [float(p) for p in outcome_prices_raw]
        except (ValueError, TypeError):
            return None

        # Only return if at least one outcome settled at 0 or 1
        # (otherwise market might still be active with live prices)
        if not any(p >= 0.95 or p <= 0.05 for p in prices):
            return None

        return {outcome: price for outcome, price in zip(outcomes, prices)}

    except Exception:
        return None


async def fetch_and_cache(
    profile_input: str,
    max_trades: Optional[int] = None,
    progress_callback=None,
) -> tuple[UserProfile, list[Trade], Path, bool]:
    """
    Full pipeline: resolve profile -> fetch trades -> parse -> cache.
    Returns (profile, trades, cache_filepath, trades_capped).
    """
    timeout = aiohttp.ClientTimeout(total=300)
    headers = {"Accept-Encoding": "gzip, deflate"}
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        if progress_callback:
            progress_callback("Resolving profile...")

        profile = await resolve_profile(profile_input, session)

        if progress_callback:
            progress_callback(f"Found wallet: {profile.wallet_address}")
            progress_callback("Fetching trades...")

        raw_trades, trades_capped = await fetch_all_trades(
            profile.wallet_address,
            session,
            max_trades=max_trades,
            progress_callback=progress_callback,
        )

        if progress_callback:
            progress_callback(f"Parsing {len(raw_trades)} trades...")

        trades = parse_trades(raw_trades)
        cache_path = save_trades(trades, profile.username)

        if progress_callback:
            progress_callback(f"Saved to {cache_path}")

        return profile, trades, cache_path, trades_capped
