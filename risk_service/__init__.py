"""Risk helpers for the BTC/ETH dry-run hedge bots."""

from risk_service.daily_loss_guard import (
    calculate_daily_loss_pct,
    calculate_daily_pnl,
    count_consecutive_losses,
    should_block_new_trades,
    should_stop_after_consecutive_losses,
)
from risk_service.exposure import (
    MAX_LEVERAGE,
    MAX_POSITION_PCT,
    calculate_account_exposure,
    calculate_notional_value,
    calculate_position_size,
    cap_position_size,
)
from risk_service.hedge_ratio import (
    ALLOWED_HEDGE_RATIOS,
    calculate_hedge_ratio,
    calculate_suggested_short_size,
)
from risk_service.kill_switch import is_kill_switch_active, kill_switch_reason
from risk_service.liquidation import (
    assess_liquidation_risk,
    estimate_short_liquidation_price,
)

__all__ = [
    "ALLOWED_HEDGE_RATIOS",
    "MAX_LEVERAGE",
    "MAX_POSITION_PCT",
    "assess_liquidation_risk",
    "calculate_account_exposure",
    "calculate_daily_loss_pct",
    "calculate_daily_pnl",
    "calculate_hedge_ratio",
    "calculate_notional_value",
    "calculate_position_size",
    "calculate_suggested_short_size",
    "cap_position_size",
    "count_consecutive_losses",
    "estimate_short_liquidation_price",
    "is_kill_switch_active",
    "kill_switch_reason",
    "should_block_new_trades",
    "should_stop_after_consecutive_losses",
]
