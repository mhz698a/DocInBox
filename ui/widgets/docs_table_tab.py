"""Searchable table for managing documents received by DocInBox."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


def _format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _format_datetime(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone().strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return value


class DocsTableTab(QWidget):
    """Inbox list with text search and pending/handled filtering."""

    selection_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._documents: list[dict[str, Any]] = []
        self._visible_by_id: dict[str, dict[str, Any]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        toolbar = QHBoxLayout()
        title = QLabel("Documentos recibidos")
        title.setObjectName("SectionTitle")
        toolbar.addWidget(title)
        toolbar.addStretch(1)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar documento…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMinimumWidth(220)
        self.search_edit.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self.search_edit)

        self.status_filter = QComboBox()
        self.status_filter.addItem("Todos los estados", "all")
        self.status_filter.addItem("Pendientes", "pending")
        self.status_filter.addItem("Atendidos", "handled")
        self.status_filter.currentIndexChanged.connect(self._apply_filters)
        toolbar.addWidget(self.status_filter)
        root.addLayout(toolbar)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Documento", "Fecha de recepción", "Tamaño", "Estado"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setMinimumSectionSize(90)
        self.table.horizontalHeader().resizeSection(0, 360)
        self.table.horizontalHeader().resizeSection(1, 180)
        self.table.horizontalHeader().resizeSection(2, 100)
        self.table.itemSelectionChanged.connect(self.selection_changed.emit)
        root.addWidget(self.table, 1)

        self.empty_label = QLabel("Todavía no se han recibido documentos.")
        self.empty_label.setObjectName("EmptyState")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.empty_label)

    def set_documents(self, documents: list[dict[str, Any]]) -> None:
        current = self.selected_document()
        selected_id = current["id"] if current else None
        self._documents = list(documents)
        self._apply_filters(selected_id=selected_id)

    def _apply_filters(self, *_args, selected_id: str | None = None) -> None:
        search = self.search_edit.text().strip().casefold()
        status = self.status_filter.currentData()
        visible = [
            item
            for item in self._documents
            if (status == "all" or item["status"] == status)
            and search in item["filename"].casefold()
        ]
        self._visible_by_id = {item["id"]: item for item in visible}
        self.table.setRowCount(0)

        for document in visible:
            row = self.table.rowCount()
            self.table.insertRow(row)
            filename_item = QTableWidgetItem(document["filename"])
            filename_item.setData(Qt.ItemDataRole.UserRole, document["id"])
            filename_item.setToolTip(document["stored_path"])
            self.table.setItem(row, 0, filename_item)
            self.table.setItem(
                row, 1, QTableWidgetItem(_format_datetime(document["received_at"]))
            )
            self.table.setItem(row, 2, QTableWidgetItem(_format_size(document["size"])))
            status_text = "Atendido" if document["status"] == "handled" else "Pendiente"
            status_item = QTableWidgetItem(status_text)
            status_item.setData(Qt.ItemDataRole.UserRole, document["status"])
            self.table.setItem(row, 3, status_item)
            if document["id"] == selected_id:
                self.table.selectRow(row)

        self.empty_label.setVisible(not visible)
        self.table.setVisible(bool(visible))

    def selected_document(self) -> dict[str, Any] | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return self._visible_by_id.get(item.data(Qt.ItemDataRole.UserRole))
