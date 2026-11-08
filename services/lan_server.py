"""Qt worker that hosts the Flask receiver on loopback only."""

from __future__ import annotations

from threading import Event, Thread

from PyQt6.QtCore import QThread, pyqtSignal
from werkzeug.serving import make_server

from app_flask import create_app
from config import Config


class LanServerThread(QThread):
    """Run the private WSGI server without exposing the host's LAN address."""

    server_ready = pyqtSignal(int)
    server_stopped = pyqtSignal()
    server_error = pyqtSignal(str)

    def __init__(
        self,
        host: str | None = "0.0.0.0",  # Forzar 0.0.0.0 para aceptar la red local
        port: int | None = None,
        app=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.host = host or Config.HOST
        self.port = Config.PORT if port is None else int(port)
        self.app = app if app is not None else create_app()
        self._server = None
        self._stop_requested = Event()
        self.bound_port: int | None = None

    def run(self) -> None:
        server = None
        try:
            server = make_server(self.host, self.port, self.app, threaded=True)
            self._server = server
            self.bound_port = int(server.server_port)
            self.server_ready.emit(self.bound_port)

            if self._stop_requested.is_set():
                Thread(target=server.shutdown, daemon=True).start()

            server.serve_forever()
        except OSError as exc:
            self.server_error.emit(f"No se pudo iniciar el receptor privado: {exc}")
        except Exception as exc:
            self.server_error.emit(f"Error en el receptor privado: {exc}")
        finally:
            if server is not None:
                server.server_close()
            self._server = None
            self.server_stopped.emit()

    def stop(self) -> None:
        """Request a clean shutdown without blocking the Qt GUI thread."""
        if self._stop_requested.is_set():
            return

        self._stop_requested.set()
        server = self._server
        if server is not None:
            Thread(target=server.shutdown, daemon=True).start()
