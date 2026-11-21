"""Embedded Windroida messenger host for Android's foreground service."""
import contextlib
import io
import json
import os
from pathlib import Path

_server = None
_runtime_root = None


def _configure_paths(files_dir):
    global _runtime_root
    root = Path(files_dir).resolve() / "windroida"
    data = root / "data"
    for directory in (
        root, data, data / "files", data / "uploads", data / "roomaudio",
        data / "wallpapers", data / "avatars",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    import common

    # common.py is imported from the read-only APK. All mutable server data and
    # web assets must live in the app's private, writable files directory.
    common.BASE_DIR = root
    common.DATA_DIR = data
    common.DB_PATH = data / "windroida.db"
    common.FILES_DIR = data / "files"
    common.UPLOADS_DIR = data / "uploads"
    common.ROOMAUDIO_DIR = data / "roomaudio"
    common.WALLPAPERS_DIR = data / "wallpapers"
    common.AVATARS_DIR = data / "avatars"
    _runtime_root = root
    return root


def start_host(files_dir, lan_addresses=""):
    """Start the same TCP and HTTPS/WebSocket server used by the Windows launcher."""
    global _server
    if _server is not None:
        return json.dumps({
            "running": True,
            "tcp_port": _server.port,
            "web_port": _server.web_port,
            "tls": bool(_server.ssl_ctx),
        })

    root = _configure_paths(files_dir)
    if not (root / "web" / "index.html").is_file():
        raise RuntimeError("Windroida web client assets were not installed")

    addresses = [x.strip() for x in str(lan_addresses).split(",") if x.strip()]
    if addresses:
        os.environ["WINDROIDA_CERT_NAMES"] = ",".join(addresses)

    from server import WindroidaServer

    instance = WindroidaServer(
        host="0.0.0.0",
        port=8765,
        tls=True,
        db_path=root / "data" / "windroida.db",
        web_port=8081,
    )
    try:
        # Suppress the desktop launcher's console output: it includes the initial
        # admin password. The password remains in the app-private 0600 file.
        with contextlib.redirect_stdout(io.StringIO()):
            instance.seed_admin()
        instance.start()
        if not instance.ssl_ctx or not instance.web:
            raise RuntimeError("Secure HTTPS could not be initialized; hosting stopped")
        _server = instance
        return json.dumps({
            "running": True,
            "tcp_port": instance.port,
            "web_port": instance.web_port,
            "tls": True,
        })
    except Exception:
        try:
            instance.stop()
        except Exception:
            pass
        raise


def stop_host():
    global _server
    instance, _server = _server, None
    if instance is None:
        return True
    instance.stop()
    return True


def host_status():
    instance = _server
    if instance is None:
        return json.dumps({"running": False})
    return json.dumps({
        "running": True,
        "tcp_port": instance.port,
        "web_port": instance.web_port,
        "tls": bool(instance.ssl_ctx),
    })
