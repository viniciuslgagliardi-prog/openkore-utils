"""Main view — Tkinter (MVP pattern)."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from openkore_utils.controllers.app_controller import AppController
from openkore_utils.core.constants import (
    APP_NAME,
    C_ACCENT,
    C_BG,
    C_BORDER,
    C_CARD,
    C_ERR,
    C_MUTED,
    C_INPUT,
    C_ON_ACCENT,
    C_OK,
    C_SUBTEXT,
    C_TEXT,
    C_WARN,
    DEFAULT_DNS,
    DEFAULT_LAN,
    FONT,
    FONT_MONO,
)
from openkore_utils.domain.validators import mask_from_snapshot
from openkore_utils.ui.theme import apply_theme


class MainWindow(tk.Tk):
    def __init__(self, ctrl: AppController | None = None) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.configure(bg=C_BG)
        self.minsize(520, 720)
        self._ctrl = ctrl or AppController()
        self.cfg = self._ctrl.config.data
        self.adapters: list[dict] = []
        self.whitelist: list[dict] = []
        self._busy = False
        self._action_buttons: list[ttk.Button] = []

        self._setup_style()
        self._build_ui()
        self._center_window()
        self.refresh_profiles()
        self.after(100, self.refresh)

    def _setup_style(self) -> None:
        apply_theme(ttk.Style(self))

    def _section(self, parent: tk.Widget, title: str) -> tk.Frame:
        border = tk.Frame(parent, bg=C_BORDER, padx=1, pady=1)
        border.pack(fill=tk.X, pady=(0, 10))
        body = tk.Frame(border, bg=C_CARD, padx=16, pady=12)
        body.pack(fill=tk.X)
        tk.Label(body, text=title, bg=C_CARD, fg=C_ACCENT, font=(FONT, 10, "bold")).pack(anchor="w", pady=(0, 8))
        return body

    def _register_btn(self, btn: ttk.Button) -> ttk.Button:
        self._action_buttons.append(btn)
        return btn

    def _scrollable(self, parent: tk.Widget) -> tk.Frame:
        """Vertical scroll with visible hint when content overflows."""
        shell = tk.Frame(parent, bg=C_BG)
        shell.pack(fill=tk.BOTH, expand=True)

        view = tk.Frame(shell, bg=C_BG)
        view.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(view, bg=C_BG, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(view, orient=tk.VERTICAL, style="Accent.Vertical.TScrollbar", command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=C_BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        hint_var = tk.StringVar(value="")
        hint = tk.Label(
            shell, textvariable=hint_var, bg=C_BG, fg=C_ACCENT,
            font=(FONT, 8), anchor="center", cursor="hand2",
        )

        def refresh_scroll_ui(_event: tk.Event | None = None) -> None:
            canvas.update_idletasks()
            inner_h = inner.winfo_reqheight()
            ch = canvas.winfo_height()
            if ch < 2:
                return
            needs = inner_h > ch + 4
            if needs:
                if not scrollbar.winfo_ismapped():
                    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            else:
                scrollbar.pack_forget()
                canvas.yview_moveto(0)
            _y0, y1 = canvas.yview()
            if needs and y1 < 0.995:
                hint_var.set("▼ Role para ver mais")
                if not hint.winfo_ismapped():
                    hint.pack(fill=tk.X, pady=(2, 0))
            else:
                hint.pack_forget()

        def on_yview(*args: object) -> None:
            scrollbar.set(*args)
            refresh_scroll_ui()

        def on_inner_configure(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            refresh_scroll_ui()

        def on_canvas_configure(event: tk.Event) -> None:
            canvas.itemconfigure(win_id, width=event.width)
            refresh_scroll_ui()

        def on_wheel(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_enter(_event: tk.Event) -> None:
            canvas.bind_all("<MouseWheel>", on_wheel)

        def on_leave(_event: tk.Event) -> None:
            canvas.unbind_all("<MouseWheel>")

        def scroll_down(_event: tk.Event) -> None:
            canvas.yview_scroll(3, "units")

        hint.bind("<Button-1>", scroll_down)
        canvas.configure(yscrollcommand=on_yview)
        inner.bind("<Configure>", on_inner_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)

        if not hasattr(self, "_scroll_refreshers"):
            self._scroll_refreshers: list = []
        self._scroll_refreshers.append(refresh_scroll_ui)
        return inner

    def _refresh_scroll_panels(self) -> None:
        for fn in getattr(self, "_scroll_refreshers", []):
            fn()

    def _build_tab_container(self, parent: tk.Widget) -> None:
        wrap = tk.Frame(parent, bg=C_BG)
        wrap.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        bar_border = tk.Frame(wrap, bg=C_BORDER)
        bar_border.pack(fill=tk.X)
        bar_inner = tk.Frame(bar_border, bg=C_BG, padx=1)
        bar_inner.pack(fill=tk.X, pady=(1, 0))
        for col in range(3):
            bar_inner.grid_columnconfigure(col, weight=1, uniform="tabs")

        self._tab_labels: dict[str, tk.Label] = {}
        self._tab_btn_frames: dict[str, tk.Frame] = {}
        self._active_tab: str | None = None

        for col, (key, label) in enumerate(
            (("setup", "Setup"), ("network", "Network / DNS"), ("profiles", "Profiles"))
        ):
            cell = tk.Frame(bar_inner, bg=C_INPUT, cursor="hand2")
            cell.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 2, 0))
            accent = tk.Frame(cell, bg=C_INPUT, height=2)
            accent.pack(fill=tk.X, side=tk.TOP)
            lbl = tk.Label(
                cell, text=label, bg=C_INPUT, fg=C_MUTED,
                font=(FONT, 10), padx=12, pady=10, cursor="hand2",
            )
            lbl.pack(fill=tk.BOTH, expand=True)
            self._tab_btn_frames[key] = cell
            self._tab_labels[key] = lbl
            cell._tab_accent = accent  # type: ignore[attr-defined]
            for w in (cell, lbl, accent):
                w.bind("<Button-1>", lambda _e, k=key: self._select_tab(k))
                w.bind("<Enter>", lambda _e, k=key: self._hover_tab(k, True))
                w.bind("<Leave>", lambda _e, k=key: self._hover_tab(k, False))

        content_border = tk.Frame(wrap, bg=C_BORDER)
        content_border.pack(fill=tk.BOTH, expand=True)
        content_inner = tk.Frame(content_border, bg=C_CARD, padx=1, pady=1)
        content_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=(0, 1))
        self._tab_page_host = tk.Frame(content_inner, bg=C_BG)
        self._tab_page_host.pack(fill=tk.BOTH, expand=True)

    def _hover_tab(self, key: str, entering: bool) -> None:
        if self._active_tab == key:
            return
        cell = self._tab_btn_frames[key]
        lbl = self._tab_labels[key]
        accent: tk.Frame = cell._tab_accent  # type: ignore[attr-defined]
        bg = C_BORDER if entering else C_INPUT
        cell.configure(bg=bg)
        lbl.configure(bg=bg, fg=C_TEXT if entering else C_MUTED)
        accent.configure(bg=bg)

    def _select_tab(self, key: str) -> None:
        if self._active_tab == key:
            return
        self._active_tab = key
        for k, cell in self._tab_btn_frames.items():
            lbl = self._tab_labels[k]
            accent: tk.Frame = cell._tab_accent  # type: ignore[attr-defined]
            selected = k == key
            bg = C_CARD if selected else C_INPUT
            cell.configure(bg=bg)
            lbl.configure(
                bg=bg,
                fg=C_ACCENT if selected else C_MUTED,
                font=(FONT, 10, "bold") if selected else (FONT, 10),
            )
            accent.configure(bg=C_ACCENT if selected else bg)
        for k, page in self._tab_pages.items():
            page.pack_forget()
        self._tab_pages[key].pack(fill=tk.BOTH, expand=True)
        if key == "profiles":
            self.refresh_profiles()
        self.after(80, self._refresh_scroll_panels)

    def _center_window(self) -> None:
        w, h = 560, 780
        self.minsize(520, 680)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=(16, 12, 16, 10))
        root.pack(fill=tk.BOTH, expand=True)

        hdr = tk.Frame(root, bg=C_BG)
        hdr.pack(fill=tk.X, pady=(0, 10))
        tk.Label(hdr, text=APP_NAME, bg=C_BG, fg=C_ACCENT, font=(FONT, 18, "bold")).pack(side=tk.LEFT)
        admin_bg = C_OK if self._ctrl.is_admin() else C_WARN
        admin_fg = C_ON_ACCENT
        admin_txt = "Admin" if self._ctrl.is_admin() else "Run as admin"
        self.admin_frame = tk.Frame(hdr, bg=admin_bg, padx=10, pady=4, cursor="hand2")
        self.admin_frame.pack(side=tk.RIGHT)
        self.admin_lbl = tk.Label(
            self.admin_frame, text=admin_txt, bg=admin_bg, fg=admin_fg,
            font=(FONT, 8, "bold"), cursor="hand2",
        )
        self.admin_lbl.pack()
        if not self._ctrl.is_admin():
            self.admin_frame.bind("<Button-1>", lambda _e: self._ctrl.relaunch_as_admin())
            self.admin_lbl.bind("<Button-1>", lambda _e: self._ctrl.relaunch_as_admin())

        ad_body = self._section(root, "Adapter")
        ad_row = tk.Frame(ad_body, bg=C_CARD)
        ad_row.pack(fill=tk.X)
        self.adapter_var = tk.StringVar()
        self.adapter_combo = ttk.Combobox(ad_row, textvariable=self.adapter_var, state="readonly", font=(FONT, 10))
        self.adapter_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ad_btns = tk.Frame(ad_row, bg=C_CARD)
        ad_btns.pack(side=tk.RIGHT)
        self._register_btn(
            ttk.Button(ad_btns, text="Open adapters", style="Ghost.TButton", command=self.on_open_adapters)
        ).pack(side=tk.LEFT, padx=(0, 4))
        self._register_btn(ttk.Button(ad_btns, text="Refresh", style="Ghost.TButton", command=self.refresh)).pack(side=tk.LEFT)
        self.adapter_var.trace_add("write", lambda *_: self._update_status_line())

        self.net_status_var = tk.StringVar(value="")
        tk.Label(ad_body, textvariable=self.net_status_var, bg=C_CARD, fg=C_SUBTEXT, font=(FONT, 9)).pack(anchor="w", pady=(6, 0))

        self._build_tab_container(root)

        self.tab_setup_outer = tk.Frame(self._tab_page_host, bg=C_BG)
        self.tab_network_outer = tk.Frame(self._tab_page_host, bg=C_BG)
        self.tab_profiles_outer = tk.Frame(self._tab_page_host, bg=C_BG)
        self._tab_pages = {
            "setup": self.tab_setup_outer,
            "network": self.tab_network_outer,
            "profiles": self.tab_profiles_outer,
        }

        self.tab_setup = self._scrollable(self.tab_setup_outer)
        tab_setup_pad = tk.Frame(self.tab_setup, bg=C_BG, padx=8, pady=8)
        tab_setup_pad.pack(fill=tk.BOTH, expand=True)
        self.tab_network = self._scrollable(self.tab_network_outer)
        tab_network_pad = tk.Frame(self.tab_network, bg=C_BG, padx=8, pady=8)
        tab_network_pad.pack(fill=tk.BOTH, expand=True)

        self._tab_profiles_footer = tk.Frame(self.tab_profiles_outer, bg=C_BORDER, padx=1, pady=1)
        self._tab_profiles_footer.pack(side=tk.BOTTOM, fill=tk.X)
        profiles_scroll_host = tk.Frame(self.tab_profiles_outer, bg=C_BG)
        profiles_scroll_host.pack(fill=tk.BOTH, expand=True)
        self.tab_profiles = self._scrollable(profiles_scroll_host)
        tab_profiles_pad = tk.Frame(self.tab_profiles, bg=C_BG, padx=8, pady=8)
        tab_profiles_pad.pack(fill=tk.BOTH, expand=True)

        self._tab_setup_body = tab_setup_pad
        self._tab_network_body = tab_network_pad
        self._tab_profiles_body = tab_profiles_pad

        self._build_tab_setup()
        self._build_tab_network()
        self._build_tab_profiles()
        self._select_tab("setup")

        self.prog_frame = ttk.Frame(root)
        self.progress = ttk.Progressbar(self.prog_frame, mode="indeterminate", style="accent.Horizontal.TProgressbar")
        self.progress_label = ttk.Label(self.prog_frame, text="", style="Muted.TLabel")
        self.prog_frame.pack_forget()

        log_border = tk.Frame(root, bg=C_BORDER, padx=1, pady=1)
        log_border.pack(fill=tk.BOTH, expand=False, pady=(8, 0))
        log_inner = tk.Frame(log_border, bg=C_CARD, padx=8, pady=6)
        log_inner.pack(fill=tk.BOTH)
        self.log_text = tk.Text(
            log_inner, height=3, wrap=tk.WORD, font=(FONT_MONO, 8),
            bg=C_INPUT, fg=C_TEXT, insertbackground=C_TEXT,
            relief=tk.FLAT, highlightthickness=1, highlightbackground=C_BORDER, highlightcolor=C_ACCENT,
            selectbackground=C_ACCENT, selectforeground=C_ON_ACCENT,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state=tk.DISABLED)

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(root, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w", pady=(6, 0))

    def _build_tab_setup(self) -> None:
        body = self._section(self._tab_setup_body, "OpenKore folder")
        row = tk.Frame(body, bg=C_CARD)
        row.pack(fill=tk.X)
        self.openkore_root_var = tk.StringVar(value=str(self._ctrl.openkore_root()))
        self._openkore_entry = ttk.Entry(row, textvariable=self.openkore_root_var, font=(FONT_MONO, 9))
        self._openkore_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self._openkore_entry.bind("<FocusOut>", lambda _e: self._update_setup_labels())
        self._register_btn(
            ttk.Button(row, text="Browse...", style="Ghost.TButton", command=self.on_browse_openkore)
        ).pack(side=tk.RIGHT, padx=(0, 4))
        self._register_btn(
            ttk.Button(row, text="Save", style="Primary.TButton", command=self.on_save_openkore_root)
        ).pack(side=tk.RIGHT)

        tk.Label(
            body,
            text="Select the OpenKore root (contains control/, openkore.pl).",
            bg=C_CARD, fg=C_MUTED, font=(FONT, 8), wraplength=420, justify="left",
        ).pack(anchor="w", pady=(8, 0))

        self.openkore_check_var = tk.StringVar()
        tk.Label(
            body, textvariable=self.openkore_check_var, bg=C_CARD, fg=C_SUBTEXT,
            font=(FONT_MONO, 8), wraplength=420, justify="left",
        ).pack(anchor="w", pady=(8, 0))

        rag_body = self._section(self._tab_setup_body, "Ragnarok folder")
        rag_row = tk.Frame(rag_body, bg=C_CARD)
        rag_row.pack(fill=tk.X)
        self.ragnarok_root_var = tk.StringVar(value=str(self._ctrl.ragnarok_root()))
        self._ragnarok_entry = ttk.Entry(rag_row, textvariable=self.ragnarok_root_var, font=(FONT_MONO, 9))
        self._ragnarok_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self._ragnarok_entry.bind("<FocusOut>", lambda _e: self._update_setup_labels())
        self._register_btn(
            ttk.Button(rag_row, text="Browse...", style="Ghost.TButton", command=self.on_browse_ragnarok)
        ).pack(side=tk.RIGHT, padx=(0, 4))
        self._register_btn(
            ttk.Button(rag_row, text="Save", style="Primary.TButton", command=self.on_save_ragnarok_root)
        ).pack(side=tk.RIGHT)

        tk.Label(
            rag_body,
            text="Folder with Ragexe.exe (bridge.dll). Example: C:\\Gravity\\Ragnarok",
            bg=C_CARD, fg=C_MUTED, font=(FONT, 8), wraplength=420, justify="left",
        ).pack(anchor="w", pady=(8, 0))

        self.ragnarok_check_var = tk.StringVar()
        tk.Label(
            rag_body, textvariable=self.ragnarok_check_var, bg=C_CARD, fg=C_SUBTEXT,
            font=(FONT_MONO, 8), wraplength=420, justify="left",
        ).pack(anchor="w", pady=(8, 0))

        rag_btn_row = tk.Frame(rag_body, bg=C_CARD)
        rag_btn_row.pack(fill=tk.X, pady=(4, 0))
        self._register_btn(
            ttk.Button(rag_btn_row, text="Open folder", style="Ghost.TButton", command=self.on_open_ragnarok_folder)
        ).pack(side=tk.LEFT)

        paths_body = self._section(self._tab_setup_body, "Paths")
        self.openkore_paths_var = tk.StringVar()
        tk.Label(
            paths_body, textvariable=self.openkore_paths_var, bg=C_CARD, fg=C_MUTED,
            font=(FONT_MONO, 8), wraplength=420, justify="left",
        ).pack(anchor="w")

        self._update_setup_labels()

    def _update_setup_labels(self) -> None:
        ok_folder = self.openkore_root_var.get().strip()
        root, checks = self._ctrl.describe_openkore_setup_at(ok_folder)
        parts = []
        for key, label in (
            ("control", "control/"),
            ("config", "control/config.txt"),
            ("openkore_pl", "openkore.pl"),
            ("profiles", "profiles/"),
        ):
            mark = "OK" if checks.get(key) else "—"
            parts.append(f"{label}: {mark}")
        self.openkore_check_var.set("  ·  ".join(parts))

        rag_folder = self.ragnarok_root_var.get().strip()
        rag_root, rag_checks = self._ctrl.describe_ragnarok_setup_at(rag_folder)
        rag_parts = []
        for key, label in (("ragexe", "Ragexe.exe"), ("bridge", "bridge.dll")):
            mark = "OK" if rag_checks.get(key) else "—"
            rag_parts.append(f"{label}: {mark}")
        self.ragnarok_check_var.set("  ·  ".join(rag_parts))

        self.openkore_paths_var.set(
            f"config → {root / 'control' / 'config.txt'}\n"
            f"profiles → {root / 'profiles'}\n"
            f"Ragexe → {rag_root / 'Ragexe.exe'}"
        )

    def _update_openkore_setup_labels(self, folder: str | None = None) -> None:
        if folder is not None:
            self.openkore_root_var.set(folder)
        self._update_setup_labels()

    def on_browse_openkore(self) -> None:
        current = self.openkore_root_var.get().strip()
        initial = current if current else str(self._ctrl.openkore_root())
        chosen = filedialog.askdirectory(title="Select OpenKore folder", initialdir=initial, mustexist=True)
        if chosen:
            self.openkore_root_var.set(chosen)
            self._update_openkore_setup_labels(chosen)
            self.on_save_openkore_root()

    def on_browse_ragnarok(self) -> None:
        current = self.ragnarok_root_var.get().strip()
        initial = current if current else str(self._ctrl.ragnarok_root())
        chosen = filedialog.askdirectory(title="Select Ragnarok folder", initialdir=initial, mustexist=True)
        if chosen:
            self.ragnarok_root_var.set(chosen)
            self._update_setup_labels()
            self.on_save_ragnarok_root()

    def on_save_ragnarok_root(self) -> None:
        folder = self.ragnarok_root_var.get().strip()
        if not folder:
            messagebox.showwarning(APP_NAME, "Ragnarok folder path is empty.")
            self.log("Ragnarok folder path is empty.", "err")
            return
        ok, msg = self._ctrl.set_ragnarok_root(folder)
        self.log(msg, "ok" if ok else "err")
        if ok:
            self.cfg = self._ctrl.config.data
            self._update_setup_labels()
            self.set_status("Ragnarok folder saved.")
        else:
            messagebox.showwarning(
                APP_NAME,
                f"Could not save this folder:\n\n{msg}\n\n"
                "Pick the folder that contains Ragexe.exe.",
            )
            saved = str(self._ctrl.ragnarok_root())
            self.ragnarok_root_var.set(saved)
            self._update_setup_labels()
            self.set_status("Ragnarok folder not saved — invalid path.")

    def on_open_ragnarok_folder(self) -> None:
        ok, msg = self._ctrl.open_ragnarok_folder()
        self.log(msg, "ok" if ok else "err")

    def on_save_openkore_root(self) -> None:
        folder = self.openkore_root_var.get().strip()
        if not folder:
            messagebox.showwarning(APP_NAME, "OpenKore folder path is empty.")
            self.log("OpenKore folder path is empty.", "err")
            return
        ok, msg = self._ctrl.set_openkore_root(folder)
        self.log(msg, "ok" if ok else "err")
        if ok:
            self.cfg = self._ctrl.config.data
            self._update_setup_labels()
            self.refresh_profiles()
            self.set_status("OpenKore folder saved.")
        else:
            messagebox.showwarning(
                APP_NAME,
                f"Could not save this folder:\n\n{msg}\n\n"
                "Pick the OpenKore root (the folder that contains control/ and openkore.pl), "
                "not Downloads or another random folder.",
            )
            saved = str(self._ctrl.openkore_root())
            self.openkore_root_var.set(saved)
            self._update_setup_labels()
            self.set_status("OpenKore folder not saved — invalid path.")

    def _build_tab_network(self) -> None:
        ip_body = self._section(self._tab_network_body, "Game IP (172.65.*)")
        ip_row = tk.Frame(ip_body, bg=C_CARD)
        ip_row.pack(fill=tk.X)
        self.ip_var = tk.StringVar(value=self.cfg.get("whitelist_ip", "172.65.10.20"))
        ttk.Entry(ip_row, textvariable=self.ip_var, font=(FONT_MONO, 11), width=18).pack(side=tk.LEFT, padx=(0, 8))
        self._register_btn(
            ttk.Button(ip_row, text="Add", style="Primary.TButton", command=self.on_add_ip)
        ).pack(side=tk.LEFT, padx=(0, 8))
        self._register_btn(
            ttk.Button(ip_row, text="Read OpenKore", style="Ghost.TButton", command=self.on_read_openkore)
        ).pack(side=tk.LEFT)
        tk.Label(
            ip_body,
            text="Change the IP and click Add for each client (multibox).",
            bg=C_CARD, fg=C_MUTED, font=(FONT, 8), wraplength=400, justify="left",
        ).pack(anchor="w", pady=(8, 0))

        act_body = self._section(self._tab_network_body, "Actions")
        self._register_btn(
            ttk.Button(act_body, text="Apply network from adapter", style="Primary.TButton", command=self.on_apply_network)
        ).pack(fill=tk.X, pady=(0, 10))
        self._register_btn(
            ttk.Button(act_body, text="Reset setup", style="Danger.TButton", command=self.on_reset_setup)
        ).pack(fill=tk.X)

        list_body = self._section(self._tab_network_body, "Added IPs")
        tree_wrap = tk.Frame(list_body, bg=C_CARD)
        tree_wrap.pack(fill=tk.BOTH, expand=True)
        cols = ("ip", "mask", "adapter")
        self.tree = ttk.Treeview(tree_wrap, columns=cols, show="headings", height=6, selectmode="browse")
        self.tree.heading("ip", text="IP")
        self.tree.heading("mask", text="Mask")
        self.tree.heading("adapter", text="Adapter")
        self.tree.column("ip", width=130)
        self.tree.column("mask", width=48)
        self.tree.column("adapter", width=160)
        scroll = ttk.Scrollbar(tree_wrap, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.list_count_var = tk.StringVar(value="0 IPs")
        tk.Label(list_body, textvariable=self.list_count_var, bg=C_CARD, fg=C_MUTED, font=(FONT, 8)).pack(anchor="w", pady=(6, 0))

        btn_row = tk.Frame(list_body, bg=C_CARD)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        self._register_btn(
            ttk.Button(btn_row, text="Remove selected", style="Ghost.TButton", command=self.on_remove_selected)
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._register_btn(
            ttk.Button(btn_row, text="Remove all", style="Ghost.TButton", command=self.on_remove_all)
        ).pack(side=tk.LEFT)

    def _build_tab_profiles(self) -> None:
        create_body = self._section(self._tab_profiles_body, "New profile")
        row = tk.Frame(create_body, bg=C_CARD)
        row.pack(fill=tk.X)
        tk.Label(row, text="Name:", bg=C_CARD, fg=C_TEXT, font=(FONT, 9), width=6, anchor="w").pack(side=tk.LEFT)
        self.profile_name_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.profile_name_var, font=(FONT_MONO, 10), width=18).pack(
            side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True,
        )
        self._register_btn(
            ttk.Button(row, text="Create from control", style="Primary.TButton", command=self.on_create_profile)
        ).pack(side=tk.RIGHT)
        tk.Label(
            create_body,
            text="Copies openkore/control/ → openkore/profiles/<name>/\n"
                 "Then run: perl openkore.pl --profile=<name>",
            bg=C_CARD, fg=C_MUTED, font=(FONT, 8), wraplength=400, justify="left",
        ).pack(anchor="w", pady=(8, 0))

        list_body = self._section(self._tab_profiles_body, "Existing profiles")
        tree_wrap = tk.Frame(list_body, bg=C_CARD)
        tree_wrap.pack(fill=tk.BOTH, expand=True)
        pcols = ("name", "char", "hook_ip")
        self.profile_tree = ttk.Treeview(tree_wrap, columns=pcols, show="headings", height=4, selectmode="browse")
        self.profile_tree.heading("name", text="Profile")
        self.profile_tree.heading("char", text="Char")
        self.profile_tree.heading("hook_ip", text="XKore_hookIp")
        self.profile_tree.column("name", width=100)
        self.profile_tree.column("char", width=40)
        self.profile_tree.column("hook_ip", width=120)
        pscroll = ttk.Scrollbar(tree_wrap, orient=tk.VERTICAL, command=self.profile_tree.yview)
        self.profile_tree.configure(yscrollcommand=pscroll.set)
        self.profile_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pscroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.profile_count_var = tk.StringVar(value="0 profiles")
        tk.Label(list_body, textvariable=self.profile_count_var, bg=C_CARD, fg=C_MUTED, font=(FONT, 8)).pack(
            anchor="w", pady=(6, 0),
        )

        prow = tk.Frame(list_body, bg=C_CARD)
        prow.pack(fill=tk.X, pady=(8, 0))
        self._register_btn(
            ttk.Button(prow, text="Refresh", style="Ghost.TButton", command=self.refresh_profiles)
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._register_btn(
            ttk.Button(prow, text="Use game IP", style="Ghost.TButton", command=self.on_use_profile_ip)
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._register_btn(
            ttk.Button(prow, text="Open folder", style="Ghost.TButton", command=self.on_open_profile_folder)
        ).pack(side=tk.LEFT)

        footer_inner = tk.Frame(self._tab_profiles_footer, bg=C_CARD, padx=12, pady=10)
        footer_inner.pack(fill=tk.X)
        launch_row = tk.Frame(footer_inner, bg=C_CARD)
        launch_row.pack(fill=tk.X)
        self._register_btn(
            ttk.Button(launch_row, text="Run OpenKore", style="Primary.TButton", command=self.on_run_openkore_profile)
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._register_btn(
            ttk.Button(launch_row, text="Run Ragexe", style="Primary.TButton", command=self.on_run_ragnarok_profile)
        ).pack(side=tk.LEFT)
        tk.Label(
            launch_row,
            text="OpenKore first, then Ragexe (bridge).",
            bg=C_CARD, fg=C_MUTED, font=(FONT, 8),
        ).pack(side=tk.LEFT, padx=(10, 0))

    def _fill_profile_tree(self, profiles: list) -> None:
        for item in self.profile_tree.get_children():
            self.profile_tree.delete(item)
        for p in profiles:
            self.profile_tree.insert("", tk.END, values=(p.name, p.char_slot or "—", p.hook_ip or "—"))
        n = len(profiles)
        self.profile_count_var.set(f"{n} profile(s)" if n else "0 profiles — create one above")

    def refresh_profiles(self) -> None:
        try:
            profiles = self._ctrl.list_profiles()
            self._fill_profile_tree(profiles)
        except Exception as e:
            self.log(str(e), "err")

    def on_create_profile(self) -> None:
        name = self.profile_name_var.get().strip()
        ok, err = self._ctrl.validate_profile_name(name)
        if not ok:
            self.log(err or "Invalid profile name.", "err")
            return

        def work():
            return self._ctrl.create_profile_from_control(name)

        def done(result):
            if isinstance(result, tuple) and result[0] == "err":
                self.log(result[1], "err")
                return
            ok, msg = result
            self.log(msg, "ok" if ok else "err")
            if ok:
                self.profile_name_var.set("")
                self.refresh_profiles()

        self._start_async(work, done, f"Creating profile {name}...")

    def _selected_profile_name(self) -> str | None:
        sel = self.profile_tree.selection()
        if not sel:
            return None
        return str(self.profile_tree.item(sel[0])["values"][0])

    def on_use_profile_ip(self) -> None:
        name = self._selected_profile_name()
        if not name:
            self.log("Select a profile in the list.", "warn")
            return
        ip = self._ctrl.read_profile_hook_ip(name)
        if ip:
            self.ip_var.set(ip)
            self.log(f"{name}: XKore_hookIp = {ip}", "ok")
        else:
            self.log(f"{name}: XKore_hookIp not set in config.txt", "warn")

    def on_open_profile_folder(self) -> None:
        name = self._selected_profile_name()
        if not name:
            self.log("Select a profile in the list.", "warn")
            return
        ok, msg = self._ctrl.open_profile_folder(name)
        self.log(msg, "ok" if ok else "err")

    def on_run_openkore_profile(self) -> None:
        name = self._selected_profile_name()
        if not name:
            self.log("Select a profile in the list.", "warn")
            return
        ok, msg = self._ctrl.launch_openkore_profile(name)
        self.log(msg, "ok" if ok else "err")

    def on_run_ragnarok_profile(self) -> None:
        name = self._selected_profile_name()
        if not name:
            self.log("Select a profile in the list.", "warn")
            return
        ok, msg = self._ctrl.launch_ragnarok_profile(name)
        self.log(msg, "ok" if ok else "err")
        if ok:
            self.log("Log in manually in the game client.", "info")

    # --- Helpers ---

    def log(self, msg: str, level: str = "info") -> None:
        prefix = {"ok": "[OK] ", "warn": "[!] ", "err": "[X] "}.get(level, "")
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, prefix + msg.rstrip() + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    def set_busy(self, busy: bool, label: str = "") -> None:
        self._busy = busy
        st = tk.DISABLED if busy else tk.NORMAL
        for btn in self._action_buttons:
            btn.configure(state=st)
        if busy:
            self.prog_frame.pack(fill=tk.X, pady=(6, 0))
            self.progress.pack(fill=tk.X)
            self.progress.start(12)
            self.progress_label.configure(text=label)
            self.progress_label.pack(anchor="w")
            self.set_status(label or "Working...")
        else:
            self.progress.stop()
            self.prog_frame.pack_forget()
            self.set_status("Ready.")

    def adapter_label(self, a: dict) -> str:
        return f"[{a['Index']}] {a['Name']} — {a.get('IPv4') or 'no IP'}"

    def selected_index(self) -> int | None:
        sel = self.adapter_var.get()
        for a in self.adapters:
            if sel == self.adapter_label(a):
                return int(a["Index"])
        return None

    def require_admin(self) -> bool:
        if self._ctrl.is_admin():
            return True
        self.log("Administrator required — click Run as admin.", "warn")
        self.set_status("Waiting for admin.")
        return False

    def _lan_from_adapter(self, if_index: int) -> dict | None:
        snap = self._ctrl.get_lan_snapshot(if_index)
        if not snap or not snap.get("IP"):
            return None
        mask = mask_from_snapshot(snap) or DEFAULT_LAN["mask"]
        gateway = (snap.get("Gateway") or "").strip() or DEFAULT_LAN["gateway"]
        return {
            "ip": snap["IP"],
            "mask": mask,
            "gateway": gateway,
            "dns": list(DEFAULT_DNS),
        }

    def _save_lan(self, lan: dict) -> None:
        self.cfg["lan"] = lan
        self._ctrl.save_config()

    def _resolve_lan(self, idx: int) -> dict:
        """Always read LAN from the adapter first — config may be stale after DHCP."""
        snap_lan = self._lan_from_adapter(idx)
        if snap_lan:
            saved_ip = (self.cfg.get("lan") or {}).get("ip")
            if saved_ip and saved_ip != snap_lan["ip"]:
                self.log(
                    f"Adapter IP is {snap_lan['ip']} (config had {saved_ip}) — using live value.",
                    "info",
                )
            return snap_lan
        return dict(self.cfg.get("lan") or DEFAULT_LAN)

    def _fill_tree(self, wl: list[dict]) -> None:
        self.whitelist = wl
        for item in self.tree.get_children():
            self.tree.delete(item)
        for w in wl:
            self.tree.insert("", tk.END, values=(
                w.get("IPAddress", ""),
                f"/{w.get('PrefixLength', '')}",
                w.get("InterfaceAlias", ""),
            ))
        self.list_count_var.set(f"{len(wl)} IP(s)" if wl else "0 IPs")

    def _update_status_line(self) -> None:
        idx = self.selected_index()
        if idx is None:
            self.net_status_var.set("")
            return
        dhcp, ips = self._ctrl.get_ipv4_mode(idx)
        _, dns_list = self._ctrl.get_dns_servers(idx)
        mode = "DHCP" if dhcp else "static"
        ip_show = ", ".join(ips) if ips else "—"
        dns_show = ", ".join(dns_list) if dns_list else "DHCP"
        self.net_status_var.set(f"IPv4: {mode} ({ip_show})  ·  DNS: {dns_show}")

    def _update_admin_badge(self) -> None:
        bg = C_OK if self._ctrl.is_admin() else C_WARN
        txt = "Admin" if self._ctrl.is_admin() else "Run as admin"
        self.admin_frame.configure(bg=bg)
        self.admin_lbl.configure(bg=bg, text=txt, fg=C_ON_ACCENT)

    def _start_async(self, work, done, label: str) -> None:
        if self._busy:
            return
        self.set_busy(True, label)

        def runner():
            try:
                result = work()
            except Exception as e:
                result = ("err", str(e))
            self.after(0, lambda: self._finish_async(done, result))

        threading.Thread(target=runner, daemon=True).start()

    def _finish_async(self, on_done, result) -> None:
        self.set_busy(False)
        on_done(result)

    # --- Actions ---

    def refresh(self) -> None:
        if self._busy:
            return
        last_idx = self.cfg.get("last_interface_index")

        def work():
            adapters = self._ctrl.list_adapters()
            wl = self._ctrl.list_whitelist_ips()
            pick = 0
            for i, a in enumerate(adapters):
                if last_idx and int(a["Index"]) == int(last_idx):
                    pick = i
            return adapters, wl, pick

        def done(data):
            if isinstance(data, tuple) and data and data[0] == "err":
                self.log(data[1], "err")
                return
            adapters, wl, pick = data
            self.adapters = adapters
            labels = [self.adapter_label(a) for a in adapters]
            self.adapter_combo["values"] = labels
            if labels:
                self.adapter_combo.current(pick)
            self._fill_tree(wl)
            self._update_admin_badge()
            self._update_status_line()

        self._start_async(work, done, "Refreshing...")

    def on_open_adapters(self) -> None:
        try:
            self._ctrl.open_network_panel()
            self.log("Opened Windows network adapters.", "ok")
            self.set_status("Network adapters panel opened.")
        except OSError as e:
            self.log(f"Could not open adapters panel: {e}", "err")

    def on_read_openkore(self) -> None:
        ip = self._ctrl.read_hook_ip()
        if ip:
            self.ip_var.set(ip)
            self.log(f"XKore_hookIp = {ip}", "ok")
        else:
            path = self.cfg.get("openkore_config", "")
            self.log(f"XKore_hookIp not found in {path}", "warn")

    def on_apply_network(self) -> None:
        if not self.require_admin():
            return
        idx = self.selected_index()
        if idx is None:
            self.log("Select an adapter.", "err")
            return
        lan = self._lan_from_adapter(idx)
        if not lan:
            self.log("Could not read network from adapter.", "err")
            return
        self.log(
            f"Applying {lan['ip']} / {lan['mask']} gw {lan['gateway']} | DNS 1.1.1.1 + 8.8.8.8...",
            "info",
        )

        def work():
            return self._ctrl.apply_lan_profile(idx, lan)

        def done(result):
            if isinstance(result, tuple) and result and result[0] == "err":
                self.log(result[1], "err")
                return
            ok, msg, _snap = result
            self.log(msg, "ok" if ok else "err")
            if ok:
                self.cfg["last_interface_index"] = idx
                self._save_lan(lan)
                self._update_status_line()
            self.refresh()

        self._start_async(work, done, "Applying network...")

    def on_add_ip(self) -> None:
        if not self.require_admin():
            return
        ip = self.ip_var.get().strip()
        if not self._ctrl.validate_whitelist_ip(ip):
            self.log("Invalid game IP (must be 172.65.X.Y).", "err")
            return
        idx = self.selected_index()
        if idx is None:
            self.log("Select an adapter.", "err")
            return

        lan = self._resolve_lan(idx)

        def work():
            existing = {
                w.get("IPAddress")
                for w in self._ctrl.list_whitelist_ips()
                if int(w.get("InterfaceIndex", -1)) == idx
            }
            if ip in existing:
                return "duplicate", ip, "already on adapter", idx, lan
            if existing:
                ok, st = self._ctrl.add_whitelist_ip(ip, idx)
                return "add", ip, st, idx, lan, ok
            ok, st, _snap = self._ctrl.apply_whitelist_ip(ip, idx, lan)
            return "full", ip, st, idx, lan, ok

        def done(result):
            if isinstance(result, tuple) and result[0] == "err":
                self.log(result[1], "err")
                return
            mode, ip, st, idx, lan, ok = result
            if mode == "duplicate":
                self.log(f"{ip}: {st}", "warn")
                return
            self.log(st, "ok" if ok else "err")
            if ok:
                self.cfg["whitelist_ip"] = ip
                self.cfg["last_interface_index"] = idx
                self._save_lan(lan)
                managed = set(self.cfg.get("managed_ips") or [])
                managed.add(ip)
                self.cfg["managed_ips"] = sorted(managed)
                self._ctrl.save_config()
            self.refresh()

        self._start_async(work, done, f"Adding {ip}...")

    def on_reset_setup(self) -> None:
        if not self.require_admin():
            return
        sel = self.selected_index()
        last = self.cfg.get("last_interface_index")
        last_idx = int(last) if last is not None else None
        self.log("Reset: removing game IPs, hosts, restoring DHCP on affected adapters...", "warn")

        def work():
            return self._ctrl.reset_setup(sel, last_idx)

        def done(result):
            if isinstance(result, tuple) and result and result[0] == "err":
                self.log(result[1], "err")
                return
            ip_logs, dhcp_logs = result
            for ip, ok, st in ip_logs:
                self.log(f"IP {ip}: {st}", "ok" if ok else "err")
            if not dhcp_logs:
                self.log("No adapters were reset — select your Wi-Fi/Ethernet and try again.", "warn")
            for idx, ok, msg in dhcp_logs:
                self.log(f"Adapter {idx}: {msg}", "ok" if ok else "err")
            self.cfg["managed_ips"] = []
            self.cfg["pinned_primary"] = None
            self.cfg["last_interface_index"] = None
            self._ctrl.save_config()
            self.log("Setup reset complete.", "ok")
            self.refresh()

        self._start_async(work, done, "Resetting setup...")

    def on_remove_selected(self) -> None:
        if not self.require_admin():
            return
        sel = self.tree.selection()
        if not sel:
            self.log("Select an IP in the list.", "warn")
            return
        ip = str(self.tree.item(sel[0])["values"][0])

        def work():
            return self._ctrl.remove_whitelist_ip(ip)

        def done(result):
            ok, st = result
            self.log(f"{ip}: {st}", "ok" if ok else "err")
            if ok:
                self.cfg["managed_ips"] = [x for x in (self.cfg.get("managed_ips") or []) if x != ip]
                self._ctrl.save_config()
            self.refresh()

        self._start_async(work, done, f"Removing {ip}...")

    def on_remove_all(self) -> None:
        if not self.require_admin():
            return
        if not self.whitelist:
            self.log("No game IPs on adapter.", "warn")
            return

        def work():
            logs = []
            for w in list(self.whitelist):
                ip = w.get("IPAddress", "")
                logs.append((ip, *self._ctrl.remove_whitelist_ip(ip)))
            self._ctrl.clean_hosts()
            return logs

        def done(result):
            if isinstance(result, tuple) and result and result[0] == "err":
                self.log(result[1], "err")
                return
            ok_n = sum(1 for _, ok, _ in result if ok)
            for ip, ok, st in result:
                self.log(f"{ip}: {st}", "ok" if ok else "err")
            self.cfg["managed_ips"] = []
            self._ctrl.save_config()
            self.log(f"Removed {ok_n}/{len(result)} IP(s).", "ok")
            self.refresh()

        self._start_async(work, done, "Removing all...")
