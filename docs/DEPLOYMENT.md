# Deployment

The target runtime is a Linux VPS with Docker Engine and the Docker Compose
plugin installed.

## Setup

```bash
git clone <repo-url> quant-hedge-bot
cd quant-hedge-bot
cp .env.example .env
```

Edit `.env` on the server only. Replace Web UI/API passwords. Keep exchange keys
empty for dry-run unless the chosen exchange requires keys for private dry-run
data access.

## Start Dry-Run

```bash
./scripts/run_dryrun.sh
```

## Status And Logs

```bash
./scripts/check_status.sh
docker compose logs -f freqtrade-btc
docker compose logs -f freqtrade-eth
```

## Safe Web UI Access

Ports are bound to localhost on the VPS:

- BTC: `127.0.0.1:8081`
- ETH: `127.0.0.1:8082`
- SOL: `127.0.0.1:8083`
- XAUT, only after futures validation passes: `127.0.0.1:8084`

Use an SSH tunnel:

```bash
ssh -L 8081:127.0.0.1:8081 -L 8082:127.0.0.1:8082 -L 8083:127.0.0.1:8083 user@your-vps
```

Do not expose Freqtrade Web UI directly to the public internet. If remote access
must be shared later, use a VPN or an HTTPS reverse proxy with Basic Auth and
strict firewall rules.
