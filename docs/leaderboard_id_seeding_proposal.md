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

### PR-1: ship a seeded name→ID mapping, and use the benchmark endpoint

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

**The seed merges into the permanent cache at startup.** The runtime
lookup path does not change at all: `get_cached_leaderboard_id` keeps
reading the one permanent mapping cache it reads today. Instead, at app
startup the seed file is folded into that cache in one bulk
read-modify-write (atomic, tolerant of a missing or malformed seed per
cache conventions). The merge rule, per entry:

- a seed name **missing** from the cache is added, tagged
  `source: "seed"`;
- an existing entry whose source is `"seed"` is **refreshed** if the
  shipped value changed, so a corrected seed actually reaches existing
  installs;
- entries learned from the live API are **never touched**.

A copy-only-when-the-cache-is-absent rule would be simpler still, but it
strands every existing install: they already have a cache file, so the
seed entries for newly imported benchmarks would never arrive. Merging
at every startup keeps one source of truth at runtime — which also
matches the likely long-term shape of this cache (a table in a
database, with the seed just rows upserted at startup).

Accepted limitation, same one the cache already has: if KovaaK's ever
re-uploads a scenario under the same name with a new leaderboard ID, the
cached entry keeps winning — true today for every learned entry too. The
escape hatch is deleting the mapping cache file (reads tolerate its
absence; the next startup re-merges the seed).

**Bulk resolution at playlist open.** Even with the seed merged, an
opened playlist can still contain scenarios whose leaderboard ID is
unknown — the main case being an *imported* benchmark playlist that is
not part of the bundled corpus (a new season, or a benchmark hidden
from our bundle), whose scenarios the seed has never seen. Today every
such scenario costs one exact-search call. The change, in the
playlist-open hydration step (`_hydrate_playlist_leaderboard_ids` in
`source/kovaaks/playlist_scenarios_service.py`): when IDs are still
missing after the cache lookup *and* the playlist's sharecode appears in
the bundled Evxl catalog, resolve all of them with a single
`get_benchmark_json` call (saving each mapping with source
`"benchmark"`) instead of one search per scenario. Bundled playlists
rarely reach this path — the seed already covers them. Community
playlists that are not benchmarks have no benchmark ID anywhere, so they
keep the existing fallbacks: total-play hydration (when a username is
configured), then exact search.

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
nothing changes yet — the rank service still returns UNKNOWN before
resolving anything — but the seed removes the only user-dependent step
in ID resolution, which is exactly what PR-2 needs to exist.

**Rejected alternatives.**

- Evxl as the ID source — verified absent at both layers (catalog and
  playlist-by-code).
- Embedding leaderboard IDs in the bundled playlist JSONs — couples the
  playlist schema to the importer and duplicates the same fact across 216
  files; a single seed file is one artifact with one regeneration story.
- Sweeping the benchmark endpoint at app startup instead of shipping a
  seed — ~216 API calls per fresh install against a slow API, versus zero
  with a shipped file.

### PR-2: Total Players without a configured user

**Service.** When no username is configured, `get_scenario_rank_info`
stops returning UNKNOWN immediately. It resolves the leaderboard ID
(the seeded mapping cache, then exact search; total-play hydration is
naturally unavailable), skips the rank fetch entirely, attaches the
leaderboard total through the existing `_with_leaderboard_total`
enrichment, and returns status UNKNOWN with `total_players` populated.
The "KovaaK's username is not configured." message moves from
`error_message` to `warning_message`: once the app deliberately supports
running without a username, an unconfigured username is a chosen,
feature-limiting state rather than a failure, and the UI's established
yellow-warning degradation (introduced for the stale-rank fallback) fits
it better than red.

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
N/A without a user. Totals are fetched lazily per scenario at playlist
open (a one-row leaderboard call each, cached under the existing
168-hour totals TTL) behind the existing pending/progressive UI.
Accepted cost: the first open of a playlist on a username-less install
performs one cheap totals call per scenario.

**The background worker stays username-gated — deliberately.** This rule
is uniform across this proposal (PR-3 included): without a username,
nothing is ever fetched in the background; totals arrive only lazily at
playlist open. Why not warm totals in the background too: the worker's
mission is percentiles for the overview, and without a username there
are no percentiles — totals alone feed only the detail grids. Its
session pipeline is built around username validation and rank fetching,
so a totals-only mode is genuine new branching through the step
machinery, bought for the smallest audience (username-less installs,
usually a transient state), whose lazy cost is already once per scenario
per week behind a progressive UI.

**Home rides along.** Home does no rank fetching or caching of its own:
its Scenario Stats rank line calls the same `get_scenario_rank_info`
service and renders the result through a pure formatter
(`format_scenario_rank` in `source/pages/home.py`). The service change
above therefore reaches Home automatically — the only Home-specific work
is display: its UNKNOWN branch, today a bare `"N/A"`, gains a
totals-aware variant when `total_players` is present, e.g.
`"N/A (18,342 players)"` (exact wording is the implementer's call). One
branch plus a test.

**Docs on ship.** The "Scenario Rank Feature" and "UI Boundaries"
sections of `AGENTS.md` change (username no longer gates all rank
lookups; UNKNOWN rows may carry totals), plus a decision-log entry
distilling the shipped PRs — per the shipping checklist.

### PR-3 (optional): warm imported playlists ahead of the first open

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
leaderboard ID (free from the seed after PR-1), fetches rank (caching
UNRANKED), and warms the total, which is exactly what the detail grid
shows. The unhide call site stays played-only; the overview's needs
have not changed.

Interplay with opening the playlist is already designed for: the worker
waits for interactive quiet between items, so during the import → click
seconds it steps aside and the open's phase-2 fan-out does the
interactive fetching; the worker fills the remainder in idle gaps, and
the two coordinate through the same caches. Worst case is one
duplicated in-flight fetch.

This PR follows the proposal-wide rule stated in PR-2: the background
worker runs only with a configured username. On a username-less install
this PR changes nothing — the worker is not running and the enqueue
no-ops, so importing a playlist still fetches nothing in the background,
and totals arrive lazily at the first open exactly as PR-2 describes.
There is no import-triggered fetching without a username in any PR of
this proposal.

## Delivery plan

- **PR-1** — importer extension emitting `resources/leaderboard_ids.json`
  (plus the regenerated seed itself), startup merge of the seed into the
  permanent mapping cache, benchmark-bulk resolution at playlist open,
  `docs/kovaaks_api_notes.md` update for the benchmark endpoint's
  placeholder-Steam-ID behavior. No dependencies.
- **PR-2** — no-username totals: service change (including the
  error-to-warning message change), playlist row formatter change, Home
  formatter branch, tests. Soft dependency on PR-1: it works without the
  seed, but then a username-less playlist open fans out over the
  exact-search endpoint — ship after PR-1.
- **PR-3 (optional)** — import-time warmup of unplayed scenarios: relax
  the played-only filter at the import enqueue call site. Small (the
  enqueue/worker machinery all exists); soft dependency on PR-1 (without
  the seed, each unplayed scenario costs the worker an exact-search
  call). Independent of PR-2.

## Testing

- PR-1: unit tests for the importer's seed emission (collection across
  payloads, conflict exclusion) against fixture payloads; the startup
  merge (missing name added; learned entry never touched; seed-owned
  entry refreshed when the shipped value changes; missing/malformed seed
  tolerated); the bulk resolution (missing IDs + catalog match → one
  benchmark call → mappings saved; no catalog match → no call).
- PR-2: `get_scenario_rank_info` with no username returns UNKNOWN with
  `total_players` set and a `warning_message` (network mocked); playlist
  formatter renders totals on an UNKNOWN row and still shows N/A for
  Position/Percentile; Home `format_scenario_rank` UNKNOWN-with-total
  variant; regression test for the original report — username-less
  install, seeded mapping, cached total → Total Players column
  populated.
