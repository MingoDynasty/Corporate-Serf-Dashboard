# 2026-09-19: A Query Parameter Selects A Control, It Does Not Suspend Its Memory

Status: Accepted

Clicking a scenario in a playlist now counts as choosing it. Before, arriving
at Scenario Performance from a playlist link put the page into a mode where
nothing the user picked was remembered, so going back to the page snapped both
dropdowns to a selection that could be weeks old. The page now remembers a
selection however it was made, and the navbar link returns to the latest one.

**The bug.** `layout()` derived `persistence=playlist_code is None` and
`persistence=scenario is None` for the two dropdowns, so a
`/?playlist_code=…&scenario=…` arrival rendered both with `persistence=False`.
Dash's `recordUiEdit` returns early on a falsy `persistence`, so every
selection made during that visit went unrecorded; `persistenceMods` skips the
component for the same reason, so the value stored *before* the visit was not
cleared either. Returning to `/` re-enabled persistence against a layout
`value` of `None`, which matched the stored original, and the pre-visit value
was restored. Confirmed against the shipped `dash_renderer` and reproduced in
a browser: with no deep-linked visit the selection survives a Home click; with
one, both dropdowns revert, through the navbar link and the header title
alike.

**The invariant this establishes.** *A browser-persisted control's layout
default never varies per visit; a per-visit initial value arrives by
callback.* Dash pins a persisted edit to the layout value it was made against
and discards the edit when a later visit renders a different one, so a default
that varies per visit retires persistence for that control instead of
overriding it. This is the per-visit twin of the keyed-by-id rule in
[2026-08-09](#2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph),
and it binds any future `?param=` preselect on any page.

**Its corollary, learned the hard way in review.** *A callback that writes a
control only on some visits starves that control's single-Input dependents on
the others.* The renderer drops a ready callback when none of its Inputs was
written and every one of them is a declared output of a group member that
already ran. `select_playlist`'s only Input was the playlist value, which
`apply_deep_link` now declares and returns `no_update` for on every visit
without `?playlist_code=` — so it stopped making its initial call, and the
scenario dropdown kept the layout's full local list while the filter named a
playlist. The fix is a second Input that nothing writes, which makes the
prune's "every Input covered" test fail; `select_playlist` carries the
`home-deep-link` store for that reason and no other. A structural test in
`tests/test_home_rank_format.py` fails if any callback's Input set is ever
again a subset of what `apply_deep_link` conditionally writes.

**The mechanism.** Both dropdowns carry `persistence=True` and an explicit
`value=None` on every visit. `layout()` resolves the query parameters into a
layout-bound `dcc.Store` (`home-deep-link`), and one callback,
`apply_deep_link`, writes them to the two dropdowns. Callback-written values
*are* persisted — the response path reaches `recordUiEdit` — so the deep link
becomes an ordinary remembered selection. Details that are load-bearing:

- **`value=None` is explicit, not omitted.** An omitted prop is `undefined`
  rather than `null`, which would not match the original already stored in
  every existing browser and would discard those values on upgrade.
- **A layout-bound store, not the URL.** Dash Pages rebuilds the page on a
  route change and the store then triggers exactly one write, keeping the deep
  link out of the router's callback graph — the same reason
  [2026-04-29](#2026-04-29-drive-playlist-table-loads-from-mounted-route-state)
  drives the playlist scenario table from mounted route state.
- **`allow_duplicate` plus `prevent_initial_call="initial_duplicate"`.**
  `check_for_new_data` already writes the scenario value, and applying the
  deep link is the mount's whole job. Folding it into `check_for_new_data` was
  rejected: that callback's `prevent_initial_call=True` stops a remount
  replaying the retained run-event batch.
- **Presence, not just value.** The store records a key only for a parameter
  the URL carried, and the callback returns `no_update` for the rest, so
  `?scenario=` alone leaves the playlist filter on the restored value. An
  unknown playlist code is recorded with no value and clears the filter, which
  is what applying the URL's selection as given means.

**The URL is not rewritten after the deep link is consumed**, so a reload
re-applies it over a later choice. `_pages_location.search` is a router
`Input`; rewriting it would remount the page. The behavior matches a URL with
parameters read as a bookmark, and the navbar link is the way back.

**Accepted cost.** Persistence restores the previous selection before the
callback's value lands, so a deep-linked visit shows the old playlist name for
one round trip. What the renderer holds during that round trip is asymmetric,
and only the playlist half is held: `getReadyCallbacks` waits on a pending
output only when an Input's `id.prop` equals the output's key, and an
`allow_duplicate` output's key carries an `@<hash>` suffix that this
comparison does not strip (though `cleanOutputProp` strips it when results are
applied). So the playlist value's dependents wait, and the scenario value's do
not: on a deep-linked visit `generate_graph` and `get_scenario_num_runs` each
run twice, once for the restored scenario and again for the deep-linked one.
A stale run's outputs are not discarded — they land. The stale
`generate_graph` response finishes before the second request is issued and
is applied, so the `cached-plot` store holds the stale plot for tens of
milliseconds. The user still does not see it, because the hold this paragraph
describes works one hop downstream: `cached-plot.data` is a plain output, so
`apply_graph_appearance` waits behind the pending second `generate_graph` and
draws once, from the deep-linked plot. That rests on `apply_deep_link`'s
response landing alongside the stale plot's, which it did in every measured
load and which nothing guarantees; "never drew the stale plot when measured"
is the honest claim, not "cannot". The cost is server-side: one plot build
that is never drawn and one stats read per deep-linked visit.
`get_scenario_rank` also runs twice, and its stale run is an ordinary mount
run: it arrives with real triggers (three `changedPropIds`), so it is
network-allowed and toast-allowed, and its lookup is TTL-governed — a cache
read while that scenario's rank cache is fresh, which is the usual case
because the scenario was the selection a moment ago and the TTL is a week,
and a KovaaK's lookup when the cache is cold or expired. The falsy list Dash
substitutes for an *untriggered* call — one item whose `prop_id` is `"."`,
so `ctx.triggered` is never `[]` inside a callback — is what keeps such a
call quiet without refusing it the network, since `_rank_allows_network`
refuses only when the interval is the sole trigger. It does not apply to this
run, which is triggered. A clientside callback would shrink the transient to a
frame at the cost of moving the resolution out of Python; it stays available
if the transient ever proves visible.

**Rejected.** Keeping `persistence=False` for the visit and clearing the
stored keys from the browser: it depends on dash-renderer's private key format
and still discards the visit's selections. Keeping the query value as the
layout `value` with persistence on: the pinned original then becomes the query
value, so the next Home visit discards the entry and both dropdowns come up
empty — the same loss, reached differently. Making `apply_deep_link` the plain
writer of the scenario value and moving `allow_duplicate` onto
`check_for_new_data`, which would make the hold symmetric and the double run
go away: it puts the mount-fire hazard on the one callback whose contract is
that a mount must not replay the retained run-event batch, which is worth more
than one never-drawn plot build per deep-linked visit. No prior entry governed
the original behavior, so nothing is superseded.
