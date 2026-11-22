import sqlite3
import unittest

import host_capacity


class FakeConnection:
    def __init__(self, alive=True):
        self.alive = alive


class HostCapacityTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL)")
        self.db.executemany("INSERT INTO users(username) VALUES (?)", [("windroida",), ("alice",), ("bob",)])
        host_capacity.ensure_schema(self.db)

    def tearDown(self):
        self.db.close()

    def test_default_limits_are_unlimited_for_existing_installations(self):
        self.assertEqual(host_capacity.get_limits(self.db), {"max_members": 0, "max_online": 0})

    def test_member_limit_counts_non_admin_accounts(self):
        host_capacity.set_limits(self.db, 2, 0, 100)
        with self.assertRaises(host_capacity.CapacityReached):
            host_capacity.check_registration_capacity(self.db, "windroida")

    def test_member_limit_allows_registration_below_limit(self):
        host_capacity.set_limits(self.db, 3, 0, 100)
        host_capacity.check_registration_capacity(self.db, "windroida")

    def test_capacity_values_are_bounded_and_booleans_rejected(self):
        for values in ((-1, 1), (100001, 1), (1, 5001), (True, 1), ("1.5", 1)):
            with self.subTest(values=values), self.assertRaises(host_capacity.InvalidCapacity):
                host_capacity.set_limits(self.db, values[0], values[1], 100)

    def test_online_limit_counts_unique_users_not_devices(self):
        sessions = {1: [FakeConnection(), FakeConnection()], 2: [FakeConnection()]}
        host_capacity.check_online_capacity(sessions, 1, 2)
        with self.assertRaises(host_capacity.CapacityReached):
            host_capacity.check_online_capacity(sessions, 3, 2)

    def test_existing_user_can_open_another_device_at_capacity(self):
        sessions = {1: [FakeConnection()], 2: [FakeConnection()]}
        host_capacity.check_online_capacity(sessions, 1, 2)

    def test_dead_sessions_do_not_consume_online_capacity(self):
        sessions = {1: [FakeConnection(False)], 2: [FakeConnection()]}
        host_capacity.check_online_capacity(sessions, 3, 2)

    def test_zero_online_limit_is_unlimited(self):
        sessions = {1: [FakeConnection()], 2: [FakeConnection()]}
        host_capacity.check_online_capacity(sessions, 3, 0)


if __name__ == "__main__":
    unittest.main()
