# 2026-09-02: Warmup Locks Are Never Held Across Cache I/O

Status: Accepted

The Playlists page could show a loading spinner for up to a minute after
startup, and importing or unhiding a playlist could appear to do nothing for
just as long. A background worker was holding a lock while it read hundreds of
small cache files, and the page needed that same lock to draw its progress
line. The worker now does its file reads with the lock released. It warms the
same scenarios as before, and a playlist you have just imported or unhidden can
now take its turn sooner instead of waiting for the scan to end.

**The invariant.** Neither `PercentileWarmupWorker._condition` nor the
module-global `_worker_lock` may be held across cache file I/O. Both are read
by UI callbacks: `get_percentile_warmup_state` (the Playlists status line and
refresh interval) takes `_worker_lock` and then `_condition`, and
`enqueue_playlist_percentile_warmup` (import, unhide) takes both as well. A
hold that spans per-scenario cache reads therefore blocks page renders, not
just the worker.

**Two sites violated it.** `_next_item` held `_condition` across its whole
skip-drain, which reads two cache files per candidate. This only bites when the
cache is warm: nothing returns early, so the loop walks the entire queue.
Measured at 0.13s for 317 scenarios on a fast SSD and about 60s on a
beta tester's disk, where per-file antivirus scanning makes small random reads
roughly 400x slower. (Attribution corrected by the 2026-09-04 entry: that
tester's reads measure 0.029 ms per open, so the ~60s was not read latency — it
was the hydration write storm running inside the same `elapsed` window. The
lock-scope decision below is unaffected.) A direct callback measurement, taken on the fast SSD with
per-candidate latency injected into `_freshly_satisfied` to model the tester's
disk, recorded 45.1s blocked versus 0.2s once the drain finished. That isolates
the lock and only the lock: the overview's own row build reads two cache files
per played scenario per row on the same disk, so the figure is not evidence
that the tester's page renders promptly after this change. `start_percentile_warmup_worker` held
`_worker_lock` across `_startup_queue()`, which reads two cache files per played
scenario; harmless from `app.py` because it runs before the server accepts
requests, but reachable from the settings save that first supplies a username.

**Shape of the fix.** `_next_item` pops under the lock and evaluates freshness
outside it; the popped name is claimed as `_in_flight` before the lock drops, so
a candidate under evaluation still counts toward `remaining_count` and the batch
cannot read as idle or announce completion mid-drain. The loop re-tests the
queue under the lock before waiting, so an enqueue that notifies while the
worker is evaluating is not lost. `start_percentile_warmup_worker` runs a
claim/park/publish handshake: it claims the start under the lock by setting
`_worker_starting`, releases the lock to enumerate, and publishes in a later
hold. There is no post-enumeration singleton re-check and nothing to discard,
because a second caller arriving during the window returns early instead of
enumerating a queue that would be thrown away. What can arrive in that window
is not a competing starter but an enqueue, which is what the parking below
exists for — the two halves are one protocol and must not be implemented
separately.

**Publication is not a gap.** Releasing the lock across enumeration means an
import or unhide can find no worker to enqueue against, where it previously
just waited for one; dropping it there would defer that playlist's warmup until
the next restart, silently. A `_worker_starting` flag marks the window, codes
arriving in it are parked in `_pending_enqueues`, and the starter adopts them in
the same lock hold that publishes the worker. They are enqueued after
publication, so they prepend ahead of the startup queue.

**Starting is a busy state, not an idle one.** The snapshot carries a
`starting` flag that is true from the moment a start claims the singleton until
its parked enqueues have drained, and the overview reads it as busy. Without
it, a poll landing before publication sees no queue, no in-flight item, and
generation 0, concludes the worker is idle, and disarms its refresh interval —
so nothing then observes the generation bumps that publication and the parked
drain produce, and the page sits on stale percentiles until the next visit. The
flag deliberately outlives publication for the same reason: clearing it at
publication would leave the same window between a freshly published empty
worker and its drain.

**Not fixed here.** `_CACHE_IO_LOCK` serializes every cache file operation
app-wide, but each hold is one file operation rather than a scan; recorded in
`docs/tech_debt.md` under Performance.
