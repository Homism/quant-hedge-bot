import json
import os
import re
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_jsonc(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)
    return json.loads(text)


def test_dry_run_configs_are_futures_isolated_and_secret_free() -> None:
    btc = load_jsonc(ROOT / "configs/btc.dryrun.json")
    eth = load_jsonc(ROOT / "configs/eth.dryrun.json")
    sol = load_jsonc(ROOT / "configs/sol.dryrun.json")
    xaut = load_jsonc(ROOT / "configs/xaut.dryrun.json")

    for config, pair in (
        (btc, "BTC/USDT:USDT"),
        (eth, "ETH/USDT:USDT"),
        (sol, "SOL/USDT:USDT"),
        (xaut, "XAUT/USDT:USDT"),
    ):
        assert config["dry_run"] is True
        assert config["trading_mode"] == "futures"
        assert config["margin_mode"] == "isolated"
        assert config["max_open_trades"] == 1
        assert config["exchange"]["pair_whitelist"] == [pair]
        assert config["exchange"]["key"] == ""
        assert config["exchange"]["secret"] == ""


def test_live_templates_remain_disabled() -> None:
    for name in (
        "btc.live.template.json",
        "eth.live.template.json",
        "sol.live.template.json",
        "xaut.live.template.json",
    ):
        path = ROOT / "configs" / name
        text = path.read_text(encoding="utf-8")
        config = load_jsonc(path)
        assert "DANGEROUS LIVE TRADING TEMPLATE" in text
        assert config["dry_run"] is True
        assert config["max_open_trades"] == 1
        assert config["margin_mode"] == "isolated"
        assert config["exchange"]["key"] == ""
        assert config["exchange"]["secret"] == ""


def test_compose_forces_dry_run_and_localhost_ports() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert 'FREQTRADE__DRY_RUN: "true"' in compose
    assert '"127.0.0.1:8081:8080"' in compose
    assert '"127.0.0.1:8082:8080"' in compose
    assert '"127.0.0.1:8083:8080"' in compose
    assert '"127.0.0.1:8084:8080"' in compose
    assert '"127.0.0.1:8090:8090"' in compose
    assert '"8081:8080"' not in compose
    assert '"8082:8080"' not in compose
    assert '"8083:8080"' not in compose
    assert '"8084:8080"' not in compose
    assert '"8090:8090"' not in compose
    assert "configs/btc.live.template.json" not in compose
    assert "configs/eth.live.template.json" not in compose
    assert "configs/sol.live.template.json" not in compose
    assert "configs/xaut.live.template.json" not in compose
    assert "xaut-validated" in compose


def test_run_dryrun_starts_xaut_only_after_validation() -> None:
    run_dryrun = (ROOT / "scripts/run_dryrun.sh").read_text(encoding="utf-8")
    assert "freqtrade-btc freqtrade-eth freqtrade-sol market-recorder dashboard" in run_dryrun
    assert "./scripts/check_xaut_markets.sh --require-futures" in run_dryrun
    assert "docker compose --profile xaut-validated up -d freqtrade-xaut" in run_dryrun
    assert "docker compose up -d freqtrade-btc freqtrade-eth freqtrade-sol freqtrade-xaut" not in run_dryrun


def test_xaut_backtest_is_validation_gated() -> None:
    run_backtest = (ROOT / "scripts/run_backtest_xaut.sh").read_text(encoding="utf-8")
    assert "./scripts/check_xaut_markets.sh --require-futures" in run_backtest
    assert "docker compose --profile xaut-validated run --rm freqtrade-xaut" in run_backtest


def test_dashboard_is_read_only_and_has_no_trade_controls() -> None:
    server = (ROOT / "dashboard/server.py").read_text(encoding="utf-8")
    index = (ROOT / "dashboard/static/index.html").read_text(encoding="utf-8")
    app = (ROOT / "dashboard/static/app.js").read_text(encoding="utf-8")
    run_dashboard = (ROOT / "scripts/run_dashboard.sh").read_text(encoding="utf-8")

    assert "def do_GET" in server
    assert "def do_POST" in server and "METHOD_NOT_ALLOWED" in server
    assert "def do_PUT" in server and "def do_DELETE" in server
    assert "/api/summary" in server
    assert "/api/v1/force" not in server
    assert "/api/v1/forcebuy" not in server
    assert "/api/v1/forcesell" not in server
    assert "/api/v1/forceexit" not in server
    assert "/api/v1/cancel" not in server
    assert "<button" not in index.lower()
    assert "<button" not in app.lower()
    assert "docker compose up -d dashboard" in run_dashboard
    assert "freqtrade-btc" not in run_dashboard
    assert "live.template" not in run_dashboard


def test_market_recorder_is_read_only_public_data_only() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    recorder = (ROOT / "market_recorder/recorder.py").read_text(encoding="utf-8")

    assert "market-recorder:" in compose
    assert "RECORDER_SNAPSHOT_INTERVAL_MS: ${RECORDER_SNAPSHOT_INTERVAL_MS:-200}" in compose
    assert "RECORDER_STATE_PATH: /runtime/market_recorder/state.json" in compose
    assert "ports:" not in compose.split("market-recorder:", 1)[1].split("dashboard:", 1)[0]
    assert "FREQTRADE__EXCHANGE__KEY" not in compose.split("market-recorder:", 1)[1].split("dashboard:", 1)[0]
    assert "trading_enabled\": False" in recorder
    assert "api_key_required\": False" in recorder
    assert "order_actions\": False" in recorder
    assert "force" not in recorder.lower()
    assert "withdraw" not in recorder.lower()


def test_scripts_are_executable_and_do_not_start_live_templates() -> None:
    for script in (ROOT / "scripts").glob("*.sh"):
        mode = os.stat(script).st_mode
        assert mode & stat.S_IXUSR, f"{script.name} is not executable"
        text = script.read_text(encoding="utf-8")
        assert ".live.template.json" not in text
        assert "dry_run false" not in text.lower()


def test_strategies_are_short_only_without_position_adjustment() -> None:
    for path in (
        ROOT / "user_data_btc/strategies/BtcHedgeStrategy.py",
        ROOT / "user_data_eth/strategies/EthHedgeStrategy.py",
        ROOT / "user_data_sol/strategies/SolHedgeStrategy.py",
        ROOT / "user_data_xaut/strategies/XautHedgeStrategy.py",
    ):
        text = path.read_text(encoding="utf-8")
        assert "can_short = True" in text
        assert "position_adjustment_enable = False" in text
        assert "def adjust_trade_position" not in text
        assert "['enter_long', 'enter_tag']" not in text
        assert '["enter_long", "enter_tag"]' not in text


def test_no_real_env_file_or_secret_values_exist() -> None:
    assert not (ROOT / ".env").exists()
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "FREQTRADE__EXCHANGE__KEY=" in env_example
    assert "FREQTRADE__EXCHANGE__SECRET=" in env_example
    assert "real-key-value" not in env_example
    assert "real-secret-value" not in env_example
