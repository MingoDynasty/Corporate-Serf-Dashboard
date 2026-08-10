# Unset-Username Position Feedback Proposal

Status: Proposed
Date: 2026-08-09

## TL;DR

With no KovaaK's username configured, opening a playlist ends in a red
"Position update incomplete — couldn't update 16 of 16 positions" toast,
and the Scenario Performance Refresh button answers a click with a red
"Position refresh failed". Nothing actually failed: the rank service
already stays fully offline without a username, so both toasts report a
persistent configuration state as if it were a transient network failure.
The fix moves the condition into the playlist page's own status line,
skips the pointless update pass entirely, and makes the Refresh answer
name the missing username and point at Settings. Red then again means a
lookup that really failed.

## Decisions needed

Each decision carries its own status so review stays scoped. Decision 1
and 2 fix which surface answers; decision 3 is the wording and severity
on those surfaces. The implementation PR starts once all three are
ratified.

1. **Playlist page goes quiet — no fill pass and no toast when the
   username is unset; the grid's status line carries the condition
   instead.** Status: Open. Recommended: yes. With no username, every
   one of the fill's per-scenario lookups short-circuits to UNKNOWN
   without touching the network, so phase 2 is a no-op that exists only
   to mislead: a live progress line over zero network activity, ending
   in a red failure toast. Skipping it and stating the condition in the
   status line follows the ratified routing policy (persistent
   conditions render in place, passive activity never toasts).
   Choosing differently — keep the fill and merely reword the toast —
   keeps the fake progress display and spends a toast on a condition
   that has an in-place home.
2. **Refresh keeps answering with a toast — one that names the real
   verdict — rather than being disabled.** Status: Open. Recommended:
   toast. The manual-refresh rule is that a click always answers on the
   callback's own notification output; answering "no username set" is
   the honest verdict and needs no new wiring. Disabling the button
   instead would need settings-reactive enable/disable state and would
   remove the answering surface — while the Position field's own hint
   already carries the repair link. Silence is not an option; it
   contradicts the ratified manual-refresh rule.
3. **Copy and severity for the two new surfaces.** Status: Open. UI copy
   is a maintainer call; proposed strings to react to, exact wording in
   Design. Playlist status line: "Positions unavailable — set your
   KovaaK's username in Settings" with Settings as a link, echoing the
   Position field's hint. Refresh toast: title "KovaaK's username not
   set", message "Set your KovaaK's username in Settings to see your
   leaderboard position.", color blue — the app's neutral-information
   color (the away-digest uses it) — because nothing failed and nothing
   is degraded. Alternative severity is yellow, but yellow currently
   means degraded data (stale serve, threshold miss, Steam mismatch),
   which this is not.

## Problem

Reproduction: unset both KovaaK's username and Steam ID in Settings,
open Playlists, select a playlist. Every per-scenario lookup
short-circuits at the top of `get_scenario_rank_info`
(`source/kovaaks/api_service.py:1567`) to
`UNKNOWN, error_message="KovaaK's username is not configured."` with
zero network calls — the
[2026-08-01 fully-offline decision](decision_log.md#2026-08-01-no-username-stays-fully-offline--user-independent-totals-rejected)
working as designed. The noise is purely presentational, on two
surfaces:

- **Playlist scenarios page.** `load_playlist_scenario_rows`
  (`source/pages/playlist_scenarios.py`) unconditionally starts the
  phase-2 fill; its workers run one no-op lookup per scenario, every
  result counts into `unknown_count`, and the terminal drain fires the
  red summary toast "Position update incomplete / Couldn't update N of
  N positions" (`_fill_summary_notification`,
  `source/pages/playlist_scenarios.py:275`). Along the way the status
  line reads "Updating positions from KovaaK's… 0/N" — while nothing is
  being fetched — and settles on "N of N positions unavailable".
- **Scenario Performance Refresh.** The passive Position field already
  handles the condition correctly: "N/A — set your KovaaK's username in
  Settings" with a clickable link (`_rank_hint_children`,
  `source/pages/home.py:469`). But `refresh_rank` treats every
  `error_message` result as a hard failure (`source/pages/home.py:697`)
  and answers the click with the generic red "Position refresh failed /
  Couldn't refresh — position unchanged." — the one cause it could name
  precisely, reported as an anonymous failure beside a field that is
  already explaining it.

Both contradict the
[2026-08-03 notification routing policy](decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy):
persistent conditions render in place instead of toasting, and toast
copy carries the verdict. The redesign gave the unset-username case
exactly that treatment on Home's passive path; the playlist fill
summary and the manual-refresh answer fell through the generic UNKNOWN
accounting because neither distinguishes *why* a lookup came back
unknown.

Verified facts that bound the design:

- The username is the required key; Steam ID alone cannot fetch
  anything. The service gates on username only, and `steam_id` is an
  optional identity disambiguator applied to an already-fetched
  leaderboard
  ([2026-04-27](decision_log.md#2026-04-27-prefer-steam-id-matching-when-configured)).
  So the gate below checks the username, and the redirect copy names
  the username — matching the Position field's existing hint.
- Identity is process-pinned in one direction only
  (`get_identity`, `source/config/settings_service.py:136`): reads stay
  live until the first non-empty username is observed, then freeze for
  the process's life. Unset → set applies immediately without a
  restart; set → unset cannot happen mid-process. A per-invocation gate
  is therefore exactly right: fill in Settings, reopen the playlist,
  and positions flow — and the gate can never strand a configured user.
- The Playlists overview page is already safe: its percentile cells are
  cache-only (`allow_network=False`), it never toasts about positions,
  and unresolved cells render as "0/N cached"
  (`source/kovaaks/playlist_overview_service.py`).

## Design

**Playlist scenarios page** (decision 1). In
`load_playlist_scenario_rows`, after the playlist resolves and before
`start_playlist_scenario_fill`, check `get_kovaaks_username()`. When it
is empty:

- Build and return the phase-1 rows as today — the local columns (Last
  played, Runs, High score, PB sens, PB accuracy) are unaffected, and
  any positions already in the disk caches still render.
- Clear the three per-row pending flags the same way the existing
  playlist-deleted branch does
  (`source/pages/playlist_scenarios.py:243`), so no cell is left
  animating for a fill that will never run.
- Do not start the fill and leave the interval disabled with a `None`
  generation token — the same shape as the page's other no-fill
  returns. `_fill_summary_notification` is untouched; the toast never
  fires because the fill it summarizes never runs.
- Return the condition as the status line's children — components are
  legal there (the output is `children`; today it happens to get plain
  strings): the proposed copy from decision 3, with "Settings" as
  `dmc.Anchor(href="/settings", refresh=False)`, the same link the
  Position field's hint uses.

**Refresh answer** (decisions 2–3). In `refresh_rank`
(`source/pages/home.py:666`), after the existing `n_clicks` and
selected-scenario guards, check `get_kovaaks_username()`. When empty,
return `no_update` for the value (the field already shows "N/A — set
your KovaaK's username in Settings") plus the decision-3 toast on the
callback's own notification output. Detection is the direct settings
read, never string-matching the service's `error_message`. The toast id
is stable and semantic (e.g. `rank-refresh-username-unset`) per the
routing policy's stable-id rule — repeat clicks re-show one toast
instead of stacking. Toast messages are plain strings under the current
`toast()` payload shape, so the message names Settings in prose; the
clickable link lives in the field hint beside it. The genuine failure
paths — network refusal, invalid username on the API side — keep the
existing red "Position refresh failed" answer unchanged.

**Docs shipped with the implementation PR** (the shipping checklist
applies):

- A decision-log entry recording the routing verdict: the
  unset-username condition is persistent state, surfaced in place on
  both pages; the manual-refresh answer names it; extends the
  2026-08-03 routing entry and the 2026-08-01 fully-offline entry.
- `docs/specs/scenario_rank.md`: the manual-Refresh paragraph in
  Failure handling gains the fourth outcome (unset username answers
  with the named-verdict toast, not the red failure), and the identity
  section notes the playlist page's in-place treatment.
- The usual `architecture.md`/README sweep for restated behavior.

## Delivery plan

- **PR 1 (this PR): the proposal.** Docs only, opened for maintainer
  ratification of decisions 1–3 and reviewer input.
- **PR 2: the implementation**, gated on decisions 1–3 flipping to
  Accepted. Both surfaces, regression tests, the decision-log entry and
  spec edits above, and deletion of this file per the shipping
  checklist. One PR — the two surfaces share the gate helper and the
  docs story, and neither is independently shippable without
  re-touching the same spec paragraphs. Recommended implementer:
  Opus 4.8 at effort high — the change is two guarded early returns
  plus tests once the decisions settle, and more capability would not
  change the diff; the judgment lives in this proposal.

## Out of scope

- The Playlists overview page: cache-only, no toasts, and its "0/N
  cached" cells are a different (already quiet) idiom. No change.
- Background refresh chains (score-aware Timer, warmup worker): already
  console-only per the 2026-08-03 background-diagnostics decision, and
  an unset username short-circuits them offline today.
- Cached positions recorded under a previously configured identity
  still render in phase-1 rows after that identity is unset (which
  takes a restart). Accepted: the cache serves what it has, and the
  escape hatch is deleting `data/cache/` — no TTL or purge machinery
  for this proposal.
- Steam-ID-only operation: the service requires a username by design;
  this proposal does not revisit that.
- Settings discoverability for first-run users (a Home setup card,
  skip semantics): owned by the deferred setup-flow proposal tracked on
  the roadmap, not here.

## Testing

- `tests/test_playlist_pages.py`: with a monkeypatched empty username,
  `load_playlist_scenario_rows` returns rows with all pending flags
  cleared, a `None` generation token, a disabled interval, and a status
  line carrying the Settings anchor — and registers no fill (the
  service registry stays empty, so no later drain can toast). With a
  username set, the existing fill-start behavior is asserted unchanged.
- Home tests (`tests/test_home_rank_format.py` or a sibling):
  `refresh_rank` with an empty username returns `no_update` for the
  value and the decision-3 toast payload (id, title, color); with a
  username set, the three existing outcomes (green fresh, yellow
  stale, red failure) are untouched.
- Docs gates: `tests/test_docs.py` (Status line, section order, link
  targets) plus the standard local validation suite on both PRs.
