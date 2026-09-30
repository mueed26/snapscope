"""`snapscope report` (the default): audit, cleanup and refresh in one run."""

from __future__ import annotations

import argparse

from snapscope.client import SnapdClient
from snapscope.commands import Command, audit, cleanup, refresh
from snapscope.render import Result


def run(client: SnapdClient, args: argparse.Namespace) -> Result:
    parts = {
        "audit": audit.run(client, args),
        "cleanup": cleanup.run(client, args),
        "refresh": refresh.run(client, args),
    }
    return Result(
        tables=[t for part in parts.values() for t in part.tables],
        data={name: part.data for name, part in parts.items()},
        exit_code=max(part.exit_code for part in parts.values()),
    )


COMMAND = Command(
    "report", "run audit, cleanup and refresh together (default)", run, audit.add_arguments
)
