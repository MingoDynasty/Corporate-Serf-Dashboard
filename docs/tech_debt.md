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

### Watch for `is_scenario_in_database` early-return pattern

`source/pages/home.py` previously had a bug where the rank callback short-circuited with `is_scenario_in_database(selected_scenario)`, which silently hid rank data for scenarios the user had not played locally. Fixed in PR #9.

When building new UI features that consume `get_scenario_rank_info(...)`, grep for similar "is this in the local database" guards and confirm they do not inadvertently block lookups for unplayed scenarios.

This is not a current bug; it is a code-pattern reminder so the same mistake does not recur.

## Performance

*(none currently tracked)*

## Documentation

### Refresh stale example screenshot

`docs/example.png` — README screenshot from before the rank UI, deliberately
kept until replaced. Recapture next time the app is running with real data.
