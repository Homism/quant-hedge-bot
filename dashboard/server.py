from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
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
_XAUT_VALIDATION_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


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


def summarize_bot(bot: BotConfig, kill_switch_active: bool, validation: dict[str, Any]) -> dict[str, Any]:
    ping, ping_error = get_json(f"{bot.api_url.rstrip('/')}/api/v1/ping")
    online = isinstance(ping, dict) and ping.get("status") == "pong"

    config, config_error = bot_endpoint(bot, "/api/v1/show_config") if online else ({}, ping_error)
    status, status_error = bot_endpoint(bot, "/api/v1/status") if online else ([], ping_error)
    profit, profit_error = bot_endpoint(bot, "/api/v1/profit") if online else ({}, ping_error)
    daily, daily_error = bot_endpoint(bot, "/api/v1/daily?timescale=7") if online else ({}, ping_error)
    trades, trades_error = bot_endpoint(bot, "/api/v1/trades?limit=1&offset=0") if online else ({}, ping_error)
    logs, logs_error = bot_endpoint(bot, "/api/v1/logs?limit=50") if online else ({}, ping_error)

    open_trades = extract_open_trades(status)
    dry_run = bool(config.get("dry_run")) if isinstance(config, dict) else None
    pair = bot.pair
    if isinstance(config, dict):
        pair = (
            config.get("exchange", {}).get("pair_whitelist", [bot.pair])[0]
            if isinstance(config.get("exchange"), dict)
            else bot.pair
        )

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
    }
    if bot.validation_gated:
        result["xaut_validation"] = validation
        result["xaut_started"] = online
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
    total_open = sum(int(bot["open_trades"] or 0) for bot in bots)
    any_risk = any(bot["risk_status"] != "ok" for bot in bots)
    any_offline = any(not bot["online"] for bot in bots if bot["key"] != "xaut" or validation.get("can_enable_bot"))
    any_error = any(bot["recent_error"] for bot in bots)
    dry_run_values = [bot["dry_run"] for bot in bots if bot["online"]]
    overview = {
        "bot_count": len(bots),
        "online_count": sum(1 for bot in bots if bot["online"]),
        "dry_run_all_online": bool(dry_run_values) and all(value is True for value in dry_run_values),
        "today_total_pnl": total_today,
        "total_open_trades": total_open,
        "any_risk_triggered": any_risk,
        "any_offline": any_offline,
        "any_error": any_error,
        "kill_switch_active": kill_switch_active,
        "updated_at": int(time.time()),
    }
    return {"overview": overview, "bots": bots, "read_only": True}


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "QuantHedgeDashboard/1.0"

    def do_GET(self) -> None:
        parsed = parse.urlparse(self.path)
        if parsed.path == "/api/summary":
            self.send_json(build_summary())
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
