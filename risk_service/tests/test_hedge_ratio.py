import pytest

from risk_service.hedge_ratio import (
    build_hedge_ratio_table,
    calculate_hedge_ratio,
    calculate_suggested_short_size,
)


def test_calculate_current_hedge_ratio() -> None:
    assert calculate_hedge_ratio(10_000, 5_000) == 0.5
    assert calculate_hedge_ratio(10_000, 12_000) == 1.0
    assert calculate_hedge_ratio(0, 1_000) == 0.0


def test_suggested_short_size_allows_only_supported_ratios() -> None:
    assert calculate_suggested_short_size(10_000, 0.25) == 2_500
    assert calculate_suggested_short_size(10_000, 0.5) == 5_000
    assert calculate_suggested_short_size(10_000, 0.75) == 7_500
    assert calculate_suggested_short_size(10_000, 1.0) == 10_000
    with pytest.raises(ValueError, match="hedge ratio"):
        calculate_suggested_short_size(10_000, 0.33)


def test_hedge_ratio_table() -> None:
    assert build_hedge_ratio_table(1_000) == {
        "25%": 250,
        "50%": 500,
        "75%": 750,
        "100%": 1_000,
    }
