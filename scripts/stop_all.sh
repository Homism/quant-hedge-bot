#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

docker compose stop freqtrade-btc freqtrade-eth
echo "Stopped BTC and ETH dry-run services."
