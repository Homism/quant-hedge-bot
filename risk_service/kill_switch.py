"""Filesystem kill switch for blocking all new trade entries."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_KILL_SWITCH_PATH = Path("runtime/KILL_SWITCH")


def resolve_kill_switch_path(path: str | os.PathLike[str] | None = None) -> Path:
    if path is not None:
        return Path(path)
    env_path = os.getenv("KILL_SWITCH_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_KILL_SWITCH_PATH


def is_kill_switch_active(path: str | os.PathLike[str] | None = None) -> bool:
    return resolve_kill_switch_path(path).exists()


def kill_switch_reason(path: str | os.PathLike[str] | None = None) -> str:
    resolved = resolve_kill_switch_path(path)
    if resolved.exists():
        return f"kill switch active: {resolved}"
    return f"kill switch not present: {resolved}"
