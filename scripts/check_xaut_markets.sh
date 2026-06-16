#!/usr/bin/env bash
set -euo pipefail

REQUIRE_FUTURES=false
for arg in "$@"; do
  case "$arg" in
    --require-futures)
      REQUIRE_FUTURES=true
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 64
      ;;
  esac
done

EXCHANGE="${XAUT_EXCHANGE_NAME:-${EXCHANGE_NAME:-binance}}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

fetch() {
  local url="$1"
  local target="$2"
  if ! curl -fsSL "$url" -o "$target"; then
    printf '{"request_failed": true, "url": "%s"}\n' "$url" > "$target"
  fi
}

case "$EXCHANGE" in
  binance)
    SPOT_URL="https://api.binance.com/api/v3/exchangeInfo?symbol=XAUTUSDT"
    FUTURES_URL="https://fapi.binance.com/fapi/v1/exchangeInfo"
    fetch "$SPOT_URL" "$TMP_DIR/spot.json"
    fetch "$FUTURES_URL" "$TMP_DIR/futures.json"
    python3 - "$TMP_DIR/spot.json" "$TMP_DIR/futures.json" "$REQUIRE_FUTURES" <<'PY'
import json
import sys
from pathlib import Path

spot_path, futures_path, require_futures = sys.argv[1], sys.argv[2], sys.argv[3] == "true"

def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"parse_error": str(exc)}

spot = load(spot_path)
futures = load(futures_path)

spot_symbols = spot.get("symbols", [])
spot_matches = [item for item in spot_symbols if item.get("symbol") == "XAUTUSDT"]
spot_exists = any(item.get("status") == "TRADING" for item in spot_matches)

futures_symbols = futures.get("symbols", [])
futures_matches = [
    item
    for item in futures_symbols
    if item.get("symbol") == "XAUTUSDT" and item.get("status") == "TRADING"
]
futures_exists = any("PERPETUAL" in str(item.get("contractType", "")) for item in futures_matches)

print("XAUT market validation")
print("exchange: binance")
print("spot pair XAUT/USDT exists:", "yes" if spot_exists else "no")
print("futures pair XAUT/USDT:USDT exists:", "yes" if futures_exists else "no")
print("can enable XAUT hedge bot:", "yes" if futures_exists else "no")
if not futures_exists:
    print("reason: XAUT futures pair was not found in Binance USDT futures exchangeInfo.")
    print("action: keep XAUT as watcher only; do not start freqtrade-xaut.")
sys.exit(0 if (futures_exists or not require_futures) else 2)
PY
    ;;
  okx)
    SPOT_URL="https://www.okx.com/api/v5/public/instruments?instType=SPOT&instId=XAUT-USDT"
    FUTURES_URL="https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=XAUT-USDT-SWAP"
    fetch "$SPOT_URL" "$TMP_DIR/spot.json"
    fetch "$FUTURES_URL" "$TMP_DIR/futures.json"
    python3 - "$TMP_DIR/spot.json" "$TMP_DIR/futures.json" "$REQUIRE_FUTURES" <<'PY'
import json
import sys
from pathlib import Path

spot_path, futures_path, require_futures = sys.argv[1], sys.argv[2], sys.argv[3] == "true"

def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"parse_error": str(exc)}

spot = load(spot_path)
futures = load(futures_path)

spot_exists = any(item.get("instId") == "XAUT-USDT" and item.get("state") == "live" for item in spot.get("data", []))
futures_exists = any(
    item.get("instId") == "XAUT-USDT-SWAP" and item.get("state") == "live"
    for item in futures.get("data", [])
)

print("XAUT market validation")
print("exchange: okx")
print("spot pair XAUT/USDT exists:", "yes" if spot_exists else "no")
print("futures pair XAUT/USDT:USDT exists:", "yes" if futures_exists else "no")
print("can enable XAUT hedge bot:", "yes" if futures_exists else "no")
if not futures_exists:
    print("reason: XAUT-USDT-SWAP was not found in OKX public swap instruments.")
    print("action: keep XAUT as watcher only; do not start freqtrade-xaut.")
sys.exit(0 if (futures_exists or not require_futures) else 2)
PY
    ;;
  *)
    echo "XAUT market validation"
    echo "exchange: $EXCHANGE"
    echo "spot pair XAUT/USDT exists: unknown"
    echo "futures pair XAUT/USDT:USDT exists: unknown"
    echo "can enable XAUT hedge bot: no"
    echo "reason: unsupported exchange template. Supported values: binance, okx."
    $REQUIRE_FUTURES && exit 2
    ;;
esac
