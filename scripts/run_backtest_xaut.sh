#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! ./scripts/check_xaut_markets.sh --require-futures; then
  echo
  echo "XAUT futures pair is not validated. Backtest is blocked."
  echo "Do not treat XAUT spot as a futures short hedge."
  exit 1
fi

DAYS="${DAYS:-365}"
TIMEFRAME="${TIMEFRAME:-1h}"
PAIR="XAUT/USDT:USDT"

mkdir -p user_data_xaut/backtest_results user_data_xaut/data

echo "Downloading missing XAUT futures data if needed..."
docker compose --profile xaut-validated run --rm freqtrade-xaut \
  download-data \
  --config /freqtrade/config.json \
  --userdir /freqtrade/user_data \
  --pairs "$PAIR" \
  --exchange "${XAUT_EXCHANGE_NAME:-${EXCHANGE_NAME:-binance}}" \
  --days "$DAYS" \
  --timeframes "$TIMEFRAME" \
  --trading-mode futures

BACKTEST_ARGS=(
  backtesting
  --config /freqtrade/config.json
  --userdir /freqtrade/user_data
  --strategy XautHedgeStrategy
  --enable-protections
  --export trades
  --backtest-directory /freqtrade/user_data/backtest_results
  --breakdown day month
)

if [[ -n "${TIMERANGE:-}" ]]; then
  BACKTEST_ARGS+=(--timerange "$TIMERANGE")
fi

echo "Running XAUT backtest..."
docker compose --profile xaut-validated run --rm freqtrade-xaut "${BACKTEST_ARGS[@]}"

echo
echo "XAUT backtest complete. Results are in user_data_xaut/backtest_results."
