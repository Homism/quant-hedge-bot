# API Key Security

Use exchange API keys only through environment variables. Do not store keys in
config files, strategy files, docs, shell history, screenshots, or Git commits.

## Required Rules

- Use a dedicated exchange sub-account.
- Enable read/trade permission only.
- Never enable withdrawal permission.
- Use IP whitelist for the VPS public IP.
- Rotate keys immediately if they may have leaked.
- Keep `.env` local to the server and never commit it.
- Use different keys for BTC and ETH bots if running leveraged live bots later.

Dry-run can run with empty API key placeholders.
