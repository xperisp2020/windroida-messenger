"""Regression tests for private-key and signing-secret file permissions."""
import os
import stat
import tempfile
import unittest
from unittest import mock
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

    def test_windroida_secret_loader_restricts_before_returning_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            instance = object.__new__(server.WindroidaServer)
            instance.db_path = str(Path(tmp) / "windroida.db")
            path = Path(tmp) / "secret.key"
            expected = b"w" * 32
            path.write_bytes(expected)
            path.chmod(0o644)
            self.assertEqual(instance._load_secret(), expected)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_windroida_drive_secret_loader_restricts_existing_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            instance = object.__new__(server.WindroidaServer)
            instance.db_path = str(Path(tmp) / "windroida.db")
            path = Path(tmp) / "drive_sso.key"
            expected = "d" * 64
            path.write_text(expected, encoding="utf-8")
            path.chmod(0o644)
            self.assertEqual(instance._load_drive_secret(), expected)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_atomic_key_copy_is_private_before_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "source.key"
            dst = Path(tmp) / "backup.key"
            src.write_bytes(b"k" * 64)
            server._atomic_copy(src, dst)
            self.assertEqual(dst.read_bytes(), b"k" * 64)
            self.assertEqual(stat.S_IMODE(dst.stat().st_mode), 0o600)

    def test_permission_errors_are_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "secret.key"
            path.write_bytes(b"x" * 32)
            with mock.patch("server.os.chmod", side_effect=PermissionError("denied")):
                with self.assertRaises(PermissionError):
                    server._restrict_private_file(path)

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
