# 2026-08-22: The Playlist Fill Reports Degradation In Place Only

Status: Accepted

Opening a playlist used to end a degraded position update with a red or
yellow toast that repeated a count the page's own status line already showed.
The toast is gone. The status line above the grid, beside the filter box, is
now the only place the fill reports that positions were unavailable or served
from cache, and a clean fill still clears it and stays silent. Nothing else about the update
changes.

Decision: the progressive fill on `/playlists/<code>` states degradation in
its status line and emits no notification. `_fill_summary_notification` and
the `notification-container.sendNotifications` output of
`drain_playlist_scenario_rows` (`source/pages/playlist_scenarios.py`) are
deleted; the callback returns the row transaction and the status only. The
status copy is unchanged, and `tests/test_playlist_pages.py` guards the
callback's declared outputs so the toast cannot return unnoticed.

Why: the toast was non-conformant against the
[2026-08-03 routing policy](2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy.md).
A degraded fill is an automatic failure during passive navigation, which that
entry routes to in-place state with no toast, and its second litmus — already
visible somewhere? then nothing — is answered by the status line, which
carries the same counts ("1 of 3 positions unavailable · 1 from cache —
KovaaK's unreachable") in the filter row directly above the grid the user is
already reading.

Rejected: ratifying the toast as a third named exception to the
persistent-condition rule, beside the Steam-ID mismatch and the startup
playlist warnings. Both of those earn their exception by having no in-place
home; this fill has one, on screen, in the reader's line of sight. The
exception would be defensible only if the status line were easy to miss, and
it is not. Ratifying it would also have made "the policy names it" the test
for conformance rather than the litmus tests themselves.

Supersedes, in part, the
[2026-07-15 progressive-fill entry](2026-07-15-stream-playlist-positions-with-generation-scoped-progressive-fill.md):
its completion-toast clauses only — the first terminal tick no longer "emits
any aggregate completion toast", and "Completion uses the existing
red/yellow/silent failure tiers" no longer describes a notification. The two
phases, the generation-scoped row identity, the cancel-on-start rule, the
tombstone retention and eviction order, the pending-flag rules, the outcome
counting, and the status settling are all unchanged and remain Accepted.

Discharges, for the playlist page only, one half of what the
[2026-08-09 unset-username entry](2026-08-09-an-unset-username-is-stated-in-place-never-reported-as-a-failure.md)
left open. That entry deferred the configured-but-wrong-username case,
noting it "still produces both generic red toasts today". A wrong username
resolves every position to `UNKNOWN`, so the aggregate toast was the
playlist page's half, and deleting it settles that surface: the fill reports
the count in place, like any other degradation.

The other half stands, and this entry rules nothing on it. Clicking Refresh
on Scenario Performance with a wrong username still answers with the generic
red "Position refresh failed" toast, and correctly so — a manual Refresh is a
user-initiated failure, which the routing policy toasts. Neither surface
diagnoses the wrong username: the playlist status line says positions are
unavailable, not why. Naming the condition is still the open question, and a
typed reason on `ScenarioRankInfo` is still where it should be
reconsidered.

Consequences: the app has one fewer toast id, and the notifications
inventory in [specs/notifications.md](../../specs/notifications.md#inventory)
loses its `playlist-progressive-fill-{generation}` row. The fill's
background-thread channel is untouched — it still streams rows into the
registry an interval callback drains, which was never a notification path.

**Superseded in part, for copy (2026-09-14).** The status line quoted above
chains its fragments with middle dots only: "1 of 3 positions unavailable · 1
from cache · KovaaK's unreachable", and "{m} of {total} positions from cache ·
KovaaK's unreachable". The in-place-only decision is unchanged. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out.md).
