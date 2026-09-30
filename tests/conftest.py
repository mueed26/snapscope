"""Shared fixtures: captured snapd responses and a fake snapd on a Unix socket."""

from __future__ import annotations

import http.server
import json
import shutil
import socketserver
import tempfile
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> Any:
    """A real snapd response captured on Ubuntu 24.04 (see tests/fixtures)."""
    return json.loads((FIXTURES / name).read_text())


def ok(result: Any) -> dict[str, Any]:
    return {"type": "sync", "status-code": 200, "status": "OK", "result": result}


def error(status: int, kind: str, message: str) -> dict[str, Any]:
    return {"type": "error", "status-code": status, "result": {"kind": kind, "message": message}}


def make_snap(name: str, **fields: Any) -> dict[str, Any]:
    """A snap as /v2/snaps returns it; override any field with keyword arguments."""
    snap: dict[str, Any] = {
        "name": name,
        "version": "1.0",
        "revision": "10",
        "tracking-channel": "latest/stable",
        "publisher": {"username": "someone", "validation": "verified"},
        "confinement": "strict",
        "devmode": False,
        "type": "app",
        "status": "active",
        "installed-size": 1_000_000,
        "base": "core24",
    }
    snap.update({k.replace("_", "-"): v for k, v in fields.items()})
    return snap


def make_connection(snap: str, interface: str, manual: bool = False) -> dict[str, Any]:
    return {
        "interface": interface,
        "plug": {"snap": snap, "plug": interface},
        "slot": {"snap": "snapd", "slot": interface},
        **({"manual": True} if manual else {}),
    }


class FakeSnapd:
    """Serves canned JSON by request path (including the query string)."""

    def __init__(self, socket_path: str) -> None:
        self.socket_path = socket_path
        self.routes: dict[str, tuple[int, Any]] = {}
        self.requests: list[str] = []

    def route(self, path: str, doc: Any, status: int = 200) -> None:
        self.routes[path] = (status, doc)


class _Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    fake: FakeSnapd


class _Handler(http.server.BaseHTTPRequestHandler):
    server: _Server

    def do_GET(self) -> None:
        fake = self.server.fake
        fake.requests.append(self.path)
        status, doc = fake.routes.get(self.path, (404, error(404, "not-found", "no route")))
        body = json.dumps(doc).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        pass  # quiet (client_address is '' on unix sockets anyway)


@pytest.fixture
def fake_snapd() -> Iterator[FakeSnapd]:
    # short path: unix socket paths max out around 108 chars
    tmp = tempfile.mkdtemp(prefix="snapd")
    fake = FakeSnapd(f"{tmp}/snapd.socket")
    server = _Server(fake.socket_path, _Handler)
    server.fake = fake
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield fake
    finally:
        server.shutdown()
        server.server_close()
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def real_system(fake_snapd: FakeSnapd) -> FakeSnapd:
    """Fake snapd replaying the responses captured from a real machine."""
    fake_snapd.route("/v2/snaps", load("snaps.json"))
    fake_snapd.route("/v2/snaps?select=all", load("snaps.json"))
    fake_snapd.route("/v2/connections", load("connections.json"))
    fake_snapd.route("/v2/find?select=refresh", load("refresh.json"))
    return fake_snapd
