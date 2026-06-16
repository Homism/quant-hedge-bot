#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Starting read-only unified Dashboard only..."
docker compose up -d dashboard
echo "Dashboard: http://127.0.0.1:8090"
echo
echo "On a VPS, use SSH tunnel:"
echo "ssh -L 8090:127.0.0.1:8090 user@your-vps"
