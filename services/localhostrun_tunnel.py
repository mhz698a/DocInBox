"""Keyless Tunnelmole tunnel managed by a Qt worker thread."""

from __future__ import annotations

import os
import queue
import re
import subprocess
import threading
import time
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

# Captura las URLs asignadas por el servicio de Tunnelmole.
_DOMAIN_PATTERN = re.compile(
    r"https://[a-zA-Z0-9.-]+\.(?:tunnelmole\.net|tunnelmole\.com)",
    re.IGNORECASE,
)


def _creation_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def resolve_tmole_binary(application_root: str | Path | None = None) -> Path:
    """Return the Tunnelmole executable shipped in the project's bin directory."""
    root = (
        Path(application_root).expanduser().resolve()
        if application_root is not None
        else Path(__file__).resolve().parents[1]
    )
    executable = root / "bin" / "tmole.exe"
    if not executable.is_file():
        raise FileNotFoundError(
            f"No se encontró el binario de Tunnelmole: {executable}"
        )
    return executable


def extract_public_url(output: str) -> str | None:
    """Extract a public Tunnelmole URL from one line of process output."""
    match = _DOMAIN_PATTERN.search(output)
    return match.group(0).rstrip(".,;") if match else None


class LocalhostRunTunnelThread(QThread):
    """Keep the Tunnelmole tunnel alive without blocking the Qt interface."""

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
        self._stop_requested = threading.Event()
        self._process: subprocess.Popen[str] | None = None

    def run(self) -> None:
        process: subprocess.Popen[str] | None = None
        output_queue: queue.Queue[str | None] = queue.Queue()
        ready = False
        recent_output: list[str] = []

        try:
            # Utiliza el ejecutable incluido en DocInBox, no una instalación global.
            tmole_path = resolve_tmole_binary()
            command = [str(tmole_path), str(self.local_port)]

            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=_creation_flags(),
            )
            self._process = process

            def read_output() -> None:
                assert process is not None and process.stdout is not None
                try:
                    for line in process.stdout:
                        output_queue.put(line)
                finally:
                    output_queue.put(None)

            threading.Thread(target=read_output, daemon=True).start()
            startup_deadline = time.monotonic() + 60

            while not self._stop_requested.is_set():
                try:
                    line = output_queue.get(timeout=0.2)
                except queue.Empty:
                    line = ""

                if line:
                    clean_line = line.strip()
                    if clean_line:
                        recent_output.append(clean_line)
                        recent_output = recent_output[-6:]

                    public_url = extract_public_url(line)
                    if public_url and not ready:
                        ready = True
                        self.tunnel_ready.emit(public_url)

                return_code = process.poll()
                if return_code is not None:
                    if not self._stop_requested.is_set():
                        if ready:
                            self.tunnel_error.emit(
                                "La conexión con Tunnelmole se cerró de manera imprevista."
                            )
                        else:
                            details = " | ".join(recent_output[-3:])
                            message = "Tunnelmole no pudo establecer el enlace público."
                            if details:
                                message += f" Detalle: {details}"
                            self.tunnel_error.emit(message)
                    break

                if not ready and time.monotonic() >= startup_deadline:
                    raise RuntimeError(
                        "Tunnelmole no devolvió una URL pública dentro del tiempo límite."
                    )

        except Exception as exc:
            if not self._stop_requested.is_set():
                self.tunnel_error.emit(str(exc))
        finally:
            if process is not None:
                try:
                    process.terminate()
                except OSError:
                    pass
            self._process = None
            self.tunnel_stopped.emit()

    def stop(self) -> None:
        """Request tunnel shutdown without blocking the Qt GUI thread."""
        self._stop_requested.set()
        process = self._process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass
