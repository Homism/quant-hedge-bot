#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

docker compose --profile xaut-validated stop freqtrade-btc freqtrade-eth freqtrade-sol freqtrade-xaut market-recorder dashboard
echo "Stopped BTC, ETH, SOL, optional validation-gated XAUT, market recorder, and Dashboard services."
