#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DAYS="${DAYS:-365}"
TIMEFRAME="${TIMEFRAME:-1h}"
PAIR="SOL/USDT:USDT"

mkdir -p user_data_sol/backtest_results user_data_sol/data

echo "Downloading missing SOL futures data if needed..."
docker compose run --rm freqtrade-sol \
  download-data \
  --config /freqtrade/config.json \
  --userdir /freqtrade/user_data \
  --pairs "$PAIR" \
  --exchange "${EXCHANGE_NAME:-binance}" \
  --days "$DAYS" \
  --timeframes "$TIMEFRAME" \
  --trading-mode futures

BACKTEST_ARGS=(
  backtesting
  --config /freqtrade/config.json
  --userdir /freqtrade/user_data
  --strategy SolHedgeStrategy
  --enable-protections
  --export trades
  --backtest-directory /freqtrade/user_data/backtest_results
  --breakdown day month
)

if [[ -n "${TIMERANGE:-}" ]]; then
  BACKTEST_ARGS+=(--timerange "$TIMERANGE")
fi

echo "Running SOL backtest..."
docker compose run --rm freqtrade-sol "${BACKTEST_ARGS[@]}"

echo
echo "SOL backtest complete. Results are in user_data_sol/backtest_results."
