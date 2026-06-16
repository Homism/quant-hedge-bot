#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

docker compose ps
echo
echo "Recent BTC logs:"
docker compose logs --tail=25 freqtrade-btc || true
echo
echo "Recent ETH logs:"
docker compose logs --tail=25 freqtrade-eth || true
echo
echo "Recent SOL logs:"
docker compose logs --tail=25 freqtrade-sol || true
echo
echo "Optional XAUT status is validation-gated. Run scripts/check_xaut_markets.sh before enabling it."
