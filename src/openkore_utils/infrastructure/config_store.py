"""JSON configuration persistence."""

from __future__ import annotations

import json
from pathlib import Path

from openkore_utils.core.constants import DEFAULT_DNS, DEFAULT_LAN, PREFIX_LEN
from openkore_utils.core.paths import config_path, legacy_config_paths


class ConfigStore:
    """Configuration repository (Single Responsibility)."""

    def __init__(self, path: Path | None = None, legacy_paths: list[Path] | None = None) -> None:
        self._path = path or config_path()
        self._legacy_paths = legacy_paths if legacy_paths is not None else legacy_config_paths()
        self._data = self._load()

    @property
    def data(self) -> dict:
        return self._data

    def save(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load(self) -> dict:
        default: dict = {
            "whitelist_ip": "172.65.10.20",
            "prefix_length": PREFIX_LEN,
            "openkore_root": str(Path.home() / "Documents" / "openkore"),
            "openkore_config": str(Path.home() / "Documents" / "openkore" / "control" / "config.txt"),
            "ragnarok_root": r"C:\Gravity\Ragnarok",
            "last_interface_index": None,
            "managed_ips": [],
            "pinned_primary": None,
            "lan": dict(DEFAULT_LAN),
        }
        source = self._path if self._path.exists() else None
        if source is None:
            for legacy in self._legacy_paths:
                if legacy.exists():
                    source = legacy
                    break
        if source and source.exists():
            try:
                default.update(json.loads(source.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        lan = dict(DEFAULT_LAN)
        lan.update(default.get("lan") or {})
        if not lan.get("dns"):
            lan["dns"] = list(DEFAULT_DNS)
        default["lan"] = lan
        return default
