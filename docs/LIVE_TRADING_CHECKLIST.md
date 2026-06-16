# Live Trading Checklist

Live trading is disabled and out of scope for the first deliverable. This
checklist is for a later explicit approval step only.

- Review all dry-run logs.
- Review BTC and ETH backtest reports.
- Confirm no strategy or config drift changed dry-run safety defaults.
- Use a dedicated exchange sub-account.
- Use isolated margin only.
- Never enable withdrawal permission.
- Enable IP whitelist.
- Start with very small size.
- Use strong Web UI/API credentials.
- Access Web UI only through SSH tunnel, VPN, or protected HTTPS proxy.
- Confirm kill switch works.
- Confirm stop scripts work.
- Confirm monitoring and alerting work.
- Prepare rollback: stop containers, remove API keys, rotate keys if needed.

There is intentionally no live start script in this repository.
