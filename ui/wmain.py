"""Main DocInBox desktop window."""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app_flask import create_app
from config import Config
from services.file_watcher import InboxWatcher
from services.lan_server import LanServerThread
from services.pinggy_tunnel import PinggyTunnelThread
from ui.widgets.docs_table_tab import DocsTableTab
from ui.widgets.header_qr import HeaderQrWidget
from ui.widgets.stats_table_tab import StatsTableTab


class MainWindow(QMainWindow):
    """Desktop control panel for the DocInBox receiver and its arrivals."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DocInBox")
        self.resize(1180, 760)
        self.setMinimumSize(900, 620)

        self.flask_app = create_app()
        self.document_store = self.flask_app.extensions["document_store"]
        self.server_thread: LanServerThread | None = None
        self.tunnel_thread: PinggyTunnelThread | None = None
        self.local_url = ""
        self.public_url = ""
        self.access_token = ""

        self._build_ui()
        self._load_stylesheet()

        self.inbox_watcher = InboxWatcher(
            self.document_store,
            interval_ms=1000,
            parent=self,
        )
        self.inbox_watcher.documents_changed.connect(self._documents_changed)
        self.inbox_watcher.start()
        QTimer.singleShot(100, self.start_server)

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(16)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("DocInBox")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Administración de documentos recibidos")
        subtitle.setObjectName("AppSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)

        self.server_button = QPushButton("Detener receptor")
        self.server_button.setObjectName("PrimaryButton")
        self.server_button.clicked.connect(self._toggle_server)
        self.server_button.setEnabled(False)
        header.addWidget(self.server_button)

        self.tunnel_button = QPushButton("Publicar con Pinggy")
        self.tunnel_button.clicked.connect(self._toggle_tunnel)
        self.tunnel_button.setEnabled(False)
        header.addWidget(self.tunnel_button)
        root.addLayout(header)

        self.status_label = QLabel("Iniciando servidor local…")
        self.status_label.setObjectName("StatusLine")
        root.addWidget(self.status_label)

        self.stats_widget = StatsTableTab()
        root.addWidget(self.stats_widget)

        content = QHBoxLayout()
        content.setSpacing(16)
        self.docs_widget = DocsTableTab()
        self.docs_widget.selection_changed.connect(self._update_actions)
        content.addWidget(self.docs_widget, 1)
        self.qr_widget = HeaderQrWidget()
        content.addWidget(self.qr_widget, 0)
        root.addLayout(content, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.open_button = QPushButton("Abrir documento")
        self.open_button.clicked.connect(self._open_selected)
        self.show_button = QPushButton("Mostrar ubicación")
        self.show_button.clicked.connect(self._show_selected_location)
        self.copy_button = QPushButton("Copiar ruta")
        self.copy_button.clicked.connect(self._copy_selected_path)
        self.handled_button = QPushButton("Marcar como atendido")
        self.handled_button.clicked.connect(self._toggle_handled)
        self.delete_button = QPushButton("Eliminar")
        self.delete_button.setObjectName("DangerButton")
        self.delete_button.clicked.connect(self._delete_selected)
        for button in (
            self.open_button,
            self.show_button,
            self.copy_button,
            self.handled_button,
            self.delete_button,
        ):
            button.setEnabled(False)
            actions.addWidget(button)
        root.addLayout(actions)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Bandeja preparada.")

    def _load_stylesheet(self) -> None:
        stylesheet = Path(__file__).resolve().parent / "styles.css"
        try:
            self.setStyleSheet(stylesheet.read_text(encoding="utf-8"))
        except OSError:
            self.statusBar().showMessage("No se pudo cargar ui/styles.css")

    def start_server(self) -> None:
        if self.server_thread and self.server_thread.isRunning():
            return
        self.status_label.setText("Iniciando receptor Flask…")
        self.server_button.setEnabled(False)
        self.tunnel_button.setEnabled(False)
        self.server_thread = LanServerThread(app=self.flask_app, parent=self)
        self.server_thread.server_ready.connect(self._server_ready)
        self.server_thread.server_error.connect(self._server_error)
        self.server_thread.server_stopped.connect(self._server_stopped)
        self.server_thread.start()

    def _server_ready(self, url: str) -> None:
        self.local_url = url.rstrip("/")
        self.qr_widget.set_connection(self.local_url, "Acceso en red local")
        self.status_label.setText(f"Receptor activo · {self.local_url}")
        self.server_button.setText("Detener receptor")
        self.server_button.setEnabled(True)
        self.tunnel_button.setText("Publicar con Pinggy")
        self.tunnel_button.setEnabled(True)

    def _server_error(self, message: str) -> None:
        self.status_label.setText(message)
        self.server_button.setText("Iniciar receptor")
        self.server_button.setEnabled(True)
        self.tunnel_button.setEnabled(False)
        self.qr_widget.set_connection(None)

    def _server_stopped(self) -> None:
        self.local_url = ""
        if self.tunnel_thread and self.tunnel_thread.isRunning():
            self.stop_tunnel()
        self.server_button.setText("Iniciar receptor")
        self.server_button.setEnabled(True)
        self.tunnel_button.setEnabled(False)
        self.qr_widget.set_connection(None)
        if not self.status_label.text().startswith("No se pudo"):
            self.status_label.setText("Receptor detenido.")

    def _toggle_server(self) -> None:
        if self.server_thread and self.server_thread.isRunning():
            self.server_button.setEnabled(False)
            self.server_thread.stop()
            if self.tunnel_thread and self.tunnel_thread.isRunning():
                self.stop_tunnel()
        else:
            self.start_server()

    def _toggle_tunnel(self) -> None:
        if self.tunnel_thread and self.tunnel_thread.isRunning():
            self.stop_tunnel()
        else:
            self.start_tunnel()

    def start_tunnel(self) -> None:
        if not self.server_thread or not self.server_thread.isRunning():
            self.statusBar().showMessage(
                "Primero debe estar activo el receptor local.", 5000
            )
            return
        if self.tunnel_thread and self.tunnel_thread.isRunning():
            return

        self.access_token = secrets.token_urlsafe(32)
        self.flask_app.config["ACCESS_TOKEN"] = self.access_token
        if self.local_url:
            local_link = f"{self.local_url}/?{urlencode({'key': self.access_token})}"
            self.qr_widget.set_connection(local_link, "Acceso local protegido")
        self.tunnel_button.setEnabled(False)
        self.status_label.setText("Conectando con Pinggy…")
        self.tunnel_thread = PinggyTunnelThread(
            self.server_thread.bound_port or Config.PORT,
            parent=self,
        )
        self.tunnel_thread.tunnel_ready.connect(self._tunnel_ready)
        self.tunnel_thread.tunnel_error.connect(self._tunnel_error)
        self.tunnel_thread.tunnel_stopped.connect(self._tunnel_stopped)
        self.tunnel_thread.start()

    def _tunnel_ready(self, base_url: str) -> None:
        self.public_url = base_url.rstrip("/")
        public_link = f"{self.public_url}/?{urlencode({'key': self.access_token})}"
        self.qr_widget.set_connection(public_link, "Acceso público · Pinggy")
        self.status_label.setText("Túnel Pinggy activo · enlace temporal protegido.")
        self.tunnel_button.setText("Detener túnel")
        self.tunnel_button.setEnabled(True)
        self.statusBar().showMessage(
            "El QR ahora apunta al enlace público de Pinggy.", 6000
        )

    def _tunnel_error(self, message: str) -> None:
        self.status_label.setText(message)
        self.statusBar().showMessage(message, 10000)

    def stop_tunnel(self) -> None:
        if self.tunnel_thread and self.tunnel_thread.isRunning():
            self.tunnel_button.setEnabled(False)
            self.status_label.setText("Deteniendo túnel Pinggy…")
            self.tunnel_thread.stop()
        else:
            self._clear_tunnel_state()

    def _tunnel_stopped(self) -> None:
        self._clear_tunnel_state()

    def _clear_tunnel_state(self) -> None:
        self.flask_app.config["ACCESS_TOKEN"] = ""
        self.access_token = ""
        self.public_url = ""
        if self.local_url:
            self.qr_widget.set_connection(self.local_url, "Acceso en red local")
            self.status_label.setText(f"Receptor activo · {self.local_url}")
            self.tunnel_button.setText("Publicar con Pinggy")
            self.tunnel_button.setEnabled(True)
        else:
            self.qr_widget.set_connection(None)
            self.tunnel_button.setEnabled(False)

    def _documents_changed(self, documents: list[dict]) -> None:
        self.docs_widget.set_documents(documents)
        self.stats_widget.set_documents(documents)
        self._update_actions()

    def _selected_document(self) -> dict | None:
        return self.docs_widget.selected_document()

    def _update_actions(self) -> None:
        document = self._selected_document()
        enabled = document is not None
        for button in (
            self.open_button,
            self.show_button,
            self.copy_button,
            self.handled_button,
            self.delete_button,
        ):
            button.setEnabled(enabled)
        if enabled:
            self.handled_button.setText(
                "Marcar como pendiente"
                if document["status"] == "handled"
                else "Marcar como atendido"
            )

    def _open_selected(self) -> None:
        document = self._selected_document()
        if not document:
            return
        path = Path(document["stored_path"])
        if not path.is_file():
            self.statusBar().showMessage(
                "El archivo ya no existe en la carpeta de recepción.", 6000
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _show_selected_location(self) -> None:
        document = self._selected_document()
        if not document:
            return
        path = Path(document["stored_path"])
        if not path.exists():
            self.statusBar().showMessage("El archivo ya no existe.", 5000)
            return
        if os.name == "nt":
            subprocess.Popen(["explorer.exe", "/select,", str(path)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def _copy_selected_path(self) -> None:
        document = self._selected_document()
        if document:
            QApplication.clipboard().setText(document["stored_path"])
            self.statusBar().showMessage("Ruta copiada.", 3000)

    def _toggle_handled(self) -> None:
        document = self._selected_document()
        if not document:
            return
        new_status = (
            self.document_store.PENDING
            if document["status"] == self.document_store.HANDLED
            else self.document_store.HANDLED
        )
        self.document_store.set_status(document["id"], new_status)
        self.inbox_watcher.refresh()

    def _delete_selected(self) -> None:
        document = self._selected_document()
        if not document:
            return
        answer = QMessageBox.question(
            self,
            "Eliminar documento",
            f"¿Eliminar permanentemente «{document['filename']}» de la bandeja?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.document_store.delete_document(document["id"])
        except OSError as exc:
            QMessageBox.critical(
                self,
                "No se pudo eliminar",
                f"No fue posible eliminar el archivo:\n{exc}",
            )
            return
        self.inbox_watcher.refresh()

    def closeEvent(self, event) -> None:
        self.inbox_watcher.stop()
        if self.tunnel_thread and self.tunnel_thread.isRunning():
            self.tunnel_thread.stop()
            self.tunnel_thread.wait(5000)
        if self.server_thread and self.server_thread.isRunning():
            self.server_thread.stop()
            self.server_thread.wait(5000)
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("DocInBox")
    app.setOrganizationName("DocInBox")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
