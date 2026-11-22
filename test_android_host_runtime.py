"""Isolated integration checks for Android host path wiring and server lifecycle."""
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
PYTHON_DIR = REPO_ROOT / "android" / "app" / "src" / "main" / "python"

CHILD_TEST = r"""
import json
import os
import socket
import ssl
import sys
from pathlib import Path

root_dir = Path(sys.argv[1])
import android_host

assert android_host._select_bind_address(["192.168.1.8", "10.0.0.2"]) == "192.168.1.8"
assert android_host._select_bind_address(["8.8.8.8"]) == "127.0.0.1"
assert android_host._select_bind_address([]) == "127.0.0.1"

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

os.environ["WINDROIDA_CERT_NAMES"] = "stale.example.invalid"
result = json.loads(android_host.start_host(
    str(root_dir), "", tcp_port, web_port
))
assert "WINDROIDA_CERT_NAMES" not in os.environ
assert result["running"] and result["tls"]
assert result["tcp_port"] == tcp_port
assert result["web_port"] == web_port
assert android_host._server.host == "127.0.0.1"
assert (root / "data" / "admin_password.txt").is_file()
assert json.loads(android_host.host_status())["running"]

tls_context = ssl._create_unverified_context()
tls_idle = tls_context.wrap_socket(
    socket.create_connection(("127.0.0.1", tcp_port), timeout=5),
    server_hostname="127.0.0.1",
)
tls_idle.settimeout(5)
android_host.stop_host()
assert not json.loads(android_host.host_status())["running"]
try:
    assert tls_idle.recv(1) == b""
except (ConnectionError, OSError):
    pass
finally:
    tls_idle.close()
for port in (tcp_port, web_port):
    try:
        socket.create_connection(("127.0.0.1", port), timeout=1).close()
    except OSError:
        pass
    else:
        raise AssertionError(f"listener on port {port} remained open after stop")
"""

class AndroidHostRuntimeTests(unittest.TestCase):
    def test_host_secrets_are_excluded_from_cloud_backup_and_device_transfer(self):
        rules = ET.parse(
            REPO_ROOT / "android" / "app" / "src" / "main" / "res" / "xml" / "data_extraction_rules.xml"
        ).getroot()
        for section_name in ("cloud-backup", "device-transfer"):
            section = rules.find(section_name)
            self.assertIsNotNone(section, f"missing {section_name} rules")
            excluded = {(item.get("domain"), item.get("path")) for item in section.findall("exclude")}
            self.assertIn(("sharedpref", "wd.xml"), excluded)
            self.assertIn(("sharedpref", "wd_host.xml"), excluded)
            self.assertIn(("sharedpref", "wd_host_return.xml"), excluded)
            self.assertIn(("file", "windroida/"), excluded)

        legacy = ET.parse(
            REPO_ROOT / "android" / "app" / "src" / "main" / "res" / "xml" / "backup_rules.xml"
        ).getroot()
        legacy_excluded = {(item.get("domain"), item.get("path")) for item in legacy.findall("exclude")}
        self.assertIn(("sharedpref", "wd_host.xml"), legacy_excluded)
        self.assertIn(("sharedpref", "wd_host_return.xml"), legacy_excluded)
        self.assertIn(("file", "windroida/"), legacy_excluded)

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
