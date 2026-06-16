# AGENTS.md

## Project Safety Rules

- Never enable live trading without explicit user approval in a later task.
- Never change dry-run defaults to live defaults.
- Never add secrets, API keys, or tokens to the repository.
- Never request or store withdrawal-enabled exchange keys.
- Never add wallet integration, private-key handling, on-chain signing, or broadcasting.
- Never add martingale, grid averaging, DCA, revenge trading, or uncontrolled scaling.
- Never add trading buttons or trading actions to the Dashboard.
- Keep Dashboard routes read-only. Dashboard may read status but must not place orders, close positions, cancel orders, or modify leverage.
- Keep the market recorder read-only. It may consume public market data and write local snapshots, but must never use API keys, private endpoints, order endpoints, or trading actions.
- Keep futures configs on isolated margin only.
- Keep max leverage capped at 2x.
- Keep max open trades at 1 per active bot unless explicitly approved.
- Keep the 5% position-size cap, 2% daily-loss guard, consecutive-loss guard, and kill switch.
- Keep SOL in default dry-run only; never promote XAUT to default dry-run unless futures validation passes.
- Never treat XAUT spot availability as permission to run a futures short hedge bot.
- Always run `./scripts/run_tests.sh` after changing `risk_service` or strategy risk behavior.
- Always explain strategy changes in plain language.
- Prioritize capital protection and observability over profitability.

## CodeGraph

This project may use a CodeGraph MCP server (`codegraph_*` tools). Use CodeGraph
for structural questions such as symbol location, call relationships, impact
analysis, signatures, and focused context. Use native search only for literal
text queries or after a specific file is already open.

If CodeGraph is not initialized, ask before running `codegraph init -i`.
