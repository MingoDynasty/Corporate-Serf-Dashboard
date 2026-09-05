# Tech Debt

Running list of code smells, minor bugs, refactors, and UI/UX paper cuts worth cleaning up eventually. Items here are not blocking any active milestone; they're tracked here so they don't get lost between sessions.

## How To Use This Doc

- Add an entry whenever a small issue is noticed but isn't worth derailing the current task.
- Audit defect corpora are adopted here, into `## Bugs`: one entry per live
  defect, with pointers to the audit evidence (maintainer ruling, PR #258).
- Keep entries brief: 1-3 lines, with file/line if applicable.
- Group items loosely by category.
- When an item is fixed, remove it. The git history is the audit trail.
- For larger refactors, prefer a proper proposal doc instead of an entry here.

---

## Bugs

The four entries below were established by the two 2026-08-12 audits, which
hold the reproductions, soak measurements, and sequenced fix plans:
`ignore/audits/engineering/2026-08-12-project-audit.md` and
`ignore/audits/runtime/2026-08-12-runtime-soak-data-integrity-audit.md`
(gitignored, main checkout only — deliberately not linked so a fresh clone's
docs link check stays green). Four further defects from the same corpus are
already fixed: the zero-score-PB `ZeroDivisionError` in the watchdog's log math
(PR #254), the two cache defects — colliding cache keys and the invalid-UTF-8
read escape (PR #264) — and the unbounded configured port (PR #266).

### Run files missed until restart on a single failed parse

`source/my_watchdog/file_watchdog.py:136-146` — one fixed 1-second sleep, one
parse attempt, no retry. A CSV still locked by KovaaK's or mid-write when the
attempt fires raises a toast but is never imported until a restart rescans the
directory. The runtime register sequences a stable run/file identity first
(its step 1, explicitly before retries), then readiness detection plus bounded
retry (step 2), and removes the blocking sleep separately (step 6); the
engineering register sequences cache hardening first and pairs the retry with
zero-PB handling.

### Fixed one-second handler sleep serializes ingestion

`source/my_watchdog/file_watchdog.py:136` — every create event holds the
handler thread for a full second, so bursts queue behind it: the 2026-08-12
soak left 391 of 1,000 files unprocessed after a ten-minute adversarial burst
plus settle.

### Startup loss window between the initial scan and the watchdog

`source/app.py:369-386` — a run written after `initialize_kovaaks_data`
finishes scanning but before `observer.start()` is never imported this
session; the soak reproduced it with a synchronized arrival. Restart
reconciles.

### Duplicate create events double-count one logical run

`source/my_watchdog/file_watchdog.py` — the handler has no event dedup, so
duplicate create events and delete/recreate patterns for one logical run file
import it twice (observed in the 2026-08-12 soak).

## Code Smells

## Refactors

### Split Evxl out of the `kovaaks` package

`EvxlPlaylist`/`EvxlPlaylistByCodeResponse` (`source/kovaaks/api_models.py`) and
`EVXL_PLAYLIST_BY_CODE_URL`/`get_evxl_playlist` (`source/kovaaks/api_service.py`)
are a third-party service living in KovaaK's-named modules. Deliberately left
there: `get_evxl_playlist` reuses the private `_get_with_retry` (thread-local
sessions, timeout config, the network-success signal), so a `source/evxl`
package would either reach into a private helper and depend on `kovaaks`
backwards, or require extracting a neutral shared HTTP client first.

Revisit when Evxl gains a **second** runtime endpoint — then extract
`source/http_client.py` and `source/evxl/` together (and update the
architecture.md module map). Not worth it for one fallback call. Note
`scripts/benchmark_importer/models.py` has its own duplicate Evxl models; a
split should decide whether they converge.

## Tooling

### `scripts/**` is exempt from the lint and type gates

`[tool.ruff.lint] exclude = ["scripts/**"]` (frozen decision 3) plus mypy's
`files = ["source"]` leave `scripts/release_job.py` gated only by its unit
tests and `compileall` — and that file picks release tags and is the last
check before an immutable release publishes.

Measured 2026-07-19 during the PR #158 review:

- Ruff, run over all five files with explicit paths, reports **40 findings** —
  mostly `D100`/`D101`/`D103` docstring rules in the two legacy script trees,
  plus `G004` and `PLR0915`. So the exclusion cannot simply be dropped.
- `scripts/release_job.py` contributes exactly **one**: `PLR0913` on
  `validate_release` (7 keyword-only arguments > 5). Settled during the PR #158
  review: keep the signature and silence the rule with a targeted per-file
  ignore. The arguments are all required and explicit, and bundling them into a
  dataclass to satisfy a heuristic would cost call-site clarity for no
  correctness gain. So narrowing the exclusion to the two legacy trees is
  mechanical, not a design question.
- `mypy scripts/release_job.py` is clean, but `mypy scripts` fails on
  `Duplicate module named "models"` — `benchmark_importer/` and `Leaderboard
  Sensitivities/` each have one and neither has an `__init__.py`. That is a
  packaging fix, not type errors.

Measure with explicit file paths. `ruff check --no-force-exclude scripts` is a
**false pass**: `--no-force-exclude` only re-admits paths named explicitly, so
directory traversal still prunes everything under the `scripts/**` exclusion
and exits 0 having checked nothing. `--show-files` lists the five files anyway,
which makes the false pass look convincing.

Revisit when the tooling spec is next opened; changing it was out of scope for
the release-job PR that surfaced it.

### Single-command local quality gate

CI enforces four of the five standard checks (ruff format, ruff lint, mypy,
pytest); `compileall` runs only in the local pre-handoff validation. Add one
local entry point (task runner or script) only if repeatedly typing the five
commands becomes burdensome.

## UI/UX

### Manual-refresh failure color, and the title it depends on

`source/pages/home.py` — a hard refresh failure is red and a served-stale
refresh is yellow, and both are titled "Position refresh failed". Softening the
red to yellow was raised during the notification redesign and deliberately left
open: the color is currently the *only* thing separating the two outcomes, so
softening it without first giving the served-stale toast a title of its own
makes them nearly indistinguishable, which is worse than leaving red alone.
Decide the title first; the color follows. Note Mantine suppresses a
notification's full-height color bar whenever an icon is present, and both of
these carry one, so the color is a 28 px circle rather than a stripe.

### Watch for `is_scenario_in_database` early-return pattern

`source/pages/home.py` previously had a bug where the rank callback short-circuited with `is_scenario_in_database(selected_scenario)`, which silently hid rank data for scenarios the user had not played locally. Fixed in PR #9.

When building new UI features that consume `get_scenario_rank_info(...)`, grep for similar "is this in the local database" guards and confirm they do not inadvertently block lookups for unplayed scenarios.

This is not a current bug; it is a code-pattern reminder so the same mistake does not recur.

### Zero-width `dmc.Space` separators offset a wrapped control row

`source/pages/home.py:1501-1502` (and `:1657`) use `dmc.Space(h="xl")` as
separators inside `direction="row"` flex rows, but `h` sets height — they are
zero-width flex items contributing only the row's own 12px gap. When the row
wraps so that one lands at the start of a line, that line's first control sits
12px right of the row's left edge. Originally measured at a 1280px viewport,
with `Top N scores` at x=278 against the row's 266; PR #199 then changed where
that row wraps, so reproduce it at whatever width now puts a separator first
rather than at that one.

Same defect class as the 32px playlist-filter indent fixed in PR #201, whose
rewrap is what made this visible; left out of #201 because removing the
separators is a judgment call about intended spacing rather than a mechanical
fix. The graph-settings modal that held the other `Space(h="xs")` is gone
(PR #209), so the three above are all that remain.

## Performance

### One global lock serializes every cache file operation

`_CACHE_IO_LOCK` in `source/kovaaks/api_service.py` is taken inside `_read_json`
and `_write_json` themselves, so every cache read and write in the app
serializes through it: the percentile warmup worker, the `playlist-fill-*`
threads, rank-freshness refresh timers, the watchdog, and every request thread.
`_write_json` spans an `fsync`, so a burst of writes stalls every request
thread that touches any cache file — which is exactly how the hydration defect
fixed by the 2026-09-04 decision-log entry produced a 38-second first page
render.

Each individual hold is a single file operation, so one hold cannot stall a page
the way the warmup lock-scope defect did (see the 2026-09-02 decision-log
entry); a tight burst of holds from one thread still can, as the 2026-09-04
entry shows. Found during that investigation and deliberately deferred: folding
an app-wide cache-locking change into a targeted concurrency fix would have made
the diff much harder to review.

### Hydration upserts the leaderboard mapping one call at a time

`hydrate_leaderboard_id_cache` calls `save_leaderboard_id` once per scenario in
the total-play response (~2,500 for one beta tester). Since the 2026-09-04
entry a call whose ID and source are both unchanged writes nothing, which
removed the startup cost, but a first run — or any run that genuinely learns new
IDs — still does one full read-modify-write of the whole ~416 KB mapping per new
entry.

A learning run now also **parses that mapping twice per new entry**: the fast
path's check revalidates the in-memory mirror, the previous call's write has
already moved the file's signature, so `_load_leaderboard_mapping` re-parses,
and the slow path then parses again through `_read_json`. Measured at a
3,000-entry / 426 KB mapping: 300 promotions produce 600 `_read_json` calls at
16.5 ms per call, against 0.06 ms and zero reads on the fast path. So the first
startup after a fresh install — where every seeded row the user has played is
promoted — is a one-off ~20% *slower* than before that entry (44.9s versus
36.9s on the same 2,500-call workload), the price of making every later startup
free.

The fix for both is a batch upsert taking the whole dict and writing once, as
`merge_seed_leaderboard_ids` already does for the bundled seed. Reusing the
just-revalidated mirror as the read-modify-write base would remove the second
parse more cheaply but is **not** the fix: under the mirror's accepted
forged-mtime blind spot that would clobber the file, where today the same blind
spot costs at most a skipped `fetched_at` refresh.

### The playlists overview re-reads the same cache files many times per render

`build_playlist_overview_rows` reads a rank file and a totals file per played
scenario per row, with no in-process memo and no dedup across rows. Measured on
a beta tester's profile (379 unique played scenarios, 797 played entries across
the 230 bundled playlists): 1,595 file opens and 6,377 filesystem operations
for one "show hidden" render, of which 836 opens — 52% — are re-reads of a file
already opened in that same render. With "show hidden" off it is 844 opens.
`WARMUP_REFRESH_INTERVAL_MS = 1_000` in `source/pages/playlists.py` repeats the
whole build once per second while the warmup worker is active. Cheap on a fast
disk, and it was not the cause of the 2026-09-04 startup defect, so it is
recorded rather than fixed. The pattern to copy is `_load_leaderboard_mapping`'s
mtime-revalidated mirror.

## Documentation

### Refresh stale example screenshot

`docs/example.png` — README screenshot from before the rank UI, deliberately
kept until replaced. Recapture next time the app is running with real data.
