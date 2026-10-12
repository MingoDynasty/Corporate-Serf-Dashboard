# 2026-07-01: Keep Scenario Rank Consistent With Score-Aware Refreshes

Status: Superseded in part, for the exhausted-loop notification ("asks the user
to click Refresh" in Consequences below), by the
[2026-08-03 console-only background diagnostics decision](#2026-08-03-background-rank-diagnostics-are-console-only).
Every other part of this entry remains Accepted.

Supersedes: The `ThreadPoolExecutor(max_workers=2)` high-score refresh and the
decision not to provide manual rank refresh in the original scenario rank
proposal (since distilled into this log and deleted).

Decision: After a local high score, run a bounded score-aware refresh using a
daemon `threading.Timer` chain with delays of 2, 4, 8, 16, and 32 seconds. Accept
the leaderboard as caught up only when its score reaches the two-decimal floor of
the local score. Route every automatic rank-cache write through one process-locked
monotonic writer so a lower score or transient `UNRANKED` result cannot replace a
known better value. The home rank widget passively re-reads rank and total caches
on its existing interval without making network calls, including when those cache
files are older than their normal TTLs. A user-clicked Refresh performs one
authoritative fetch and may deliberately write a lower score or `UNRANKED` result.

Why: KovaaK's leaderboard updates are eventually consistent, so the old single
post-PB fetch could persist lagging data for the week-long cache TTL. Timer
attempts keep delayed work off a bounded executor, centralized write arbitration
prevents loop/read races, and the cache-only UI poll surfaces successful background
writes within about one second. Automatic rechecks after the bounded window would
hammer permanently divergent offline/server-down scores; explicit Refresh gives
the user a bounded escape hatch instead.

Consequences: Automatic rank displays move forward by score and never flicker from
a known rank to `UNRANKED`; explicit Refresh is board-authoritative and can move
backward after a leaderboard reset. Interval ticks resolve only cached leaderboard
IDs, read rank and total files independent of TTL, emit no repeated warning/error
toasts, and make zero KovaaK's requests. A refresh loop that exhausts leaves the
previous cache untouched and asks the user to click Refresh. The retry schedule is
a code constant, not configuration.
