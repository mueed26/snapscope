"""`snapscope cleanup`: disk space held by old revisions and unused base snaps.

Only reports and prints the commands to run; it never removes anything itself.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass

from snapscope.client import SnapdClient
from snapscope.commands import Command
from snapscope.models import Snap, human_size
from snapscope.render import Result, Table


@dataclass(frozen=True)
class Reclaimable:
    snap: str
    revision: str
    version: str
    size: int
    reason: str
    command: str


def find_reclaimable(all_revisions: list[Snap]) -> list[Reclaimable]:
    """Pure logic over every installed revision (active and disabled)."""
    items: list[Reclaimable] = []
    active = [s for s in all_revisions if s.active]

    # snapd keeps previous revisions for rollback; each one costs disk space
    for s in all_revisions:
        if not s.active:
            items.append(
                Reclaimable(
                    s.name,
                    s.revision,
                    s.version,
                    s.installed_size,
                    "disabled revision",
                    f"sudo snap remove {s.name} --revision={s.revision}",
                )
            )

    # a base nothing runs on can go (snapd itself does not need one)
    used_bases = {s.runtime for s in active if not s.is_base}
    for s in active:
        if s.is_base and s.name not in used_bases:
            items.append(
                Reclaimable(
                    s.name,
                    s.revision,
                    s.version,
                    s.installed_size,
                    "unused base",
                    f"sudo snap remove {s.name}",
                )
            )

    items.sort(key=lambda r: (-r.size, r.snap))
    return items


def build(all_revisions: list[Snap]) -> Result:
    items = find_reclaimable(all_revisions)
    total = sum(r.size for r in items)
    notes = [f"Reclaimable: {human_size(total)}"] if items else []
    if any(r.reason == "disabled revision" for r in items):
        notes.append("To keep fewer revisions in future: sudo snap set system refresh.retain=2")
    table = Table(
        title="Disk cleanup",
        columns=["Snap", "Rev", "Version", "Size", "Reason", "Command"],
        rows=[
            [r.snap, r.revision, r.version, human_size(r.size), r.reason, r.command] for r in items
        ],
        notes=notes,
        empty="Nothing to reclaim: no disabled revisions or unused bases.",
    )
    data = {"reclaimable": [asdict(r) for r in items], "reclaimable_bytes": total}
    return Result([table], data)


def run(client: SnapdClient, args: argparse.Namespace) -> Result:
    return build([Snap.from_api(d) for d in client.snaps(all_revisions=True)])


COMMAND = Command("cleanup", "show disk space used by old revisions and unused bases", run)
