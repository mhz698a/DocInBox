"""Runtime configuration for DocInBox."""

from __future__ import annotations

import os, sys
from pathlib import Path

from services.file_policy import SUPPORTED_EXTENSIONS


def _default_app_data_dir() -> Path:
    if os.name == "nt":
        local_app_data = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
        return local_app_data / "DocInBox"
    return Path.home() / ".local" / "share" / "DocInBox"


def _positive_int(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser un número entero.") from exc
    if value <= 0:
        raise ValueError(f"{name} debe ser mayor que cero.")
    return value

def get_program_path():
    """
    Retorna la ruta absoluta del directorio donde se encuentra el script,
    funcionando tanto en modo de desarrollo (.py) como compilado (.exe).
    """
    # Si el script está compilado, sys tiene el atributo 'frozen'
    if getattr(sys, 'frozen', False):
        # PyInstaller guarda la ruta del ejecutable en sys.executable
        # Si usas _MEIPASS, apuntaría a la carpeta temporal de extracción
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        # En modo no compilado, usamos __file__
        return os.path.dirname(os.path.abspath(__file__))

class Config:
    """Application defaults; environment variables can override each value."""

    APP_DATA_DIR = Path(
        os.environ.get("DOCINBOX_DATA_DIR", str(_default_app_data_dir()))
    ).expanduser()

    # Flask is deliberately loopback-only. Public access is provided by localhost.run.
    HOST = "127.0.0.1"
    PORT = _positive_int("DOCINBOX_PORT", 8765)
    MAX_UPLOAD_MB = _positive_int("DOCINBOX_MAX_UPLOAD_MB", 100)
    MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
    MAX_CONTENT_LENGTH = MAX_UPLOAD_BYTES + 1024 * 1024
    ALLOWED_EXTENSIONS = frozenset(SUPPORTED_EXTENSIONS)

    UPLOAD_FOLDER = Path(
        os.environ.get("DOCINBOX_STORAGE_DIR", str(APP_DATA_DIR / "Received"))
    ).expanduser()
    DATABASE_PATH = Path(
        os.environ.get(
            "DOCINBOX_DATABASE_PATH",
            str(APP_DATA_DIR / "inbox.sqlite3"),
        )
    ).expanduser()

    LOCALHOSTRUN_SSH_PORT = _positive_int(
        "DOCINBOX_LOCALHOSTRUN_SSH_PORT",
        22,
    )
    # OpenSSH stores the server key on first connection (TOFU) and rejects changes.
    LOCALHOSTRUN_KNOWN_HOSTS = APP_DATA_DIR / "ssh" / "localhostrun_known_hosts"
