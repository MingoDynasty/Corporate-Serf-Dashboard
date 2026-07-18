# Proposal: release, versioning, and distribution model

Status: Proposed — revision 2, 2026-07-18. Revision 0 received an external
design review (Codex) before PR #150 opened; revision 2 folds in the second
Codex round from the PR itself. Every finding was triaged (fix / accept /
defer); the finding-by-finding dispositions live in the review handoff doc
(untracked, `ignore/pr-reviews/pr150-review.md`).

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
  since May 2026), so concurrent pushes cannot race the `.N` computation;
- is idempotent: if a tag already points at `HEAD`, it is reused and a
  missing release is repaired rather than allocating a new suffix;
- creates the tag, then a **draft** release, attaches the source zip, and
  only then publishes — required once releases are immutable (D7), because
  assets cannot be added after publication. The zip is produced by
  `git archive --format=zip <tag SHA>` — the only producer that expands the
  export-subst stamp (D2); zipping a checkout would ship `version.txt`
  unexpanded;
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
   update policy (see D6). This is the authoritative identity for installed
   copies — the export-subst stamp alone cannot carry the tag name.
2. **`version.txt`** committed with the placeholder `$Format:%h %cs$` plus a
   `.gitattributes` line `version.txt export-subst`. GitHub's archive
   endpoints run `git archive`, which expands the placeholder, so any zip
   download — even outside the installer — carries its short SHA + commit
   date. (Same mechanism as setuptools-scm's `.git_archival.txt`.)
3. **Git fallback**: if the placeholder is unexpanded, we're in a checkout —
   `git rev-parse --short HEAD`; else `unknown`.

Precedence: manifest → expanded `version.txt` → git → `unknown`. All
user-visible identity (D3) derives from this one `BuildInfo`.
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

**Mechanism.** `install.ps1` at repo root; user instruction is one line:
`irm https://raw.githubusercontent.com/MingoDynasty/Corporate-Serf-Dashboard/main/install.ps1 | iex`.
The script:

- makes the **entire toolchain app-local**, not just the uv binary:
  `UV_UNMANAGED_INSTALL` places the exact pinned uv
  (`tool.uv.required-version`, currently `==0.11.26`) in the install tree,
  invoked by absolute path; `UV_PYTHON_INSTALL_DIR` keeps managed CPython
  under the install root and `--managed-python` forbids silently selecting
  whatever Python the machine happens to have; `UV_CACHE_DIR` keeps the
  cache inside too. Nothing uses or disturbs any uv/Python already on the
  machine, and uninstall is honest: delete the folder and the shortcut;
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
- writes the install manifest (D2) atomically and creates a desktop
  shortcut.

The README documents a manual alternative (download the release zip
yourself, inspect, run the script from the extract) for users who won't pipe
a script from the internet, and notes that `-ExecutionPolicy Bypass` does
not and should not defeat enterprise Group Policy/AppLocker — home machines
are the audience.

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
changing — when it does, the versioned launcher overwrites it on a higher
embedded version marker (no richer update protocol than that). The
versioned launcher then applies the manifest policy:

- `update_policy: "latest"` (default): query `releases/latest` with a short
  timeout; if its tag differs from the installed one, download into a new
  per-tag directory and sync — but do **not** promote yet. The new version
  starts as a pending activation: the launcher polls
  `http://localhost:<port>` for readiness (the same poll that decides when
  to open the browser), and only a ready app gets the manifest atomically
  rewritten to make it authoritative. On timeout or early exit, the
  launcher starts the previous version instead and leaves the manifest
  untouched — a crashing release never becomes the recorded install. (A
  readiness failure can also be config-caused, in which case the previous
  version fails identically and the launcher surfaces the app's error
  output; it does not try to attribute blame.) On any network/API failure:
  run the existing install unchanged (fail-open, offline-safe). One
  unauthenticated API call per launch is well inside GitHub's 60/hour/IP
  limit; no caching layer is warranted for one call.
- `update_policy: "pinned"` + `pinned_tag`: skip the update check entirely
  and run the pinned version. A rollback install (`install.ps1 -Tag
  v2026.07.17`) **writes this pin**; without it, the next launch would
  immediately re-install the bad latest release, making rollback a no-op —
  the external review's sharpest catch. Returning to normal is explicit:
  re-run the installer without `-Tag` (or a documented one-line manifest
  edit), which restores `latest`.

The previous version's directory is kept until the new one has started
successfully once, then pruned (keep last two).

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
update check; in-app update UI. Each has a trigger to revisit: more users,
a second audience, or evidence of tampering risk.

## Delivery plan

- **PR 1 — build identity**: `version.txt` + `.gitattributes`, `BuildInfo`
  reader with the D2 precedence chain, tooltip + log line + title fix,
  `.python-version` (trivial rider — every later PR then inherits the
  pinned interpreter), tests including the empirical export-subst check
  against GitHub's zip download. No dependencies.
- **PR 2 — state root**: `CSD_STATE_DIR` + paths module, package-relative
  `resources/`, an actionable startup error when `stats_dir` does not exist
  (today the watchdog observer throws a raw traceback at the "Change me!"
  placeholder), tests. Independent of PR 1.
- **PR 3 — release job in CI**: D1 in full (blocklist gating, concurrency,
  idempotency, `git archive` asset, draft→publish). The D7
  immutable-releases setting is flipped **before merge**; post-merge
  verification downloads the first release's named asset and asserts the
  export-subst stamp expanded.
- **PR 4 — installer + launcher + README**: D5 + D6 (first-run stats-dir
  detection, root bootstrap, pending-activation update), README "Easy
  install", rollback, and uninstall sections. Depends on PRs 1–3 (needs a
  real release, the state root, and the manifest reader). As the PR that
  finishes shipping this proposal, it also owes the AGENTS.md "Shipping a
  proposal" definition of done: distill durable decisions into
  `docs/decision_log.md`, delete this file, update `docs/roadmap.md` /
  `docs/product.md` / `docs/tech_debt.md`, and repair references.
