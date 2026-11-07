"""localhost.run connection QR widget."""

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
    """Show only the public localhost.run URL; never display the local host address."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("QrCard")
        self._url = ""
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        self.mode_label = QLabel("ESPERANDO CONEXIÓN")
        self.mode_label.setObjectName("QrMode")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.mode_label)

        self.qr_label = QLabel("Esperando la dirección pública temporal.")
        self.qr_label.setObjectName("QrImage")
        self.qr_label.setFixedSize(346, 188)
        self.qr_label.setWordWrap(True)
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.qr_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.url_label = QLabel(
            "La dirección HTTPS aparecerá cuando se establezca el túnel."
        )
        self.url_label.setObjectName("QrUrl")
        self.url_label.setWordWrap(True)
        self.url_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.url_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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

    def set_connection(self, url: str | None, mode: str = "localhost.run") -> None:
        self._url = (url or "").strip()
        self.mode_label.setText(mode.upper() if self._url else "ESPERANDO CONEXIÓN")
        self.url_label.setText(
            self._url or "La dirección pública no está disponible."
        )
        self.copy_button.setEnabled(bool(self._url))
        self.open_button.setEnabled(bool(self._url))
        if not self._url:
            self.qr_label.setPixmap(QPixmap())
            self.qr_label.setText("Esperando la dirección pública temporal.")
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
