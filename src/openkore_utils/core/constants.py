"""Global application constants."""

from __future__ import annotations

import sys

APP_NAME = "OpenKore Utils"
APP_VERSION = "5.2"
PREFIX_LEN = 32
HOSTS_MARK = "# OpenKore Utils"
LEGACY_HOSTS_MARKS = ("# MeuOPK latam Cloudflare",)

DEFAULT_DNS = ["1.1.1.1", "8.8.8.8"]
# Any of these on an adapter suggests OpenKore Utils configured DNS (incl. older builds).
OPENKORE_DNS_SERVERS = frozenset({"1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4"})
DEFAULT_LAN: dict = {
    "ip": "192.168.1.100",
    "mask": "255.255.255.0",
    "gateway": "192.168.1.1",
    "dns": list(DEFAULT_DNS),
}

# Dracula theme (VS Code)
C_BG = "#282a36"
C_CARD = "#343746"
C_INPUT = "#21222c"
C_BORDER = "#44475a"
C_ACCENT = "#bd93f9"
C_ACCENT_HOVER = "#caa6fa"
C_CYAN = "#8be9fd"
C_PINK = "#ff79c6"
C_OK = "#50fa7b"
C_OK_BG = "#2d3f35"
C_WARN = "#ffb86c"
C_WARN_BG = "#3d3428"
C_ERR = "#ff5555"
C_ERR_HOVER = "#ff6e6e"
C_MUTED = "#6272a4"
C_TEXT = "#f8f8f2"
C_SUBTEXT = "#a9b1d0"
C_ON_ACCENT = "#282a36"

FONT = "Segoe UI"
FONT_MONO = "Cascadia Mono"
if sys.platform == "win32":
    try:
        import tkinter.font as tkfont

        if "Segoe UI" not in tkfont.families():
            FONT = "TkDefaultFont"
        if "Cascadia Mono" not in tkfont.families():
            FONT_MONO = "Consolas"
    except Exception:
        FONT_MONO = "Consolas"
