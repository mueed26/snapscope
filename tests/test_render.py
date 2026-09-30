from __future__ import annotations

import json

from snapscope.render import Result, Table, render


def sample() -> Result:
    table = Table(
        "Things", ["Name", "Severity"], [["alpha", "WARN"], ["b|c", "INFO"]], ["2 things"]
    )
    return Result([table], {"count": 2})


def test_text_columns_are_aligned() -> None:
    lines = render(sample(), "table").splitlines()
    assert lines[0] == "Things"
    assert lines[1] == "Name   Severity"
    assert lines[2] == "alpha  WARN"
    assert lines[-1] == "2 things"


def test_colour_does_not_break_alignment() -> None:
    coloured = render(sample(), "table", color=True)
    assert "\033[33mWARN" in coloured
    plain = render(sample(), "table")
    strip = coloured.replace("\033[0m", "").replace("\033[1m", "")
    for code in ("\033[33m", "\033[36m"):
        strip = strip.replace(code, "")
    assert strip.split("\n")[1:] == plain.split("\n")[1:]


def test_markdown_escapes_pipes() -> None:
    out = render(sample(), "markdown")
    assert "| Name | Severity |" in out
    assert "| b\\|c | INFO |" in out


def test_json_uses_data_not_tables() -> None:
    assert json.loads(render(sample(), "json")) == {"count": 2}


def test_empty_table_message() -> None:
    out = render(Result([Table("T", ["A"], [], empty="nothing here")], {}), "table")
    assert out == "T\nnothing here\n"
