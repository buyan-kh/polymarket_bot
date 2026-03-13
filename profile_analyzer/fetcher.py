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

    # Fetch profile page to get wallet address
    url = f"https://polymarket.com/@{username}"
    async with session.get(url) as resp:
        if resp.status != 200:
            raise ValueError(f"Could not fetch profile page for '{username}' (HTTP {resp.status})")
        html = await resp.text()

    # Extract wallet address from page source (look for 0x address pattern in JSON data)
    # Polymarket embeds user data in __NEXT_DATA__ script tag
    wallet_match = re.search(r'"proxyWallets":\["(0x[a-fA-F0-9]{40})"', html)
    if not wallet_match:
        # Try alternate patterns
        wallet_match = re.search(r'"address":"(0x[a-fA-F0-9]{40})"', html)
    if not wallet_match:
        # Try the data API directly
        wallet_match = re.search(r'"walletAddress":"(0x[a-fA-F0-9]{40})"', html)
    if not wallet_match:
        # Search for any 0x address near the username context
        wallet_match = re.search(r'(0x[a-fA-F0-9]{40})', html)
    if not wallet_match:
        raise ValueError(
            f"Could not find wallet address for '{username}'. "
            "Try providing the wallet address directly (0x...)."
        )

    wallet = wallet_match.group(1).lower()
    return UserProfile(username=username, wallet_address=wallet)


async def fetch_all_trades(
    wallet_address: str,
    session: aiohttp.ClientSession,
    limit: int = 1000,
    max_trades: Optional[int] = None,
    progress_callback=None,
) -> list[dict]:
    """
    Fetch all trades for a wallet address from the Polymarket Data API.
    Uses offset-based pagination.
    """
    all_trades = []
    offset = 0
    batch_size = min(limit, 10000)

    while True:
        params = {
            "user": wallet_address,
            "limit": batch_size,
            "offset": offset,
            "takerOnly": "false",
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

    return all_trades


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


async def fetch_and_cache(
    profile_input: str,
    max_trades: Optional[int] = None,
    progress_callback=None,
) -> tuple[UserProfile, list[Trade], Path]:
    """
    Full pipeline: resolve profile -> fetch trades -> parse -> cache.
    Returns (profile, trades, cache_filepath).
    """
    timeout = aiohttp.ClientTimeout(total=300)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        if progress_callback:
            progress_callback("Resolving profile...")

        profile = await resolve_profile(profile_input, session)

        if progress_callback:
            progress_callback(f"Found wallet: {profile.wallet_address}")
            progress_callback("Fetching trades...")

        raw_trades = await fetch_all_trades(
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

        return profile, trades, cache_path
