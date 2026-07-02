# Playlist Generator Refactor Proposal

Status: Proposed (updated 2026-07-02 after first Q&A round: naming, Evxl
auto-refresh default, circuit-breaker lever, provenance metadata, 4-PR staging)
Date: 2026-07-01
Sequencing: implement after the Scenario Rank Eventual Consistency work fully
lands (PR #38 was 1 of 2; wait for the second PR so `api_service.py` churn does
not collide).

## Goal

Make `scripts/Playlist Generator/script.py` complete a full 217-benchmark run
unattended: no hand-edited counter hacks, no fatal mid-run exceptions from a
single flaky request, resumable after interruption, and able to generate the
playlists that KovaaK's own search endpoint cannot find.

## Why Now

- New Evxl benchmarks were released; `resources/evxl/benchmarks.json` was
  manually refreshed on 2026-07-01 and the script must be re-run for all 217
  sharecodes.
- The 2026-07-01 run died at item 33/217 with an uncaught `ReadTimeout` after
  `_get_with_retry`'s single retry was exhausted twice in a row.
- Historic workaround was editing a `counter < N` skip into the source — the
  commented remnants are still in the committed script.
- Some sharecodes (e.g. `KovaaKsHeadshottingAquamarineCapture`, Setsunai's
  Static Benchmark) return empty from KovaaK's search endpoint, so today they
  can be generated neither by the script nor by the app's UI import.

## Verified Findings (2026-07-01)

These were confirmed empirically during the audit; the design below depends on
them.

1. **Every observed timeout was on KovaaK's `/playlist/playlists?search=`.**
   The benchmark endpoint barely appears in run logs because
   `get_benchmark_json(use_cache=True)` serves from `cache/benchmarks/`.
   Timeouts occurred roughly every 10–25 sequential requests, with no 429 —
   consistent with silent server-side throttling.
2. **The playlist-search call exists only to fetch the display name.** The
   generated file's scenarios and thresholds all come from the benchmark
   endpoint; the search response contributes exactly one string
   (`playlistName`) plus existence confirmation.
3. **Evxl's `GET https://api.evxl.app/kovaaks/playlist-by-code?shareCode=X`
   resolves sharecodes that KovaaK's search misses**, including the Setsunai
   example. Response shape is snake_case (`playlist.playlist_name`,
   `playlist.playlist_code`, `scenario_list[].scenario_name`) plus a
   `playlist_b64` blob — a different schema from KovaaK's
   `PlaylistAPIResponse`.
4. **Evxl has no rank-thresholds endpoint.** The full OpenAPI spec
   (`api.evxl.app/documentation/json`) contains nothing equivalent to KovaaK's
   `player-progress-rank-benchmark`. Thresholds (`rank_maxes`) must keep
   coming from KovaaK's. "Ditch KovaaK's entirely" is not possible.
5. **The script only runs under PyCharm.** `from kovaaks.api_service import…`
   requires `source/` on `sys.path`, which PyCharm injects; plain
   `uv run python script.py` fails with `ModuleNotFoundError`. All paths
   (`../../resources/evxl/benchmarks.json`, `generated/`, and `api_service`'s
   import-time `make_cache()` → `cache/`) resolve against the CWD, which is why
   a stray `cache/` tree exists inside the script folder.
6. **Latent wrong-name bug:** the loop finds the exact `playlistCode` match
   into `playlist`, then ignores it and reads `playlist_response.data[0]` for
   the name (script.py lines 75 and 132). Wrong output if the exact match is
   not first.
7. Evxl's data file contains two duplicate sharecodes
   (`KovaaKsDinkingGearedWindow`, `KovaaKsResettingScaredShotgun`); the script
   keeps the first occurrence.

## Requirements, Non-Goals, and Accepted Tradeoffs

The stable anchor for review passes and implementation.

**Requirements:**

- **R1** — A full run completes end-to-end despite individual transient API
  failures; a failed sharecode is skipped and reported, not fatal.
- **R2** — A systemic outage stops the run early instead of hammering the API
  for the remaining items.
- **R3** — Re-running after an interruption skips already-generated,
  still-current sharecodes without hand-edited counters.
- **R4** — A from-scratch regeneration path exists that trusts no local state
  (manifest or benchmark cache).
- **R5** — Sharecodes missing from KovaaK's search (Setsunai case) generate
  successfully.
- **R6** — The script runs from a plain `uv run` invocation at the repo root;
  no IDE-injected `sys.path` or CWD assumptions.
- **R7** — The run ends with an explicit summary (generated / skipped /
  failed, with sharecodes) and a non-zero exit code if anything failed.
- **R8** — No behavior change for the Dash app's use of shared
  `api_service.py` functions (defaults preserved).

**Non-goals:**

- **N1** — Fixing the app's UI playlist import for search-missing sharecodes
  (see Out of Scope; separate proposal).
- **N2** — Moving generated playlists into `data/playlists/` or auto-copying
  into `resources/playlists/generated/`. The `data/` decision exists
  (decision_log 2026-06-22) but its migration is separate work.
- **N3** — Migrating retries to urllib3 `Retry`
  (`api_retry_urllib3_migration_proposal.md` — remains Deferred; see D2).
- **N4** — Parallelizing requests. Sequential with politeness delay is
  deliberate.

**Accepted tradeoffs:**

- **T1** — Threshold changes made on KovaaK's side under an *unchanged*
  `kovaaksBenchmarkId` are invisible to both the manifest and the benchmark
  cache; only `--force` picks them up. Accepted: Evxl bumps rank data rarely,
  and `--force` is cheap.
- **T2** — Depending on `api.evxl.app` (a community mirror) for name/code
  resolution. If Evxl disappears, the script falls back to being exactly as
  broken as today's KovaaK's-search path — no worse. Accepted for a
  manually-run generator script.
- **T3** — The manifest is per-machine local state (gitignored under
  `generated/`); a fresh clone regenerates from scratch. Accepted — that is
  also the correct behavior.
- **T4** — Duplicate sharecodes in Evxl data keep first-wins with a warning
  (existing behavior).

## Design

Decisions numbered for the review passes. Each is fix-scoped to the script
except D2 and D11 (shared code, drive-by size).

### D1 — Resolve playlist name/code via Evxl `playlist-by-code`

Replace the KovaaK's `/playlist/playlists?search=` call with
`GET https://api.evxl.app/kovaaks/playlist-by-code?shareCode=<code>`.

- Add a script-local pydantic model for the response (in the script's
  `models.py`): `playlist.playlist_name`, `playlist.playlist_code`,
  `scenario_list` — ignore `playlist_b64`.
- The exact-match search loop (and finding #6's wrong-name bug) is deleted
  outright: by-code resolution returns one playlist or an error.
- Scenarios and thresholds continue to come from KovaaK's benchmark endpoint
  via the existing `get_benchmark_json(…, use_cache=True)` (finding #4).
- The Evxl HTTP call goes through a small script-local helper using
  `_get_with_retry` semantics (D2) so it gets the same timeout/retry
  treatment. It does **not** get added to `Endpoints` in `api_service.py` —
  that enum is KovaaK's-only, and the app has no Evxl dependency (N1).

### D2 — Parameterize retry attempts in `_get_with_retry`

Add keyword-only parameters, defaults preserving current behavior exactly
(R8):

```python
def _get_with_retry(url, *, attempts: int = 2,
                    backoff_seconds: Sequence[float] = (0.0,), **kwargs)
```

- `attempts` — total tries for transient failures (current hardcoded 2).
- `backoff_seconds` — sleep before retry *i* (current behavior: immediate
  retry, hence default `(0.0,)`). Indexed with clamping so
  `attempts=4, backoff_seconds=(2, 4, 8)` does what it reads like.
- 429 handling (Retry-After parse + cap) is unchanged per attempt.
- The script calls with `attempts=4, backoff_seconds=(2, 4, 8)`.

Relation to `api_retry_urllib3_migration_proposal.md`: that doc defers
migration until we want "more attempts, real exponential backoff, broader
status codes". This adds the first two — but only as opt-in parameters on the
existing helper, keeping the two deliberate behaviors (Retry-After cap,
recovery logging) the migration would lose. The deferral stands; this does not
re-trigger it. If a third caller ever needs per-endpoint retry *policy*
objects, that is the migration trigger.

Note: with D1 removing the timeout-prone endpoint from the hot path, D2 is a
safety net, not the primary fix.

### D3 — Per-item failure handling with a circuit breaker

- Wrap each sharecode's work in `try/except (requests.RequestException,
  ValidationError)`: log, record the failure, continue (R1).
- Abort the whole run after N **consecutive** failures (R2) — a one-off
  timeout gets skipped; a systemic outage stops the run. N is a CLI lever,
  `--max-consecutive-failures` (default 3), so it can be tuned during testing
  without source edits.
- End-of-run summary: counts and sharecode lists for generated / skipped
  (manifest) / failed; exit 1 if any failures (R7).

### D4 — Rank-count mismatch becomes a per-item failure

The current bare `raise Exception` on
`len(rank_maxes) != len(rankColors)` becomes a recorded per-item failure
(flows through D3). It still logs at ERROR with both counts — it usually means
Evxl and KovaaK's disagree about a benchmark's rank ladder and needs human
eyes, but it must not kill the other 216 items.

### D5 — Politeness delay

`time.sleep(0.5)` between items that made at least one network request (skip
the sleep for fully-cached/manifest-skipped items). The observed
timeout-every-~10-requests pattern (finding #1) looks like throttling;
back-to-back hammering makes it worse.

### D6 — Manifest-based resume and provenance

`generated/manifest.json` maps sharecode → `{file, playlist_name,
kovaaks_benchmark_id, rank_colors, generated_at}`.

- On start, a sharecode is **skipped** iff it has a manifest entry whose
  `kovaaks_benchmark_id` and `rank_colors` match the current
  `benchmarks.json` entry. A changed Evxl entry therefore regenerates
  automatically (this is what makes "I pulled a new benchmarks.json with
  changed benchmarks" work without `--force`); unchanged entries resume for
  free (R3).
- Sharecodes present in the manifest but **removed** from the current Evxl
  data are logged as a warning (orphaned generated files); never deleted
  automatically.
- The manifest is rewritten after each successful item (217 entries — a
  trivial file; no atomicity machinery needed beyond write-then-rename if we
  want to be tidy).
- The filename cannot serve as the resume marker because it derives from the
  playlist *name*, which is only known after the API call — hence a manifest.

**Provenance stamp:** each generated playlist JSON additionally embeds a
`generated_from` object — `{sharecode, kovaaks_benchmark_id, rank_colors,
generated_at, generator: "benchmark_importer"}`. The app's `PlaylistData` is a
plain pydantic v2 `BaseModel`, so unknown keys are ignored on load — this
costs nothing today and is the hook that lets a future app feature detect
stale benchmark data per playlist (see Out of Scope #3). The copies the user
promotes into `resources/playlists/` carry their provenance with them.

### D7 — CLI flags replace the counter hacks; Evxl refresh is the default

**Default startup behavior:** download `https://evxl.app/data/benchmarks`,
compare to `resources/evxl/benchmarks.json`, and if it differs, overwrite the
snapshot and log a diff summary ("Evxl data changed: N entries added/changed/
removed"); if identical, log "Evxl data unchanged". On network failure, warn
and fall back to the committed snapshot. This implements the existing TODO
and, combined with D6, makes a plain script run the staleness check *and* the
incremental update in one step: only entries that actually changed
regenerate. Dirtying the working tree is deliberate — the snapshot update
belongs in the same commit as the regenerated playlists.

`argparse` with:

- `--offline` — skip the live Evxl fetch; use the committed snapshot as-is
  (reproducible runs, working offline).
- `--force` — ignore the manifest **and** pass `use_cache=False` to
  `get_benchmark_json` (R4; covers T1's threshold-drift case).
- `--only SHARECODE` (repeatable) — generate specific sharecodes (replaces the
  hardcoded sharecode pin). `--only X --force` is the "re-check this WIP
  benchmark's thresholds" tool (Viscose-style churn).
- `--limit N` — stop after N generated items (replaces the counter hack).
- `--max-consecutive-failures N` — circuit-breaker threshold (default 3; D3).

Delete the commented counter/sharecode blocks and the dead "debugging only"
TODO blocks.

### D8 — Filename sanitization

Sanitize the playlist name for Windows before writing: strip `<>:"/\|?*`,
trailing dots/spaces. If two different sharecodes sanitize to the same
filename in one run, suffix the later one with its sharecode and log a
warning (never silently overwrite).

### D9 — Runnable from the repo root

- Imports become `from source.kovaaks…` (repo convention), with a two-line
  `sys.path` bootstrap inserting the repo root (derived from `__file__`) so
  both PyCharm and `uv run python "scripts/Playlist Generator/script.py"`
  work.
- All paths derive from `__file__`: `EVXL_BENCHMARKS_JSON_FILE` →
  `REPO_ROOT / "resources/evxl/benchmarks.json"`, output →
  `SCRIPT_DIR / "generated"`.
- Consequence: `api_service`'s import-time `make_cache()` now creates/uses
  `cache/` at the repo root — the *same* benchmark cache the app uses, which
  is a feature (script runs warm the app's cache). The stray
  `scripts/Playlist Generator/cache/` tree can be deleted or merged into the
  root `cache/benchmarks/` once.

### D10 — Rename the directory to `scripts/benchmark_importer`

Two renames folded together:

**The name.** "Playlist Generator" is wrong on both words. The domain
distinction (worth writing into the readme glossary, D12): a *playlist* is a
bare scenario list (what the UI's Import Playlist produces — no rank data); a
*benchmark* is a playlist **plus** rank data (thresholds + colors) — which is
the only thing this script produces. And "generate" implies authoring
something new, when the script fetches and merges existing upstream data —
that is an *import*. So: noun `benchmark`, verb `import` →
`scripts/benchmark_importer`. ("sync" was considered — the manifest makes
runs convergent — but rejected: it overpromises, since removed upstream
entries are warned about, not deleted.) The output directory stays
`generated/`.

**The mechanics.** The space in `Playlist Generator` makes the module
unimportable, which blocks pytest coverage of the new helpers (manifest
logic, sanitization) and forces quoted paths everywhere. Only this script is
renamed — `Leaderboard Sensitivities` stays until it earns the same
treatment. Cost: PyCharm run-config path update.

### D11 — Drive-by fixes in shared code (separate commits)

- `get_benchmark_json` return type hint says `str`, returns a parsed dict;
  also calls `response.json()` twice on a cache miss. Fix both.
- Script logging: keep root at DEBUG but set `urllib3` to WARNING so progress
  lines are readable.

### D12 — Documentation

- Rewrite the script `readme.md`: the playlist-vs-benchmark glossary (D10),
  the full pipeline (Evxl `benchmarks.json` → script → `generated/` +
  manifest → manual copy to `resources/playlists/generated/` → user copies
  chosen playlists to `resources/playlists/` → app restart), the run command,
  all CLI flags, and the Evxl API links (already drafted uncommitted).
- One-line pointer from `docs/architecture.md` to the script (it is currently
  referenced nowhere in `docs/`).
- On ship: distill into a `decision_log.md` entry (Evxl for name/code
  resolution, KovaaK's for thresholds) and delete this proposal.

## Out of Scope — flagged for separate work

1. **App-side Evxl fallback for UI import.** `load_playlist_from_code`
   (`source/kovaaks/data_service.py`) has the same blind spot for
   search-missing sharecodes ("Failed to import playlist" toast). Falling back
   to Evxl when KovaaK's search returns empty would fix it, but puts a
   community-mirror dependency *in the app*, deserves its own small proposal.
   If accepted later, the Evxl client/model from D1 gets promoted from the
   script into `source/kovaaks/` — D1 deliberately keeps it script-local until
   then.
2. **`data/playlists/` migration and auto-copy of generated files.** Covered
   by the Accepted decision "Keep User Runtime Data Under `data/`"
   (decision_log 2026-06-22): bundled playlists stay in
   `resources/playlists/`, future user-imported ones go to `data/playlists/`.
   The manual copy step stays until that migration happens.
3. **In-app stale-benchmark awareness and one-click update.** The target
   workflow, staged so this proposal only pays for the cheap part:
   - *Built now (D6):* every generated file carries a `generated_from`
     provenance stamp (Evxl `kovaaksBenchmarkId` + `rank_colors` + timestamp).
   - *Awareness (future, app-side):* the app fetches the small live Evxl file
     (startup or a "Check for benchmark updates" button), compares each
     loaded playlist's provenance against the current Evxl entry, and badges
     mismatches — "benchmark data has changed upstream". No per-benchmark
     KovaaK's calls, so it stays cheap.
   - *Update (future, app-side):* one-click regenerate per playlist. This
     requires promoting the import core from the script into a
     `source/kovaaks/` service (the script then becomes a thin CLI over it)
     and lands naturally with the `data/playlists/` migration (#2).
   - *Limit:* KovaaK's-side threshold changes under an unchanged Evxl entry
     (WIP benchmarks like Viscose S2) are invisible to provenance comparison
     — same blind spot as T1. The remedy is the explicit per-benchmark
     refresh (`--only X --force` now; a per-playlist Refresh button later).
     No cheap automatic detection exists: verifying thresholds means one
     KovaaK's benchmark call per playlist, so it stays an explicit action.

## Test Plan

- **`api_service` (D2, D11):** extend the existing retry tests — attempts
  respected, backoff schedule consumed with clamping, defaults produce
  today's exact behavior (one immediate retry), 429 path unchanged;
  `get_benchmark_json` single-parse + type fix.
- **Script helpers (needs D10):** manifest skip/regenerate decision matrix
  (missing entry / matching entry / changed `kovaaksBenchmarkId` / changed
  `rank_colors` / `--force`), filename sanitization cases incl. collision
  suffixing, circuit-breaker abort after 3 consecutive failures, summary
  exit codes.
- **Manual gate:** one full `uv run` from the repo root against the live
  APIs; confirm the Setsunai sharecode generates (R5) and the run summary is
  clean.
- Repo gates (`pytest`, `pylint`, `mypy`) per CLAUDE.md on the touched files.

## Implementation / PR Staging

Four PRs, in order, each independently shippable and reviewable:

1. **PR-A (shared code, small):** D2 retry parameters + tests, D11 drive-by
   fixes. No caller behavior changes; app defaults identical. Land first so
   the script PRs rebase on stable helper signatures.
2. **PR-B1 (mechanical, behavior-preserving):** D10 rename to
   `scripts/benchmark_importer`, D9 repo-root runnable (imports, `__file__`
   paths, `sys.path` bootstrap), delete debug cruft, argparse skeleton
   (`--only`, `--limit`), urllib3 log level. Mostly renames and plumbing —
   fast review.
3. **PR-B2 (reliability — "the run completes"):** D1 Evxl playlist-by-code,
   D3 per-item failures + circuit breaker, D4 rank-mismatch downgrade, D5
   politeness delay, D8 filename sanitization. After this PR a full 217-item
   run finishes unattended (R1, R2, R5, R7).
4. **PR-B3 (incremental runs):** D6 manifest + provenance, D7's default Evxl
   refresh + `--offline` + `--force`, D12 readme rewrite + architecture
   pointer. After this PR reruns are cheap (R3, R4).

All wait for Scenario Rank Eventual Consistency PR 2 of 2 to land first
(`api_service.py` conflict avoidance).

## Resolved Decisions (2026-07-02 Q&A round)

- **Circuit-breaker threshold** is a CLI lever (`--max-consecutive-failures`,
  default 3), not a constant — tunable during testing without source edits.
- **Evxl refresh is the default, not a flag.** Fetch live, diff against the
  snapshot, overwrite on change with a logged summary; `--offline` opts out.
  A stale snapshot is the #1 reason to run the script, so the default should
  handle it; D6's per-entry manifest comparison makes the refresh
  automatically incremental. The KovaaK's-side threshold-drift caveat stays
  accepted as T1.
- **urllib3 `Retry` migration order:** unchanged — it does **not** precede
  this work. Robustness comes from retry *policy* (attempts, backoff), which
  D2's parameters deliver identically; the migration swaps mechanism, loses
  the Retry-After cap and recovery logging, and forces a test rewrite for the
  same behavior. If the migration ever happens, D2's parameters map 1:1 onto
  `Retry(total=…, backoff_factor=…)` per that proposal's recipe, so nothing
  here is throwaway.
- **Naming:** `scripts/benchmark_importer` (D10) — noun *benchmark* (playlist
  + rank data), verb *import* (fetch-and-merge, not authoring).

## Open Questions

- **Q1** — Confirm the `benchmark_importer` name (D10) before PR-B1, since
  the rename anchors the PR split.
