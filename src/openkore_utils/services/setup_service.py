"""Network setup status evaluation."""

from __future__ import annotations

from openkore_utils.core.constants import DEFAULT_DNS
from openkore_utils.domain.models import SetupStep
from openkore_utils.domain.validators import validate_whitelist_ip
from openkore_utils.services.network_service import NetworkService


class SetupService:
    def __init__(self, network: NetworkService) -> None:
        self._network = network

    @staticmethod
    def _dns_is_configured(actual: list[str], expected: list[str]) -> bool:
        if not actual:
            return False
        return set(expected).issubset(set(actual))

    def evaluate_setup(
        self,
        if_index: int | None,
        lan: dict,
        whitelist_ips: list[str],
    ) -> list[SetupStep]:
        expected_dns = lan.get("dns") or list(DEFAULT_DNS)
        lan_exp = f"{lan['ip']} / {lan['mask']} gw {lan['gateway']}"
        dns_exp = ", ".join(expected_dns)
        wl_exp_list = [ip for ip in whitelist_ips if validate_whitelist_ip(ip)]
        wl_exp = ", ".join(wl_exp_list) if wl_exp_list else "(set in Apply IP)"

        if if_index is None:
            pick = "Select your Wi-Fi or Ethernet adapter above"
            return [
                SetupStep("lan", "Step 1 — Home LAN IP", False, pick, lan_exp),
                SetupStep("dns", "Step 2 — DNS servers", False, pick, dns_exp),
                SetupStep("whitelist", "Step 3 — Game IP (OpenKore)", False, pick, wl_exp),
            ]

        snap = self._network.get_lan_ipv4_snapshot(if_index)
        dhcp, all_ips = self._network.get_ipv4_mode(if_index)
        dns_auto, dns_list = self._network.get_dns_servers(if_index)
        wl_on = sorted(ip for ip in all_ips if ip.startswith("172.65."))

        if dhcp:
            lan_cur = f"Automatic (router assigns) — now: {snap.get('IP') if snap else '?'}"
            lan_ok = False
        elif snap and snap.get("IP") == lan["ip"] and snap.get("Mask") == lan["mask"] and (snap.get("Gateway") or "") == lan["gateway"]:
            lan_ok = True
            lan_cur = f"{snap['IP']} / {snap['Mask']} gw {snap.get('Gateway') or '?'}"
        elif snap:
            lan_ok = False
            lan_cur = f"Does not match expected — {snap.get('IP')} / {snap.get('Mask')}"
        else:
            lan_ok = False
            lan_cur = "no LAN IPv4"

        if dns_auto or not dns_list:
            dns_cur = "Automatic or empty"
            dns_ok = False
        elif self._dns_is_configured(dns_list, expected_dns):
            dns_ok = True
            dns_cur = ", ".join(dns_list)
        else:
            dns_ok = False
            dns_cur = ", ".join(dns_list)

        if not wl_exp_list:
            wl_ok = bool(wl_on)
            wl_cur = ", ".join(wl_on) if wl_on else "none"
            wl_exp_show = wl_exp
        else:
            missing = [ip for ip in wl_exp_list if ip not in wl_on]
            wl_ok = not missing
            wl_cur = ", ".join(wl_on) if wl_on else "none"
            wl_exp_show = wl_exp + (f" — missing: {', '.join(missing)}" if missing else "")

        return [
            SetupStep("lan", "Step 1 — Home LAN IP", lan_ok, lan_cur, lan_exp),
            SetupStep("dns", "Step 2 — DNS servers", dns_ok, dns_cur, dns_exp),
            SetupStep("whitelist", "Step 3 — Game IP (OpenKore)", wl_ok, wl_cur, wl_exp_show),
        ]
