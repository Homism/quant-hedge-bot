#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p user_data_btc/logs user_data_eth/logs runtime

echo "Starting BTC and ETH Freqtrade bots in forced dry-run mode..."
docker compose up -d freqtrade-btc freqtrade-eth

echo
echo "Dry-run services started."
echo "BTC Web UI: http://127.0.0.1:8081"
echo "ETH Web UI: http://127.0.0.1:8082"
echo
echo "On a VPS, use SSH tunnels instead of exposing ports publicly:"
echo "ssh -L 8081:127.0.0.1:8081 -L 8082:127.0.0.1:8082 user@your-vps"
