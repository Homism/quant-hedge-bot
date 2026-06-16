"""Daily loss and losing-streak guard helpers."""

from __future__ import annotations

from collections.abc import Iterable

MAX_DAILY_LOSS_PCT = 0.02
MAX_CONSECUTIVE_LOSSES = 3


def calculate_daily_pnl(closed_trade_pnls: Iterable[float]) -> float:
    return sum(float(value) for value in closed_trade_pnls)


def calculate_daily_loss_pct(realized_pnl: float, starting_balance: float) -> float:
    balance = float(starting_balance)
    if balance <= 0:
        raise ValueError("starting_balance must be positive")
    pnl = float(realized_pnl)
    if pnl >= 0:
        return 0.0
    return abs(pnl) / balance


def should_block_new_trades(
    realized_pnl: float,
    starting_balance: float,
    max_daily_loss_pct: float = MAX_DAILY_LOSS_PCT,
) -> bool:
    if float(max_daily_loss_pct) > MAX_DAILY_LOSS_PCT:
        raise ValueError("max_daily_loss_pct cannot exceed 2%")
    return calculate_daily_loss_pct(realized_pnl, starting_balance) >= float(max_daily_loss_pct)


def count_consecutive_losses(closed_trade_pnls_newest_first: Iterable[float]) -> int:
    count = 0
    for pnl in closed_trade_pnls_newest_first:
        if float(pnl) < 0:
            count += 1
            continue
        break
    return count


def should_stop_after_consecutive_losses(
    closed_trade_pnls_newest_first: Iterable[float],
    max_consecutive_losses: int = MAX_CONSECUTIVE_LOSSES,
) -> bool:
    if int(max_consecutive_losses) > MAX_CONSECUTIVE_LOSSES:
        raise ValueError("max_consecutive_losses cannot exceed 3")
    return count_consecutive_losses(closed_trade_pnls_newest_first) >= int(max_consecutive_losses)
