# BTC/ETH/SOL Freqtrade Quant Hedge Bot

This repository is a dry-run-first BTC/ETH/SOL quantitative hedge bot built on Freqtrade.
It also contains an XAUT market-validation watcher and a validation-gated XAUT
template that must not be started unless a futures pair is confirmed.

It is not a wallet project. It does not connect to blockchain wallets, private keys,
on-chain signing, or on-chain broadcasting. It is designed for centralized exchange
APIs only.

## Safety Defaults

- Dry-run is enabled in every active config.
- Docker Compose also forces `FREQTRADE__DRY_RUN=true`.
- There is no live-trading start script.
- API keys are not stored in config files.
- `.env` is ignored by Git. Only `.env.example` is committed.
- Web UI ports bind to `127.0.0.1` only.
- The unified Dashboard is read-only and binds to `127.0.0.1:8090` only.
- Futures mode uses isolated margin only.
- Max leverage is capped at 2x.
- Max open trades is 1 per active bot.
- Max stake is capped at 5% of available balance.
- Daily loss guard blocks new entries at 2%.
- Three consecutive losing trades block new entries.
- A filesystem kill switch blocks all new entries.
- No martingale, grid averaging, DCA, or automatic position scaling.

## Layout

- `docker-compose.yml` runs `freqtrade-btc`, `freqtrade-eth`, and `freqtrade-sol`.
- `freqtrade-xaut` is profile-gated by `xaut-validated` and starts only after market validation passes.
- `configs/*.dryrun.json` are the active dry-run configs.
- `configs/*.live.template.json` are disabled reference templates only.
- `user_data_btc/strategies/BtcHedgeStrategy.py` is the BTC strategy.
- `user_data_eth/strategies/EthHedgeStrategy.py` is the ETH strategy.
- `user_data_sol/strategies/SolHedgeStrategy.py` is the SOL strategy.
- `user_data_xaut/strategies/XautHedgeStrategy.py` is present only for validated XAUT futures use.
- `risk_service/` contains pure risk helpers and tests.
- `dashboard/` contains the read-only unified status dashboard.
- `scripts/` contains dry-run, backtest, status, backup, and test helpers.
- `docs/` contains operational documentation.

## Configure

Copy `.env.example` to `.env` on the machine that runs the bot:

```bash
cp .env.example .env
```

Do not commit `.env`. For dry-run, API keys can remain empty. If you later add
exchange keys, use a dedicated sub-account, read/trade permission only, no
withdrawal permission, and IP whitelist.

## Run Dry-Run

```bash
./scripts/run_dryrun.sh
```

Local Web UI:

- BTC: `http://127.0.0.1:8081`
- ETH: `http://127.0.0.1:8082`
- SOL: `http://127.0.0.1:8083`
- Dashboard: `http://127.0.0.1:8090`

On a VPS, use an SSH tunnel:

```bash
ssh -L 8081:127.0.0.1:8081 -L 8082:127.0.0.1:8082 -L 8083:127.0.0.1:8083 -L 8084:127.0.0.1:8084 -L 8090:127.0.0.1:8090 user@your-vps
```

The Dashboard is status-only. It does not place orders, close trades, cancel
orders, modify leverage, modify strategy files, or change `dry_run`.

## XAUT Market Validation

XAUT is Tether Gold. XAUT spot availability does not mean a futures short hedge
is available. Check public markets first:

```bash
./scripts/check_xaut_markets.sh
```

If the script reports no futures pair, keep XAUT as watcher only. The default
dry-run script also runs this validation and skips XAUT if validation fails.

## Backtest

```bash
./scripts/run_backtest_btc.sh
./scripts/run_backtest_eth.sh
./scripts/run_backtest_sol.sh
```

`./scripts/run_backtest_xaut.sh` blocks itself unless XAUT futures validation passes.

Optional variables:

```bash
DAYS=180 ./scripts/run_backtest_btc.sh
TIMERANGE=20240101-20240601 ./scripts/run_backtest_eth.sh
TIMEFRAME=1h ./scripts/run_backtest_sol.sh
```

## Kill Switch

Create this file to block all new entries and request exit through strategy logic:

```bash
touch runtime/KILL_SWITCH
```

Remove it to allow new dry-run entries again:

```bash
rm runtime/KILL_SWITCH
```

## Tests

```bash
python3 -m pip install -r requirements-dev.txt
./scripts/run_tests.sh
```

## Live Trading

Live trading is intentionally not enabled. The live template files are disabled
by default and must not be used without a separate explicit request and a full
safety review.
