"""Exposure and position-size helpers.

All values are expressed in stake currency, normally USDT.
"""

from __future__ import annotations

from collections.abc import Iterable

MAX_POSITION_PCT = 0.05
MAX_LEVERAGE = 2.0


def _require_non_negative(value: float, name: str) -> float:
    numeric = float(value)
    if numeric < 0:
        raise ValueError(f"{name} must be non-negative")
    return numeric


def _require_positive(value: float, name: str) -> float:
    numeric = float(value)
    if numeric <= 0:
        raise ValueError(f"{name} must be positive")
    return numeric


def _validate_position_pct(max_position_pct: float) -> float:
    pct = _require_non_negative(max_position_pct, "max_position_pct")
    if pct > MAX_POSITION_PCT:
        raise ValueError("max_position_pct cannot exceed 5%")
    return pct


def validate_leverage(leverage: float) -> float:
    lev = _require_positive(leverage, "leverage")
    if lev > MAX_LEVERAGE:
        raise ValueError("leverage cannot exceed 2x")
    return lev


def calculate_position_size(
    available_balance: float,
    max_position_pct: float = MAX_POSITION_PCT,
) -> float:
    """Return the maximum stake amount allowed for one position."""

    balance = _require_non_negative(available_balance, "available_balance")
    pct = _validate_position_pct(max_position_pct)
    return balance * pct


def cap_position_size(
    proposed_stake: float,
    available_balance: float,
    max_position_pct: float = MAX_POSITION_PCT,
    min_stake: float | None = None,
) -> float:
    """Cap a proposed stake at the configured risk limit.

    Returning 0 means the exchange minimum is larger than the allowed risk size,
    so the trade should be blocked instead of enlarged.
    """

    proposed = _require_non_negative(proposed_stake, "proposed_stake")
    cap = calculate_position_size(available_balance, max_position_pct)
    stake = min(proposed, cap)
    if min_stake is not None and stake < float(min_stake):
        return 0.0
    return stake


def calculate_notional_value(stake_amount: float, leverage: float = 1.0) -> float:
    stake = _require_non_negative(stake_amount, "stake_amount")
    lev = validate_leverage(leverage)
    return stake * lev


def calculate_account_exposure(
    open_position_notionals: Iterable[float],
    available_balance: float,
) -> float:
    """Return notional exposure divided by available balance."""

    balance = _require_positive(available_balance, "available_balance")
    total_notional = sum(abs(float(value)) for value in open_position_notionals)
    return total_notional / balance
