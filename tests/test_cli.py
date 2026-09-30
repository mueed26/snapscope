"""End-to-end: the real CLI talking to a fake snapd over a Unix socket."""

from __future__ import annotations

import json

import pytest
from conftest import FakeSnapd

from snapscope.cli import main


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def test_list(real_system: FakeSnapd, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "--socket", real_system.socket_path, "list")
    assert code == 0
    assert "kubectl" in out
    assert "classic" in out
    assert "canonical✓" in out
    assert "7 snaps using" in out


def test_options_after_the_subcommand(
    real_system: FakeSnapd, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = run(capsys, "list", "--socket", real_system.socket_path, "--json")
    assert code == 0
    assert len(json.loads(out)["snaps"]) == 7


def test_audit_json_and_exit_code(
    real_system: FakeSnapd, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = run(capsys, "--socket", real_system.socket_path, "--json", "audit")
    assert code == 1
    assert json.loads(out)["counts"]["warn"] == 2


def test_min_severity_option(real_system: FakeSnapd, capsys: pytest.CaptureFixture[str]) -> None:
    _, out, _ = run(capsys, "--socket", real_system.socket_path, "audit", "--min-severity", "info")
    assert "system-observe" in out


def test_default_command_is_report(
    real_system: FakeSnapd, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = run(capsys, "--socket", real_system.socket_path)
    assert code == 1
    for title in ("Security audit", "Disk cleanup", "Pending refreshes"):
        assert title in out


def test_markdown(real_system: FakeSnapd, capsys: pytest.CaptureFixture[str]) -> None:
    _, out, _ = run(capsys, "--socket", real_system.socket_path, "-f", "markdown", "report")
    assert "## Security audit" in out
    assert "| WARN | kubectl |" in out


def test_report_json_has_every_section(
    real_system: FakeSnapd, capsys: pytest.CaptureFixture[str]
) -> None:
    _, out, _ = run(capsys, "--socket", real_system.socket_path, "--json")
    assert set(json.loads(out)) == {"audit", "cleanup", "refresh"}


def test_snapd_missing(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(capsys, "--socket", "/nonexistent.socket", "list")
    assert code == 3
    assert out == ""
    assert "snapd socket not found" in err


def test_unknown_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["frobnicate"])
    assert info.value.code == 2  # argparse usage error
