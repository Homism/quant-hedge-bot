# Strategy Logic

The BTC and ETH strategies are conservative short hedge strategies for futures
dry-run.

## Indicators

- EMA20: short-term recovery pressure.
- EMA50: slower trend filter.
- RSI14: momentum filter.
- Volume mean 20: avoids acting on weak signals in inactive markets.

## Short Entry

A short hedge signal requires:

- Close below EMA50.
- EMA20 below EMA50.
- RSI below 45.
- Current volume above the 20-candle average.
- Volume above zero.

The strategies do not create long entries.

## Short Exit

A short hedge exits when:

- Price recovers above EMA20.
- Price recovers above EMA50.
- RSI recovers above 52.
- Stoploss or ROI logic exits.
- Trade is stale for 12 hours.
- Kill switch is active.

## Risk Assumptions

The bot is a defensive hedge assistant, not an aggressive profit maximizer.
Position size is capped at 5% of available balance, leverage is capped at 2x,
and dry-run is the default operating mode.
