"""
Tests for the Black-Scholes pricing engine.
"""

import pytest
import math
from pricing import (
    black_scholes_binary,
    minutes_to_years,
    get_fair_values,
    get_skewed_bid,
    kelly_size,
)


class TestBlackScholesBinary:
    """Tests for the Black-Scholes binary option pricing."""
    
    def test_at_the_money_is_roughly_50_percent(self):
        """ATM binary option should be close to 50%."""
        # With short time to expiry, drift effects are minimal
        result = black_scholes_binary(
            S=100000,  # Current price
            K=100000,  # Strike = Current (ATM)
            T=minutes_to_years(15),  # 15 minutes
            sigma=0.60,
        )
        assert 0.45 <= result <= 0.55
    
    def test_deep_in_the_money(self):
        """Deep ITM should be close to 1.0."""
        result = black_scholes_binary(
            S=110000,  # Current price
            K=100000,  # Strike well below current
            T=minutes_to_years(15),
            sigma=0.60,
        )
        assert result > 0.90
    
    def test_deep_out_of_the_money(self):
        """Deep OTM should be close to 0.0."""
        result = black_scholes_binary(
            S=90000,   # Current price
            K=100000,  # Strike well above current
            T=minutes_to_years(15),
            sigma=0.60,
        )
        assert result < 0.10
    
    def test_at_expiry_above_strike(self):
        """At expiry, above strike = 100%."""
        result = black_scholes_binary(
            S=100001,
            K=100000,
            T=0,  # At expiry
            sigma=0.60,
        )
        assert result == 1.0
    
    def test_at_expiry_below_strike(self):
        """At expiry, below strike = 0%."""
        result = black_scholes_binary(
            S=99999,
            K=100000,
            T=0,  # At expiry
            sigma=0.60,
        )
        assert result == 0.0
    
    def test_higher_volatility_increases_otm_value(self):
        """Higher vol should increase OTM option value (more uncertainty)."""
        base = black_scholes_binary(S=95000, K=100000, T=minutes_to_years(15), sigma=0.30)
        high_vol = black_scholes_binary(S=95000, K=100000, T=minutes_to_years(15), sigma=0.90)
        
        # Higher vol means more chance to reach strike
        assert high_vol > base
    
    def test_longer_time_increases_uncertainty(self):
        """Longer time to expiry should move probabilities toward 50%."""
        short_time = black_scholes_binary(S=105000, K=100000, T=minutes_to_years(5), sigma=0.60)
        long_time = black_scholes_binary(S=105000, K=100000, T=minutes_to_years(60), sigma=0.60)
        
        # With ITM option, longer time = more uncertainty = lower probability
        # (more time for price to drop below strike)
        assert long_time < short_time
    
    def test_zero_volatility_raises(self):
        """Zero volatility should raise ValueError."""
        with pytest.raises(ValueError):
            black_scholes_binary(S=100000, K=100000, T=0.01, sigma=0)
    
    def test_negative_volatility_raises(self):
        """Negative volatility should raise ValueError."""
        with pytest.raises(ValueError):
            black_scholes_binary(S=100000, K=100000, T=0.01, sigma=-0.5)


class TestTimeConversion:
    """Tests for time conversion utilities."""
    
    def test_minutes_to_years(self):
        """Test minute to year conversion."""
        # 525960 minutes in a year (365.25 days)
        one_year = minutes_to_years(365.25 * 24 * 60)
        assert abs(one_year - 1.0) < 0.001
    
    def test_15_minutes(self):
        """15 minutes should be a tiny fraction of a year."""
        T = minutes_to_years(15)
        assert T < 0.0001  # Less than 0.01% of a year


class TestFairValues:
    """Tests for fair value calculations."""
    
    def test_yes_plus_no_equals_one(self):
        """YES + NO fair values should sum to 1.0."""
        fv_yes, fv_no = get_fair_values(
            S=100000, K=100000, T=0.001, sigma=0.60
        )
        assert abs(fv_yes + fv_no - 1.0) < 0.0001


class TestSkewedBid:
    """Tests for inventory-adjusted bid calculation."""
    
    def test_zero_inventory_no_skew(self):
        """Zero inventory should give fair value minus spread."""
        bid = get_skewed_bid(
            fair_value=0.50,
            inventory=0,
            spread=0.02,
            risk_factor=0.01,
        )
        assert abs(bid - 0.48) < 0.0001
    
    def test_positive_inventory_lowers_bid(self):
        """Holding inventory should lower the bid."""
        no_inv = get_skewed_bid(0.50, inventory=0, spread=0.02, risk_factor=0.01)
        with_inv = get_skewed_bid(0.50, inventory=10, spread=0.02, risk_factor=0.01)
        
        assert with_inv < no_inv
    
    def test_bid_clamped_to_valid_range(self):
        """Bid should be clamped to 0.01-0.99."""
        # Very low fair value or high inventory
        bid = get_skewed_bid(
            fair_value=0.05,
            inventory=100,
            spread=0.02,
            risk_factor=0.01,
        )
        assert bid >= 0.01
        
        # Very high fair value
        bid = get_skewed_bid(
            fair_value=0.99,
            inventory=0,
            spread=0.02,
        )
        assert bid <= 0.99


class TestKellySize:
    """Tests for Kelly criterion sizing."""
    
    def test_no_edge_no_bet(self):
        """50% probability with even odds = no edge = no bet."""
        size = kelly_size(bankroll=1000, probability=0.50)
        assert size == 0
    
    def test_positive_edge_positive_size(self):
        """Positive edge should give positive size."""
        size = kelly_size(bankroll=1000, probability=0.60)
        assert size > 0
    
    def test_fraction_reduces_size(self):
        """Using fraction of Kelly should reduce size."""
        full = kelly_size(bankroll=1000, probability=0.60, fraction=1.0)
        tenth = kelly_size(bankroll=1000, probability=0.60, fraction=0.1)
        
        assert abs(tenth - full * 0.1) < 0.01
    
    def test_extreme_probabilities_return_zero(self):
        """Probabilities of 0 or 1 should return 0 (can't bet on certainty)."""
        assert kelly_size(1000, probability=0) == 0
        assert kelly_size(1000, probability=1) == 0
