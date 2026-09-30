"""`snapscope audit`: flag snaps whose sandbox or permissions deserve a look."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass

from snapscope.client import SnapdClient
from snapscope.commands import Command
from snapscope.models import Connection, Snap
from snapscope.render import Result, Table

SEVERITIES = ("info", "warn", "high")

# Interfaces worth knowing about when a snap has them connected.
# See https://snapcraft.io/docs/supported-interfaces
SENSITIVE_INTERFACES: dict[str, tuple[str, str]] = {
    "snapd-control": ("high", "can install and remove snaps: full control of the system"),
    "docker-support": ("high", "effectively root access on the host"),
    "kernel-module-control": ("high", "can load kernel modules"),
    "system-files": ("high", "can access specific system files outside the sandbox"),
    "block-devices": ("high", "raw access to disks"),
    "account-control": ("high", "can add and change user accounts"),
    "ssh-keys": ("high", "can read your private SSH keys"),
    "system-backup": ("high", "read access to the whole filesystem"),
    "home": ("warn", "can read and write non-hidden files in your home directory"),
    "personal-files": ("warn", "can access specific hidden files in your home directory"),
    "removable-media": ("warn", "can access USB drives and SD cards"),
    "camera": ("warn", "can use cameras"),
    "audio-record": ("warn", "can record audio"),
    "network-control": ("warn", "can reconfigure networking"),
    "process-control": ("warn", "can kill and renice any process"),
    "raw-usb": ("warn", "raw access to USB devices"),
    "ssh-public-keys": ("info", "can read your public SSH keys"),
    "system-observe": ("info", "can see all processes and system details"),
    "hardware-observe": ("info", "can read hardware details"),
    "mount-observe": ("info", "can see mounted filesystems"),
    "network-observe": ("info", "can see network status and connections"),
    "log-observe": ("info", "can read system logs"),
}


@dataclass(frozen=True)
class Finding:
    severity: str
    snap: str
    check: str
    detail: str


def rank(severity: str) -> int:
    return SEVERITIES.index(severity)


def audit(snaps: list[Snap], connections: list[Connection]) -> list[Finding]:
    """Pure audit logic, it can be tested with any inputs."""
    active = {s.name: s for s in snaps if s.active}
    findings: list[Finding] = []

    for snap in active.values():
        if snap.devmode:
            findings.append(
                Finding(
                    "high", snap.name, "devmode", "sandbox violations are only logged, not blocked"
                )
            )
        elif snap.confinement == "classic":
            findings.append(
                Finding("warn", snap.name, "classic confinement", "runs without the snap sandbox")
            )
        if snap.held:
            findings.append(
                Finding(
                    "warn",
                    snap.name,
                    "refresh held",
                    "automatic updates, including security fixes, are paused",
                )
            )
        if snap.validation == "unproven" and not snap.is_base:
            findings.append(
                Finding(
                    "info",
                    snap.name,
                    "unverified publisher",
                    f"publisher '{snap.publisher}' is not verified by the Snap Store",
                )
            )

    for conn in connections:
        # only the plug side is interesting: that is the snap being granted access
        if conn.plug_snap not in active or conn.interface not in SENSITIVE_INTERFACES:
            continue
        severity, why = SENSITIVE_INTERFACES[conn.interface]
        how = " (connected manually)" if conn.manual else ""
        findings.append(Finding(severity, conn.plug_snap, f"{conn.interface} interface", why + how))

    findings.sort(key=lambda f: (-rank(f.severity), f.snap, f.check))
    return findings


def exit_code(findings: list[Finding]) -> int:
    """0 clean (info only), 1 warnings, 2 high-severity findings: the severity rank."""
    return max((rank(f.severity) for f in findings), default=0)


def build(snaps: list[Snap], connections: list[Connection], min_severity: str) -> Result:
    findings = audit(snaps, connections)
    shown = [f for f in findings if rank(f.severity) >= rank(min_severity)]
    counts = {sev: sum(f.severity == sev for f in findings) for sev in SEVERITIES}

    summary = (
        f"{len(findings)} findings: "
        f"{counts['high']} high, {counts['warn']} warn, {counts['info']} info"
    )
    hidden = len(findings) - len(shown)
    if hidden:
        summary += f" ({hidden} below '{min_severity}' hidden; use --min-severity info to show)"
    table = Table(
        title="Security audit",
        columns=["Severity", "Snap", "Check", "Detail"],
        rows=[[f.severity.upper(), f.snap, f.check, f.detail] for f in shown],
        notes=[summary],
        empty="No findings at this severity.",
    )
    data = {"findings": [asdict(f) for f in findings], "counts": counts}
    return Result([table], data, exit_code(findings))


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--min-severity",
        choices=SEVERITIES,
        default="warn",
        help="hide findings below this severity in the table (default: %(default)s)",
    )


def run(client: SnapdClient, args: argparse.Namespace) -> Result:
    snaps = [Snap.from_api(d) for d in client.snaps()]
    connections = [Connection.from_api(d) for d in client.connections()]
    return build(snaps, connections, args.min_severity)


COMMAND = Command(
    "audit", "flag risky confinement, held refreshes and sensitive interfaces", run, add_arguments
)
