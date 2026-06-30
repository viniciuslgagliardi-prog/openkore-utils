"""Tkinter styles — Dracula dark theme."""

from __future__ import annotations

from tkinter import ttk

from openkore_utils.core.constants import (
    C_ACCENT,
    C_ACCENT_HOVER,
    C_BG,
    C_BORDER,
    C_CARD,
    C_ERR,
    C_ERR_HOVER,
    C_INPUT,
    C_MUTED,
    C_ON_ACCENT,
    C_PINK,
    C_SUBTEXT,
    C_TEXT,
    FONT,
    FONT_MONO,
)


def apply_theme(style: ttk.Style) -> None:
    style.theme_use("clam")

    style.configure(".", background=C_BG, foreground=C_TEXT, font=(FONT, 10))
    style.configure("TFrame", background=C_BG)
    style.configure("Card.TFrame", background=C_CARD)

    style.configure("TLabel", background=C_BG, foreground=C_TEXT, font=(FONT, 10))
    style.configure("Card.TLabel", background=C_CARD, foreground=C_TEXT, font=(FONT, 10))
    style.configure("Muted.TLabel", background=C_BG, foreground=C_MUTED, font=(FONT, 9))
    style.configure("CardMuted.TLabel", background=C_CARD, foreground=C_MUTED, font=(FONT, 9))
    style.configure("Status.TLabel", background=C_BG, foreground=C_SUBTEXT, font=(FONT, 9))

    # Default / ghost buttons
    style.configure(
        "TButton",
        font=(FONT, 10),
        padding=(14, 9),
        background=C_CARD,
        foreground=C_TEXT,
        bordercolor=C_BORDER,
        focusthickness=0,
    )
    style.map(
        "TButton",
        background=[("active", C_BORDER), ("disabled", C_CARD)],
        foreground=[("disabled", C_MUTED)],
    )

    style.configure(
        "Ghost.TButton",
        font=(FONT, 9),
        padding=(12, 8),
        background=C_CARD,
        foreground=C_SUBTEXT,
        bordercolor=C_BORDER,
    )
    style.map(
        "Ghost.TButton",
        background=[("active", C_BORDER), ("!disabled", C_CARD)],
        foreground=[("active", C_TEXT), ("!disabled", C_SUBTEXT)],
    )

    # Primary — Dracula purple
    style.configure(
        "Primary.TButton",
        font=(FONT, 10, "bold"),
        padding=(18, 10),
        background=C_ACCENT,
        foreground=C_ON_ACCENT,
        bordercolor=C_ACCENT,
    )
    style.map(
        "Primary.TButton",
        background=[("active", C_ACCENT_HOVER), ("!disabled", C_ACCENT), ("disabled", C_BORDER)],
        foreground=[("!disabled", C_ON_ACCENT), ("disabled", C_MUTED)],
    )

    # Danger — Dracula red
    style.configure(
        "Danger.TButton",
        font=(FONT, 10),
        padding=(14, 10),
        background=C_ERR,
        foreground=C_TEXT,
        bordercolor=C_ERR,
    )
    style.map(
        "Danger.TButton",
        background=[("active", C_ERR_HOVER), ("!disabled", C_ERR), ("disabled", C_BORDER)],
        foreground=[("!disabled", C_TEXT), ("disabled", C_MUTED)],
    )

    style.configure(
        "accent.Horizontal.TProgressbar",
        troughcolor=C_BORDER,
        background=C_PINK,
        thickness=4,
        bordercolor=C_BG,
        lightcolor=C_PINK,
        darkcolor=C_PINK,
    )

    style.configure("TNotebook", background=C_BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure(
        "TNotebook.Tab",
        padding=(16, 9),
        font=(FONT, 10),
        background=C_BG,
        foreground=C_MUTED,
        bordercolor=C_BG,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", C_CARD), ("!selected", C_BG)],
        foreground=[("selected", C_ACCENT), ("!selected", C_MUTED)],
        expand=[("selected", (0, 2, 0, 0))],
    )

    style.configure(
        "Treeview",
        font=(FONT_MONO, 9),
        rowheight=26,
        background=C_INPUT,
        fieldbackground=C_INPUT,
        foreground=C_TEXT,
        bordercolor=C_BORDER,
        relief="flat",
    )
    style.configure(
        "Treeview.Heading",
        font=(FONT, 9, "bold"),
        background=C_CARD,
        foreground=C_MUTED,
        bordercolor=C_BORDER,
        relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", C_ACCENT)],
        foreground=[("selected", C_ON_ACCENT)],
    )

    style.configure(
        "TCombobox",
        padding=6,
        fieldbackground=C_INPUT,
        background=C_CARD,
        foreground=C_TEXT,
        arrowcolor=C_TEXT,
        bordercolor=C_BORDER,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", C_INPUT)],
        foreground=[("readonly", C_TEXT)],
    )

    style.configure(
        "TEntry",
        fieldbackground=C_INPUT,
        foreground=C_TEXT,
        insertcolor=C_TEXT,
        bordercolor=C_BORDER,
    )

    style.configure(
        "Accent.Vertical.TScrollbar",
        troughcolor=C_BORDER,
        background=C_SUBTEXT,
        arrowcolor=C_TEXT,
        bordercolor=C_BORDER,
        arrowsize=14,
    )
    style.map(
        "Accent.Vertical.TScrollbar",
        background=[("active", C_ACCENT), ("!disabled", C_SUBTEXT)],
    )


# Backward-compatible alias
apply_win11_theme = apply_theme
