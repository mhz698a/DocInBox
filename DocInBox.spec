# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-folder build for the DocInBox Windows desktop application.

Run from the repository root:
    python -m PyInstaller --noconfirm --clean DocInBox.spec

Only runtime resources are copied. Source tests, documentation, Git metadata,
virtual environments, and build caches are intentionally left out.
"""

from pathlib import Path

ROOT = Path(SPECPATH).resolve()

ENTRY_POINT = ROOT / "app.py"
TEMPLATES_DIR = ROOT / "templates"
UI_STYLESHEET = ROOT / "ui" / "styles.css"
APP_ICON = ROOT / "assets" / "icon.ico"

REQUIRED_PATHS = (
    ENTRY_POINT,
    TEMPLATES_DIR / "index.html",
    TEMPLATES_DIR / "app.js",
    TEMPLATES_DIR / "s.css",
    TEMPLATES_DIR / "favicon.ico",
    UI_STYLESHEET,
    APP_ICON,
)
MISSING_PATHS = [str(path) for path in REQUIRED_PATHS if not path.exists()]
if MISSING_PATHS:
    raise FileNotFoundError(
        "Missing DocInBox build resources:\n" + "\n".join(MISSING_PATHS)
    )

# Keep the Flask web UI beside app_flask.py and the desktop stylesheet beside
# ui/wmain.py. The icon is under the bundle directory's assets/ folder.
DATAS = [
    (str(TEMPLATES_DIR), "templates"),
    (str(UI_STYLESHEET), "ui"),
    (str(APP_ICON), "assets"),
]

# qrcode loads its Pillow image backend lazily. PyMuPDF is imported through
# the legacy-compatible "fitz" name; include the native binding explicitly.
HIDDEN_IMPORTS = [
    "qrcode.image.pil",
    "pymupdf.mupdf",
]

# These are optional development, notebook, plotting, or alternative-GUI
# dependencies and are not used by DocInBox.
EXCLUDES = [
    "tkinter",
    "PyQt5",
    "PySide2",
    "PySide6",
    "wx",
    "pytest",
    "IPython",
    "jupyter",
    "notebook",
    "matplotlib",
    "numpy",
    "scipy",
    "pandas",
]

a = Analysis(
    [str(ENTRY_POINT)],
    pathex=[str(ROOT)],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DocInBox",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(APP_ICON)],
    contents_directory="_internal",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="DocInBox",
)
