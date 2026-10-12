# 2026-08-03: Background Rank Diagnostics Are Console-Only

Status: Accepted

Supersedes: the "asks the user to click Refresh" consequence of the
[2026-07-01 score-aware refresh entry](#2026-07-01-keep-scenario-rank-consistent-with-score-aware-refreshes).
The rest of that decision — the timer schedule, the two-decimal catch-up floor,
the monotonic writer, the cache-only interval poll, and the board-authoritative
manual Refresh — is unchanged.

When a position lookup fails in the background, the app no longer shows the user
an error message. The failure is written to the console and the log file, and
the position on screen keeps showing the last value the app confirmed. Nothing
is lost or overwritten by the failure, but the app no longer announces it
either: a background failure is now something the user finds in the log, or
infers from a position that did not move after a personal best.

Decision: four background diagnostic error toasts are deleted and their
`logger` siblings retained. Three are in the rank-freshness timer chain in
`kovaaks/api_service.py` — retry exhaustion, the unknown-user stop, and the
unexpected-error safety net — and one is in `my_watchdog/file_watchdog.py`,
where scheduling the refresh itself fails. `api_service.py` loses its
`dash_logger` import and module-global with them; `file_watchdog.py` keeps both
for its run-import failure toast, which this entry does not touch.

Why: these calls were dead code when written — `dash_logger` records emitted
from a plain thread never reached a callback context — and PR #115's queueing
handler made them live without anyone re-deciding whether they should be. What
they actually deliver is a generic red "Error" toast, batched onto the next
Home visit. One channel was reporting two failures of different kinds, and the
reasons for dropping it differ per kind — neither of them is "the chain retries
until it works", which is true of no path here:

- **An exhausted chain has a recoverable outcome, not a self-healing one.**
  The chain stops; nothing reschedules it. What makes the outcome benign is the
  monotonic writer: a failed attempt never replaces the cached position, so the
  widget keeps serving the last confirmed value and the *next successful
  lookup* corrects it — a later PB, a manual Refresh, or a foreground fetch
  once the week-long rank-cache TTL expires (the interval poll is cache-only
  and never triggers one). With no later PB, the displayed position can sit at
  its pre-PB value for that full TTL. That is bounded staleness on a value that
  was correct when written, and it is the honest ceiling on this decision.
- **The unknown-user stop never recovers, and is not claimed to.**
  `_run_attempt` returns without scheduling, and every later PB repeats the
  same failure until the username is fixed on the settings page. It is dropped
  for a different reason: it is a persistent misconfiguration that the
  foreground already reports. Home's rank callback takes `run-events` as an
  input, so the same new run that schedules the chain also triggers a
  network-allowed foreground lookup, which returns `UNKNOWN` carrying
  `KovaaK's username '<name>' was not found.` and toasts it through
  `_emit_rank_messages`. The deleted background toast was a second, later, less
  specific copy of a message the user already receives.

Consequences — the accepted loss is on the exhaustion path: it now has no
user-visible surface at all, so noticing one means reading `data/logs/debug.log`
or the console, or noticing the position did not move. This entry accepts that
rather than solving it. The remedy on the table — a persistent in-place state on
the Position field that explains why the value is what it is — is a UI addition
belonging to the notification redesign, not to a deletion-only change, and is
tracked there (PR #82, the routing-policy and in-place-state decisions). Manual
Refresh, which reports its own failures in the foreground, remains the escape
hatch the superseded entry reserved for a permanently divergent score; what
changes is that the app no longer prompts for it. The regression tests for these
paths assert the retained log records rather than toast delivery.

Scope: this entry decides these four call sites only. The broader notification
redesign — which subsystem owns toasts, the routing policy that produced this
verdict, and the fate of every other toast in the app — was still under debate
in PR #82 when this shipped, and is now recorded in the
[2026-08-03 notification-layer entry](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
above. The deletion was split out (PR #194) because it stands alone: nothing
else reads the removed calls, and the retained logging is untouched.
