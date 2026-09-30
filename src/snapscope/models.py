"""Typed views of the snapd API objects snapscope uses.

Parsing lives here, separate from I/O, so tests can feed in captured JSON.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# Snap types that provide a runtime rather than an application.
BASE_TYPES = frozenset({"base", "os"})


@dataclass(frozen=True)
class Snap:
    name: str
    version: str
    revision: str
    channel: str
    publisher: str
    validation: str  # "verified", "starred" or "unproven"
    confinement: str  # "strict", "classic" or "devmode"
    devmode: bool
    type: str  # "app", "base", "os", "snapd", "gadget", "kernel"
    status: str  # "active" for the current revision, otherwise disabled
    installed_size: int
    base: str
    held: bool

    @classmethod
    def from_api(cls, d: Mapping[str, Any]) -> Snap:
        publisher = d.get("publisher") or {}
        return cls(
            name=str(d["name"]),
            version=str(d.get("version", "")),
            revision=str(d.get("revision", "")),
            channel=str(d.get("tracking-channel") or d.get("channel") or ""),
            publisher=str(publisher.get("username") or d.get("developer") or ""),
            validation=str(publisher.get("validation", "unproven")),
            confinement=str(d.get("confinement", "strict")),
            devmode=bool(d.get("devmode", False)),
            type=str(d.get("type", "app")),
            status=str(d.get("status", "active")),
            installed_size=int(d.get("installed-size") or 0),
            base=str(d.get("base") or ""),
            held=bool(d.get("hold")),
        )

    @property
    def active(self) -> bool:
        return self.status == "active"

    @property
    def is_base(self) -> bool:
        return self.type in BASE_TYPES

    @property
    def runtime(self) -> str:
        """The base this snap runs on; app snaps without one use "core"."""
        if self.base:
            return self.base
        return "core" if self.type == "app" else ""


@dataclass(frozen=True)
class Connection:
    interface: str
    plug_snap: str
    plug: str
    slot_snap: str
    slot: str
    manual: bool  # connected by a user rather than automatically

    @classmethod
    def from_api(cls, d: Mapping[str, Any]) -> Connection:
        return cls(
            interface=str(d["interface"]),
            plug_snap=str(d["plug"]["snap"]),
            plug=str(d["plug"]["plug"]),
            slot_snap=str(d["slot"]["snap"]),
            slot=str(d["slot"]["slot"]),
            manual=bool(d.get("manual", False)),
        )


def human_size(n: int) -> str:
    """Format a byte count the way `snap` and `df -h` do, e.g. 10.4MB."""
    size = float(n)
    for unit in ("B", "kB", "MB", "GB"):
        if size < 1000 or unit == "GB":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1000
    raise AssertionError("unreachable")


def publisher_label(snap: Snap) -> str:
    """Publisher name with the Snap Store's marks: ✓ verified, ✪ starred."""
    mark = {"verified": "✓", "starred": "✪"}.get(snap.validation, "")
    return f"{snap.publisher}{mark}"
