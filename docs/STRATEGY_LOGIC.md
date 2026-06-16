# Strategy Logic

The BTC, ETH, and SOL strategies are conservative short hedge strategies for
futures dry-run. XAUT has the same defensive pattern, but it is validation-gated
because XAUT spot availability does not prove futures availability.

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

SOL is treated as a standard crypto futures bot. XAUT is Tether Gold, so it must
only be used for futures short hedging after `scripts/check_xaut_markets.sh`
confirms a futures pair.
