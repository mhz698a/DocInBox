"""Local static IP announcer for fixed printed QR codes in LAN environments."""

from __future__ import annotations

import socket
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal


class LocalhostRunTunnelThread(QThread):
    """Provides the fixed local network IP for permanent printed QR codes."""

    tunnel_ready = pyqtSignal(str)
    tunnel_error = pyqtSignal(str)
    tunnel_stopped = pyqtSignal()

    def __init__(
        self,
        local_port: int,
        known_hosts_path: str | Path = "",
        ssh_port: int = 22,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.local_port = int(local_port)

    def run(self) -> None:
        try:
            # Obtener la IP estática actual de la PC servidor en la red local
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("10.255.255.255", 1))
                ip_local = s.getsockname()[0]
            except Exception:
                ip_local = "127.0.0.1"
            finally:
                s.close()

            # Construir la URL base permanente
            base_url = f"http://{ip_local}:{self.local_port}"
            self.tunnel_ready.emit(base_url)

        except Exception as exc:
            self.tunnel_error.emit(f"No se pudo obtener la IP local estática: {exc}")
            self.tunnel_stopped.emit()

    def stop(self) -> None:
        """Clean stop for the thread."""
        self.tunnel_stopped.emit()