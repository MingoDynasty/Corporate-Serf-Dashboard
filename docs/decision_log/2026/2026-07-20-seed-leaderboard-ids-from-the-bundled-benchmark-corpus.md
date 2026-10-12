# 2026-07-20: Seed Leaderboard IDs From The Bundled Benchmark Corpus

Status: Accepted

Decision: the benchmark importer embeds each scenario's KovaaK's
`leaderboard_id` — from the `/benchmarks/player-progress-rank-benchmark`
payload it already fetches — into every generated playlist JSON, and the app
folds those embedded IDs into the permanent name->ID mapping cache at startup.
The scenario schema field is optional (`Scenario.leaderboard_id`, default
`None`) so imported and pre-change files keep validating, and the runtime
lookup path (`get_cached_leaderboard_id`) is unchanged.

**The corpus is the seed.** The IDs live in the same files as the scenario
names, so every corpus lifecycle rule (staging, review, activation, retention)
applies to both automatically — the shipped corpus and the shipped IDs cannot
diverge because they are one artifact. There is no aggregate seed file.

**Startup merge against the asserted set.** The existing full-corpus scan now
also collects the embedded `scenario name -> leaderboard_id` pairs. Names two
bundled files disagree on are excluded with a warning; the survivors form the
*asserted set*. The merge is one atomic read-modify-write of the mapping cache:

- an asserted name missing from the cache is added, tagged `source: "seed"`;
- a seed-owned entry whose asserted value changed is refreshed, so corrected
  IDs reach existing installs;
- a seed-owned entry whose name is no longer asserted is removed, so an
  upgraded install never resolves a mapping a fresh install would not;
- entries learned from the live API are never touched, and a name that already
  has a learned entry never gets a seed-owned row.

If any bundled file fails to load, the merge still adds and refreshes but
suppresses removals — a partial view of the corpus must not retract mappings it
may still assert.

**Regeneration mechanic.** The generated-file provenance carries a
`schema_version` marker (`generated_from.schema_version`), bumped when the
generated schema changes. `should_skip_generation` then treats a file written
under an older schema as stale, so a plain importer run regenerates the whole
corpus through the benchmark payload cache — without `--force`, which would
refetch every payload live.

Why: resolving a scenario name to its leaderboard ID was treated as
user-dependent, and it isn't. The bulk mapper (total-play hydration) only
returns *played* scenarios, so every unplayed playlist scenario fell through to
the exact-name search endpoint (`/scenario/popular`) — the slowest,
most timeout-prone call in the app's KovaaK's surface, one call per scenario —
and a username-less install could not resolve IDs at all. Shipping the IDs with
the corpus makes first opens of unfamiliar bundled playlists fast and
identity-free.

Accepted limitation: if KovaaK's ever re-uploads a scenario under the same name
with a new leaderboard ID, a *learned* cache entry keeps winning until it is
deleted — seed-owned entries are refreshed by the merge, so only learned rows
can pin a stale value. Escape hatch: delete the mapping cache file; the next
startup re-merges the bundled IDs.

Corpus coverage is CI-enforced (`tests/test_playlist_rekey.py`): every scenario
of every tracked `resources/benchmarks/*.json` carries a non-null
`leaderboard_id`, with an exception list that ships empty.
