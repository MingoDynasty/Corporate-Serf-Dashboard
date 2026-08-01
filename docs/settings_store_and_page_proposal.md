# Settings Store and Settings Page

Status: Proposed
Date: 2026-07-20 (reworked the same day from a detection-first draft —
identity auto-detection and the initial-setup flow moved to a
deliberately unscheduled follow-on proposal, working notes in
`ignore/design-notes/config-settings-arc.md`; amended 2026-08-01 to
replace the installer's settings seed with an app-side `stats_dir`
startup bootstrap)

## Problem

Three user-level values live in `config.toml`: `stats_dir`,
`kovaaks_username`, and `steam_id`. That placement has three costs:

1. **Hand-edit only.** Moving a Steam library means editing a text file to
   fix `stats_dir`; enabling rank lookups means discovering two fields in
   `example.toml`. There is no in-app way to see or change any of them.
2. **Frozen at boot.** `get_config()` is `@cache`d, so every change
   requires a restart — even though all three values are consumed
   per-operation and identity could apply live.
3. **Conflated ownership.** `config.toml` is written by a human (and once
   by the installer) and read by the app. User-level settings want the
   opposite: written by the app (a settings page now, auto-detection
   later), read per-operation. A file with two writers — the user's editor
   and the app — invites clobbered edits and precedence rules.

The 2026-07-20 config-architecture discussion settled the target shape:
`config.toml` is reserved for human-owned boot facts (`port`, `debug`) and
rarely-touched escape hatches (TTLs, timeouts, warmup toggle), while
everything user-facing lives in an app-owned store, edited on a settings
page. This proposal delivers the store, the relocation of all three
values, and the page — with plain manual entry and basic validation only.
Auto-detection of these values (which was drafted first and reordered:
manual editing must exist before detection so every detection dead end can
resolve to "type it on the page") is the follow-on.

## Verified facts (current `main`)

- `source/kovaaks/api_service.py` already takes `username`/`steam_id` as
  function arguments throughout — it never reads them from config. Config
  reads sit at five chokepoint files that pass them down:
  `source/pages/home.py`, `source/my_watchdog/file_watchdog.py`,
  `source/kovaaks/percentile_warmup_service.py`,
  `source/kovaaks/playlist_overview_service.py`,
  `source/kovaaks/playlist_scenarios_service.py`. All read per-operation,
  so identity applies live once the read is redirected — with one
  exception:
- `start_percentile_warmup_worker` (called once from `app.py`) returns
  early when no username is configured and never starts the worker. It is
  idempotent and lock-guarded, so it can simply be called again after
  identity is saved.
- Every existing consumer guards identity with truthiness (`if not
  config.kovaaks_username`), so an accessor that returns `None`/empty for
  "not configured" keeps all call-site semantics unchanged.
- `app.py` exits with an actionable stderr message when `stats_dir` is
  missing or not a directory. That is a policy choice, not a structural
  requirement: only `port` is needed to serve pages. Without a stats
  directory the app is merely empty, not broken.
- The installer already detects the stats directory (registry +
  `libraryfolders.vdf`), confirms it with the user, writes it into
  `config.toml`, and round-trips the generated file through the installed
  app's own `load_config()`. After PR #167 the generated file is
  `stats_dir` + `port`.
- The store mechanics being proposed are already proven in-repo by the
  visibility store (`source/kovaaks/playlist_visibility_service.py`):
  module `RLock`, in-process cache, atomic writes (temp file + fsync +
  `replace_with_retry`), tolerant reads.

## Design

### The store: `data/settings.json`

**One home, one writer** — the durable rule this proposal introduces:
every parameter lives in exactly one file, and every file has exactly one
owner. `config.toml` stays human-owned and app-read-only. `data/
settings.json` is app-owned, written through a new
`source/config/settings_service.py` (mechanics mirroring the visibility
store) — with no exceptions: the installer never touches it (the app
bootstraps its own `stats_dir`, below).

Flat JSON, three keys, no `schema_version`, no nesting:

```json
{
  "stats_dir": "S:/SteamLibrary/steamapps/common/FPSAimTrainer/FPSAimTrainer/stats",
  "kovaaks_username": "MingoDynasty",
  "steam_id": "76561197986713986"
}
```

**Unset semantics are deliberately simple:** a missing key, an empty
value, and a missing/unreadable/malformed file all mean the same thing —
*not configured*, feature off. No identity means rank lookups are
disabled (exactly today's empty-string behavior); no usable `stats_dir`
means the app runs empty (below). Malformed files are logged, never
fatal, and rewritten whole on the next save. One structural nuance: the
`stats_dir` bootstrap (below) fires only on a *missing key*, so a
deliberately cleared `""` is never overridden — consumers still treat
the two identically. (A richer
asked-vs-declined lifecycle was part of the detection-first draft and is
deferred with detection — nothing in this proposal prompts the user, so
nothing needs to remember a refusal.)

Hand-editing the file while the app is stopped remains a legitimate
escape hatch; edits while it runs are not picked up (the service caches
in-process — the settings page is the live write path).

### Identity relocation (PR 1)

- `ConfigData` drops `kovaaks_username` and `steam_id`; the five
  chokepoints read through the settings service instead, per-operation —
  so a save on the settings page affects the next lookup without a
  restart.
- `example.toml` drops the two entries (it documents `config.toml` keys
  only).
- Migration is manual, per the single-user no-compat-shims convention:
  the PR description names the two lines to delete from `config.toml`
  and gives the exact `settings.json` content. A forgotten edit fails
  startup with the existing config error — pydantic's unknown-key
  rejection stays, because it is what catches typos in a hand-edited
  file.

### `stats_dir` relocation and nullable startup (PR 2)

- `ConfigData` drops `stats_dir`. The installed `config.toml` becomes
  `port` only.
- **The app starts without a usable stats directory.** When the value is
  unset — or set but not an existing directory (the moved-library case) —
  startup skips the initial stats scan and the file watchdog, logs one
  line naming the configured path, and serves normally: pages render
  with empty data, and Home shows a persistent hint ("No stats directory
  configured — set it in Settings") linking to the settings page. Unset
  and invalid behave identically; today's `SystemExit` path and its
  stderr message are removed, and the startup-contract tests flip
  accordingly (missing `port` still exits; missing `stats_dir` no
  longer does).
- **Startup bootstrap (app-side `stats_dir` detection).** When the
  `stats_dir` key is absent (a missing file counts), startup runs a
  local detection — Steam root from the registry (HKCU `SteamPath`,
  HKLM fallbacks, the same candidate list the installer used), `"path"`
  entries from `steamapps/libraryfolders.vdf`, probe
  `<library>/steamapps/common/FPSAimTrainer/FPSAimTrainer/stats` — and
  writes the first existing directory through the settings service. No
  hit: write nothing and retry next startup, so a dashboard installed
  before KovaaK's self-configures once KovaaK's appears. Silent by
  design — no confirmation step; on a machine with a stale copy in a
  second Steam library the pick can be wrong, which is immediately
  visible (wrong/empty data), fixable on the settings page, and
  properly solved by the follow-on proposal's candidate dropdown. The
  bootstrap runs only from the real server startup path (never at
  import), and the detector is pure enough to unit-test with fixture
  vdf content and temp directories. Because the page writes all three
  keys on every save, a deliberately cleared `stats_dir` is `""` (key
  present) and is never overridden.
- **Installer simplification.** `Find-KovaaksStatsDir`, the `[Y/n]`
  confirm, the manual-entry retry loop, and the stats-dir `Stop-Fatal`
  are deleted; `Write-FirstRunConfig` writes the port-only `config.toml`
  (its `load_config()` round-trip validation stays). Installs become
  fully non-interactive, and the installer never touches
  `settings.json`. This lands a proposal early versus the original
  plan, because the app-side bootstrap makes the installer's detection
  redundant rather than merely relocated.
- `docs/decision_log.md`: dated supersede notes on the 2026-07-19
  first-run-config entry (installer-written config is now `port` only;
  stats-directory detection moved into the app). History kept, per
  convention.

### Settings page (PR 3)

A new page (`/settings`, with a nav entry) showing the three values with
manual entry and a single Save:

- **Validation on save, offline and basic only:** `stats_dir` must be an
  existing directory (the same check startup used to enforce fatally) or
  empty; `steam_id` must be digits-only when non-empty; the username is
  free text. No online verification of any value — confirming a username
  against KovaaK's is detection territory and stays out of this
  proposal.
- **Apply semantics:** identity saves apply live — the save handler also
  calls `start_percentile_warmup_worker()` (idempotent) when a username
  is present, so warmup starts without a restart. A `stats_dir` save
  persists immediately but shows a "restart the dashboard to apply"
  notice whenever the saved value differs from the value the server
  booted with. The app never restarts itself, and there is no live
  re-initialization of the watchdog or in-memory data — that machinery
  is the riskiest code the arc could contain, and a restart costs the
  user one console close and a shortcut click.
- **Callback safety:** the save callback is `n_clicks`-guarded with a
  None-trigger regression test (the known
  initial-call-despite-`prevent_initial_call` hazard — this callback
  writes state).
- The page talks only to the settings service; no endpoint logic in UI
  code, per the UI-boundary convention.

### Non-goals

- No identity auto-detection (the KovaaK's-API-verified kind), no
  candidate dropdowns, and no initial-setup flow — follow-on proposal
  territory (working notes:
  `ignore/design-notes/config-settings-arc.md`). The silent `stats_dir`
  bootstrap above is the one detection this proposal ships: it is
  local-only, consent-free, and replaces the installer's detection
  outright instead of relocating it.
- No asked-vs-declined lifecycle state; nothing in this proposal prompts.
- No About/version UX (separately earmarked; it will later join the page
  this proposal creates).
- No moves for TTLs, timeouts, `percentile_warmup_enabled`, or
  `polling_interval`: escape hatches stay in `config.toml` on the cached
  config object.
- No self-restart, no live `stats_dir` re-initialization, no in-app
  migrations.

## Register of decisions

- R1 — `data/settings.json` is the app-owned user-settings store, written
  only through `settings_service.py`; nothing else ever writes it — the
  installer included. `config.toml` is human-owned, app-read-only (one
  home, one writer).
- R2 — Flat three-key schema, no `schema_version`. Missing key, empty
  value, and unusable file all mean "not configured"; malformed files are
  logged, never fatal. No asked/declined tri-state. Consumers never
  distinguish absent from empty; only the R5 bootstrap does.
- R3 — Identity leaves `ConfigData`; consumers read the settings service
  per-operation (live apply). Manual two-line migration; pydantic's
  unknown-key rejection stays.
- R4 — `stats_dir` leaves `ConfigData`; the app starts and serves without
  a usable stats directory (scan and watchdog skipped, empty pages, Home
  hint to Settings). Invalid behaves as unset; startup no longer exits
  for stats problems. Installed `config.toml` is `port` only.
- R5 — `stats_dir` bootstraps app-side: on startup with the key absent,
  a silent local detection (registry → `libraryfolders.vdf` → path
  probe) writes the first hit through the service; no hit writes
  nothing and retries next startup. No confirmation step. The
  installer's detection, prompts, and stats-dir fatal are deleted;
  installs become fully non-interactive.
- R6 — Settings page with manual entry, single Save, and offline
  validation only: directory-exists for `stats_dir`, digits-only for
  `steam_id`, free-text username. No online verification.
- R7 — Apply semantics: identity live (save also live-starts the warmup
  worker, idempotently); `stats_dir` restart-required, signaled by a
  notice comparing the saved value to the boot value. The app never
  self-restarts.
- R8 — State-writing page callbacks are `n_clicks`-guarded with a
  None-trigger regression test.

## Delivery plan

- **PR 1 — settings store and identity relocation.** New
  `settings_service.py` (store, accessors, tests); `ConfigData` drops the
  two identity fields; the five chokepoint files switch to service reads;
  `example.toml` drops the entries; `docs/architecture.md` module map
  gains the service; manual-migration note in the PR description. Hard
  dependencies: none.
- **PR 2 — `stats_dir` relocation, nullable startup, bootstrap,
  installer simplification.** `ConfigData` drops `stats_dir`; startup
  tolerates unset/invalid (skip scan + watchdog, Home hint, tests
  flip); app-side startup bootstrap detection (fixture-tested);
  installer loses detection/prompts and writes the port-only
  `config.toml`; decision-log supersede notes. Hard dependency: PR 1.
- **PR 3 — settings page.** `/settings` page, validation, apply
  semantics, callback guards and tests. Ships the proposal: distills
  R1–R8's durables into `docs/decision_log.md`, deletes this file,
  updates `docs/roadmap.md` and `docs/product.md`, archives the consumed
  kickoff prompts. Hard dependency: PR 2.

All three PRs run the standard gates; none may call the live KovaaK's API
or read the real registry in tests.
