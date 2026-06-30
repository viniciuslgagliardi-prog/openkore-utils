"""
Facade / Presenter — single entry point for the UI (MVP pattern).

The View (Tkinter) should only call methods on this class.
"""

from __future__ import annotations

from pathlib import Path

from openkore_utils.core.constants import DEFAULT_DNS, OPENKORE_DNS_SERVERS
from openkore_utils.domain.models import LanProfile, SetupStep
from openkore_utils.domain.validators import (
    default_dns_if_empty,
    ip_sequence,
    parse_dns_list,
    validate_ipv4,
    validate_whitelist_ip,
)
from openkore_utils.infrastructure.admin import is_admin, relaunch_as_admin
from openkore_utils.infrastructure.config_store import ConfigStore
from openkore_utils.services.hosts_service import HostsService
from openkore_utils.services.launch_service import launch_openkore, launch_ragnarok
from openkore_utils.services.network_service import NetworkService
from openkore_utils.services.openkore_service import read_hook_ip, read_xkore_port
from openkore_utils.services.profile_service import (
    ProfileInfo,
    create_profile_from_control,
    describe_openkore_root,
    describe_ragnarok_root,
    list_profiles,
    openkore_root_from_config,
    ragnarok_root_from_config,
    validate_openkore_root,
    validate_profile_name,
    validate_ragnarok_root,
)
from openkore_utils.services.setup_service import SetupService


class AppController:
    """Orchestrates services — manual dependency injection in constructor."""

    def __init__(self, config: ConfigStore | None = None) -> None:
        self.config = config or ConfigStore()
        self.network = NetworkService()
        self.setup = SetupService(self.network)
        self.hosts = HostsService()

    # --- Admin ---
    is_admin = staticmethod(is_admin)
    relaunch_as_admin = staticmethod(relaunch_as_admin)

    # --- Config ---
    def save_config(self) -> None:
        self.config.save()

    # --- OpenKore ---
    def read_hook_ip(self) -> str | None:
        path = self.config.data.get("openkore_config", "")
        return read_hook_ip(str(path))

    # --- Profiles ---
    def openkore_root(self) -> Path:
        return openkore_root_from_config(self.config.data)

    def describe_openkore_setup(self) -> dict[str, bool]:
        return describe_openkore_root(self.openkore_root())

    def describe_openkore_setup_at(self, folder: str) -> tuple[Path, dict[str, bool]]:
        root = Path(folder.strip()) if folder.strip() else self.openkore_root()
        return root, describe_openkore_root(root)

    def set_openkore_root(self, folder: str) -> tuple[bool, str]:
        root = Path(folder.strip())
        ok, err = validate_openkore_root(root)
        if not ok:
            return False, err
        resolved = root.resolve()
        self.config.data["openkore_root"] = str(resolved)
        self.config.data["openkore_config"] = str(resolved / "control" / "config.txt")
        self.save_config()
        return True, f"OpenKore folder: {resolved}"

    def ragnarok_root(self) -> Path:
        return ragnarok_root_from_config(self.config.data)

    def describe_ragnarok_setup_at(self, folder: str) -> tuple[Path, dict[str, bool]]:
        root = Path(folder.strip()) if folder.strip() else self.ragnarok_root()
        return root, describe_ragnarok_root(root)

    def set_ragnarok_root(self, folder: str) -> tuple[bool, str]:
        root = Path(folder.strip())
        ok, err = validate_ragnarok_root(root)
        if not ok:
            return False, err
        resolved = root.resolve()
        self.config.data["ragnarok_root"] = str(resolved)
        self.save_config()
        return True, f"Ragnarok folder: {resolved}"

    def open_ragnarok_folder(self) -> tuple[bool, str]:
        return self._open_folder(self.ragnarok_root())

    def list_profiles(self) -> list[ProfileInfo]:
        return list_profiles(self.openkore_root())

    validate_profile_name = staticmethod(validate_profile_name)

    def create_profile_from_control(self, name: str) -> tuple[bool, str]:
        return create_profile_from_control(self.openkore_root(), name)

    def profile_config_path(self, profile_name: str) -> Path:
        return Path(self.openkore_root()) / "profiles" / profile_name / "config.txt"

    def read_profile_hook_ip(self, profile_name: str) -> str | None:
        return read_hook_ip(str(self.profile_config_path(profile_name)))

    def read_profile_xkore_port(self, profile_name: str) -> int:
        return read_xkore_port(str(self.profile_config_path(profile_name)))

    def launch_openkore_profile(self, profile_name: str) -> tuple[bool, str]:
        return launch_openkore(self.openkore_root(), profile_name.strip())

    def launch_ragnarok_profile(self, profile_name: str) -> tuple[bool, str]:
        cfg = str(self.profile_config_path(profile_name))
        hook_ip = read_hook_ip(cfg) or ""
        port = read_xkore_port(cfg)
        return launch_ragnarok(self.ragnarok_root(), hook_ip, port)

    def open_profile_folder(self, profile_name: str) -> tuple[bool, str]:
        folder = self.profile_config_path(profile_name).parent
        if not folder.is_dir():
            return False, f"Profile folder not found: {folder}"
        return self._open_folder(folder)

    @staticmethod
    def _open_folder(folder: Path) -> tuple[bool, str]:
        import os
        import sys

        if not folder.is_dir():
            return False, f"Folder not found: {folder}"
        if sys.platform != "win32":
            return False, "Opening folders is supported on Windows only."
        os.startfile(folder)  # type: ignore[attr-defined]
        return True, f"Opened: {folder}"

    # --- Network ---
    def list_adapters(self) -> list[dict]:
        return self.network.list_adapters()

    def list_whitelist_ips(self) -> list[dict]:
        return self.network.list_whitelist_ips()

    def evaluate_setup(self, if_index: int | None, lan: dict, whitelist_ips: list[str]) -> list[SetupStep]:
        return self.setup.evaluate_setup(if_index, lan, whitelist_ips)

    def get_lan_snapshot(self, if_index: int) -> dict | None:
        return self.network.get_lan_ipv4_snapshot(if_index)

    def apply_lan_profile(self, if_index: int, lan: dict) -> tuple[bool, str, dict | None]:
        dns = default_dns_if_empty(lan.get("dns") or [])
        return self.network.apply_lan_profile(if_index, lan["ip"], lan["mask"], lan["gateway"], dns)

    def apply_dns_only(self, if_index: int, dns: list[str]) -> tuple[bool, str]:
        return self.network.apply_dns_only(if_index, default_dns_if_empty(dns))

    def apply_whitelist_ip(self, ip: str, if_index: int, lan: dict) -> tuple[bool, str, dict | None]:
        return self.network.apply_whitelist_ip(ip, if_index, lan)

    def add_whitelist_ip(self, ip: str, if_index: int) -> tuple[bool, str]:
        return self.network.add_ip(ip, if_index)

    def remove_whitelist_ip(self, ip: str) -> tuple[bool, str]:
        return self.network.remove_ip(ip)

    def reset_dhcp(self, if_index: int) -> tuple[bool, str]:
        self.hosts.clean_openkore_entries()
        return self.network.reset_adapter_dhcp(if_index)

    def reset_dhcp_many(self, indices: list[int]) -> list[tuple[int, bool, str]]:
        return self.network.reset_adapter_dhcp_many(indices)

    def reset_dns(self, if_index: int) -> tuple[bool, str]:
        return self.network.reset_dns(if_index)

    def restore_full_network(self, interface_indices: list[int]) -> tuple[list, list]:
        wl = self.network.list_whitelist_ips()
        ip_logs: list[tuple[str, bool, str]] = []
        for w in wl:
            ip = w.get("IPAddress", "")
            ok, st = self.network.remove_ip(ip)
            ip_logs.append((ip, ok, st))
        self.hosts.clean_openkore_entries()
        dhcp_logs = self.network.reset_adapter_dhcp_many(interface_indices)
        return ip_logs, dhcp_logs

    def open_network_panel(self) -> None:
        self.network.open_network_adapters()

    def ping(self, ip: str) -> tuple[bool, str, bool]:
        return self.network.ping_ip(ip)

    def get_ipv4_mode(self, if_index: int) -> tuple[bool, list[str]]:
        return self.network.get_ipv4_mode(if_index)

    def get_dns_servers(self, if_index: int) -> tuple[bool, list[str]]:
        return self.network.get_dns_servers(if_index)

    def clean_hosts(self) -> None:
        self.hosts.clean_openkore_entries()

    def collect_reset_interface_indices(
        self,
        selected_if_index: int | None,
        last_if_index: int | None,
    ) -> list[int]:
        """Adapters that may have been changed by OpenKore Utils."""
        indices: set[int] = set()
        openkore_dns = OPENKORE_DNS_SERVERS
        lan_ip = str(self.config.data.get("lan", {}).get("ip") or "")

        for w in self.network.list_whitelist_ips():
            ii = w.get("InterfaceIndex")
            if ii is not None:
                indices.add(int(ii))

        if selected_if_index is not None:
            indices.add(selected_if_index)
        if last_if_index is not None:
            indices.add(int(last_if_index))

        for a in self.network.list_adapters():
            idx = int(a["Index"])
            dhcp, ips = self.network.get_ipv4_mode(idx)
            _, dns = self.network.get_dns_servers(idx)
            if any(ip.startswith("172.65.") for ip in ips):
                indices.add(idx)
            if dns and openkore_dns.intersection(dns):
                indices.add(idx)
            if lan_ip and not dhcp and lan_ip in ips:
                indices.add(idx)

        if not indices and selected_if_index is not None:
            indices.add(selected_if_index)
        if not indices:
            for a in self.network.list_adapters():
                indices.add(int(a["Index"]))
        return sorted(indices)

    def reset_setup(
        self,
        selected_if_index: int | None,
        last_if_index: int | None,
    ) -> tuple[list[tuple[str, bool, str]], list[tuple[int, bool, str]]]:
        indices = self.collect_reset_interface_indices(selected_if_index, last_if_index)
        wl = self.network.list_whitelist_ips()
        ip_logs: list[tuple[str, bool, str]] = []
        for w in wl:
            ip = w.get("IPAddress", "")
            ok, st = self.network.remove_ip(ip)
            ip_logs.append((ip, ok, st))
        self.hosts.clean_openkore_entries()
        dhcp_logs = self.network.reset_adapter_dhcp_many(indices)
        return ip_logs, dhcp_logs

    # --- Validators (exposed for the View) ---
    validate_ipv4 = staticmethod(validate_ipv4)
    validate_whitelist_ip = staticmethod(validate_whitelist_ip)
    parse_dns_list = staticmethod(parse_dns_list)
    ip_sequence = staticmethod(ip_sequence)

    def parse_lan_from_ui(self, ip: str, mask: str, gw: str, dns_text: str) -> tuple[LanProfile | None, str | None]:
        dns = parse_dns_list(dns_text)
        if not validate_ipv4(ip):
            return None, "Invalid IP address."
        if not validate_ipv4(mask):
            return None, "Invalid subnet mask."
        if not validate_ipv4(gw):
            return None, "Invalid gateway."
        if not dns:
            dns = default_dns_if_empty([])
        return LanProfile(ip=ip, mask=mask, gateway=gw, dns=dns), None

    def save_lan_to_config(self, lan: LanProfile | dict) -> None:
        if isinstance(lan, LanProfile):
            self.config.data["lan"] = lan.as_dict()
        else:
            self.config.data["lan"] = lan
        self.save_config()
