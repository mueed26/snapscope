"""Pending snap updates and held snaps."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from typing import Any

from snapscope.client import SnapdClient, SnapdError
from snapscope.commands import Command
from snapscope.models import Snap
from snapscope.render import Result, Table


@dataclass(frozen=True)
class Update:
    snap: str
    installed_version: str
    installed_revision: str
    available_version: str
    available_revision: str
    channel: str


def pending_updates(installed: list[Snap], candidates: list[dict[str, Any]]) -> list[Update]:
    current = {s.name: s for s in installed if s.active}
    updates = []
    for c in candidates:
        name = str(c["name"])
        mine = current.get(name)
        updates.append(
            Update(
                snap=name,
                installed_version=mine.version if mine else "",
                installed_revision=mine.revision if mine else "",
                available_version=str(c.get("version", "")),
                available_revision=str(c.get("revision", "")),
                channel=str(c.get("channel", "")),
            )
        )
    return sorted(updates, key=lambda u: u.snap)


def build(
    installed: list[Snap], candidates: list[dict[str, Any]] | None, error: str = ""
) -> Result:
    held = sorted(s.name for s in installed if s.active and s.held)
    notes = []
    if held:
        notes.append("Held (not updated automatically): " + ", ".join(held))

    if candidates is None:
        table = Table(
            "Pending refreshes",
            [],
            [],
            notes,
            empty=f"Could not check the Snap Store: {error}",
        )
        return Result([table], {"error": error, "held": held})

    updates = pending_updates(installed, candidates)
    if updates:
        notes.insert(0, "Run: sudo snap refresh")
    table = Table(
        title="Pending refreshes",
        columns=["Snap", "Installed", "Available", "Channel"],
        rows=[
            [
                u.snap,
                f"{u.installed_version} ({u.installed_revision})",
                f"{u.available_version} ({u.available_revision})",
                u.channel,
            ]
            for u in updates
        ],
        notes=notes,
        empty="All snaps are up to date.",
    )
    data = {"updates": [asdict(u) for u in updates], "held": held}
    return Result([table], data, 1 if updates else 0)


def run(client: SnapdClient, args: argparse.Namespace) -> Result:
    installed = [Snap.from_api(d) for d in client.snaps()]
    try:
        candidates = client.refresh_candidates()
    except SnapdError as exc:  # offline etc: report, don't crash
        return build(installed, None, str(exc))
    return build(installed, candidates)


COMMAND = Command("refresh", "show pending updates from the Snap Store and held snaps", run)
