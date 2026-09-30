# Roadmap

Each item is sized for one pull request.

## 1. Warn about risky channels

Flag snaps tracking `edge`, `beta` or `candidate` (for example
`latest/edge`), since pre-release builds on a production machine are a risk.
The data is already there in `Snap.channel`: add a rule to `audit()` and a
test in `tests/test_audit.py`.

## 2. Allowlist for expected findings

Some findings are intentional, such as `kubectl` needing classic
confinement. Read `~/.config/snapscope/allow.toml` (Python's built-in
`tomllib` on 3.11+) listing `snap` + `check` pairs to hide, and still count
them in the JSON output as "allowed".

## 3. Package snapscope as a snap

This is the interesting one. A strictly confined snap can't simply read
`/run/snapd.socket`: full access needs the `snapd-control` interface, which
is super-privileged and needs manual approval from the Snap Store. Options to
investigate:

- `/run/snapd-snap.socket`, which serves a limited set of endpoints to snaps.
  Are `/v2/snaps` and `/v2/connections` among them?
- requesting `classic` confinement, and justifying it
- a `snapd-control` request with a clear security argument

Write up the findings; the trade-off is the point.

## 4. `cleanup --fix`

Remove the reported revisions through the API itself
(`POST /v2/snaps/{name}` with `{"action": "remove", "revision": N}`) after
asking for confirmation. This needs root and handling of snapd's async
"change" responses (poll `/v2/changes/{id}`).

## 5. Fleet mode

`snapscope --json` from many machines (over SSH) combined into one table
that shows which hosts have which findings.

## 6. Shell completion and a man page

Generate bash and zsh completion from the argparse parser, plus a man page.


## good luckk bludd