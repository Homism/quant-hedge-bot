import pytest

from risk_service.exposure import (
    calculate_account_exposure,
    calculate_notional_value,
    calculate_position_size,
    cap_position_size,
)


def test_position_size_is_capped_at_five_percent() -> None:
    assert calculate_position_size(10_000) == 500


def test_position_size_rejects_limits_above_five_percent() -> None:
    with pytest.raises(ValueError, match="5%"):
        calculate_position_size(10_000, max_position_pct=0.10)


def test_cap_position_size_blocks_when_exchange_minimum_is_too_large() -> None:
    assert cap_position_size(1_000, 10_000, min_stake=600) == 0


def test_notional_value_rejects_leverage_above_two() -> None:
    assert calculate_notional_value(500, leverage=2) == 1_000
    with pytest.raises(ValueError, match="2x"):
        calculate_notional_value(500, leverage=3)


def test_account_exposure_uses_absolute_notional() -> None:
    assert calculate_account_exposure([-250, 250], available_balance=1_000) == 0.5
