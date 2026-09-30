"""Command-line entry point."""

from __future__ import annotations

import argparse
import os
import sys

from snapscope import __version__
from snapscope.client import DEFAULT_SOCKET, SnapdClient, SnapdError
from snapscope.commands import Command, all_commands
from snapscope.render import FORMATS, render

EXIT_ERROR = 3

# Defaults for the shared options, applied after parsing (see build_parser).
SHARED_DEFAULTS = {"format": "table", "no_color": False, "socket": DEFAULT_SOCKET}


def build_parser(commands: list[Command]) -> argparse.ArgumentParser:
    # Shared options work both before and after the sub-command
    # (`snapscope --json audit` and `snapscope audit --json`). The top-level
    # parser and each sub-parser share these option objects, so their defaults
    # must stay SUPPRESS: a real default would let the sub-parser overwrite a
    # value given before the sub-command. parse_args() fills them in instead.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-f", "--format", choices=FORMATS, default=argparse.SUPPRESS, help="output format"
    )
    common.add_argument(
        "--json",
        dest="format",
        action="store_const",
        const="json",
        default=argparse.SUPPRESS,
        help="shortcut for --format json",
    )
    common.add_argument(
        "--no-color", action="store_true", default=argparse.SUPPRESS, help="disable colours"
    )
    common.add_argument(
        "--socket", default=argparse.SUPPRESS, help=f"snapd socket (default: {DEFAULT_SOCKET})"
    )

    parser = argparse.ArgumentParser(
        prog="snapscope",
        description="Audit the snaps on this machine: security, disk usage and pending refreshes.",
        parents=[common],
        epilog="Exit status: 0 all clear, 1 warnings or updates, 2 high severity, 3 error.",
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    for cmd in commands:
        p = sub.add_parser(cmd.name, help=cmd.help, description=cmd.help, parents=[common])
        if cmd.add_arguments:
            cmd.add_arguments(p)
    return parser


def parse_args(argv: list[str] | None, commands: list[Command]) -> argparse.Namespace:
    args = build_parser(commands).parse_args(argv)
    for name, value in SHARED_DEFAULTS.items():
        if not hasattr(args, name):
            setattr(args, name, value)
    if args.command is None:
        # no sub-command: run the first one, with its own options' defaults
        args.command = commands[0].name
        if commands[0].add_arguments:
            defaults = argparse.ArgumentParser(add_help=False)
            commands[0].add_arguments(defaults)
            args = defaults.parse_args([], namespace=args)
    return args


def main(argv: list[str] | None = None) -> int:
    commands = all_commands()
    args = parse_args(argv, commands)
    command = next(c for c in commands if c.name == args.command)

    try:
        result = command.run(SnapdClient(args.socket), args)
    except SnapdError as exc:
        print(f"snapscope: {exc}", file=sys.stderr)
        return EXIT_ERROR

    color = (
        args.format == "table"
        and not args.no_color
        and sys.stdout.isatty()
        and "NO_COLOR" not in os.environ
    )
    try:
        sys.stdout.write(render(result, args.format, color))
        sys.stdout.flush()
    except BrokenPipeError:  # e.g. `snapscope list | head`
        sys.stderr.close()
    return result.exit_code
