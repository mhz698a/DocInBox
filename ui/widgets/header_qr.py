"""Connection QR widget for LAN and Pinggy addresses."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class HeaderQrWidget(QFrame):
    """Show the active receiver address and a QR code for it."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("QrCard")
        self._url = ""
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        self.mode_label = QLabel("SIN SERVIDOR")
        self.mode_label.setObjectName("QrMode")
        root.addWidget(self.mode_label)

        self.qr_label = QLabel("Inicia el receptor para generar el QR.")
        self.qr_label.setObjectName("QrImage")
        self.qr_label.setFixedSize(188, 188)
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.qr_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.url_label = QLabel("El enlace aparecerá aquí.")
        self.url_label.setObjectName("QrUrl")
        self.url_label.setWordWrap(True)
        self.url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self.url_label)

        buttons = QHBoxLayout()
        self.copy_button = QPushButton("Copiar enlace")
        self.open_button = QPushButton("Abrir")
        self.copy_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.copy_button.clicked.connect(self._copy_url)
        self.open_button.clicked.connect(self._open_url)
        buttons.addWidget(self.copy_button)
        buttons.addWidget(self.open_button)
        root.addLayout(buttons)

    def set_connection(self, url: str | None, mode: str = "LAN") -> None:
        self._url = (url or "").strip()
        self.mode_label.setText(mode.upper() if self._url else "SIN SERVIDOR")
        self.url_label.setText(self._url or "El enlace aparecerá aquí.")
        self.copy_button.setEnabled(bool(self._url))
        self.open_button.setEnabled(bool(self._url))
        if not self._url:
            self.qr_label.setPixmap(QPixmap())
            self.qr_label.setText("Inicia el receptor para generar el QR.")
            return

        try:
            import qrcode

            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=5,
                border=2,
            )
            qr.add_data(self._url)
            qr.make(fit=True)
            image = qr.make_image(
                fill_color="#111827",
                back_color="#f5f7fb",
            ).convert("RGB")
            width, height = image.size
            qimage = QImage(
                image.tobytes(),
                width,
                height,
                width * 3,
                QImage.Format.Format_RGB888,
            ).copy()
            pixmap = QPixmap.fromImage(qimage).scaled(
                180,
                180,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
            self.qr_label.setText("")
            self.qr_label.setPixmap(pixmap)
        except Exception as exc:
            self.qr_label.setPixmap(QPixmap())
            self.qr_label.setText(f"No se pudo generar el QR: {exc}")

    def _copy_url(self) -> None:
        if self._url:
            QApplication.clipboard().setText(self._url)

    def _open_url(self) -> None:
        if self._url:
            QDesktopServices.openUrl(QUrl(self._url))
