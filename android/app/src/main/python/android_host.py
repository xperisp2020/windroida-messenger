"""Embedded Windroida messenger host for Android's foreground service."""
import contextlib
import io
import ipaddress
import json
import os
import threading
from pathlib import Path

_server = None
_runtime_root = None
_lock = threading.RLock()


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

    # All mutable server data and web assets live in app-private writable storage.
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


def _is_private_ipv4(value):
    try:
        address = ipaddress.ip_address(str(value).strip())
    except ValueError:
        return False
    return isinstance(address, ipaddress.IPv4Address) and not address.is_link_local and (
        address.is_private or address.is_loopback
    )


def _select_bind_address(addresses):
    """Bind only to a validated private LAN IPv4 address; fall back to loopback."""
    for raw in addresses:
        try:
            address = ipaddress.ip_address(str(raw).strip())
        except ValueError:
            continue
        if isinstance(address, ipaddress.IPv4Address) and not address.is_link_local and (
            address.is_private or address.is_loopback
        ):
            return str(address)
    return "127.0.0.1"


def start_host(files_dir, lan_addresses="", tcp_port=8765, web_port=8081):
    """Start the same TCP and HTTPS/WebSocket server used by the Windows launcher."""
    global _server
    with _lock:
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
        bind_address = _select_bind_address(addresses)
        certificate_names = [
            str(ipaddress.ip_address(value))
            for value in addresses
            if _is_private_ipv4(value)
        ]
        if certificate_names:
            os.environ["WINDROIDA_CERT_NAMES"] = ",".join(certificate_names)

        from server import WindroidaServer

        # Do not listen on every interface: Android's public/cellular interfaces must not
        # become reachable just because the phone is hosting for its local Wi-Fi network.
        instance = WindroidaServer(
            host=bind_address,
            port=int(tcp_port),
            tls=True,
            db_path=root / "data" / "windroida.db",
            web_port=int(web_port),
        )
        try:
            # seed_admin prints the generated password on desktop. Capture it here;
            # the only persisted copy remains the private admin_password.txt file.
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
    with _lock:
        instance, _server = _server, None
        if instance is None:
            return True
        instance.stop()
        return True


def host_status():
    with _lock:
        instance = _server
        if instance is None:
            return json.dumps({"running": False})
        return json.dumps({
            "running": True,
            "tcp_port": instance.port,
            "web_port": instance.web_port,
            "tls": bool(instance.ssl_ctx),
        })
