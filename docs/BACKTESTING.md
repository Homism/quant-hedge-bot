# Backtesting

Backtesting validates strategy behavior against historical futures candles. It
does not prove future profitability.

## Run

```bash
./scripts/run_backtest_btc.sh
./scripts/run_backtest_eth.sh
./scripts/run_backtest_sol.sh
```

The scripts download missing futures data first, then run Freqtrade backtesting
with protections enabled and export trade results to:

- `user_data_btc/backtest_results/`
- `user_data_eth/backtest_results/`
- `user_data_sol/backtest_results/`

XAUT is validation-gated:

```bash
./scripts/check_xaut_markets.sh
./scripts/run_backtest_xaut.sh
```

The XAUT backtest script exits before doing anything if no futures market is
confirmed.

## Useful Options

```bash
DAYS=180 ./scripts/run_backtest_btc.sh
TIMEFRAME=1h ./scripts/run_backtest_eth.sh
TIMERANGE=20240101-20240601 ./scripts/run_backtest_sol.sh
TIMERANGE=20240101-20240601 ./scripts/run_backtest_btc.sh
```

## What To Review

- Total return
- Max drawdown
- Trade count
- Win rate
- Average profit
- Worst trade
- Consecutive losses
- Average trade duration
- Exit reasons

Prefer low drawdown, low trade frequency, and stable behavior over headline
profit.
