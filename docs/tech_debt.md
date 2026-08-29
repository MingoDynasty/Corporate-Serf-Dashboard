# Tech Debt

Running list of code smells, minor bugs, refactors, and UI/UX paper cuts worth cleaning up eventually. Items here are not blocking any active milestone; they're tracked here so they don't get lost between sessions.

## How To Use This Doc

- Add an entry whenever a small issue is noticed but isn't worth derailing the current task.
- Keep entries brief: 1-3 lines, with file/line if applicable.
- Group items loosely by category.
- When an item is fixed, remove it. The git history is the audit trail.
- For larger refactors, prefer a proper proposal doc instead of an entry here.

---

## Bugs

The seven entries below were established by the two 2026-08-12 audits, which
hold the reproductions, soak measurements, and sequenced fix plans:
`ignore/audits/engineering/2026-08-12-project-audit.md` and
`ignore/audits/runtime/2026-08-12-runtime-soak-data-integrity-audit.md`
(gitignored, main checkout only — deliberately not linked so a fresh clone's
docs link check stays green). An eighth defect from the same corpus, the
zero-score-PB `ZeroDivisionError` in the watchdog's log math, was fixed by
PR #254.

### Run files missed until restart on a single failed parse

`source/my_watchdog/file_watchdog.py:136-146` — one fixed 1-second sleep, one
parse attempt, no retry. A CSV still locked by KovaaK's or mid-write when the
attempt fires raises a toast but is never imported until a restart rescans the
directory. Both audits name this plus the sleep item below as the corpus's
first fix PR, treating the two as one design problem (readiness detection plus
bounded retry).

### Fixed one-second handler sleep serializes ingestion

`source/my_watchdog/file_watchdog.py:136` — every create event holds the
handler thread for a full second, so bursts queue behind it: the 2026-08-12
soak left 391 of 1,000 files unprocessed after a ten-minute adversarial burst
plus settle. Fix together with the retry item above.

### Startup loss window between the initial scan and the watchdog

`source/app.py:369-386` — a run written after `initialize_kovaaks_data`
finishes scanning but before `observer.start()` is never imported this
session; the soak reproduced it with a synchronized arrival. Restart
reconciles.

### Duplicate create events double-count one logical run

`source/my_watchdog/file_watchdog.py` — the handler has no event dedup, so
duplicate create events and delete/recreate patterns for one logical run file
import it twice (observed in the 2026-08-12 soak).

### Invalid-UTF-8 cache bytes escape the tolerant read boundary

`source/kovaaks/api_service.py:440-447` — `_read_json` catches `OSError` and
`json.JSONDecodeError` but not `UnicodeDecodeError`, so corrupt cache bytes
raise instead of reading as a miss; the soak run showed this can terminate
startup. One-line guard.

### Distinct usernames collide onto one cache path

`source/kovaaks/api_service.py:468-472` — `_safe_cache_key` maps every
non-alphanumeric character to `_`, so usernames like `a.b` and `a_b` share and
overwrite each other's total-play caches (merged and per-page) and rank caches
(reproduced in the engineering audit).

### Out-of-range port crashes with a raw traceback

`source/config/config_service.py:37` accepts any `int` for `port`;
`sock.bind()` then raises `OverflowError` for e.g. 70000, which the
`except OSError` in `source/app.py:164-167` does not catch — the user gets a
traceback instead of the curated startup error naming the setting (reproduced
in the engineering audit).

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

*(none currently tracked)*

## Documentation

### Refresh stale example screenshot

`docs/example.png` — README screenshot from before the rank UI, deliberately
kept until replaced. Recapture next time the app is running with real data.
