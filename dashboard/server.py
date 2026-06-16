from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import parse, request

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
KILL_SWITCH_PATH = Path(os.getenv("KILL_SWITCH_PATH", "/runtime/KILL_SWITCH"))
REQUEST_TIMEOUT = float(os.getenv("DASHBOARD_REQUEST_TIMEOUT", "3"))
XAUT_VALIDATION_TTL = int(os.getenv("DASHBOARD_XAUT_VALIDATION_TTL", "300"))
MARKET_DATA_TTL = int(os.getenv("DASHBOARD_MARKET_DATA_TTL", "30"))
MARKET_RECORDER_STATE_PATH = Path(os.getenv("MARKET_RECORDER_STATE_PATH", "/runtime/market_recorder/state.json"))
MARKET_RECORDER_STALE_MS = int(os.getenv("MARKET_RECORDER_STALE_MS", "3000"))
_XAUT_VALIDATION_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_MARKET_DATA_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}

MAX_LEVERAGE = 2
MAX_POSITION_SIZE_PCT = 5
DAILY_LOSS_LIMIT_PCT = 2
CONSECUTIVE_LOSS_LIMIT = 3


@dataclass(frozen=True)
class BotConfig:
    key: str
    label: str
    api_url: str
    username: str
    password: str
    pair: str
    port: int
    validation_gated: bool = False


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def bot_configs() -> list[BotConfig]:
    return [
        BotConfig(
            "btc",
            "BTC",
            _env("DASHBOARD_BTC_API_URL", "http://freqtrade-btc:8080"),
            _env("BTC_FREQTRADE__API_SERVER__USERNAME", "freqtrader_btc"),
            _env("BTC_FREQTRADE__API_SERVER__PASSWORD", "change-me-btc-local-only"),
            "BTC/USDT:USDT",
            8081,
        ),
        BotConfig(
            "eth",
            "ETH",
            _env("DASHBOARD_ETH_API_URL", "http://freqtrade-eth:8080"),
            _env("ETH_FREQTRADE__API_SERVER__USERNAME", "freqtrader_eth"),
            _env("ETH_FREQTRADE__API_SERVER__PASSWORD", "change-me-eth-local-only"),
            "ETH/USDT:USDT",
            8082,
        ),
        BotConfig(
            "sol",
            "SOL",
            _env("DASHBOARD_SOL_API_URL", "http://freqtrade-sol:8080"),
            _env("SOL_FREQTRADE__API_SERVER__USERNAME", "freqtrader_sol"),
            _env("SOL_FREQTRADE__API_SERVER__PASSWORD", "change-me-sol-local-only"),
            "SOL/USDT:USDT",
            8083,
        ),
        BotConfig(
            "xaut",
            "XAUT",
            _env("DASHBOARD_XAUT_API_URL", "http://freqtrade-xaut:8080"),
            _env("XAUT_FREQTRADE__API_SERVER__USERNAME", "freqtrader_xaut"),
            _env("XAUT_FREQTRADE__API_SERVER__PASSWORD", "change-me-xaut-local-only"),
            "XAUT/USDT:USDT",
            8084,
            validation_gated=True,
        ),
    ]


def get_json(url: str, username: str | None = None, password: str | None = None) -> tuple[Any, str | None]:
    headers = {"Accept": "application/json"}
    if username and password:
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"
    req = request.Request(url, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8")), None
    except Exception as exc:
        return None, str(exc)


def bot_endpoint(bot: BotConfig, path: str) -> tuple[Any, str | None]:
    url = f"{bot.api_url.rstrip('/')}{path}"
    return get_json(url, bot.username, bot.password)


def first_number(payload: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = payload.get(key)
        number = safe_float(value)
        if number is not None:
            return number
    return None


def safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    number = safe_float(value)
    return int(number) if number is not None else None


def pair_to_binance_symbol(pair: str) -> str:
    base_quote = pair.split(":", 1)[0]
    base, quote = base_quote.split("/", 1)
    return f"{base}{quote}"


def utc_iso_from_ms(value: Any) -> str | None:
    number = safe_float(value)
    if number is None:
        return None
    return datetime.fromtimestamp(number / 1000, tz=timezone.utc).isoformat()


def parse_candles(raw: Any) -> list[dict[str, Any]]:
    candles: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return candles
    for item in raw:
        if not isinstance(item, list) or len(item) < 6:
            continue
        candles.append(
            {
                "open_time": safe_int(item[0]),
                "open": safe_float(item[1]),
                "high": safe_float(item[2]),
                "low": safe_float(item[3]),
                "close": safe_float(item[4]),
                "volume": safe_float(item[5]),
                "close_time": safe_int(item[6]) if len(item) > 6 else None,
            }
        )
    return candles


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    current = sum(values[:period]) / period
    multiplier = 2 / (period + 1)
    for value in values[period:]:
        current = (value - current) * multiplier + current
    return current


def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    changes = [values[index] - values[index - 1] for index in range(1, len(values))]
    recent = changes[-period:]
    gains = [max(change, 0) for change in recent]
    losses = [abs(min(change, 0)) for change in recent]
    average_gain = sum(gains) / period
    average_loss = sum(losses) / period
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def volume_average(candles: list[dict[str, Any]], period: int = 20) -> float | None:
    volumes = [candle["volume"] for candle in candles if candle.get("volume") is not None]
    if len(volumes) < period:
        return None
    return sum(volumes[-period:]) / period


def evaluate_strategy(market: dict[str, Any]) -> dict[str, Any]:
    indicators = market.get("indicators") or {}
    price = safe_float(market.get("current_price"))
    ema20 = safe_float(indicators.get("ema20"))
    ema50 = safe_float(indicators.get("ema50"))
    current_rsi = safe_float(indicators.get("rsi"))
    current_volume = safe_float(market.get("current_candle_volume"))
    avg_volume = safe_float(indicators.get("volume_average"))

    checks = [
        (
            "price_below_ema50",
            price is not None and ema50 is not None and price < ema50,
            "价格低于 EMA50",
            "价格仍高于或等于 EMA50",
        ),
        (
            "ema20_below_ema50",
            ema20 is not None and ema50 is not None and ema20 < ema50,
            "EMA20 低于 EMA50",
            "EMA20 未低于 EMA50",
        ),
        (
            "rsi_below_45",
            current_rsi is not None and current_rsi < 45,
            "RSI 低于 45",
            "RSI 未低于 45",
        ),
        (
            "volume_above_average",
            current_volume is not None and avg_volume is not None and current_volume > avg_volume,
            "成交量高于 20 根均量",
            "成交量未强于 20 根均量",
        ),
    ]
    entry_reasons = [success_text for _, passed, success_text, _ in checks if passed]
    entry_blockers = [failure_text for _, passed, _, failure_text in checks if not passed]

    exit_checks = [
        (
            "price_above_ema20",
            price is not None and ema20 is not None and price > ema20,
            "价格重新站上 EMA20",
        ),
        (
            "price_above_ema50",
            price is not None and ema50 is not None and price > ema50,
            "价格重新站上 EMA50",
        ),
        (
            "rsi_above_52",
            current_rsi is not None and current_rsi > 52,
            "RSI 回到 52 以上",
        ),
    ]
    exit_reasons = [text for _, passed, text in exit_checks if passed]
    short_entry_met = not entry_blockers
    exit_met = bool(exit_reasons)
    return {
        "short_entry_met": short_entry_met,
        "exit_met": exit_met,
        "entry_reasons": entry_reasons,
        "entry_blockers": entry_blockers,
        "exit_reasons": exit_reasons,
        "entry_explanation": (
            "满足做空入场条件：" + "、".join(entry_reasons)
            if short_entry_met
            else "暂不开仓：" + "、".join(entry_blockers)
        ),
        "exit_explanation": (
            "满足退出条件：" + "、".join(exit_reasons)
            if exit_met
            else "暂不退出：价格和 RSI 尚未出现明确恢复信号"
        ),
    }


def binance_market_snapshot(pair: str) -> dict[str, Any]:
    symbol = pair_to_binance_symbol(pair)
    cache_key = f"binance:{symbol}"
    cached = _MARKET_DATA_CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < MARKET_DATA_TTL:
        return cached[1]

    ticker, ticker_error = get_json(f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}")
    premium, premium_error = get_json(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}")
    raw_candles, candle_error = get_json(f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1h&limit=80")
    candles = parse_candles(raw_candles)
    closes = [candle["close"] for candle in candles if candle.get("close") is not None]
    last_candle = candles[-1] if candles else {}
    last_price = first_number(ticker or {}, ("lastPrice", "weightedAvgPrice")) if isinstance(ticker, dict) else None
    fallback_price = safe_float(last_candle.get("close"))
    current_price = last_price if last_price is not None else fallback_price
    current_volume = safe_float(last_candle.get("volume"))

    market = {
        "source": "binance_futures_public",
        "symbol": symbol,
        "current_price": current_price,
        "change_24h_pct": first_number(ticker or {}, ("priceChangePercent",)) if isinstance(ticker, dict) else None,
        "volume_24h": first_number(ticker or {}, ("volume",)) if isinstance(ticker, dict) else None,
        "quote_volume_24h": first_number(ticker or {}, ("quoteVolume",)) if isinstance(ticker, dict) else None,
        "funding_rate": first_number(premium or {}, ("lastFundingRate",)) if isinstance(premium, dict) else None,
        "last_candle_time": utc_iso_from_ms(last_candle.get("close_time")),
        "current_candle_volume": current_volume,
        "indicators": {
            "ema20": ema(closes, 20),
            "ema50": ema(closes, 50),
            "rsi": rsi(closes, 14),
            "volume_average": volume_average(candles, 20),
        },
        "error": ticker_error or premium_error or candle_error,
    }
    market["strategy"] = evaluate_strategy(market)
    _MARKET_DATA_CACHE[cache_key] = (now, market)
    return market


def xaut_external_prices() -> dict[str, Any]:
    cached = _MARKET_DATA_CACHE.get("xaut:external_prices")
    now = time.time()
    if cached and now - cached[0] < MARKET_DATA_TTL:
        return cached[1]

    binance, binance_error = get_json("https://api.binance.com/api/v3/ticker/price?symbol=XAUTUSDT")
    okx, okx_error = get_json("https://www.okx.com/api/v5/market/ticker?instId=XAUT-USDT")
    binance_price = first_number(binance or {}, ("price",)) if isinstance(binance, dict) else None
    okx_price = None
    if isinstance(okx, dict):
        rows = okx.get("data")
        if isinstance(rows, list) and rows:
            okx_price = first_number(rows[0], ("last",))
    spread_pct = None
    if binance_price is not None and okx_price not in (None, 0):
        spread_pct = ((binance_price - okx_price) / okx_price) * 100
    result = {
        "binance_price": binance_price,
        "okx_price": okx_price,
        "spread_pct": spread_pct,
        "spread_note": "后续用于 XAUT spread monitor",
        "error": binance_error or okx_error,
    }
    _MARKET_DATA_CACHE["xaut:external_prices"] = (now, result)
    return result


def load_market_recorder_state() -> dict[str, Any]:
    checked_at_ms = int(time.time() * 1000)
    base = {
        "service": "market_recorder",
        "read_only": True,
        "trading_enabled": False,
        "api_key_required": False,
        "order_actions": False,
        "state_file": str(MARKET_RECORDER_STATE_PATH),
        "state_file_exists": MARKET_RECORDER_STATE_PATH.exists(),
        "fresh": False,
        "healthy": False,
        "status": "not_started",
        "age_ms": None,
        "checked_at_ms": checked_at_ms,
    }
    if not MARKET_RECORDER_STATE_PATH.exists():
        return base
    try:
        payload = json.loads(MARKET_RECORDER_STATE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        base.update({"status": "state_error", "error": str(exc)})
        return base
    if not isinstance(payload, dict):
        base.update({"status": "state_error", "error": "Recorder state is not a JSON object."})
        return base

    updated_at_ms = safe_int(payload.get("updated_at_ms"))
    age_ms = checked_at_ms - updated_at_ms if updated_at_ms is not None else None
    fresh = age_ms is not None and age_ms <= MARKET_RECORDER_STALE_MS
    sources = payload.get("sources") if isinstance(payload.get("sources"), dict) else {}
    connected_sources = [
        source
        for source in ("binance_futures", "okx_public")
        if isinstance(sources.get(source), dict) and sources[source].get("connected") is True
    ]
    status = payload.get("status")
    if not status:
        status = "running" if fresh else "stale"
    payload.update(
        {
            "read_only": True,
            "trading_enabled": False,
            "api_key_required": False,
            "order_actions": False,
            "state_file": str(MARKET_RECORDER_STATE_PATH),
            "state_file_exists": True,
            "fresh": fresh,
            "healthy": fresh and len(connected_sources) == 2,
            "status": status if fresh or status == "stopped" else "stale",
            "age_ms": age_ms,
            "checked_at_ms": checked_at_ms,
            "connected_sources": connected_sources,
            "expected_sources": ["binance_futures", "okx_public"],
        }
    )
    return payload


def xaut_validation(exchange: str) -> dict[str, Any]:
    cached = _XAUT_VALIDATION_CACHE.get(exchange)
    now = time.time()
    if cached and now - cached[0] < XAUT_VALIDATION_TTL:
        return cached[1]

    if exchange == "okx":
        spot_url = "https://www.okx.com/api/v5/public/instruments?instType=SPOT&instId=XAUT-USDT"
        futures_url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=XAUT-USDT-SWAP"
        spot, spot_error = get_json(spot_url)
        futures, futures_error = get_json(futures_url)
        spot_exists = any(
            item.get("instId") == "XAUT-USDT" and item.get("state") == "live"
            for item in (spot or {}).get("data", [])
        )
        futures_exists = any(
            item.get("instId") == "XAUT-USDT-SWAP" and item.get("state") == "live"
            for item in (futures or {}).get("data", [])
        )
        result = {
            "exchange": "okx",
            "spot_pair": "XAUT/USDT",
            "futures_pair": "XAUT/USDT:USDT",
            "spot_exists": spot_exists,
            "futures_exists": futures_exists,
            "can_enable_bot": futures_exists,
            "error": spot_error or futures_error,
            "reason": None if futures_exists else "OKX XAUT-USDT-SWAP was not found.",
        }
        _XAUT_VALIDATION_CACHE[exchange] = (now, result)
        return result

    spot, spot_error = get_json("https://api.binance.com/api/v3/exchangeInfo?symbol=XAUTUSDT")
    futures, futures_error = get_json("https://fapi.binance.com/fapi/v1/exchangeInfo")
    spot_exists = any(
        item.get("symbol") == "XAUTUSDT" and item.get("status") == "TRADING"
        for item in (spot or {}).get("symbols", [])
    )
    futures_exists = any(
        item.get("symbol") == "XAUTUSDT"
        and item.get("status") == "TRADING"
        and "PERPETUAL" in str(item.get("contractType", ""))
        for item in (futures or {}).get("symbols", [])
    )
    result = {
        "exchange": "binance",
        "spot_pair": "XAUT/USDT",
        "futures_pair": "XAUT/USDT:USDT",
        "spot_exists": spot_exists,
        "futures_exists": futures_exists,
        "can_enable_bot": futures_exists,
        "error": spot_error or futures_error,
        "reason": None if futures_exists else "Binance XAUTUSDT futures was not found.",
    }
    _XAUT_VALIDATION_CACHE[exchange] = (now, result)
    return result


def extract_open_trades(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("trades", "data", "result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def number_from(payload: Any, keys: tuple[str, ...]) -> float | None:
    if not isinstance(payload, dict):
        return None
    for key in keys:
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def find_recent_error(logs_payload: Any, error: str | None) -> str | None:
    if error:
        return error
    entries: list[Any] = []
    if isinstance(logs_payload, dict):
        entries = logs_payload.get("logs") or logs_payload.get("data") or []
    elif isinstance(logs_payload, list):
        entries = logs_payload
    for entry in reversed(entries):
        text = " ".join(str(part) for part in entry) if isinstance(entry, list) else str(entry)
        if "ERROR" in text or "WARNING" in text:
            return text[-240:]
    return None


def recent_trade(open_trades: list[dict[str, Any]], trades_payload: Any) -> str:
    history: list[dict[str, Any]] = []
    if isinstance(trades_payload, dict):
        value = trades_payload.get("trades") or trades_payload.get("data")
        if isinstance(value, list):
            history = [item for item in value if isinstance(item, dict)]
    if history:
        trade = history[0]
        pair = trade.get("pair", "unknown")
        direction = trade.get("trade_direction") or ("short" if trade.get("is_short") else "long")
        profit = trade.get("close_profit") or trade.get("profit_ratio")
        return f"{pair} {direction} profit={profit}" if profit is not None else f"{pair} {direction}"
    if open_trades:
        trade = open_trades[0]
        pair = trade.get("pair", "unknown")
        direction = trade.get("trade_direction") or ("short" if trade.get("is_short") else "long")
        return f"open {pair} {direction}"
    return "none"


def parse_trade_time(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        normalized = text.replace("Z", "+00:00")
        if "." in normalized and "+" not in normalized and normalized.count(":") >= 2:
            normalized = normalized.split(".", 1)[0]
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def iso_or_none(value: Any) -> str | None:
    parsed = parse_trade_time(value)
    return parsed.isoformat() if parsed else None


def is_today(value: str | None) -> bool:
    parsed = parse_trade_time(value)
    if parsed is None:
        return False
    return parsed.astimezone(timezone.utc).date() == datetime.now(timezone.utc).date()


def extract_trade_history(trades_payload: Any) -> list[dict[str, Any]]:
    if not isinstance(trades_payload, dict):
        return []
    value = trades_payload.get("trades") or trades_payload.get("data") or []
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def trade_record(trade: dict[str, Any]) -> dict[str, Any]:
    open_time = (
        trade.get("open_date")
        or trade.get("open_date_utc")
        or trade.get("open_timestamp")
        or trade.get("open_date_hum")
    )
    close_time = (
        trade.get("close_date")
        or trade.get("close_date_utc")
        or trade.get("close_timestamp")
        or trade.get("close_date_hum")
    )
    side = trade.get("trade_direction") or ("short" if trade.get("is_short") else "long")
    entry_price = first_number(trade, ("open_rate", "entry_price", "open_rate_requested"))
    exit_price = first_number(trade, ("close_rate", "exit_price", "close_rate_requested"))
    simulated_pnl = first_number(
        trade,
        ("close_profit_abs", "profit_abs", "realized_profit", "profit_closed_abs"),
    )
    if simulated_pnl is None:
        ratio = first_number(trade, ("close_profit", "profit_ratio"))
        stake = first_number(trade, ("stake_amount", "amount"))
        if ratio is not None and stake is not None:
            simulated_pnl = ratio * stake
    return {
        "id": trade.get("trade_id") or trade.get("id"),
        "pair": trade.get("pair"),
        "open_time": iso_or_none(open_time),
        "close_time": iso_or_none(close_time),
        "side": side,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "simulated_pnl": simulated_pnl,
        "exit_reason": trade.get("exit_reason") or trade.get("close_reason") or trade.get("sell_reason"),
        "is_open": bool(trade.get("is_open")),
    }


def trade_records(trades_payload: Any, limit: int = 8) -> list[dict[str, Any]]:
    records = [trade_record(trade) for trade in extract_trade_history(trades_payload)]
    records.sort(key=lambda item: item.get("close_time") or item.get("open_time") or "", reverse=True)
    return records[:limit]


def consecutive_losses(records: list[dict[str, Any]]) -> int:
    losses = 0
    for record in records:
        pnl = safe_float(record.get("simulated_pnl"))
        if record.get("is_open") or pnl is None:
            continue
        if pnl < 0:
            losses += 1
            continue
        break
    return losses


def trade_extreme(records: list[dict[str, Any]], best: bool) -> dict[str, Any] | None:
    closed = [
        record
        for record in records
        if not record.get("is_open") and safe_float(record.get("simulated_pnl")) is not None
    ]
    if not closed:
        return None
    return max(closed, key=lambda item: safe_float(item.get("simulated_pnl")) or 0) if best else min(
        closed,
        key=lambda item: safe_float(item.get("simulated_pnl")) or 0,
    )


def current_daily_loss(today_pnl: float | None) -> float:
    if today_pnl is None or today_pnl >= 0:
        return 0.0
    return abs(today_pnl)


def summarize_bot(bot: BotConfig, kill_switch_active: bool, validation: dict[str, Any]) -> dict[str, Any]:
    ping, ping_error = get_json(f"{bot.api_url.rstrip('/')}/api/v1/ping")
    online = isinstance(ping, dict) and ping.get("status") == "pong"

    config, config_error = bot_endpoint(bot, "/api/v1/show_config") if online else ({}, ping_error)
    status, status_error = bot_endpoint(bot, "/api/v1/status") if online else ([], ping_error)
    profit, profit_error = bot_endpoint(bot, "/api/v1/profit") if online else ({}, ping_error)
    daily, daily_error = bot_endpoint(bot, "/api/v1/daily?timescale=7") if online else ({}, ping_error)
    trades, trades_error = bot_endpoint(bot, "/api/v1/trades?limit=20&offset=0") if online else ({}, ping_error)
    logs, logs_error = bot_endpoint(bot, "/api/v1/logs?limit=50") if online else ({}, ping_error)

    open_trades = extract_open_trades(status)
    dry_run = bool(config.get("dry_run")) if isinstance(config, dict) else None
    pair = bot.pair
    if isinstance(config, dict):
        exchange_config = config.get("exchange")
        if isinstance(exchange_config, dict):
            whitelist = exchange_config.get("pair_whitelist")
            if isinstance(whitelist, list) and whitelist:
                pair = whitelist[0]

    current_pnl = number_from(
        profit,
        ("profit_all_coin", "profit_closed_coin", "profit_all_abs", "profit_closed_abs"),
    )
    today_pnl = number_from(
        profit,
        ("profit_today_abs", "profit_today_coin", "today_profit_abs", "today_profit"),
    )
    if today_pnl is None and isinstance(daily, dict):
        rows = daily.get("data") or daily.get("days") or []
        if isinstance(rows, list) and rows:
            today_pnl = number_from(rows[-1], ("abs_profit", "profit_abs", "profit"))

    recent_error = find_recent_error(logs, config_error or status_error or profit_error or daily_error or trades_error or logs_error)
    risk_status = "blocked" if kill_switch_active else "ok"
    if not online or dry_run is not True or recent_error:
        risk_status = "attention" if not kill_switch_active else "blocked"

    market = binance_market_snapshot(pair)
    records = trade_records(trades)
    losses = consecutive_losses(records)
    max_drawdown = number_from(
        profit,
        ("max_drawdown", "max_drawdown_abs", "max_drawdown_account", "max_drawdown_abs_account"),
    )
    risk = {
        "max_leverage": MAX_LEVERAGE,
        "max_position_size_pct": MAX_POSITION_SIZE_PCT,
        "daily_loss_limit_pct": DAILY_LOSS_LIMIT_PCT,
        "current_daily_simulated_loss": current_daily_loss(today_pnl),
        "consecutive_losses": losses,
        "consecutive_loss_limit": CONSECUTIVE_LOSS_LIMIT,
        "kill_switch_active": kill_switch_active,
        "risk_status": risk_status,
    }

    result = {
        "key": bot.key,
        "label": bot.label,
        "online": online,
        "dry_run": dry_run,
        "pair": pair,
        "open_trades": len(open_trades),
        "current_pnl": current_pnl,
        "today_pnl": today_pnl,
        "recent_trade": recent_trade(open_trades, trades),
        "recent_error": recent_error,
        "risk_status": risk_status,
        "kill_switch_active": kill_switch_active,
        "api_url": bot.api_url,
        "local_port": bot.port,
        "market": market,
        "strategy_indicators": market.get("indicators", {}),
        "strategy_decision": market.get("strategy", {}),
        "simulated_trades": records,
        "closed_trades_today": sum(1 for record in records if not record.get("is_open") and is_today(record.get("close_time"))),
        "best_simulated_trade": trade_extreme(records, best=True),
        "worst_simulated_trade": trade_extreme(records, best=False),
        "max_drawdown": max_drawdown,
        "risk": risk,
    }
    if bot.validation_gated:
        result["xaut_validation"] = validation
        result["xaut_started"] = online
        result["xaut_market"] = xaut_external_prices()
        if not online:
            result["xaut_not_started_reason"] = (
                None
                if validation.get("can_enable_bot")
                else validation.get("reason") or "XAUT futures validation did not pass."
            )
    return result


def build_summary() -> dict[str, Any]:
    kill_switch_active = KILL_SWITCH_PATH.exists()
    exchange = _env("XAUT_EXCHANGE_NAME", _env("EXCHANGE_NAME", "binance")).lower()
    validation = xaut_validation(exchange)
    bots = [summarize_bot(bot, kill_switch_active, validation) for bot in bot_configs()]
    total_today = sum(bot["today_pnl"] or 0 for bot in bots)
    total_simulated_pnl = sum(bot["current_pnl"] or 0 for bot in bots)
    total_open = sum(int(bot["open_trades"] or 0) for bot in bots)
    all_records = [
        record
        for bot in bots
        for record in bot.get("simulated_trades", [])
        if isinstance(record, dict)
    ]
    any_risk = any(bot["risk_status"] != "ok" for bot in bots)
    any_offline = any(not bot["online"] for bot in bots if bot["key"] != "xaut" or validation.get("can_enable_bot"))
    any_error = any(bot["recent_error"] for bot in bots)
    dry_run_values = [bot["dry_run"] for bot in bots if bot["online"]]
    drawdowns = [safe_float(bot.get("max_drawdown")) for bot in bots if safe_float(bot.get("max_drawdown")) is not None]
    overview = {
        "bot_count": len(bots),
        "online_count": sum(1 for bot in bots if bot["online"]),
        "dry_run_all_online": bool(dry_run_values) and all(value is True for value in dry_run_values),
        "total_simulated_pnl": total_simulated_pnl,
        "today_total_pnl": total_today,
        "total_open_trades": total_open,
        "total_closed_trades_today": sum(
            1 for record in all_records if not record.get("is_open") and is_today(record.get("close_time"))
        ),
        "best_simulated_trade": trade_extreme(all_records, best=True),
        "worst_simulated_trade": trade_extreme(all_records, best=False),
        "max_drawdown": max(drawdowns) if drawdowns else None,
        "any_risk_triggered": any_risk,
        "any_offline": any_offline,
        "any_error": any_error,
        "kill_switch_active": kill_switch_active,
        "updated_at": int(time.time()),
    }
    return {"overview": overview, "bots": bots, "market_recorder": load_market_recorder_state(), "read_only": True}


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "QuantHedgeDashboard/1.0"

    def do_GET(self) -> None:
        parsed = parse.urlparse(self.path)
        if parsed.path == "/api/summary":
            self.send_json(build_summary())
            return
        if parsed.path == "/api/market-recorder":
            self.send_json(load_market_recorder_state())
            return
        if parsed.path in {"/", "/index.html"}:
            self.send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/styles.css":
            self.send_file(STATIC_DIR / "styles.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self.send_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "Dashboard is read-only")

    def do_PUT(self) -> None:
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "Dashboard is read-only")

    def do_DELETE(self) -> None:
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "Dashboard is read-only")

    def send_json(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path: Path, content_type: str) -> None:
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    port = int(os.getenv("DASHBOARD_PORT", "8090"))
    httpd = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"read-only dashboard listening on {host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
