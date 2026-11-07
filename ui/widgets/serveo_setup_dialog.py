"""One-time registration instructions for DocInBox's Serveo SSH identity."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices


class ServeoSetupDialog(QDialog):
    """Require the generated public key to be registered before tunneling."""

    def __init__(self, public_key: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configurar acceso privado de Serveo")
        self.setMinimumSize(600, 420)

        root = QVBoxLayout(self)
        intro = QLabel(
            "Para evitar que Serveo publique la IP de origen de un túnel anónimo, "
            "DocInBox usará una identidad SSH registrada y un subdominio reservado. "
            "La clave privada permanecerá en este equipo."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        steps = QLabel(
            "1. Copia la clave pública de abajo.\n"
            "2. Inicia sesión en Serveo y agrega la clave SSH a tu cuenta.\n"
            "3. Regresa aquí y confirma el registro."
        )
        steps.setWordWrap(True)
        root.addWidget(steps)

        self.public_key_edit = QPlainTextEdit()
        self.public_key_edit.setReadOnly(True)
        self.public_key_edit.setPlainText(public_key)
        self.public_key_edit.setMaximumHeight(95)
        root.addWidget(self.public_key_edit)

        actions = QHBoxLayout()
        copy_button = QPushButton("Copiar clave pública")
        open_button = QPushButton("Abrir consola Serveo")
        copy_button.clicked.connect(
            lambda: QApplication.clipboard().setText(public_key)
        )
        open_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://console.serveo.net/"))
        )
        actions.addWidget(copy_button)
        actions.addWidget(open_button)
        actions.addStretch(1)
        root.addLayout(actions)

        self.registered_checkbox = QCheckBox(
            "Ya agregué esta clave pública a mi cuenta de Serveo."
        )
        self.registered_checkbox.toggled.connect(self._update_accept_state)
        root.addWidget(self.registered_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.accept_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.accept_button.setText("Continuar")
        self.accept_button.setEnabled(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _update_accept_state(self, checked: bool) -> None:
        self.accept_button.setEnabled(bool(checked))
