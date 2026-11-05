# 2026-11-05: A Fresh Total A Later Rank Outruns Is Re-Read Once

Status: Accepted

A scenario whose leaderboard position had passed the player count cached for
it lost its percentile, and the playlists holding it showed the cached-coverage
placeholder for up to a week. Now the next lookup that may reach KovaaK's
re-reads that count once instead of waiting out its week, so opening the
playlist, or the background warmup at the next start, brings the percentile
back on a board that grew. When a count read after the position still sits
below it, the position is the stale number, so the app stops asking and waits
for the position to refresh.

Decision: a fetching lookup reads the leaderboard total with its TTL bypassed
when `_total_trails_rank` holds: the result is RANKED with a rank and a
`fetched_at`, the TTL-fresh cached total sits below the rank (strictly, as the
[2026-09-20 guard](2026-09-20-a-rank-above-the-known-total-suppresses-the-percentile.md)
compares), and the totals file's mtime, the clock its TTL runs on, is earlier
than the rank's `fetched_at`. `_leaderboard_total_ttl_hours` makes that call
for both fetching readers of the total: `_with_leaderboard_total` on its
unforced path (a Run History lookup, the playlist scenarios fill's network
phase, a TTL-expired foreground lookup) and the percentile warmup worker's
`process_warmup_item`. It logs the bypass once at INFO, with the rank and the
total. `_freshly_satisfied` applies the same predicate, so the worker dequeues
such a scenario as unsatisfied instead of skipping it as fresh. A re-read that
lands stores a total newer than the rank, so the bypass runs once per stored
rank, not once per lookup. A failed re-read degrades as every failed total read
does: the last cached total, the percentile still suppressed, and
`total_refresh_failed` set, which only a clicked Refresh reads; the next
fetching lookup tries again, as it would for an expired total. Cache-only reads
(`allow_network=False`) are unchanged and never fetch, and `force_refresh`
already bypasses the TTL.

Why: the 2026-09-20 guard made the readout honest but long-lived. With the
total TTL-fresh nothing automatic re-read it, so the placeholder's own remedy,
"Open the playlist to fetch it now", did nothing for up to
`leaderboard_total_cache_ttl_hours`, and only a clicked Refresh cleared it.
Boards are expected to grow, so a rank above a total stored before it is good
evidence the total is the stale side. Ordering the two by time is what makes
the bypass run once: a pair the re-read cannot heal, where a board lost rows
and the stored rank is the stale side, would otherwise spend a total request on
every lookup of that scenario, against the long-lived rank cache's purpose of
keeping ordinary scenario switching off the leaderboard endpoints.

Consequences: for a board that grew, opening the playlist clears the
placeholder again, because the fill's network phase takes the bypass, and so
does the warmup worker's next pass over the scenario, at startup or after an
import or unhide. The Run History position line gets its percentile back on its
next lookup that may fetch. Nothing new is shown while the total is re-read: it
rides lookups that already wait on the network. A pair the re-read cannot heal
keeps the 2026-09-20 behavior, suppressed until a clicked Refresh, a rank
refresh, or the total's TTL, and the worker counts it fresh again, so the
[2026-07-16](2026-07-16-warm-playlist-percentiles-with-one-polite-background-worker.md)
amendment that a worker-fresh scenario can hold a row on the placeholder still
holds for that pair.

Rejected: re-reading on every lookup while the rank exceeds the total, the
unbounded case above. Also rejected: starting a re-read from the cache-only
readers (the overview, the Run History interval tick, the fill's first paint),
which are network-free by contract.

Not done: `_has_displayable_percentile`, the warmup queue's ordering key, still
counts a trailing pair as displayable, so such a scenario is queued behind the
ones with no percentile at all rather than among them.
