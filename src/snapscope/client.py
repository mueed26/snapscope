"""Minimal client for the snapd REST API, spoken over its Unix socket.

snapd serves HTTP on /run/snapd.socket; this is the same API the `snap`
command uses. Read-only endpoints need no root access.
"""

from __future__ import annotations

import http.client
import json
import socket
from typing import Any
from urllib.parse import urlencode

DEFAULT_SOCKET = "/run/snapd.socket"


class SnapdError(Exception):
    """snapd answered with an error response."""

    def __init__(self, message: str, kind: str = "", status: int = 0) -> None:
        super().__init__(message)
        self.kind = kind
        self.status = status


class SnapdUnavailable(SnapdError):
    """The snapd socket could not be reached at all."""


class _UnixHTTPConnection(http.client.HTTPConnection):
    """HTTPConnection that connects to a Unix socket instead of TCP."""

    def __init__(self, socket_path: str, timeout: float) -> None:
        super().__init__("localhost", timeout=timeout)
        self._socket_path = socket_path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect(self._socket_path)
        except OSError:
            sock.close()
            raise
        self.sock = sock


def parse_response(body: bytes, http_status: int) -> Any:
    """Unwrap a snapd JSON envelope, returning its "result" or raising SnapdError."""
    try:
        doc = json.loads(body)
    except ValueError as exc:
        raise SnapdError(f"invalid JSON from snapd (HTTP {http_status})") from exc
    if not isinstance(doc, dict):
        raise SnapdError("unexpected response from snapd")
    if doc.get("type") == "error":
        result = doc.get("result") or {}
        raise SnapdError(
            str(result.get("message", "unknown error")),
            kind=str(result.get("kind", "")),
            status=int(doc.get("status-code", http_status)),
        )
    return doc.get("result")


class SnapdClient:
    def __init__(self, socket_path: str = DEFAULT_SOCKET, timeout: float = 30.0) -> None:
        self.socket_path = socket_path
        self.timeout = timeout

    def get(self, path: str, **params: str) -> Any:
        """GET an API path such as "/v2/snaps" and return the unwrapped result."""
        url = f"{path}?{urlencode(params)}" if params else path
        conn = _UnixHTTPConnection(self.socket_path, self.timeout)
        try:
            conn.request("GET", url, headers={"Accept": "application/json"})
            resp = conn.getresponse()
            body = resp.read()
        except FileNotFoundError as exc:
            raise SnapdUnavailable(
                f"snapd socket not found at {self.socket_path} (is snapd installed and running?)"
            ) from exc
        except PermissionError as exc:
            raise SnapdUnavailable(f"permission denied opening {self.socket_path}") from exc
        except OSError as exc:
            raise SnapdUnavailable(f"cannot talk to snapd at {self.socket_path}: {exc}") from exc
        finally:
            conn.close()
        return parse_response(body, resp.status)

    def snaps(self, all_revisions: bool = False) -> list[dict[str, Any]]:
        """Installed snaps; with all_revisions, disabled revisions are included too."""
        result = self.get("/v2/snaps", select="all") if all_revisions else self.get("/v2/snaps")
        return list(result or [])

    def connections(self) -> list[dict[str, Any]]:
        """Established interface connections."""
        result = self.get("/v2/connections") or {}
        return list(result.get("established") or [])

    def refresh_candidates(self) -> list[dict[str, Any]]:
        """Snaps with a newer revision in the store (this call contacts the Snap Store)."""
        try:
            result = self.get("/v2/find", select="refresh")
        except SnapdError as exc:
            if exc.kind == "snap-not-found":  # snapd's way of saying "nothing to refresh"
                return []
            raise
        return list(result or [])
