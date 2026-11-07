"""Runtime configuration for DocInBox."""

from __future__ import annotations

import os
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


class Config:
    """Application defaults; environment variables can override each value."""

    APP_DATA_DIR = Path(
        os.environ.get("DOCINBOX_DATA_DIR", str(_default_app_data_dir()))
    ).expanduser()

    # Flask is deliberately loopback-only. Public access is provided by Serveo.
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

    SERVEO_SSH_DIR = APP_DATA_DIR / "ssh"
    SERVEO_SSH_KEY = Path(
        os.environ.get(
            "DOCINBOX_SERVEO_SSH_KEY",
            str(SERVEO_SSH_DIR / "docinbox_ed25519"),
        )
    ).expanduser()
    SERVEO_KNOWN_HOSTS = SERVEO_SSH_DIR / "known_hosts"
    SERVEO_HOST = "serveo.net"
    SERVEO_SSH_PORT = _positive_int("DOCINBOX_SERVEO_SSH_PORT", 22)
    # Ed25519 host key fingerprint published in Serveo's Windows SSH guide.
    SERVEO_HOST_KEY_FINGERPRINT = (
        "SHA256:GnmVK+70U6GqbupoV+gg7LnHHUsW1IjrK0cLqvDJxIk"
    )
