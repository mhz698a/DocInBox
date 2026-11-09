from __future__ import annotations

import socket
import unittest
from unittest.mock import Mock, patch

from services.localhostrun_tunnel import build_lan_url, detect_lan_ipv4


class LanAddressTests(unittest.TestCase):
    @patch("services.localhostrun_tunnel.socket.socket")
    def test_detects_ipv4_selected_by_routing_table(self, socket_factory) -> None:
        probe = Mock()
        probe.getsockname.return_value = ("192.168.1.25", 0)
        socket_factory.return_value = probe

        self.assertEqual(detect_lan_ipv4(), "192.168.1.25")
        socket_factory.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect.assert_called_once_with(("10.255.255.255", 1))
        probe.close.assert_called_once()

    @patch("services.localhostrun_tunnel.socket.socket")
    def test_falls_back_to_loopback_when_no_lan_route_is_available(
        self, socket_factory
    ) -> None:
        probe = Mock()
        probe.connect.side_effect = OSError("No route")
        socket_factory.return_value = probe

        self.assertEqual(detect_lan_ipv4(), "127.0.0.1")
        probe.close.assert_called_once()

    def test_builds_http_url_for_lan_devices(self) -> None:
        self.assertEqual(
            build_lan_url("192.168.1.25", 8765),
            "http://192.168.1.25:8765",
        )

    def test_rejects_invalid_addresses_and_ports(self) -> None:
        with self.assertRaises(ValueError):
            build_lan_url("not-an-ip", 8765)
        with self.assertRaises(ValueError):
            build_lan_url("192.168.1.25", 0)
        with self.assertRaises(ValueError):
            build_lan_url("192.168.1.25", 65536)


if __name__ == "__main__":
    unittest.main()
