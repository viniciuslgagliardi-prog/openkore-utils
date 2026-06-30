"""Launch OpenKore and Ragnarok client (bridge / XKore 1)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from openkore_utils.services.profile_service import validate_openkore_root, validate_ragnarok_root

DEFAULT_XKORE_PORT = 2350


def _new_console_kwargs() -> dict:
    if sys.platform != "win32":
        return {}
    return {"creationflags": subprocess.CREATE_NEW_CONSOLE}


def launch_openkore(openkore_root: Path, profile: str) -> tuple[bool, str]:
    ok, err = validate_openkore_root(openkore_root)
    if not ok:
        return False, err
    perl = shutil.which("perl")
    if not perl:
        return False, "Perl not found in PATH (install Strawberry Perl)."
    script = openkore_root / "openkore.pl"
    if not script.is_file():
        return False, f"Not found: {script}"
    subprocess.Popen(
        [perl, str(script), f"--profile={profile}"],
        cwd=str(openkore_root),
        **_new_console_kwargs(),
    )
    return True, f"OpenKore started: perl openkore.pl --profile={profile}"


def launch_ragnarok(ragnarok_root: Path, hook_ip: str, port: int = DEFAULT_XKORE_PORT) -> tuple[bool, str]:
    ok, err = validate_ragnarok_root(ragnarok_root)
    if not ok:
        return False, err
    ip = (hook_ip or "").strip()
    if not ip:
        return False, "XKore_hookIp not set in profile config.txt"
    exe = ragnarok_root / "Ragexe.exe"
    subprocess.Popen(
        [str(exe), "1rag1", "-ip", ip, "-port", str(port)],
        cwd=str(ragnarok_root),
    )
    return True, f"Ragexe started: 1rag1 -ip {ip} -port {port}"
