from __future__ import annotations

import unittest

from services.serveo_tunnel import (
    build_ssh_command,
    extract_reserved_url,
)


class ServeoTunnelCommandTests(unittest.TestCase):
    def test_command_uses_registered_identity_and_reserved_hostname(self) -> None:
        command = build_ssh_command(
            "ssh.exe",
            8765,
            r"C:\Users\Test\AppData\Local\DocInBox\ssh\docinbox_ed25519",
            r"C:\Users\Test\AppData\Local\DocInBox\ssh\known_hosts",
            "docinbox-a1b2c3d4e5.serveo.net",
        )

        self.assertIn("IdentitiesOnly=yes", command)
        self.assertIn("BatchMode=yes", command)
        self.assertIn("StrictHostKeyChecking=yes", command)
        self.assertIn(
            "docinbox-a1b2c3d4e5.serveo.net:80:127.0.0.1:8765",
            command,
        )
        self.assertNotIn("-N", command)

    def test_command_rejects_arbitrary_or_anonymous_hostnames(self) -> None:
        with self.assertRaises(ValueError):
            build_ssh_command(
                "ssh",
                8765,
                "private_key",
                "known_hosts",
                "192-0-2-1.serveo.net",
            )

    def test_extract_only_accepts_the_reserved_hostname(self) -> None:
        line = "Forwarding HTTP traffic from https://docinbox-a1b2c3d4e5.serveo.net"
        self.assertEqual(
            extract_reserved_url(line, "docinbox-a1b2c3d4e5.serveo.net"),
            "https://docinbox-a1b2c3d4e5.serveo.net",
        )

    def test_extract_rejects_anonymous_or_unexpected_hostname(self) -> None:
        line = "Forwarding HTTP traffic from https://203-0-113-4.serveo.net"
        with self.assertRaises(RuntimeError):
            extract_reserved_url(line, "docinbox-a1b2c3d4e5.serveo.net")
        self.assertIsNone(
            extract_reserved_url(
                "Connecting to serveo.net...",
                "docinbox-a1b2c3d4e5.serveo.net",
            )
        )


if __name__ == "__main__":
    unittest.main()
