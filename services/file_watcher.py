"""Poll the inbox repository and notify the desktop when arrivals change."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from services.document_store import DocumentStore


class InboxWatcher(QObject):
    """Lightweight Qt poller for the SQLite inbox; it never blocks Flask."""

    documents_changed = pyqtSignal(object)

    def __init__(
        self,
        store: DocumentStore,
        interval_ms: int = 1000,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.store = store
        self.timer = QTimer(self)
        self.timer.setInterval(max(250, int(interval_ms)))
        self.timer.timeout.connect(self.refresh)
        self._last_signature: tuple[tuple[Any, ...], ...] | None = None

    def start(self) -> None:
        self.refresh()
        self.timer.start()

    def stop(self) -> None:
        self.timer.stop()

    def refresh(self) -> None:
        try:
            documents = self.store.list_documents()
        except Exception:
            return

        signature = tuple(
            (
                item["id"],
                item["filename"],
                item["size"],
                item["received_at"],
                item["status"],
            )
            for item in documents
        )
        if signature != self._last_signature:
            self._last_signature = signature
            self.documents_changed.emit(documents)
