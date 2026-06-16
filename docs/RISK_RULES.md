# Risk Rules

These rules are mandatory for this project.

## Position And Leverage

- Futures mode only for hedge simulation.
- Isolated margin only.
- Max leverage is 2x.
- Max open trades is 1 per active bot.
- Max stake per position is 5% of available balance.
- No automatic leverage increase.
- No uncontrolled position scaling.

## Loss Guards

- Daily loss guard blocks new entries after 2% realized daily loss.
- Consecutive loss guard blocks new entries after 3 losing trades.
- Freqtrade protections add cooldown, stoploss guard, and max drawdown guard.

## Strategy Prohibitions

- No martingale.
- No grid averaging.
- No DCA.
- No revenge trading.
- No position-adjustment callback.

## Kill Switch

Create `runtime/KILL_SWITCH` to block all new entries:

```bash
touch runtime/KILL_SWITCH
```

Remove it to permit dry-run entries again:

```bash
rm runtime/KILL_SWITCH
```

## XAUT Gate

XAUT is Tether Gold. It can only be used for a short hedge when a futures market
such as `XAUT/USDT:USDT` is confirmed. If only spot `XAUT/USDT` exists, keep it
as watcher only and do not start the XAUT bot.
