#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p backups
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="backups/quant-hedge-dryrun-${STAMP}.tar.gz"

tar \
  --exclude=".env" \
  --exclude="backups" \
  --exclude="user_data_btc/data" \
  --exclude="user_data_eth/data" \
  --exclude="user_data_sol/data" \
  --exclude="user_data_xaut/data" \
  -czf "$ARCHIVE" \
  configs user_data_btc user_data_eth user_data_sol user_data_xaut dashboard market_recorder risk_service docs scripts docker-compose.yml README.md AGENTS.md .env.example

echo "Backup written to $ARCHIVE"
