from __future__ import annotations

from conftest import load, make_snap

from snapscope.commands.refresh import build, pending_updates
from snapscope.models import Snap


def test_real_refresh_candidates() -> None:
    installed = [Snap.from_api(d) for d in load("snaps.json")["result"]]
    updates = pending_updates(installed, load("refresh.json")["result"])
    assert len(updates) == 1
    snapd = updates[0]
    assert snapd.snap == "snapd"
    assert snapd.installed_revision == "27738"
    assert snapd.available_revision == "28254"


def test_updates_set_exit_code_and_hint() -> None:
    installed = [Snap.from_api(make_snap("app", version="1.0", revision="5"))]
    result = build(installed, [{"name": "app", "version": "2.0", "revision": "6"}])
    assert result.exit_code == 1
    assert result.tables[0].rows == [["app", "1.0 (5)", "2.0 (6)", ""]]
    assert result.tables[0].notes == ["Run: sudo snap refresh"]


def test_up_to_date() -> None:
    result = build([Snap.from_api(make_snap("app"))], [])
    assert result.exit_code == 0
    assert result.tables[0].rows == []


def test_held_snaps_are_listed() -> None:
    installed = [Snap.from_api(make_snap("frozen", hold="2315-01-01T00:00:00Z"))]
    result = build(installed, [])
    assert result.data["held"] == ["frozen"]
    assert "frozen" in result.tables[0].notes[0]


def test_store_unreachable_is_reported_not_raised() -> None:
    result = build([], None, "network timeout")
    assert result.exit_code == 0
    assert result.data["error"] == "network timeout"
    assert "network timeout" in result.tables[0].empty
