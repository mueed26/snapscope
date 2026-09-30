"""Sub-commands. Each module exposes a COMMAND.

all_commands() sets their order in --help; the first one runs when no
sub-command is given.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass

from snapscope.client import SnapdClient
from snapscope.render import Result


@dataclass(frozen=True)
class Command:
    name: str
    help: str
    run: Callable[[SnapdClient, argparse.Namespace], Result]
    add_arguments: Callable[[argparse.ArgumentParser], None] | None = None


def all_commands() -> list[Command]:
    # imported here so each command module can import Command from this package
    from snapscope.commands import audit, cleanup, list_snaps

    return [list_snaps.COMMAND, audit.COMMAND, cleanup.COMMAND]
