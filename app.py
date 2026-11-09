"""DocInBox desktop entry point. Use --web-only for Flask without Qt."""

from __future__ import annotations

import sys
import ctypes

myappid = "doc_in_box.doc_in_box.doc_in_box.1.0"
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

def main() -> int:
    if "--web-only" in sys.argv:
        from app_flask import main as run_web_server
        run_web_server()
        return 0

    from ui.wmain import main as run_desktop
    return run_desktop()


if __name__ == "__main__":
    raise SystemExit(main())
