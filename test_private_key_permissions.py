"""Regression tests for private-key and signing-secret file permissions."""
import os
import stat
import tempfile
import unittest
from pathlib import Path

import server
from ghab.server import config, tls


@unittest.skipIf(os.name == "nt", "POSIX permission bits are not enforced the same way on Windows")
class PrivateFilePermissionTests(unittest.TestCase):
    def test_windroida_secret_is_created_owner_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "secret.key"
            server._write_private_bytes(path, b"x" * 32)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_existing_windroida_secret_permissions_are_restricted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "secret.key"
            path.write_bytes(b"x" * 32)
            path.chmod(0o644)
            server._restrict_private_file(path)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_ghab_session_secret_permissions_are_restricted(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = config.DATA_DIR
            try:
                config.DATA_DIR = tmp
                path = Path(tmp) / "secret.key"
                path.write_text("s" * 64, encoding="utf-8")
                path.chmod(0o644)
                self.assertEqual(config.secret_key(), "s" * 64)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            finally:
                config.DATA_DIR = original

    def test_ghab_tls_key_writer_creates_owner_only_file(self):
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
        except ImportError:
            self.skipTest("cryptography is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "server-key.pem"
            tls._write_key(str(path), ec.generate_private_key(ec.SECP256R1()))
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
