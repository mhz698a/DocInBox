"""Compact inbox statistics cards."""

from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class _StatCard(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("StatLabel")
        self.value_label = QLabel("0")
        self.value_label.setObjectName("StatValue")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: int) -> None:
        self.value_label.setText(str(value))


class StatsTableTab(QWidget):
    """Summary of total, pending and handled documents."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.total_card = _StatCard("TOTAL RECIBIDOS")
        self.pending_card = _StatCard("PENDIENTES")
        self.handled_card = _StatCard("ATENDIDOS")
        for card in (self.total_card, self.pending_card, self.handled_card):
            layout.addWidget(card)

    def set_documents(self, documents: list[dict[str, Any]]) -> None:
        total = len(documents)
        handled = sum(item["status"] == "handled" for item in documents)
        self.total_card.set_value(total)
        self.pending_card.set_value(total - handled)
        self.handled_card.set_value(handled)
