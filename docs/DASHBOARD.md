# Unified Dashboard

The unified Dashboard is a read-only local status page for BTC, ETH, SOL, and
validation-gated XAUT Freqtrade bots.

It does not:

- place orders
- close trades
- cancel orders
- change leverage
- modify strategies
- modify config
- change `dry_run`

## Local URL

The Dashboard binds only to localhost:

```text
127.0.0.1:8090
```

Open locally:

```text
http://127.0.0.1:8090
```

## VPS Access

Use SSH tunnel:

```bash
ssh -L 8090:127.0.0.1:8090 root@your-vps
```

Then open:

```text
http://127.0.0.1:8090
```

To also open all Freqtrade UIs:

```bash
ssh -L 8081:127.0.0.1:8081 \
    -L 8082:127.0.0.1:8082 \
    -L 8083:127.0.0.1:8083 \
    -L 8084:127.0.0.1:8084 \
    -L 8090:127.0.0.1:8090 \
    root@your-vps
```

## Data Shown

- online status
- dry-run status
- pair
- open trade count
- simulated PnL
- today simulated PnL
- recent trade
- recent error
- risk status
- kill switch status
- XAUT futures validation state

Do not expose this Dashboard to the public internet.
