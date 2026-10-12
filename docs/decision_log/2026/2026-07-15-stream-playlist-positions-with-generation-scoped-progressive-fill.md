# 2026-07-15: Stream Playlist Positions With Generation-Scoped Progressive Fill

Status: Superseded in part, for the aggregate completion toast alone, by
the
[2026-08-22 in-place-only entry](2026-08-22-the-playlist-fill-reports-degradation-in-place-only.md)
(the fill states degradation in the page's status line and emits no
notification). The fill mechanism, generation scoping, tombstones, and
status settling are unchanged and remain Accepted.

Supersedes: The blocking all-scenarios load and Dash Loading wrapper for the
per-playlist scenario grid. The bounded, grid-owned scrolling decision from
2026-07-06 remains in force.

Decision: Opening `/playlists/<code>` has two phases. Phase 1 paints every row
from local stats plus TTL-ignored rank caches, with explicit per-cell pending
flags for unresolved Position, Total Players, and Percentile values. Phase 2
hydrates leaderboard IDs once, then runs the normal cache/network lookup path
through the existing four-worker fan-out in one daemon-thread fill. Workers
stream complete row dictionaries into a lock-guarded in-memory registry keyed
by a per-open generation token. A one-second, enable-only interval drains those
rows through AG Grid update transactions; row identity is
`generation_token:playlist_order`, so a superseded response cannot update the
current grid.

Starting a fill synchronously cancels every other live generation. Completion
and cancellation become bounded tombstones with final counters, a terminal
state, and an atomic consumed flag. The first terminal tick alone drains final
updates, rebuilds unresolved cancelled rows cache-only, settles the status, and
emits any aggregate completion toast; later ticks only reassert the settled
status. Consumed tombstones drop queued rows and finalization payloads, but stay
in the same eight-item retention set as unconsumed tombstones. Overflow evicts
consumed before unconsumed, oldest first within each class, and the cap is
enforced at every terminal transition.

Pending state is never inferred from null values: resolved `UNRANKED` Position
is valid with a null sort key. Completed/finalized rows clear all pending flags.
Outcomes are counted before row formatting as fresh, `UNKNOWN`, or structurally
`served_stale`; the transient stale marker is never written to the rank cache.
Completion uses the existing red/yellow/silent failure tiers without
per-scenario toast spam. The API coordination signal keeps two monotonic
timestamps: interactive rank activity includes cache hits, while network
success changes only after a real successful HTTP response.

Why: Cold or flaky playlist opens previously hid six locally available columns
behind minutes of blocking API work. Progressive fill makes the training table
useful immediately while preserving the existing cache freshness and lookup
semantics. Generation-scoped row IDs plus consumed tombstones close the races
created by navigation, two tabs, callback responses already in flight, and
DashProxy's spurious initial callback behavior without adding a persistent job
system.

Consequences: The grid no longer uses `dcc.Loading`; animated CSS placeholders
and a `done/total` status provide progress. Clean fills clear the status and stay
silent, degraded fills retain a compact summary, and cancelled fills settle as
interrupted with no cell left pending. The registry is process-local and
single-user: reloads start a new fill, a second tab cancels the first tab's
network work, and completed API calls still warm the normal atomic disk caches.
Shipped in PR #127.
