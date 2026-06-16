#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p user_data_btc/logs user_data_eth/logs user_data_sol/logs user_data_xaut/logs runtime

echo "Starting BTC, ETH, and SOL Freqtrade bots in forced dry-run mode..."
docker compose up -d freqtrade-btc freqtrade-eth freqtrade-sol

XAUT_STARTED=false
echo
echo "Checking XAUT futures market before any XAUT bot start..."
if ./scripts/check_xaut_markets.sh --require-futures; then
  echo "XAUT futures validation passed. Starting validation-gated XAUT dry-run bot..."
  docker compose --profile xaut-validated up -d freqtrade-xaut
  XAUT_STARTED=true
else
  echo "XAUT futures validation did not pass. XAUT bot is not started."
fi

echo
echo "Dry-run services started."
echo "BTC Web UI: http://127.0.0.1:8081"
echo "ETH Web UI: http://127.0.0.1:8082"
echo "SOL Web UI: http://127.0.0.1:8083"
if [[ "$XAUT_STARTED" == "true" ]]; then
  echo "XAUT Web UI: http://127.0.0.1:8084"
else
  echo "XAUT Web UI: not started; validation did not pass."
fi
echo
echo "On a VPS, use SSH tunnels instead of exposing ports publicly:"
echo "ssh -L 8081:127.0.0.1:8081 -L 8082:127.0.0.1:8082 -L 8083:127.0.0.1:8083 -L 8084:127.0.0.1:8084 user@your-vps"
