"""Runtime configuration for DocInBox."""

from __future__ import annotations

import os
from pathlib import Path


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
    HOST = os.environ.get("DOCINBOX_HOST", "0.0.0.0")
    PORT = _positive_int("DOCINBOX_PORT", 8765)
    MAX_UPLOAD_MB = _positive_int("DOCINBOX_MAX_UPLOAD_MB", 100)
    MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
    MAX_CONTENT_LENGTH = MAX_UPLOAD_BYTES + 1024 * 1024
    UPLOAD_FOLDER = Path(
        os.environ.get("DOCINBOX_STORAGE_DIR", str(APP_DATA_DIR / "Received"))
    ).expanduser()
    DATABASE_PATH = Path(
        os.environ.get(
            "DOCINBOX_DATABASE_PATH",
            str(APP_DATA_DIR / "inbox.sqlite3"),
        )
    ).expanduser()
