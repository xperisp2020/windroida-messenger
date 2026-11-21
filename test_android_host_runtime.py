"""Integration checks for Android host path wiring and embedded server lifecycle."""
import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")

PYTHON_DIR = Path(__file__).parent / "android" / "app" / "src" / "main" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class AndroidHostRuntimeTests(unittest.TestCase):
    def test_private_paths_and_embedded_server_start_stop(self):
        with tempfile.TemporaryDirectory(prefix="windroida-android-host-") as temp:
            import android_host

            root = android_host._configure_paths(temp)
            web = root / "web"
            web.mkdir(parents=True, exist_ok=True)
            (web / "index.html").write_text("host test", encoding="utf-8")

            import common
            import server
            import webgw

            self.assertEqual(common.BASE_DIR, root)
            self.assertEqual(common.DATA_DIR, root / "data")
            self.assertEqual(common.DB_PATH, root / "data" / "windroida.db")
            self.assertEqual(server.DATA_DIR, root / "data")
            self.assertEqual(Path(webgw.WEB_DIR), root / "web")
            self.assertTrue((root / "web" / "index.html").is_file())
            self.assertTrue((root / "data").is_dir())

            tcp_port = free_port()
            web_port = free_port()
            while web_port == tcp_port:
                web_port = free_port()
            result = json.loads(android_host.start_host(
                temp, "127.0.0.1", tcp_port, web_port
            ))
            self.assertTrue(result["running"])
            self.assertTrue(result["tls"])
            self.assertEqual(result["tcp_port"], tcp_port)
            self.assertEqual(result["web_port"], web_port)
            self.assertTrue((root / "data" / "admin_password.txt").is_file())
            self.assertTrue(json.loads(android_host.host_status())["running"])

            android_host.stop_host()
            self.assertFalse(json.loads(android_host.host_status())["running"])
            for port in (tcp_port, web_port):
                with self.assertRaises(OSError):
                    socket.create_connection(("127.0.0.1", port), timeout=1)


if __name__ == "__main__":
    unittest.main()
