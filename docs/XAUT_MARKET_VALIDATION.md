# XAUT Market Validation

XAUT is Tether Gold. It is a gold-backed token, not a standard crypto futures
market by default.

Having a spot pair such as `XAUT/USDT` does not mean a futures pair such as
`XAUT/USDT:USDT` is available. This matters because the hedge bot needs futures
shorting. Spot-only XAUT can be monitored, but it cannot be used by this project
as a futures short hedge.

## Check Markets

Run:

```bash
./scripts/check_xaut_markets.sh
```

The script uses public exchange endpoints only. It does not need API keys, does
not place orders, and does not modify config.

Default exchange:

```bash
EXCHANGE_NAME=binance ./scripts/check_xaut_markets.sh
```

Optional OKX check:

```bash
XAUT_EXCHANGE_NAME=okx ./scripts/check_xaut_markets.sh
```

## Interpreting Results

- `spot pair XAUT/USDT exists: yes` means XAUT spot can be monitored.
- `futures pair XAUT/USDT:USDT exists: yes` means the XAUT hedge bot can be considered for dry-run.
- `can enable XAUT hedge bot: no` means do not start `freqtrade-xaut`.

## Default Behavior

The default dry-run script always starts BTC, ETH, and SOL. It then runs this
market validation. XAUT starts only if futures validation passes. The Docker
Compose service is under the `xaut-validated` profile.
