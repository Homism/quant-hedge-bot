from risk_service.config import load_env_settings


def test_env_loading_defaults_to_dry_run_and_binance() -> None:
    settings = load_env_settings({})
    assert settings.exchange_name == "binance"
    assert settings.dry_run is True
    assert settings.redacted()["exchange_key_set"] is False


def test_env_loading_redacts_secret_values() -> None:
    settings = load_env_settings(
        {
            "EXCHANGE_NAME": "binance",
            "FREQTRADE__EXCHANGE__KEY": "real-key-value",
            "FREQTRADE__EXCHANGE__SECRET": "real-secret-value",
            "FREQTRADE__TELEGRAM__ENABLED": "true",
            "FREQTRADE__TELEGRAM__TOKEN": "telegram-token",
            "FREQTRADE__TELEGRAM__CHAT_ID": "123",
            "FREQTRADE__DRY_RUN": "true",
        }
    )
    redacted = settings.redacted()
    assert redacted["exchange_key_set"] is True
    assert redacted["exchange_secret_set"] is True
    assert "real-key-value" not in str(redacted)
    assert "real-secret-value" not in str(redacted)
