"""Approximate liquidation-risk helpers.

These calculations are conservative estimates for pre-trade screening. Real
liquidation prices are exchange-specific and depend on maintenance margin,
funding, fees, and exchange risk tiers.
"""

from __future__ import annotations

from dataclasses import dataclass

from risk_service.exposure import MAX_LEVERAGE, validate_leverage


@dataclass(frozen=True)
class LiquidationAssessment:
    entry_price: float
    leverage: float
    liquidation_price: float
    buffer_pct: float
    is_safe: bool
    reason: str


def _require_positive(value: float, name: str) -> float:
    numeric = float(value)
    if numeric <= 0:
        raise ValueError(f"{name} must be positive")
    return numeric


def estimate_short_liquidation_price(
    entry_price: float,
    leverage: float,
    maintenance_margin_rate: float = 0.005,
) -> float:
    """Estimate a short liquidation price above entry."""

    entry = _require_positive(entry_price, "entry_price")
    lev = validate_leverage(leverage)
    maintenance = float(maintenance_margin_rate)
    if maintenance < 0 or maintenance >= 1:
        raise ValueError("maintenance_margin_rate must be between 0 and 1")
    return entry * (1 + (1 / lev) - maintenance)


def calculate_short_liquidation_buffer_pct(
    entry_price: float,
    liquidation_price: float,
) -> float:
    entry = _require_positive(entry_price, "entry_price")
    liquidation = _require_positive(liquidation_price, "liquidation_price")
    return (liquidation - entry) / entry


def assess_liquidation_risk(
    entry_price: float,
    leverage: float,
    stoploss_price: float | None = None,
    min_buffer_pct: float = 0.2,
) -> LiquidationAssessment:
    """Assess whether a short has enough room before liquidation."""

    entry = _require_positive(entry_price, "entry_price")
    if float(leverage) > MAX_LEVERAGE:
        raise ValueError("leverage cannot exceed 2x")

    liquidation = estimate_short_liquidation_price(entry, leverage)
    buffer_pct = calculate_short_liquidation_buffer_pct(entry, liquidation)

    if stoploss_price is not None:
        stop = _require_positive(stoploss_price, "stoploss_price")
        stop_buffer_pct = (liquidation - stop) / entry
        if stop_buffer_pct <= 0:
            return LiquidationAssessment(
                entry,
                float(leverage),
                liquidation,
                stop_buffer_pct,
                False,
                "stoploss is at or beyond estimated liquidation price",
            )
        buffer_pct = min(buffer_pct, stop_buffer_pct)

    is_safe = buffer_pct >= float(min_buffer_pct)
    reason = "liquidation buffer is acceptable" if is_safe else "liquidation buffer is too small"
    return LiquidationAssessment(entry, float(leverage), liquidation, buffer_pct, is_safe, reason)
