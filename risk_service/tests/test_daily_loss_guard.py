import pytest

from risk_service.daily_loss_guard import (
    calculate_daily_loss_pct,
    calculate_daily_pnl,
    count_consecutive_losses,
    should_block_new_trades,
    should_stop_after_consecutive_losses,
)


def test_daily_loss_calculation() -> None:
    assert calculate_daily_pnl([10, -25, 5]) == -10
    assert calculate_daily_loss_pct(-20, 1_000) == 0.02
    assert calculate_daily_loss_pct(20, 1_000) == 0


def test_daily_loss_blocks_at_two_percent() -> None:
    assert should_block_new_trades(-20, 1_000)
    assert not should_block_new_trades(-19.99, 1_000)
    with pytest.raises(ValueError, match="2%"):
        should_block_new_trades(-20, 1_000, max_daily_loss_pct=0.03)


def test_consecutive_loss_guard() -> None:
    assert count_consecutive_losses([-1, -2, -3, 1]) == 3
    assert count_consecutive_losses([-1, 1, -2, -3]) == 1
    assert should_stop_after_consecutive_losses([-1, -2, -3])
    assert not should_stop_after_consecutive_losses([-1, -2, 1])
    with pytest.raises(ValueError, match="3"):
        should_stop_after_consecutive_losses([-1, -2, -3, -4], max_consecutive_losses=4)
