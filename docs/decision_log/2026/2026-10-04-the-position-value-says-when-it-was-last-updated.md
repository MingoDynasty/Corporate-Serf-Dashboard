# 2026-10-04: The Position Value Says When It Was Last Updated

Status: Accepted

Hovering the Position value on the Scenario Performance page now shows when
that position was last updated. A cached position can be a week old, and
nothing on screen told a fresh one from an old one. The age sits beside the
Refresh button, so it comes with a way to act on it. The playlist pages don't
show it, because they have no refresh of their own.

**Settled in chat, 2026-10-04.** The maintainer directed the Scenario
Performance-only scope. The wording is the maintainer's proposal, adopted over
the author's "Checked"; it was not separately ruled.

**Copy.** `Last updated {age} · {timestamp}`, as in `Last updated 3 days ago ·
Oct 1, 2026, 4:18 AM`. It is a status readout, so it takes no period.

**"Last updated", not "Checked".** The time is the rank cache entry's
`fetched_at`, which moves only when a leaderboard read is stored. A fetch that
fails leaves it alone, and so does an automatic read the monotonic writer
refuses
([2026-07-01](2026-07-01-keep-scenario-rank-consistent-with-score-aware-refreshes.md)).
"Checked" describes what the app did and is false in both cases: with KovaaK's
unreachable for a month the app goes on trying, while the position on screen
is a month old. "Last updated" describes the data and holds in every case. It
does not mean the position moved, since a read that returns the same position
restarts the age.

**Scenario Performance only.** There the value sits beside **Refresh**, so an
age is a reason to click or not. The playlist scenario table has no refresh
control, so an age there is information with no action, and opening a playlist
already re-reads every entry past the cache lifetime, so nearly every row
would read under a week. Revisit if that table gains a refresh action. An age
always visible beside the value was rejected too: it would mark every routine
cache read, and the field keeps its marks for failures.

**The time is the position's alone.** The readout joins two caches, and the
leaderboard total carries its own time. A clicked Refresh and a PB catch-up
re-read both together
([2026-09-19](2026-09-19-a-clicked-refresh-re-reads-the-leaderboard-total.md)),
but a lifetime-driven fetch does not, so the two can differ by up to the
lifetime. The hover dates the position and shows no second time.

**The tooltip is part of the layout, not of the value's children.** Home
rewrites the value on every polling tick, and Dash remounts component children
on each write. Built into the children, an open tooltip blinked off in 16 of
72 samples over four seconds, and the value's node was replaced between
samples, which would also drop keyboard focus (headless Edge, 2026-10-04). As
a fixed element whose label a store feeds, it held in 73 of 73, and the value
stays a plain text node. The age is worded in the browser by the helpers the
Last played hover uses, on the same 30-second tick.
