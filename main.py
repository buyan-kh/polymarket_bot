"""
Main entry point for the Legged Arb Market Maker Bot.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta

from config import load_config, MarketConfig
from bot import LeggedArbBot
from order_manager import PaperOrderManager, LiveOrderManager
from market_data import MarketDataManager
from market_discovery import MarketDiscovery, discover_markets_cli

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Reduce noise from external libraries
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)


async def auto_discover_market(asset: str = "BTC") -> MarketConfig:
    """
    Automatically discover the next available market.
    
    Args:
        asset: "BTC" or "ETH"
        
    Returns:
        MarketConfig with discovered market details
    """
    discovery = MarketDiscovery()
    
    try:
        logger.info(f"🔍 Auto-discovering next {asset} 15-minute market...")
        
        market = await discovery.find_next_market(asset, min_time_remaining=120)
        
        if not market:
            raise ValueError(f"No active {asset} 15-minute markets found")
        
        logger.info(f"✅ Found market: {market.slug}")
        logger.info(f"   Window: {market.window_start_time}-{market.window_end_time}")
        logger.info(f"   Time left: {market.time_to_expiry/60:.1f} min")
        logger.info(f"   Condition: {market.condition_id[:30]}...")
        
        return MarketConfig(
            condition_id=market.condition_id,
            yes_token_id=market.yes_token_id,
            no_token_id=market.no_token_id,
            strike_price=0.0,  # Up/down markets track direction, not absolute price
        ), market.expiry_timestamp
        
    finally:
        await discovery.close()


async def run_with_discovery(
    asset: str = "BTC",
    paper_mode: bool = True,
    continuous: bool = False,
):
    """
    Run bot with automatic market discovery.
    
    Args:
        asset: "BTC" or "ETH"
        paper_mode: If True, use paper trading
        continuous: If True, automatically find next market when current expires
    """
    config = load_config()
    config.paper_mode = paper_mode
    
    while True:
        try:
            # Discover market
            market_config, expiry_ts = await auto_discover_market(asset)
            config.market = market_config
            
            # Initialize order manager
            if config.paper_mode:
                order_manager = PaperOrderManager(
                    yes_token_id=config.market.yes_token_id,
                    no_token_id=config.market.no_token_id,
                )
            else:
                from py_clob_client.client import ClobClient
                
                clob_client = ClobClient(
                    host=config.clob_host,
                    chain_id=config.chain_id,
                    key=config.private_key,
                )
                clob_client.set_api_creds(clob_client.derive_api_key())
                
                order_manager = LiveOrderManager(
                    clob_client=clob_client,
                    yes_token_id=config.market.yes_token_id,
                    no_token_id=config.market.no_token_id,
                )
            
            # Initialize market data
            market_data = MarketDataManager(
                use_live=not config.paper_mode,
                symbols=["btcusdt" if asset == "BTC" else "ethusdt"],
            )
            
            # Create bot
            bot = LeggedArbBot(
                config=config,
                order_manager=order_manager,
                market_data=market_data,
            )
            bot.set_expiry(expiry_ts)
            
            # Calculate how long to run
            time_to_expiry = expiry_ts - datetime.now().timestamp()
            run_duration = max(10, time_to_expiry - 60)  # Stop 1 min before expiry
            
            logger.info(f"⏱️  Running for {run_duration/60:.1f} minutes until near expiry")
            
            # Run bot with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        market_data.start(),
                        bot.run(tick_interval=1.0),
                    ),
                    timeout=run_duration,
                )
            except asyncio.TimeoutError:
                logger.info("⏰ Market cycle complete, cleaning up...")
                await order_manager.cancel_all_orders()
            
            await market_data.stop()
            
            if not continuous:
                break
            
            # Wait for next cycle
            logger.info("⏳ Waiting 30 seconds before discovering next market...")
            await asyncio.sleep(30)
            
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            if not continuous:
                raise
            logger.info("Retrying in 30 seconds...")
            await asyncio.sleep(30)


async def main(paper_mode: bool = None, asset: str = None, auto_discover: bool = False):
    """
    Main application entry point.
    
    Args:
        paper_mode: Override config paper mode
        asset: Asset to trade ("BTC" or "ETH")
        auto_discover: If True, automatically discover markets
    """
    if auto_discover and asset:
        await run_with_discovery(asset=asset, paper_mode=paper_mode or True)
        return
    
    # Original manual config mode
    config = load_config()
    
    if paper_mode is not None:
        config.paper_mode = paper_mode
    
    # Validate configuration
    if not config.paper_mode:
        if not config.private_key:
            logger.error("PRIVATE_KEY required for live trading")
            sys.exit(1)
        if not config.market.condition_id:
            logger.error("CONDITION_ID required - use --discover to auto-find markets")
            sys.exit(1)
    
    # Initialize order manager
    if config.paper_mode:
        order_manager = PaperOrderManager(
            yes_token_id=config.market.yes_token_id or "YES_TOKEN",
            no_token_id=config.market.no_token_id or "NO_TOKEN",
        )
    else:
        from py_clob_client.client import ClobClient
        
        clob_client = ClobClient(
            host=config.clob_host,
            chain_id=config.chain_id,
            key=config.private_key,
        )
        clob_client.set_api_creds(clob_client.derive_api_key())
        
        order_manager = LiveOrderManager(
            clob_client=clob_client,
            yes_token_id=config.market.yes_token_id,
            no_token_id=config.market.no_token_id,
        )
    
    # Initialize market data
    market_data = MarketDataManager(
        use_live=not config.paper_mode,
        symbols=["btcusdt"],
    )
    
    # Create bot
    bot = LeggedArbBot(
        config=config,
        order_manager=order_manager,
        market_data=market_data,
    )
    
    # Set expiry (for paper trading, use 15 minutes from now)
    if config.paper_mode:
        expiry = datetime.now() + timedelta(minutes=15)
        bot.set_expiry(expiry.timestamp())
    
    # Run
    try:
        await asyncio.gather(
            market_data.start(),
            bot.run(tick_interval=1.0),
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await market_data.stop()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Legged Arb Market Maker Bot for Polymarket 15-min cycles"
    )
    parser.add_argument(
        "--paper",
        action="store_true",
        help="Run in paper trading mode (no real orders)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run in live trading mode (real orders)",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Auto-discover available 15-minute markets",
    )
    parser.add_argument(
        "--asset",
        choices=["BTC", "ETH"],
        default="BTC",
        help="Asset to trade (default: BTC)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_markets",
        help="List all available 15-minute markets and exit",
    )
    
    args = parser.parse_args()
    
    if args.live and args.paper:
        print("Error: Cannot specify both --live and --paper")
        sys.exit(1)
    
    # List markets mode
    if args.list_markets:
        asyncio.run(discover_markets_cli())
        sys.exit(0)
    
    # Determine paper mode
    paper_mode = not args.live  # Default to paper unless --live
    
    # Run with auto-discovery or manual config
    asyncio.run(main(
        paper_mode=paper_mode,
        asset=args.asset,
        auto_discover=args.discover,
    ))

