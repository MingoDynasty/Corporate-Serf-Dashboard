# Release, Install, and Update

Every push to the main branch that changes what an installed copy runs is
cut into a dated, immutable GitHub release by CI, with no human picking a
version number. Installing is one PowerShell command that brings its own
Python and package manager under one folder, asks nothing, and leaves a
desktop shortcut. Each launch checks for a newer release, stages it beside
the current one, and only records it as the install once it has actually
started and identified itself. A launch opens the dashboard in a browser
tab by default, and one config setting turns that off; either way the
console window prints the address it is serving. Removing the app is
deleting that folder and the shortcut.

Statements below describe what the scripts, the CI job, and the app do today
and link the [decision log](../decision_log.md) entries that set them;
rationale lives in those entries, not here. A statement with no link is an
implementation fact that no decision-log entry governs. Runtime structure is
mapped in [architecture.md](../architecture.md); the user-facing rationale is
in [product.md](../product.md); the operator's view is the README's
[Install](../../README.md#install),
[Manual install](../../README.md#manual-install), and
[Uninstall](../../README.md#uninstall) sections. The launcher's console
lines quoted here are plain console output, not app notifications.

## Cutting a release

- The `release` job in `.github/workflows/ci.yml` runs only on a push to
  `main`, with `needs: [test, release-gate]`, so a commit whose format, lint,
  type, or test gate failed never becomes a release
  ([2026-07-19](../decision_log.md#2026-07-19-releases-are-automated-calver-tags-cut-by-ci);
  the gates themselves:
  [2026-07-03](../decision_log.md#2026-07-03-ci-runs-the-merge-bar-on-every-pr),
  [2026-07-06](../decision_log.md#2026-07-06-adopt-the-cross-repo-python-v2-tooling-spec)).
  The job runs on Linux so `git archive` ships LF blobs. `scripts/**`,
  including `release_job.py`, is outside the lint and type gates and is
  covered by its unit tests only
  ([tech_debt.md](../tech_debt.md#scripts-is-exempt-from-the-lint-and-type-gates)).
- `release-gate` diffs the whole pushed range (`--no-renames`) and asks
  `should_release`. A path is release-worthy unless it ends in `.md`, is
  `.gitignore` or `.pre-commit-config.yaml`, or starts with `docs/`,
  `tests/`, `.github/`, or `.idea/`; one release-worthy path releases the
  push, and an empty or unknowable range (new ref, force push, pruned base)
  releases conservatively
  ([2026-07-19](../decision_log.md#2026-07-19-releases-are-automated-calver-tags-cut-by-ci);
  `.idea/`:
  [2026-08-08](../decision_log.md#2026-08-08-pycharm-config-stays-tracked-and-its-upgrade-churn-is-committed-once)).
- Tags are `vYYYY.MM.DD` in UTC; same-day repeats take `.N`, counting from
  the highest serial already used. A rerun reuses a tag already pointing at
  `HEAD`, and a tag that exists but points elsewhere fails the job
  ([2026-07-19](../decision_log.md#2026-07-19-releases-are-automated-calver-tags-cut-by-ci)).
- Order is fixed: push the tag, build the assets, create (or resume) a
  **draft** release, attach assets with `--clobber`, validate, then publish.
  An already-published tag ends the job with nothing to do
  ([2026-07-19](../decision_log.md#2026-07-19-releases-and-their-assets-are-immutable)).
- Releases serialize through the `release` concurrency group (`queue: max`).
  At publish time the job scans every published release and passes
  `--latest=false` when any of them descends from its own commit; after
  claiming Latest it asserts `releases/latest` resolves to its tag
  ([2026-07-19](../decision_log.md#2026-07-19-releases-are-automated-calver-tags-cut-by-ci)).
- Assets are exactly two: `Corporate-Serf-Dashboard-<tag>.zip`, built by
  `git archive` with the prefix `Corporate-Serf-Dashboard-<tag>/`, and
  `release.json` with the frozen v1 fields `schema_version`, `tag`, `sha`,
  `commit_date`, `uv_version`, `python_version`, `source_asset`. `uv_version`
  is read from `tool.uv.required-version` in `pyproject.toml`, which must be
  an exact `==` pin, and `python_version` from `.python-version`
  ([2026-07-19](../decision_log.md#2026-07-19-releases-are-automated-calver-tags-cut-by-ci),
  [2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).
- `version.txt` carries `sha: $Format:%H$` and `commit-date: $Format:%cs$`
  under an `export-subst` attribute; `git archive` expands them, so the zip
  and GitHub's own source archive both carry the full SHA and commit date
  ([2026-07-19](../decision_log.md#2026-07-19-build-identity-comes-from-the-manifest-corroborated-by-the-stamp)).
  The `test` job separately downloads GitHub's archive of the commit under
  test (the PR head on a pull request)
  and fails if the stamp is unexpanded or names another SHA.
- `validate_release` refuses the draft when: the archive is not named
  `source_asset_name(tag)`; it lacks `<prefix>version.txt`; the stamp is
  unexpanded or its SHA or date disagree with the released commit; any
  `REQUIRED_ARCHIVE_ENTRIES` path is missing (a directory entry counts only
  with a child path under it); any `EXCLUDED_ARCHIVE_TREES` prefix is
  present; or `release.json` differs from the payload the job intended, in
  any field or by an extra field
  ([2026-08-21](../decision_log.md#2026-08-21-release-integrity-rests-on-github-digests-and-an-enforced-archive-contract)).
- After validation the job reads the draft's assets back and requires
  exactly the zip and `release.json`, each in state `uploaded`, each with a
  GitHub digest equal to `sha256:` of the local file; a missing or `null`
  digest fails. No checksum file is published and the launcher verifies no
  hash
  ([2026-08-21](../decision_log.md#2026-08-21-release-integrity-rests-on-github-digests-and-an-enforced-archive-contract)).
- The release page opens with `.github/release-notes-header.md`, prepended
  to GitHub's generated notes. Its first line is "Immutable GitHub releases ·
  SHA-256 digests for the app zip and release.json"; it says "The launcher
  reads `release.json` automatically. Most people only need the app zip.",
  explains `Get-FileHash`, and ends "The "Source code" downloads are
  generated by GitHub rather than by this project's build. They carry no
  digest. Use the app zip."
  ([2026-08-21](../decision_log.md#2026-08-21-release-integrity-rests-on-github-digests-and-an-enforced-archive-contract)).

## The archive contract

- `.gitattributes` marks `/tests`, `/.idea`, and `/.github` `export-ignore`
  in the anchored directory form, so neither the release zip nor GitHub's
  source archive carries them, not even as empty directories. `docs/` ships
  ([2026-08-21](../decision_log.md#2026-08-21-release-integrity-rests-on-github-digests-and-an-enforced-archive-contract)).
- A fresh install therefore holds, under `versions/<tag>/`, every tracked
  path outside those three trees, agent tooling (`.claude/`, `AGENTS.md`,
  `CLAUDE.md`) included. The contract guarantees at least `source/`,
  `assets/`, `resources/`, `scripts/`, `docs/`, `install.ps1`,
  `pyproject.toml`, `uv.lock`, `.python-version`, `version.txt`,
  `example.toml`, `LICENSE`, and `README.md`; the staged `release.json` and
  the synced `.venv/` sit beside them
  ([2026-08-21](../decision_log.md#2026-08-21-release-integrity-rests-on-github-digests-and-an-enforced-archive-contract)).

## Installing

- The one-liner fetches `get.ps1` from `main`. The shim resolves
  `releases/latest`, fetches that tag's `install.ps1` to
  `%TEMP%\csd-install-<tag>.ps1`, and runs it in a child Windows PowerShell
  5.1 with `-ExecutionPolicy Bypass -File ... -LatestTag <tag>`, passing
  through any extra arguments. A 404 on either fetch prints "Corporate Serf
  Dashboard: the release is not ready yet -- try again shortly." and
  returns; the temp file is not deleted
  ([2026-07-19](../decision_log.md#2026-07-19-the-installer-brings-its-own-toolchain-app-locally)).
- `install.ps1` installs `-Tag` (pinned), else `-LatestTag` (unpinned), else
  the tag `releases/latest` resolves; with no release published it stops
  with "no release is published yet -- try again shortly." It then reads the
  tag's `release.json`, stops on a `schema_version` other than 1 ("Re-run
  the install one-liner to get the matching installer.") or a missing
  `tag`, `sha`, `commit_date`, `uv_version`, or `source_asset`
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).
- The install root defaults to `%LOCALAPPDATA%\CorporateSerfDashboard`
  (`-InstallRoot` overrides). The toolchain is app-local: uv at
  `uv\<uv_version>\uv.exe` via `UV_UNMANAGED_INSTALL` from
  `astral.sh/uv/<uv_version>/install.ps1`, CPython under `python\` via
  `UV_PYTHON_INSTALL_DIR` and `--managed-python`, the cache under
  `uv-cache\`. The uv version comes from the release, not the install
  ([2026-07-19](../decision_log.md#2026-07-19-the-installer-brings-its-own-toolchain-app-locally)).
- The zip is downloaded from the release's `source_asset`; a 404 falls back
  to `archive/refs/tags/<tag>.zip`. Exactly one top-level directory is
  required, its name discovered after extraction; the extracted
  `version.txt` must contain the release's `sha`; then it is moved to
  `versions\<tag>\`, `release.json` is written beside it byte-for-byte, and
  `uv sync --locked --no-dev --managed-python` runs there. A reinstall onto
  a tag whose directory already exists parks that directory under `tmp\`
  first and restores it if the replacement fails before its sync completes
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract),
  [2026-07-19](../decision_log.md#2026-07-19-build-identity-comes-from-the-manifest-corroborated-by-the-stamp)).
- Installs ask no questions. With no `config.toml` at the root, the installer
  writes one carrying only `port = 8050` under a comment header; an existing
  `config.toml` and `data/` are never touched ("Keeping the existing
  config.toml."). The file is then round-tripped through the installed
  app's own `load_config()` with `CSD_STATE_DIR` set to the root, and a
  failure stops the install before the manifest or shortcut are written
  or replaced
  ([2026-07-19](../decision_log.md#2026-07-19-the-installer-brings-its-own-toolchain-app-locally),
  port:
  [2026-07-19](../decision_log.md#2026-07-19-default-port-is-8050-not-8080)).
- `install.json` at the root carries `schema_version: 1`, `tag`, `sha`,
  `commit_date`, `update_policy` (`latest`, or `pinned` plus `pinned_tag`
  under `-Tag`). It never carries a uv or zip-prefix field. `config.toml`,
  `install.json`, and `launch.ps1` are written atomically (temp file, then
  `File.Replace` or move), UTF-8 without BOM, forward-slash paths; the
  `release.json` copy is exempt and kept verbatim
  ([2026-07-19](../decision_log.md#2026-07-19-powershell-writes-utf-8-without-bom-and-forward-slash-paths),
  [2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).
- `launch.ps1` at the root is a copy of the release's
  `scripts\launch_bootstrap.ps1`. The desktop shortcut "Corporate Serf
  Dashboard.lnk" targets `powershell.exe -NoProfile -ExecutionPolicy Bypass
  -File "<root>\launch.ps1"` with the root as working directory; it never
  points into a version directory
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).
- Closing lines: "Installed Corporate Serf Dashboard <tag>.", then under a
  pin "This install is PINNED to <tag> and will not auto-update." and
  "Re-run the installer without -Tag to return to automatic updates.", then
  'Launch it from the "Corporate Serf Dashboard" desktop shortcut.' and "To
  uninstall: delete the shortcut and the folder <root>". Uninstall is
  exactly that; nothing outside the root is modified except the shortcut
  and the `%TEMP%` copy of the installer
  ([2026-07-19](../decision_log.md#2026-07-19-the-installer-brings-its-own-toolchain-app-locally)).
- All scripts target Windows PowerShell 5.1 and are committed BOM-free;
  the bootstrap must carry a `# csd-bootstrap-version: N` marker
  ([2026-07-19](../decision_log.md#2026-07-19-powershell-writes-utf-8-without-bom-and-forward-slash-paths)).

## Starting

- `launch.ps1` reads `install.json`, selects `pinned_tag` under a `pinned`
  policy and `tag` otherwise, and runs
  `versions\<tag>\scripts\launcher.ps1 -InstallRoot <root>`, exiting with
  its code. An unreadable manifest or missing launcher prints
  `ERROR: ...`, the reinstall one-liner, and waits on "Press Enter to close"
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).
- The launcher holds a named mutex `Local\CorporateSerfDashboard-<hash of
  root>` for its own and the app's lifetime. A second launch exits 0 without
  updating or touching the manifest
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).
  It opens the browser only when `open_browser_on_launch` is on, printing
  "Corporate Serf Dashboard is already running; opening it in the browser.";
  with the setting off it prints "Corporate Serf Dashboard is already running
  at http://<browser>:<port>/." and opens nothing. This branch prints no
  "Dashboard running at" line and does not wait, so its console window closes
  at once
  ([2026-09-04](../decision_log.md#2026-09-04-the-launchers-browser-open-is-a-config-knob-tab-reuse-is-not-achievable)).
- `Get-ConfiguredEndpoint` asks the selected version's own `load_config()`
  for `port`, `host`, and `open_browser_on_launch`, with `CSD_STATE_DIR` set
  to the root; it takes the last stdout line, requires exactly three
  whitespace-separated fields, and reads the third as the flag when it is the
  literal `True`. Any failure yields `8050`, `127.0.0.1`, and open. Two
  properties keep 5.1, the shell the desktop shortcut runs, from making every
  launch a failure: the snippet it runs as `python -c` carries no double
  quote, because 5.1 drops the double quotes inside a native command's
  argument; and the capture runs under a function-local
  `$ErrorActionPreference = 'Continue'`, because under `Stop` 5.1 turns that
  command's first redirected stderr line into a terminating error, which the
  loader's own unknown-key warning would trigger
  ([2026-09-04](../decision_log.md#2026-09-04-the-launchers-browser-open-is-a-config-knob-tab-reuse-is-not-achievable)).
- `Get-ProbeAddress` maps `0.0.0.0` to `127.0.0.1`, `::` to `[::1]`, and any
  other host to its literal (IPv6 bracketed). `Get-BrowserAddress` returns
  `localhost` only for the default host `127.0.0.1` and the probe address
  otherwise
  ([2026-08-09](../decision_log.md#2026-08-09-human-facing-urls-say-localhost-machine-probes-stay-on-127001),
  [2026-08-14](../decision_log.md#2026-08-14-the-listen-address-is-configurable-loopback-by-default)).
- `Start-AppVersion` runs `versions\<tag>\.venv\Scripts\python.exe
  source/app.py` with the version directory as working directory,
  `CSD_STATE_DIR` set to the root and `CSD_LAUNCH_TOKEN` set to a fresh
  GUID, stdout and stderr redirected to `data\logs\launcher-app-stdout.log`
  and `launcher-app-stderr.log`. No uv runs on a normal start
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).
- `/health` returns JSON `tag`, `sha`, `commit_date`, `source` from
  `get_build_info()` plus `launch_token` echoed from `CSD_LAUNCH_TOKEN`,
  unauthenticated, on whatever `host` the app binds.
- `Wait-AppReady` polls `http://<probe>:<port>/health` with a 2 s request
  timeout every 0.5 s for up to `$HealthTimeoutSec` = 120 s, and returns
  `ready` only when the child is still alive and the response's `sha`
  equals the expected full SHA and `launch_token` equals the token; the tag
  is not checked. A child exit returns `exited` at the next loop check; the
  ceiling returns `timeout`
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract),
  [2026-08-21](../decision_log.md#2026-08-21-the-launcher-narrates-a-slow-start-and-keeps-its-120-second-ceiling)).
- Heartbeat: nothing is printed if the app is ready within 5 s. Otherwise
  "Still starting Corporate Serf Dashboard ... N seconds elapsed." prints at
  5 s and then at least every 5 s (loop granularity can add up to ~2.5 s,
  and a slow-to-refuse loopback port shifts the first lines to ~7/12 s), and
  a ready that follows any heartbeat prints "Corporate Serf Dashboard is
  ready after N seconds."; `exited` and `timeout` print no completion line
  ([2026-08-21](../decision_log.md#2026-08-21-the-launcher-narrates-a-slow-start-and-keeps-its-120-second-ceiling)).
- Normal start prints "Starting Corporate Serf Dashboard <tag> ...". A
  non-ready outcome kills the child tree, `Show-AppFailure` prints
  "WARNING: the dashboard failed to start (<state>)." plus the last 15
  lines of `launcher-app-stderr.log` under an "--- app error output ---"
  rule, and `Stop-Fatal` prints "ERROR: version <tag> did not become ready
  on port <port>. A readiness failure can be config-caused: check
  config.toml in <root> and the app error output above.", the reinstall
  one-liner, and "Press Enter to close"
  ([2026-08-21](../decision_log.md#2026-08-21-the-launcher-narrates-a-slow-start-and-keeps-its-120-second-ceiling)).
- After ready, the browser opens at `http://<browser>:<port>/` when
  `open_browser_on_launch` is on, old versions are pruned, the bootstrap is
  updated, and "Dashboard running at http://<browser>:<port>/ -- close this
  window (or press Ctrl+C) to stop it." prints either way; a failed
  post-start step prints a `WARNING:` and leaves the app running. The
  launcher then waits on the app and exits with its code
  ([2026-08-09](../decision_log.md#2026-08-09-human-facing-urls-say-localhost-machine-probes-stay-on-127001),
  [2026-09-04](../decision_log.md#2026-09-04-the-launchers-browser-open-is-a-config-knob-tab-reuse-is-not-achievable)).
- A port already taken is the app's failure, not the launcher's: the app
  binds exclusively and exits, which the launcher reports as `exited`
  ([2026-07-19](../decision_log.md#2026-07-19-the-app-binds-its-port-exclusively-and-exits-if-it-is-taken)).

## Updating

- Under any policy other than `pinned` (the scripts write only `latest`)
  the launcher queries `releases/latest` with a
  5 s timeout; any failure prints "Update check failed (<reason>); starting
  the installed version." and runs the installed version. A `pinned`
  policy skips the check entirely; re-running the installer without `-Tag`
  rewrites the policy to `latest`
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).
- A different tag prints "Update available: <old> -> <new>" and fetches its
  `release.json`. A failed fetch of `release.json`, a `schema_version`
  other than 1, a parse failure, or a
  missing field prints a yellow banner: "A new release (<tag>) exists, but
  this installed launcher cannot understand it (<reason>).", "Starting the
  installed version instead. Updating requires reinstalling:", the
  one-liner, and "(Reinstalling keeps your config and data.)"
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).
- The new release is provisioned and staged exactly as the installer does
  it (uv per release, download with source-archive fallback, one top-level
  directory, stamp must carry the SHA, verbatim `release.json`, `uv sync`),
  into its own `versions\<tag>\`; an existing directory of that tag is
  replaced. "Starting <tag> (pending activation) ..." starts it with a fresh
  token and `Wait-AppReady` gates it on that release's `sha`
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).
- On `ready` the manifest is rewritten atomically to the new tag, SHA, and
  date with policy `latest`, "Updated to <tag>." prints, the browser opens
  when `open_browser_on_launch` is on, the previous version is kept and
  every other version directory pruned,
  and the bootstrap is updated. On `exited` or `timeout` the pending process
  is killed, "WARNING: release <tag> failed to start (<state>); starting
  <old> instead." prints with the stderr tail, the manifest is untouched,
  and the previous version starts. Any exception before promotion kills the
  pending process and prints "Update to <tag> failed (<reason>); starting
  the installed version."; after promotion it prints "WARNING: a
  post-update step failed (<reason>); the update itself succeeded."
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).
- The launcher that performs an update is the previous release's: the
  bootstrap picked it from the manifest before the check ran. A change to
  launcher behavior therefore takes effect from the launch after the one
  that installed it, not on that launch
  ([2026-09-04](../decision_log.md#2026-09-04-the-launchers-browser-open-is-a-config-knob-tab-reuse-is-not-achievable)).
- A release that fails its gate is retried in full on every launch until a
  newer release appears
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).
- `Remove-PrunedVersions` keeps the active tag plus the replaced tag when it
  still exists, else the most recently written other directory, and deletes
  the rest ("Pruned old version <tag>."; a failure is a `WARNING:`)
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).
- `Update-Bootstrap` replaces the root `launch.ps1` only when the installed
  release's template carries a higher `csd-bootstrap-version` marker: it
  writes `launch.ps1.new` beside it, checks the copy's marker and parses it
  with the PowerShell parser, then `File.Replace`s over the live file; a
  failed check deletes the temp file and prints "WARNING: new launch.ps1
  bootstrap failed validation; keeping the current one." Success prints
  "Updated the launch.ps1 bootstrap to version N." The live file is never
  truncated in place. The marker is `1` today
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).
- Everything an old launcher parses is the frozen v1 wire contract:
  `release.json` and `install.json` fields, asset names and download paths,
  the uv and Python provisioning inputs. Changes within v1 are additive
  only
  ([2026-07-19](../decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)).

## Build identity

- `get_build_info()` resolves once per process, in order: the `release.json`
  beside the code (`source: "release-file"`), `install.json` in the state
  root (`"manifest"`), the expanded `version.txt` stamp (`"archive"`,
  `tag: None`), `git show` on the code root (`"git"`), else `"unknown"`.
  Either JSON file counts only when its `schema_version` is 1, it has a
  `sha`, and that `sha` equals the expanded stamp's; an unexpanded stamp
  disqualifies both
  ([2026-07-19](../decision_log.md#2026-07-19-build-identity-comes-from-the-manifest-corroborated-by-the-stamp)).
- A dev checkout reports its HEAD SHA and date with `tag: None`,
  `source: "git"`, and `release_label` `dev`; an installed copy reports its
  tag and `release-file`; nothing identifiable reports `unknown`.
- Identity surfaces as the startup log line `Build <short sha> (<date>),
  <label>` in `debug.log`, in `/health`, and on the Settings page as
  "Version <label>" and "Commit <short sha> (<date>)"; the Dash app title
  carries the tag only when one is known; opt-in, `show_version_in_title`
  prefixes every tab title with the label. The Settings page section's own
  rules are set by
  ([2026-08-02](../decision_log.md#2026-08-02-the-settings-page-owns-version-display)).

## State root

- The installer sets `CSD_STATE_DIR` to the install root around its
  `load_config()` round-trip, clearing it afterward; the launcher sets it
  to the install root around the endpoint read, clearing it afterward, and
  again when it starts the app process, where it is left set (only the
  launch token is cleared). In an installed copy the state root is therefore the install root:
  `config.toml`, `install.json`, and `data/` sit beside `versions/`. Unset
  means the working directory; what the root holds is set by
  ([2026-07-19](../decision_log.md#2026-07-19-all-mutable-state-lives-under-an-explicit-state-root)).

## Schema migration shipping

- `scripts/stamp_schema_version.py` ships in every release under
  `versions/<tag>/scripts/`. Its documented order is: back up `data/`,
  update to the stamping release or newer, close the app, run the script
  with the release's own `.venv\Scripts\python.exe`, relaunch. It resolves
  the state root from `--state-dir`, then `CSD_STATE_DIR`, then the install
  root inferred from a `versions/<tag>/scripts` shape with `install.json`
  above it, then the working directory. The store contract is set by
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
