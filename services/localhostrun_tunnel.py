"""Keyless localhost.run SSH tunnel managed by a Qt worker thread."""

from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


_DOMAIN_PATTERN = re.compile(
    r"(?<![a-z0-9.-])((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+"
    r"(?:localhost\\.run|lhr\\.life))(?![a-z0-9.-])",
    re.IGNORECASE,
)


def _creation_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def build_ssh_command(
    ssh_executable: str,
    local_port: int,
    known_hosts_path: str | Path,
    ssh_port: int = 22,
) -> list[str]:
    """Build the documented free nokey tunnel command without shell parsing."""
    local_port = int(local_port)
    ssh_port = int(ssh_port)
    if not 1 <= local_port <= 65535:
        raise ValueError("El puerto local debe estar entre 1 y 65535.")
    if not 1 <= ssh_port <= 65535:
        raise ValueError("El puerto SSH debe estar entre 1 y 65535.")

    return [
        ssh_executable,
        "-T",
        "-p",
        str(ssh_port),
        "-o",
        "BatchMode=yes",
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ServerAliveInterval=60",
        "-o",
        "ServerAliveCountMax=3",
        "-o",
        "ConnectTimeout=15",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        f"UserKnownHostsFile={Path(known_hosts_path)}",
        "-R",
        f"80:127.0.0.1:{local_port}",
        "nokey@localhost.run",
        "--",
        "--no-inject-http-proxy-headers",
    ]


def extract_public_url(output_line: str) -> str | None:
    """Extract only an HTTPS hostname belonging to localhost.run's free domains."""
    match = _DOMAIN_PATTERN.search(output_line)
    if not match:
        return None

    hostname = match.group(1).lower().rstrip(".")
    return f"https://{hostname}"


class LocalhostRunTunnelThread(QThread):
    """Keep the keyless SSH tunnel alive without blocking the Qt interface."""

    tunnel_ready = pyqtSignal(str)
    tunnel_error = pyqtSignal(str)
    tunnel_stopped = pyqtSignal()

    def __init__(
        self,
        local_port: int,
        known_hosts_path: str | Path,
        ssh_port: int = 22,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.local_port = int(local_port)
        self.known_hosts_path = Path(known_hosts_path).expanduser()
        self.ssh_port = int(ssh_port)
        self._stop_requested = threading.Event()
        self._process: subprocess.Popen[str] | None = None

    def run(self) -> None:
        process: subprocess.Popen[str] | None = None
        output_queue: queue.Queue[str | None] = queue.Queue()
        ready = False
        recent_output: list[str] = []

        try:
            ssh = shutil.which("ssh")
            if not ssh:
                raise RuntimeError(
                    "No se encontró OpenSSH (ssh.exe). Instala OpenSSH Client "
                    "desde las características opcionales de Windows."
                )

            self.known_hosts_path.parent.mkdir(parents=True, exist_ok=True)
            command = build_ssh_command(
                ssh,
                self.local_port,
                self.known_hosts_path,
                self.ssh_port,
            )
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
                                "La conexión SSH con localhost.run se cerró. "
                                "El receptor permanece privado."
                            )
                        else:
                            details = " | ".join(recent_output[-3:])
                            message = (
                                "localhost.run no pudo establecer el túnel gratuito. "
                                "Comprueba la conexión a Internet y que OpenSSH pueda "
                                "conectarse al puerto SSH del servicio."
                            )
                            if details:
                                message += f" Detalle: {details}"
                            self.tunnel_error.emit(message)
                    break

                if not ready and time.monotonic() >= startup_deadline:
                    raise RuntimeError(
                        "localhost.run no anunció una URL pública en 60 segundos. "
                        "El receptor permanece privado."
                    )

        except Exception as exc:
            if not self._stop_requested.is_set():
                self.tunnel_error.emit(str(exc))
        finally:
            if process is not None:
                self._terminate_process(process)
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

    @staticmethod
    def _terminate_process(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
                process.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                pass
