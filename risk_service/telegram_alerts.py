"""Optional Telegram alert sender.

The sender is a no-op unless both token and chat_id are present in the
environment. It is deliberately tiny so risk guards can notify without adding
another runtime dependency.
"""

from __future__ import annotations

import json
import logging
import os
from urllib import request

logger = logging.getLogger(__name__)


def send_optional_telegram_alert(message: str) -> bool:
    token = os.getenv("FREQTRADE__TELEGRAM__TOKEN", "")
    chat_id = os.getenv("FREQTRADE__TELEGRAM__CHAT_ID", "")
    enabled = os.getenv("FREQTRADE__TELEGRAM__ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not enabled or not token or not chat_id:
        return False

    payload = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    req = request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=5) as response:
            return 200 <= response.status < 300
    except Exception as exc:  # pragma: no cover - network depends on runtime credentials.
        logger.warning("telegram alert failed: %s", exc)
        return False
