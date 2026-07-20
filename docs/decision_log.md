# Decision Log

Durable project decisions that future contributors and agents should preserve unless a newer entry supersedes them.

Use this log for decisions that are hard to reverse, cross-cutting, based on external API behavior, or likely to be questioned later. Do not record every small implementation choice.

When a decision changes, keep the old entry and mark it `Superseded`. Add a new entry explaining what changed, why, and any migration notes.

## Status Values

- `Proposed`: under consideration, not yet agreed.
- `Accepted`: current agreed decision.
- `Superseded`: replaced by a newer decision.
- `Rejected`: considered and intentionally not chosen.

## 2026-07-19: Releases Are Automated CalVer Tags Cut By CI

Status: Accepted

Decision: every push to `main` that changes anything an installed copy runs
publishes a GitHub Release tagged `vYYYY.MM.DD` (`.N` suffix for same-day
repeats). No human picks a version number or judges whether a commit "deserves"
a release. The job lives in `.github/workflows/ci.yml` with `needs: test` — a
commit that fails the gates never becomes a release — and the logic is in
`scripts/release_job.py`.

The skip rule is a **blocklist** (`docs/`, `tests/`, `.github/`, any `*.md`,
`.gitignore`, `.pre-commit-config.yaml`), not an allowlist, because the failure
directions are asymmetric: a redundant release is only noise, while a missed
release strands distribution inputs — `install.ps1`, the launcher,
`example.toml`, `.python-version`, `.gitattributes` — at an older tag. When in
doubt, release.

Two properties the job must keep:

- **The Latest invariant.** Concurrent pushes serialize through a fixed
  concurrency group (`cancel-in-progress: false`, `queue: max`), but that
  serialization is FIFO by wait-start time, not by source order — a newer push
  with faster tests can enter the critical section first. So inside it the job
  checks ancestry (`git merge-base --is-ancestor`) against published releases
  and passes `make_latest: false` when a published release descends from its
  own SHA. `make_latest` defaults to true, so without this an older commit's
  slow run would silently downgrade every `latest`-tracking install. After
  claiming Latest, the job asserts `releases/latest` really resolves to its tag.
- **Idempotency across every partial-failure state**, not just
  tag-without-release: a rerun reuses a tag already pointing at `HEAD` and
  *resumes an existing draft* (re-attaching assets) rather than creating a
  second release.

The zip asset is built by `git archive`, the only producer that expands the
`export-subst` stamp — zipping a checkout would ship `version.txt` unexpanded.
A second, tiny asset (`release.json`) carries the tag, full SHA, commit date,
and that release's uv and Python pins, so the installer and launcher never parse
TOML from PowerShell or spend an extra API call resolving the exact SHA
(`releases/latest` reports `target_commitish`, which may be a branch name).

Why: the maintainer explicitly does not want per-commit SemVer judgment, and the
app has no API consumers to justify SemVer semantics. Market research across
fast-shipping projects (yt-dlp, Path of Building Community, RuneLite, and
FFmpeg's binary channels) found dated, immutable, retained artifacts to be the
baseline even for daily-or-faster shippers, and found no comparable project
shipping *unidentified* builds from a branch tip — tags are load-bearing for
rollback and support.

Provenance: this entry and the six below distill the release, versioning, and
distribution proposal added in PR #150 and deleted once shipped (git history
holds the full text). It went through four external design-review rounds plus
the market-research run summarized above, and was implemented in PRs #154,
#155, #158, #159, and the activation PR that removed it.

## 2026-07-19: Releases And Their Assets Are Immutable

Status: Accepted

Decision: GitHub's immutable-releases setting is enabled on the repo, so tags
and releases cannot be moved or deleted. The release job therefore creates a
tag, then a **draft**, attaches assets, validates them, and only then publishes.

Why: rollback is only trustworthy if `v2026.07.19` means the same bytes forever;
a movable tag makes "go back to the version that worked" meaningless. The
setting is not retroactive, which is why it was flipped *before* the release-job
PR merged — that merge cut the first release, and a release published while the
setting was off stays mutable forever.

The consequence to remember: assets lock at publication, so validation must run
pre-publish. After an immutable release is published it is too late to fix a bad
asset — the only remedy is another release. This is what forces the draft-first
flow above; do not "simplify" it into publish-then-attach.

Launcher-side checksum verification is deliberately deferred: HTTPS to
github.com is the trust anchor at this audience size.

## 2026-07-19: Build Identity Comes From The Manifest, Corroborated By The Stamp

Status: Accepted

Decision: one reader (`source/utilities/build_info.py`) resolves the running
build's identity, and every user-visible build string derives from it. The
precedence is manifest → expanded stamp → git → `unknown`:

1. **`install.json`** — the install manifest, written atomically by the
   installer/launcher into the state root, never by the app. The only layer that
   can know the release *tag*.
2. **`version.txt`** — committed with git `export-subst` placeholders
   (`sha: $Format:%H$`, `commit-date: $Format:%cs$`) plus a `.gitattributes`
   entry. GitHub's archive endpoints run `git archive`, which expands them, so
   any zip download carries its full SHA and commit date.
3. **git** — if the placeholders are unexpanded, this is a checkout, so ask it.

The manifest is authoritative **only when it corroborates the running code**:
its `sha` must equal the SHA in the expanded stamp sitting beside that code. The
manifest describes the install's *state*, not any one code directory, so during
a staged update it still names the previous version while the new one is already
running. Unconditional manifest-first precedence would make the new build report
the old identity — and the launcher's own promotion check would then reject it
forever. This was found by the Codex review of PR #154, during implementation,
against a frozen design.

Accepted consequence: a freshly promoted version reports `source: "archive"` and
`tag: None` until the next launch. SHA and date still identify it exactly, and
the tag↔SHA mapping is public in the releases.

`version.txt` is deliberately plain `key: value` text rather than JSON: the
committed file needs a comment header (a raw placeholder looks broken to anyone
browsing the repo), and `export-subst` output is not JSON-escaped, so a JSON
envelope would silently constrain future placeholders to escape-safe expansions.

Identity surfaces in three places, chosen to cost no screen real estate: a
startup line in `data/logs/debug.log` (bug reports arrive with the log), the
existing GitHub icon tooltip in the header, and the browser title (which now
derives from `BuildInfo` instead of advertising a static `v1.0.0`). A footer or
an app-settings page was rejected as spending permanent space on a string read
once per bug report.

Why not have CI commit a version file on every push: the commit changes the SHA,
so the file always describes its own parent; it doubles commit traffic; and it
forces constant fetch friction for the maintainer and for parallel agent
sessions. `export-subst` needs no commits and is never stale.

## 2026-07-19: All Mutable State Lives Under An Explicit State Root

Status: Accepted

Decision: `CSD_STATE_DIR` names the directory holding every mutable file —
`config.toml` and everything under `data/` (playlists, logs, preferences,
caches). Unset means the current working directory, so dev checkouts behave
exactly as before. Bundled read-only assets (`resources/benchmarks`) stop
resolving from the working directory and resolve relative to the installed
package instead, since they ship with the code. `source/utilities/paths.py`
centralizes both rules.

Why: without this split, versioned code directories cannot work at all. Running
the app from a fresh version directory would lose `config.toml` and `data/`;
running it from the state root would lose `resources/benchmarks`. An environment
variable keeps the contract explicit and testable, and lets the launcher — not
the app — own the choice of directories. (An early revision of the proposal
claimed the installer needed zero code changes; that claim was wrong and the
external review killed it.)

## 2026-07-19: The Installer Brings Its Own Toolchain, App-Locally

Status: Accepted

Decision: installation is a PowerShell one-liner that fetches `get.ps1` from
`main`. That shim is deliberately trivial and permanently backward compatible —
resolve the latest release, fetch *that release's* `install.ps1`, run it,
nothing else — so the installer is always exactly the same age as the payload it
installs. Without the split, any installer change that merged ahead of its
release would run against a payload whose layout it no longer matched, and would
stay broken indefinitely if a release job failed.

The installer puts the **entire toolchain** under the install root
(`%LOCALAPPDATA%\CorporateSerfDashboard` by default): `UV_UNMANAGED_INSTALL`
places uv in the tree and it is invoked by absolute path,
`UV_PYTHON_INSTALL_DIR` plus `--managed-python` keep a managed CPython there
instead of silently selecting whatever Python the machine has, and
`UV_CACHE_DIR` keeps the cache inside too. No Python, uv, or registry state
outside the root is used or disturbed, so uninstall is deleting the folder and
the shortcut. Two files are written outside it by design: the desktop shortcut
itself, and `get.ps1`'s copy of the installer at
`%TEMP%\csd-install-<tag>.ps1`, which is inert once the install finishes and is
deliberately not cleaned up (the shim stays trivial); the README documents
deleting it.

The uv version is **per release, not per install**: installer and launcher read
the target release's `release.json` and provision that exact uv before syncing.
An install-time-frozen uv would brick the first update that bumps the pin — the
old binary rejects the new project, and `UV_UNMANAGED_INSTALL` disables uv
self-update — so the toolchain upgrade must ride the same transaction as the
code.

First run does not merely copy `example.toml`, whose `stats_dir = "Change me!"`
placeholder would crash the first launch. The installer locates the KovaaK's
stats directory itself (Steam's registry `InstallPath` plus
`libraryfolders.vdf`), confirms it with the user, validates that it exists, and
writes it into `config.toml`. It then **round-trips the generated config through
the installed app's own `load_config()`** and aborts loudly on failure, before
writing the manifest or creating the shortcut. Validating with `tomllib` alone
would only prove the file is syntactically TOML; the app's loader also proves
the schema is one the app accepts. A config the app cannot load must fail the
install loudly rather than surface later as a permanently broken first launch —
permanent because existing `config.toml` and `data/` are never touched again.

Why: the user's machine needs exactly one bootstrapped tool, acquired the way
rustup and uv themselves are distributed. Python and git are never
prerequisites. PyInstaller was rejected: unsigned executables trip SmartScreen
and AV heuristics (fatal for a gaming audience's trust), signing is a recurring
cost, every release would become a large re-download, and bundling
dash/plotly/dash-ag-grid assets under PyInstaller is a known hook-debugging time
sink. Revisit only if "run one command" ever becomes too much to ask.

Addendum (2026-07-20): the first-run `config.toml` now writes only the two
required fields, `stats_dir` and `port`. `polling_interval` (1000) and
`sens_round_decimal_places` (1) gained code defaults on `ConfigData`, so they
are no longer required fields and no longer seeded into the generated file —
`example.toml` still documents them for anyone who wants to tune them. The
round-trip through the installed app's `load_config()` still runs and must pass
with the two-field file.

## 2026-07-19: PowerShell Writes UTF-8 Without BOM And Forward-Slash Paths

Status: Accepted

Decision: every machine-readable file written by the install/launch scripts
(`config.toml`, `install.json`, the `launch.ps1` bootstrap) is written UTF-8
**without** a byte-order mark, via `System.Text.UTF8Encoding($false)`, and every
path inside them uses forward slashes. The scripts target Windows PowerShell
5.1 — the shell the one-liner actually lands in on a stock Windows 11 machine.

Why: 5.1's `-Encoding UTF8` emits a BOM, and this repo's Python 3.14 `tomllib`
rejects both a BOM and raw `\` in TOML basic strings. Either alone yields a
config the app can never parse, which the never-touch-an-existing-config rule
would then make permanent. Both halves were verified empirically against this
repo's interpreter rather than taken from documentation.

This is a contract, not a style preference: do not "modernize" these writes to
`Set-Content -Encoding UTF8`, and do not let Windows-native backslashes reach a
generated TOML file.

## 2026-07-19: Updates Are Staged, Reversible, And Speak A Frozen Wire Contract

Status: Accepted

Decision: the desktop shortcut targets a stable bootstrap at the install root
(`launch.ps1`) that reads the manifest and delegates to the selected version's
launcher — nothing else. Per-tag directories get pruned (keep last two), so the
shortcut must never point into one. When the bootstrap itself must change, the
versioned launcher replaces it on a higher embedded marker by writing a
same-directory temp file, validating its marker and PowerShell syntax, then
renaming over it. Never truncate the live file in place: PowerShell keeps
executing the already-parsed body, so an interrupted in-place write leaves a
working session now and a bricked entrypoint for every launch after it.

The launcher is **single-instance** via a named mutex scoped to the install
root, held for the launcher+app lifetime. A second launch opens the browser at
the running instance and exits without updating, syncing, or touching the
manifest — atomic manifest writes protect one file, not a whole transaction.

Then it applies the manifest's policy:

- **`latest`** (default): query `releases/latest` on a short timeout; a
  different tag is downloaded and synced into a new per-tag directory but is
  **not promoted yet**. It starts as a pending activation, and the launcher
  polls `/health` until the child process is still alive *and* the response
  carries the expected full SHA and a per-launch token passed in by environment
  variable. A bare HTTP 200 is not proof of life: an already-running instance or
  an unrelated service holding the port can answer while the pending process
  never bound. Only then is the manifest atomically rewritten. On timeout or
  early exit the launcher starts the previous version and leaves the manifest
  untouched — a crashing release never becomes the recorded install. The gate
  deliberately does **not** require a tag match, because a build on trial is
  still described by the previous manifest and reports `tag: None` under the
  corroboration rule above. Any network or API failure fails open: run what is
  installed, offline-safe.
- **`pinned`** + `pinned_tag`: skip the update check entirely. A rollback
  install (`install.ps1 -Tag ...`) *writes this pin*; without it the next launch
  would immediately reinstall the bad release, making rollback a no-op. Undoing
  it is explicit: re-run the installer without `-Tag`.

**Wire contract v1.** A pinned or long-offline install may jump from the first
launcher straight to any future release, and the launcher performing that update
is always the *old* one. So everything an old launcher parses is a frozen,
versioned contract from day one: `release.json` and `install.json` both carry
`schema_version: 1`, and the v1 field set froze when the installer shipped.
Changes within v1 are additive-only. A breaking change bumps the version and
dual-publishes the v1 envelope for as long as v1 launchers may exist. A launcher
meeting an unknown `schema_version` — or any parse failure — runs the existing
install and says so loudly ("re-run the install one-liner"), because fail-open
alone would convert a contract break into *silent permanent stranding*: every
launch retries, fails, runs the old version, and never tells the user.

`install.json` deliberately carries **no uv field and no zip-prefix field**. The
launcher takes uv from the new release's `release.json` at update time, and
running the current version needs no uv at all — it starts the synced venv's
`python.exe` directly, which is offline-safe and makes the health gate and the
kill target the real server process rather than a wrapper. The zip's top-level
directory name is **discovered after extraction, never derived**: the named
asset keeps the "v" (`Corporate-Serf-Dashboard-v2026.07.19/`) while GitHub's
source-archive fallback strips it. Both scripts assert exactly one top-level
directory and verify the extracted stamp's SHA before syncing.

Rollback protects *code*; durable state is governed by a rule rather than
machinery. Releases must read older state (missing keys get defaults) and must
not rewrite user-authored files. The durable state is a handful of tiny,
schema-stable files, so a genuine format break is rare enough to be called out
in its PR with a manual step — the house convention at this user-base size.
State snapshot/restore was deferred on that basis.

Accepted limitation: a release that fails its health gate is retried in full —
download, sync, then the readiness timeout — on every launch until the next
release lands. Bounded by the near-daily release cadence; the escape hatches are
the rollback pin and waiting for the replacement release. Documented rather than
solved with a failed-tag marker.

## 2026-07-19: The App Binds Its Port Exclusively And Exits If It Is Taken

Status: Accepted

Decision: `source/app.py` creates and binds the listening socket itself
(`bind_server_socket`), sets `SO_EXCLUSIVEADDRUSE` where the platform has it,
and hands the bound socket to waitress as `serve(app.server, sockets=[sock],
threads=8)`. A failed bind prints an actionable message naming the port and
`config.toml`, then exits 1. Do not "simplify" this back to
`serve(app.server, host=..., port=...)` — that reintroduces the bug below.

Why: on Windows, a socket bound with `SO_REUSEADDR` (waitress's default for
sockets it creates) does not reserve the address. A second process can bind
the same `127.0.0.1:<port>` while the first is serving it, and Windows then
splits incoming connections nondeterministically between the two. The visible
symptom is a second copy of the dashboard silently answering some requests
with its own state — observed live during the release-launcher work, where
the launcher's `/health` token gate correctly refused to promote the build
but the user got a 120-second hang instead of an error. It is also the
long-standing "one dev run shadowing another on localhost" trap. POSIX
already refuses the second bind, so the flag is the Windows-only half of a
behavior we want everywhere.

Mechanism, verified against waitress 3.0.2: a socket passed through
`sockets=` is constructed with `bind_socket=False`, so waitress never binds
it, and `accept_connections()` calls `listen()` — hand it over **bound but
not listening**. Waitress then calls `set_reuse_addr()` on it unconditionally;
on an exclusively-bound socket that `setsockopt` fails with `WSAEINVAL`
(10022) and waitress swallows the error, so exclusivity survives. Confirmed
empirically: with the flag set, a second bind of the same port is refused
whether the second binder asks for a plain bind (`WSAEADDRINUSE` 10048),
`SO_REUSEADDR` (`WSAEACCES` 10013), or `SO_EXCLUSIVEADDRUSE` (10048).

Alternatives rejected: probing `/health` for a foreign responder before
binding (racy — the port can be taken between probe and bind — and blind to
non-app squatters like Steam on 8080); a launcher-side check (the launcher
already fails safe on a shadowed health answer, and with this change the
duplicate exits immediately, which its "exited" path already handles).

Scope: the `config.debug` Flask development-server path is unchanged; it is a
dev-only convenience. The bind happens immediately before `serve()`, so a
duplicate instance still does its ~2s of startup work before exiting.

POSIX footnote: binding the socket ourselves means waitress's pre-bind
`SO_REUSEADDR` no longer applies, and on POSIX that flag is what lets a
server rebind a port whose old connections are still in `TIME_WAIT`. A fast
restart there could now be refused. Windows is unaffected — verified that an
immediate rebind succeeds with a genuine `TIME_WAIT` pair on the port. We
accept this because nothing serves on POSIX: the app targets Windows and CI
runs `windows-latest` only. If that ever changes, set `SO_REUSEADDR` before
`bind()` on non-Windows platforms — on POSIX it permits the `TIME_WAIT`
rebind without letting a second live server share the port, so it restores
the old behavior without weakening the Windows guarantee.

Addendum, 2026-07-20: both loopback faces are bound, not just IPv4.
`bind_server_socket` now returns a list — `127.0.0.1` and `::1`, same port,
each claimed with the same `SO_EXCLUSIVEADDRUSE` treatment — and both go to
waitress as `sockets=`. The IPv4-only bind left the decision half-enforced:
on Windows `localhost` may resolve to `::1` first, so an unrelated process
holding the IPv6 face still captured every browser request to
`http://localhost:<port>/` while the dashboard sat unreachable on IPv4.
Observed live during the PR #153 session — another project's server held
wildcard `::` while the dashboard held `127.0.0.1`, and the browser got the
stranger's 404 page. (The squatter was *not* a `config.debug` run of this
app: werkzeug picks the address family with a colon heuristic, so its
`host="localhost"` always binds `AF_INET` `127.0.0.1` — verified against the
pinned werkzeug.) Claiming `::1` ourselves collapses that to the two outcomes
the original decision wanted: a specific bind takes routing precedence over
someone else's wildcard `::`, and if the face is genuinely taken the app
exits loudly instead of being silently shadowed.

Do not "simplify" the two sockets into one dual-stack `AF_INET6` socket with
`IPV6_V6ONLY=0`. That shape does not work here at all: v4-mapped addressing
applies only to wildcard binds, so a dual-stack socket bound to `::1` accepts
no `127.0.0.1` traffic whatsoever. Two explicit sockets are the only correct
shape, and they keep the per-face exclusivity semantics verified above.

Failure semantics stay deliberately two-bucket. Either face already taken
(`EADDRINUSE`) closes whatever was bound and takes the existing exit-1 path,
now with a message saying the port must be free on both addresses — a port
free on only one face is refused outright rather than half-served. IPv6
genuinely absent (`EAFNOSUPPORT` creating the socket, or `EADDRNOTAVAIL`
binding `::1`) logs one info line and serves IPv4 alone; on such a machine
`localhost` resolves to IPv4 anyway, so the ambiguity disappears with the
interface. Re-verified against waitress 3.0.2 that the multi-socket path
gives each socket the same treatment as the single-socket contract above:
`create_server` loops over `adj.sockets` constructing every `AF_INET`/
`AF_INET6` socket with `bind_socket=False`, calls the swallowed
`set_reuse_addr()` per socket, and calls `listen()` per socket in
`accept_connections()`; with two entries it returns a `MultiSocketServer`
driving both from one loop.

## 2026-07-19: Default Port Is 8050, Not 8080

Status: Accepted

Decision: The example config (`example.toml`) ships with `port = 8050`. The
app itself has no built-in default — `port` is a required config field served
through waitress — so the example file is the only default we own.

Why: 8080 is one of the most contended ports on end-user machines; Steam in
particular holds it whenever it is running, and this app's audience is
KovaaK's players, who all run Steam. 8050 is the Dash convention (`app.run()`
default), so it signals "Dash app" to anyone inspecting the port, and its
only common occupant is *other* Dash apps run with defaults — a rare
collision for this audience. No port choice defends against Windows
Hyper-V/WSL2 excluded-port-range reservations, which land semi-randomly;
the `port` config setting remains the escape hatch for any collision.

Migration: none in-app (single-user convention — no compat shims). Existing
installs keep whatever their `config.toml` says; only fresh copies of
`example.toml` pick up 8050.

## 2026-07-18: Accept Dash's First-Request Pages Race Instead of Warming the App

Status: Accepted

Decision: The browser-console noise on the first page load after a server
start — a `TypeError: Cannot read properties of undefined (reading 'apply')`
from `handleClientside`, plus a flood of ~86 "ID not found in layout" entries
in the dev-tools overlay — is a known upstream Dash defect. We accept it and
do not work around it. Treat it as expected baseline noise during browser
checks; reload the page before judging whether the console is clean.

Why: Dash's `enable_pages()` registers its page router as a `before_request`
hook (`dash/dash.py`, in `router_sync`/`router_async`). The hook sets its
`_got_first_request["pages"]` guard flag *before* it finishes its work, and
takes no lock:

```python
if self._got_first_request["pages"]:
    return
self._got_first_request["pages"] = True
...   # builds validation_layout, registers the document.title clientside callback
```

Inline clientside function bodies are injected into the index HTML at render
time. Under a threaded server — Waitress with `threads=8` in production,
Flask's threaded dev server when `debug = true` — a concurrent early request
sees the flag already set, returns immediately, and serves an index page whose
script block is missing, while `/_dash-dependencies` still advertises the
callback. The renderer looks the function up, gets `undefined`, and calls
`.apply` on it. `validation_layout` is populated in the same unfinished hook
body, which is why the "ID not found in layout" flood appears alongside: one
root cause, two symptoms.

Measured 2026-07-18 on dash 4.4.0: eight simultaneous first requests produced
**seven of eight** renders missing the script; every later render has it. A
browser triggers it because it opens several connections at startup.

The missing function is Dash's own `_pages_dummy` `document.title` setter, not
application code — all six of our clientside callbacks register correctly every
time. It is not a dash-extensions defect either: `DashProxy._setup_server`
correctly takes a `setup_server_lock`, and plain `dash.Dash` races identically
(measured: 7/8 for both, in a minimal app with no dash-extensions involved).
It reproduces on dash 4.3.0 and 4.4.0 alike, so it is not a regression from the
PR #146 dependency upgrade.

### Reproducing it requires a wide enough race window

Two conditions must both hold, which is why a casual minimal repro shows
nothing and reports "works fine":

1. **`suppress_callback_exceptions` must be at its default `False`.** When it
   is `True`, Dash skips the whole `validation_layout` block inside the pages
   router (`dash/dash.py`, the `if not self.config.suppress_callback_exceptions:`
   guard) — which is the slow part of the hook. The window collapses to
   near-zero and the race effectively never fires. This app leaves the setting
   at its default.
2. **Page layouts must be expensive enough to matter.** That block calls every
   registered page's layout function to build `validation_layout`. The window
   is as wide as those calls take. A `html.Div("hi")` page closes it instantly;
   this app's real page layouts hold it open long enough to lose 7 of 8 races.
   A minimal repro reproduces once a page layout is given real work to do
   (a 0.4s sleep was sufficient).

Practical consequence: **do not expect an upstream fix to arrive on its own.**
Most small Dash apps and most upstream tests satisfy neither condition, so the
bug is invisible in exactly the places that would catch it. Absent someone
filing it (not done as of 2026-07-18), assume it survives future Dash releases
rather than treating a version bump as a likely cure. Re-check cheaply after a
Dash upgrade: load the app once, reload, and see whether the first-load console
noise is gone.

Impact is cosmetic and self-healing: on an affected load `document.title` shows
the app-level title instead of the page title, and any reload fixes it. A
workaround for someone else's bug is not worth carrying for that.

"No feature is affected" is measured, not assumed. Exercised on a load
confirmed to have lost the race — six of seven clientside functions registered,
86 "ID not found in layout" entries, the app-level title — the Home page still
rendered fully, the Plotly graph mounted (a beat later than usual), server
callbacks fired and returned 200, and toggling the x-axis radio round-tripped
end to end and updated the figure. The only observable defect was
`document.title`. The "ID not found in layout" flood is the renderer reporting
a transient state it recovers from, not callbacks being dropped.

Validated mitigation, should this ever become worth fixing: prime the app with
one synchronous in-process request before serving — `with
app.server.test_client() as c: c.get("/")` in `main()`, ahead of `serve(...)` /
`app.run(...)`. Measured under the same eight-way concurrency test, this took
seven-of-eight failures down to zero. Deliberately not applied.

## 2026-07-18: Accept dash-ag-grid's `columnSizeOptions` Console Warning

Status: Accepted

Decision: The AG Grid console warning `invalid gridOptions property
'columnSizeOptions'`, emitted once per grid mount on the Playlists and
per-playlist scenario pages, is benign upstream noise from the dash-ag-grid
wrapper. We accept it, keep passing `columnSizeOptions`, and do not work
around it. It is distinct from the first-request pages race above: that noise
appears only on the first load after a server start, while this warning
appears on every mount of either grid.

Why: dash-ag-grid folds its remaining props into AG Grid's `gridOptions`
after stripping its own Dash-side props via a hardcoded list
(`PROPS_NOT_FOR_AG_GRID` in the wrapper's `src/lib/fragments/AgGrid.react.js`).
That list contains `columnSize` but not `columnSizeOptions`, so the prop
leaks through and AG Grid's validator flags an unknown key. Our usage is
correct — both are documented top-level `dag.AgGrid` props, and the wrapper
genuinely consumes `columnSizeOptions` (it destructures `keys`, `skipHeader`,
`defaultMinWidth`, `defaultMaxWidth`, and `columnLimits` from it to drive
`autoSizeColumns`/`sizeColumnsToFit`; verified in the installed 35.3.0
bundle). The upstream fix is adding one string to that list.

Correction to the record: the warning was believed fixed by the PR #146
upgrade to dash-ag-grid 35.3.0. Re-verification on a bare `main` baseline
(2026-07-18, during the PR #153 work) showed it still present, so treat it as
expected noise on 35.3.0, not a regression signal.

Alternatives rejected:

- Dropping the prop silences the warning but loses the `keys`/`skipHeader`
  autosize configuration — real behavior traded for cosmetics.
- AG Grid's blanket switch `suppressPropertyNamesCheck` would silence it —
  the bundled v35 validator still honors the flag — but the option is
  deprecated since v33 (AG Grid's deprecation message calls it redundant now
  that `context` exists for arbitrary user data), so enabling it trades the
  invalid-property warning for a deprecation warning while also disabling
  the check that catches real typos in our own gridOptions and colDefs.
- Re-implementing autosizing through a clientside grid-API call just to avoid
  the prop is a workaround for someone else's cosmetic bug — the same bar the
  pages-race entry above declines to meet.

Consequences: treat the warning as expected baseline noise during browser
checks. Not filed upstream as of 2026-07-18, so do not assume a version bump
fixes it; re-check cheaply after a dash-ag-grid upgrade by loading
`/playlists` and looking for the warning. If an upgrade makes it disappear,
mark this entry superseded.

## 2026-07-17: Playlist Import Falls Back to Evxl Exact By-Code

Status: Accepted

Decision: KovaaK's `/playlist/playlists?search=<code>` stays the primary lookup
for playlist import. Whenever it fails to produce exactly one usable record —
zero after the null-drop validator, or more than one match — import falls back
to Evxl's exact `playlist-by-code` endpoint
(`https://api.evxl.app/kovaaks/playlist-by-code?shareCode=<code>`) before
refusing. If the fallback also fails, the user sees the same refusal message as
before.

Why: KovaaK's search has a null-hydration quirk — for some real, public
playlists it counts the match but returns a `null` record, which the
`ignore_null_playlist_items` validator drops, so a valid playlist looks like
zero results (observed: `KovaaKsCarryingGodlikeTile`; details in
`kovaaks_api_notes.md`). There is no first-party KovaaK's by-code endpoint, and
Evxl's by-code lookup resolves arbitrary community playlists exactly.

This is the app's first *runtime* dependency on Evxl; previously Evxl was used
only by the offline `scripts/benchmark_importer`. First-party KovaaK's data
stays preferred on the happy path — Evxl's copy is cached upstream (can be days
stale) and its case-strict HTTP 400 on mis-cased codes would be a worse
default — so Evxl is consulted only when the first-party search cannot resolve
the code cleanly. The stored code is always the canonical `playlist_code` from
whichever source resolved it, never the pasted input.

## 2026-07-16: Warm Playlist Percentiles With One Polite Background Worker

Status: Accepted

Decision: After startup finishes ingesting local runs, one app-lifetime daemon
worker warms the rank and leaderboard-total caches used by the Playlists
overview. Its queue contains only played scenarios from visible playlists,
grouped to finish recently played playlists first. The worker is sequential,
leaves a two-second politeness gap between network items, and blocks on a
condition variable when idle. Unhiding or importing a playlist prepends that
playlist's played scenarios and wakes the same worker; hiding or deleting does
not cancel already queued work.

Queue duplication is intentionally cheap rather than prevented. Every dequeue
rechecks the disk caches and a session outcome map, so duplicate names from
overlapping playlists, repeated imports, and hide/unhide spam skip without
network work. A scenario is fresh enough for the worker when it has a fresh
UNRANKED cache entry, or a fresh RANKED entry plus a fresh leaderboard total.
The overview's display rule is weaker and monotonic: it may read entries of any
age, but it shows aggregate percentiles only after every played scenario in the
playlist is display-resolved. Until then both aggregate cells show an honest
`n/total cached` placeholder; a fully resolved all-UNRANKED playlist shows
`N/A`, not a pending state.

Interactive rank work always takes priority. The shared API activity signal
keeps separate monotonic timestamps for interactive lookups (cache hits
included) and successful network responses. The worker waits for an
interactive quiet window, while outage backoff wakes early only after evidence
of a real network success. The worker calls the lower-level resolve, rank, and
total operations so it can classify failures without the UI service's UNKNOWN
flattening. Before caching UNRANKED it requires one positive username
validation per session; an API-confirmed unknown username stops the whole
queue and produces one UI notification. Connection errors, 5xx responses, and
post-retry 429s tail-requeue with escalating global backoff; read timeouts and
permanent failures become terminal for that session. Three transient attempts
per name are allowed. A restart reconstructs work from cache freshness rather
than persisting queue state.

The Playlists page reads the worker through an immutable snapshot. While queued
or in-flight work exists it shows `Updating percentile data: N remaining
(~ETA)`, using unique non-terminal names and recent pace; outage backoff adds a
paused/retry time and fatal state remains visible. A one-second interval
rebuilds the normal cache-only overview rows and disables itself only after one
final idle rebuild. `Interval.disabled` has one callback owner. That callback
observes a monotonic enqueue generation and is also driven by the page's row
refresh store, so work enqueued after idle re-arms the browser interval and an
older snapshot cannot disable a newer re-arm. Interval-driven cache reads pass
`record_activity=False`; otherwise the reporting loop would continuously mark
the user active and postpone the worker it reports on.

Why: A cold overview previously showed incomplete percentile aggregates only
for scenarios the user happened to open, which made cross-playlist comparisons
biased and unstable. Bulk warming the full play history would spend API budget
on data no overview consumes, while parallel fetching would add avoidable load.
The played-visible queue plus all-or-nothing display makes each completed value
trustworthy, and the background status makes a 15-minute cold fill visible
without blocking any route.

Consequences: `percentile_warmup_enabled` disables only this worker, and an
empty `kovaaks_username` keeps startup and enqueue hooks fully offline.
Interactive Home and playlist-scenario refreshes remain available. The queue,
pace, backoff, and generation state are process-local; cache files remain the
durable data plane and retain their existing atomic-write and monotonic-rank
rules. A separate background TTL and negative leaderboard-resolution cache are
deferred levers. Shipped across PRs #129, #130, #132, and #133.

## 2026-07-13: KovaaK's Timeout Is 30s (Configurable); Read Timeouts Are Not Retried

Status: Accepted

Decision: All KovaaK's API requests share one timeout, default 30 seconds,
configurable via `kovaaks_api_timeout_seconds` in `config.toml` and applied at
app startup through `api_service.set_request_timeout()`. `_get_with_retry`
retries only `requests.ConnectionError` (which covers `ConnectTimeout`); a
`ReadTimeout` fails immediately instead of being retried.

Supersedes: the `requests.Timeout` clause of the 2026-04-28 transient-retry
decision. The `429`/`Retry-After` policy and the `ConnectionError` retry from
that entry stand, and the 2026-06-21 keep-the-hand-rolled-retry decision is
reaffirmed, not revisited.

Rationale: measured 2026-07-13 during a KovaaK's slow spell,
`/leaderboard/scores/global` latency ranged 9–28s while responses stayed
valid — a Postman probe succeeded after ~28s, and in-app fetches succeeded at
9.0–9.4s, just under the old hardcoded 10s wire. With a 10s timeout every
attempt during the spell died, and because the stale-rank fallback is
deliberately read-only (see the 2026-07-12 entry), the same expired cache
entry re-timed-out on every page open — one expired scenario added ~20s to
every playlist load until a fetch succeeded. A read timeout also does not
cancel the server-side query, so the old immediate retry doubled KovaaK's
load for almost nothing (2 of 63 retries succeeded that night); a connection
error, by contrast, means the request never reached the server and remains
safe to retry. 30s clears the observed worst case, and the config knob is the
escape hatch if slow spells drift past it.

Constraints:

- Deliberately a single timeout value — no connect/read split and no
  urllib3 `Retry` adoption (the 2026-06-21 entry holds the full migration
  analysis). Beyond that entry's reasons: the per-retry warnings in
  `_get_with_retry` are the primary forensic log, and the benchmark importer
  depends on its per-call `attempts`/`backoff_seconds` knobs, which
  `requests` cannot express per request through adapter-mounted `Retry`.
- The importer shares the helper, so its retry schedule now governs only
  connection errors and 429s; a read timeout fails the sharecode
  immediately.

## 2026-07-12: Rank-Fetch Failure Degrades To The Last Cached Rank

Status: Accepted

Decision: When `get_scenario_rank_info` has resolved a leaderboard but the
live rank fetch fails — either an unreachable endpoint (`RequestException`) or
a successful-but-unusable, schema-invalid response (`ValidationError`) — it
falls back to the last cached rank (read via `_cached_rank`, ignoring the
rank-cache TTL) instead of returning UNKNOWN. Both failure modes route through
the shared `_stale_rank_fallback` helper. UNKNOWN is reserved for the case
where there is genuinely nothing cached to show. `force_refresh=True` inherits
the same fallback — a failed forced refresh showing last-known still beats
"N/A".

Rationale: the app should never display less than it already knows, and the
behavior was already inconsistent — the Playlists overview reads ranks with
`allow_network=False`, which serves TTL-expired cached ranks, so a transient
KovaaK's failure made the overview show a percentile while Home and the
playlist-scenarios page showed "N/A" for the same scenario. This extends the
existing graceful-degradation precedent in the same function
(`_with_leaderboard_total` keeps a valid rank when the total-players fetch
fails).

Constraints:

- **Read-only.** The fallback path never writes the cache — no
  `_save_rank_monotonic`, no `_write_json`. A write would bump the cache
  file's mtime and launder stale data into TTL-fresh on the next read.
- `scenario_name` is backfilled via `model_copy` when the cached rank lacks
  it; the leaderboard total is attached best-effort from
  `_cached_leaderboard_total` (also TTL-free) and percentile derived, mirroring
  the `allow_network=False` read path.
- The resolve-failure branch is unchanged: no `leaderboard_id` means nothing
  is cached to fall back on.
- The stale result carries a `warning_message`, driving a three-tier toast
  model on the Home rank paths: fetch fails with nothing cached → red error;
  fetch fails but a stale rank is served → yellow warning; fetch succeeds →
  green success (manual refresh only). `refresh_rank`'s green confirmation is
  suppressed by any error *or* warning. No persistent on-display staleness
  indicator is surfaced (`fetched_at` remains on the model for a future
  opt-in).

## 2026-07-11: The Playlist Overview Is The Playlist Management Surface

Status: Accepted

Decision: The `/playlists` overview is the single surface for managing
playlists and benchmarks. It lists every loaded playlist with local
aggregates and hosts all management controls — per-code show/hide, share-code
import, and delete for user playlists — rather than spreading them across a
Settings modal and the filesystem. Concretely:

- **Visibility is a plain per-code show-list**, not file state. It is
  persisted as the `shown_playlists` key in `data/preferences.json`, and a
  playlist is visible iff its code is in the list — uniformly for bundled
  benchmarks and user playlists. A missing (or unusable) preferences file
  yields a first-run seed — the bundled `DEFAULT_VISIBLE_CODES` (Voltaic +
  Viscose) plus every code loaded from the user root — **without writing**;
  the file materializes on the first show/hide, and an existing file is
  authoritative including an empty list (everything hidden on purpose).
  Importing a code appends it (importing is the intent to see); hide removes,
  unhide re-adds. `get_visible_playlist_selector_options()` is the single
  visibility filter every option list consumes (Home filter, Journey picker,
  overview), so they cannot disagree. Hidden playlists still load, their
  `/playlists/{code}` routes still resolve, and rank overlays still draw.
- **The full bundled benchmark library ships flat under
  `resources/benchmarks/`** and is scanned in full at startup, with only the
  curated defaults visible. The whole root is pipeline-managed (machine
  generated by `scripts/benchmark_importer/`; don't hand-edit); the
  bundled-invariant test asserts every committed file carries rank data.
  Enabling a benchmark is one unhide click, not a copy-and-restart, and app
  updates refresh the library automatically.
- **Delete exists only for user playlists** (`data/playlists/` files). It
  unlinks the file recorded for that code at load/import time (not a
  reconstructed name, so hand-dropped filenames are handled), drops the store
  entry, and forgets the code's show-list membership so `preferences.json`
  does not accumulate dead codes. Bundled benchmarks cannot be deleted —
  hiding is the equivalent, which forecloses the delete-then-reimport
  degradation (a share-code re-import comes back rank-less).
- **Startup stays read-only.** A `data/playlists/` file whose code is already
  served by a bundled benchmark (a pre-#90 copy-to-activate leftover) is
  skipped with a warning; the overview surfaces those dead copies with an
  in-app cleanup action instead of deleting anything at load.

Why: The bare `/playlists` route was a name-only dropdown that answered
nothing about where to direct attention, and shipping the whole benchmark
library would have flooded every dropdown with 100+ rows. Visibility protects
browsing and first-run focus (search only helps when you already know the
name). Managing playlists by editing files ("copy a JSON in, restart") is the
opposite of "the user interacts with the app, not the filesystem." The
single-writer/single-user assumption (the user is also the library curator)
lets visibility be a plain show-list instead of a richer defaults-aware store.

Consequences: This entry supersedes the `resources/playlists/` bundled-root
path in the 2026-06-22 and 2026-07-07 entries: the bundled root is now
`resources/benchmarks/`. Accepted tradeoff: a future default-worthy benchmark
(e.g. a Voltaic S6) arrives hidden, because a plain show-list has no
live-evaluated notion of "new default." This is acceptable while the app has
one user who is also the curator — a new benchmark only enters
`resources/benchmarks/` because that user ran the importer and committed it,
and unhiding it is one known click. The rejected richer design (a `shown`
list plus a `hidden` list plus a live-evaluated defaults constant, letting
shipped defaults auto-surface) remains the known, backward-compatible upgrade
path if the app is ever distributed to non-curator users; it was declined
here as machinery defending against a surprise this app cannot currently
produce. Separately, deleting the three legacy top-level Viscose files during
the library flip changed 19 served thresholds; the canonical values are a
fresh importer pull taken at flip time (OQ-9), because KovaaK's is
authoritative for thresholds and the served top-level values were
demonstrably stale.

## 2026-07-11: Match Scenario Names On Their Stripped Form

Status: Accepted

Decision: Scenario-name matching is exact on **stripped** names, and the strip
is enforced at two boundaries: the CSV run parse
(`source/kovaaks/data_service.py`, `scenario = line.split(",", 1)[1].strip()`)
and a `field_validator` on `Scenario.name` in `source/kovaaks/data_models.py`.
The model validator normalizes every path that builds a `Scenario` — runtime
share-code import, bundled/user playlist file load
(`PlaylistData.model_validate_json`), and the benchmark importer's output —
so a playlist scenario name always joins `kovaaks_database` (which is keyed by
the CSV-stripped names) under the same key. The validator is lenient on an
empty result (a whitespace-only name becomes `""` rather than raising, unlike
the sibling `code` validator) because a blank scenario name is an odd upstream
quirk, not a store key, and must not reject the whole playlist import.

Why: Every scenario lookup is exact-match — `is_scenario_in_database` (dict
membership), `get_rank_data_from_playlist_code` (`!=` compare),
`get_scenarios_from_playlist_code` (verbatim) — while `kovaaks_database` keys
are always stripped. A padded name from the KovaaK's playlist API therefore
never resolved local runs / PB / rank overlays. Padding is observed, not
hypothetical: PR #97 found real corpus files with one- and five-space paddings
from the KovaaK's benchmark API. The model boundary was chosen over a call-site
strip (which would fix only one of the three entry points — the #97
whack-a-mole) and over normalize-at-lookup (which would spread the invariant
across every comparison and dict lookup); it is a single choke point that
mirrors the existing `PlaylistData.strip_and_require_code` precedent.

Consequences: The two enforcement points must agree — drift between the CSV
parse strip and the `Scenario.name` validator silently recreates this bug
class, so a future change to the normalization strategy must update both
together (a shared `normalize_scenario_name()` helper was considered and
declined as premature; this entry is the cheaper drift guard). Nothing bakes
the association in: `kovaaks_database` is rebuilt from CSVs each startup and the
validator re-runs on every playlist file load, so the match key is re-derived
at runtime on both sides and changing strategy re-keys everything on the next
startup. Name-keyed persisted caches (leaderboard-id / rank) tolerate a
strategy change by design — a miss refetches, bounded by the 168 h TTLs. The
only one-way loss is that imported playlist JSON persists the stripped name,
discarding original padding (semantically void whitespace, recoverable by
re-import from the code). The benchmark importer's own `.strip()` at
`scripts/benchmark_importer/script.py` is now redundant defense-in-depth and is
left in place. Shipped in PR #100.

## 2026-07-11: Humanize The Absolute Timestamp Format

Status: Accepted

Decision: The absolute "on-hover / in-title" timestamp adopts a GitHub-shaped, humanized format instead of the previous `%Y-%m-%d %I:%M:%S %p` (which rendered `2026-04-12 07:04:22 PM`). Two variants: staleness surfaces (home last-played tooltip, playlist/scenario grid tooltips, plot-title `updated:`) show `Apr 9, 2026, 7:04 PM` (no seconds); the per-run scatter hover shows `Apr 9, 2026, 7:04:22 PM` (seconds kept). Format rules: abbreviated English month from a hardcoded array (never `%b`/`calendar.month_abbr`), unpadded day, 4-digit year, unpadded 12-hour hour with `0 → 12` (midnight `12:xx AM`, noon `12:xx PM`), zero-padded minutes/seconds, uppercase space-separated AM/PM, browser/local time with no timezone suffix. The Python side is `format_absolute_timestamp(dt, *, include_seconds=False)` in `source/utilities/utilities.py`; the JS side is `dagfuncs.absoluteTime` in `assets/dashAgGridFunctions.js`, which mirrors the no-seconds variant. The relative string, the `Never`/`—` sentinels, the epoch-seconds plumbing, and the dotted-underline tooltip affordance are all unchanged.

Why: Market research (GitHub, Discord, Slack, Steam, AWS Cloudscape) confirmed the relative-primary + absolute-on-hover pattern is standard, but the old absolute string deviated from every comparator — a zero-padded 12-hour hour (no consumer app pads it), seconds on staleness surfaces (GitHub/Discord/Cloudscape all drop them), and a machine-register ISO date glued to a consumer-register AM/PM time. The GitHub shape reads as one register. Seconds are kept only on the run-level hover because they cross-reference KovaaK's second-stamped stats CSV filenames. The format is hand-rolled (not `strftime`/`toLocaleString`) for locale independence (hardcoded month array) and because no cross-platform strftime code exists for an unpadded hour (`%-I` is POSIX-only, `%#I` Windows-only).

Consequences: Python↔JS parity is held by this spec and by hand — there is no JS test harness — so the two implementations must be kept in sync (both carry a comment pointing at the other). This supersedes only the exact-format aspect of the 2026-06-21 and 2026-06-30 entries; their behavioral decisions stand.

## 2026-07-09: Load Configuration Lazily At Application Startup

Status: Accepted

Decision: Configuration is loaded and cached through `get_config()` instead of
at module import. `main()` owns the initial load and translates expected file,
decode, TOML, and validation failures into the existing concise startup error
before loading playlists or initializing runtime services. Other modules resolve
the cached configuration only inside function bodies.

Why: Import-time loading forced pytest to overwrite the real repo-root
`config.toml`, keeping its backup only in process memory. Abnormal termination
could permanently replace a user's configuration, and concurrent test sessions
could corrupt each other's backup/restore chain. A lazy production accessor makes
modules import-safe and gives tests an in-process seam without adding a test-only
environment-variable override.

Consequences: Tests monkeypatch the config loader and clear the accessor cache;
they never modify the real `config.toml`. `get_config()` propagates load errors,
while the executable startup boundary alone prints the user-facing message and
exits. Playlist loading happens in `main()` after configuration validation so a
bad config still produces exactly one clean error with no prior warning output.

## 2026-07-09: Accept Unsynchronized In-Memory Stores (Single-Writer)

Status: Accepted

Decision: The module-global in-memory stores in `source/kovaaks/data_service.py`
(`kovaaks_database`, `run_database`, and `playlist_database`) remain
unsynchronized. No lock is added. This is a reviewed acceptance, not an
oversight.

Why: Design review (2026-07-09) verified the structural guarantees that bound
the risk. After startup, the watchdog observer thread is the only writer to
`kovaaks_database`/`run_database` (the startup bulk load is single-threaded,
before the observer and server exist), so writer-writer corruption cannot
occur. The top-level `kovaaks_database` dict is read via GIL-atomic lookups;
the one reader that iterates it (`get_scenario_stats_snapshot`, PR #78)
snapshots with a single C-level `list()` call that a concurrent insert cannot
break, and PR #78 also made the writer replace `ScenarioStats` objects instead
of mutating fields in place, so a reader that binds one sees field-consistent
values. The remaining exposure is server-thread readers iterating nested
`sortedcontainers` structures (and the journey page walking `run_database`)
mid-`add()`: worst case is a skipped or duplicated point, or a rare exception,
in one render. Dash contains callback exceptions and no path writes torn state
back. Self-healing has two cadences: home-page consumers re-render on the
polling interval, so races there clear within about a second; the journey,
playlist grid, and playlist overview pages rebuild store-derived data only on
navigation or control interaction (their intervals only re-tick relative
timestamps), so a raced render there can persist until the next interaction.
Both cadences stay within the accepted class — a wrong or failed render, never
corrupted state. The load-before-notify
ordering in `_enqueue_after_loading` guarantees a drained message's run is
already fully visible in the stores. `playlist_database` carried the same
class between server threads (the import callback's insert vs. `.values()`
iterations under Waitress's worker pool) until PR #78 converted its iterating
readers to the same `list()` snapshot pattern, leaving only atomic containment
checks and single-key lookups exposed — which are safe. A coarse lock
was rejected because it imposes permanent accessor discipline — silent when
violated — against a self-healing one-frame glitch; a single-writer ingest
redesign was rejected as not worth reworking the load-before-notify contract
on its own.

Consequences: Two lists govern when this decision ends. Hazard triggers (add
synchronization, or implement the single-writer ingest redesign): a store-race
exception or corruption actually observed in logs; a genuine second writer to
these stores (for example runtime playlist reload or a background recompute);
a move to free-threaded (no-GIL) CPython, which weakens the per-bytecode
atomicity and pure-Python `sortedcontainers` invariants this acceptance leans
on. Resolving events (the problem dissolves as a side effect): a SQLite
migration, or an ingest rework undertaken for other reasons (which should then
adopt the single-writer design). For the SQLite path, file-backed WAL is the
chosen shape — a design choice, not the only technically viable one. In-memory
variants can be shared across threads (a single serialized connection via
`check_same_thread=False`, or one shared database via `cache=shared` or SQLite
3.36+'s `memdb` VFS), while a naive connection-per-thread `:memory:` setup
silently gives each thread a separate empty database. The shared variants are
rejected because WAL does not support in-memory databases, so each of them
forfeits concurrent snapshot-isolated readers and reintroduces reader-writer
serialization or a discouraged mode; file-backed is also the only shape that
serves the persistence and startup-scan justifications that would motivate the
migration in the first place. Run History adds more reader iteration over `run_database` but no
writers; it stays within this acceptance. New readers that iterate a shared
store dict should follow the established snapshot pattern — one C-level
`list()` call before iterating (see `get_scenario_stats_snapshot`). That
pattern is deliberately not extended to the nested `sortedcontainers`
structures, where `list()` is itself Python-level iteration and offers no
atomicity; those remain the accepted self-healing class above.

## 2026-07-08: Judge Score-Threshold Notifications Against The Previous PB

Status: Accepted

Decision: Score-threshold notification verdicts compare in score space against
the personal best the run was chasing:
`score >= previous_high_score * score_threshold_percentage / 100`. The overlay
line still uses the current post-run personal best for the same percentage
setting.

Why: The toast already displays the run's percentage against the previous PB.
Using the post-run PB for the verdict made goals above 100% unreachable,
because a new PB moved the target upward before the run was judged. Keeping the
comparison in score space preserves the exact-threshold `>=` boundary; the
displayed-ratio form can round `820 / 800 * 100` below `102.5` and turn an
exact hit into a failure.

Consequences: Goals above 100% now pass when a run beats the previous PB by
the configured margin. New-scenario and new-sensitivity events still carry
`previous_high_score=None`, so they remain verdict-less. Backlog summaries keep
judging only the batch's latest run; fuller historical pass/fail review belongs
to run history.

## 2026-04-27: Use JSON Files For Runtime API Caches

Status: Accepted (cache root superseded by the 2026-07-11 cache-relocation
entry: caches now live under `data/cache/`)

Decision: Store current API cache data as JSON files under `cache/`.

Why: The current cache use cases are simple key-value lookups with short or medium TTLs. JSON keeps the implementation transparent, easy to inspect, and low-friction.

Consequences: Cache reads must tolerate missing, malformed, stale, or partially-written files. Cache writes should be atomic where practical. Reconsider SQLite when we need rank history, multi-record queries, or stronger transactional guarantees.

## 2026-06-22: Keep User Runtime Data Under `data/`

Status: Accepted (bundled-root path superseded in part by the 2026-07-11
playlist-overview entry: bundled playlists now live under
`resources/benchmarks/`, not `resources/playlists/`; the deferred cache move
shipped in the 2026-07-11 cache-relocation entry)

Decision: Store user/runtime app data under a repo-local ignored `data/` directory. New runtime logs belong under `data/logs/`. Existing API caches remain under `cache/` until a separate migration moves them.

Why: Logs are runtime artifacts, but they are not cache. A dedicated `data/` root keeps future runtime state such as logs, imported/custom playlists, and an eventual SQLite database grouped in one place without mixing it with source-controlled resources.

Consequences: Keep bundled/default playlists under `resources/playlists/`. Put future user-imported or user-created playlists under `data/playlists/`. If the existing API cache moves from `cache/` to `data/cache/`, handle it as a dedicated compatibility migration instead of silently changing paths.

## 2026-07-07: Use Playlist Codes As Playlist Identity

Status: Accepted (bundled-root path superseded in part by the 2026-07-11
playlist-overview entry: the loader's first root is now
`resources/benchmarks/`, not `resources/playlists/`)

Decision: Treat KovaaK's playlist `code` as the app's playlist identity everywhere: the in-memory `playlist_database` key, route value, selector value, import duplicate check, and import filename suffix. Playlist names are display-only labels. Selectors receive finished `{label, value}` options from the service; labels become `Name (CODE)` only when duplicate names need disambiguation.

Why: KovaaK's playlist names are not unique, so name-keyed storage silently dropped later same-named playlists and made those playlists unreachable even by their stable code routes. Codes are already user-facing through share-code imports and `/playlists/{playlistCode}` URLs, so they are the stable identity to preserve.

Consequences: The startup loader scans top-level JSON files from `resources/playlists/` first and `data/playlists/` second, sorted within each root by `(filename.casefold(), filename)`. The first occurrence of a code wins; duplicate-code files are skipped with a warning naming both files, and startup warnings are buffered until the UI mounts so they become visible notifications instead of being dropped outside Dash callback context. This supersedes the 2026-07-05 proposal call that user-root files should win: the final rule is bundled-wins because bundled benchmark files carry rank data and share-code imports do not. New imports write atomically to `data/playlists/{sanitized name} [{code}].json`; importing an existing code is refused with a user-visible message naming the existing playlist. The `data/playlists/` root may be absent on clean checkouts and is created on first import. Legacy user imports under `resources/playlists/` are a clean break, not migrated; owners preview and remove ignored legacy files manually with `git clean -Xn resources/playlists` then `git clean -Xf resources/playlists`, re-importing anything still wanted by share code.

## 2026-04-27: Treat `total-play` As Metadata Only

Status: Accepted

Decision: Use `/user/scenario/total-play` only to hydrate or upsert scenario metadata such as `scenarioName -> leaderboardId`.

Why: The endpoint can lag behind current leaderboard scores and ranks. `/leaderboard/scores/global` is the authoritative source for current rank.

Consequences: Current-rank lookup should not trust score or rank data from `total-play`. The endpoint remains useful for cache initialization and metadata discovery.

## 2026-04-27: Keep KovaaK's API Details Behind `ScenarioRankInfo`

Status: Accepted

Decision: UI code consumes `ScenarioRankInfo` and should not know which KovaaK's endpoint produced the data.

Why: Endpoint details, fallback behavior, cache rules, and expected API failures belong in the service layer. This keeps Dash callbacks focused on rendering.

Consequences: Expected KovaaK's API/domain failures should become `ScenarioRankInfo(status=UNKNOWN, error_message=...)` in `api_service.py`. UI code can render `RANKED`, `UNRANKED`, or `UNKNOWN` without duplicating endpoint logic.

## 2026-04-27: Prefer Steam ID Matching When Configured

Status: Accepted

Decision: When `steam_id` is configured, prefer it for leaderboard identity matching. If Steam ID matching fails but exact username matching succeeds, keep the rank result and surface a warning.

Why: `usernameSearch` can return partial matches. Steam ID is the strongest identity check, but a mistyped Steam ID should not hide otherwise valid exact-username rank data.

Consequences: The warning is transient and derived from current config each time rank info is returned. It should not be persisted in rank cache.

## 2026-04-27: Make Leaderboard Total Enrichment Best-Effort

Status: Accepted

Decision: Leaderboard total lookup should never invalidate a valid rank or unranked result.

Why: Total players and percentile are enrichment data. If total lookup fails because of network errors, malformed responses, validation failures, or cache I/O issues, showing the valid rank alone is better than falling back to `N/A`.

Consequences: `_with_leaderboard_total()` catches expected total-enrichment failures, logs them, and returns the original `ScenarioRankInfo`.

## 2026-04-29: Cache Leaderboard Totals For One Week

Status: Accepted

Decision: `leaderboard_total_cache_ttl_hours` defaults to `168`, matching `scenario_rank_cache_ttl_hours`.

Why: Leaderboard total player counts are expected to increase slowly. For large leaderboards, a mildly stale total count changes displayed percentile by less than the UI's two-decimal precision in most cases, while avoiding daily cold-cache total fetches across every playlist scenario.

Consequences: Total-count freshness remains configurable. If users notice stale total counts causing misleading displays, revisit the TTL or add a targeted refresh flow.

## 2026-04-27: Use The Midpoint Percentile Formula

Status: Accepted

Decision: Derive percentile with:

```python
percentile = ((total_players - rank + 0.5) / total_players) * 100
```

Why: This matches the KovaaK's-style percentile behavior we agreed to use.

Consequences: Percentile is display-only metadata derived when rank info is returned. It is not stored in rank cache. No tiny-leaderboard special casing is planned, so `rank 1 of 1` displays `50.00%`.

## 2026-04-27: Keep KovaaK's API Findings In A Dedicated Notes File

Status: Accepted

Decision: Track KovaaK's endpoint behavior, relied-upon fields, and discovered quirks in `docs/kovaaks_api_notes.md`.

Why: We are probing unofficial or lightly documented API behavior across multiple milestones. Keeping API lore in one living document helps future agents avoid rediscovering endpoint semantics from chat history.

Consequences: When new endpoint behavior or failure modes are discovered, update the notes file and add regression coverage when practical.

## 2026-04-28: Retry KovaaK's GET Transient Failures Once

Status: Superseded in part by the 2026-07-13 timeout/read-timeout decision — `requests.Timeout` is no longer in the retry set (read timeouts fail immediately); the `429`/`Retry-After` policy and the `requests.ConnectionError` retry stand

Decision: KovaaK's GET requests should retry exactly once on HTTP `429 Too Many Requests`, `requests.Timeout`, and `requests.ConnectionError`. `429` retries should honor `Retry-After` when present and cap the wait.

Why: Playlist scenario overview can create bursty cold-cache rank and total lookups. KovaaK's can also occasionally exceed the current read timeout for one row while adjacent requests succeed. A single bounded retry handles transient failures without turning the retry helper into a full scheduler or hiding unrelated failures.

Consequences: Retry remains GET-only. Non-429 HTTP failures and unexpected exceptions continue through the existing service-layer error handling. Recovered retries are logged but are not user-facing notifications.

## 2026-04-29: Drive Playlist Table Loads From Mounted Route State

Status: Accepted

Decision: Playlist scenario table loads should be driven by state created in the mounted `/playlists/<playlist_code>` layout, not directly by selector changes or URL-change callbacks.

Why: When the playlist selector changes the route, Dash Pages can briefly have the old page instance responding to the URL update before the new route layout finishes mounting. If the expensive table load listens directly to that navigation event, one user selection can trigger duplicate cache/API loads.

Consequences: Keep the selector callback navigation-only. The route layout should publish the resolved playlist code through a lightweight mounted component, currently `dcc.Store(id="playlist-scenarios-code")`, and the table-loading callback should use that mounted state as its trigger.

## 2026-04-29: Use Controlled AG Grid JS For Null-Aware Sorting

Status: Accepted

Decision: Playlist scenario AG Grid tables may use repo-owned JavaScript comparators from `assets/dashAgGridFunctions.js` with `dangerously_allow_code=True` when AG Grid requires client-side sort behavior that Python cannot provide directly.

Why: AG Grid sorting runs in the browser. The playlist table needs `NULLS LAST` behavior for rank, total, and percentile columns so unknown values do not sort ahead of real numeric values.

Consequences: Only reference controlled functions committed under `assets/`. Do not generate JavaScript strings from user input. If additional custom grid behavior is needed, prefer adding named functions to `assets/dashAgGridFunctions.js` rather than embedding ad hoc code in page callbacks.

## 2026-04-29: Use Thread-Local Sessions For KovaaK's GET Requests

Status: Accepted

Decision: KovaaK's GET requests should go through a reusable `requests.Session` scoped to the current worker thread.

Why: Cold-cache playlist table loads make many small HTTPS calls. Reusing sessions lets Requests keep connections alive and avoid repeated TCP/TLS setup. Keeping sessions thread-local avoids sharing one mutable `Session` object across the playlist table's concurrent worker threads.

Consequences: `_get_with_retry()` should call the thread-local session wrapper instead of `requests.get(...)` directly. Tests should patch that wrapper when faking HTTP responses. If we later add async HTTP or a centralized rate limiter, revisit this decision.

## 2026-06-21: Keep The Hand-Rolled GET Retry; Defer urllib3 `Retry` Migration

Status: Accepted

Decision: Keep the hand-rolled retry helpers in `source/kovaaks/api_service.py`
(`_get_with_retry`, `_retry_after_seconds`) instead of mounting a urllib3
`HTTPAdapter(max_retries=Retry(...))` on the thread-local sessions. Reconsider
only when requirements grow past one retry (exponential backoff with jitter, a
broader `status_forcelist` such as 503, separate connect/read budgets).

Why: The happy path maps cleanly onto urllib3 `Retry`, but a faithful migration
is not a clean delete. It would lose the 0.5s default delay on a 429 without
`Retry-After` (urllib3 sleeps 0s on the first retry), change the exhaustion
exception types the tests assert on (`HTTPError`/bare timeout become
`RetryError`/wrapped `ConnectionError`), downgrade recovered-retry logging from
WARNING to a DEBUG line on urllib3's logger, and still require a wrapper for the
per-request timeout default. Preserving the 5s `Retry-After` cap needs
`retry_after_max`, which requires pinning `urllib3>=2.6` — currently only a
transitive dependency. Net-neutral complexity plus a full test rewrite does not
clear the bar for replacing working, ratified code.

Consequences: The retry layer stays per-request and hand-rolled; the score-aware
rank refresh loop sits on top of it and relies on its contract (one inner retry,
bounded sleeps). If migrating later, the minimal-drift recipe is: one
module-level `Retry(total=1, status=1, connect=1, read=1, status_forcelist=[429],
allowed_methods={"GET"}, retry_after_max=5, raise_on_status=False)` mounted on
both schemes of each thread-local session, a thin wrapper retained for the
timeout default and WARNING log, and an explicit `urllib3>=2.6` floor. The full
analysis lives in git history as `docs/api_retry_urllib3_migration_proposal.md`.

## 2026-07-03: Playlists Routes Are Stable; The Bare-Route Selector Is Transitional

Status: Accepted

Decision: The playlists feature owns two routes: `/playlists` (navbar
destination) and `/playlists/{playlistCode}` (per-playlist scenario table).
The per-playlist route and its `playlistCode` URL identity are stable
contracts. The current content of the bare route — a selector dropdown plus an
empty prompt — is transitional scaffolding from milestone 1: when the
playlist-level overview (roadmap milestone 2) ships, the overview replaces the
bare-route content, overview rows navigate to `/playlists/{playlistCode}`, and
the selector dropdowns are removed from both pages.

Why: A single canonical landing route keeps the navbar destination stable
across milestones, and the human-readable playlist code is already user-facing
via the import flow. The overview is a strictly richer playlist picker than a
name-only dropdown (it surfaces last-played, aggregate percentile, and similar
metadata), so keeping the selector after it ships would be scaffolding
outliving its purpose. Distilled from the milestone-1 playlist scenarios
proposal (shipped in PRs #12, #15, #16).

Consequences: Keep the selector wiring separate enough that its removal is a
clean delete, not a refactor. Post-overview, switching playlists means
navigating back to `/playlists` and clicking a row, so the overview needs
visible row-click affordances (cursor, hover tint, full-row target). Do not
bake the selector into the per-playlist page in a way that blocks removal.

## 2026-06-20: Reference dash-ag-grid Grid Functions By Bare Name

Status: Accepted

Decision: In dash-ag-grid `{"function": "..."}` strings (`valueFormatter`, `tooltipValueGetter`, `comparator`, `valueGetter`, etc.), reference functions from the `assets/dashAgGridFunctions.js` registry by their **bare name** — `relativeTime(params.value, "Never")`, `nullsLastComparator` — never with a `dagfuncs.` prefix.

Why: dash-ag-grid (35.2.0) does not run these strings as a browser-global eval. It parses each to an AST and evaluates it against a constructed scope that spreads the contents of `window.dashAgGridFunctions` in as bare names (alongside `params`, `agGrid`, `d3`, `dash_clientside`). There is no `dagfuncs` object in that scope — the identifier never appears in the dash-ag-grid bundle — so `dagfuncs.X(...)` resolves to undefined and the expression **silently fails**: the cell renders the raw field value, or the comparator falls back to AG Grid's default sort, with no console error. The `assets/` file's `var dagfuncs = (window.dashAgGridFunctions = ...)` alias is only for *defining* the registry functions.

Consequences: Plain Dash `clientside_callback`s are different — they run in real browser global scope, so there use the full `window.dashAgGridFunctions.X(...)` path (e.g. the home page's "Last played" relative-time callback). This decision corrected two silent bugs: the grid "Last Played" `valueFormatter`/`tooltipValueGetter` (PR #17) and the `NULLS LAST` comparator on all sortable columns (PR #19), the latter broken since the 2026-04-29 "Use Controlled AG Grid JS For Null-Aware Sorting" entry. Verified by decompiling the installed bundle and by a live browser test.

## 2026-06-20: Interim Merge Bar Until Lint/Format Cleanup

Status: Superseded by the 2026-07-03 ruff-only tooling decision

Decision: Until the lint/format cleanup lands, the merge bar is: `uv run pytest` and `uv run mypy source` must be **green**, and `uv run pylint source` plus `black --check`/`isort --check` must **not regress versus `main`** (no new findings in the files a change touches). The absolute CLAUDE.md bar (pylint `fail-under = 10`, black/isort clean) is the target, not yet current reality.

Why: As of 2026-06-20 `main` is green on pytest and mypy (the latter since PR #18 deleted a dead `mypy.ini` that was shadowing `[tool.mypy]`), but not on pylint (9.22/10 — missing docstrings, TODOs, broad-except, too-many-*), `black --check` (3 files), or `isort --check` (2 files). Those are pre-existing and reproduce on the committed LF blobs (not a CRLF flap). There is no CI, so the gates are an honour-system check; blocking feature PRs on an absolute bar `main` itself cannot meet is incoherent, while a baseline-comparison bar keeps shipping unblocked without growing the debt.

Consequences: Reviewers compare pylint/black/isort output for the changed files against the `main` baseline rather than requiring a green absolute run; pytest and mypy are hard green gates. The remaining pylint cleanup is deferred tech debt (~115 findings on `main`, dominated by missing docstrings, plus fix-or-disable calls on `too-many-*`, `broad-except`, `fixme`, and similar); the `black`/`isort` deltas are a few files. Remove this interim framing once pylint and the formatters are green on `main`.

## 2026-07-03: Consolidate Formatting And Linting On Ruff

Status: Accepted

Decision: Use ruff as the sole formatter and linter, with mypy and pytest retained as separate gates. Ruff formats at 88 characters and enforces a 120-character hard ceiling through `E501`. Lint `source/` and `tests/`, but exclude `scripts/`; tests are exempt from missing-docstring, design-metric, and unused-argument rules. Require docstrings in `source/`, leave deliberate TODOs unenforced, and keep preview mode disabled. Local pre-commit hooks enforce ruff check and format; mypy, pytest, and the inexpensive CPython `compileall` syntax check remain manual validation because the project has no CI.

Why: The previous black, isort, and pylint configuration described conflicting line lengths, duplicated responsibilities, and could not meet its own score gate while intentional TODOs remained. One pinned ruff configuration provides a green, deterministic format/lint bar without a score or `fail-under`, while preserving the established 88-character formatting and keeping tests and replacement-bound scripts free from low-value lint churn.

Consequences: Pylint, black, and isort are no longer direct dependencies or configured tools. Black and isort remain transitive lockfile dependencies of `datamodel-code-generator`. Accepted enforcement losses are: no ruff equivalents for duplicate-code, too-many-instance-attributes, or too-many-lines; preview-only rules for unspecified-encoding, too-many-locals, too-many-positional-arguments, too-many-boolean-expressions, and too-many-nested-blocks remain disabled; and `no-else-return` is outside the selected rule families. The two current encoding omissions and the current unnecessary `else` were fixed once during migration, but are not ongoing gates. Keep the pre-commit ruff revision synchronized with the ruff version in `uv.lock`, and add CI or a single-command task runner separately.

## 2026-07-03: CI Runs The Merge Bar On Every PR

Status: Superseded in part by the 2026-07-06 cross-repo Python v2 tooling decision

Decision: A single GitHub Actions `gates` job runs the repository merge bar on
every pull request and push to `main`: ruff format check, ruff lint, mypy,
CPython `compileall`, and pytest. It runs on `windows-latest`, validates the
lockfile with `uv sync --locked`, and executes each gate with
`uv run --no-sync`. Python and uv are pinned, action dependencies use immutable
full commit SHAs, the workflow token has read-only contents access, and
superseded runs on the same ref are cancelled.

Why: This fulfills the deferred CI consequence of the 2026-07-03 ruff
consolidation decision. An executable merge bar catches stale lockfiles,
formatting drift, type errors, syntax errors, and regressions consistently,
including on doc-only changes where the docs hygiene tests still matter.
Windows matches the supported development and runtime environment.

Consequences: `.github/workflows/gates.yml` is the canonical executable list of
gates. Local pre-handoff validation remains unchanged because it is the fastest
feedback path. A local single-command task runner remains optional rather than
part of this decision. After the workflow has established a short green
history, the repository owner should mark the `gates` check required on
`main`; branch protection is intentionally outside the workflow.

## 2026-07-06: Adopt The Cross-Repo Python V2 Tooling Spec

Status: Accepted

Supersedes: The workflow shape, command set, tool and runtime pin placement,
and concurrency behavior in the 2026-07-03 CI decision. Windows execution,
locked dependency sync, SHA-pinned actions, read-only contents permission, and
the broader local pre-handoff validation remain in force.

Decision: Use the canonical `tooling-spec: python-v2` workflow at
`.github/workflows/ci.yml`. Its matrix-backed `test (windows-latest)` job runs
`uv sync --locked`, ruff format, ruff lint, bare mypy, and bare pytest.
`pyproject.toml` owns the required uv version (`==0.11.26`), pytest discovery
and options, and mypy's `source/` scope. The workflow no longer overrides Git
line endings, cancels superseded runs, caches uv, pins Python or uv through
`setup-uv`, or runs `compileall`.

Why: The cross-repo spec keeps local and CI invocations aligned through project
configuration and gives repositories one recognizable CI shape. Moving the uv,
pytest, and mypy defaults into `pyproject.toml` makes the bare commands
authoritative in every environment instead of relying on workflow-only flags.

Consequences: Local pre-handoff validation still includes `compileall`, while
CI has four named checks inside the single Windows matrix job. CI resolves a
compatible interpreter from `requires-python = ">=3.14"`; this migration does
not add a `.python-version` pin. The required branch-protection check changes
from `gates` to `test (windows-latest)` and must be updated by the repository
owner at merge time. Add a minimal `.gitattributes` only if a runner actually
reports line-ending format drift; the migration's first CI run did not.

## 2026-06-21: Relative ("Humanized") Last-Played Timestamps

Status: Superseded in part by the 2026-06-30 home empty-state decision and, for the exact absolute-string format (`%Y-%m-%d %I:%M:%S %p`), by the 2026-07-11 humanized absolute-format decision

Decision: "Last played" renders as a relative, humanized string ("5 minutes ago") in both the home Scenario Stats block and the playlists grid, with the exact timestamp shown on hover (`%Y-%m-%d %I:%M:%S %p`). Formatting lives in a single shared pair of pure JS helpers (`relativeTime`/`absoluteTime`) in `assets/dashAgGridFunctions.js`. Rules: a single rounded unit, never compound — just now (≤60s, including ≤0 / future) → N minutes → N hours → N days → N months → N years, with months/years calendar-based and a `max(0, …)` clamp (no `Intl` dependency, no "over"/"about" prefix). The value stays relative all the way (no absolute-date cutover) because it is a staleness gauge, not a reference date. Timestamps are epoch **seconds** end-to-end (the JS multiplies by 1000). Sentinels: "Never" on the grid (in a playlist but never played), "N/A" on home (no selection / not in DB) — never blank. The home value self-updates via a dedicated 30s `dcc.Interval` (decoupled from `polling_interval`); the grid live-ticks via a dedicated interval + `refreshCells({force: true, columns: ['last_played_sort']})`.

Why: A relative string answers "how stale is this?" directly, while the tooltip preserves the exact instant. Hand-rolled formatting (~30 lines) is simpler than `Intl` for an English-only app and fully controls the edges; calendar-based month/year math matches what a human reading two dates would say and avoids day-division boundary fudges.

Consequences: Shipped in PRs #17/#19 (Phase 1: shared helpers, home self-update, grid render-on-load) and #23 (Phase 2: grid live-ticking). Exact-timestamp access is hover-only (tooltip), consciously waived for this local single-user app. For how grid colDef `{"function": ...}` strings invoke these helpers, see the 2026-06-20 "Reference dash-ag-grid Grid Functions By Bare Name" entry. This entry distills and replaces `docs/relative_timestamp_proposal.md`, now deleted.

## 2026-06-30: Model Home Last-Played Empty States Explicitly

Status: Superseded in part, for the exact absolute-string format (`%Y-%m-%d %I:%M:%S %p`), by the 2026-07-11 humanized absolute-format decision

Supersedes: The home sentinel and hover-only tooltip interaction in the 2026-06-21 relative timestamp decision. The playlist-grid behavior and shared timestamp formatting rules remain unchanged.

Decision: Home Scenario Stats distinguishes three "Last played" states: no scenario selected renders `—`; a selected scenario with no local play data renders `Never`; and a selected scenario with play data renders the relative timestamp. Only a real timestamp receives the dotted underline and `cursor: help` affordance. Its exact local timestamp (`%Y-%m-%d %I:%M:%S %p`) is available by hover, keyboard focus, or touch. Empty states are not focusable and disable the tooltip entirely.

Why: `—` communicates an unselected field without implying missing or failed data, while `Never` communicates a known selected scenario with no recorded plays. Showing the affordance only when more information exists keeps the interaction honest and avoids a tooltip that merely repeats an empty-state value.

Consequences: The home callback owns the empty-state value and tooltip affordance alongside the raw timestamp. The clientside relative-time callback continues to own the live-updating visible timestamp. A selected scenario missing from the local database is treated as having no local play data; temporary loading or error states must not be mapped to `Never`.

## 2026-07-01: Keep Scenario Rank Consistent With Score-Aware Refreshes

Status: Accepted

Supersedes: The `ThreadPoolExecutor(max_workers=2)` high-score refresh and the
decision not to provide manual rank refresh in the original scenario rank
proposal (since distilled into this log and deleted).

Decision: After a local high score, run a bounded score-aware refresh using a
daemon `threading.Timer` chain with delays of 2, 4, 8, 16, and 32 seconds. Accept
the leaderboard as caught up only when its score reaches the two-decimal floor of
the local score. Route every automatic rank-cache write through one process-locked
monotonic writer so a lower score or transient `UNRANKED` result cannot replace a
known better value. The home rank widget passively re-reads rank and total caches
on its existing interval without making network calls, including when those cache
files are older than their normal TTLs. A user-clicked Refresh performs one
authoritative fetch and may deliberately write a lower score or `UNRANKED` result.

Why: KovaaK's leaderboard updates are eventually consistent, so the old single
post-PB fetch could persist lagging data for the week-long cache TTL. Timer
attempts keep delayed work off a bounded executor, centralized write arbitration
prevents loop/read races, and the cache-only UI poll surfaces successful background
writes within about one second. Automatic rechecks after the bounded window would
hammer permanently divergent offline/server-down scores; explicit Refresh gives
the user a bounded escape hatch instead.

Consequences: Automatic rank displays move forward by score and never flicker from
a known rank to `UNRANKED`; explicit Refresh is board-authoritative and can move
backward after a leaderboard reset. Interval ticks resolve only cached leaderboard
IDs, read rank and total files independent of TTL, emit no repeated warning/error
toasts, and make zero KovaaK's requests. A refresh loop that exhausts leaves the
previous cache untouched and asks the user to click Refresh. The retry schedule is
a code constant, not configuration.

## 2026-07-03: Import Benchmarks From Evxl And KovaaK's

Status: Accepted

Decision: The benchmark importer uses Evxl to resolve playlist names and codes,
and KovaaK's to fetch benchmark rank thresholds. In project terminology, a
*playlist* is a bare scenario list without rank data; a *benchmark* is a
playlist plus rank thresholds and colors. Generated benchmark JSON carries a
`generated_from` provenance stamp containing the Evxl sharecode, KovaaK's
benchmark ID, ordered rank-color pairs, generation timestamp, and generator
name.

Why: KovaaK's playlist search cannot resolve every known sharecode, while Evxl's
exact-code endpoint can; Evxl does not expose the per-scenario rank thresholds,
so KovaaK's remains authoritative for those values. The terminology distinguishes
the app's playlist import from the richer files produced by the importer.
Provenance makes the upstream inputs inspectable and allows generated files to be
checked for stale or mismatched benchmark metadata.

Consequences: Keep Evxl-specific resolution and snapshot handling in
`scripts/benchmark_importer/` unless an app-side feature explicitly adopts that
dependency. Preserve rank-color order when comparing provenance because colors
pair positionally with KovaaK's thresholds. Conflicting duplicate Evxl
sharecodes must be skipped and reported rather than resolved first-wins because
a missing benchmark is visible and recoverable, while silently pairing the wrong
rank thresholds is not. KovaaK's threshold changes under an unchanged benchmark
ID remain invisible to provenance checks and require an explicit forced refresh.

## 2026-07-06: Coalesce Pending Home Run Events

Status: Accepted

Decision: Home's `check_for_new_data` callback is the sole consumer of the
process-wide run-event deque. On each invocation it drains all pending messages,
lands on the most recently played scenario when automatic scenario switching is
enabled, and publishes a JSON-safe `run-events` summary for that scenario.
`generate_graph` rebuilds from the already-current in-memory stores and creates
toasts from that summary only when `run-events` triggered it. A single run keeps
the existing per-run toast behavior; a backlog produces one scenario-named
summary based on the latest matching run. The watchdog must successfully load a
run into the stores before enqueueing its message. The supported usage model is
one active Home tab; extra tabs remain crash-safe but unsynchronized.

Why: Home's interval does not run while the page is unmounted, so queued events
previously replayed one tick at a time on return. That rebuilt the same final
plot repeatedly, moved the scenario dropdown through stale history, and emitted
stale toast batches. Enqueue-before-load also allowed a consumer to rebuild
before the corresponding run was queryable, or to toast a run whose second parse
failed.

Consequences: A backlog is consumed in one tick, produces at most one dropdown
change and one toast batch, and cannot expose a message without queryable run
data. Mixed-scenario counts describe only the landing scenario. Nonmatching
events are discarded when automatic switching is off, preserving the previous
policy without wasting ticks. Coherent multi-tab delivery would require a
broadcast or push transport and remains outside this local single-user design.

## 2026-07-06: One Word Per Concept In Leaderboard Verbiage

Status: Accepted

Decision: "Rank" was used for both benchmark tiers (Bronze/Silver/..., Rank
Overlay) and leaderboard placement (Home "Rank:", grid "Current Rank"),
mirroring a split in the ecosystem (KovaaK's leaderboards: rank = position;
Voltaic/Aimlabs: rank = tier). In user-facing text, **Rank** means tier only,
**Position** means leaderboard placement ("Total Players" for board size), and
**PB** prefixes stats of the personal-best run (PB Score, PB cm/360, PB
Accuracy). "Unranked" is retained as KovaaK's own term for having no leaderboard
entry.

Consequences: Labels, plot annotations, and toasts follow the invariant.
Internal identifiers, component ids, and row field names keep their old names
because this is a label-only rename. New UI text must not reintroduce "rank" for
leaderboard placement.

## 2026-07-06: Let The Playlist Scenarios Grid Own Vertical Scrolling

Status: Accepted

Decision: Bound the playlist scenarios page to the Mantine AppShell content
viewport and let the AG Grid use its normal layout with an internal vertical
scrollbar. The page Stack and Dash Loading wrappers form a flex column, and the
grid fills the remaining space with a 300px minimum height. Keep the existing
content-based column sizing and capped flexible Scenario column.

Why: `domLayout: autoHeight` expanded the grid to every row, so the document
scrolled and carried the column headers out of view on large playlists. A
bounded grid keeps the headers visible while the user sorts and scans scenarios
deep in the playlist, and restores row virtualization.

Consequences: Short playlists show empty grid body below their final row instead
of collapsing the grid. Very short windows may still scroll the page to preserve
the 300px usable minimum. The layout tracks AppShell header and padding variables
instead of duplicating their pixel values.

## 2026-07-11: Move The API Cache Under data/cache/

Status: Accepted

Decision: Relocate the runtime API cache root from `cache/` to `data/cache/`
as a plain path change, with no in-app compatibility migration. An existing
`cache/` directory is moved by hand after the change lands.

Why: The 2026-06-22 entry grouped user/runtime state under `data/` but
deferred the cache to a dedicated compatibility migration. The app currently
has exactly one user and the cache is fully regenerable from the API, so
migration code would outlive its single use; a one-time manual move (or just
letting the cache rebuild) covers it.

Consequences: All runtime state — logs, preferences, user playlists, and the
cache — lives under one ignored `data/` root. A legacy `cache/` root left in
place is silently ignored; `.gitignore` keeps its entry so pre-move checkouts
stay clean. Revisit an in-app migration only if the app gains users beyond
its author.

## 2026-07-15: Stream Playlist Positions With Generation-Scoped Progressive Fill

Status: Accepted

Supersedes: The blocking all-scenarios load and Dash Loading wrapper for the
per-playlist scenario grid. The bounded, grid-owned scrolling decision from
2026-07-06 remains in force.

Decision: Opening `/playlists/<code>` has two phases. Phase 1 paints every row
from local stats plus TTL-ignored rank caches, with explicit per-cell pending
flags for unresolved Position, Total Players, and Percentile values. Phase 2
hydrates leaderboard IDs once, then runs the normal cache/network lookup path
through the existing four-worker fan-out in one daemon-thread fill. Workers
stream complete row dictionaries into a lock-guarded in-memory registry keyed
by a per-open generation token. A one-second, enable-only interval drains those
rows through AG Grid update transactions; row identity is
`generation_token:playlist_order`, so a superseded response cannot update the
current grid.

Starting a fill synchronously cancels every other live generation. Completion
and cancellation become bounded tombstones with final counters, a terminal
state, and an atomic consumed flag. The first terminal tick alone drains final
updates, rebuilds unresolved cancelled rows cache-only, settles the status, and
emits any aggregate completion toast; later ticks only reassert the settled
status. Consumed tombstones drop queued rows and finalization payloads, but stay
in the same eight-item retention set as unconsumed tombstones. Overflow evicts
consumed before unconsumed, oldest first within each class, and the cap is
enforced at every terminal transition.

Pending state is never inferred from null values: resolved `UNRANKED` Position
is valid with a null sort key. Completed/finalized rows clear all pending flags.
Outcomes are counted before row formatting as fresh, `UNKNOWN`, or structurally
`served_stale`; the transient stale marker is never written to the rank cache.
Completion uses the existing red/yellow/silent failure tiers without
per-scenario toast spam. The API coordination signal keeps two monotonic
timestamps: interactive rank activity includes cache hits, while network
success changes only after a real successful HTTP response.

Why: Cold or flaky playlist opens previously hid six locally available columns
behind minutes of blocking API work. Progressive fill makes the training table
useful immediately while preserving the existing cache freshness and lookup
semantics. Generation-scoped row IDs plus consumed tombstones close the races
created by navigation, two tabs, callback responses already in flight, and
DashProxy's spurious initial callback behavior without adding a persistent job
system.

Consequences: The grid no longer uses `dcc.Loading`; animated CSS placeholders
and a `done/total` status provide progress. Clean fills clear the status and stay
silent, degraded fills retain a compact summary, and cancelled fills settle as
interrupted with no cell left pending. The registry is process-local and
single-user: reloads start a new fill, a second tab cancels the first tab's
network work, and completed API calls still warm the normal atomic disk caches.
Shipped in PR #127.

## 2026-07-16: Keep Pre-Hydration States Honest

Status: Accepted

Decision: Empty-state copy renders only after the owning data callback resolves.
AG Grid layouts omit initial `rowData` so the built-in loading overlay owns the
hydration gap. Plot layouts use a transparent, annotation-free placeholder;
`generate_empty_plot` is reserved for resolved-empty results.

Consequences: Initial page hydration stays visually neutral and never makes a
false no-data claim. Callbacks that resolve to empty grid rows or empty figures
continue to show their explicit empty-state guidance.

## 2026-07-17: Absorb Poll-Tick Bursts With Threads, Not Visibility Gating

Status: Accepted

Decision: Waitress runs with 8 worker threads (PR #116) as the sole fix for
poll-tick pressure. The demand-side alternative — pausing Home's
`interval-component` while the tab is hidden (Page Visibility API) — stays
unbuilt; its pre-approved design is parked as a kickoff prompt in
`ignore/prompts/icebox/` for reactivation if the symptom returns.

Why: Every Home polling tick (1 s default) fires three callback POSTs at once
(`check_for_new_data`, `flush_background_notifications`, and the cache-only
branch of `get_scenario_rank`). Against Waitress's default 4 threads, that
burst plus one thread held by a slow KovaaK's fetch (slow spells reach ~28 s)
left zero headroom, and a single idle tab produced task-queue-depth warnings.
Raising supply to 8 threads was deliberately tried first as the minimal fix,
with visibility-gated polling queued as the contingent next step; four days of
post-merge logs showed zero warnings, so the contingency never fired. Push
delivery (WebSocket/SSE) was also rejected: this is a single-user local app,
and with the warnings gone the polling cost argument for push collapses.

Consequences: An idle-but-hidden Home tab still polls (~3 POSTs/s of cheap
cache-only work) — accepted chatter, not a defect. If queue-depth warnings
reappear, reach for the iceboxed visibility-gating prompt (gate on
`document.hidden`, never window focus: an unfocused-but-visible window on a
secondary monitor must keep polling) before raising threads further.

## 2026-07-18: Leaderboard Mapping Reads Through an mtime-Revalidated In-Memory Mirror

Status: Accepted

Decision: `get_cached_leaderboard_id` serves lookups from a module-level parsed
copy of `scenario_name_to_leaderboard_id.json`, revalidated on every read by
comparing the file's identity — `(path, st_mtime_ns, st_size)` from one
`stat()` call — against the signature recorded when the copy was parsed. In
cache-policy terms: read-through population, write-around writes
(`save_leaderboard_id` still writes only the file), revalidate-on-read
coherence. Disk remains the source of truth; memory is a verified mirror. The
check-and-load runs under `_CACHE_IO_LOCK`, which `_write_json` also holds, so
lookups cannot interleave with in-process writes.

Why: The mapping file is a whole-store key-value file (~140KB, ~1,000 entries,
append-mostly immutable facts) consulted once per rank lookup, so every point
lookup paid a full parse. The playlist overview's "Show hidden" toggle made
this visible: rebuilding all 217 rows performed 1,062 cache-only rank lookups
and re-parsed the same file 1,062 times (~150MB of JSON) — measured at 0.77s
per toggle, and again on every 1s warmup-interval repaint. The mtime cache
alone cut the build to 0.19s; per-build memoization alone reached only 0.44s
because playlist overlap is modest (1,062 lookups over 659 distinct scenarios,
1.61x), so the per-lookup parse, not duplication, was the dominant cost.

Alternatives considered: (a) a loading spinner — rejected: the row-build
callback is shared with the warmup interval and refresh-store bumps, so any
`dcc.Loading`/`running=` indicator flashes on every automated repaint, and it
decorates waste rather than removing it; (b) per-build memoization of rank
resolution in the overview service — deferred, not rejected: it would add
snapshot consistency (the R11 property scenario stats already have) and take
0.19s to 0.11s, but is no longer the headline fix; (c) write-through (updating
the in-memory copy in `save_leaderboard_id` instead of revalidating) —
rejected: it maintains coherence only for writes made through this process's
write path, and the cache conventions explicitly support external mutation
(deleting `data/cache/` mid-run, other processes); trusting memory
unconditionally would invert the source of truth. As a redundant addition on
top of revalidation it buys one ~1ms parse per rare write at the cost of a
three-way coherence invariant (file, dict, signature) in the write path;
(d) SQLite — unchanged from the 2026-06 cache-layer decision: indexed point
reads would dissolve this whole class of cost and subsume this fix, but the
migration stays parked behind its documented triggers (rank history,
multi-record queries, transactional guarantees).

Consequences: `api_service` is no longer fully stateless — this one file has
an in-memory mirror, with the invariant that every serve is preceded by a
fresh `stat()` proof. The signature includes the resolved path so tests that
repoint `CACHE_DIR` cannot alias a stale copy; `st_size` guards against
same-mtime rewrites on coarse-timestamp filesystems. Metadata revalidation
inherently cannot detect a rewrite that preserves both size and timestamp
(deliberate `os.utime` forgery after an in-place edit — the known limit of
every mtime-keyed cache, `.pyc` included). This is an accepted risk, not an
oversight: the PR #147 review asked for a bounded forced refresh and a
60-second re-parse backstop was briefly added, then removed at the
maintainer's direction — a periodic redundant reload with no intervening
write contradicts the cache's purpose (fast reads until the next write), no
realistic writer forges timestamps (atomic replace, editors, and restores
all shift mtime_ns or size), and the only actor who could is the single
user poisoning their own local cache. A content-hash key was also rejected:
it must read the whole file per check (~146ms vs ~27ms per toggle build for
`stat`), returning a third of the original cost to buy a guarantee only the
forgery scenario needs. A regression test pins the accepted behavior
(forged rewrite served until the next genuine write) so it reads as
deliberate. A missing mapping file no
longer logs a read-failure warning per lookup (the stat short-circuits the
read), and a malformed file warns once per file version instead of once per
lookup. All `resolve_leaderboard_id` callers (Home rank display, playlist
drill-in fill, warmup worker, watchdog rank-freshness timers) share the
parse-free path. The other cache files (per-scenario rank, totals) stay as
direct per-read files: small, per-key reads where mirroring would add
bookkeeping for little gain. Regression tests pin the single-parse property,
write-then-read invalidation, external rewrite, deletion, and malformed-file
tolerance.
