"""Read OpenKore config.txt."""

from __future__ import annotations

import re
from pathlib import Path


def read_hook_ip(config_path: str) -> str | None:
    return read_config_field(config_path, "XKore_hookIp")


def read_xkore_port(config_path: str, default: int = 2350) -> int:
    raw = read_config_field(config_path, "XKore_port")
    if not raw:
        return default
    try:
        port = int(raw)
        return port if 1 <= port <= 65535 else default
    except ValueError:
        return default


def read_config_field(config_path: str, field: str) -> str | None:
    path = Path(config_path)
    if not path.is_file():
        return None
    pattern = re.compile(rf"^\s*{re.escape(field)}\s+(\S+)", re.IGNORECASE)
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1)
    return None
