"""OpenKore profile folders (profiles plugin)."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from openkore_utils.services.openkore_service import read_config_field, read_hook_ip

PROFILE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
DEFAULT_RAGNAROK_ROOT = Path(r"C:\Gravity\Ragnarok")


@dataclass(frozen=True)
class ProfileInfo:
    name: str
    hook_ip: str | None
    char_slot: str | None
    username: str | None


def openkore_root_from_config(config: dict) -> Path:
    explicit = config.get("openkore_root")
    if explicit:
        return Path(str(explicit))
    cfg_file = config.get("openkore_config", "")
    if cfg_file:
        p = Path(str(cfg_file))
        if p.is_file():
            if p.parent.name == "control":
                return p.parent.parent
            return p.parent.parent
    return Path.home() / "Documents" / "openkore"


def validate_openkore_root(root: Path) -> tuple[bool, str]:
    if not root.is_dir():
        return False, "Folder does not exist."
    control = root / "control"
    if not control.is_dir():
        return False, "Missing control/ — pick the OpenKore root folder (parent of control/)."
    if not (control / "config.txt").is_file():
        return False, "Missing control/config.txt in that folder."
    return True, ""


def describe_openkore_root(root: Path) -> dict[str, bool]:
    return {
        "control": (root / "control").is_dir(),
        "config": (root / "control" / "config.txt").is_file(),
        "profiles": (root / "profiles").is_dir(),
        "openkore_pl": (root / "openkore.pl").is_file(),
    }


def ragnarok_root_from_config(config: dict) -> Path:
    explicit = config.get("ragnarok_root")
    if explicit:
        return Path(str(explicit))
    return DEFAULT_RAGNAROK_ROOT


def validate_ragnarok_root(root: Path) -> tuple[bool, str]:
    if not root.is_dir():
        return False, "Folder does not exist."
    if not (root / "Ragexe.exe").is_file():
        return False, "Missing Ragexe.exe — pick the Ragnarok game folder."
    return True, ""


def describe_ragnarok_root(root: Path) -> dict[str, bool]:
    return {
        "ragexe": (root / "Ragexe.exe").is_file(),
        "bridge": (root / "bridge.dll").is_file(),
    }


def validate_profile_name(name: str) -> tuple[bool, str | None]:
    cleaned = name.strip()
    if not cleaned:
        return False, "Profile name is required."
    if cleaned.startswith(".") or cleaned.startswith("#"):
        return False, "Name cannot start with . or #."
    if not PROFILE_NAME_RE.match(cleaned):
        return False, "Use only letters, numbers, underscore, hyphen, or dot."
    return True, None


def list_profiles(openkore_root: Path) -> list[ProfileInfo]:
    profiles_dir = openkore_root / "profiles"
    if not profiles_dir.is_dir():
        return []
    out: list[ProfileInfo] = []
    for entry in sorted(profiles_dir.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith(".") or name.startswith("#"):
            continue
        config = entry / "config.txt"
        hook_ip = read_hook_ip(str(config)) if config.is_file() else None
        char_slot = read_config_field(str(config), "char") if config.is_file() else None
        username = read_config_field(str(config), "username") if config.is_file() else None
        out.append(ProfileInfo(name=name, hook_ip=hook_ip, char_slot=char_slot, username=username))
    return out


def create_profile_from_control(openkore_root: Path, name: str) -> tuple[bool, str]:
    ok, err = validate_profile_name(name)
    if not ok:
        return False, err or "Invalid name."

    control = openkore_root / "control"
    if not control.is_dir():
        return False, f"control folder not found: {control}"

    dest = openkore_root / "profiles" / name.strip()
    if dest.exists():
        return False, f"Profile '{name}' already exists."

    dest.mkdir(parents=True)
    copied = 0
    try:
        for item in control.iterdir():
            if item.is_file() and not item.name.startswith("."):
                shutil.copy2(item, dest / item.name)
                copied += 1
    except OSError as e:
        shutil.rmtree(dest, ignore_errors=True)
        return False, str(e)

    if copied == 0:
        dest.rmdir()
        return False, "No files found in control/ to copy."

    return True, f"Profile '{name}' created ({copied} files). Run: perl openkore.pl --profile={name}"
