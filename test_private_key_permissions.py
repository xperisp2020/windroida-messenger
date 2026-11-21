"""Regression tests for private-key and signing-secret file permissions."""
import builtins
import os
import stat
import shutil
import subprocess
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

    def test_ghab_session_secret_is_atomically_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = config.DATA_DIR
            real_replace = os.replace
            try:
                config.DATA_DIR = tmp
                path = Path(tmp) / "secret.key"

                def checked_replace(source, destination):
                    self.assertEqual(Path(destination), path)
                    self.assertEqual(stat.S_IMODE(Path(source).stat().st_mode), 0o600)
                    self.assertEqual(len(Path(source).read_text(encoding="utf-8")), 64)
                    real_replace(source, destination)

                with mock.patch("ghab.server.config.os.replace", side_effect=checked_replace) as replace:
                    value = config.secret_key()
                self.assertEqual(len(value), 64)
                replace.assert_called_once()
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

    def test_openssl_fallback_key_is_private_before_post_creation_restriction(self):
        if not shutil.which("openssl"):
            self.skipTest("openssl is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            crt, key = Path(tmp) / "server.crt", Path(tmp) / "server.key"
            real_run = subprocess.run

            def inspect_created_key(*args, **kwargs):
                result = real_run(*args, **kwargs)
                self.assertEqual(stat.S_IMODE(key.stat().st_mode), 0o600)
                return result

            with mock.patch("server.subprocess.run", side_effect=inspect_created_key):
                self.assertTrue(server.WindroidaServer._cert_openssl(crt, key, ["localhost"]))
            self.assertEqual(stat.S_IMODE(key.stat().st_mode), 0o600)

    def test_ghab_openssl_fallback_key_is_private_at_creation(self):
        if not shutil.which("openssl"):
            self.skipTest("openssl is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            cert_dir = Path(tmp)
            custom_dir = cert_dir / "custom"
            real_import = builtins.__import__
            real_run = subprocess.run
            key = cert_dir / "key.pem"

            def without_cryptography(name, *args, **kwargs):
                if name == "cryptography" or name.startswith("cryptography."):
                    raise ImportError("forced OpenSSL fallback test")
                return real_import(name, *args, **kwargs)

            def inspect_created_key(*args, **kwargs):
                result = real_run(*args, **kwargs)
                if args and args[0] and args[0][0] == "openssl":
                    self.assertEqual(stat.S_IMODE(key.stat().st_mode), 0o600)
                return result

            with mock.patch.object(tls, "CERT_DIR", str(cert_dir)), \
                 mock.patch.object(tls, "CUSTOM_DIR", str(custom_dir)), \
                 mock.patch.dict(os.environ, {"GHAB_CERT": "", "GHAB_KEY": ""}), \
                 mock.patch("builtins.__import__", side_effect=without_cryptography), \
                 mock.patch("ghab.server.tls.subprocess.run", side_effect=inspect_created_key):
                result = tls.ensure_cert("localhost")
            self.assertIsNotNone(result)
            self.assertEqual(stat.S_IMODE(key.stat().st_mode), 0o600)

    def test_ghab_custom_tls_rejects_symlinked_private_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cert = root / "fullchain.pem"
            cert.write_text("certificate", encoding="utf-8")
            target = root / "unrelated-private-key.pem"
            target.write_text("private key", encoding="utf-8")
            link = root / "privkey.pem"
            link.symlink_to(target)

            with mock.patch.dict(os.environ, {"GHAB_CERT": str(cert), "GHAB_KEY": str(link)}):
                with self.assertRaises(PermissionError):
                    tls.custom_cert()

            custom = root / "custom"
            custom.mkdir()
            (custom / "fullchain.pem").write_text("certificate", encoding="utf-8")
            (custom / "privkey.pem").symlink_to(target)
            with mock.patch.dict(os.environ, {"GHAB_CERT": "", "GHAB_KEY": ""}):
                with mock.patch.object(tls, "CUSTOM_DIR", str(custom)):
                    with self.assertRaises(PermissionError):
                        tls.custom_cert()

@unittest.skipUnless(os.name == "nt", "Windows ACL checks run only on Windows")
class WindowsPrivateAclTests(unittest.TestCase):
    def assert_owner_only_acl(self, path):
        account = subprocess.run(["whoami"], check=True, capture_output=True, text=True).stdout.strip().lower()
        acl = subprocess.run(["icacls", str(path)], check=True, capture_output=True, text=True).stdout.lower()
        self.assertIn(account, acl)
        self.assertIn("(f)", acl)
        for broad_principal in ("everyone", "authenticated users", "builtin\\users"):
            self.assertNotIn(broad_principal, acl)

    def test_windroida_secret_creation_sets_owner_acl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "secret.key"
            server._write_private_bytes(path, b"w" * 32)
            self.assert_owner_only_acl(path)

    def test_existing_windroida_secret_acl_is_restricted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "secret.key"
            path.write_bytes(b"x" * 32)
            subprocess.run(["icacls", str(path), "/grant", "*S-1-1-0:(F)"], check=True, capture_output=True, text=True)
            server._restrict_private_file(path)
            self.assert_owner_only_acl(path)

    def test_ghab_session_secret_creation_sets_owner_acl(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = config.DATA_DIR
            try:
                config.DATA_DIR = tmp
                config.secret_key()
                self.assert_owner_only_acl(Path(tmp) / "secret.key")
            finally:
                config.DATA_DIR = original

    def test_ghab_tls_key_creation_sets_owner_acl(self):
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
        except ImportError:
            self.skipTest("cryptography is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "server-key.pem"
            tls._write_key(str(path), ec.generate_private_key(ec.SECP256R1()))
            self.assert_owner_only_acl(path)


if __name__ == "__main__":
    unittest.main()
