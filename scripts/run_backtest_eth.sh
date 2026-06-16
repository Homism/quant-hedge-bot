#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DAYS="${DAYS:-365}"
TIMEFRAME="${TIMEFRAME:-1h}"
PAIR="ETH/USDT:USDT"

mkdir -p user_data_eth/backtest_results user_data_eth/data

echo "Downloading missing ETH futures data if needed..."
docker compose run --rm freqtrade-eth \
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
  --strategy EthHedgeStrategy
  --enable-protections
  --export trades
  --backtest-directory /freqtrade/user_data/backtest_results
  --breakdown day month
)

if [[ -n "${TIMERANGE:-}" ]]; then
  BACKTEST_ARGS+=(--timerange "$TIMERANGE")
fi

echo "Running ETH backtest..."
docker compose run --rm freqtrade-eth "${BACKTEST_ARGS[@]}"

echo
echo "ETH backtest complete. Results are in user_data_eth/backtest_results."
