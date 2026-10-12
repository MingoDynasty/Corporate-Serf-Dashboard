# 2026-09-20: A Rank Above The Known Total Suppresses The Percentile

Status: Accepted

A scenario's position and its leaderboard's player count are fetched and cached
separately, so a current position can be paired with an older, smaller count
and the percentile derived from the pair goes negative. The app now withholds
the percentile whenever the position sits past the count it knows, showing the
two numbers on their own until the count refreshes, which clicking Refresh on
that scenario forces. A user sees that scenario's Position lose its percentile,
and the playlists holding it fall back to the cached-coverage placeholder in
Median Percentile and Lowest Percentile.

Decision: `_with_percentile` derives nothing when `rank > total_players`. It
returns the result unchanged — `rank` and `total_players` both survive,
`percentile` stays `None` — and logs the scenario, leaderboard id, rank and
total at WARNING so the staleness is diagnosable from `data/logs/debug.log`.
That warning is emitted once per leaderboard per rank/total pair, because the
cache-only read path re-derives the percentile on every polling tick and the
playlists overview re-derives it per played scenario: one line in the log
means one condition, not one occurrence.
The guard is strictly `>`: `rank == total_players` is a real last place on the
board and keeps its
[midpoint value](#2026-04-27-use-the-midpoint-percentile-formula).

Why: rank comes from `/leaderboard/scores/global` with `usernameSearch`, whose
`total` counts search matches rather than the board, so the population is a
second unfiltered request cached under `leaderboard_total_cache_ttl_hours`
([one week by default](#2026-04-29-cache-leaderboard-totals-for-one-week)).
Boards are expected to grow, so a cached total is normally a lower bound on the
live one, and `((total - rank + 0.5) / total) * 100` crosses zero as soon as
the rank passes it: a board cached at 500 that grew to 1,200 renders a 900th
placement as `900 of 500 (-79.90% percentile)`. Every path whose rank and total
ages are independent can reach it — the percentile warmup worker, the playlist
scenarios fill, the overview's cache-only reads, a TTL-expired foreground
lookup, the stale-rank fallback, and a clicked Refresh whose total re-read
failed and fell back to the cached count
([2026-09-19](#2026-09-19-a-clicked-refresh-re-reads-the-leaderboard-total)).

Consequences: a suppressed percentile leaves that scenario unresolved for the
playlists overview, so the whole playlist shows the
`{resolved}/{played} cached` placeholder in both percentile columns instead of
a median it cannot support. That is the honest readout — the aggregate
genuinely is not known — but it is visible, and it lasts until the total
refreshes. The placeholder's tooltip suggests opening the playlist, which
doesn't clear it while the total is TTL-fresh, because the playlist's fill
honors that TTL. A clicked Refresh on that scenario does, since it re-reads the
total
([2026-09-19](#2026-09-19-a-clicked-refresh-re-reads-the-leaderboard-total));
otherwise the row waits out `leaderboard_total_cache_ttl_hours`, a week by
default. The suppression also breaks two properties
[2026-07-16](#2026-07-16-warm-playlist-percentiles-with-one-polite-background-worker)
stated for that placeholder, whose display rule it called weaker than the
warmup worker's freshness test and monotonic: a scenario the worker counts as
fresh can still hold a row on the placeholder, and a row that was showing
aggregates can return to it.

Rejected: clamping to `0.0`, or to the value at `rank == total`. Either
invents a number from data already known to be inconsistent, and the invented
floor still feeds the median as though it had been measured. Also rejected:
dropping the total along with the percentile, which discards a count the app
legitimately has and contradicts the principle that a degraded read
[shows no less than the app already knows](#2026-07-12-rank-fetch-failure-degrades-to-the-last-cached-rank).

Not done: refreshing the total when the guard trips. A rank above the total is
good evidence the total is stale. The self-heal would not live in
`_with_percentile`, which stays a pure derivation, but in the network-allowed
enrichment path: `_with_leaderboard_total` bypassing the TTL once when the
cached total sits below the rank, plus `_freshly_satisfied` learning the same
condition so the warmup worker stops skipping the scenario as satisfied. It
covers only a board that grew. If a board ever loses rows, the stale side is
the rank, and a total re-read heals nothing. Suppression is the right floor
either way, which is why the self-heal is a separable follow-up rather than
part of this guard.
