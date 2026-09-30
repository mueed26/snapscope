from __future__ import annotations

from conftest import load, make_snap

from snapscope.commands.cleanup import build, find_reclaimable
from snapscope.models import Snap


def snaps(*dicts: dict[str, object]) -> list[Snap]:
    return [Snap.from_api(d) for d in dicts]


def test_disabled_revisions_are_reclaimable() -> None:
    items = find_reclaimable(
        snaps(
            make_snap("app", revision="12"),
            make_snap("app", revision="11", status="installed", installed_size=5_000_000),
            make_snap("app", revision="10", status="installed", installed_size=4_000_000),
            make_snap("core24", type="base", base=""),
        )
    )
    assert [(r.snap, r.revision, r.reason) for r in items] == [
        ("app", "11", "disabled revision"),
        ("app", "10", "disabled revision"),
    ]
    assert items[0].command == "sudo snap remove app --revision=11"


def test_unused_bases() -> None:
    items = find_reclaimable(
        snaps(
            make_snap("app", base="core22"),
            make_snap("legacy", base=""),  # no base: runs on "core"
            make_snap("core22", type="base", base=""),
            make_snap("core18", type="base", base=""),
            make_snap("core", type="os", base=""),
            make_snap("snapd", type="snapd", base=""),
        )
    )
    assert [(r.snap, r.reason, r.command) for r in items] == [
        ("core18", "unused base", "sudo snap remove core18"),
    ]


def test_real_system_has_nothing_to_reclaim() -> None:
    result = build(snaps(*load("snaps.json")["result"]))
    assert result.tables[0].rows == []
    assert result.data["reclaimable_bytes"] == 0
    assert result.exit_code == 0


def test_totals_and_retain_tip() -> None:
    result = build(
        snaps(
            make_snap("app"),
            make_snap("app", revision="9", status="installed", installed_size=2_500_000),
        )
    )
    assert result.data["reclaimable_bytes"] == 2_500_000
    assert result.tables[0].notes[0] == "Reclaimable: 2.5MB"
    assert "refresh.retain" in result.tables[0].notes[1]
