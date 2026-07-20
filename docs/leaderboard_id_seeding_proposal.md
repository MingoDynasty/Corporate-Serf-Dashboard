# Leaderboard ID Seeding

Status: Proposed
Date: 2026-07-19 (narrowed 2026-07-20; the no-username work moved to
`user_independent_totals_proposal.md`, proposed in its own PR; pivoted
2026-07-20 from an aggregate seed file to corpus-embedded IDs after
review)

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

**Each generated playlist carries its own leaderboard IDs.** The
benchmark importer (`scripts/benchmark_importer/` — the offline,
on-demand maintainer tool that regenerates `resources/benchmarks/` from
the Evxl catalog) builds every playlist's scenario list from the
`get_benchmark_json` payload it fetches for that benchmark
(`generate_playlist`) — and that payload carries a `leaderboard_id` for
every scenario. Instead of discarding the ID, the importer embeds it:
each scenario entry in a generated playlist JSON gains a
`leaderboard_id` field, written from the payload the importer is
already holding at that moment. There is no aggregate seed file, no
end-of-run step, and no network call beyond what generation already
makes — a scoped run (`--only`, `--limit`) or a run aborted by the
transient-failure breaker embeds IDs for exactly the playlists it
generated and touches nothing else.

**The corpus is the seed.** Because the IDs live in the same files as
the scenario names, every corpus lifecycle rule applies to both
automatically: staging in `generated/`, human review, activation into
`resources/benchmarks/`, and the importer's retention policies — a
sharecode that leaves the Evxl catalog, turns conflicting, or is
recorded known-bad keeps its last-known-good file, and with it, its
mappings. The shipped corpus and the shipped IDs cannot diverge,
because they are the same artifact. One transitional gap, accepted: a
retained last-known-good file generated before this change carries no
IDs, so its scenarios stay unseeded (falling back to the existing
resolution paths) until its benchmark next regenerates.

**Schema.** The scenario `leaderboard_id` field is optional.
User-imported playlists and pre-change files simply lack it; nothing
outside the bundled corpus is expected to carry it. The bundled corpus
and the app code ship together (the corpus is checked into the repo),
so there is no version-skew concern. The shipping PR regenerates all
216 bundled playlists once so the field is present corpus-wide.

**The bundled IDs merge into the permanent cache at startup.** The
runtime lookup path does not change at all: `get_cached_leaderboard_id`
keeps reading the one permanent mapping cache it reads today. The app
already scans the full bundled corpus at startup; that scan now also
collects the embedded `scenario name → leaderboard_id` pairs, and their
union is folded into the cache in one bulk read-modify-write (atomic).
The merge rule, per entry:

- a bundled name **missing** from the cache is added, tagged
  `source: "seed"`;
- an existing `source: "seed"` entry is **refreshed** if the bundled
  value changed, so corrected IDs actually reach existing installs;
- an existing `source: "seed"` entry whose name is absent from the
  bundled corpus is **removed** — the corpus has stopped asserting it,
  and an upgraded install must not keep resolving a mapping a fresh
  install would not have;
- entries learned from the live API are **never touched**, including
  when the bundled corpus disagrees with them.

If two bundled playlists disagree on an ID for the same name (should
not happen; would be upstream weirdness), the merge excludes that name
and logs a warning rather than asserting an ambiguous mapping. If any
bundled playlist fails to load, the merge still adds and refreshes but
skips removals for that startup — a partial view of the corpus must not
retract mappings the corpus may still assert.

The post-merge invariant, stated carefully: the cache is the union of
learned entries and the bundled IDs, with learned entries taking
precedence on overlap; `source: "seed"` entries never contain a name
the bundled corpus does not currently assert. (Not "the seed-owned
entries are exactly the bundled IDs" — a name that already has a
learned entry never gets a seed-owned row at all.)

A copy-only-when-the-cache-is-absent rule would be simpler still, but it
strands every existing install: they already have a cache file, so the
IDs for newly imported benchmarks would never arrive. Merging at every
startup keeps one source of truth at runtime — which also matches the
likely long-term shape of this cache (a table in a database, with the
bundled IDs just rows upserted at startup).

Accepted limitation, narrower than the cache's general one: if KovaaK's
ever re-uploads a scenario under the same name with a new leaderboard
ID, a **learned** cache entry keeps winning until it is deleted —
seed-owned entries are refreshed by the merge, so only learned rows can
pin a stale value. The escape hatch is deleting the mapping cache file
(reads tolerate its absence; the next startup re-merges the bundled
IDs).

**Effects.** Unplayed scenarios of bundled playlists stop hitting the
search endpoint (their IDs ship with the corpus), so first opens of
unfamiliar playlists get faster and less flaky. Imported playlists
outside the bundled corpus are unchanged: their unmapped scenarios keep
the existing fallbacks (total-play hydration for played scenarios when a
username is configured, then exact search). And ID resolution no longer
requires a user at all, which is what the user-independent totals
proposal builds on.

## Rejected alternatives

- Evxl as the ID source — verified absent at both layers (catalog and
  playlist-by-code).
- An aggregate `resources/leaderboard_ids.json` seed file — this
  proposal's original shape. Rejected after two review passes kept
  finding lifecycle machinery a cross-run artifact requires: full-corpus
  rebuild rules (an incremental run holds payloads only for what it
  regenerated), staging/activation coupling with the reviewed corpus,
  retraction bookkeeping against the importer's retention policies
  (last-known-good files whose codes left the catalog or went
  known-bad), scoped-run and circuit-breaker containment for its
  fetch-on-miss completion, and a reserved staging filename. Embedding
  the IDs in the corpus files eliminates the artifact and the whole
  class of consistency questions.
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

One PR: the importer embedding change with its optional schema field,
the once-regenerated bundled corpus, the startup merge, and a
`docs/kovaaks_api_notes.md` update recording the benchmark endpoint's
placeholder-Steam-ID behavior. No dependencies. The user-independent
totals proposal depends on this PR.

## Testing

- Importer: a generated playlist embeds the payload's `leaderboard_id`
  per scenario (fixture payloads); files without the field — imported
  playlists and pre-change corpus files — still validate (schema
  optionality).
- Startup merge: a missing name is added; a learned entry is never
  touched; a seed-owned entry is refreshed when the bundled value
  changes; a seed-owned entry absent from the bundled corpus is removed
  (the upgrade case); two bundled playlists disagreeing on a name
  excludes it with a warning; an unloadable bundled file still allows
  adds and refreshes but suppresses removals.
