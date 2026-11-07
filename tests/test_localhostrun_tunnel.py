from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.localhostrun_tunnel import (
    build_tmole_command,
    extract_public_url,
    resolve_tmole_binary,
)


class TunnelmoleBinaryTests(unittest.TestCase):
    def test_command_uses_bundled_tmole_exe_and_receiver_port(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            binary = root / "bin" / "tmole.exe"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"MZ")

            command = build_tmole_command(8765, root)

            self.assertEqual(command, [str(binary.resolve()), "8765"])

    def test_resolves_tmole_binary_from_project_bin_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            binary = root / "bin" / "tmole.exe"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"MZ")

            self.assertEqual(resolve_tmole_binary(root), binary.resolve())

    def test_missing_bundled_binary_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(FileNotFoundError, "tmole.exe"):
                resolve_tmole_binary(temporary_directory)


class TunnelmoleUrlTests(unittest.TestCase):
    def test_extracts_tunnelmole_net_url(self) -> None:
        self.assertEqual(
            extract_public_url(
                "Forwarding HTTPS traffic from https://receive-123.tunnelmole.net"
            ),
            "https://receive-123.tunnelmole.net",
        )

    def test_extracts_tunnelmole_com_url(self) -> None:
        self.assertEqual(
            extract_public_url("https://receive-123.tunnelmole.com"),
            "https://receive-123.tunnelmole.com",
        )

    def test_removes_trailing_output_punctuation(self) -> None:
        self.assertEqual(
            extract_public_url("Tunnel ready: https://receive-123.tunnelmole.net."),
            "https://receive-123.tunnelmole.net",
        )

    def test_rejects_localhostrun_local_addresses_and_unrelated_domains(self) -> None:
        self.assertIsNone(extract_public_url("https://example.localhost.run"))
        self.assertIsNone(extract_public_url("http://127.0.0.1:8765"))
        self.assertIsNone(extract_public_url("https://192.168.1.20"))
        self.assertIsNone(extract_public_url("https://tunnelmole.net.evil.test"))


if __name__ == "__main__":
    unittest.main()
