from __future__ import annotations

from conftest import load, make_connection, make_snap

from snapscope.commands.audit import Finding, audit, build, exit_code
from snapscope.models import Connection, Snap


def snaps(*dicts: dict[str, object]) -> list[Snap]:
    return [Snap.from_api(d) for d in dicts]


def conns(*dicts: dict[str, object]) -> list[Connection]:
    return [Connection.from_api(d) for d in dicts]


def checks(findings: list[Finding]) -> set[tuple[str, str, str]]:
    return {(f.severity, f.snap, f.check) for f in findings}


def test_clean_strict_snap_has_no_findings() -> None:
    assert audit(snaps(make_snap("ok")), []) == []


def test_classic_and_devmode() -> None:
    found = audit(
        snaps(
            make_snap("tool", confinement="classic"),
            make_snap("dev", confinement="devmode", devmode=True),
        ),
        [],
    )
    assert checks(found) == {
        ("warn", "tool", "classic confinement"),
        ("high", "dev", "devmode"),
    }


def test_held_refresh_and_unverified_publisher() -> None:
    found = audit(
        snaps(
            make_snap("held", hold="2315-01-01T00:00:00Z"),
            make_snap("anon", publisher={"username": "x", "validation": "unproven"}),
        ),
        [],
    )
    assert checks(found) == {
        ("warn", "held", "refresh held"),
        ("info", "anon", "unverified publisher"),
    }


def test_sensitive_interfaces_by_severity() -> None:
    found = audit(
        snaps(make_snap("app")),
        conns(
            make_connection("app", "ssh-keys"),
            make_connection("app", "home", manual=True),
            make_connection("app", "system-observe"),
            make_connection("app", "network"),  # not sensitive
        ),
    )
    assert checks(found) == {
        ("high", "app", "ssh-keys interface"),
        ("warn", "app", "home interface"),
        ("info", "app", "system-observe interface"),
    }
    home = next(f for f in found if f.check == "home interface")
    assert "manually" in home.detail


def test_findings_sorted_most_severe_first() -> None:
    found = audit(
        snaps(make_snap("a", confinement="classic"), make_snap("b")),
        conns(make_connection("b", "ssh-keys"), make_connection("b", "log-observe")),
    )
    assert [f.severity for f in found] == ["high", "warn", "info"]


def test_ignores_connections_of_disabled_or_unknown_snaps() -> None:
    found = audit(
        snaps(make_snap("old", status="installed")),
        conns(make_connection("old", "home"), make_connection("ghost", "home")),
    )
    assert found == []


def test_exit_codes() -> None:
    assert exit_code([]) == 0
    assert exit_code([Finding("info", "a", "c", "d")]) == 0
    assert exit_code([Finding("warn", "a", "c", "d")]) == 1
    assert exit_code([Finding("warn", "a", "c", "d"), Finding("high", "a", "c", "d")]) == 2


def test_real_system() -> None:
    found = audit(
        snaps(*load("snaps.json")["result"]),
        conns(*load("connections.json")["result"]["established"]),
    )
    assert ("warn", "kubectl", "classic confinement") in checks(found)
    assert ("warn", "htop", "process-control interface") in checks(found)
    assert exit_code(found) == 1


def test_min_severity_hides_rows_but_keeps_counts() -> None:
    result = build(
        snaps(make_snap("a", confinement="classic")),
        conns(make_connection("a", "system-observe")),
        "warn",
    )
    table = result.tables[0]
    assert [row[0] for row in table.rows] == ["WARN"]
    assert result.data["counts"] == {"info": 1, "warn": 1, "high": 0}
    assert "1 below 'warn' hidden" in table.notes[0]
    assert result.exit_code == 1
