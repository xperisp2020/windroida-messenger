"""Isolated integration checks for Android host path wiring and server lifecycle."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
PYTHON_DIR = REPO_ROOT / "android" / "app" / "src" / "main" / "python"

CHILD_TEST = r"""
import json
import socket
import sys
from pathlib import Path

root_dir = Path(sys.argv[1])
import android_host

root = android_host._configure_paths(root_dir)
web = root / "web"
web.mkdir(parents=True, exist_ok=True)
(web / "index.html").write_text("Windroida host test", encoding="utf-8")

import common
import server
import webgw

assert common.BASE_DIR == root
assert common.DATA_DIR == root / "data"
assert common.DB_PATH == root / "data" / "windroida.db"
assert server.DATA_DIR == root / "data"
assert Path(webgw.WEB_DIR) == root / "web"
assert (root / "data").is_dir()

def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]

tcp_port = free_port()
web_port = free_port()
while web_port == tcp_port:
    web_port = free_port()

result = json.loads(android_host.start_host(
    str(root_dir), "127.0.0.1", tcp_port, web_port
))
assert result["running"] and result["tls"]
assert result["tcp_port"] == tcp_port
assert result["web_port"] == web_port
assert (root / "data" / "admin_password.txt").is_file()
assert json.loads(android_host.host_status())["running"]

android_host.stop_host()
assert not json.loads(android_host.host_status())["running"]
for port in (tcp_port, web_port):
    try:
        socket.create_connection(("127.0.0.1", port), timeout=1).close()
    except OSError:
        pass
    else:
        raise AssertionError(f"listener on port {port} remained open after stop")
"""

class AndroidHostRuntimeTests(unittest.TestCase):
    def test_private_paths_and_embedded_server_start_stop(self):
        with tempfile.TemporaryDirectory(prefix="windroida-android-host-") as temp:
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join(
                [str(PYTHON_DIR), str(REPO_ROOT), env.get("PYTHONPATH", "")]
            )
            result = subprocess.run(
                [sys.executable, "-c", CHILD_TEST, temp],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=90,
            )
            self.assertEqual(
                result.returncode, 0,
                "Android host subprocess failed.\nSTDOUT:\n"
                + result.stdout + "\nSTDERR:\n" + result.stderr,
            )


if __name__ == "__main__":
    unittest.main()
