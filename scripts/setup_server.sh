#!/usr/bin/env bash
set -euo pipefail

echo "Server checklist for the dry-run hedge bot:"
echo "1. Install Docker Engine and the Docker Compose plugin."
echo "2. Clone or copy this repository to the VPS."
echo "3. Copy .env.example to .env on the VPS only, then set non-withdrawal API keys if needed."
echo "4. Replace the local-only Web UI passwords in .env."
echo "5. Start dry-run with: ./scripts/run_dryrun.sh"
echo "6. Access BTC/ETH/SOL/XAUT Web UI and Dashboard only through SSH tunnel or VPN."
echo "7. Run ./scripts/check_xaut_markets.sh before any XAUT backtest or XAUT profile use."
echo
echo "This script does not install packages or enable live trading."
