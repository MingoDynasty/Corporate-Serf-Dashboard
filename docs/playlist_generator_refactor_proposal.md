# Playlist Generator Refactor Proposal

Status: Final (2026-07-02) — first Q&A round plus external review rounds 1
(six findings), 2 (eight findings), and 3 (five findings + housekeeping) all
folded in; duplicate-sharecode handling decided same day (D13); no open
questions remain.
Date: 2026-07-01
Sequencing: satisfied — the Scenario Rank Eventual Consistency work fully
landed with PR #40 (confirmed 2026-07-02). Implementation can begin once this
proposal merges to main.

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
- The committed script still contains **active** debugging guards — a hard
  `counter >= 2` stop and a pinned-sharecode filter — plus a commented
  `counter < N` skip from earlier runs. "Run everything" currently requires
  hand-editing the source.
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
7. Evxl's data file contains duplicate sharecodes, and (re-verified
   2026-07-02) both current ones are **conflicting**, not benign echoes:
   `KovaaKsDinkingGearedWindow` is "33 - benchmarks by unnamed33" under both
   Intermediate (id 2287) and Advanced (id 2305) — different rank ladders —
   and `KovaaKsResettingScaredShotgun` is claimed by two unrelated
   benchmarks ("e1se Tracking Routine / Beginner" id 693 vs "i feel evil /
   EVIL" id 2594). The current script's first-wins silently picks one rank
   ladder. The dataset is also volatile: the committed snapshot (196
   difficulties) lags live (218) — a partial serve was committed at some
   point, exactly the event D7's removal guard exists to catch.

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
- **T3** — The manifest is per-machine local state; a fresh clone regenerates
  from scratch. Accepted — that is also the correct behavior. Note: nothing
  under the script's `generated/` directory is gitignored today (it is merely
  untracked); PR-B3 adds an ignore rule for the **whole** directory, since
  outputs are scratch by design — the promoted copies live in the committed
  `resources/playlists/generated/`.
- **T4** — Benchmarks with conflicting duplicate sharecodes are simply
  *absent* from the generated output until Evxl fixes the data (D13).
  Accepted: duplicates are upstream bugs, raised with the Evxl maintainer
  when discovered; correctness beats availability here. (Replaces the
  original first-wins-with-a-warning behavior — see finding #7 for why
  first-wins silently writes wrong rank data.)

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
- The transient-failure log message becomes provider-neutral with attempt
  counts ("Transient GET failure at %s (attempt %d/%d); retrying: %s") —
  the current "KovaaK's … retrying once" wording turns false on both counts
  once D1 routes Evxl calls through the helper and `attempts` can exceed 2.
  Log wording is not behavior; R8 is unaffected.

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
  ValidationError, BenchmarkDataMismatchError)`: log, record the failure,
  continue (R1). `BenchmarkDataMismatchError` is the script-local domain
  exception defined in D4 — without it in the tuple, the rank-count mismatch
  would raise something uncaught and still kill the run.
- Abort the whole run after N **consecutive** failures (R2) — a one-off
  timeout gets skipped; a systemic outage stops the run. N is a CLI lever,
  `--max-consecutive-failures` (default 3), so it can be tuned during testing
  without source edits.
- End-of-run summary: counts and sharecode lists for generated / skipped
  (manifest) / failed / conflicts (D13); exit 1 if any failures or
  conflicts (R7).

### D4 — Rank-count mismatch becomes a per-item failure

The current bare `raise Exception` on
`len(rank_maxes) != len(rankColors)` becomes `raise
BenchmarkDataMismatchError(...)` — a script-local exception defined
specifically so D3's per-item handler catches it (neither
`RequestException` nor `ValidationError` naturally represents this expected
data disagreement). It still logs at ERROR with both counts — it usually
means Evxl and KovaaK's disagree about a benchmark's rank ladder and needs
human eyes, but it must not kill the other 216 items.

### D5 — Politeness delay

`time.sleep(0.5)` between items that made at least one network request (skip
the sleep for fully-cached/manifest-skipped items). The observed
timeout-every-~10-requests pattern (finding #1) looks like throttling;
back-to-back hammering makes it worse.

### D6 — Manifest-based resume and provenance

`generated/manifest.json` maps sharecode → `{file, playlist_name,
kovaaks_benchmark_id, rank_colors, generated_at}`.

- `rank_colors` is stored — in both the manifest and the provenance stamp —
  as an **ordered list of `[name, color]` pairs**, compared
  order-sensitively. Plain dict equality would treat a pure reorder as
  "unchanged", but generation pairs `rankColors` positionally with KovaaK's
  `rank_maxes`, so a reorder silently changes every rank↔threshold
  association and must trigger regeneration.
- On start, a sharecode is **skipped** iff (a) it has a manifest entry whose
  `kovaaks_benchmark_id` and ordered `rank_colors` match the current
  `benchmarks.json` entry, **and** (b) the referenced output file exists and
  passes the integrity check below — a manifest entry whose file was
  deleted, truncated, or corrupted regenerates instead of skipping. A
  changed Evxl entry therefore regenerates automatically (this is what makes
  "I pulled a new benchmarks.json with changed benchmarks" work without
  `--force`); unchanged, intact entries resume for free (R3). 217 small JSON
  parses per run is trivial.
- **File integrity check, in this order:** load the file as *raw JSON* and
  compare the full `generated_from` provenance — sharecode,
  `kovaaks_benchmark_id`, and ordered `rank_colors` — against the manifest
  entry; then validate the playlist shape. The order matters:
  `PlaylistData` *ignores* unknown keys, so validating first would silently
  discard `generated_from` before it can be read, letting wrong-provenance
  files pass. (A script-local wrapper model extending `PlaylistData` with a
  required `generated_from` field does both checks in one validation.)
- **Path confinement:** a manifest entry's `file` must resolve inside
  `generated/` before it is read — or, in the rename case below, deleted. A
  syntactically valid but corrupted or tampered manifest must not be able to
  point the integrity check or the rename cleanup's delete at an arbitrary
  filesystem path.
- Sharecodes present in the manifest but **removed** from the current Evxl
  data are logged as a warning (orphaned generated files); never deleted
  automatically. If a *retained* sharecode's playlist name changes, the old
  file is deleted and the manifest entry updated — the manifest proves the
  sharecode owns that file, so replacing superseded own output is not data
  loss (contrast with the removed-sharecode case above).
- Ordering per item: write the playlist file successfully **first**, then
  commit its manifest entry. The manifest is rewritten after each successful
  item (217 entries — a trivial file) via temp-file + `os.replace` — atomic
  replacement is required, not optional: a crash mid-write must not corrupt
  the resume state. A missing or malformed manifest is warned about and
  treated as empty local state.
- The filename cannot serve as the resume marker because it derives from the
  playlist *name*, which is only known after the API call — hence a manifest.

**Provenance stamp:** each generated playlist JSON additionally embeds a
`generated_from` object — `{sharecode, kovaaks_benchmark_id, rank_colors,
generated_at, generator: "benchmark_importer"}`, with `rank_colors` as the
same ordered pair list as the manifest. The app's `PlaylistData` is a
plain pydantic v2 `BaseModel`, so unknown keys are ignored on load — this
costs nothing today and is the hook that lets a future app feature detect
stale benchmark data per playlist (see Out of Scope #3). The copies the user
promotes into `resources/playlists/` carry their provenance with them.

### D7 — CLI flags replace the counter hacks; Evxl refresh is the default

**Default startup behavior:** download `https://evxl.app/data/benchmarks` and
validate it as a complete `EvxlData` model **before** comparing — an HTTP 200
carrying malformed JSON, an error document, or a partially valid dataset must
never replace the snapshot. The live-vs-snapshot comparison and the
per-entry diff use the **same ordered-pair `rank_colors` representation as
D6** — plain model/dict equality would classify a pure reorder as
"unchanged" here, one layer before D6 could ever see it. If valid and
different, overwrite `resources/evxl/benchmarks.json` atomically (temp file
+ `os.replace`) and log a diff summary ("Evxl data changed: N entries
added/changed/removed"); if identical, log "Evxl data unchanged". On fetch
*or* validation failure, warn and fall back to the committed snapshot. This implements the existing TODO
and, combined with D6, makes a plain script run the staleness check *and* the
incremental update in one step: only entries that actually changed
regenerate. Dirtying the working tree is deliberate — the snapshot update
belongs in the same commit as the regenerated playlists.

**Removal guard:** schema validation cannot prove completeness — an empty
list or a partially valid dataset can still parse as `EvxlData`. The rule
is **all-or-nothing on the candidate**: if the validated live data would
*remove* any sharecode present in the current snapshot, the entire
candidate is rejected — including its additions and changes — the would-be
removals are logged, and the run proceeds against the existing snapshot;
`--accept-removals` accepts the whole candidate. A candidate with only
additions/changes replaces the snapshot automatically. (Partially applying
a mixed candidate — merging its additions while keeping the removed entries
— was considered and rejected: the snapshot must stay an exact mirror of
*some* upstream state, or provenance comparisons stop meaning anything. An
empty or truncated-but-valid response is caught by the same rule, since it
necessarily implies removals.)

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
- `--accept-removals` — allow a live Evxl download that removes sharecodes
  to replace the snapshot (see removal guard above).

Delete the debugging guards (the active hard stop + sharecode pin, plus the
commented counter skip) and the dead "debugging only" TODO blocks. Timing:
this removal lands in PR-B2 together with the failure handling, not in PR-B1
(see Implementation / PR Staging).

### D8 — Filename sanitization and cross-run collision ownership

Sanitization must be Windows-complete, not just illegal-character stripping:

- Strip `<>:"/\|?*` and trailing dots/spaces.
- Windows reserved basenames (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`,
  `LPT1`–`LPT9`, case-insensitive) get the sharecode suffixed.
- An empty sanitized name falls back to the sharecode as the filename.
- Ownership keys are **casefolded**: `Foo.json` and `foo.json` are the same
  file on NTFS, so they must be the same ownership key.

Collision ownership spans runs **without depending on the manifest**: the
ownership map is seeded by scanning existing `generated/*.json` files and
reading each file's embedded `code` field (part of `PlaylistData` from the
start — no provenance stamp required). This makes D8 fully deliverable in
PR-B2, before the manifest exists, and stays correct afterwards: `--only`
and `--limit` runs see files created by any previous run.

The scan must be junk-tolerant, because it runs at startup *before* D3's
per-item handling can catch anything: it explicitly excludes
`manifest.json` (which lives in the same directory and has no `code`), and
a file that fails to parse or lacks a `code` field is logged and treated as
**unowned** — never a startup abort. Overwriting an unowned (corrupt) file
at a target path is permitted with a warning: if it actually belonged to
another sharecode, that sharecode's D6 integrity check will fail provenance
on its next turn and regenerate it, so the system self-heals rather than
accumulating suffixed orphans next to garbage. On collision,
suffix the later sharecode's filename with its sharecode and log a warning —
never silently overwrite a file owned by another sharecode. (A sharecode
replacing its *own* previous file — the rename case — is handled in D6.)

### D9 — Runnable from the repo root

- Imports become `from source.kovaaks…` (repo convention), with a bootstrap
  that — **before importing any `source` module** — inserts the repo root
  (derived from `__file__`) into `sys.path` *and* runs
  `os.chdir(REPO_ROOT)`. The chdir is load-bearing, not cosmetic:
  `api_service.CACHE_DIR` is the CWD-relative string `"cache"` and
  `make_cache()` runs at import time, so `sys.path` alone would still let a
  PyCharm run with a script-dir CWD create a stray script-local cache.
  (Making `CACHE_DIR` absolute in shared code was considered and rejected
  for scope — R8 keeps app behavior untouched.) The script's own paths stay
  `__file__`-derived and are unaffected by the chdir.
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
- `get_benchmark_json`'s cache path uses raw `json.load` on read and a
  non-atomic write. Switch to the existing tolerant `_read_json` (a
  malformed/truncated cache file becomes `None` → refetch, instead of an
  uncaught `JSONDecodeError` outside D3's caught tuple killing a script run)
  and atomic `_write_json`.
- Tolerant reading alone is not enough: syntactically valid but
  wrong-shaped cache content (e.g. `{}`) passes `_read_json` and would
  surface later as a permanently failed item. On a cache hit,
  additionally validate the cached data against `BenchmarksAPIResponse`;
  a `ValidationError` is treated as a cache miss → refetch and overwrite.
  The gate applies only to the *cached* copy — a fresh response that fails
  validation is a real error and surfaces normally. Signature and return
  type are unchanged (validation is a gate, the raw JSON is still what is
  returned).
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

### D13 — Duplicate sharecodes: dedupe if identical, skip-and-report if not

Duplicate sharecodes are not expected; when discovered they are raised with
the Evxl maintainer as upstream bugs. The importer's whole job is to handle
them gracefully — verified 2026-07-02 that both current duplicates are
*conflicting* (finding #7), so graceful cannot mean first-wins:

- At load, classify duplicates over the **raw entries**, before the
  sharecode-keyed dict collapses them:
  - **Identical payload** (same `kovaaksBenchmarkId` + same ordered
    `rank_colors`) → dedupe with a single log line; harmless.
  - **Conflicting payload** → generate nothing for that sharecode; report
    it in the summary's *conflicts* bucket (D3) listing every claimant
    (benchmark, difficulty, benchmark ID, rank ladder), and exit non-zero.
- Why skip instead of first-wins: a missing file is visible and
  recoverable; silently wrong rank thresholds are neither. Remedies while
  waiting on upstream: report to the Evxl maintainer, or hand-edit the
  snapshot and run `--offline`.
- A conflict is **not** a removal for D7's guard, and conflicting
  sharecodes get no D6 manifest entry and no D8 ownership claim.
- Per-difficulty support (one file per `(sharecode, difficulty)` entry) was
  considered and rejected: duplicates are upstream bugs to fix, not a data
  model to accommodate.

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
  `get_benchmark_json` single-parse + type fix; a malformed/truncated
  benchmark cache file refetches instead of raising; a syntactically valid
  but schema-invalid cache (e.g. `{}`) also refetches; cache writes are
  atomic; the transient-failure log carries provider-neutral attempt
  counts.
- **Script helpers (needs D10):**
  - Manifest skip/regenerate decision matrix: missing entry / matching entry
    / changed `kovaaksBenchmarkId` / changed `rank_colors` / missing,
    malformed, or wrong-sharecode output file (regenerates, not skips) /
    `--force`.
  - Malformed or missing manifest → warned about, treated as empty state.
  - Manifest replacement is atomic (temp file + `os.replace`).
  - Filename sanitization cases: reserved basenames (`CON`, `NUL`, …), an
    empty sanitized name (falls back to sharecode), case-insensitive
    collisions (`Foo.json` vs `foo.json`), and a collision with a file owned
    by a previously-generated sharecode → suffixed, never overwritten.
  - Rank-count mismatch records one failed sharecode and the run continues.
  - Malformed or schema-invalid live Evxl data preserves the committed
    snapshot; schema-*valid* live data implying sharecode removals also
    preserves it unless `--accept-removals` is passed.
  - A pure reorder of an entry's `rank_colors` regenerates — tested
    end-to-end: a reordered *live* download must replace the snapshot (D7)
    and then trigger regeneration (D6), not be classified "unchanged" at
    either layer.
  - A manifest entry whose `file` resolves outside `generated/` is rejected
    (never read, never deleted).
  - The ownership scan skips `manifest.json` and treats unparseable or
    `code`-less files as unowned without aborting startup.
  - A mixed live candidate (additions *and* removals) is rejected in full
    without `--accept-removals`; an additions/changes-only candidate
    replaces the snapshot automatically.
  - An identical-payload duplicate sharecode dedupes to one generated file;
    a conflicting duplicate generates nothing, lands in the conflicts
    bucket with a non-zero exit, gets no manifest entry, and is not
    counted as a D7 removal.
  - Circuit-breaker abort at the configured consecutive-failure threshold;
    summary exit codes.
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
   paths, `sys.path` bootstrap), urllib3 log level. The active debugging
   guards (hard stop + sharecode pin) stay untouched — the committed script
   keeps processing one pinned item, so this PR cannot regress into the fatal
   full-run timeout before failure handling exists. Mostly renames and
   plumbing — fast review.
3. **PR-B2 (reliability — "the run completes"):** D1 Evxl playlist-by-code,
   D3 per-item failures + circuit breaker, D4 rank-mismatch domain exception,
   D5 politeness delay, D8 filename sanitization with cross-run ownership
   (fully deliverable here — ownership scans existing output files' `code`
   fields, no manifest dependency), D13 duplicate classification with the
   conflicts summary bucket, and — only now that failure handling
   exists — removal of the debugging guards plus the argparse flags
   (`--only`, `--limit`, `--max-consecutive-failures`). This PR owns the
   default-behavior change from one pinned item to all 217. After it, a full
   run finishes unattended (R1, R2, R5, R7).
4. **PR-B3 (incremental runs):** D6 manifest + provenance, D7's default Evxl
   refresh + removal guard + `--offline` + `--force` + `--accept-removals`,
   the gitignore rule for the script's `generated/` directory (T3), D12
   readme rewrite + architecture pointer. After this PR reruns are cheap
   (R3, R4).

The original precondition — waiting for the Scenario Rank Eventual
Consistency PRs — is satisfied (PR #40 confirmed as the final one); the only
remaining gate is this proposal merging to main.

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

### External review round (2026-07-02)

All six findings of the external proposal review accepted (the review doc is
ephemeral per the handoff-doc convention; findings are distilled here):

- **PR-B1 scope corrected** — the committed script's guards are *active*, so
  removing them was never behavior-preserving; guards stay through B1, and
  their removal + the argparse flags move to B2 alongside the failure
  handling (fixes a staging contradiction that would have reintroduced the
  fatal full-run timeout).
- **Cross-run collision ownership** (D8) — the collision map is seeded from
  manifest entries, closing the manifest-skipped-A / new-B overwrite hole.
  *(Superseded in round 2: ownership now derives from output files'
  embedded `code` fields, with no manifest dependency.)*
- **Resume marker hardened** (D6) — skip requires an intact,
  provenance-matching output file, not manifest metadata alone; manifest
  writes are atomic with defined file-then-manifest ordering; malformed
  manifest → empty state with a warning.
- **Rank-mismatch exception typed** (D3/D4) — `BenchmarkDataMismatchError`,
  explicitly in the per-item caught tuple.
- **Evxl download validated before snapshot replacement** (D7) — schema
  validation + atomic replace; fallback on fetch or validation failure.
- **Gitignore gap closed** (T3) — `generated/` is untracked, not ignored;
  PR-B3 adds the rule.

Refinements over the review's recommendations: a rename within the *same*
sharecode deletes the superseded file (manifest proves ownership) rather
than accumulating orphans; the whole `generated/` directory is ignored, not
only the manifest, since promoted copies live in
`resources/playlists/generated/`.

### External review round 2 (2026-07-02)

Eight findings (five from the review doc, three PR-inline), all accepted:

- **D9 CWD dependence** — `sys.path` alone doesn't move the cache;
  `CACHE_DIR` is CWD-relative and `make_cache()` runs at import. Fix: the
  bootstrap runs `os.chdir(REPO_ROOT)` before importing `source` modules.
  Making `CACHE_DIR` absolute in shared code was rejected for scope (R8).
- **D8/staging contradiction** — cross-run ownership originally leaned on
  the manifest, which arrives one PR later. Fix (better than either option
  offered): ownership permanently derives from existing output files'
  embedded `code` field — D8 loses its manifest dependency entirely and is
  fully deliverable in PR-B2.
- **Malformed benchmark cache** — raw `json.load` in `get_benchmark_json`
  raises `JSONDecodeError` outside D3's caught tuple. Fix in D11/PR-A:
  tolerant `_read_json` (→ refetch) + atomic `_write_json`.
- **Manifest path confinement + full-provenance compare** (D6) — a
  corrupted-but-valid manifest must not read or delete arbitrary paths;
  integrity checks compare complete provenance, not just sharecode.
- **Windows filename completeness** (D8) — reserved basenames, empty
  sanitized names, casefolded ownership keys; tests added.
- **Evxl completeness beyond schema** (D7, PR-inline) — removal guard: live
  data implying sharecode removals keeps the snapshot unless
  `--accept-removals`; catches empty/partial-but-valid responses.
- **Provenance read order** (D6, PR-inline) — raw JSON (or a wrapper model
  with required `generated_from`) *before* `PlaylistData` validation, which
  would otherwise silently drop the stamp.
- **`rank_colors` ordering** (D6, PR-inline) — stored/compared as an ordered
  pair list; dict equality would miss reorders that repair against the
  positional `rank_maxes` pairing.

Housekeeping from the same round: the Sequencing precondition is marked
satisfied (PR #40 confirmed as EC 2/2).

### External review round 3 (2026-07-02)

Five findings plus two housekeeping items, all accepted:

- **Ownership scan robustness** (D8) — the `generated/*.json` scan would
  have consumed its own `manifest.json` (no `code` field) and could abort
  startup on any truncated output file, since it runs before D3's per-item
  handling. Fix: exclude the manifest explicitly; unparseable or
  `code`-less files are logged and treated as unowned. Refinement beyond
  the review: overwriting an unowned corrupt file is *permitted* (with a
  warning) rather than suffixed around — a wrongly overwritten file's true
  owner fails its D6 provenance check and regenerates, so the system
  self-heals instead of accumulating suffixed orphans beside garbage.
- **Ordered comparison extended to the live diff** (D7) — round 2 made the
  D6/manifest comparison order-sensitive but left D7's live-vs-snapshot
  diff on model equality, which would classify a pure `rank_colors`
  reorder as "unchanged" one layer earlier. Both layers now use the same
  ordered-pair representation; end-to-end reorder test added.
- **Cache shape gate** (D11) — `_read_json` tolerance only covers invalid
  JSON; a valid-but-wrong-shape cache (`{}`) would become a permanently
  failed item. Cached benchmark data now validates against
  `BenchmarksAPIResponse` before acceptance; invalid shape = cache miss →
  refetch. Fresh responses are not gated.
- **Removal guard made explicitly all-or-nothing** (D7) — the round-2
  wording was contradictory for mixed candidates (removals + additions).
  Any removal now rejects the entire candidate until `--accept-removals`;
  partial application was considered and rejected (the snapshot must
  mirror an actual upstream state).
- **Provider-neutral retry logging** (D2) — "KovaaK's … retrying once"
  becomes attempt-counted, provider-neutral wording, since D1 routes Evxl
  through the same helper and attempts can exceed 2.
- Housekeeping: the staging footer no longer claims all PRs wait on the
  Scenario Rank work (contradicted the satisfied Sequencing header), and
  round 1's collision-ownership bullet is marked superseded by round 2's
  file-scan design.

### Duplicate-sharecode decision (2026-07-02)

Maintainer ruling: duplicate sharecodes are upstream Evxl bugs — raise them
with the Evxl maintainer; the importer only needs to handle them
gracefully. An empirical check found both current duplicates are
*conflicting* (finding #7), so the original T4 (first-wins with a warning)
was replaced by D13: dedupe identical payloads, skip-and-report conflicting
ones in a dedicated summary bucket. Per-difficulty `(sharecode,
difficulty)` support was considered and rejected. The same check exposed
that the committed snapshot (196 difficulties) lags live Evxl (218) — a
partial serve was committed; re-pull before the next run (post-refactor,
the D7 removal guard makes this loud instead of silent).

## Open Questions

None. Q1 (the `benchmark_importer` name) was confirmed by the maintainer on
2026-07-02, independently endorsed by the external review.
