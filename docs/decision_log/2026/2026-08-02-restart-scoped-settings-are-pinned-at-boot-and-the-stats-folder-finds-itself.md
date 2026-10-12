# 2026-08-02: Restart-Scoped Settings Are Pinned At Boot, And The Stats Folder Finds Itself

Status: Accepted

The app no longer has to be told where the KovaaK's stats folder is. On a
start with nothing ever configured it looks the folder up the way the
installer used to, stores what it finds, and uses it immediately. Settings
that cannot safely change under a running app are frozen when it starts, so a
saved change either applies at once or the Settings page says a restart is
needed. The app also starts and serves with no stats folder at all, showing
empty pages and a hint instead of refusing to run.

Decision — **restart-scoped values are pinned, not re-read.** `stats_dir` is
resolved once by server startup (`resolve_stats_dir`) and every consumer reads
that pin (`get_usable_stats_dir`); a per-operation read would let a mid-run
save move half the app to a new directory while the watchdog and the runs
already in memory stayed on the old one. Whether the directory is usable is
decided as part of that resolution, not per call, so a directory that appears
mid-run — a network library coming online — cannot half-enable an app whose
scan and watchdog were already skipped. A pin that was never resolved (tests,
imports, any entry point that is not the real startup) reads exactly like an
unset value.

Identity is pinned as a **pair**, frozen by the first read that observes a
configured username. Reading both fields together is what stops a lookup from
straddling a save and resolving one player's rank into another's cache entry.
Staying live until that first non-empty read is what lets a first-time
identity set apply without a restart; a later change is restart-scoped
instead, because the warmup worker keeps the context it started with and the
caches it fills are scoped to one identity per process. `is_restart_pending()`
derives the Settings page's notice by comparing the store against both pins,
so the notice describes reality for every consumer and stands until the
restart actually happens. It is derived, never stored. Its look, unruled here
and shipped as orange text, is set by the
[2026-09-15 setup-hints entry](#2026-09-15-setup-hints-wear-the-notice-anatomy);
its trigger and its derivation are unchanged. The app never restarts
itself, and there is no live re-initialization of the watchdog, the warmup
singleton, or the in-memory data — that machinery is the riskiest code this
arc could have contained, and a restart costs one console close and a shortcut
click.

**The app starts without a usable stats directory.** Unset, and set but not an
existing directory (the moved-library case), behave identically: startup skips
the initial scan and the file watchdog, logs one line naming what was
configured, and serves — only `port` is needed to serve pages. Home shows a
hint linking to the settings page. The `SystemExit` that used to guard this is
gone.

**`stats_dir` bootstraps app-side**, replacing the detection deleted from the
installer (see the 2026-08-02 addendum on the 2026-07-19 installer entry
below, which this supersedes for stats-directory detection). On startup with
the key **absent** — a missing file counts — the app collects Steam's install
roots from the registry (`HKCU` `SteamPath`, then both `HKLM` `InstallPath`
views, every hit kept), treats those roots as libraries, adds every `"path"`
value from each root's `steamapps/libraryfolders.vdf`, and probes
`<library>/steamapps/common/FPSAimTrainer/FPSAimTrainer/stats` per unique
library. The first existing directory is written through the settings service,
merged with whatever is already stored. The bootstrap runs before the pin
above, so a first detection serves the boot that made it. A miss writes
nothing and is retried on the next start, so a dashboard installed before
KovaaK's self-configures once KovaaK's appears. A present-but-empty value is
never overridden: that is the user saying "run without run data" on the page,
and the page writes every key on every save precisely so this distinction
survives.

The pick is silent — no confirmation step. On a machine with a stale copy in a
second Steam library it can be wrong, which is immediately visible (empty or
wrong data), fixable on the settings page, and properly solved by the
follow-on proposal's candidate dropdown. The page shipping first is why the
silent write is acceptable at all: the repair surface precedes it.

The vdf is read with the installer's flat `"path"\s*"([^"]*)"` regex,
unescaping `\\`, rather than with the `vdf` PyPI package: no new dependency
for a file read once per start, the upstream package is unmaintained, and the
regex ignores the file's structure by design. It harvests the per-library
object format Steam writes today; a pre-structured file (numeric key to path)
contributes no extra libraries, exactly as the installer behaved, and the
Steam roots themselves are still probed. An unreadable or malformed vdf is
logged and skipped, never fatal. The bootstrap runs only from the real server
startup path, never at import, and the registry read is isolated in one
function so no test ever touches the real registry.

Provenance: same proposal and delivery arc as the entry above (PR #171;
PRs #181, #182, #183, #184).
