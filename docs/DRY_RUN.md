# Dry-Run

Dry-run simulates trades through Freqtrade without placing real exchange orders.
The active configs and Docker Compose force dry-run mode.

## Start

```bash
./scripts/run_dryrun.sh
```

## Monitor

- BTC Web UI: `http://127.0.0.1:8081`
- ETH Web UI: `http://127.0.0.1:8082`
- SOL Web UI: `http://127.0.0.1:8083`
- Unified Dashboard: `http://127.0.0.1:8090`
- Status: `./scripts/check_status.sh`
- Logs: `docker compose logs -f freqtrade-btc`

## Runtime Behavior

- Simulated wallet starts at 10,000 USDT per bot.
- Each active bot trades one pair only.
- Max open trades is 1 per active bot.
- Strategy entries are short-only.
- Default dry-run always starts BTC, ETH, and SOL.
- XAUT starts only after `scripts/check_xaut_markets.sh --require-futures` passes.
- The unified Dashboard starts with dry-run and is read-only.
- Risk guards log blocked entries.
- Telegram is optional and disabled unless env vars are set.

Run dry-run for multiple market regimes before considering any live-trading
review.

## Web UI Ports

- BTC: `127.0.0.1:8081`
- ETH: `127.0.0.1:8082`
- SOL: `127.0.0.1:8083`
- XAUT, only if futures validation passes: `127.0.0.1:8084`
- Dashboard: `127.0.0.1:8090`
