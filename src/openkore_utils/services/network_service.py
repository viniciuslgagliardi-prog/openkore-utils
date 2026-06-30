"""Network operations (adapters, IPv4, DNS, whitelist)."""

from __future__ import annotations

import json
import os
import subprocess
import sys

from openkore_utils.core.constants import DEFAULT_DNS, PREFIX_LEN
from openkore_utils.domain.validators import default_dns_if_empty, validate_ipv4
from openkore_utils.infrastructure.powershell import run_powershell, hidden_subprocess_kwargs


class NetworkService:
    def list_adapters(self) -> list[dict]:
        ps = r"""
$items = Get-NetAdapter -Physical -ErrorAction SilentlyContinue |
    Where-Object { $_.Status -eq 'Up' } |
    ForEach-Object {
        $idx = $_.ifIndex
        $ips = @(Get-NetIPAddress -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object { $_.IPAddress -notlike '127.*' -and $_.PrefixOrigin -ne 'WellKnown' } |
            Select-Object -ExpandProperty IPAddress)
        [PSCustomObject]@{ Index = $idx; Name = $_.Name; Desc = $_.InterfaceDescription; IPv4 = ($ips -join ', ') }
    }
$items | ConvertTo-Json -Compress
"""
        code, out = run_powershell(ps)
        if code != 0 or not out or out == "null":
            return []
        try:
            data = json.loads(out)
            return [data] if isinstance(data, dict) else data
        except json.JSONDecodeError:
            return []

    def list_whitelist_ips(self) -> list[dict]:
        ps = r"""
Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -like '172.65.*' } |
    Select-Object InterfaceAlias, InterfaceIndex, IPAddress, PrefixLength |
    ConvertTo-Json -Compress
"""
        code, out = run_powershell(ps)
        if code != 0 or not out or out == "null":
            return []
        try:
            data = json.loads(out)
            items = [data] if isinstance(data, dict) else data
            return sorted(items, key=lambda x: tuple(int(p) for p in x["IPAddress"].split(".")))
        except (json.JSONDecodeError, KeyError, ValueError):
            return []

    def get_lan_ipv4_snapshot(self, if_index: int) -> dict | None:
        """Current LAN IPv4 (excluding 172.65.* / APIPA) + gateway + DNS."""
        ps = f"""
function PrefixToMask([int]$p) {{
    return ([System.Net.IPAddress]([uint32]::MaxValue -shl (32 - $p))).ToString()
}}
$idx = {if_index}
$addrs = Get-NetIPAddress -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {{
        $_.IPAddress -notlike '172.65.*' -and
        $_.IPAddress -notlike '169.254.*' -and
        $_.PrefixOrigin -ne 'WellKnown'
    }} | Sort-Object {{
        if ($_.SuffixOrigin -eq 'Dhcp') {{ 0 }}
        elseif ($_.PrefixOrigin -eq 'Manual') {{ 1 }}
        else {{ 2 }}
    }}
$a = $addrs | Select-Object -First 1
if (-not $a) {{ Write-Output 'ERR:no_lan_ip'; exit 1 }}
$gw = (Get-NetRoute -InterfaceIndex $idx -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue |
    Sort-Object RouteMetric | Select-Object -First 1 -ExpandProperty NextHop)
$dhcp = (Get-NetIPInterface -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction SilentlyContinue).Dhcp -eq 'Enabled'
$dns = @(Get-DnsClientServerAddress -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty ServerAddresses | Where-Object {{ $_ }})
@{{
    IP = $a.IPAddress
    Prefix = $a.PrefixLength
    Mask = (PrefixToMask $a.PrefixLength)
    Gateway = $gw
    Dhcp = $dhcp
    Dns = ($dns -join ',')
}} | ConvertTo-Json -Compress
"""
        code, out = run_powershell(ps)
        if code != 0 or not out or out.startswith("ERR:"):
            return None
        try:
            data = json.loads(out)
            if isinstance(data, dict) and data.get("Prefix") is not None:
                from openkore_utils.domain.validators import prefix_to_mask

                data["Mask"] = prefix_to_mask(int(data["Prefix"]))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    def apply_lan_profile(
        self,
        if_index: int,
        ip: str,
        mask: str,
        gateway: str,
        dns_servers: list[str],
    ) -> tuple[bool, str, dict | None]:
        """IPv4 manual + DNS (Cloudflare/Google) antes do whitelist 172.65.*."""
        if not validate_ipv4(ip) or not validate_ipv4(mask) or not validate_ipv4(gateway):
            return False, "Invalid IP, subnet mask, or gateway.", None
        dns = default_dns_if_empty(dns_servers)
        if not dns or not all(validate_ipv4(d) for d in dns):
            return False, "Invalid DNS.", None
        dns_esc = ",".join(f"'{d}'" for d in dns)
        ps = f"""
$idx = {if_index}
$adapter = Get-NetAdapter -InterfaceIndex $idx -ErrorAction Stop
$name = $adapter.Name
$ip = '{ip}'
$mask = '{mask}'
$gw = '{gateway}'
$dns = @({dns_esc})

& netsh interface ipv4 set address name="$name" static $ip $mask $gw 1 | Out-Null
if ($LASTEXITCODE -ne 0) {{ Write-Output 'ERR:address'; exit 2 }}
& netsh interface ipv4 set dnsservers name="$name" static $dns[0] primary validate=no | Out-Null
if ($LASTEXITCODE -ne 0) {{ Write-Output 'ERR:dns'; exit 3 }}
for ($i = 1; $i -lt $dns.Count; $i++) {{
    & netsh interface ipv4 add dnsservers name="$name" $dns[$i] index=($i + 1) validate=no | Out-Null
}}
@{{
    IP = $ip
    Mask = $mask
    Gateway = $gw
    Dns = ($dns -join ',')
    Action = 'applied'
}} | ConvertTo-Json -Compress
"""
        code, out = run_powershell(ps)
        if code != 0 or not out:
            return False, out or "Failed to apply LAN settings.", None
        if out.startswith("ERR:"):
            err = {
                "ERR:address": "Failed to set IP/mask/gateway (netsh).",
                "ERR:dns": "Failed to set DNS (netsh).",
            }.get(out.strip(), out)
            return False, err, None
        try:
            snap = json.loads(out)
        except json.JSONDecodeError:
            return False, "Invalid response when applying LAN.", None
        dns_shown = ", ".join(dns)
        msg = f"LAN {ip} / {mask} gw {gateway} | DNS {dns_shown}"
        return True, msg, snap

    def apply_dns_only(self, if_index: int, dns_servers: list[str]) -> tuple[bool, str]:
        dns = default_dns_if_empty(dns_servers)
        if not dns or not all(validate_ipv4(d) for d in dns):
            return False, "Invalid DNS."
        dns_esc = ",".join(f"'{d}'" for d in dns)
        ps = f"""
$name = (Get-NetAdapter -InterfaceIndex {if_index} -ErrorAction Stop).Name
$dns = @({dns_esc})
& netsh interface ipv4 set dnsservers name="$name" static $dns[0] primary validate=no | Out-Null
if ($LASTEXITCODE -ne 0) {{ Write-Output 'ERR:dns'; exit 1 }}
for ($i = 1; $i -lt $dns.Count; $i++) {{
    & netsh interface ipv4 add dnsservers name="$name" $dns[$i] index=($i + 1) validate=no | Out-Null
}}
Write-Output 'OK'
"""
        code, out = run_powershell(ps)
        if code != 0:
            return False, out or "Failed to apply DNS."
        return True, f"DNS: {', '.join(dns)}"

    def apply_whitelist_ip(self, ip: str, if_index: int, lan: dict) -> tuple[bool, str, dict | None]:
        """Static LAN + DNS + whitelist 172.65.* /32."""
        ok, lan_msg, snap = self.apply_lan_profile(
            if_index,
            lan["ip"],
            lan["mask"],
            lan["gateway"],
            lan.get("dns") or list(DEFAULT_DNS),
        )
        if not ok:
            return False, lan_msg, snap
        ok2, st = self.add_ip(ip, if_index)
        if not ok2:
            return False, f"{lan_msg}; whitelist failed: {st}", snap
        return True, f"{lan_msg}; whitelist {st}", snap

    def add_ip(self, ip: str, if_index: int) -> tuple[bool, str]:
        ps = f"""
$ip = '{ip}'; $idx = {if_index}
$exists = Get-NetIPAddress -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {{ $_.IPAddress -eq $ip }}
if ($exists) {{ Write-Output 'ALREADY'; exit 0 }}
New-NetIPAddress -InterfaceIndex $idx -IPAddress $ip -PrefixLength {PREFIX_LEN} -SkipAsSource $true -ErrorAction Stop | Out-Null
Write-Output 'OK'
"""
        code, out = run_powershell(ps)
        if code != 0:
            return False, out or "Failed to add IP."
        if "ALREADY" in out:
            return True, "already exists"
        return True, "added"

    def remove_ip(self, ip: str) -> tuple[bool, str]:
        ps = f"""
$ip = '{ip}'
$addrs = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {{ $_.IPAddress -eq $ip }}
if (-not $addrs) {{ Write-Output 'NONE'; exit 0 }}
foreach ($a in $addrs) {{ Remove-NetIPAddress -IPAddress $ip -InterfaceIndex $a.InterfaceIndex -Confirm:$false -ErrorAction Stop }}
Write-Output 'OK'
"""
        code, out = run_powershell(ps)
        if code != 0:
            return False, out or "Failed to remove IP."
        if "NONE" in out:
            return True, "not on adapter"
        return True, "removed"

    def get_ipv4_mode(self, if_index: int) -> tuple[bool, list[str]]:
        """Returns (dhcp_enabled, list of IPv4 addresses on adapter)."""
        ps = f"""
$ipif = Get-NetIPInterface -InterfaceIndex {if_index} -AddressFamily IPv4 -ErrorAction SilentlyContinue
if (-not $ipif) {{ Write-Output 'UNKNOWN'; exit 0 }}
$dhcp = $ipif.Dhcp -eq 'Enabled'
$ips = @(Get-NetIPAddress -InterfaceIndex {if_index} -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {{ $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' }} |
    Select-Object -ExpandProperty IPAddress)
$tag = if ($dhcp) {{ 'DHCP' }} else {{ 'STATIC' }}
Write-Output ($tag + ':' + ($ips -join ','))
"""
        code, out = run_powershell(ps)
        if code != 0 or not out or out.strip() == "UNKNOWN":
            return True, []
        tag, _, rest = out.partition(":")
        ips = [s.strip() for s in rest.split(",") if s.strip()]
        return tag.strip().upper() == "DHCP", ips

    def reset_adapter_dhcp(self, if_index: int) -> tuple[bool, str]:
        """DHCP for IPv4 + DNS on adapter — removes 172.65.* IPs first."""
        ps = f"""
$idx = {if_index}
$adapter = Get-NetAdapter -InterfaceIndex $idx -ErrorAction Stop
$name = $adapter.Name
Get-NetIPAddress -InterfaceIndex $idx -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {{ $_.IPAddress -like '172.65.*' }} |
    ForEach-Object {{
        Remove-NetIPAddress -IPAddress $_.IPAddress -InterfaceIndex $idx -Confirm:$false -ErrorAction SilentlyContinue
    }}
& netsh interface ipv4 set address name="$name" source=dhcp | Out-Null
if ($LASTEXITCODE -ne 0) {{ Write-Output 'ERR: falha ao definir IPv4 DHCP'; exit 1 }}
& netsh interface ipv4 set dnsservers name="$name" source=dhcp | Out-Null
if ($LASTEXITCODE -ne 0) {{ Write-Output 'ERR: falha ao definir DNS DHCP'; exit 2 }}
Write-Output 'OK'
"""
        code, out = run_powershell(ps)
        if code != 0:
            return False, out or "Failed to restore DHCP."
        return True, "IPv4 and DNS set to automatic (DHCP)"

    def reset_adapter_dhcp_many(self, indices: list[int]) -> list[tuple[int, bool, str]]:
        seen: set[int] = set()
        results: list[tuple[int, bool, str]] = []
        for idx in indices:
            if idx in seen:
                continue
            seen.add(idx)
            ok, msg = self.reset_adapter_dhcp(idx)
            results.append((idx, ok, msg))
        return results

    def get_dns_servers(self, if_index: int) -> tuple[bool, list[str]]:
        """Returns (dhcp_enabled, list of DNS servers)."""
        ps = f"""
$cfg = Get-DnsClientServerAddress -InterfaceIndex {if_index} -AddressFamily IPv4 -ErrorAction SilentlyContinue
if (-not $cfg) {{ Write-Output 'AUTO'; exit 0 }}
$s = @($cfg.ServerAddresses | Where-Object {{ $_ }})
if ($s.Count -eq 0) {{ Write-Output 'AUTO' }} else {{ Write-Output ($s -join ',') }}
"""
        code, out = run_powershell(ps)
        if code != 0 or not out:
            return True, []
        if out.strip() == "AUTO":
            return True, []
        return False, [s.strip() for s in out.split(",") if s.strip()]

    def reset_dns(self, if_index: int) -> tuple[bool, str]:
        ps = f"""
$idx = {if_index}
Set-DnsClientServerAddress -InterfaceIndex $idx -ResetServerAddresses -ErrorAction Stop
Set-DnsClientServerAddress -InterfaceIndex $idx -ResetServerAddresses -AddressFamily IPv6 -ErrorAction SilentlyContinue
Write-Output 'OK'
"""
        code, out = run_powershell(ps)
        if code != 0:
            return False, out or "Failed to restore DNS."
        return True, "DNS set to automatic (DHCP)"

    def reset_dns_many(self, indices: list[int]) -> list[tuple[int, bool, str]]:
        seen: set[int] = set()
        results: list[tuple[int, bool, str]] = []
        for idx in indices:
            if idx in seen:
                continue
            seen.add(idx)
            ok, msg = self.reset_dns(idx)
            results.append((idx, ok, msg))
        return results

    def open_network_adapters(self) -> None:
        # ncpa.cpl is not a direct executable — use os.startfile on Windows
        if sys.platform == "win32":
            os.startfile("ncpa.cpl")  # type: ignore[attr-defined]
        else:
            raise OSError("Windows only")

    def ping_ip(self, ip: str) -> tuple[bool, str, bool]:
        r = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", ip],
            capture_output=True,
            text=True,
            encoding="cp850",
            errors="replace",
            **hidden_subprocess_kwargs(),
        )
        text = ((r.stdout or "") + (r.stderr or "")).replace(" ", "").lower()
        local = "time<1ms" in text or "time=0ms" in text or "tempo<1ms" in text or "tempo=0ms" in text
        ok = r.returncode == 0
        if ok and local:
            return True, "Local ping OK (<1 ms).", True
        if ok:
            return True, "External ping (not local).", False
        return False, "No response.", False
