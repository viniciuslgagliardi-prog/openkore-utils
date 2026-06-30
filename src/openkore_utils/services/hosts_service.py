"""Windows hosts file cleanup."""

from __future__ import annotations

from pathlib import Path

from openkore_utils.core.constants import HOSTS_MARK, LEGACY_HOSTS_MARKS


class HostsService:
    HOSTS_FILE = Path(r"C:\Windows\System32\drivers\etc\hosts")

    def clean_openkore_entries(self) -> None:
        if not self.HOSTS_FILE.is_file():
            return
        lines = self.HOSTS_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        filtered = [
            line
            for line in lines
            if "172.65." not in line
            and HOSTS_MARK not in line
            and not any(mark in line for mark in LEGACY_HOSTS_MARKS)
        ]
        if len(filtered) != len(lines):
            self.HOSTS_FILE.write_text("\n".join(filtered) + ("\n" if filtered else ""), encoding="utf-8")
