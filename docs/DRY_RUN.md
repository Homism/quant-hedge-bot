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
- Status: `./scripts/check_status.sh`
- Logs: `docker compose logs -f freqtrade-btc`

## Runtime Behavior

- Simulated wallet starts at 10,000 USDT per bot.
- Each bot trades one pair only.
- Max open trades is 1 per bot.
- Strategy entries are short-only.
- Risk guards log blocked entries.
- Telegram is optional and disabled unless env vars are set.

Run dry-run for multiple market regimes before considering any live-trading
review.
