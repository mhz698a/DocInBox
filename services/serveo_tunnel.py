"""Authenticated Serveo SSH tunnel managed by a Qt worker thread."""

from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


_URL_PATTERN = re.compile(
    r"https://([a-z0-9][a-z0-9.-]*\.serveo\.net)(?::\d+)?",
    re.IGNORECASE,
)
_HOSTNAME_PATTERN = re.compile(r"docinbox-[a-f0-9]{10}\.serveo\.net", re.IGNORECASE)


def _creation_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def ensure_serveo_identity(private_key_path: str | Path) -> tuple[Path, str, bool]:
    """Ensure an Ed25519 keypair exists and return (private_path, public_key, created)."""
    private_path = Path(private_key_path).expanduser()
    public_path = Path(f"{private_path}.pub")
    private_path.parent.mkdir(parents=True, exist_ok=True)

    if private_path.exists() and public_path.exists():
        return private_path, public_path.read_text(encoding="utf-8").strip(), False

    if private_path.exists() and not public_path.exists():
        raise RuntimeError(
            "Existe la clave privada de Serveo, pero falta su archivo .pub. "
            "No se reemplazó para evitar perder la identidad registrada."
        )

    ssh_keygen = shutil.which("ssh-keygen")
    if not ssh_keygen:
        raise RuntimeError(
            "No se encontró ssh-keygen. Instala la característica OpenSSH Client "
            "de Windows o agrega OpenSSH al PATH."
        )

    result = subprocess.run(
        [
            ssh_keygen,
            "-q",
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            "DocInBox",
            "-f",
            str(private_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=_creation_flags(),
        check=False,
    )
    if result.returncode != 0 or not public_path.is_file():
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            "No se pudo generar la identidad SSH de DocInBox."
            + (f" {detail}" if detail else "")
        )

    if os.name != "nt":
        try:
            private_path.chmod(0o600)
            private_path.parent.chmod(0o700)
        except OSError:
            pass

    return private_path, public_path.read_text(encoding="utf-8").strip(), True


def build_ssh_command(
    ssh_executable: str,
    local_port: int,
    private_key_path: str | Path,
    known_hosts_path: str | Path,
    public_hostname: str,
    ssh_port: int = 22,
) -> list[str]:
    """Build a shell-free command requesting a reserved Serveo hostname."""
    if not _HOSTNAME_PATTERN.fullmatch(public_hostname):
        raise ValueError("El subdominio solicitado para Serveo no es válido.")

    global_known_hosts = "NUL" if os.name == "nt" else "/dev/null"
    remote_forward = f"{public_hostname}:80:127.0.0.1:{int(local_port)}"

    return [
        ssh_executable,
        "-T",
        "-p",
        str(int(ssh_port)),
        "-i",
        str(Path(private_key_path)),
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "BatchMode=yes",
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ServerAliveCountMax=3",
        "-o",
        "ConnectTimeout=15",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        f"UserKnownHostsFile={Path(known_hosts_path)}",
        "-o",
        f"GlobalKnownHostsFile={global_known_hosts}",
        "-R",
        remote_forward,
        "--",
        "serveo.net",
        "--https-only",
    ]


def extract_reserved_url(output_line: str, expected_hostname: str) -> str | None:
    """Accept only the exact requested Serveo hostname; never an anonymous URL."""
    match = _URL_PATTERN.search(output_line)
    if not match:
        return None
    hostname = match.group(1).lower()
    if hostname != expected_hostname.lower():
        raise RuntimeError(
            "Serveo devolvió un hostname distinto al reservado. "
            "Se rechazó para evitar publicar una dirección anónima."
        )
    return f"https://{hostname}"


class ServeoTunnelThread(QThread):
    """Keep an authenticated reverse SSH tunnel alive without blocking Qt."""

    tunnel_ready = pyqtSignal(str)
    tunnel_error = pyqtSignal(str)
    tunnel_stopped = pyqtSignal()

    def __init__(
        self,
        local_port: int,
        private_key_path: str | Path,
        known_hosts_path: str | Path,
        public_hostname: str,
        ssh_port: int = 22,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.local_port = int(local_port)
        self.private_key_path = Path(private_key_path)
        self.known_hosts_path = Path(known_hosts_path)
        self.public_hostname = public_hostname.lower()
        self.ssh_port = int(ssh_port)
        self._stop_requested = threading.Event()
        self._process: subprocess.Popen[str] | None = None

    def run(self) -> None:
        process = None
        reader_queue: queue.Queue[str | None] = queue.Queue()
        ready = False
        try:
            self._prepare_known_hosts()
            ssh = shutil.which("ssh")
            if not ssh:
                raise RuntimeError(
                    "No se encontró OpenSSH (ssh.exe). Instala OpenSSH Client "
                    "en las características opcionales de Windows."
                )

            command = build_ssh_command(
                ssh,
                self.local_port,
                self.private_key_path,
                self.known_hosts_path,
                self.public_hostname,
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
                    for output_line in process.stdout:
                        reader_queue.put(output_line)
                finally:
                    reader_queue.put(None)

            threading.Thread(target=read_output, daemon=True).start()
            startup_deadline = time.monotonic() + 60

            while not self._stop_requested.is_set():
                try:
                    output_line = reader_queue.get(timeout=0.2)
                except queue.Empty:
                    output_line = ""

                if output_line:
                    public_url = extract_reserved_url(
                        output_line,
                        self.public_hostname,
                    )
                    if public_url and not ready:
                        ready = True
                        self.tunnel_ready.emit(public_url)

                return_code = process.poll()
                if return_code is not None:
                    if not self._stop_requested.is_set():
                        if ready:
                            self.tunnel_error.emit(
                                "La conexión SSH con Serveo se cerró. "
                                "El receptor permanece privado."
                            )
                        else:
                            self.tunnel_error.emit(
                                "Serveo no pudo establecer el túnel reservado. "
                                "Verifica que la clave pública de DocInBox esté "
                                "registrada en tu cuenta de Serveo y que el "
                                "subdominio solicitado esté disponible."
                            )
                    break

                if not ready and time.monotonic() >= startup_deadline:
                    raise RuntimeError(
                        "Serveo no confirmó el subdominio reservado en 60 segundos."
                    )

        except Exception as exc:
            if not self._stop_requested.is_set():
                self.tunnel_error.emit(str(exc))
        finally:
            if process is not None:
                self._terminate_process(process)
            self._process = None
            self.tunnel_stopped.emit()

    def _prepare_known_hosts(self) -> None:
        ssh_keyscan = shutil.which("ssh-keyscan")
        ssh_keygen = shutil.which("ssh-keygen")
        if not ssh_keyscan or not ssh_keygen:
            raise RuntimeError(
                "OpenSSH no incluye ssh-keyscan o ssh-keygen en el PATH. "
                "Repara o reinstala OpenSSH Client."
            )

        result = subprocess.run(
            [
                ssh_keyscan,
                "-p",
                str(self.ssh_port),
                "-t",
                "ed25519",
                "serveo.net",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=_creation_flags(),
            check=False,
        )
        key_lines = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if result.returncode != 0 or not key_lines:
            raise RuntimeError(
                "No se pudo consultar la clave SSH de Serveo para verificar el servidor."
            )

        self.known_hosts_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            dir=self.known_hosts_path.parent,
            suffix=".known_hosts.tmp",
        ) as temp_file:
            temp_file.write("\n".join(key_lines) + "\n")
            temporary_path = Path(temp_file.name)

        try:
            fingerprint_result = subprocess.run(
                [ssh_keygen, "-lf", str(temporary_path)],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=_creation_flags(),
                check=False,
            )
            fingerprints = re.findall(
                r"SHA256:[A-Za-z0-9+/]+",
                fingerprint_result.stdout,
            )
            expected = "SHA256:GnmVK+70U6GqbupoV+gg7LnHHUsW1IjrK0cLqvDJxIk"
            if fingerprint_result.returncode != 0 or expected not in fingerprints:
                observed = ", ".join(fingerprints) if fingerprints else "no disponible"
                raise RuntimeError(
                    "La huella SSH de Serveo no coincide con la publicada "
                    f"en su documentación. Huella observada: {observed}. "
                    "Se canceló la conexión por seguridad."
                )
            temporary_path.replace(self.known_hosts_path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def stop(self) -> None:
        """Request tunnel shutdown; the worker owns final process cleanup."""
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
