# 2026-07-16: Warm Playlist Percentiles With One Polite Background Worker

Status: Superseded in part by the
[2026-08-03 quiet-layer entry](2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy.md):
the fatal-state toast for an unknown username was removed in PR #196; the
overview's status line and a WARNING log carry it. Amended by
[2026-09-20](2026-09-20-a-rank-above-the-known-total-suppresses-the-percentile.md):
the display rule is no longer weaker and monotonic, because a RANKED scenario
whose rank sits above its cached total is worker-fresh yet display-unresolved,
and a resolved row returns to the placeholder when a rewritten rank lands above
the cached total. Everything else stands.

Decision: After startup finishes ingesting local runs, one app-lifetime daemon
worker warms the rank and leaderboard-total caches used by the Playlists
overview. Its queue contains only played scenarios from visible playlists,
grouped to finish recently played playlists first. The worker is sequential,
leaves a two-second politeness gap between network items, and blocks on a
condition variable when idle. Unhiding or importing a playlist prepends that
playlist's played scenarios and wakes the same worker; hiding or deleting does
not cancel already queued work.

Queue duplication is intentionally cheap rather than prevented. Every dequeue
rechecks the disk caches and a session outcome map, so duplicate names from
overlapping playlists, repeated imports, and hide/unhide spam skip without
network work. A scenario is fresh enough for the worker when it has a fresh
UNRANKED cache entry, or a fresh RANKED entry plus a fresh leaderboard total.
The overview's display rule is weaker and monotonic: it may read entries of any
age, but it shows aggregate percentiles only after every played scenario in the
playlist is display-resolved. Until then both aggregate cells show an honest
`n/total cached` placeholder; a fully resolved all-UNRANKED playlist shows
`N/A`, not a pending state.

Interactive rank work always takes priority. The shared API activity signal
keeps separate monotonic timestamps for interactive lookups (cache hits
included) and successful network responses. The worker waits for an
interactive quiet window, while outage backoff wakes early only after evidence
of a real network success. The worker calls the lower-level resolve, rank, and
total operations so it can classify failures without the UI service's UNKNOWN
flattening. Before caching UNRANKED it requires one positive username
validation per session; an API-confirmed unknown username stops the whole
queue and produces one UI notification. Connection errors, 5xx responses, and
post-retry 429s tail-requeue with escalating global backoff; read timeouts and
permanent failures become terminal for that session. Three transient attempts
per name are allowed. A restart reconstructs work from cache freshness rather
than persisting queue state.

The Playlists page reads the worker through an immutable snapshot. While queued
or in-flight work exists it shows `Updating percentile data: N remaining
(~ETA)`, using unique non-terminal names and recent pace; outage backoff adds a
paused/retry time and fatal state remains visible. A one-second interval
rebuilds the normal cache-only overview rows and disables itself only after one
final idle rebuild. `Interval.disabled` has one callback owner. That callback
observes a monotonic enqueue generation and is also driven by the page's row
refresh store, so work enqueued after idle re-arms the browser interval and an
older snapshot cannot disable a newer re-arm. Interval-driven cache reads pass
`record_activity=False`; otherwise the reporting loop would continuously mark
the user active and postpone the worker it reports on.

Why: A cold overview previously showed incomplete percentile aggregates only
for scenarios the user happened to open, which made cross-playlist comparisons
biased and unstable. Bulk warming the full play history would spend API budget
on data no overview consumes, while parallel fetching would add avoidable load.
The played-visible queue plus all-or-nothing display makes each completed value
trustworthy, and the background status makes a 15-minute cold fill visible
without blocking any route.

Consequences: `percentile_warmup_enabled` disables only this worker, and an
empty `kovaaks_username` keeps startup and enqueue hooks fully offline.
Interactive Home and playlist-scenario refreshes remain available. The queue,
pace, backoff, and generation state are process-local; cache files remain the
durable data plane and retain their existing atomic-write and monotonic-rank
rules. A separate background TTL and negative leaderboard-resolution cache are
deferred levers. Shipped across PRs #129, #130, #132, and #133.
