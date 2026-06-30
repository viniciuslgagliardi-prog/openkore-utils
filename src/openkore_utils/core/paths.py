"""File paths (frozen exe or development)."""

from __future__ import annotations

import sys
from pathlib import Path


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # src/openkore_utils/core/paths.py -> project root (openkore-utils)
    return Path(__file__).resolve().parents[3]


def config_path() -> Path:
    return app_base_dir() / "openkore_utils_config.json"


def legacy_config_paths() -> list[Path]:
    """Older config filenames kept for migration."""
    base = app_base_dir()
    return [
        base / "rede_config.json",
        base / "network_config.json",
    ]
