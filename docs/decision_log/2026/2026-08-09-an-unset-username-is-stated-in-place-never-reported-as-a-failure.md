# 2026-08-09: An Unset Username Is Stated In Place, Never Reported As A Failure

Status: Accepted, except that the per-click-id mechanism described below is
superseded by the 2026-08-31
["Repeatable Toasts Replace In Place With A Visible Re-Entry"](#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)
entry: the blue notice is now a single-identity channel that re-pops by showing
a fresh instance id. The ruling — an unset username is configuration state
answered blue, never a red failure — is untouched. The
configured-but-wrong-username case the Scope note below defers is now half
settled by the 2026-08-22
["The Playlist Fill Reports Degradation In Place Only"](#2026-08-22-the-playlist-fill-reports-degradation-in-place-only)
entry, which deleted the playlist fill's aggregate toast — and with it
`_fill_summary_notification`, described below as untouched. Only the Refresh
half of "both generic red toasts" still fires. Everything else here stands.

With no KovaaK's username configured, opening a playlist used to run a
position update that fetched nothing and then popped a red "Position update
incomplete — couldn't update 16 of 16 positions", and clicking Refresh on the
Scenario Performance page answered with a red "Position refresh failed".
Nothing had failed: without a username the app never contacts KovaaK's at all.
The playlist page now skips that pointless update and says "Positions
unavailable — set your KovaaK's username in Settings" in its own status line,
and Refresh answers with a blue notice naming the missing username. Red again
means a lookup that really failed.

Decision: both position surfaces gate on the configured username before doing
any work, and report the unset case as the persistent configuration state it
is.

- `load_playlist_scenario_rows` (`source/pages/playlist_scenarios.py`) checks
  `get_kovaaks_username()` after the playlist resolves and before
  `start_playlist_scenario_fill`. When it is empty the phase-1 rows are
  returned with every pending flag cleared, a `None` generation token, the
  drain interval disabled, and the status line carrying the copy above with
  "Settings" as a `dmc.Anchor` — the same link the Position field's hint uses.
  `_fill_summary_notification` is untouched: the toast cannot fire because the
  fill it summarizes never runs.
- `refresh_rank` (`source/pages/home.py`) checks the same read after its
  `n_clicks` and selected-scenario guards, and returns `no_update` for the
  value plus one blue toast titled "KovaaK's username not set". The value is
  left alone because the field already reads "N/A — set your KovaaK's username
  in Settings".

Why in place on the playlist page and a toast on Refresh: the
[2026-08-03 routing policy](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
sends persistent conditions to in-place UI, and the playlist grid has such a
home. Refresh collides with the same policy's user-initiated branch, and that
branch wins for this event: the in-place hint was already on screen before the
click, so it cannot produce any perceptible response to the click itself, and
a user who clicks Refresh beside the hint plausibly clicked because they had
not read it. To keep every click answerable the toast carries a fresh
per-click id, the same mechanism the green confirmation uses — a stable id
would be swallowed by DMC's `show` while the previous toast is still up.
*(Superseded 2026-08-31: the toast is a channel whose fresh instance id per
emission does the same job, and hides the instance it replaces so repeats do not
stack.)* Blue, not yellow: yellow means degraded data (stale serve, threshold miss, Steam
mismatch), and nothing here is degraded.

Why skipping the fill is safe without a compensating cancel call: skipping
`start_playlist_scenario_fill` also skips its `_cancel_live_fills_locked` side
effect. Identity is process-pinned in one direction only — reads stay live
until the first non-empty username is observed, then freeze — so a tripped
gate means the username has been empty for the whole process, every earlier
playlist open tripped it too, and no live fill can exist.

Why the gate reads settings directly: string-matching the service's
`error_message` would couple routing to display copy, and a typed reason field
on `ScenarioRankInfo` cannot serve a pre-flight gate that must skip the fill
before any lookup runs. Only two sites consume the condition.

Scope: this entry rules on the **unset**-username case only. A username that
is configured but wrong is a different mechanism — it is knowable only per
result, after a network round-trip — and still produces both generic red
toasts today. That case is deliberately deferred and remains open; a typed
reason on `ScenarioRankInfo` is where it should be reconsidered.

Consequences: nothing is superseded. This discharges the kernel the
[2026-08-01 fully-offline entry](#2026-08-01-no-username-stays-fully-offline--user-independent-totals-rejected)
deferred until a settings page existed to point at — quiet state instead of a
red error, no futile fill, and a pointer to how to turn the features on.
Position cells still render N/A throughout: the service's guard fires before
any cache read, so no cached position can contradict the status line.

**Superseded in part, for copy (2026-09-14).** The two strings quoted above
now read "Positions unavailable. Set your KovaaK's username in Settings.",
with the period outside the link, and "N/A · set your KovaaK's username in
Settings". The ruling is unchanged. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out).

Provenance: distilled from `docs/unset_username_position_feedback_proposal.md`
(four decisions ratified 2026-08-09), committed and then deleted in the
shipping PR — git history holds the full text.
