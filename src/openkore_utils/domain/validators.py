"""IP and sequence validation — no side effects."""

from __future__ import annotations

import re

from openkore_utils.core.constants import DEFAULT_DNS


def validate_ipv4(ip: str) -> bool:
    m = re.match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", ip.strip())
    return bool(m and all(0 <= int(g) <= 255 for g in m.groups()))


def prefix_to_mask(prefix: int) -> str:
    """Convert CIDR prefix length to dotted subnet mask."""
    if prefix < 0 or prefix > 32:
        return ""
    if prefix == 0:
        return "0.0.0.0"
    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    return ".".join(str((mask >> (8 * (3 - i))) & 0xFF) for i in range(4))


def mask_from_snapshot(snap: dict) -> str:
    """Subnet mask from adapter snapshot (Prefix preferred over Mask field)."""
    prefix = snap.get("Prefix")
    if prefix is not None:
        try:
            m = prefix_to_mask(int(prefix))
            if m:
                return m
        except (TypeError, ValueError):
            pass
    mask = str(snap.get("Mask") or "").strip()
    return mask if validate_ipv4(mask) and not mask.startswith("0.") else ""


def parse_dns_list(text: str) -> list[str]:
    out: list[str] = []
    for part in re.split(r"[,;\s]+", text.strip()):
        p = part.strip()
        if p and validate_ipv4(p) and p not in out:
            out.append(p)
    return out


def validate_whitelist_ip(ip: str) -> bool:
    m = re.match(r"^172\.65\.(\d{1,3})\.(\d{1,3})$", ip.strip())
    return bool(m and all(1 <= int(g) <= 255 for g in m.groups()))


def ip_sequence(start_ip: str, count: int) -> tuple[list[str], str | None]:
    if count < 1 or count > 50:
        return [], "Count must be between 1 and 50."
    if not validate_whitelist_ip(start_ip):
        return [], "Invalid start IP (172.65.X.Y)."
    parts = start_ip.strip().split(".")
    base = [int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])]
    if base[0] != 172 or base[1] != 65:
        return [], "IP must start with 172.65."
    out: list[str] = []
    o3, o4 = base[2], base[3]
    for _ in range(count):
        if o4 > 255:
            return [], f"Last octet overflow after {len(out)} IP(s)."
        ip = f"172.65.{o3}.{o4}"
        if not validate_whitelist_ip(ip):
            return [], f"Invalid IP in sequence: {ip}"
        out.append(ip)
        o4 += 1
        if o4 > 255:
            o4 = 1
            o3 += 1
            if o3 > 255:
                return [], "IP sequence overflow."
    return out, None


def default_dns_if_empty(dns: list[str]) -> list[str]:
    return dns if dns else list(DEFAULT_DNS)
