"""Runtime configuration for DocInBox."""

from __future__ import annotations

import os
from pathlib import Path


def _default_storage_dir() -> Path:
    """Return a per-user directory outside the source tree."""
    if os.name == "nt":
        local_app_data = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
        return local_app_data / "DocInBox" / "Received"

    return Path.home() / "Documents" / "DocInBox" / "Received"


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

    HOST = os.environ.get("DOCINBOX_HOST", "0.0.0.0")
    PORT = _positive_int("DOCINBOX_PORT", 8765)
    MAX_UPLOAD_MB = _positive_int("DOCINBOX_MAX_UPLOAD_MB", 100)
    MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
    # Allow multipart boundaries and headers in addition to the file payload.
    MAX_CONTENT_LENGTH = MAX_UPLOAD_BYTES + 1024 * 1024
    UPLOAD_FOLDER = Path(
        os.environ.get("DOCINBOX_STORAGE_DIR", str(_default_storage_dir()))
    ).expanduser()
