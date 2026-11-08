"""Main DocInBox desktop window."""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode

from PyQt6.QtCore import QSettings, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
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
from services.file_policy import SUPPORTED_EXTENSIONS, normalized_extensions
from services.file_watcher import InboxWatcher
from services.lan_server import LanServerThread
from services.localhostrun_tunnel import LocalhostRunTunnelThread
from services.qr_pdf import generate_qr_pdf
from ui.widgets.docs_table_tab import DocsTableTab
from ui.widgets.file_types_dialog import FileTypesDialog
from ui.widgets.header_qr import HeaderQrWidget
from ui.widgets.stats_table_tab import StatsTableTab


def _format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


class MainWindow(QMainWindow):
    """Desktop control panel for the private receiver and localhost.run access."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DocInBox")
        self.resize(1180, 760)
        self.setMinimumSize(900, 620)

        self.settings = QSettings("DocInBox", "DocInBox")
        self.flask_app = create_app()
        self.document_store = self.flask_app.extensions["document_store"]
        self.server_thread: LanServerThread | None = None
        self.localhostrun_thread: LocalhostRunTunnelThread | None = None
        self.access_token = ""
        self._public_qr_url = ""
        self._last_tunnel_error = ""
        self._last_server_error = ""
        self._server_stop_pending = False

        self.allowed_extensions = self._load_allowed_extensions()
        self.flask_app.config["ALLOWED_EXTENSIONS"] = set(self.allowed_extensions)

        self._prompt_startup_cleanup()
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

    def _load_allowed_extensions(self) -> set[str]:
        stored = self.settings.value("uploads/allowed_extensions", None)
        if stored is None:
            return set(SUPPORTED_EXTENSIONS)
        if isinstance(stored, str):
            stored = [stored]
        allowed = normalized_extensions(stored)
        return set(allowed.intersection(SUPPORTED_EXTENSIONS))

    def _prompt_startup_cleanup(self) -> None:
        documents = self.document_store.list_documents()
        if not documents:
            return

        total_size = sum(int(document["size"]) for document in documents)
        answer = QMessageBox.warning(
            self,
            "Documentos de sesiones anteriores",
            (
                f"Hay {len(documents)} documento(s) almacenado(s) "
                f"({ _format_size(total_size) }).\n\n"
                "¿Deseas limpiar ahora todos los documentos recibidos?\n\n"
                "Se eliminarán permanentemente los archivos y sus registros. "
                "Esta acción no se puede deshacer."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        deleted_count, failed_files = self.document_store.clear_all_documents()
        if failed_files:
            details = "\n".join(failed_files[:8])
            if len(failed_files) > 8:
                details += f"\n… y {len(failed_files) - 8} archivo(s) más."
            QMessageBox.warning(
                self,
                "Limpieza incompleta",
                (
                    f"Se eliminaron {deleted_count} documento(s). "
                    f"No se pudieron eliminar {len(failed_files)} archivo(s):\n\n"
                    f"{details}"
                ),
            )

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

        self.server_button = QPushButton("Iniciar receptor")
        self.server_button.setObjectName("PrimaryButton")
        self.server_button.clicked.connect(self._toggle_server)
        header.addWidget(self.server_button)

        self.file_types_button = QPushButton("Permitir tipo de archivos")
        self.file_types_button.clicked.connect(self._configure_file_types)
        header.addWidget(self.file_types_button)

        self.print_qr_button = QPushButton("Imprimir Código QR")
        self.print_qr_button.setEnabled(False)
        self.print_qr_button.clicked.connect(self._print_qr_pdf)
        header.addWidget(self.print_qr_button)
        root.addLayout(header)

        self.status_label = QLabel(
            "El servidor permanecerá privado hasta confirmar el túnel seguro."
        )
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

    def _clear_public_qr(self) -> None:
        self._public_qr_url = ""
        if hasattr(self, "print_qr_button"):
            self.print_qr_button.setEnabled(False)

    def start_server(self) -> None:
        if self.server_thread and self.server_thread.isRunning():
            return

        self.flask_app.config["ACCESS_TOKEN"] = ""
        self.access_token = ""
        self._clear_public_qr()
        self.qr_widget.set_connection(None)
        self.status_label.setText("Iniciando receptor privado…")
        self.server_button.setText("Iniciando…")
        self.server_button.setEnabled(False)

        self.server_thread = LanServerThread(app=self.flask_app, parent=self)
        self.server_thread.server_ready.connect(self._server_ready)
        self.server_thread.server_error.connect(self._server_error)
        self.server_thread.server_stopped.connect(self._server_stopped)
        self.server_thread.start()

    def _server_ready(self, _bound_port: int) -> None:
        self._last_server_error = ""
        self.status_label.setText(
            "Receptor privado activo · conectando con localhost.run sin cuenta ni claves de usuario…"
        )
        self.server_button.setText("Detener receptor")
        self.server_button.setEnabled(True)
        self._start_localhostrun_tunnel()

    def _server_error(self, message: str) -> None:
        self._last_server_error = message
        self.flask_app.config["ACCESS_TOKEN"] = ""
        self.access_token = ""
        self._clear_public_qr()
        self.status_label.setText(message)
        self.server_button.setText("Cerrando receptor…")
        self.server_button.setEnabled(False)
        self.qr_widget.set_connection(None)
        if self.localhostrun_thread and self.localhostrun_thread.isRunning():
            self.localhostrun_thread.stop()

    def _server_stopped(self) -> None:
        self.flask_app.config["ACCESS_TOKEN"] = ""
        self.access_token = ""
        self._clear_public_qr()
        self.qr_widget.set_connection(None)
        if self.localhostrun_thread and self.localhostrun_thread.isRunning():
            self.localhostrun_thread.stop()
        self._server_stop_pending = True
        self.server_button.setText("Cerrando túnel…")
        self.server_button.setEnabled(False)
        QTimer.singleShot(150, self._finalize_server_stop)

    def _finalize_server_stop(self) -> None:
        server_running = bool(self.server_thread and self.server_thread.isRunning())
        tunnel_running = bool(self.localhostrun_thread and self.localhostrun_thread.isRunning())
        if server_running or tunnel_running:
            QTimer.singleShot(100, self._finalize_server_stop)
            return

        self._server_stop_pending = False
        self.server_button.setText("Iniciar receptor")
        self.server_button.setEnabled(True)
        self.status_label.setText(self._last_server_error or "Receptor detenido.")

    def _toggle_server(self) -> None:
        if self.server_thread and self.server_thread.isRunning():
            self.server_button.setEnabled(False)
            self.server_button.setText("Deteniendo…")
            self._clear_public_qr()
            self._server_stop_pending = bool(
                self.localhostrun_thread and self.localhostrun_thread.isRunning()
            )
            if self._server_stop_pending:
                self.localhostrun_thread.stop()
            self.flask_app.config["ACCESS_TOKEN"] = ""
            self.access_token = ""
            self.server_thread.stop()
        else:
            self.start_server()

    def _start_localhostrun_tunnel(self) -> None:
        """Use a persistent static token and static LAN IP for the printed QR."""
        if not self.server_thread or not self.server_thread.isRunning():
            return
        if self.localhostrun_thread and self.localhostrun_thread.isRunning():
            return
        
        # 1. Recuperar o generar un Token de acceso PERSISTENTE (para que el QR impreso nunca caduque)
        stored_token = self.settings.value("security/access_token", "")
        if not stored_token:
            stored_token = secrets.token_urlsafe(32)
            self.settings.setValue("security/access_token", stored_token)
            self.settings.sync()
        
        self.access_token = stored_token
        self.flask_app.config["ACCESS_TOKEN"] = self.access_token
        self._last_tunnel_error = ""
        
        self.status_label.setText("Cargando configuración de red local estática…")

        # Reutilizamos la estructura del hilo para pasar el puerto y obtener la IP estática
        self.localhostrun_thread = LocalhostRunTunnelThread(
            local_port=self.server_thread.bound_port or Config.PORT,
            parent=self,
        )
        self.localhostrun_thread.tunnel_ready.connect(self._localhostrun_ready)
        self.localhostrun_thread.tunnel_error.connect(self._localhostrun_error)
        self.localhostrun_thread.tunnel_stopped.connect(self._localhostrun_stopped)
        self.localhostrun_thread.start()

    def _localhostrun_ready(self, base_url: str) -> None:
        public_link = f"{base_url.rstrip('/')}/?{urlencode({'key': self.access_token})}"
        self._public_qr_url = public_link
        self.print_qr_button.setEnabled(True)
        self.qr_widget.set_connection(public_link, "Acceso HTTPS · localhost.run")
        self.status_label.setText("Receptor activo · enlace HTTPS de localhost.run disponible.")
        self.statusBar().showMessage(
            "El QR contiene únicamente la dirección HTTPS pública temporal.",
            6000,
        )

    def _localhostrun_error(self, message: str) -> None:
        self._last_tunnel_error = message
        self.flask_app.config["ACCESS_TOKEN"] = ""
        self.access_token = ""
        self._clear_public_qr()
        self.qr_widget.set_connection(None)
        self.status_label.setText(
            "El receptor permanece privado porque no se pudo establecer el túnel."
        )
        self.statusBar().showMessage(message, 12000)

    def _localhostrun_stopped(self) -> None:
        self.flask_app.config["ACCESS_TOKEN"] = ""
        self.access_token = ""
        self._clear_public_qr()
        self.qr_widget.set_connection(None)

        if self._server_stop_pending:
            QTimer.singleShot(150, self._finalize_server_stop)
            return

        if self.server_thread and self.server_thread.isRunning():
            if self._last_tunnel_error:
                self.status_label.setText(
                    "Receptor privado activo · el túnel localhost.run no está disponible."
                )
            else:
                self.status_label.setText(
                    "Receptor privado activo · conexión localhost.run detenida."
                )

    def _print_qr_pdf(self) -> None:
        """Save the active receiver QR to PDF and optionally open it."""
        public_url = self._public_qr_url.strip()
        if not public_url:
            self._clear_public_qr()
            self.statusBar().showMessage(
                "No hay un código QR público disponible para imprimir.", 5000
            )
            return

        default_path = Path.home() / "DocInBox_Codigo_QR.pdf"
        selected_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar código QR como PDF",
            str(default_path),
            "Documento PDF (*.pdf)",
        )
        if not selected_path:
            return

        output_path = Path(selected_path).expanduser()
        if output_path.suffix.lower() != ".pdf":
            output_path = output_path.with_suffix(".pdf")

        try:
            generated_path = generate_qr_pdf(public_url, output_path)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "No se pudo generar el PDF",
                f"No fue posible crear el documento del código QR:\n{exc}",
            )
            return

        answer = QMessageBox.question(
            self,
            "PDF generado",
            (
                f"El código QR se guardó correctamente en:\n{generated_path}\n\n"
                "¿Deseas abrir el documento ahora?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Yes:
            opened = QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(generated_path))
            )
            if not opened:
                QMessageBox.warning(
                    self,
                    "No se pudo abrir el PDF",
                    "El documento se generó, pero Windows no pudo abrirlo.",
                )
        else:
            self.statusBar().showMessage(
                f"PDF del código QR guardado en {generated_path}", 7000
            )

    def _configure_file_types(self) -> None:
        dialog = FileTypesDialog(self.allowed_extensions, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        self.allowed_extensions = dialog.selected_extensions()
        self.flask_app.config["ALLOWED_EXTENSIONS"] = set(self.allowed_extensions)
        ordered = [
            extension
            for extension in SUPPORTED_EXTENSIONS
            if extension in self.allowed_extensions
        ]
        self.settings.setValue("uploads/allowed_extensions", ordered)
        self.settings.sync()

        if ordered:
            detail = ", ".join(f".{extension}" for extension in ordered)
            self.statusBar().showMessage(
                f"Tipos permitidos actualizados: {detail}", 7000
            )
        else:
            self.statusBar().showMessage(
                "No hay extensiones habilitadas; el receptor rechazará todos los archivos.",
                7000,
            )

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
            if document["status"] == "handled"
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
        if self.localhostrun_thread and self.localhostrun_thread.isRunning():
            self.localhostrun_thread.stop()
            self.localhostrun_thread.wait(5000)
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
