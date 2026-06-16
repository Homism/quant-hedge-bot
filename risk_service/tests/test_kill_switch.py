from risk_service.kill_switch import is_kill_switch_active, kill_switch_reason


def test_kill_switch_activates_when_file_exists(tmp_path) -> None:
    switch = tmp_path / "KILL_SWITCH"
    assert not is_kill_switch_active(switch)
    assert "not present" in kill_switch_reason(switch)

    switch.write_text("stop", encoding="utf-8")
    assert is_kill_switch_active(switch)
    assert "active" in kill_switch_reason(switch)
