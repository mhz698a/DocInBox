"""Qt worker that hosts the Flask receiver without blocking the GUI thread."""

from __future__ import annotations

import socket
from threading import Event, Thread

from PyQt6.QtCore import QThread, pyqtSignal
from werkzeug.serving import make_server

from app_flask import create_app
from config import Config


class LanServerThread(QThread):
    """Run the DocInBox WSGI server in a dedicated Qt thread."""

    server_ready = pyqtSignal(str)
    server_stopped = pyqtSignal()
    server_error = pyqtSignal(str)

    def __init__(
        self,
        host: str | None = None,
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
            address = self._advertised_host()
            self.server_ready.emit(f"http://{address}:{self.bound_port}")

            if self._stop_requested.is_set():
                Thread(target=server.shutdown, daemon=True).start()

            # Always enter serve_forever, including a stop requested during startup.
            server.serve_forever()
        except OSError as exc:
            self.server_error.emit(f"No se pudo iniciar el servidor LAN: {exc}")
        except Exception as exc:
            self.server_error.emit(f"Error en el servidor LAN: {exc}")
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

    def _advertised_host(self) -> str:
        """Resolve a usable LAN address when the server binds to all interfaces."""
        if self.host not in ("0.0.0.0", ""):
            return self.host

        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # UDP connect only asks the OS for the route; it sends no packet.
            probe.connect(("192.0.2.1", 80))
            return str(probe.getsockname()[0])
        except OSError:
            try:
                return socket.gethostbyname(socket.gethostname())
            except OSError:
                return "127.0.0.1"
        finally:
            probe.close()
