from __future__ import annotations

import pytest
from conftest import load, make_snap

from snapscope.models import Connection, Snap, human_size, publisher_label


@pytest.fixture
def real_snaps() -> dict[str, Snap]:
    return {s.name: s for s in (Snap.from_api(d) for d in load("snaps.json")["result"])}


def test_parses_real_snapd_output(real_snaps: dict[str, Snap]) -> None:
    kubectl = real_snaps["kubectl"]
    assert kubectl.confinement == "classic"
    assert kubectl.base == "core20"
    assert kubectl.channel == "latest/stable"
    assert real_snaps["htop"].validation == "starred"
    assert real_snaps["core"].is_base  # type "os"
    assert real_snaps["core20"].is_base  # type "base"
    assert not real_snaps["snapd"].is_base


def test_app_without_base_runs_on_core(real_snaps: dict[str, Snap]) -> None:
    assert real_snaps["hello-world"].runtime == "core"
    assert real_snaps["htop"].runtime == "core24"
    assert real_snaps["snapd"].runtime == ""


def test_hold_and_status() -> None:
    held = Snap.from_api(make_snap("a", hold="2315-01-01T00:00:00Z"))
    assert held.held
    assert not Snap.from_api(make_snap("b")).held
    assert not Snap.from_api(make_snap("c", status="installed")).active


def test_missing_optional_fields_have_safe_defaults() -> None:
    snap = Snap.from_api({"name": "bare"})
    assert snap.validation == "unproven"
    assert snap.installed_size == 0
    assert snap.confinement == "strict"


def test_connection_from_api() -> None:
    conn = Connection.from_api(load("connections.json")["result"]["established"][0])
    assert conn.plug_snap == "htop"
    assert conn.slot_snap == "snapd"
    assert not conn.manual


@pytest.mark.parametrize(
    ("n", "text"),
    [(0, "0B"), (999, "999B"), (20480, "20.5kB"), (10_883_072, "10.9MB"), (3 * 10**12, "3000.0GB")],
)
def test_human_size(n: int, text: str) -> None:
    assert human_size(n) == text


def test_publisher_label(real_snaps: dict[str, Snap]) -> None:
    assert publisher_label(real_snaps["kubectl"]) == "canonical✓"
    assert publisher_label(real_snaps["htop"]) == "maxiberta✪"
    assert publisher_label(Snap.from_api({"name": "x", "developer": "bob"})) == "bob"
