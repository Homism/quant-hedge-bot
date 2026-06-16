"""Environment-loading helpers that avoid exposing secret values."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class EnvSettings:
    exchange_name: str
    exchange_key: str
    exchange_secret: str
    telegram_enabled: bool
    telegram_token: str
    telegram_chat_id: str
    dry_run: bool

    def redacted(self) -> dict[str, object]:
        return {
            "exchange_name": self.exchange_name,
            "exchange_key_set": bool(self.exchange_key),
            "exchange_secret_set": bool(self.exchange_secret),
            "telegram_enabled": self.telegram_enabled,
            "telegram_token_set": bool(self.telegram_token),
            "telegram_chat_id_set": bool(self.telegram_chat_id),
            "dry_run": self.dry_run,
        }


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_env_settings(env: Mapping[str, str] | None = None) -> EnvSettings:
    source = os.environ if env is None else env
    return EnvSettings(
        exchange_name=source.get("EXCHANGE_NAME", "binance"),
        exchange_key=source.get("FREQTRADE__EXCHANGE__KEY", ""),
        exchange_secret=source.get("FREQTRADE__EXCHANGE__SECRET", ""),
        telegram_enabled=_truthy(source.get("FREQTRADE__TELEGRAM__ENABLED")),
        telegram_token=source.get("FREQTRADE__TELEGRAM__TOKEN", ""),
        telegram_chat_id=source.get("FREQTRADE__TELEGRAM__CHAT_ID", ""),
        dry_run=_truthy(source.get("FREQTRADE__DRY_RUN"), default=True),
    )
