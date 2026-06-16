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

    for config, pair in ((btc, "BTC/USDT:USDT"), (eth, "ETH/USDT:USDT")):
        assert config["dry_run"] is True
        assert config["trading_mode"] == "futures"
        assert config["margin_mode"] == "isolated"
        assert config["max_open_trades"] == 1
        assert config["exchange"]["pair_whitelist"] == [pair]
        assert config["exchange"]["key"] == ""
        assert config["exchange"]["secret"] == ""


def test_live_templates_remain_disabled() -> None:
    for name in ("btc.live.template.json", "eth.live.template.json"):
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
    assert "configs/btc.live.template.json" not in compose
    assert "configs/eth.live.template.json" not in compose


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
