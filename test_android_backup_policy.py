"""Ensure Android private messaging data cannot be copied by OS backup/transfer."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ANDROID = ROOT / "android" / "app" / "src" / "main"
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


class AndroidBackupPolicyTests(unittest.TestCase):
    def test_backup_is_disabled_at_application_level(self):
        root = ET.parse(ANDROID / "AndroidManifest.xml").getroot()
        app = root.find("application")
        self.assertIsNotNone(app)
        self.assertEqual(app.get(ANDROID_NS + "allowBackup"), "false")

    def test_legacy_full_backup_excludes_private_state(self):
        root = ET.parse(ANDROID / "res/xml/backup_rules.xml").getroot()
        excluded = {(node.get("domain"), node.get("path")) for node in root.findall("exclude")}
        for domain in ("database", "file", "sharedpref"):
            self.assertIn((domain, "."), excluded)
        self.assertIn(("root", "app_webview/"), excluded)

    def test_cloud_and_device_transfer_exclude_private_state(self):
        root = ET.parse(ANDROID / "res/xml/data_extraction_rules.xml").getroot()
        for section_name in ("cloud-backup", "device-transfer"):
            section = root.find(section_name)
            self.assertIsNotNone(section)
            excluded = {(node.get("domain"), node.get("path")) for node in section.findall("exclude")}
            for domain in ("database", "file", "sharedpref"):
                self.assertIn((domain, "."), excluded)
            self.assertIn(("root", "app_webview/"), excluded)


if __name__ == "__main__":
    unittest.main()
