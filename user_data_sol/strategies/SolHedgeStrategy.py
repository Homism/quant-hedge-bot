from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import talib.abstract as ta
from freqtrade.strategy import IStrategy
from pandas import DataFrame

from risk_service.daily_loss_guard import (
    calculate_daily_pnl,
    should_block_new_trades,
    should_stop_after_consecutive_losses,
)
from risk_service.exposure import MAX_LEVERAGE, cap_position_size
from risk_service.kill_switch import is_kill_switch_active, kill_switch_reason
from risk_service.telegram_alerts import send_optional_telegram_alert

logger = logging.getLogger(__name__)


class SolHedgeStrategy(IStrategy):
    """Conservative SOL short hedge strategy for futures dry-run."""

    INTERFACE_VERSION = 3

    can_short = True
    timeframe = "1h"
    startup_candle_count = 60
    process_only_new_candles = True

    # Defensive exit profile: take modest hedge profits, cap downside, no DCA.
    minimal_roi = {"0": 0.04, "120": 0.02, "240": 0.0}
    stoploss = -0.05
    trailing_stop = False
    use_exit_signal = True
    ignore_roi_if_entry_signal = False
    position_adjustment_enable = False

    max_safe_leverage = MAX_LEVERAGE
    max_position_pct = 0.05
    stale_trade_hours = 12

    def bot_start(self, **kwargs: Any) -> None:
        self._kill_switch_alerted = False
        send_optional_telegram_alert("SOL hedge bot started in dry-run mode.")

    @property
    def protections(self) -> list[dict[str, Any]]:
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 1},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 72,
                "trade_limit": 3,
                "stop_duration_candles": 72,
                "required_profit": 0.0,
                "only_per_pair": False,
                "only_per_side": False,
            },
            {
                "method": "MaxDrawdown",
                "calculation_mode": "equity",
                "lookback_period_candles": 24,
                "trade_limit": 1,
                "stop_duration_candles": 24,
                "max_allowed_drawdown": 0.02,
            },
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # EMA20 tracks short-term recovery pressure.
        dataframe["ema_20"] = ta.EMA(dataframe, timeperiod=20)
        # EMA50 defines the slower defensive trend filter.
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        # RSI below 45 confirms weak momentum before opening a short hedge.
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        # Volume must exceed its recent average so weak signals in dead markets are ignored.
        dataframe["volume_mean_20"] = dataframe["volume"].rolling(20, min_periods=20).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0

        defensive_short = (
            (dataframe["close"] < dataframe["ema_50"])
            & (dataframe["ema_20"] < dataframe["ema_50"])
            & (dataframe["rsi"] < 45)
            & (dataframe["volume"] > dataframe["volume_mean_20"])
            & (dataframe["volume"] > 0)
        )

        dataframe.loc[defensive_short, ["enter_short", "enter_tag"]] = (
            1,
            "sol_defensive_ema_rsi_volume_short",
        )
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0

        hedge_recovery = (
            (dataframe["close"] > dataframe["ema_20"])
            | (dataframe["close"] > dataframe["ema_50"])
            | (dataframe["rsi"] > 52)
        ) & (dataframe["volume"] > 0)

        dataframe.loc[hedge_recovery, ["exit_short", "exit_tag"]] = (
            1,
            "sol_recovery_exit",
        )
        return dataframe

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs: Any,
    ) -> float:
        return min(self.max_safe_leverage, float(max_leverage or self.max_safe_leverage))

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs: Any,
    ) -> float:
        available_balance = float(max_stake or proposed_stake or 0)
        stake = cap_position_size(
            proposed_stake=available_balance,
            available_balance=available_balance,
            max_position_pct=self.max_position_pct,
            min_stake=min_stake,
        )
        if stake <= 0:
            logger.warning("blocked trade: 5%% position cap is below exchange minimum stake")
            send_optional_telegram_alert("SOL risk guard blocked a trade: position cap below minimum.")
        elif stake < available_balance:
            logger.info("position stake capped at %.2f USDT by 5%% risk limit", stake)
        return stake

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: str | None,
        side: str,
        **kwargs: Any,
    ) -> bool:
        if side != "short":
            return self._block_entry("strategy allows only short hedge entries")

        if is_kill_switch_active():
            return self._block_entry(kill_switch_reason())

        closed_today = self._closed_trades(pair, current_time, days=1)
        balance = self._stake_balance()
        if balance > 0:
            daily_pnl = calculate_daily_pnl(self._absolute_pnls(closed_today))
            if should_block_new_trades(daily_pnl, balance):
                return self._block_entry("daily loss limit reached")

        recent_closed = self._closed_trades(pair, current_time, days=30)
        if should_stop_after_consecutive_losses(self._absolute_pnls(recent_closed)):
            return self._block_entry("three consecutive losing trades reached")

        return True

    def custom_exit(
        self,
        pair: str,
        trade: Any,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs: Any,
    ) -> str | bool | None:
        if is_kill_switch_active():
            return "kill_switch_exit"

        age = self._trade_age(current_time, getattr(trade, "open_date_utc", None))
        if age is not None and age >= timedelta(hours=self.stale_trade_hours):
            return "stale_trade_timeout"
        return None

    def bot_loop_start(self, current_time: datetime, **kwargs: Any) -> None:
        active = is_kill_switch_active()
        if active and not getattr(self, "_kill_switch_alerted", False):
            logger.warning("risk guard active: %s", kill_switch_reason())
            send_optional_telegram_alert("SOL kill switch activated. New entries are blocked.")
            self._kill_switch_alerted = True
        elif not active:
            self._kill_switch_alerted = False

    def _block_entry(self, reason: str) -> bool:
        logger.warning("blocked trade: %s", reason)
        send_optional_telegram_alert(f"SOL risk guard blocked a trade: {reason}")
        return False

    def _stake_balance(self) -> float:
        try:
            return float(self.wallets.get_total_stake_amount())
        except Exception:
            return float(self.config.get("dry_run_wallet", 0) or 0)

    def _closed_trades(self, pair: str, current_time: datetime, days: int) -> list[Any]:
        try:
            from freqtrade.persistence import Trade

            since = current_time - timedelta(days=days)
            trades = list(Trade.get_trades_proxy(pair=pair, is_open=False, close_date=since))
            return sorted(
                trades,
                key=lambda trade: self._normalize_datetime(
                    getattr(trade, "close_date_utc", None),
                    current_time,
                ),
                reverse=True,
            )
        except Exception as exc:
            logger.warning("could not read closed trades for risk guard: %s", exc)
            return []

    @staticmethod
    def _trade_age(current_time: datetime, open_date: datetime | None) -> timedelta | None:
        if open_date is None:
            return None
        return current_time - SolHedgeStrategy._normalize_datetime(open_date, current_time)

    @staticmethod
    def _normalize_datetime(value: datetime | None, reference: datetime) -> datetime:
        if value is None:
            return datetime.min.replace(tzinfo=reference.tzinfo)
        if reference.tzinfo is not None and value.tzinfo is None:
            return value.replace(tzinfo=reference.tzinfo)
        if reference.tzinfo is None and value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value

    @staticmethod
    def _absolute_pnls(trades: list[Any]) -> list[float]:
        pnls: list[float] = []
        for trade in trades:
            value = getattr(trade, "close_profit_abs", None)
            if value is None:
                value = getattr(trade, "close_profit", 0.0)
            pnls.append(float(value or 0.0))
        return pnls
