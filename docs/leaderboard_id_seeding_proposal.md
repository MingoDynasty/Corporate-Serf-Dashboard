# Leaderboard ID Seeding And User-Independent Totals

Status: Proposed
Date: 2026-07-19

## Problem

Resolving a scenario name to its KovaaK's leaderboard ID is treated as a
user-dependent operation, and it isn't. That one mismatch causes two
user-visible gaps:

1. **Resolution is expensive for everyone.** The bulk mapper — total-play
   hydration — only returns scenarios the configured user has *played*.
   Every unplayed playlist scenario falls through to
   `search_scenario_exact`, one call per scenario against the exact-name
   scenario search endpoint, which is the slowest and most timeout-prone
   call in the app's KovaaK's surface (see `docs/kovaaks_api_notes.md`).
2. **Without a username, playlists are dead.** `get_scenario_rank_info`
   returns UNKNOWN before resolving anything when no username is
   configured, so a fresh install (no `kovaaks_username`, no `steam_id`)
   shows N/A in every rank column of the Playlists pages. Position and
   Percentile genuinely need a user — but Total Players is a property of
   the leaderboard alone, and could be shown.

## Verified facts (probed live 2026-07-19)

- Evxl is not a source of leaderboard IDs. The bundled catalog
  (`resources/evxl/benchmarks.json`) contains no scenario-level data at
  all (benchmark → difficulties → categories → subcategories, with only
  a `scenarioCount` at the leaf). Evxl's playlist-by-code endpoint
  returns `{scenario_name, play_count}` per scenario — no IDs.
- KovaaK's own `/benchmarks/player-progress-rank-benchmark` returns every
  scenario in a benchmark with its `leaderboard_id`, in one call, and
  accepts the placeholder Steam ID `00000000000000000` — no real user
  identity needed. Verified against benchmark 598 (Sparky Voltaic S1):
  one call, 20 scenarios, each with `leaderboard_id`. The app already has
  a client for it (`get_benchmark_json` in `source/kovaaks/api_service.py`)
  that sends exactly that placeholder. Its only caller today is the
  benchmark importer script, which already fetches this payload for every
  bundled benchmark to build rank thresholds — and discards the
  `leaderboard_id` field.
- The endpoint is keyed by **benchmark ID**, not by playlist sharecode.
  The Evxl catalog maps each of its difficulties' sharecodes to a
  `kovaaksBenchmarkId`, covering the whole bundled corpus (216 playlists,
  2,629 unique scenario names). Arbitrary community playlists have no
  benchmark ID, so the endpoint cannot cover them.
- Leaderboard IDs are stable. The codebase already assumes this: the
  permanent name→ID mapping cache has no TTL, is called "the cheapest and
  most trusted source once learned", and logs conflicts instead of
  overwriting.

## Design

### PR-B: ship a seeded name→ID mapping, and use the benchmark endpoint

**Seed generation is an importer byproduct.** The benchmark importer
(`scripts/benchmark_importer/` — the offline, on-demand maintainer tool
that regenerates `resources/benchmarks/` from the Evxl catalog) already
calls `get_benchmark_json` for every benchmark it processes to build
rank thresholds (`generate_playlist`). Each bundled playlist's scenario
list is itself built from that payload, so the payload the importer is
already holding contains a `leaderboard_id` for every scenario that
lands in the corpus — coverage is complete by construction, with zero
additional API calls. The importer extension collects
`scenario name → leaderboard_id` pairs from those payloads (using the
same names the generated playlists carry) and writes
`resources/leaderboard_ids.json`, a flat `{scenario_name:
leaderboard_id}` object — machine-generated like `resources/benchmarks/`,
never hand-edited. If two benchmarks disagree on an ID for the same name
(should not happen; would be upstream weirdness), the importer excludes
that name and reports it, rather than shipping an ambiguous entry. The
seed refreshes whenever the corpus does, in the same run.

**Runtime fallback layer.** `get_cached_leaderboard_id` consults the
user's permanent mapping cache first, then the seed (loaded once per
process, read-only, tolerant of a missing/malformed file per cache
conventions). The learned cache wins on overlap because it comes from the
live API and can be newer than the shipped seed after an upstream rename.
Seed hits are not copied into the user cache — the in-process dict is
already the cheap path, and copying would freeze seed values past their
next regeneration.

**Bulk resolution at playlist open.** The playlist-open hydration step
(`_hydrate_playlist_leaderboard_ids` in
`source/kovaaks/playlist_scenarios_service.py`) gains a tier: when
scenarios remain unmapped and the playlist's sharecode appears in the
bundled Evxl catalog, make one `get_benchmark_json` call for its
`kovaaksBenchmarkId` and save every returned mapping (source
`"benchmark"`). With the seed shipped, bundled playlists rarely need
this; the tier exists for *imported* benchmark playlists that are not in
the bundle — a new season, or a hidden benchmark — where it replaces N
exact-search calls with one benchmark call. Arbitrary community playlists
(no benchmark ID anywhere) keep the existing path: cache → seed →
total-play hydration (when a user is configured) → exact search.

This runs lazily at playlist open, not eagerly at import time. Import is
itself a network fetch against the timeout-prone playlist endpoint, and
its UI blocks on a spinner for the duration — chaining a second API call
there lengthens the user-blocking window for a benefit invisible at
import time. More decisively, the open-time path must exist anyway
(playlists imported before this feature, or an import whose bulk resolve
failed, still need resolution at open), so an import-time fetch would be
a second code path for the same optimization. At open, the progressive
pending UI already absorbs slow or failed resolution gracefully.

**Effects.** With a username configured: unplayed playlist scenarios stop
hitting the search endpoint (they resolve from the seed), so first opens
of unfamiliar playlists get faster and less flaky. Without a username:
resolution now works at all, which is what PR-C builds on.

**Rejected alternatives.**

- Evxl as the ID source — verified absent at both layers (catalog and
  playlist-by-code).
- Embedding leaderboard IDs in the bundled playlist JSONs — couples the
  playlist schema to the importer and duplicates the same fact across 216
  files; a single seed file is one artifact with one regeneration story.
- Sweeping the benchmark endpoint at app startup instead of shipping a
  seed — ~216 API calls per fresh install against a slow API, versus zero
  with a shipped file.

### PR-C: Total Players without a configured user

**Service.** When no username is configured, `get_scenario_rank_info`
stops returning UNKNOWN immediately. It resolves the leaderboard ID
(permanent cache → seed → exact search; total-play hydration is
naturally unavailable), skips the rank fetch entirely, attaches the
leaderboard total through the existing `_with_leaderboard_total`
enrichment, and returns status UNKNOWN with `total_players` populated and
the existing "KovaaK's username is not configured." `error_message`.

**No new status.** UNKNOWN keeps meaning exactly what it means — the
*rank* is unknown. The total is orthogonal enrichment, same as the
existing rule that percentile is derived, not stored. This avoids
touching the `ScenarioRankStatus` enum (stable JSON values) and the rank
cache (nothing is cached for a user that doesn't exist; the rank fetch
never runs).

**UI.** The playlist row formatter
(`format_playlist_scenario_rank_row`) currently fills Total Players only
for RANKED/UNRANKED rows; it changes to render `total_players` whenever
the value is present, regardless of status. Position and Percentile stay
N/A without a user. The percentile warmup worker stays username-gated —
no background prefetch for an unconfigured install; totals are fetched
lazily per scenario at playlist open (a one-row leaderboard call each,
cached under the existing 168-hour totals TTL) behind the existing
pending/progressive UI. Accepted cost: the first open of a playlist on a
username-less install performs one cheap totals call per scenario.

**Home rides along.** Home's Scenario Stats rank line consumes the same
`get_scenario_rank_info` result through a pure formatter
(`format_scenario_rank` in `source/pages/home.py`), so the service
change reaches it for free. Its UNKNOWN branch — today a bare `"N/A"` —
gains a totals-aware variant when `total_players` is present, e.g.
`"N/A (18,342 players)"` (exact wording is the implementer's call). One
branch plus a test.

**Docs on ship.** The "Scenario Rank Feature" and "UI Boundaries"
sections of `AGENTS.md` change (username no longer gates all rank
lookups; UNKNOWN rows may carry totals), plus a decision-log entry
distilling both PRs — per the shipping checklist.

### PR-D (optional): warm imported playlists ahead of the first open

The import-then-browse flow already has a background hook: a successful
import calls `enqueue_playlist_percentile_warmup` (as does unhiding a
playlist), which batch-prepends the playlist's scenarios to the warmup
worker's queue with move-to-front dedup and wakes it. The gap is one
filter: the enqueue keeps only *played* scenarios
(`_ordered_played_scenarios`), which is the right mission for the
overview but nearly empty for a freshly imported benchmark the user
hasn't trained yet.

The change is to relax that filter for the **import** call site only:
enqueue the full scenario list (played first under the existing
ordering heuristic, unplayed after in playlist order). The worker's
per-item step needs no changes — an unplayed scenario resolves its
leaderboard ID (free from the seed after PR-B), fetches rank (caching
UNRANKED), and warms the total, which is exactly what the detail grid
shows. The unhide call site stays played-only; the overview's needs
have not changed.

Interplay with opening the playlist is already designed for: the worker
waits for interactive quiet between items, so during the import → click
seconds it steps aside and the open's phase-2 fan-out does the
interactive fetching; the worker fills the remainder in idle gaps, and
the two coordinate through the same caches. Worst case is one
duplicated in-flight fetch.

Scoped to the configured-username case. A totals-only worker mode for
username-less installs (the worker is gated off entirely without a
username, including its validation step) is deliberately out: it is the
one piece that would need real new worker branching, and PR-C's
progressive open-time fetch already covers that audience.

## Delivery plan

- **PR-B** — importer extension emitting `resources/leaderboard_ids.json`
  (plus the regenerated seed itself), runtime seed fallback in
  `get_cached_leaderboard_id`, benchmark-bulk tier at playlist open,
  `docs/kovaaks_api_notes.md` update for the benchmark endpoint's
  placeholder-Steam-ID behavior. No dependencies.
- **PR-C** — no-username totals: service change, playlist row formatter
  change, Home formatter branch, tests. Soft dependency on PR-B: it works
  without the seed, but then a username-less playlist open fans out over
  the exact-search endpoint — ship after PR-B.
- **PR-D (optional)** — import-time warmup of unplayed scenarios: relax
  the played-only filter at the import enqueue call site. Small (the
  enqueue/worker machinery all exists); soft dependency on PR-B (without
  the seed, each unplayed scenario costs the worker an exact-search
  call). Independent of PR-C.

(The related build-tooltip/dual-bind work discussed alongside this
proposal ships independently and is not part of it.)

## Testing

- PR-B: unit tests for the importer's seed emission (collection across
  payloads, conflict exclusion) against fixture payloads; runtime
  precedence (learned cache beats seed; seed hit on cache miss; both-miss
  falls through); the bulk tier (unmapped scenarios + catalog match → one
  benchmark call → mappings saved; no catalog match → no call).
- PR-C: `get_scenario_rank_info` with no username returns UNKNOWN with
  `total_players` set (network mocked); playlist formatter renders totals
  on an UNKNOWN row and still shows N/A for Position/Percentile; Home
  `format_scenario_rank` UNKNOWN-with-total variant; regression test for
  the original report — username-less install, seeded mapping, cached
  total → Total Players column populated.
