"""Cross-platform integration test for stopping a TLS-enabled messenger server."""
import socket
import ssl
import tempfile
import unittest
from pathlib import Path

import server


class ServerTlsShutdownTests(unittest.TestCase):
    def test_stop_closes_idle_tls_client_and_listener(self):
        with tempfile.TemporaryDirectory(prefix="windroida-tls-stop-") as temp:
            instance = server.WindroidaServer(
                "127.0.0.1", 0, tls=True,
                db_path=Path(temp) / "windroida.db",
                web_port=None,
            )
            instance.seed_admin()
            port = instance.start()
            client = None
            try:
                context = ssl._create_unverified_context()
                client = context.wrap_socket(
                    socket.create_connection(("127.0.0.1", port), timeout=5),
                    server_hostname="127.0.0.1",
                )
                client.settimeout(5)
                with instance.conns_lock:
                    self.assertEqual(len(instance.open_sockets), 1)

                instance.stop()
                try:
                    received = client.recv(1)
                except (OSError, ssl.SSLError):
                    received = b""
                self.assertEqual(received, b"", "server stop must close the established TLS client")

                with self.assertRaises(OSError):
                    socket.create_connection(("127.0.0.1", port), timeout=1)
            finally:
                if client is not None:
                    client.close()
                instance.stop()


if __name__ == "__main__":
    unittest.main()
