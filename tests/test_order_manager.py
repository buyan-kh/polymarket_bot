"""
Tests for the order manager.
"""

import pytest
import asyncio
from order_manager import (
    PaperOrderManager,
    OrderSide,
    OrderStatus,
    Order,
    OrderBook,
)


@pytest.fixture
def paper_manager():
    """Create a paper order manager for testing."""
    return PaperOrderManager(
        yes_token_id="YES_TOKEN_123",
        no_token_id="NO_TOKEN_456",
    )


class TestOrderBook:
    """Tests for OrderBook data structure."""
    
    def test_best_bid_ask(self):
        """Best bid/ask should return first level."""
        book = OrderBook(
            bids=[(0.48, 100), (0.47, 200)],
            asks=[(0.52, 100), (0.53, 200)],
        )
        assert book.best_bid == 0.48
        assert book.best_ask == 0.52
    
    def test_spread(self):
        """Spread should be ask - bid."""
        book = OrderBook(
            bids=[(0.48, 100)],
            asks=[(0.52, 100)],
        )
        assert abs(book.spread - 0.04) < 0.0001
    
    def test_empty_book(self):
        """Empty book should return None for best levels."""
        book = OrderBook(bids=[], asks=[])
        assert book.best_bid is None
        assert book.best_ask is None
        assert book.spread is None


class TestPaperOrderManager:
    """Tests for paper trading order manager."""
    
    @pytest.mark.asyncio
    async def test_place_limit_buy(self, paper_manager):
        """Should create and track order."""
        order = await paper_manager.place_limit_buy(
            side=OrderSide.YES,
            price=0.48,
            size=10,
        )
        
        assert order.id.startswith("paper_")
        assert order.side == OrderSide.YES
        assert order.price == 0.48
        assert order.size == 10
        assert order.status == OrderStatus.OPEN
        assert order.id in paper_manager.orders
    
    @pytest.mark.asyncio
    async def test_cancel_order(self, paper_manager):
        """Should cancel existing order."""
        order = await paper_manager.place_limit_buy(OrderSide.YES, 0.48, 10)
        
        result = await paper_manager.cancel_order(order.id)
        
        assert result is True
        assert paper_manager.orders[order.id].status == OrderStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_order(self, paper_manager):
        """Should return False for nonexistent order."""
        result = await paper_manager.cancel_order("fake_id")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cancel_all_orders(self, paper_manager):
        """Should cancel all open orders."""
        await paper_manager.place_limit_buy(OrderSide.YES, 0.48, 10)
        await paper_manager.place_limit_buy(OrderSide.NO, 0.50, 10)
        
        count = await paper_manager.cancel_all_orders()
        
        assert count == 2
        for order in paper_manager.orders.values():
            assert order.status == OrderStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_market_buy(self, paper_manager):
        """Should execute market buy at best ask."""
        fills = []
        
        async def on_fill(side, price, qty):
            fills.append((side, price, qty))
        
        paper_manager.set_fill_callback(on_fill)
        
        order = await paper_manager.market_buy(OrderSide.YES, 10)
        
        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == 10
        assert len(fills) == 1
        assert fills[0][0] == "YES"
    
    @pytest.mark.asyncio
    async def test_simulate_fill(self, paper_manager):
        """Should trigger fill callback on simulated fill."""
        fills = []
        
        async def on_fill(side, price, qty):
            fills.append((side, price, qty))
        
        paper_manager.set_fill_callback(on_fill)
        
        order = await paper_manager.place_limit_buy(OrderSide.NO, 0.50, 20)
        result = await paper_manager.simulate_fill(order.id)
        
        assert result is True
        assert order.status == OrderStatus.FILLED
        assert len(fills) == 1
        assert fills[0] == ("NO", 0.50, 20)
    
    @pytest.mark.asyncio
    async def test_get_open_orders(self, paper_manager):
        """Should return only open orders."""
        order1 = await paper_manager.place_limit_buy(OrderSide.YES, 0.48, 10)
        order2 = await paper_manager.place_limit_buy(OrderSide.NO, 0.50, 10)
        await paper_manager.cancel_order(order1.id)
        
        open_orders = paper_manager.get_open_orders()
        
        assert len(open_orders) == 1
        assert open_orders[0].id == order2.id
    
    @pytest.mark.asyncio
    async def test_get_open_orders_by_side(self, paper_manager):
        """Should filter open orders by side."""
        await paper_manager.place_limit_buy(OrderSide.YES, 0.48, 10)
        await paper_manager.place_limit_buy(OrderSide.NO, 0.50, 10)
        
        yes_orders = paper_manager.get_open_orders(OrderSide.YES)
        no_orders = paper_manager.get_open_orders(OrderSide.NO)
        
        assert len(yes_orders) == 1
        assert len(no_orders) == 1
        assert yes_orders[0].side == OrderSide.YES
        assert no_orders[0].side == OrderSide.NO


class TestOrder:
    """Tests for Order data structure."""
    
    def test_remaining_quantity(self):
        """Remaining should be size - filled."""
        order = Order(
            id="test",
            side=OrderSide.YES,
            price=0.50,
            size=100,
            filled_qty=25,
        )
        assert order.remaining == 75
    
    def test_is_active(self):
        """Open and partially filled should be active."""
        open_order = Order(id="1", side=OrderSide.YES, price=0.5, size=10, status=OrderStatus.OPEN)
        partial_order = Order(id="2", side=OrderSide.YES, price=0.5, size=10, status=OrderStatus.PARTIALLY_FILLED)
        filled_order = Order(id="3", side=OrderSide.YES, price=0.5, size=10, status=OrderStatus.FILLED)
        cancelled_order = Order(id="4", side=OrderSide.YES, price=0.5, size=10, status=OrderStatus.CANCELLED)
        
        assert open_order.is_active is True
        assert partial_order.is_active is True
        assert filled_order.is_active is False
        assert cancelled_order.is_active is False
