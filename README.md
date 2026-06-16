# BTC/ETH Freqtrade Quant Hedge Bot

This repository is a dry-run-first BTC/ETH quantitative hedge bot built on Freqtrade.

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
- Futures mode uses isolated margin only.
- Max leverage is capped at 2x.
- Max open trades is 1 per bot.
- Max stake is capped at 5% of available balance.
- Daily loss guard blocks new entries at 2%.
- Three consecutive losing trades block new entries.
- A filesystem kill switch blocks all new entries.
- No martingale, grid averaging, DCA, or automatic position scaling.

## Layout

- `docker-compose.yml` runs `freqtrade-btc` and `freqtrade-eth`.
- `configs/*.dryrun.json` are the active dry-run configs.
- `configs/*.live.template.json` are disabled reference templates only.
- `user_data_btc/strategies/BtcHedgeStrategy.py` is the BTC strategy.
- `user_data_eth/strategies/EthHedgeStrategy.py` is the ETH strategy.
- `risk_service/` contains pure risk helpers and tests.
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

On a VPS, use an SSH tunnel:

```bash
ssh -L 8081:127.0.0.1:8081 -L 8082:127.0.0.1:8082 user@your-vps
```

## Backtest

```bash
./scripts/run_backtest_btc.sh
./scripts/run_backtest_eth.sh
```

Optional variables:

```bash
DAYS=180 ./scripts/run_backtest_btc.sh
TIMERANGE=20240101-20240601 ./scripts/run_backtest_eth.sh
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
