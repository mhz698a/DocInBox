from __future__ import annotations

import unittest

from services.localhostrun_tunnel import (
    build_ssh_command,
    extract_public_url,
)


class LocalhostRunTunnelTests(unittest.TestCase):
    def test_command_uses_keyless_user_and_loopback_forward(self) -> None:
        command = build_ssh_command(
            "ssh.exe",
            8765,
            r"C:\Users\Test\AppData\Local\DocInBox\ssh\localhostrun_known_hosts",
        )

        self.assertIn("nokey@localhost.run", command)
        self.assertIn("80:127.0.0.1:8765", command)
        self.assertIn("BatchMode=yes", command)
        self.assertIn("StrictHostKeyChecking=accept-new", command)
        self.assertIn("ServerAliveInterval=60", command)
        self.assertIn("--no-inject-http-proxy-headers", command)
        self.assertNotIn("-i", command)
        self.assertNotIn("ssh-keygen", command)
        self.assertNotIn("ssh-keyscan", command)

    def test_command_uses_configurable_ssh_port_and_known_hosts(self) -> None:
        command = build_ssh_command(
            "C:\\Windows\\System32\\OpenSSH\\ssh.exe",
            9000,
            r"C:\Data\DocInBox\known_hosts",
            ssh_port=2222,
        )

        self.assertIn("2222", command)
        self.assertIn(
            "UserKnownHostsFile=C:\\Data\\DocInBox\\known_hosts",
            command,
        )
        self.assertIn("80:127.0.0.1:9000", command)

    def test_extracts_localhost_run_domain(self) -> None:
        line = "yourapp.localhost.run tunneled with tls termination"
        self.assertEqual(
            extract_public_url(line),
            "https://yourapp.localhost.run",
        )

    def test_extracts_lhr_life_domain(self) -> None:
        line = "a1b2c3d4e5f6.lhr.life tunneled with tls termination"
        self.assertEqual(
            extract_public_url(line),
            "https://a1b2c3d4e5f6.lhr.life",
        )

    def test_extracts_https_url_from_ssh_output(self) -> None:
        line = "Forwarding HTTPS traffic from https://receive-123.lhr.life"
        self.assertEqual(
            extract_public_url(line),
            "https://receive-123.lhr.life",
        )

    def test_rejects_non_provider_domains_and_local_addresses(self) -> None:
        self.assertIsNone(extract_public_url("Connected to ssh.example.com"))
        self.assertIsNone(extract_public_url("127.0.0.1:8765"))
        self.assertIsNone(extract_public_url("192.168.1.20"))
        self.assertIsNone(extract_public_url("localhost:8765"))


if __name__ == "__main__":
    unittest.main()
