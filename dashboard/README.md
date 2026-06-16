# Unified Dashboard

This dashboard is read-only. It serves a local webpage and reads status from the
Freqtrade REST APIs for BTC, ETH, SOL, and validation-gated XAUT.

It does not place orders, close trades, cancel orders, change leverage, modify
configs, or change `dry_run`.

Default local URL:

```bash
http://127.0.0.1:8090
```

On a VPS, access it through SSH tunnel:

```bash
ssh -L 8090:127.0.0.1:8090 root@your-vps
```
