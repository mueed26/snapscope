from __future__ import annotations

import json

import pytest
from conftest import FakeSnapd, error, load, ok

from snapscope.client import SnapdClient, SnapdError, SnapdUnavailable, parse_response


def test_parse_response_returns_result() -> None:
    assert parse_response(json.dumps(ok([1, 2])).encode(), 200) == [1, 2]


def test_parse_response_raises_snapd_errors() -> None:
    body = json.dumps(load("error.json")).encode()
    with pytest.raises(SnapdError) as info:
        parse_response(body, 404)
    assert info.value.kind == "snap-not-found"
    assert info.value.status == 404
    assert "not installed" in str(info.value)


@pytest.mark.parametrize("body", [b"not json", b"[1, 2]"])
def test_parse_response_rejects_garbage(body: bytes) -> None:
    with pytest.raises(SnapdError):
        parse_response(body, 200)


def test_get_over_unix_socket(fake_snapd: FakeSnapd) -> None:
    fake_snapd.route("/v2/snaps", ok([{"name": "hello"}]))
    assert SnapdClient(fake_snapd.socket_path).snaps() == [{"name": "hello"}]


def test_query_parameters_are_encoded(fake_snapd: FakeSnapd) -> None:
    fake_snapd.route("/v2/snaps?select=all", ok([]))
    SnapdClient(fake_snapd.socket_path).snaps(all_revisions=True)
    assert fake_snapd.requests == ["/v2/snaps?select=all"]


def test_connections_returns_established_only(real_system: FakeSnapd) -> None:
    conns = SnapdClient(real_system.socket_path).connections()
    assert {c["interface"] for c in conns} == {
        "hardware-observe",
        "network",
        "process-control",
        "system-observe",
    }


def test_nothing_to_refresh_is_an_empty_list(fake_snapd: FakeSnapd) -> None:
    fake_snapd.route(
        "/v2/find?select=refresh", error(404, "snap-not-found", "snap not found"), status=404
    )
    assert SnapdClient(fake_snapd.socket_path).refresh_candidates() == []


def test_other_refresh_errors_propagate(fake_snapd: FakeSnapd) -> None:
    fake_snapd.route(
        "/v2/find?select=refresh", error(400, "network-timeout", "store unreachable"), 400
    )
    with pytest.raises(SnapdError, match="store unreachable"):
        SnapdClient(fake_snapd.socket_path).refresh_candidates()


def test_missing_socket_is_reported_clearly() -> None:
    client = SnapdClient("/nonexistent/snapd.socket")
    with pytest.raises(SnapdUnavailable, match="not found"):
        client.snaps()
