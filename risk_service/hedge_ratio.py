"""Hedge-ratio helpers for spot exposure and short hedge sizing."""

from __future__ import annotations

ALLOWED_HEDGE_RATIOS = (0.25, 0.5, 0.75, 1.0)


def _require_non_negative(value: float, name: str) -> float:
    numeric = float(value)
    if numeric < 0:
        raise ValueError(f"{name} must be non-negative")
    return numeric


def _validate_ratio(ratio: float) -> float:
    numeric = float(ratio)
    if numeric not in ALLOWED_HEDGE_RATIOS:
        allowed = ", ".join(f"{item:.0%}" for item in ALLOWED_HEDGE_RATIOS)
        raise ValueError(f"hedge ratio must be one of: {allowed}")
    return numeric


def calculate_hedge_ratio(spot_exposure_value: float, short_notional_value: float) -> float:
    """Return the current hedge ratio, capped at 100% for reporting."""

    exposure = _require_non_negative(spot_exposure_value, "spot_exposure_value")
    short_notional = _require_non_negative(short_notional_value, "short_notional_value")
    if exposure == 0:
        return 0.0
    return min(short_notional / exposure, 1.0)


def calculate_suggested_short_size(
    spot_exposure_value: float,
    hedge_ratio: float,
) -> float:
    """Return suggested short notional for an allowed hedge ratio."""

    exposure = _require_non_negative(spot_exposure_value, "spot_exposure_value")
    ratio = _validate_ratio(hedge_ratio)
    return exposure * ratio


def build_hedge_ratio_table(spot_exposure_value: float) -> dict[str, float]:
    exposure = _require_non_negative(spot_exposure_value, "spot_exposure_value")
    return {
        f"{ratio:.0%}": calculate_suggested_short_size(exposure, ratio)
        for ratio in ALLOWED_HEDGE_RATIOS
    }
