"""Pinggy tunnel lifecycle isolated from the Qt main thread."""

from __future__ import annotations

from threading import Event, Thread

from PyQt6.QtCore import QThread, pyqtSignal


class PinggyTunnelThread(QThread):
    """Create an HTTPS Pinggy tunnel and expose its assigned public URL."""

    tunnel_ready = pyqtSignal(str)
    tunnel_error = pyqtSignal(str)
    tunnel_stopped = pyqtSignal()

    def __init__(self, local_port: int, parent=None) -> None:
        super().__init__(parent)
        self.local_port = int(local_port)
        self._tunnel = None
        self._stop_requested = Event()

    def run(self) -> None:
        tunnel = None
        try:
            import pinggy

            tunnel = pinggy.Tunnel()
            self._tunnel = tunnel
            tunnel.add_forwarding(f"127.0.0.1:{self.local_port}")
            tunnel.httpsonly = True
            tunnel.auto_reconnect = True
            tunnel.start(thread=True, block_until_ready=True)

            if self._stop_requested.is_set():
                self._stop_tunnel(tunnel)
                return

            urls = list(tunnel.urls or [])
            public_url = next(
                (str(url) for url in urls if str(url).lower().startswith("https://")),
                None,
            )
            if not public_url and urls:
                public_url = str(urls[0])
            if not public_url:
                raise RuntimeError(
                    "Pinggy conectó el túnel, pero no devolvió una URL pública."
                )

            self.tunnel_ready.emit(public_url.rstrip("/"))
            tunnel.wait()
        except ImportError:
            self.tunnel_error.emit(
                "No está instalado el SDK de Pinggy. Ejecuta: "
                "python -m pip install pinggy"
            )
        except Exception as exc:
            self.tunnel_error.emit(f"No se pudo iniciar el túnel Pinggy: {exc}")
        finally:
            self._tunnel = None
            self.tunnel_stopped.emit()

    def stop(self) -> None:
        """Stop the SDK tunnel without joining its worker on the GUI thread."""
        self._stop_requested.set()
        tunnel = self._tunnel
        if tunnel is not None:
            Thread(target=self._stop_tunnel, args=(tunnel,), daemon=True).start()

    @staticmethod
    def _stop_tunnel(tunnel) -> None:
        try:
            tunnel.stop()
        except Exception:
            pass
