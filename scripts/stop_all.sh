#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

docker compose --profile xaut-validated stop freqtrade-btc freqtrade-eth freqtrade-sol freqtrade-xaut
echo "Stopped BTC, ETH, SOL, and optional validation-gated XAUT dry-run services."
