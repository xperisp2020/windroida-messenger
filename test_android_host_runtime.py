"""Desktop-side checks for Android host path wiring before APK packaging."""
import sys
import tempfile
import unittest
from pathlib import Path

PYTHON_DIR = Path(__file__).parent / "android" / "app" / "src" / "main" / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


class AndroidHostRuntimeTests(unittest.TestCase):
    def test_server_and_web_gateway_use_app_private_runtime_paths(self):
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


if __name__ == "__main__":
    unittest.main()
