"""
Black-Scholes Binary Options Pricing Engine.
Calculates fair value probability for binary options based on:
- Current underlying price
- Strike price  
- Time to expiry
- Implied volatility
"""

import math
from scipy.stats import norm
from datetime import datetime
from typing import Tuple


def black_scholes_binary(
    S: float,
    K: float,
    T: float,
    sigma: float,
    r: float = 0.0
) -> float:
    """
    Calculate fair value probability for a binary (digital) option.
    
    This uses the Black-Scholes formula for a cash-or-nothing binary option,
    which pays $1 if the underlying price S is above strike K at expiry.
    
    Args:
        S: Current underlying price (e.g., BTC spot price)
        K: Strike price of the binary option
        T: Time to expiry in years (e.g., 15 minutes = 15/525600)
        sigma: Implied volatility (annualized, e.g., 0.60 for 60%)
        r: Risk-free rate (default 0, negligible for short-term)
    
    Returns:
        Probability that price will be above strike at expiry (0.0 to 1.0)
    """
    if T <= 0:
        # At or past expiry: deterministic outcome
        return 1.0 if S > K else 0.0
    
    if sigma <= 0:
        raise ValueError("Volatility must be positive")
    
    # Calculate d2 (the key term for binary options)
    # d2 = (ln(S/K) + (r - σ²/2) * T) / (σ * √T)
    sqrt_T = math.sqrt(T)
    d2 = (math.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    
    # Fair value is N(d2) - cumulative normal distribution
    fair_value = norm.cdf(d2)
    
    return fair_value


def calculate_time_to_expiry(expiry_timestamp: float) -> float:
    """
    Calculate time to expiry in years.
    
    Args:
        expiry_timestamp: Unix timestamp of expiry
    
    Returns:
        Time to expiry in years (for Black-Scholes T parameter)
    """
    now = datetime.now().timestamp()
    seconds_remaining = max(0, expiry_timestamp - now)
    
    # Convert to years (365.25 days * 24 hours * 60 minutes * 60 seconds)
    seconds_per_year = 365.25 * 24 * 60 * 60
    return seconds_remaining / seconds_per_year


def minutes_to_years(minutes: float) -> float:
    """Convert minutes to years for Black-Scholes T parameter."""
    return minutes / (365.25 * 24 * 60)


def get_fair_values(
    S: float,
    K: float,
    T: float,
    sigma: float
) -> Tuple[float, float]:
    """
    Get fair values for both YES and NO sides.
    
    Args:
        S: Current underlying price
        K: Strike price
        T: Time to expiry in years
        sigma: Implied volatility
    
    Returns:
        Tuple of (fair_value_yes, fair_value_no)
    """
    fv_yes = black_scholes_binary(S, K, T, sigma)
    fv_no = 1.0 - fv_yes
    return (fv_yes, fv_no)


def get_skewed_bid(
    fair_value: float,
    inventory: float,
    spread: float,
    risk_factor: float = 0.01
) -> float:
    """
    Calculate inventory-adjusted bid price.
    
    Adjusts bid based on current inventory to manage risk:
    - Higher inventory → lower bid (discourage accumulation)
    - Lower inventory → bid closer to fair value
    
    Formula: Bid = FairValue - Spread - (Inventory × RiskFactor)
    
    Args:
        fair_value: Calculated fair value from Black-Scholes
        inventory: Current position in this side (positive = long)
        spread: Base spread to capture (e.g., 0.02)
        risk_factor: How much to adjust per unit of inventory
    
    Returns:
        Skewed bid price
    """
    skew = inventory * risk_factor
    bid = fair_value - spread - skew
    
    # Clamp to valid range
    return max(0.01, min(0.99, bid))


def kelly_size(
    bankroll: float,
    probability: float,
    odds: float = 1.0,
    fraction: float = 0.1
) -> float:
    """
    Calculate position size using fractional Kelly criterion.
    
    Kelly formula: f* = (bp - q) / b
    where b = odds, p = probability of winning, q = 1-p
    
    We use a fraction of Kelly (default 10%) for safety.
    
    Args:
        bankroll: Total available capital
        probability: Estimated probability of winning
        odds: Payout odds (default 1:1 for binary options)
        fraction: Fraction of Kelly to use (default 0.1)
    
    Returns:
        Recommended position size in dollars
    """
    if probability <= 0 or probability >= 1:
        return 0
    
    q = 1 - probability
    kelly = (odds * probability - q) / odds
    
    # Only bet if positive edge
    if kelly <= 0:
        return 0
    
    return bankroll * fraction * kelly
