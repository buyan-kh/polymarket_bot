"""
Order Management for Polymarket CLOB.
Handles order placement, cancellation, and fill tracking.
Supports both live trading and paper trading modes.
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Callable, Awaitable
from enum import Enum

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    YES = "YES"
    NO = "NO"


class OrderStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Represents a limit order."""
    id: str
    side: OrderSide
    price: float
    size: float
    status: OrderStatus = OrderStatus.PENDING
    filled_qty: float = 0.0
    filled_avg_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    token_id: str = ""
    
    @property
    def remaining(self) -> float:
        return self.size - self.filled_qty
    
    @property
    def is_active(self) -> bool:
        return self.status in {OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED}


@dataclass
class OrderBook:
    """Simplified order book snapshot."""
    bids: List[tuple]  # [(price, size), ...]
    asks: List[tuple]  # [(price, size), ...]
    
    @property
    def best_bid(self) -> Optional[float]:
        return self.bids[0][0] if self.bids else None
    
    @property
    def best_ask(self) -> Optional[float]:
        return self.asks[0][0] if self.asks else None
    
    @property
    def spread(self) -> Optional[float]:
        if self.best_bid and self.best_ask:
            return self.best_ask - self.best_bid
        return None


# Type for fill callback: (side, price, qty) -> None
FillCallback = Callable[[str, float, float], Awaitable[None]]


class BaseOrderManager(ABC):
    """Abstract base class for order management."""
    
    def __init__(self, yes_token_id: str, no_token_id: str):
        self.yes_token_id = yes_token_id
        self.no_token_id = no_token_id
        self.orders: Dict[str, Order] = {}
        self._fill_callback: Optional[FillCallback] = None
    
    def set_fill_callback(self, callback: FillCallback) -> None:
        """Set callback to be invoked when orders are filled."""
        self._fill_callback = callback
    
    def get_token_id(self, side: OrderSide) -> str:
        """Get token ID for a given side."""
        return self.yes_token_id if side == OrderSide.YES else self.no_token_id
    
    @abstractmethod
    async def place_limit_buy(
        self, side: OrderSide, price: float, size: float
    ) -> Order:
        """Place a limit buy order."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID."""
        pass
    
    @abstractmethod
    async def cancel_all_orders(self) -> int:
        """Cancel all open orders. Returns count cancelled."""
        pass
    
    @abstractmethod
    async def market_buy(self, side: OrderSide, size: float) -> Order:
        """Execute a market buy order."""
        pass
    
    @abstractmethod
    async def get_order_book(self, side: OrderSide) -> OrderBook:
        """Get current order book for a side."""
        pass
    
    @abstractmethod
    async def refresh_order_status(self, order_id: str) -> Order:
        """Refresh and return the current status of an order."""
        pass
    
    def get_open_orders(self, side: Optional[OrderSide] = None) -> List[Order]:
        """Get all open orders, optionally filtered by side."""
        orders = [o for o in self.orders.values() if o.is_active]
        if side:
            orders = [o for o in orders if o.side == side]
        return orders
    
    async def _notify_fill(self, side: str, price: float, qty: float) -> None:
        """Notify callback of a fill."""
        if self._fill_callback:
            await self._fill_callback(side, price, qty)


class PaperOrderManager(BaseOrderManager):
    """
    Paper trading order manager for testing.
    Simulates fills based on market price movements.
    """
    
    def __init__(self, yes_token_id: str, no_token_id: str):
        super().__init__(yes_token_id, no_token_id)
        self._simulated_books: Dict[OrderSide, OrderBook] = {
            OrderSide.YES: OrderBook(bids=[(0.50, 100)], asks=[(0.52, 100)]),
            OrderSide.NO: OrderBook(bids=[(0.48, 100)], asks=[(0.50, 100)]),
        }
        logger.info("Paper trading mode initialized")
    
    async def place_limit_buy(
        self, side: OrderSide, price: float, size: float
    ) -> Order:
        """Place a simulated limit order."""
        order = Order(
            id=f"paper_{uuid.uuid4().hex[:8]}",
            side=side,
            price=price,
            size=size,
            status=OrderStatus.OPEN,
            token_id=self.get_token_id(side),
        )
        self.orders[order.id] = order
        logger.info(f"[PAPER] Placed {side.value} bid: {size}@{price:.4f}")
        return order
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a simulated order."""
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            logger.info(f"[PAPER] Cancelled order {order_id}")
            return True
        return False
    
    async def cancel_all_orders(self) -> int:
        """Cancel all simulated orders."""
        count = 0
        for order in self.orders.values():
            if order.is_active:
                order.status = OrderStatus.CANCELLED
                count += 1
        logger.info(f"[PAPER] Cancelled {count} orders")
        return count
    
    async def market_buy(self, side: OrderSide, size: float) -> Order:
        """Simulate a market buy at best ask."""
        book = self._simulated_books[side]
        fill_price = book.best_ask or 0.55
        
        order = Order(
            id=f"paper_mkt_{uuid.uuid4().hex[:8]}",
            side=side,
            price=fill_price,
            size=size,
            status=OrderStatus.FILLED,
            filled_qty=size,
            filled_avg_price=fill_price,
            token_id=self.get_token_id(side),
        )
        self.orders[order.id] = order
        
        logger.info(f"[PAPER] Market buy {side.value}: {size}@{fill_price:.4f}")
        await self._notify_fill(side.value, fill_price, size)
        
        return order
    
    async def get_order_book(self, side: OrderSide) -> OrderBook:
        """Return simulated order book."""
        return self._simulated_books[side]
    
    async def refresh_order_status(self, order_id: str) -> Order:
        """Return current order status."""
        return self.orders.get(order_id)
    
    def update_simulated_book(
        self, side: OrderSide, best_bid: float, best_ask: float
    ) -> None:
        """Update simulated order book for testing."""
        self._simulated_books[side] = OrderBook(
            bids=[(best_bid, 100)],
            asks=[(best_ask, 100)],
        )
    
    async def simulate_fill(self, order_id: str, fill_price: Optional[float] = None) -> bool:
        """Manually trigger a fill for testing."""
        order = self.orders.get(order_id)
        if not order or not order.is_active:
            return False
        
        price = fill_price or order.price
        order.status = OrderStatus.FILLED
        order.filled_qty = order.size
        order.filled_avg_price = price
        
        logger.info(f"[PAPER] Simulated fill: {order.side.value} {order.size}@{price:.4f}")
        await self._notify_fill(order.side.value, price, order.size)
        
        return True


class LiveOrderManager(BaseOrderManager):
    """
    Live order manager using Polymarket CLOB API.
    """
    
    def __init__(
        self,
        clob_client,  # ClobClient instance from py-clob-client
        yes_token_id: str,
        no_token_id: str,
    ):
        super().__init__(yes_token_id, no_token_id)
        self.client = clob_client
        logger.info("Live trading mode initialized")
    
    async def place_limit_buy(
        self, side: OrderSide, price: float, size: float
    ) -> Order:
        """Place a limit buy order via Polymarket API."""
        token_id = self.get_token_id(side)
        
        try:
            # py-clob-client order format
            # Note: The actual API call format may vary - adjust as needed
            response = await asyncio.to_thread(
                self.client.create_and_post_order,
                {
                    "tokenID": token_id,
                    "price": price,
                    "size": size,
                    "side": "BUY",
                }
            )
            
            order = Order(
                id=response.get("orderID", str(uuid.uuid4())),
                side=side,
                price=price,
                size=size,
                status=OrderStatus.OPEN,
                token_id=token_id,
            )
            self.orders[order.id] = order
            
            logger.info(f"Placed {side.value} bid: {size}@{price:.4f} (ID: {order.id[:8]})")
            return order
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order via Polymarket API."""
        try:
            await asyncio.to_thread(self.client.cancel, order_id)
            
            if order_id in self.orders:
                self.orders[order_id].status = OrderStatus.CANCELLED
            
            logger.info(f"Cancelled order {order_id[:8]}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def cancel_all_orders(self) -> int:
        """Cancel all open orders."""
        count = 0
        for order in list(self.orders.values()):
            if order.is_active:
                if await self.cancel_order(order.id):
                    count += 1
        return count
    
    async def market_buy(self, side: OrderSide, size: float) -> Order:
        """Execute market buy by taking best ask."""
        book = await self.get_order_book(side)
        
        if not book.best_ask:
            raise ValueError(f"No asks available for {side.value}")
        
        # Place limit order at ask price for immediate fill
        return await self.place_limit_buy(side, book.best_ask, size)
    
    async def get_order_book(self, side: OrderSide) -> OrderBook:
        """Fetch order book from Polymarket API."""
        token_id = self.get_token_id(side)
        
        try:
            response = await asyncio.to_thread(
                self.client.get_order_book, token_id
            )
            
            bids = [(float(b["price"]), float(b["size"])) for b in response.get("bids", [])]
            asks = [(float(a["price"]), float(a["size"])) for a in response.get("asks", [])]
            
            return OrderBook(bids=bids, asks=asks)
            
        except Exception as e:
            logger.error(f"Failed to fetch order book: {e}")
            return OrderBook(bids=[], asks=[])
    
    async def refresh_order_status(self, order_id: str) -> Order:
        """Refresh order status from API."""
        try:
            response = await asyncio.to_thread(
                self.client.get_order, order_id
            )
            
            if order_id in self.orders:
                order = self.orders[order_id]
                
                # Update status based on response
                status_map = {
                    "open": OrderStatus.OPEN,
                    "filled": OrderStatus.FILLED,
                    "cancelled": OrderStatus.CANCELLED,
                }
                order.status = status_map.get(
                    response.get("status", ""),
                    order.status
                )
                order.filled_qty = float(response.get("filledSize", 0))
                order.filled_avg_price = float(response.get("avgFillPrice", 0))
                
                # Check if newly filled
                if order.status == OrderStatus.FILLED and order.filled_qty > 0:
                    await self._notify_fill(
                        order.side.value,
                        order.filled_avg_price,
                        order.filled_qty
                    )
                
                return order
                
        except Exception as e:
            logger.error(f"Failed to refresh order {order_id}: {e}")
        
        return self.orders.get(order_id)
    
    async def poll_for_fills(self, interval: float = 1.0) -> None:
        """
        Continuously poll for order fills.
        Should be run as a background task.
        """
        while True:
            for order_id in list(self.orders.keys()):
                order = self.orders.get(order_id)
                if order and order.is_active:
                    await self.refresh_order_status(order_id)
            
            await asyncio.sleep(interval)
