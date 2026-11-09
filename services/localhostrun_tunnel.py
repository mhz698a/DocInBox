"""Legacy-named Qt worker that detects the current LAN IPv4 address."""

from __future__ import annotations

import ipaddress
import socket

from PyQt6.QtCore import QThread, pyqtSignal


def detect_lan_ipv4() -> str:
    """Detect the IPv4 address selected by the operating system for LAN traffic.

    The UDP socket is used only to ask the routing table which local interface
    would be used. No application payload is sent to the probe destination.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))
        address = probe.getsockname()[0]
        return str(ipaddress.IPv4Address(address))
    except (OSError, ValueError):
        return "127.0.0.1"
    finally:
        probe.close()


def build_lan_url(ip_address: str, port: int) -> str:
    """Build the HTTP URL advertised to devices in the same local network."""
    address = str(ipaddress.IPv4Address(ip_address))
    port_number = int(port)
    if not 1 <= port_number <= 65535:
        raise ValueError("El puerto debe estar entre 1 y 65535.")
    return f"http://{address}:{port_number}"


class LocalhostRunTunnelThread(QThread):
    """Return the detected LAN address without blocking the Qt interface.

    The class name is retained for import compatibility with earlier revisions;
    this implementation does not start an external tunnel provider.
    """

    tunnel_ready = pyqtSignal(str)
    tunnel_error = pyqtSignal(str)
    tunnel_stopped = pyqtSignal()

    def __init__(self, local_port: int, parent=None) -> None:
        super().__init__(parent)
        self.local_port = int(local_port)

    def run(self) -> None:
        try:
            base_url = build_lan_url(detect_lan_ipv4(), self.local_port)
            self.tunnel_ready.emit(base_url)
        except Exception as exc:
            self.tunnel_error.emit(
                f"No se pudo obtener la dirección de red local: {exc}"
            )
            self.tunnel_stopped.emit()

    def stop(self) -> None:
        """Notify the owning window that LAN address detection is no longer used."""
        self.tunnel_stopped.emit()
