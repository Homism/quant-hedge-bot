import pytest

from risk_service.liquidation import (
    assess_liquidation_risk,
    estimate_short_liquidation_price,
)


def test_short_liquidation_estimate_is_above_entry() -> None:
    assert estimate_short_liquidation_price(100, leverage=2) == pytest.approx(149.5)


def test_liquidation_assessment_flags_small_stoploss_buffer() -> None:
    safe = assess_liquidation_risk(100, leverage=2)
    assert safe.is_safe

    unsafe = assess_liquidation_risk(100, leverage=2, stoploss_price=140)
    assert not unsafe.is_safe
    assert "too small" in unsafe.reason


def test_liquidation_rejects_leverage_above_two() -> None:
    with pytest.raises(ValueError, match="2x"):
        assess_liquidation_risk(100, leverage=3)
