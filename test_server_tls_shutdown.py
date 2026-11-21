"""Cross-platform integration test for stopping a TLS-enabled messenger server."""
import socket
import ssl
import tempfile
import time
import unittest
from pathlib import Path

import server


class ServerTlsShutdownTests(unittest.TestCase):
    def test_stop_closes_idle_tls_client_and_listener(self):
        with tempfile.TemporaryDirectory(prefix="windroida-tls-stop-") as temp:
            instance = server.WindroidaServer(
                "127.0.0.1", 0, tls=True,
                db_path=Path(temp) / "windroida.db",
                web_port=0,
            )
            instance.seed_admin()
            port = instance.start()
            web_port = instance.web.port
            client = None
            web_client = None
            try:
                context = ssl._create_unverified_context()
                client = context.wrap_socket(
                    socket.create_connection(("127.0.0.1", port), timeout=5),
                    server_hostname="127.0.0.1",
                )
                client.settimeout(5)
                web_client = context.wrap_socket(
                    socket.create_connection(("127.0.0.1", web_port), timeout=5),
                    server_hostname="127.0.0.1",
                )
                web_client.settimeout(5)
                deadline = time.time() + 5
                while time.time() < deadline:
                    with instance.conns_lock:
                        tcp_tracked = len(instance.open_sockets)
                    with instance.web._conn_lock:
                        web_tracked = len(instance.web._sockets)
                    if tcp_tracked == 1 and web_tracked == 1:
                        break
                    time.sleep(0.05)
                self.assertEqual(tcp_tracked, 1, "TCP TLS socket was not tracked")
                self.assertEqual(web_tracked, 1, "HTTPS TLS socket was not tracked")

                instance.stop()
                for label, active_client in (("TCP", client), ("HTTPS", web_client)):
                    try:
                        received = active_client.recv(1)
                    except (OSError, ssl.SSLError):
                        received = b""
                    self.assertEqual(received, b"", f"server stop must close the established {label} TLS client")

                deadline = time.time() + 5
                while time.time() < deadline:
                    with instance.conns_lock:
                        remaining = len(instance.open_sockets)
                    if remaining == 0:
                        break
                    time.sleep(0.05)
                self.assertEqual(remaining, 0, "server retained TLS socket references after shutdown")
                deadline = time.time() + 5
                while time.time() < deadline:
                    with instance.web._conn_lock:
                        web_remaining = len(instance.web._sockets)
                    if web_remaining == 0:
                        break
                    time.sleep(0.05)
                self.assertEqual(web_remaining, 0, "web gateway retained TLS socket references after shutdown")

                for stopped_port in (port, web_port):
                    with self.assertRaises(OSError):
                        socket.create_connection(("127.0.0.1", stopped_port), timeout=1)
            finally:
                if client is not None:
                    client.close()
                if web_client is not None:
                    web_client.close()
                instance.stop()


if __name__ == "__main__":
    unittest.main()
