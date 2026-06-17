from __future__ import annotations

import base64
import calendar
import gzip
import hashlib
import json
import os
import signal
import socket
import ssl
import struct
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


BINANCE_FUTURES_WS = "wss://fstream.binance.com/ws/{symbol_lower}@bookTicker"
OKX_PUBLIC_WS = "wss://ws.okx.com:8443/ws/v5/public"
DEFAULT_SYMBOL = "XAUTUSDT"
DEFAULT_OKX_INST_ID = "XAUT-USDT"
DEFAULT_INTERVAL_MS = 200
DEFAULT_MAX_SNAPSHOT_BYTES = 100 * 1024 * 1024
DEFAULT_RETENTION_HOURS = 72
RETENTION_MAINTENANCE_INTERVAL_MS = 60_000


def now_ms() -> int:
    return int(time.time() * 1000)


def iso_from_ms(value: int | None) -> str | None:
    if value is None:
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(value / 1000))


def hour_bucket_from_ms(value: int) -> str:
    return time.strftime("%Y-%m-%d_%H", time.gmtime(value / 1000))


def asset_prefix(symbol: str) -> str:
    cleaned = "".join(ch for ch in symbol.lower() if ch.isalnum())
    return cleaned.removesuffix("usdt") or cleaned or "market"


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


@dataclass
class Quote:
    source: str
    symbol: str
    bid: float | None
    ask: float | None
    bid_size: float | None
    ask_size: float | None
    mid: float | None
    spread: float | None
    spread_pct: float | None
    exchange_ts_ms: int | None
    recv_ts_ms: int
    latency_ms: int | None
    sequence: int | None = None
    raw_type: str | None = None


def make_quote(
    *,
    source: str,
    symbol: str,
    bid: Any,
    ask: Any,
    bid_size: Any,
    ask_size: Any,
    exchange_ts_ms: Any,
    recv_ts_ms: int | None = None,
    sequence: Any = None,
    raw_type: str | None = None,
) -> Quote:
    recv = recv_ts_ms or now_ms()
    bid_value = safe_float(bid)
    ask_value = safe_float(ask)
    mid = (bid_value + ask_value) / 2 if bid_value is not None and ask_value is not None else None
    spread = ask_value - bid_value if bid_value is not None and ask_value is not None else None
    spread_pct = (spread / mid) * 100 if spread is not None and mid not in (None, 0) else None
    exchange_ts = safe_int(exchange_ts_ms)
    latency = recv - exchange_ts if exchange_ts is not None else None
    return Quote(
        source=source,
        symbol=symbol,
        bid=bid_value,
        ask=ask_value,
        bid_size=safe_float(bid_size),
        ask_size=safe_float(ask_size),
        mid=mid,
        spread=spread,
        spread_pct=spread_pct,
        exchange_ts_ms=exchange_ts,
        recv_ts_ms=recv,
        latency_ms=latency,
        sequence=safe_int(sequence),
        raw_type=raw_type,
    )


def quote_from_binance_book_ticker(payload: dict[str, Any], recv_ts_ms: int | None = None) -> Quote | None:
    if not isinstance(payload, dict) or payload.get("e") != "bookTicker":
        return None
    return make_quote(
        source="binance_futures",
        symbol=str(payload.get("s") or ""),
        bid=payload.get("b"),
        ask=payload.get("a"),
        bid_size=payload.get("B"),
        ask_size=payload.get("A"),
        exchange_ts_ms=payload.get("E") or payload.get("T"),
        recv_ts_ms=recv_ts_ms,
        sequence=payload.get("u"),
        raw_type=payload.get("e"),
    )


def quote_from_okx_books5(payload: dict[str, Any], recv_ts_ms: int | None = None) -> Quote | None:
    if not isinstance(payload, dict):
        return None
    arg = payload.get("arg")
    if not isinstance(arg, dict) or arg.get("channel") != "books5":
        return None
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        return None
    row = rows[0]
    if not isinstance(row, dict):
        return None
    bids = row.get("bids")
    asks = row.get("asks")
    if not isinstance(bids, list) or not bids or not isinstance(asks, list) or not asks:
        return None
    bid = bids[0] if isinstance(bids[0], list) else []
    ask = asks[0] if isinstance(asks[0], list) else []
    if len(bid) < 2 or len(ask) < 2:
        return None
    return make_quote(
        source="okx_public",
        symbol=str(arg.get("instId") or ""),
        bid=bid[0],
        ask=ask[0],
        bid_size=bid[1],
        ask_size=ask[1],
        exchange_ts_ms=row.get("ts"),
        recv_ts_ms=recv_ts_ms,
        sequence=row.get("seqId"),
        raw_type="books5",
    )


def cross_spread(binance: Quote | None, okx: Quote | None) -> dict[str, Any]:
    if not binance or not okx:
        return {
            "available": False,
            "reason": "waiting_for_both_sources",
        }

    mid_abs = None
    mid_pct = None
    if binance.mid is not None and okx.mid not in (None, 0):
        mid_abs = binance.mid - okx.mid
        mid_pct = (mid_abs / okx.mid) * 100

    sell_binance_buy_okx = None
    sell_binance_buy_okx_pct = None
    if binance.bid is not None and okx.ask not in (None, 0):
        sell_binance_buy_okx = binance.bid - okx.ask
        sell_binance_buy_okx_pct = (sell_binance_buy_okx / okx.ask) * 100

    sell_okx_buy_binance = None
    sell_okx_buy_binance_pct = None
    if okx.bid is not None and binance.ask not in (None, 0):
        sell_okx_buy_binance = okx.bid - binance.ask
        sell_okx_buy_binance_pct = (sell_okx_buy_binance / binance.ask) * 100

    candidates = {
        "sell_binance_buy_okx": sell_binance_buy_okx,
        "sell_okx_buy_binance": sell_okx_buy_binance,
    }
    positive = {key: value for key, value in candidates.items() if value is not None and value > 0}
    best_direction = max(positive, key=positive.get) if positive else "none"
    best_edge = positive.get(best_direction)

    return {
        "available": True,
        "symbol": "XAUT",
        "binance_mid": binance.mid,
        "okx_mid": okx.mid,
        "mid_spread_abs": mid_abs,
        "mid_spread_pct": mid_pct,
        "sell_binance_buy_okx_abs": sell_binance_buy_okx,
        "sell_binance_buy_okx_pct": sell_binance_buy_okx_pct,
        "sell_okx_buy_binance_abs": sell_okx_buy_binance,
        "sell_okx_buy_binance_pct": sell_okx_buy_binance_pct,
        "best_direction": best_direction,
        "best_edge_abs": best_edge,
        "binance_latency_ms": binance.latency_ms,
        "okx_latency_ms": okx.latency_ms,
        "captured_at_ms": max(binance.recv_ts_ms, okx.recv_ts_ms),
        "captured_at": iso_from_ms(max(binance.recv_ts_ms, okx.recv_ts_ms)),
    }


class SharedBook:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._quotes: dict[str, Quote] = {}
        self._status: dict[str, dict[str, Any]] = {
            "binance_futures": {"connected": False, "status": "starting", "reconnects": 0},
            "okx_public": {"connected": False, "status": "starting", "reconnects": 0},
        }

    def set_status(self, source: str, **updates: Any) -> None:
        with self._lock:
            current = self._status.setdefault(source, {})
            current.update(updates)
            current["updated_at_ms"] = now_ms()
            current["updated_at"] = iso_from_ms(current["updated_at_ms"])

    def mark_reconnect(self, source: str, error: str) -> None:
        with self._lock:
            current = self._status.setdefault(source, {})
            current["connected"] = False
            current["status"] = "reconnecting"
            current["last_error"] = error[-300:]
            current["reconnects"] = int(current.get("reconnects") or 0) + 1
            current["updated_at_ms"] = now_ms()
            current["updated_at"] = iso_from_ms(current["updated_at_ms"])

    def update_quote(self, quote: Quote) -> None:
        with self._lock:
            self._quotes[quote.source] = quote
            current = self._status.setdefault(quote.source, {})
            current.update(
                {
                    "connected": True,
                    "status": "connected",
                    "last_message_ms": quote.recv_ts_ms,
                    "last_message_at": iso_from_ms(quote.recv_ts_ms),
                    "last_latency_ms": quote.latency_ms,
                    "last_error": None,
                }
            )

    def snapshot(self, *, symbol: str, okx_inst_id: str, interval_ms: int, snapshots_written: int, started_at_ms: int) -> dict[str, Any]:
        captured = now_ms()
        with self._lock:
            quotes = dict(self._quotes)
            statuses = json.loads(json.dumps(self._status))
        binance = quotes.get("binance_futures")
        okx = quotes.get("okx_public")
        quote_payload = {source: asdict(quote) for source, quote in quotes.items()}
        for source, status in statuses.items():
            last_message_ms = status.get("last_message_ms")
            status["last_message_age_ms"] = captured - int(last_message_ms) if last_message_ms else None
        return {
            "service": "market_recorder",
            "read_only": True,
            "trading_enabled": False,
            "api_key_required": False,
            "order_actions": False,
            "symbol": symbol,
            "okx_inst_id": okx_inst_id,
            "interval_ms": interval_ms,
            "started_at_ms": started_at_ms,
            "started_at": iso_from_ms(started_at_ms),
            "updated_at_ms": captured,
            "updated_at": iso_from_ms(captured),
            "snapshots_written": snapshots_written,
            "sources": statuses,
            "quotes": quote_payload,
            "xaut_spread": cross_spread(binance, okx),
        }


class WebSocketClient:
    def __init__(self, url: str, *, name: str, timeout: float = 10) -> None:
        self.url = url
        self.name = name
        self.timeout = timeout
        self.sock: ssl.SSLSocket | socket.socket | None = None

    def connect(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"wss", "ws"}:
            raise ValueError(f"Unsupported websocket scheme: {parsed.scheme}")
        host = parsed.hostname
        if host is None:
            raise ValueError("Websocket URL has no host")
        port = parsed.port or (443 if parsed.scheme == "wss" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        raw_sock = socket.create_connection((host, port), timeout=self.timeout)
        if parsed.scheme == "wss":
            context = ssl.create_default_context()
            sock: ssl.SSLSocket | socket.socket = context.wrap_socket(raw_sock, server_hostname=host)
        else:
            sock = raw_sock
        sock.settimeout(1.0)

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "User-Agent: quant-hedge-market-recorder/1.0\r\n"
            "\r\n"
        )
        sock.sendall(request.encode("ascii"))
        header = self._read_http_header(sock)
        first_line = header.split("\r\n", 1)[0]
        if " 101 " not in first_line:
            raise ConnectionError(f"{self.name} websocket handshake failed: {first_line}")
        accept = self._header_value(header, "Sec-WebSocket-Accept")
        expected = base64.b64encode(hashlib.sha1(f"{key}258EAFA5-E914-47DA-95CA-C5AB0DC85B11".encode("ascii")).digest()).decode("ascii")
        if accept and accept != expected:
            raise ConnectionError(f"{self.name} websocket accept header mismatch")
        self.sock = sock

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def send_text(self, text: str) -> None:
        self._send_frame(0x1, text.encode("utf-8"))

    def send_pong(self, payload: bytes = b"") -> None:
        self._send_frame(0xA, payload)

    def recv_text(self) -> str:
        fragments: list[bytes] = []
        text_opcode_seen = False
        while True:
            fin, opcode, payload = self._read_frame()
            if opcode == 0x8:
                raise ConnectionError(f"{self.name} websocket closed by server")
            if opcode == 0x9:
                self.send_pong(payload)
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x1:
                text_opcode_seen = True
                fragments.append(payload)
            elif opcode == 0x0 and text_opcode_seen:
                fragments.append(payload)
            elif opcode == 0x2:
                fragments.append(payload)
            else:
                continue
            if fin:
                return b"".join(fragments).decode("utf-8")

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        if not self.sock:
            raise ConnectionError(f"{self.name} websocket is not connected")
        length = len(payload)
        first = 0x80 | opcode
        mask_bit = 0x80
        if length < 126:
            header = struct.pack("!BB", first, mask_bit | length)
        elif length <= 0xFFFF:
            header = struct.pack("!BBH", first, mask_bit | 126, length)
        else:
            header = struct.pack("!BBQ", first, mask_bit | 127, length)
        mask = os.urandom(4)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.sock.sendall(header + mask + masked)

    def _read_frame(self) -> tuple[bool, int, bytes]:
        if not self.sock:
            raise ConnectionError(f"{self.name} websocket is not connected")
        head = self._read_exact(2)
        first, second = head[0], head[1]
        fin = bool(first & 0x80)
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        mask = self._read_exact(4) if masked else b""
        payload = self._read_exact(length) if length else b""
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return fin, opcode, payload

    def _read_exact(self, length: int) -> bytes:
        if not self.sock:
            raise ConnectionError(f"{self.name} websocket is not connected")
        chunks = bytearray()
        while len(chunks) < length:
            chunk = self.sock.recv(length - len(chunks))
            if not chunk:
                raise ConnectionError(f"{self.name} websocket connection ended")
            chunks.extend(chunk)
        return bytes(chunks)

    @staticmethod
    def _read_http_header(sock: ssl.SSLSocket | socket.socket) -> str:
        data = bytearray()
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(1)
            if not chunk:
                raise ConnectionError("websocket handshake ended before headers")
            data.extend(chunk)
            if len(data) > 16384:
                raise ConnectionError("websocket handshake header too large")
        return data.decode("iso-8859-1")

    @staticmethod
    def _header_value(header: str, name: str) -> str | None:
        prefix = f"{name.lower()}:"
        for line in header.split("\r\n")[1:]:
            if line.lower().startswith(prefix):
                return line.split(":", 1)[1].strip()
        return None


def binance_loop(shared: SharedBook, stop: threading.Event, *, symbol: str, url: str) -> None:
    while not stop.is_set():
        client = WebSocketClient(url, name="binance_futures")
        try:
            shared.set_status("binance_futures", connected=False, status="connecting", url=url, last_error=None)
            client.connect()
            shared.set_status("binance_futures", connected=True, status="connected", url=url, last_error=None)
            while not stop.is_set():
                try:
                    text = client.recv_text()
                except socket.timeout:
                    continue
                recv = now_ms()
                payload = json.loads(text)
                quote = quote_from_binance_book_ticker(payload, recv)
                if quote:
                    shared.update_quote(quote)
        except Exception as exc:
            shared.mark_reconnect("binance_futures", str(exc))
            print(f"[market-recorder] Binance reconnect: {exc}", flush=True)
            stop.wait(2)
        finally:
            client.close()


def okx_loop(shared: SharedBook, stop: threading.Event, *, inst_id: str, url: str) -> None:
    subscribe = {"op": "subscribe", "args": [{"channel": "books5", "instId": inst_id}]}
    while not stop.is_set():
        client = WebSocketClient(url, name="okx_public")
        try:
            shared.set_status("okx_public", connected=False, status="connecting", url=url, inst_id=inst_id, last_error=None)
            client.connect()
            client.send_text(json.dumps(subscribe, separators=(",", ":")))
            shared.set_status("okx_public", connected=True, status="subscribed", url=url, inst_id=inst_id, last_error=None)
            last_ping = now_ms()
            while not stop.is_set():
                if now_ms() - last_ping > 20000:
                    client.send_text("ping")
                    last_ping = now_ms()
                try:
                    text = client.recv_text()
                except socket.timeout:
                    continue
                recv = now_ms()
                if text == "pong":
                    shared.set_status("okx_public", connected=True, status="connected", last_pong_ms=recv, last_pong_at=iso_from_ms(recv))
                    continue
                payload = json.loads(text)
                if payload.get("event") == "error":
                    raise ConnectionError(json.dumps(payload, ensure_ascii=False))
                quote = quote_from_okx_books5(payload, recv)
                if quote:
                    shared.update_quote(quote)
        except Exception as exc:
            shared.mark_reconnect("okx_public", str(exc))
            print(f"[market-recorder] OKX reconnect: {exc}", flush=True)
            stop.wait(2)
        finally:
            client.close()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)


def append_snapshot(path: Path, payload: dict[str, Any], *, max_bytes: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > max_bytes:
        rotated = path.with_suffix(f"{path.suffix}.1")
        if rotated.exists():
            rotated.unlink()
        path.replace(rotated)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def hourly_snapshot_path(directory: Path, symbol: str, timestamp_ms: int) -> Path:
    return directory / f"{asset_prefix(symbol)}_{hour_bucket_from_ms(timestamp_ms)}.jsonl"


def append_hourly_snapshot(directory: Path, symbol: str, payload: dict[str, Any]) -> Path:
    timestamp_ms = safe_int(payload.get("updated_at_ms")) or now_ms()
    path = hourly_snapshot_path(directory, symbol, timestamp_ms)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    return path


def parse_hourly_file(path: Path, prefix: str) -> int | None:
    name = path.name
    suffix = ".jsonl.gz" if name.endswith(".jsonl.gz") else ".jsonl" if name.endswith(".jsonl") else None
    if suffix is None or not name.startswith(f"{prefix}_"):
        return None
    bucket = name.removeprefix(f"{prefix}_").removesuffix(suffix)
    try:
        parsed = time.strptime(bucket, "%Y-%m-%d_%H")
    except ValueError:
        return None
    return calendar.timegm(parsed) * 1000


def compress_file(path: Path) -> Path:
    gz_path = path.with_suffix(f"{path.suffix}.gz")
    if gz_path.exists():
        path.unlink()
        return gz_path
    tmp_path = gz_path.with_suffix(f"{gz_path.suffix}.tmp")
    with path.open("rb") as source, gzip.open(tmp_path, "wb", compresslevel=6) as target:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            target.write(chunk)
    tmp_path.replace(gz_path)
    path.unlink()
    return gz_path


def retention_summary(directory: Path, symbol: str) -> dict[str, Any]:
    prefix = asset_prefix(symbol)
    files: list[dict[str, Any]] = []
    if directory.exists():
        for path in directory.iterdir():
            hour_ms = parse_hourly_file(path, prefix)
            if hour_ms is None or not path.is_file():
                continue
            files.append(
                {
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                    "hour_ms": hour_ms,
                    "hour": iso_from_ms(hour_ms),
                    "compressed": path.name.endswith(".gz"),
                }
            )
    files.sort(key=lambda item: item["hour_ms"])
    unique_hours = sorted({item["hour_ms"] for item in files})
    total_bytes = sum(int(item["size_bytes"]) for item in files)
    return {
        "hourly_dir": str(directory),
        "file_count": len(files),
        "compressed_file_count": sum(1 for item in files if item["compressed"]),
        "uncompressed_file_count": sum(1 for item in files if not item["compressed"]),
        "retained_hours": len(unique_hours),
        "oldest_hour": iso_from_ms(unique_hours[0]) if unique_hours else None,
        "newest_hour": iso_from_ms(unique_hours[-1]) if unique_hours else None,
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / 1024 / 1024, 3),
        "latest_files": files[-5:],
    }


def maintain_hourly_retention(directory: Path, symbol: str, *, retention_hours: int, current_timestamp_ms: int) -> dict[str, Any]:
    prefix = asset_prefix(symbol)
    current_hour = hour_bucket_from_ms(current_timestamp_ms)
    cutoff_ms = current_timestamp_ms - retention_hours * 60 * 60 * 1000
    directory.mkdir(parents=True, exist_ok=True)

    for path in list(directory.iterdir()):
        hour_ms = parse_hourly_file(path, prefix)
        if hour_ms is None or not path.is_file():
            continue
        if hour_ms < cutoff_ms:
            path.unlink()
            continue
        if path.name.endswith(".jsonl") and current_hour not in path.name:
            compress_file(path)
    summary = retention_summary(directory, symbol)
    summary["retention_hours_target"] = retention_hours
    summary["current_hour"] = current_hour
    summary["last_maintenance_at_ms"] = current_timestamp_ms
    summary["last_maintenance_at"] = iso_from_ms(current_timestamp_ms)
    return summary


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def main() -> int:
    symbol = os.getenv("RECORDER_SYMBOL", DEFAULT_SYMBOL).upper()
    okx_inst_id = os.getenv("RECORDER_OKX_INST_ID", DEFAULT_OKX_INST_ID).upper()
    interval_ms = max(50, env_int("RECORDER_SNAPSHOT_INTERVAL_MS", DEFAULT_INTERVAL_MS))
    state_path = Path(os.getenv("RECORDER_STATE_PATH", "/runtime/market_recorder/state.json"))
    snapshot_path = Path(os.getenv("RECORDER_SNAPSHOT_PATH", "/runtime/market_recorder/xaut_snapshots.jsonl"))
    hourly_dir = Path(os.getenv("RECORDER_HOURLY_DIR", "/runtime/market_recorder/hourly"))
    max_snapshot_bytes = env_int("RECORDER_MAX_SNAPSHOT_BYTES", DEFAULT_MAX_SNAPSHOT_BYTES)
    retention_hours = max(1, env_int("RECORDER_RETENTION_HOURS", DEFAULT_RETENTION_HOURS))
    binance_url = os.getenv("RECORDER_BINANCE_WS_URL", BINANCE_FUTURES_WS.format(symbol_lower=symbol.lower()))
    okx_url = os.getenv("RECORDER_OKX_WS_URL", OKX_PUBLIC_WS)

    stop = threading.Event()
    shared = SharedBook()
    started_at = now_ms()
    snapshots_written = 0
    last_retention_maintenance_ms = 0
    retention = retention_summary(hourly_dir, symbol)
    retention["retention_hours_target"] = retention_hours

    def request_stop(signum: int, _frame: Any) -> None:
        print(f"[market-recorder] Received signal {signum}, stopping.", flush=True)
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    threads = [
        threading.Thread(target=binance_loop, args=(shared, stop), kwargs={"symbol": symbol, "url": binance_url}, daemon=True),
        threading.Thread(target=okx_loop, args=(shared, stop), kwargs={"inst_id": okx_inst_id, "url": okx_url}, daemon=True),
    ]
    for thread in threads:
        thread.start()

    print(
        f"[market-recorder] Started read-only XAUT recorder interval={interval_ms}ms symbol={symbol} okx={okx_inst_id} retention_hours={retention_hours}",
        flush=True,
    )
    while not stop.is_set():
        cycle_started = time.monotonic()
        snapshots_written += 1
        current_ms = now_ms()
        if current_ms - last_retention_maintenance_ms >= RETENTION_MAINTENANCE_INTERVAL_MS:
            retention = maintain_hourly_retention(
                hourly_dir,
                symbol,
                retention_hours=retention_hours,
                current_timestamp_ms=current_ms,
            )
            last_retention_maintenance_ms = current_ms
        snapshot = shared.snapshot(
            symbol=symbol,
            okx_inst_id=okx_inst_id,
            interval_ms=interval_ms,
            snapshots_written=snapshots_written,
            started_at_ms=started_at,
        )
        snapshot["snapshot_path"] = str(snapshot_path)
        snapshot["hourly_dir"] = str(hourly_dir)
        snapshot["retention"] = retention
        hourly_path = append_hourly_snapshot(hourly_dir, symbol, snapshot)
        snapshot["hourly_snapshot_path"] = str(hourly_path)
        atomic_write_json(state_path, snapshot)
        append_snapshot(snapshot_path, snapshot, max_bytes=max_snapshot_bytes)
        elapsed = (time.monotonic() - cycle_started) * 1000
        stop.wait(max(0.001, (interval_ms - elapsed) / 1000))

    final_snapshot = shared.snapshot(
        symbol=symbol,
        okx_inst_id=okx_inst_id,
        interval_ms=interval_ms,
        snapshots_written=snapshots_written,
        started_at_ms=started_at,
    )
    final_snapshot["stopped_at_ms"] = now_ms()
    final_snapshot["stopped_at"] = iso_from_ms(final_snapshot["stopped_at_ms"])
    final_snapshot["status"] = "stopped"
    final_snapshot["hourly_dir"] = str(hourly_dir)
    final_snapshot["retention"] = retention_summary(hourly_dir, symbol)
    atomic_write_json(state_path, final_snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
