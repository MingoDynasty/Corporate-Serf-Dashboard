# Proposal: release, versioning, and distribution model

Status: Proposed — revision 5, 2026-07-18. Revision 5 amends D2 and D6 only:
implementing PR 1 surfaced a conflict *between* those two decisions (the
manifest-first precedence made a pending update permanently unpromotable),
found by the Codex review of PR #154 and confirmed there — a P1-class
finding, which is the trigger the freeze rule requires. Everything below
that is revision 4, unchanged.

Revision 4, 2026-07-18. Four external design-review
rounds (Codex): r0–r2 general, then a scoped round-4 P1 hunt against
revision 3's freeze, which produced five confirmed release blockers —
the freeze rule (design changes require a P1-class finding) working as
intended. All are folded in below; finding-by-finding dispositions live in
the review handoff doc (untracked, `ignore/pr-reviews/pr150-review.md`).
The freeze is re-declared as of r4 on the same rule. Two round-4 claims
were verified empirically in-house before adoption: this repo's Python
3.14 `tomllib` rejects both a UTF-8 BOM and raw backslash Windows paths in
TOML basic strings.

## Background

Corporate Serf Dashboard is a local Python/Dash web app (single maintainer,
near-daily merges to `main`) that watches a KovaaK's aim-trainer stats
directory and serves a dashboard at `localhost:<port>`. It must run on the
user's machine (it reads local files); there is no hosted variant, no library
API, and no downstream consumer of any interface.

Distribution today: users `git clone` and run `uv sync && uv run python
source/app.py` (README). There are no releases, no tags, and no version
identity — `pyproject.toml` carries a static `version = "1.0.0"` that never
changes, and the browser title advertises it (`source/app.py`,
`APP_NAME = f"... v{version('Corporate-Serf-Dashboard')}"`). Every mutable
and bundled path is resolved from the process working directory:
`config.toml` (`source/config/config_service.py`), `data/logs/`
(`source/app.py`), `resources/benchmarks` and `data/playlists`
(`source/kovaaks/data_service.py`), `data/preferences.json`
(`source/kovaaks/playlist_visibility_service.py`).

Two problems motivate this proposal:

1. **Non-technical users** (Windows gamers) can't be assumed to have Python,
   uv, or git, or to be comfortable with any of them.
2. **No build identity**: when a user reports a bug there is no way to know
   what they are running, and no way for them to go back to a working build.

## Decisions

### D1. No manual versioning; CI-gated automated CalVer tags + GitHub Releases

**Mechanism.** A `release` job is added to the existing CI workflow
(`.github/workflows/ci.yml`), running only on push to `main` with
`needs: test` — a commit that fails gates never becomes a release. The job:

- is skipped only when the push touches nothing outside known non-runtime
  paths (`docs/**`, `tests/**`, `**/*.md`, `.gitignore`,
  `.pre-commit-config.yaml`, `.github/**`) — a blocklist, not an allowlist,
  because the failure directions are asymmetric: a redundant release is
  noise, while a missed release strands distribution inputs (`install.ps1`,
  the launcher, `example.toml`, `.python-version`, `.gitattributes`) at an
  older tag. When in doubt, release;
- computes the next tag `vYYYY.MM.DD` (`.N` suffix for same-day repeats) from
  existing tags at execution time;
- serializes via a fixed concurrency group with `cancel-in-progress: false`
  and `queue: max` (GitHub Actions has supported >1 queued run per group
  since May 2026), so concurrent pushes cannot race the `.N` computation.
  Serialization does **not** establish source order — FIFO is by
  wait-start time, and a newer push with faster tests can release first —
  so the job also enforces a **Latest invariant**: inside the critical
  section it checks ancestry (`git merge-base --is-ancestor`) against
  already-published releases; if a published release's commit descends
  from the job's SHA, the job publishes its release explicitly with
  `make_latest: false` (older source must never displace newer source as
  Latest — `make_latest` defaults to true and would otherwise let a slow
  older run silently downgrade every `latest`-tracking install). After
  claiming Latest, the job asserts `releases/latest` resolves to the tag
  it just published;
- is idempotent across every partial-failure state, not just
  tag-without-release: a rerun reuses a tag already pointing at `HEAD`,
  locates and **resumes an existing draft** (re-attaching assets) rather
  than creating a second release, and only then publishes;
- creates the tag, then a **draft** release, attaches assets, validates,
  and only then publishes — required once releases are immutable (D7),
  because assets lock at publication, which also means validation must run
  pre-publish (after publishing an immutable release it is too late to fix
  one). The zip is produced by `git archive --format=zip <tag SHA>` — the
  only producer that expands the export-subst stamp (D2); zipping a
  checkout would ship `version.txt` unexpanded — and the validation step
  unzips the built asset and asserts the stamp actually expanded;
- attaches a second, tiny asset: `release.json` — machine-readable release
  metadata carrying the tag, the **full commit SHA**, the commit date, and
  the release's `tool.uv.required-version` and `.python-version` values.
  Installer and launcher consume this instead of parsing TOML from
  PowerShell or making extra API calls for the exact SHA
  (`releases/latest` alone reports `target_commitish`, which may be a
  branch name rather than a SHA);
- holds `contents: write` at job scope only; the workflow keeps its current
  top-level `contents: read`.

Nothing is compiled; the zip of the tagged source is the artifact, since
users run from source via uv. No human ever chooses a version number or
decides whether a commit "deserves" a release.

**Why.** The maintainer explicitly does not want per-commit release judgment
(SemVer bump decisions), and the app has no API consumers to justify SemVer
semantics. But market research (below) found no comparable project shipping
*unidentified* builds from a branch tip: dated, immutable, retained artifacts
are the observed baseline even for daily-or-faster shippers, because tags are
load-bearing for rollback and support. yt-dlp shows automation removes the
manual version-selection overhead entirely (its versions are auto-generated
`yyyy.mm.dd[.rev]` in CI) — though workflow maintenance and failed-release
recovery remain real, small, costs.

### D2. Build identity: install manifest as source of truth, export-subst as stamp

**Mechanism.** Three layers, one `BuildInfo` reader:

1. **Install manifest** (`install.json`, written atomically by the
   installer/launcher, never by the app): tag, full SHA, commit date, and
   update policy (see D6), copied from the release's `release.json` asset
   (D1) — the defined source for the exact SHA. This is the authoritative
   identity for installed copies — the export-subst stamp alone cannot
   carry the tag name.
2. **`version.txt`** committed in labeled `key: value` form with git
   placeholders — `sha: $Format:%H$` and `commit-date: $Format:%cs$`,
   preceded by an explanatory comment header — plus a `.gitattributes`
   line `version.txt export-subst` (the `.git_archival.txt` idiom).
   GitHub's archive endpoints run `git archive`, which expands the
   placeholders, so any zip download — even outside the installer —
   carries its full SHA + commit date; `BuildInfo` shortens the SHA for
   display only. Deliberately plain text rather than JSON: the committed
   file needs its comment header (a raw placeholder looks broken to repo
   browsers), and export-subst output is not JSON-escaped, so a JSON
   envelope would silently constrain future placeholders to escape-safe
   expansions.
3. **Git fallback**: if the placeholder is unexpanded, we're in a checkout —
   `git rev-parse HEAD`; else `unknown`.

Precedence: manifest → expanded `version.txt` → git → `unknown`, with one
condition on the first step (revision 5): **the manifest is authoritative
only when it corroborates the running code** — its `sha` must equal the SHA
in the expanded stamp beside the code. The manifest belongs to the install's
state, not to any one code directory, so during a pending activation (D6) it
still names the *previous* version while the new one is already running.
Unconditional manifest-first precedence would therefore make the new build
report the old identity, and the launcher's own promotion check would reject
it forever. Missing, unexpanded, or mismatched stamp ⇒ the manifest is
ignored and the stamp (then git) answers. The accepted consequence is that a
freshly promoted version keeps reporting `source: "archive"` and `tag: None`
until the next launch; SHA and date still identify it exactly, and D1 makes
the tag↔SHA mapping public.

All user-visible identity (D3) derives from this one `BuildInfo`.
Implementation must verify the export-subst expansion empirically before
building on it: the mechanism is documented
(`git-scm.com/docs/gitattributes`, GitHub source archives are `git archive`
output), but our research run's adversarial verification of this specific
claim was lost to infrastructure errors, not confirmed. PR 1 checks GitHub's
on-demand zip download; PR 3's verification checks the named release asset
itself once the first release publishes (the asset is what the launcher
actually consumes).

**Why manifest + stamp, not a CI-committed version file.** A bot committing
a version file on every push is self-defeating: the commit changes the SHA
so the file always describes the parent commit, doubles commit traffic, and
forces constant fetch friction for the maintainer and parallel agent
sessions. export-subst needs no commits and is never stale; the manifest
adds the tag and policy, which no in-repo file can know.

### D3. Where the identity surfaces

**Mechanism.** (a) One log line at startup into `data/logs/debug.log`
(`Build <sha> (<date>), <tag|dev|unknown>`) — bug reports arrive with the
log file. (b) Appended to the existing GitHub icon tooltip in the header
("View this app on GitHub — build 0d597ab (2026-07-18)"). (c) The browser
title stops advertising the static `v1.0.0`: it derives from `BuildInfo`
(tag when known, otherwise no version suffix).

**Why.** The maintainer wants the header clean; a footer would spend
vertical space on every page for a string read once per bug report. The
tooltip costs zero pixels; the log line is the copy that matters. An
app-settings page/modal was rejected as a new surface invented to house one
read-only string. The title fix removes the only currently-displayed version
string, which is wrong today and would become misleading under D1.

### D4. Explicit state root, so code and state can separate

**Mechanism.** A new environment variable (working name `CSD_STATE_DIR`)
names the directory holding all mutable state: `config.toml`, `data/`
(playlists, logs, preferences). Unset ⇒ current working directory, so dev
checkouts behave exactly as today. Bundled read-only assets
(`resources/benchmarks`) stop resolving from CWD and resolve relative to the
installed package (`Path(__file__)`), since they ship with the code. A small
paths module centralizes both rules; the services listed in Background
switch to it.

**Why.** Without this, versioned code directories cannot work: running the
app from a fresh version directory loses `config.toml`/`data/`, and running
it from the state root loses `resources/benchmarks`. (Revision 0 claimed the
installer needed "zero code changes"; the external review correctly killed
that claim.) An env var keeps the contract explicit and testable, and the
launcher — not the app — owns choosing the directories.

### D5. Install path: PowerShell one-liner, app-local toolchain

**Mechanism.** Two scripts, so the installer is always the same age as its
payload. The one-liner fetches a deliberately trivial, permanently
backward-compatible shim from `main` — `get.ps1`: resolve the latest
release tag, fetch that tag's `install.ps1`, run it, nothing else:
`irm https://raw.githubusercontent.com/MingoDynasty/Corporate-Serf-Dashboard/main/get.ps1 | iex`.
The real installer (`install.ps1`, fetched at the tag it installs) can then
change freely between releases without ever running against an older
payload whose layout it no longer matches — the skew that would otherwise
open every time an installer change merges ahead of its release, and stay
open indefinitely if a release job fails. The installer:

- makes the **entire toolchain app-local**, not just the uv binary:
  `UV_UNMANAGED_INSTALL` places uv in the install tree, invoked by absolute
  path; `UV_PYTHON_INSTALL_DIR` keeps managed CPython under the install
  root and `--managed-python` forbids silently selecting whatever Python
  the machine happens to have; `UV_CACHE_DIR` keeps the cache inside too.
  Nothing uses or disturbs any uv/Python already on the machine, and
  uninstall is honest: delete the folder and the shortcut. The uv version
  is **per release, not per install**: installer and launcher read the
  target release's `release.json` (D1) and ensure that exact uv
  (`tool.uv.required-version`, currently `==0.11.26`) is present
  app-locally *before* syncing that release. An install-time-frozen uv
  would brick the first update that bumps the pin — the old binary rejects
  the new project, and `UV_UNMANAGED_INSTALL` disables uv self-update — so
  the toolchain upgrade must ride the same update transaction as the code;
- provisions CPython per a committed `.python-version` (3.14). **This file
  does not exist yet** — creating it is assigned to PR 1 — because
  `requires-python = ">=3.14"` alone would silently float to 3.15+;
- downloads the **latest release asset zip** (not `main`'s tip; falls back
  to the tag's source archive if the asset is missing), extracts the code
  into a per-tag directory under `%LOCALAPPDATA%\CorporateSerfDashboard`,
  and syncs with `--locked --no-dev` (dev group is synced by default
  otherwise; `uv.lock` is committed and CI already enforces `--locked`);
- on first run, does not merely copy `example.toml` (whose
  `stats_dir = "Change me!"` placeholder would crash the first launch when
  the watchdog observer schedules a nonexistent directory): it locates the
  KovaaK's stats directory itself — Steam's registry `InstallPath` plus
  `libraryfolders.vdf` → `steamapps/common/FPSAimTrainer/FPSAimTrainer/stats`
  — confirms it with the user, falls back to a prompt, validates that the
  directory exists, and writes it into `config.toml`. Existing `config.toml`
  and `data/` are never touched (they live in the state root, which version
  swaps never write to);
- targets **Windows PowerShell 5.1** (stock Windows 11 — the shell the
  one-liner actually lands in) and treats serialization as a contract:
  every machine-readable file (`config.toml`, `install.json`) is written
  UTF-8 **without BOM** via `System.Text.UTF8Encoding($false)` — 5.1's
  `-Encoding UTF8` emits a BOM — and paths are written with forward
  slashes. Verified against this repo's Python 3.14: `tomllib` rejects
  both a BOM and raw `\` in TOML basic strings, and either alone would
  yield a config the app can never parse — which the
  preserve-existing-config rule would then make permanent;
- validates before it commits: after writing `config.toml`, it round-trip
  parses the generated file with the installed Python's `tomllib`, and
  only then writes the install manifest (D2) atomically and creates the
  desktop shortcut — a config the app cannot parse must fail the install
  loudly, never surface later as a permanently broken first launch.

The README documents a manual alternative (download the release zip
yourself, inspect it, then run the installer with an exact copy-pastable
terminal command — double-clicking a `.ps1` deliberately does not execute
it on Windows) for users who won't pipe a script from the internet, and
notes that `-ExecutionPolicy Bypass` does not and should not defeat
enterprise Group Policy/AppLocker — home machines are the audience.

**Why.** The user's machine needs exactly one bootstrapped tool (uv),
acquired the way rustup/uv themselves are distributed, and app-local
installation makes the app's toolchain invisible to whatever else the user
has. Python and git are never prerequisites. PyInstaller was rejected (see
Rejected alternatives).

### D6. Update UX: launcher with a persistent update policy; tags are rollback

**Mechanism.** The desktop shortcut targets a deliberately trivial,
**stable bootstrap** at the install root (`launch.ps1`): read the manifest,
delegate to the selected version's launcher, nothing else. Per-tag
directories get pruned, so the shortcut must never point into one; and
because the bootstrap does almost nothing, it should almost never need
changing — when it does, the versioned launcher replaces it on a higher
embedded version marker, and the replacement must be **atomic**: write a
same-directory temp file (UTF-8, no BOM), validate its marker and
PowerShell syntax, then rename over `launch.ps1`. Never truncate the live
file in place — Windows PowerShell keeps executing the already-parsed body,
so an interrupted in-place write leaves a working session now and a bricked
entrypoint for every launch after it (review empirically confirmed a
running 5.1 script is replaceable without a lock error).

The launcher is **single-instance**: it takes a named mutex scoped to the
install root and holds it for the launcher+app lifetime. A second
double-click sees the mutex, opens the browser at the running instance,
and exits — it does not update, sync, or touch the manifest. Without this,
two quick launches race the same per-tag extract, the manifest, and the
port; atomic manifest writes protect one file, not the whole transaction.
The versioned launcher then applies the manifest policy:

- `update_policy: "latest"` (default): query `releases/latest` with a short
  timeout; if its tag differs from the installed one, download into a new
  per-tag directory and sync — but do **not** promote yet. The new version
  starts as a pending activation: the launcher polls a small identity
  endpoint (`/health`, added in PR 1) that reports the app's `BuildInfo`
  and echoes back a per-launch token passed via environment variable — a
  bare HTTP 200 is not proof of life, because an already-running instance
  or an unrelated service (Steam famously squats on the default port 8080)
  can answer while the pending process failed to bind. Promotion requires
  the child process still alive **and** the response carrying the expected
  full SHA and launch token; the same poll decides when to open the browser.
  The gate must **not** require a tag match (revision 5): a build on trial
  has not been promoted, so its manifest still names the previous version
  and is ignored under D2's corroboration rule — it reports its own SHA with
  `tag: None`. Requiring a tag here would reject every valid update. Only then is the manifest atomically rewritten to make the new
  version authoritative. On timeout or early exit, the
  launcher starts the previous version instead and leaves the manifest
  untouched — a crashing release never becomes the recorded install. (A
  readiness failure can also be config-caused, in which case the previous
  version fails identically and the launcher surfaces the app's error
  output; it does not try to attribute blame.) On any network/API failure:
  run the existing install unchanged (fail-open, offline-safe). A
  schema-incompatible release (D8) also fails open, but **loudly**: run
  the existing install and tell the user to re-run the install one-liner —
  silent permanent stranding is the one failure this design must never
  produce. One unauthenticated API call per launch is well inside GitHub's
  60/hour/IP limit; no caching layer is warranted for one call.
- `update_policy: "pinned"` + `pinned_tag`: skip the update check entirely
  and run the pinned version. A rollback install (`install.ps1 -Tag
  v2026.07.17`) **writes this pin**; without it, the next launch would
  immediately re-install the bad latest release, making rollback a no-op —
  the external review's sharpest catch. Returning to normal is explicit:
  re-run the installer without `-Tag` (or a documented one-line manifest
  edit), which restores `latest`.

The previous version's directory is kept until the new one has started
successfully once, then pruned (keep last two).

Rollback protects **code**; durable state is governed by a compatibility
rule rather than machinery. Releases must read older state (missing keys
get defaults — already the norm here) and must not rewrite user-authored
files (`config.toml` is user-owned after install; the app writes only
under `data/`). The durable state is a handful of tiny, schema-stable
files (preferences.json, imported playlist JSONs), so a release that
genuinely changes a state format is rare enough to be called out in its
PR/release notes with a manual step — the house convention for a
single-digit user base. State snapshot/restore machinery is deferred, not
built (see Deferred).

**Why.** This preserves "everyone runs latest" as the default with one
double-click, while making a bad morning push recoverable *durably*.
Channel separation (stable/nightly) à la yt-dlp/PoB is deferred — single
channel is defensible at this audience size; the research says channels are
the deferrable part, identity is not.

### D7. Immutability is enforced, not assumed

**Mechanism.** Enable GitHub's immutable-releases setting on the repo so
tags/releases cannot be moved or deleted. The setting is not retroactive,
and merging PR 3 itself cuts the first release — so this is a **pre-merge**
step of PR 3, not post-merge, or that first release stays mutable forever.
It is also what forces D1's draft-first flow, since immutable release
assets lock at publication. The named asset zip gives stable bytes with a
GitHub-provided digest; launcher-side checksum verification is deferred
(HTTPS to github.com is the trust anchor for this audience).

### D8. Update wire contract v1 — the first launcher is supported forever

**Mechanism.** A pinned or long-offline install may legitimately jump from
the first PR-4 launcher straight to any future release, and the launcher
executing that update is always the *old* one. Everything old launchers
parse or act on is therefore a frozen, versioned wire contract from day
one:

- `release.json` and `install.json` both carry `schema_version: 1`. The v1
  field set — names, types, required fields, release asset names/paths,
  and the uv/Python provisioning inputs — freezes when PR 4 ships.
- Evolution rule: changes within v1 are additive-only (new optional
  fields; v1 consumers ignore what they don't recognize). A breaking
  change bumps `schema_version` and dual-publishes the v1 envelope
  alongside the new one for as long as v1 launchers may exist.
- A launcher that meets an unknown `schema_version` — or any parse
  failure — runs the existing install and surfaces an actionable message
  ("update requires reinstalling: re-run the install one-liner") instead
  of failing silently. Re-running the one-liner always recovers, because
  `get.ps1` pairs a fresh installer with a fresh payload (D5).

**Why.** Fail-open alone converts a wire-contract break into *silent
permanent stranding*: every launch retries the parse, fails, runs the old
version, and never tells the user. The contract freeze makes breaks rare;
the loud incompatible-schema path makes the rare break user-recoverable
without support.

## Rejected alternatives

- **PyInstaller exe.** Unsigned exes trip SmartScreen and AV heuristics
  (fatal for a gaming audience's trust); code signing is a recurring cost;
  every release becomes a CI build plus a large user re-download, fighting
  the daily cadence; dash/plotly/dash-ag-grid asset bundling under
  PyInstaller is a known hook-debugging time sink. Revisit only if "run any
  command" ever becomes too much to ask.
- **CI commits a version file on every push.** See D2.
- **SemVer / conventional-commit automation (release-please etc.).**
  Reintroduces per-commit judgment (feat vs fix) — the exact treadmill being
  avoided — for semantics no consumer of this app needs.
- **PyPI + `uvx` now.** Clean long-term story but requires an entry point
  and further state-dir work; the release-zip model plus D4 is a smaller
  step. Deferred, not rejected.

## Evidence (market research, 2026-07-18)

Method: multi-agent research run — 5 search angles, 19 sources fetched, 93
claims extracted, top 25 adversarially verified (3 independent verifiers per
claim; 9 confirmed, 1 refuted, 15 lost to verifier infrastructure errors —
votes lost, not research; the lost claims were largely corroborative
detail). FFmpeg was checked separately against primary sources.

- **yt-dlp**: every build in every channel — including the per-push
  "canary" master channel — is an immutable tagged CalVer GitHub release;
  versions are auto-generated `yyyy.mm.dd[.rev]`; the self-updater is
  version-addressable and documents *downgrades* (`--update-to
  stable@2023.07.06`).
  [README](https://github.com/yt-dlp/yt-dlp/blob/master/README.md),
  [release.yml](https://github.com/yt-dlp/yt-dlp/blob/master/.github/workflows/release.yml).
- **Path of Building Community** (closest analog: gaming-community Windows
  app): develops on `dev`, ships via an automated release workflow gated on
  merges to `master`; even its opt-in beta channel stamps the short SHA into
  the version.
  [RELEASE.md](https://github.com/PathOfBuildingCommunity/PathOfBuilding/blob/dev/RELEASE.md),
  [release.yml](https://github.com/PathOfBuildingCommunity/PathOfBuilding/blob/dev/.github/workflows/release.yml).
- **RuneLite**: the auto-update launcher itself is formally versioned (57
  tagged releases, platform installers).
  [runelite/launcher](https://github.com/runelite/launcher).
- **FFmpeg**: the project ships source only and tells source-compiling users
  to prefer the development branch — the strongest real precedent for
  "master is what users run." But the binary channels non-technical users
  actually use convert master into dated immutable artifacts: BtbN publishes
  daily tagged releases (`autobuild-2026-07-18-13-13`) plus a rolling
  `latest`; gyan.dev bakes date + short SHA into filenames
  (`ffmpeg-2026-07-13-git-9c2aabaa34-essentials_build.7z`) and archives old
  builds. FFmpeg reserves version numbers for distributors/API consumers — a
  class this project does not have.
  [download page](https://ffmpeg.org/download.html),
  [BtbN releases](https://github.com/BtbN/FFmpeg-Builds/releases),
  [gyan.dev builds](https://www.gyan.dev/ffmpeg/builds/).
- Mechanism references: [gitattributes export-subst](https://git-scm.com/docs/gitattributes),
  [setuptools-scm archival usage](https://setuptools-scm.readthedocs.io/en/latest/usage/),
  [Actions concurrency `queue: max` (May 2026)](https://github.blog/changelog/2026-05-07-github-actions-concurrency-groups-now-allow-larger-queues/),
  [uv installer options](https://docs.astral.sh/uv/configuration/installer/).

Verdict: "raw default-branch installs with no identity" was observed nowhere
in the sample. The convergent pattern for fast shippers is machine-generated
date/SHA identity on immutable, retained artifacts — which D1+D2 provide.
Caveats: the verified sample is three projects plus FFmpeg, all larger than
this one (evidence of where the pattern converges, not proof that tagless is
unworkable at this size); the Zed auto-update post-mortem went unverified.

## Deferred (explicitly out of scope)

Channel separation (stable/nightly); PyPI + `uvx` distribution;
launcher-side checksum verification; ETag/conditional-request caching of the
update check; in-app update UI; state snapshot/restore on rollback (the D6
compatibility rule covers it at this scale). Each has a trigger to revisit:
more users, a second audience, evidence of tampering risk, or a real
state-format break.

## Delivery plan

- **PR 1 — build identity**: `version.txt` + `.gitattributes`, `BuildInfo`
  reader with the D2 precedence chain, tooltip + log line + title fix, the
  `/health` identity endpoint (BuildInfo + launch-token echo),
  `.python-version` (trivial rider — every later PR then inherits the
  pinned interpreter), tests including the empirical export-subst check
  against GitHub's zip download of the pushed commit
  (`/archive/<sha>.zip` — works before any release exists), run as a
  dedicated retried CI step rather than inside the default pytest gate so
  a network flake blocks a merge without polluting local test runs. No
  dependencies.
- **PR 2 — state root**: `CSD_STATE_DIR` + paths module, package-relative
  `resources/`, an actionable startup error when `stats_dir` does not exist
  (today the watchdog observer throws a raw traceback at the "Change me!"
  placeholder), tests. Independent of PR 1.
- **PR 3 — release job in CI**: D1 in full (blocklist gating, concurrency,
  draft-resume idempotency, `git archive` asset, `release.json` metadata,
  pre-publish validation of the expanded stamp inside the built zip,
  draft→publish). The D7 immutable-releases setting is flipped **before
  merge**; post-merge verification re-downloads the first release's assets
  to confirm the in-workflow validation.
- **PR 4 — installer + launcher (mechanics only, unadvertised)**: D5 + D6
  + D8 (`get.ps1` shim + tag-versioned `install.ps1`, first-run stats-dir
  detection, root bootstrap, single-instance mutex, per-release uv
  provisioning, pending-activation update with identity probe,
  `schema_version: 1` manifests). Deliberately does **not** touch the
  README: advertising the one-liner in the same PR opens a window —
  between merge and the release job finishing, or indefinitely if that
  job fails — where `get.ps1` resolves a latest tag containing no
  `install.ps1`. The shim still gets a friendly "release not ready yet —
  try again shortly" message for that 404 as bootstrap-era safety.
  Depends on PRs 1–3 (needs a real release, the state root, the
  `/health` endpoint, and the manifest reader).
- **PR 5 — activation (docs-only)**: after PR 4's release is verified
  end-to-end on a clean machine (one-liner → running dashboard), add the
  README "Easy install", rollback, and uninstall sections. Docs-only, so
  the D1 blocklist means it cuts no release — and none is needed. As the
  PR that finishes shipping this proposal, it owes the AGENTS.md
  "Shipping a proposal" definition of done: distill durable decisions
  into `docs/decision_log.md`, delete this file, update `docs/roadmap.md`
  / `docs/product.md` / `docs/tech_debt.md`, and repair references.
