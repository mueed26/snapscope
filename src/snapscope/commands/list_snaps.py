"""`snapscope list`: installed snaps with confinement, size and notes."""

from __future__ import annotations

import argparse
from dataclasses import asdict

from snapscope.client import SnapdClient
from snapscope.commands import Command
from snapscope.models import Snap, human_size, publisher_label
from snapscope.render import Result, Table


def notes_for(snap: Snap) -> str:
    notes = []
    if snap.devmode:
        notes.append("devmode")
    elif snap.confinement != "strict":
        notes.append(snap.confinement)
    if snap.type != "app":
        notes.append(snap.type)
    if snap.held:
        notes.append("held")
    return ",".join(notes) or "-"


def build(snaps: list[Snap]) -> Result:
    snaps = sorted(snaps, key=lambda s: s.name)
    total = sum(s.installed_size for s in snaps)
    rows = [
        [
            s.name,
            s.version,
            s.revision,
            s.channel,
            publisher_label(s),
            human_size(s.installed_size),
            notes_for(s),
        ]
        for s in snaps
    ]
    table = Table(
        title="Installed snaps",
        columns=["Name", "Version", "Rev", "Tracking", "Publisher", "Size", "Notes"],
        rows=rows,
        notes=[f"{len(snaps)} snaps using {human_size(total)}"],
        empty="No snaps installed.",
    )
    data = {"snaps": [asdict(s) for s in snaps], "total_size": total}
    return Result([table], data)


def run(client: SnapdClient, args: argparse.Namespace) -> Result:
    return build([Snap.from_api(d) for d in client.snaps()])


COMMAND = Command("list", "list installed snaps with confinement, size and notes", run)
