"""End-to-end tests for server-enforced host capacity on the real TCP protocol."""
import os
import tempfile
import time
import unittest
from pathlib import Path


class HostCapacityIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="windroida-capacity-")
        root = Path(cls.temp.name)
        import common

        common.DATA_DIR = root / "data"
        common.UPLOADS_DIR = common.DATA_DIR / "uploads"
        common.AVATARS_DIR = common.DATA_DIR / "avatars"
        common.WALLPAPERS_DIR = common.DATA_DIR / "wallpapers"
        common.ROOMAUDIO_DIR = common.DATA_DIR / "roomaudio"
        common.FILES_DIR = root / "files"
        for directory in (
            common.DATA_DIR,
            common.UPLOADS_DIR,
            common.AVATARS_DIR,
            common.WALLPAPERS_DIR,
            common.ROOMAUDIO_DIR,
            common.FILES_DIR,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        os.environ["WINDROIDA_ADMIN"] = "windroida"
        os.environ["WINDROIDA_ADMIN_PASSWORD"] = "Strong-Admin-Password-2026!"
        import server
        from client_core import Client

        cls.Client = Client
        cls.server = server.WindroidaServer(
            "127.0.0.1", 0, db_path=root / "windroida.db", web_port=None
        )
        cls.server.seed_admin()
        cls.port = cls.server.start()
        cls.clients = []

    @classmethod
    def tearDownClass(cls):
        for client in cls.clients:
            try:
                client.close()
            except Exception:
                pass
        cls.server.stop()
        deadline = time.time() + 10
        while time.time() < deadline:
            with cls.server.sessions_lock:
                sessions_empty = not any(cls.server.sessions.values())
            with cls.server.conns_lock:
                connections_empty = cls.server.conns_total == 0
            if sessions_empty and connections_empty:
                break
            time.sleep(0.05)
        cls.temp.cleanup()
        os.environ.pop("WINDROIDA_ADMIN_PASSWORD", None)
        os.environ.pop("WINDROIDA_ADMIN", None)

    def client(self):
        client = self.Client()
        client.connect("127.0.0.1", self.port)
        self.clients.append(client)
        return client

    @staticmethod
    def register(client, username):
        return client.call(
            "register",
            username=username,
            password="Strong-User-Password-2026!",
            display_name=username,
            sec_question="Integration test question?",
            sec_answer="answer",
            device="capacity-integration",
        )

    def wait_user_offline(self, uid):
        deadline = time.time() + 5
        while time.time() < deadline:
            with self.server.sessions_lock:
                active = any(c.alive for c in self.server.sessions.get(uid, []))
            if not active:
                return
            time.sleep(0.05)
        self.fail("user session did not become offline after client close")

    def test_member_and_online_limits_are_enforced_by_server(self):
        owner = self.client()
        login = owner.call(
            "login",
            username="windroida",
            password="Strong-Admin-Password-2026!",
            device="capacity-owner",
        )
        self.assertTrue(login.get("ok"), login)

        configured = owner.call(
            "host_limits", action="set", max_members=1, max_online=0
        )
        self.assertTrue(configured.get("ok"), configured)

        alice = self.client()
        alice_result = self.register(alice, "alice")
        self.assertTrue(alice_result.get("ok"), alice_result)
        alice_id = alice_result["me"]["id"]

        bob = self.client()
        blocked_by_member_limit = self.register(bob, "bobby")
        self.assertFalse(blocked_by_member_limit.get("ok"), blocked_by_member_limit)

        configured = owner.call(
            "host_limits", action="set", max_members=0, max_online=2
        )
        self.assertTrue(configured.get("ok"), configured)

        # A second device for an already-online account does not consume another user slot.
        alice_second_device = self.client()
        second_login = alice_second_device.call(
            "login",
            username="alice",
            password="Strong-User-Password-2026!",
            device="capacity-second-device",
        )
        self.assertTrue(second_login.get("ok"), second_login)

        # Owner + Alice already occupy both unique-user slots.
        blocked_by_online_limit = self.register(bob, "bobby")
        self.assertFalse(blocked_by_online_limit.get("ok"), blocked_by_online_limit)

        alice.close()
        alice_second_device.close()
        self.wait_user_offline(alice_id)

        # Once Alice is offline, Bob can register and occupy the second slot.
        bob_result = self.register(bob, "bobby")
        self.assertTrue(bob_result.get("ok"), bob_result)

        # A non-owner cannot inspect capacity or member/online counts.
        private_capacity = bob.call("host_limits")
        self.assertFalse(private_capacity.get("ok"), private_capacity)

        # Owner + Bob fill the limit; an offline existing account cannot log in.
        alice_third_device = self.client()
        denied_login = alice_third_device.call(
            "login",
            username="alice",
            password="Strong-User-Password-2026!",
            device="capacity-third-device",
        )
        self.assertFalse(denied_login.get("ok"), denied_login)

        status = owner.call("host_limits")
        self.assertTrue(status.get("ok"), status)
        self.assertEqual(status["capacity"], {"max_members": 0, "max_online": 2})
        self.assertEqual(status["members"], 2)
        self.assertEqual(status["online"], 2)
        self.assertTrue(status["is_owner"])


if __name__ == "__main__":
    unittest.main()
