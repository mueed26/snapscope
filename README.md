<h1 align="center">snapscope</h1>

<p align="center">
  <b>Audit the snaps on an Ubuntu machine: security, disk usage and pending refreshes.</b><br>
  Talks directly to snapd's REST API. Pure Python, zero dependencies.
</p>

<p align="center">
  <a href="https://github.com/mueed26/snapscope/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/mueed26/snapscope/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="Platform: Ubuntu / Linux" src="https://img.shields.io/badge/platform-Ubuntu%20%7C%20Linux-E95420">
  <img alt="Type checked: mypy strict" src="https://img.shields.io/badge/mypy-strict-2a6db2">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green">
</p>

---

`snap list` tells you what is installed. `snapscope` tells you what deserves a
look: snaps running outside the sandbox, snaps with access to your SSH keys
or home folder, disk space wasted on old revisions, and updates waiting in the
Snap Store.

Real output from an Ubuntu 24.04 machine:

```text
$ snapscope
Security audit
Severity  Snap     Check                      Detail
WARN      htop     process-control interface  can kill and renice any process
WARN      kubectl  classic confinement        runs without the snap sandbox
4 findings: 0 high, 2 warn, 2 info (2 below 'warn' hidden; use --min-severity info to show)

Disk cleanup
Nothing to reclaim: no disabled revisions or unused bases.

Pending refreshes
Snap   Installed       Available       Channel
snapd  2.76.3 (27738)  2.77.1 (28254)  latest/stable
Run: sudo snap refresh
```

## Contents

- [Features](#features)
- [Quick start](#quick-start)
- [Commands](#commands)
- [The security audit](#the-security-audit)
- [How it works](#how-it-works)
- [Development](#development)
- [Project structure](#project-structure)
- [Roadmap](#roadmap)
- [License](#license)

## Features

- **Security audit.** Flags `devmode` and `classic` confinement, held
  refreshes, unverified publishers, and 22 sensitive interfaces
  (`ssh-keys`, `docker-support`, `home`, `camera`, ...) ranked by severity
- **Disk cleanup.** Finds disabled revisions and base snaps that no app
  uses, and prints the exact `snap remove` commands. It never deletes
  anything itself
- **Pending refreshes.** Checks the Snap Store for newer revisions and lists
  snaps whose automatic updates are held
- **Three output formats.** Aligned tables, `--json` for scripts and
  `--format markdown` for issues and wikis
- **Scriptable exit codes.** `0` clear, `1` warnings or updates, `2` high
  severity, `3` error
- **No dependencies.** Standard library only. Speaks HTTP to
  `/run/snapd.socket` directly, and needs no root access
- **Tested properly.** 53 tests against a fake snapd on a real Unix socket,
  using responses captured from a real machine. CI on Python 3.10, 3.12 and
  3.13, plus a run against real snapd on GitHub's Ubuntu machines

## Quick start

```bash
sudo apt install -y python3-venv git
git clone https://github.com/mueed26/snapscope.git
cd snapscope
python3 -m venv ~/venvs/snapscope && source ~/venvs/snapscope/bin/activate
pip install -e .
snapscope
```

## Commands

| Command | What it does |
|---|---|
| `snapscope` or `snapscope report` | Audit, cleanup and refresh together |
| `snapscope list` | Installed snaps with version, channel, publisher, size and notes |
| `snapscope audit` | Security findings (`--min-severity info\|warn\|high`, default `warn`) |
| `snapscope cleanup` | Reclaimable disk space and the commands to reclaim it |
| `snapscope refresh` | Pending updates from the Snap Store and held snaps |

Options work before or after the command:

| Option | Description |
|---|---|
| `--json` | JSON output |
| `-f`, `--format table\|json\|markdown` | Choose the output format |
| `--no-color` | Plain output (the `NO_COLOR` environment variable also works) |
| `--socket PATH` | Talk to a different snapd socket |
| `-V`, `--version` | Show version |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | All clear |
| `1` | Warnings, or updates pending |
| `2` | High-severity findings |
| `3` | Error (for example, snapd not reachable) |

### Examples

Alert when something high-risk is installed (exit code 2):

```bash
snapscope audit > /dev/null; [ $? -eq 2 ] && echo "high-risk snap found"
```

Post a report to a GitHub issue:

```bash
snapscope --format markdown | gh issue create --title "Snap audit" --body-file -
```

Pull every finding out of the JSON:

```bash
snapscope --json | jq -r '.audit.findings[] | "\(.severity)\t\(.snap)\t\(.check)"'
```

## The security audit

| Check | Severity | Why it matters |
|---|---|---|
| `devmode` | HIGH | Sandbox violations are only logged, not blocked |
| `classic` confinement | WARN | The snap runs with no sandbox at all, like a normal package |
| Refresh held | WARN | Automatic updates, including security fixes, are paused |
| Unverified publisher | INFO | The Snap Store has not verified the publisher's identity |
| `snapd-control`, `docker-support`, `kernel-module-control`, `system-files`, `block-devices`, `account-control`, `ssh-keys`, `system-backup` | HIGH | Close to root access, or access to secrets |
| `home`, `personal-files`, `removable-media`, `camera`, `audio-record`, `network-control`, `process-control`, `raw-usb` | WARN | Access to personal data or devices, or control over the system |
| `system-observe`, `hardware-observe`, `mount-observe`, `network-observe`, `log-observe`, `ssh-public-keys` | INFO | Read-only visibility into the system |

Only the **plug** side of a connection is reported: that's the snap being
granted access. Connections a user made by hand are marked
"connected manually".

## How it works

```text
snapscope ──HTTP over Unix socket──► /run/snapd.socket (snapd)
                                        GET /v2/snaps[?select=all]
                                        GET /v2/connections
                                        GET /v2/find?select=refresh
    │
    ▼
models.py   JSON → typed Snap / Connection objects
    │
    ▼
commands/   pure functions: audit(), find_reclaimable(), pending_updates()
    │
    ▼
render.py   Result → table, JSON or Markdown
```

- **snapd speaks HTTP on a Unix socket.** `client.py` subclasses
  `http.client.HTTPConnection` to connect to `/run/snapd.socket` instead of
  TCP. This is the same API the `snap` command itself uses.
- **Logic is kept separate from I/O.** The audit, cleanup and refresh logic
  are pure functions over typed objects, so they're tested directly with any
  input.
- **Commands are plug-ins.** Each command is a module that exports a
  `Command` and is listed once in `commands/__init__.py`. The first entry is
  the default.
- **Failures are handled gracefully.** If the Snap Store can't be reached,
  the report still runs and says so. If snapd itself is missing, you get a
  clear message and exit code 3.

## Development

```bash
python3 -m venv ~/venvs/snapscope && source ~/venvs/snapscope/bin/activate
pip install -e ".[dev]"
pytest                       # 53 tests
ruff check . && ruff format --check .
mypy                         # strict mode
```

The tests don't need snapd. `tests/conftest.py` starts a small HTTP server
on a temporary Unix socket that serves JSON captured from a real Ubuntu 24.04
machine (`tests/fixtures/`), so the real client code is exercised end to end.

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs lint, type
checks and tests on Python 3.10, 3.12 and 3.13, then runs `snapscope` against
the real snapd on an `ubuntu-24.04` runner.

## Project structure

```text
snapscope/
├── src/snapscope/
│   ├── cli.py              argument parsing, exit codes
│   ├── client.py           snapd REST client over the Unix socket
│   ├── models.py           Snap and Connection types, parsing
│   ├── render.py           table, JSON and Markdown output
│   └── commands/
│       ├── __init__.py     command registry
│       ├── report.py       default: audit + cleanup + refresh
│       ├── list_snaps.py
│       ├── audit.py
│       ├── cleanup.py
│       └── refresh.py
├── tests/                  53 tests, fake snapd, captured fixtures
├── .github/workflows/      CI
└── pyproject.toml
```

## Roadmap

See [ROADMAP.md](ROADMAP.md): packaging snapscope as a snap (and the
confinement question that raises), an opt-in `--fix` for cleanup, an
allowlist for expected findings, and a check for snaps tracking risky
channels.

## License

[MIT](LICENSE) © 2026 Mueed Hyder
