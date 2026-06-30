"""Domain models (pure data)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SetupStep:
    key: str
    title: str
    ok: bool
    current: str
    expected: str


@dataclass
class LanProfile:
    ip: str
    mask: str
    gateway: str
    dns: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"ip": self.ip, "mask": self.mask, "gateway": self.gateway, "dns": list(self.dns)}

    @classmethod
    def from_dict(cls, data: dict) -> LanProfile:
        return cls(
            ip=str(data.get("ip", "")),
            mask=str(data.get("mask", "")),
            gateway=str(data.get("gateway", "")),
            dns=list(data.get("dns") or []),
        )
