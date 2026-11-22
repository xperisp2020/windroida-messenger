"""Cross-platform host capacity policy shared by Windows and Android-compatible server runtimes.

A zero limit means unlimited. Enforcement is performed by the server, never by the UI.
"""
import sqlite3


class CapacityReached(Exception):
    """A configured host capacity has been reached."""


class InvalidCapacity(ValueError):
    """A capacity setting is outside the supported range."""


def ensure_schema(db):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS host_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            max_members INTEGER NOT NULL DEFAULT 0 CHECK (max_members >= 0),
            max_online INTEGER NOT NULL DEFAULT 0 CHECK (max_online >= 0),
            updated_at INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    db.execute(
        "INSERT OR IGNORE INTO host_settings(id, max_members, max_online, updated_at) VALUES (1, 0, 0, 0)"
    )


def get_limits(db):
    row = db.execute("SELECT max_members, max_online FROM host_settings WHERE id=1").fetchone()
    return {"max_members": int(row["max_members"]), "max_online": int(row["max_online"])}


def _capacity(value, name, maximum):
    if isinstance(value, bool):
        raise InvalidCapacity(name)
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        raise InvalidCapacity(name)
    if str(value).strip() != str(parsed) or not 0 <= parsed <= maximum:
        raise InvalidCapacity(name)
    return parsed


def set_limits(db, max_members, max_online, updated_at):
    members = _capacity(max_members, "max_members", 100000)
    online = _capacity(max_online, "max_online", 5000)
    ensure_schema(db)
    with db:
        db.execute(
            "UPDATE host_settings SET max_members=?, max_online=?, updated_at=? WHERE id=1",
            (members, online, int(updated_at)),
        )
    return {"max_members": members, "max_online": online}


def check_registration_capacity(db, admin_user):
    limits = get_limits(db)
    if limits["max_members"]:
        count = db.execute(
            "SELECT COUNT(*) FROM users WHERE username COLLATE NOCASE <> ?",
            (admin_user,),
        ).fetchone()[0]
        if count >= limits["max_members"]:
            raise CapacityReached("ظرفیت ثبت‌نام این سرور تکمیل شده است")


def online_user_count(sessions):
    return sum(
        1 for connections in sessions.values()
        if any(getattr(connection, "alive", False) for connection in connections)
    )


def check_online_capacity(sessions, uid, max_online):
    if not max_online:
        return
    existing = sessions.get(uid, ())
    if any(getattr(connection, "alive", False) for connection in existing):
        return
    if online_user_count(sessions) >= max_online:
        raise CapacityReached("ظرفیت اتصال هم‌زمان این سرور تکمیل شده است")
