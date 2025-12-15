"""
Tests for the state machine.
"""

import pytest
from state_machine import StateMachine, BotState, Position, Inventory


class TestPosition:
    """Tests for Position tracking."""
    
    def test_initial_state(self):
        """New position should be empty."""
        pos = Position()
        assert pos.quantity == 0
        assert pos.total_cost == 0
        assert pos.avg_cost == 0
    
    def test_add_shares(self):
        """Adding shares should update quantity and cost."""
        pos = Position()
        pos.add(10, 0.48)
        
        assert pos.quantity == 10
        assert pos.total_cost == 4.80
        assert abs(pos.avg_cost - 0.48) < 0.0001
    
    def test_multiple_adds_average_cost(self):
        """Multiple adds should calculate average cost correctly."""
        pos = Position()
        pos.add(10, 0.40)  # 10 @ $0.40 = $4.00
        pos.add(10, 0.50)  # 10 @ $0.50 = $5.00
        
        assert pos.quantity == 20
        assert pos.total_cost == 9.00
        assert abs(pos.avg_cost - 0.45) < 0.0001
    
    def test_reset(self):
        """Reset should clear position."""
        pos = Position()
        pos.add(10, 0.50)
        pos.reset()
        
        assert pos.quantity == 0
        assert pos.total_cost == 0


class TestInventory:
    """Tests for Inventory tracking."""
    
    def test_total_cost(self):
        """Total cost should sum both sides."""
        inv = Inventory()
        inv.yes.add(10, 0.48)
        inv.no.add(10, 0.50)
        
        assert abs(inv.total_cost - 9.80) < 0.0001
    
    def test_locked_profit_when_paired(self):
        """Should calculate locked profit correctly."""
        inv = Inventory()
        inv.yes.add(10, 0.48)
        inv.no.add(10, 0.50)
        
        # Cost per pair: 0.48 + 0.50 = 0.98
        # Payout per pair: 1.00
        # Profit per pair: 0.02
        # Total profit: 0.02 * 10 = 0.20
        assert abs(inv.locked_profit - 0.20) < 0.0001
    
    def test_no_profit_if_unbalanced(self):
        """Profit requires matching quantities."""
        inv = Inventory()
        inv.yes.add(10, 0.48)
        # No NO position
        
        assert inv.locked_profit == 0


class TestStateMachine:
    """Tests for StateMachine transitions."""
    
    def test_initial_state(self):
        """Should start in NEUTRAL."""
        sm = StateMachine()
        assert sm.state == BotState.NEUTRAL
    
    def test_valid_transition_neutral_to_legged_yes(self):
        """NEUTRAL -> LEGGED_YES is valid."""
        sm = StateMachine()
        assert sm.can_transition(BotState.LEGGED_YES)
        assert sm.transition(BotState.LEGGED_YES)
        assert sm.state == BotState.LEGGED_YES
    
    def test_valid_transition_neutral_to_legged_no(self):
        """NEUTRAL -> LEGGED_NO is valid."""
        sm = StateMachine()
        assert sm.can_transition(BotState.LEGGED_NO)
        assert sm.transition(BotState.LEGGED_NO)
        assert sm.state == BotState.LEGGED_NO
    
    def test_invalid_transition_neutral_to_locked(self):
        """NEUTRAL -> LOCKED is invalid (must go through LEGGED)."""
        sm = StateMachine()
        assert not sm.can_transition(BotState.LOCKED)
        assert not sm.transition(BotState.LOCKED)
        assert sm.state == BotState.NEUTRAL  # State unchanged
    
    def test_full_path_via_yes(self):
        """Complete path: NEUTRAL -> LEGGED_YES -> LOCKED."""
        sm = StateMachine()
        
        sm.transition(BotState.LEGGED_YES)
        assert sm.state == BotState.LEGGED_YES
        
        sm.transition(BotState.LOCKED)
        assert sm.state == BotState.LOCKED
    
    def test_full_path_via_no(self):
        """Complete path: NEUTRAL -> LEGGED_NO -> LOCKED."""
        sm = StateMachine()
        
        sm.transition(BotState.LEGGED_NO)
        assert sm.state == BotState.LEGGED_NO
        
        sm.transition(BotState.LOCKED)
        assert sm.state == BotState.LOCKED
    
    def test_stop_loss_path(self):
        """LEGGED_YES -> NEUTRAL is valid (stop loss)."""
        sm = StateMachine()
        sm.transition(BotState.LEGGED_YES)
        
        assert sm.can_transition(BotState.NEUTRAL)
        assert sm.transition(BotState.NEUTRAL, "stop loss")
        assert sm.state == BotState.NEUTRAL
    
    def test_on_fill_updates_state(self):
        """Fill events should trigger state transitions."""
        sm = StateMachine()
        
        # First fill: YES
        new_state = sm.on_fill("YES", 0.48, 10)
        assert new_state == BotState.LEGGED_YES
        assert sm.inventory.yes.quantity == 10
        
        # Second fill: NO
        new_state = sm.on_fill("NO", 0.50, 10)
        assert new_state == BotState.LOCKED
        assert sm.inventory.no.quantity == 10
    
    def test_force_neutral(self):
        """Force neutral should reset regardless of current state."""
        sm = StateMachine()
        sm.transition(BotState.LEGGED_YES)
        sm.inventory.yes.add(10, 0.48)
        
        sm.force_neutral("emergency")
        
        assert sm.state == BotState.NEUTRAL
        assert sm.inventory.yes.quantity == 0
    
    def test_get_summary(self):
        """Summary should include all relevant info."""
        sm = StateMachine()
        sm.on_fill("YES", 0.48, 10)
        sm.on_fill("NO", 0.50, 10)
        
        summary = sm.get_summary()
        
        assert summary["state"] == "LOCKED"
        assert summary["yes_qty"] == 10
        assert summary["no_qty"] == 10
        assert abs(summary["locked_profit"] - 0.20) < 0.0001
        assert summary["transitions"] == 2
