# Leaderboard ID Seeding

Status: Proposed
Date: 2026-07-19 (narrowed 2026-07-20; the no-username work moved to
`user_independent_totals_proposal.md`, proposed in its own PR)

## Problem

Resolving a scenario name to its KovaaK's leaderboard ID is treated as a
user-dependent operation, and it isn't. The bulk mapper — total-play
hydration — only returns scenarios the configured user has *played*.
Every unplayed playlist scenario falls through to
`search_scenario_exact`, one call per scenario against the exact-name
scenario search endpoint, which is the slowest and most timeout-prone
call in the app's KovaaK's surface (see `docs/kovaaks_api_notes.md`).
Opening an unfamiliar playlist therefore fans out over the flakiest
endpoint, and a username-less install cannot resolve IDs at all — the
gap the user-independent totals proposal builds on.

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
- Leaderboard IDs are stable. The codebase already assumes this: the
  permanent name→ID mapping cache has no TTL, is called "the cheapest and
  most trusted source once learned", and logs conflicts instead of
  overwriting.

## Design

**Seed generation is a full-corpus importer step.** The benchmark
importer (`scripts/benchmark_importer/` — the offline, on-demand
maintainer tool that regenerates `resources/benchmarks/` from the Evxl
catalog) already calls `get_benchmark_json` for every benchmark it
imports to build rank thresholds (`generate_playlist`), and each bundled
playlist's scenario list is built from that same payload — so the payload
family behind the corpus carries a `leaderboard_id` for every scenario in
it. The seed step is deliberately *not* a per-benchmark side effect of
generation: an incremental run skips benchmarks whose output is already
current (`should_skip_generation`), so a normal run never holds fresh
payloads for most of the corpus. Instead, at the end of every run, the
step enumerates the full active benchmark set (the catalog minus
ledger-blocked and deliberately excluded entries), obtains every payload
from the importer's benchmark-JSON cache (`data/cache/benchmarks/`,
fetch-on-miss through the same retrying client), and rebuilds the
complete `scenario name → leaderboard_id` map from scratch — full
coverage on every run, whether the run regenerated one benchmark or all
of them, at zero or few API calls. If two benchmarks disagree on an ID
for the same name (should not happen; would be upstream weirdness), the
step excludes that name and reports it, rather than shipping an
ambiguous entry.

**The seed stages and activates with the corpus.** The importer writes
its output to a staging area (`scripts/benchmark_importer/generated/`)
for human review, and reviewed playlists are then copied into
`resources/benchmarks/`. The seed follows the same lifecycle: the step
writes the snapshot into the staging area — never directly to
`resources/` — and the same activation step that copies reviewed
playlists also copies `leaderboard_ids.json`, so the shipped seed and
the shipped corpus always come from the same run. Every emitted seed is
a full snapshot, so activation replaces the shipped file wholesale;
an incremental run cannot leave a partial map behind. The shipped file
is a flat `{scenario_name: leaderboard_id}` object — machine-generated
like `resources/benchmarks/`, never hand-edited.

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
- an existing entry whose source is `"seed"` but whose name is absent
  from the shipped seed is **removed** — the seed has stopped asserting
  it (conflict exclusion, or a benchmark leaving the corpus), and an
  upgraded install must not keep resolving a mapping a fresh install
  would not have;
- entries learned from the live API are **never touched**.

A missing or malformed seed file skips the merge entirely — no
additions, refreshes, or removals. After a successful merge the
invariant is simple: the seed-owned entries of the cache are exactly
the shipped seed; learned entries are unaffected either way.

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

**Effects.** Unplayed scenarios of bundled playlists stop hitting the
search endpoint (their IDs come from the seed), so first opens of
unfamiliar playlists get faster and less flaky. Imported playlists
outside the bundled corpus are unchanged: their unmapped scenarios keep
the existing fallbacks (total-play hydration for played scenarios when a
username is configured, then exact search). And ID resolution no longer
requires a user at all, which is what the user-independent totals
proposal builds on.

## Rejected alternatives

- Evxl as the ID source — verified absent at both layers (catalog and
  playlist-by-code).
- Embedding leaderboard IDs in the bundled playlist JSONs — couples the
  playlist schema to the importer and duplicates the same fact across 216
  files; a single seed file is one artifact with one regeneration story.
- Sweeping the benchmark endpoint at app startup instead of shipping a
  seed — ~216 API calls per fresh install against a slow API, versus zero
  with a shipped file.
- Bulk-resolving missing IDs at playlist open by looking the playlist's
  sharecode up in the bundled Evxl catalog and calling the benchmark
  endpoint once. Dropped: the catalog snapshot and the seed are
  regenerated by the same importer run, so any sharecode the bundled
  catalog can resolve is already covered by the seed — except benchmarks
  whose import failed or was deliberately excluded, a handful of
  pathological codes not worth a code path. The case that actually
  occurs (importing a benchmark newer than the release) is not covered
  by a bundled snapshot either way.

## Delivery plan

One PR: the importer's full-corpus seed step (staged with the corpus),
the activated `resources/leaderboard_ids.json` snapshot, the startup
merge, and a `docs/kovaaks_api_notes.md` update recording the benchmark
endpoint's placeholder-Steam-ID behavior. No dependencies. The user-independent
totals proposal depends on this PR.

## Testing

- Importer seed emission: full-corpus rebuild against fixture payloads
  and a fixture payload cache — an incremental run that regenerates a
  single benchmark still emits a seed covering the whole active set
  (cache hits for the rest, fetch on miss); conflict exclusion; the
  snapshot lands in the staging area, not `resources/`.
- Startup merge: a missing name is added; a learned entry is never
  touched; a seed-owned entry is refreshed when the shipped value
  changes; a seed-owned entry absent from the new seed is removed (the
  upgrade case); a missing or malformed seed changes nothing — no
  additions, refreshes, or removals.
