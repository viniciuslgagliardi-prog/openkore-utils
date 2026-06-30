"""Entry point: python -m openkore_utils"""

from __future__ import annotations

import sys

from openkore_utils.controllers.app_controller import AppController
from openkore_utils.ui.main_window import MainWindow


def _enable_win_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            from ctypes import windll

            windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> None:
    _enable_win_dpi_awareness()
    ctrl = AppController()
    if not ctrl.is_admin():
        ctrl.relaunch_as_admin()
    app = MainWindow(ctrl)
    app.mainloop()


if __name__ == "__main__":
    main()
