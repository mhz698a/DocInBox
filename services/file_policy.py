"""Allowed file types for the DocInBox receiving endpoint."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


SUPPORTED_EXTENSIONS = (
    "doc",
    "docx",
    "xlsx",
    "xls",
    "ppt",
    "pptx",
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "gif",
    "txt",
    "mp3",
    "wav",
    "flac",
    "m4a",
    "mp4",
    "mkv",
    "avi",
)


def normalized_extensions(values: Iterable[str]) -> frozenset[str]:
    """Normalize extension preferences loaded from settings or app config."""
    return frozenset(
        str(value).strip().lower().lstrip(".")
        for value in values
        if str(value).strip()
    )


def is_extension_allowed(filename: str, allowed: Iterable[str]) -> bool:
    """Return whether a filename has an explicitly enabled extension."""
    extension = Path(filename).suffix.lower().lstrip(".")
    return bool(extension) and extension in normalized_extensions(allowed)
