# 2026-09-19: A Clicked Refresh Re-Reads The Leaderboard Total

Status: Accepted (amended by
[2026-09-20](2026-09-20-a-rank-above-the-known-total-suppresses-the-percentile.md):
the `rank > total` guard it deferred has landed)

The Refresh button beside the Position field used to fetch a live position and
divide it by a player count that could be a week old, so the percentile it
showed was two numbers from different moments. Clicking Refresh now re-reads
the count as well and recomputes the percentile from both. When the position
refreshes but the count cannot be reached, the app keeps the last count it has
and says so in an orange notification instead of confirming a clean refresh.
Automatic lookups that still go to the network reuse a cached count for a
week, and when their own fetch fails they now fall back to the last count they
have instead of showing none.

**What `force_refresh` means now.** It marks the whole readout
board-authoritative, not just the rank: `get_scenario_rank_info` passes it
through to `_with_leaderboard_total`, which bypasses
`leaderboard_total_cache_ttl_hours` for that call. The flag already bypassed
the rank cache and already permitted a regressing write
([2026-07-01](2026-07-01-keep-scenario-rank-consistent-with-score-aware-refreshes.md));
the denominator was the part it did not cover. The PB-triggered freshness chain
had been forcing the total since 59b2d1d by passing a zero TTL, never recorded
as a decision — an unlogged precedent that this entry adopts and states, and
that call now names the flag instead of the zero.

**Why the one-week TTL still stands elsewhere.**
[2026-04-29](2026-04-29-cache-leaderboard-totals-for-one-week.md) priced the
trade against bursty cold-cache total fetches across every playlist scenario,
and named "a targeted refresh flow" as the remedy if stale totals ever
misled. The Refresh button is that flow: one leaderboard, one extra
unfiltered GET, at a moment the user asked for truth. Every other automatic
path that fetches — the warmup worker, the network phase of the playlist
scenarios fill, a foreground lookup whose rank cache expired — keeps the TTL,
so the knob still governs what it was bought for. A cache-only reader never
had a TTL to keep: the playlists overview, the Home interval tick and the
fill's first paint all pass `allow_network=False`, which serves the rank and
total caches regardless of age so those surfaces can render without touching
the network. A percentile needs an unfiltered count the rank call cannot
supply: with `usernameSearch` the response's `total` is the number of search
matches, not the board population.

**The failed-total fallback is not gated on the flag.** A total fetch that
fails now substitutes the last cached count whatever its age and marks the
result `total_refresh_failed`, for every caller rather than only a clicked
one. One rule, because the cache-only interval path and `_stale_rank_fallback`
already read the total TTL-free, so gating it would have left three callers
disagreeing about the same cache. The consequence for automatic renders: one
whose own total fetch fails now shows the last cached count at any age where
it used to show none. On Home that is the count the next interval tick would
have supplied a second later anyway; in the playlist scenarios fill it is the
one the first paint had already shown. It also supersedes the Consequences line of
[2026-04-27](2026-04-27-make-leaderboard-total-enrichment-best-effort.md), which
described returning the original `ScenarioRankInfo` untouched.

**Orange when the position lands and the count does not.** A clicked refresh
whose total fetch failed answers orange — the partial-success rung
([2026-08-30](2026-08-30-one-severity-color-language-for-inline-notices.md)),
**extended here** from "a follow-up write did not" to any follow-up step, since
what failed is a read. `docs/specs/notifications.md` carries the widened
sentence.
Green would assert a freshness the readout does not have, and the served-stale
yellow would claim the position came from cache when the position is the one
part that did refresh. It shares the per-scenario success channel, so the
green a re-click earns replaces it rather than stacking under a contradicting
verdict. Rejected: dropping the count entirely, which shows less than the app
knows and contradicts
[2026-07-12](2026-07-12-rank-fetch-failure-degrades-to-the-last-cached-rank.md);
a silent green over the cached count, which is the smallest diff but leaves
the button's promise unverifiable; a new inline hint, since the affordance is
already beside the value and the same host is failing seconds apart. No total
request is made at all when the rank fetch itself failed.

**Not fixed here.** `_with_percentile` guarded `total_players <= 0` but not
`rank > total`, so an automatic path, or a click whose total re-read failed
and fell back to the cached count, could still print a negative percentile
from a fresh rank over an older smaller count. The guard shipped separately in
[2026-09-20](2026-09-20-a-rank-above-the-known-total-suppresses-the-percentile.md),
and that pairing now withholds the percentile instead. The click's orange
verdict is unchanged by it: the verdict keys on the failed re-read, not on the
percentile.
