"""Output: aligned text tables, Markdown and JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

FORMATS = ("table", "json", "markdown")

_RESET = "\033[0m"
_BOLD = "\033[1m"
_COLOURS = {"HIGH": "\033[31m", "WARN": "\033[33m", "INFO": "\033[36m"}


@dataclass
class Table:
    title: str
    columns: list[str]
    rows: list[list[str]]
    notes: list[str] = field(default_factory=list)  # lines printed under the table
    empty: str = "Nothing to show."


@dataclass
class Result:
    """What a command produces: tables for people, data for machines."""

    tables: list[Table]
    data: dict[str, Any]
    exit_code: int = 0


def render(result: Result, fmt: str, color: bool = False) -> str:
    if fmt == "json":
        return json.dumps(result.data, indent=2) + "\n"
    if fmt == "markdown":
        return "\n".join(_markdown(t) for t in result.tables)
    return "\n".join(_text(t, color) for t in result.tables)


def _text(table: Table, color: bool) -> str:
    lines = [f"{_BOLD}{table.title}{_RESET}" if color else table.title]
    if table.rows:
        widths = [len(c) for c in table.columns]
        for row in table.rows:
            widths = [max(w, len(cell)) for w, cell in zip(widths, row, strict=True)]
        widths[-1] = 0  # no padding after the last column, so no trailing spaces
        lines.append("  ".join(c.ljust(w) for c, w in zip(table.columns, widths, strict=True)))
        for row in table.rows:
            cells = [_paint(c.ljust(w), c, color) for c, w in zip(row, widths, strict=True)]
            lines.append("  ".join(cells))
    else:
        lines.append(table.empty)
    lines.extend(table.notes)
    return "\n".join(lines) + "\n"


def _paint(padded: str, value: str, color: bool) -> str:
    # colour after padding so escape codes don't upset the column widths
    if color and value in _COLOURS:
        return f"{_COLOURS[value]}{padded}{_RESET}"
    return padded


def _markdown(table: Table) -> str:
    lines = [f"## {table.title}", ""]
    if table.rows:
        lines.append("| " + " | ".join(table.columns) + " |")
        lines.append("|" + "---|" * len(table.columns))
        for row in table.rows:
            lines.append("| " + " | ".join(_md_cell(c) for c in row) + " |")
    else:
        lines.append(table.empty)
    if table.notes:
        lines.append("")
        lines.extend(table.notes)
    return "\n".join(lines) + "\n"


def _md_cell(value: str) -> str:
    return value.replace("|", "\\|") or " "
