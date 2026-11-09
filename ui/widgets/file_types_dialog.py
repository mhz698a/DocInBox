"""Dialog for choosing which file extensions the receiver accepts."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.file_policy import SUPPORTED_EXTENSIONS


class FileTypesDialog(QDialog):
    """Checkbox-based allowed-extension configuration."""

    def __init__(
        self,
        selected_extensions: set[str] | frozenset[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Permitir tipo de archivos")
        self.setMinimumWidth(430)
        self._checkboxes: dict[str, QCheckBox] = {}

        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "Selecciona las extensiones que podrán enviarse al receptor. "
                "La validación también se realiza en el servidor."
            )
        )

        grid = QGridLayout()
        grid.setHorizontalSpacing(22)
        grid.setVerticalSpacing(9)
        for index, extension in enumerate(SUPPORTED_EXTENSIONS):
            checkbox = QCheckBox(f".{extension}")
            checkbox.setChecked(extension in selected_extensions)
            self._checkboxes[extension] = checkbox
            grid.addWidget(checkbox, index // 4, index % 4)
        root.addLayout(grid)

        quick_actions = QHBoxLayout()
        select_all = QPushButton("Seleccionar todos")
        clear_all = QPushButton("Desmarcar todos")
        select_all.clicked.connect(self._select_all)
        clear_all.clicked.connect(self._clear_all)
        quick_actions.addWidget(select_all)
        quick_actions.addWidget(clear_all)
        quick_actions.addStretch(1)
        root.addLayout(quick_actions)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _select_all(self) -> None:
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(True)

    def _clear_all(self) -> None:
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(False)

    def selected_extensions(self) -> set[str]:
        return {
            extension
            for extension, checkbox in self._checkboxes.items()
            if checkbox.isChecked()
        }
