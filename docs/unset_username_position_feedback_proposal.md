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

Each decision carries its own status so review stays scoped. Decisions 1
and 2 fix which surface answers; decision 3 is the wording and severity
on those surfaces; decision 4 bounds the scope against the neighboring
defect. The implementation PR starts once all four are ratified.

1. **Playlist page goes quiet — no fill pass and no toast when the
   username is unset; the grid's status line carries the condition
   instead.** Status: Open. Recommended: yes. With no username, every
   one of the fill's per-scenario lookups short-circuits to UNKNOWN
   without touching the network, so phase 2 is a no-op that exists only
   to mislead: a live progress line over zero network activity, ending
   in a red failure toast. Skipping it and stating the condition in the
   status line follows the ratified routing policy (persistent
   conditions render in place, passive activity never toasts) — and the
   status line cannot be contradicted by anything on screen, because
   without the username key the position columns are all N/A (the
   service's guard fires before any cache read). Choosing differently —
   keep the fill and merely reword the toast — keeps the fake progress
   display and spends a toast on a condition that has an in-place home.
2. **Refresh keeps answering with a toast — one that names the real
   verdict — rather than being disabled or silenced.** Status: Open.
   Recommended: toast. Stated honestly, the ratified routing policy
   cuts both ways here. Its first branch sends persistent conditions to
   in-place UI, "never a toast", and its litmus test names the Position
   field — the very surface already carrying this hint; its third
   branch answers a user-initiated action on the callback's own output
   because "the user asked and deserves the result". The argument that
   survives the collision is structural, not "a rule says so": the
   in-place home was already displaying the answer before the click, so
   it cannot produce any perceptible response to the click itself — and
   a user who clicks Refresh beside the hint plausibly clicked because
   they had not read it. A deliberate click deserves a response the
   user can watch happen; user-initiated wins for this event. To keep
   that premise true on every click, the toast carries a fresh
   per-click id (the green confirmation's existing mechanism) — a
   stable id would be silently swallowed for repeat clicks while the
   previous toast is still on screen. Disabling the button instead
   would need settings-reactive enable/disable wiring and would remove
   the answering surface; silence would leave a deliberate click with
   no visible result at all.
3. **Copy, severity, and icon for the two new surfaces.** Status: Open.
   UI copy is a maintainer call; proposed package to react to, exact
   mechanics in Design. Playlist status line: "Positions unavailable —
   set your KovaaK's username in Settings" with Settings as a link,
   echoing the Position field's hint. Refresh toast: title "KovaaK's
   username not set", message "Set your KovaaK's username in Settings
   to see your leaderboard position.", color blue — the app's
   neutral-information color (the away-digest uses it) — because
   nothing failed and nothing is degraded, and the same refresh icon
   the other manual-refresh answers carry. One caveat so the ruling is
   made on what will actually render: with an icon present, Mantine
   suppresses the full-height color bar (recorded in the tech-debt
   register), so the blue shows as a small colored circle and the title
   does the real work — consistent with the policy's
   title-carries-the-verdict standard. The existing red/yellow
   manual-refresh pair shares one title and is separated by color
   alone; this outcome gets its own title, so that recorded concern
   does not extend to it. Alternative severity is yellow, but yellow
   currently means degraded data (stale serve, threshold miss, Steam
   mismatch), which this is not.
4. **The configured-but-invalid username sibling is deferred, not
   folded in.** Status: Open. Recommended: defer, named in Out of
   scope. A username that is set but wrong raises the service's
   unknown-user error, lands as UNKNOWN plus an error message, counts
   into the fill's unknown tally, and fires the identical pair of red
   toasts — the same defect class one step over, and arguably the more
   confusing instance, because the user believes they configured it.
   It cannot ride this proposal's mechanism: detecting an invalid
   username costs a network round-trip, so it cannot be a pre-flight
   gate, and routing it correctly needs the service to say *why* a
   lookup came back unknown. Folding it in roughly doubles the
   implementation PR and drags the fill's terminal-drain accounting
   into scope. Deferring it explicitly also keeps the shipped
   decision-log entry honest: the entry records a verdict on the unset
   case only and names the invalid case as open. Choosing differently
   buys one fewer red-toast class at the cost of a materially larger
   PR.

## Problem

Reproduction: unset both KovaaK's username and Steam ID in Settings,
open Playlists, select a playlist. Every per-scenario lookup
short-circuits at the `if not username:` guard at the top of
`get_scenario_rank_info` (`source/kovaaks/api_service.py`) to
`UNKNOWN, error_message="KovaaK's username is not configured."` with
zero network calls — the
[2026-08-01 fully-offline decision](decision_log.md#2026-08-01-no-username-stays-fully-offline--user-independent-totals-rejected)
working as designed. (Symbols are cited without line numbers — they
survive rebases; the branch is merged current with `main` as of this
writing.) The noise is purely presentational, on two surfaces:

- **Playlist scenarios page.** `load_playlist_scenario_rows`
  (`source/pages/playlist_scenarios.py`) unconditionally starts the
  phase-2 fill; its workers run one no-op lookup per scenario, every
  result counts into `unknown_count`, and the terminal drain fires the
  red summary toast "Position update incomplete / Couldn't update N of
  N positions" (`_fill_summary_notification`, same file). Along the
  way the status line reads "Updating positions from KovaaK's… 0/N" —
  while nothing is being fetched — and settles on "N of N positions
  unavailable".
- **Scenario Performance Refresh.** The passive Position field already
  handles the condition correctly: "N/A — set your KovaaK's username in
  Settings" with a clickable link (`_rank_hint_children`,
  `source/pages/home.py`). But `refresh_rank` (same file) treats every
  `error_message` result as a hard failure and answers the click with
  the generic red "Position refresh failed / Couldn't refresh —
  position unchanged." — the one cause it could name precisely,
  reported as an anonymous failure beside a field that is already
  explaining it.

Both contradict the
[2026-08-03 notification routing policy](decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy):
persistent conditions render in place instead of toasting, and toast
copy carries the verdict. The redesign gave the unset-username case
exactly that treatment on Home's passive path; the playlist fill
summary and the manual-refresh answer fell through the generic UNKNOWN
accounting because neither distinguishes *why* a lookup came back
unknown. The same accounting gap has a second tenant: a
configured-but-invalid username (`UnknownKovaaksUserError`, raised in
`source/kovaaks/api_service.py`) produces the identical two red
toasts. Decision 4 rules on its scope; this proposal fixes the unset
case.

Verified facts that bound the design:

- The username is the required key; Steam ID alone cannot fetch
  anything. The service gates on username only, and `steam_id` is an
  optional identity disambiguator applied to an already-fetched
  leaderboard
  ([2026-04-27](decision_log.md#2026-04-27-prefer-steam-id-matching-when-configured)).
  So the gate below checks the username, and the redirect copy names
  the username — matching the Position field's existing hint.
- The no-username guard fires *before* leaderboard resolution or any
  rank-cache read, so a username-less process renders N/A in every
  position cell — including cache files written under a previously
  configured identity, which are unreachable without the username key.
  Nothing on screen can contradict the quiet status line.
- Identity is process-pinned in one direction only (`get_identity`,
  `source/config/settings_service.py`): reads stay live until the
  first non-empty username is observed, then freeze for the process's
  life. Unset → set applies immediately without a restart; set → unset
  cannot happen mid-process. A per-invocation gate is therefore
  exactly right: fill in Settings, reopen the playlist, and positions
  flow — and the gate can never strand a configured user.
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
  played, Runs, High score, PB sens, PB accuracy) are unaffected. The
  position columns all render N/A: the service's no-username guard
  returns UNKNOWN before any cache read, so no cached position can
  appear.
- Clear the three per-row pending flags the same way the existing
  playlist-deleted branch does (`source/pages/playlist_scenarios.py`),
  so no cell is left animating for a fill that will never run.
- Do not start the fill and leave the interval disabled with a `None`
  generation token — the same shape as the page's other no-fill
  returns. `_fill_summary_notification` is untouched; the toast never
  fires because the fill it summarizes never runs.
- Skipping `start_playlist_scenario_fill` also skips its
  cancel-older-fills side effect (`_cancel_live_fills_locked`). That is
  sound, not an oversight: identity only moves unset → set within a
  process, so a tripped gate means the username has been empty for the
  whole process, every earlier playlist open tripped it too, and no
  live fill can exist. Do not add a compensating cancel call.
- Return the condition as the status line's children — components are
  legal there (the output is `children`; today it happens to get plain
  strings): the proposed copy from decision 3, with "Settings" as
  `dmc.Anchor(href="/settings", refresh=False)`, the same link the
  Position field's hint uses.

**Refresh answer** (decisions 2–3). In `refresh_rank`
(`source/pages/home.py`), after the existing `n_clicks` and
selected-scenario guards, check `get_kovaaks_username()`. When empty,
return `no_update` for the value (the field already shows "N/A — set
your KovaaK's username in Settings") plus the decision-3 toast on the
callback's own notification output. The toast id is fresh per click,
exactly like `_rank_refresh_success_notification`'s uuid: DMC's `show`
ignores a payload whose id is already on screen, so a stable id would
swallow every repeat click inside the previous toast's lifetime and
break decision 2's every-click-answers premise. The heavier
`upsert_toast` update/show replacement would also work but is
unnecessary for a discrete click result. Toast messages are plain
strings under the current `toast()` payload shape, so the message names
Settings in prose; the clickable link lives in the field hint beside
it. The genuine failure paths — network refusal, invalid username on
the API side — keep the existing red "Position refresh failed" answer
unchanged.

**Detection.** Both surfaces gate on the direct settings read
(`get_kovaaks_username()`). Two alternatives rejected: string-matching
the service's `error_message` (brittle coupling to display copy), and a
typed reason field on `ScenarioRankInfo` so consumers route on the
service's own verdict instead of re-reading settings. The typed reason
is the right instinct but the wrong fit here: the playlist page needs a
pre-flight gate that skips the whole fill before any lookup runs —
which a per-result reason cannot deliver — and only two sites consume
it. The deferred invalid-username follow-up (decision 4) is where a
typed reason would earn its place, because that case is only knowable
per-result; re-open the idea there.

**Docs shipped with the implementation PR** (the shipping checklist
applies):

- A decision-log entry recording the routing verdict — scoped
  explicitly to the *unset*-username condition, naming the
  invalid-username case as deferred (decision 4) so the entry does not
  overclaim: the condition is persistent state, surfaced in place on
  both pages, with the manual-refresh answer naming it; extends the
  2026-08-03 routing entry and the 2026-08-01 fully-offline entry.
- `docs/specs/scenario_rank.md`: the manual-Refresh paragraph in
  Failure handling gains the fourth outcome (unset username answers
  with the named-verdict toast, not the red failure), and the named
  per-click-id exception to the stable-id rule widens from the green
  confirmation alone to repeatable manual-refresh answers. The
  identity section notes the playlist page's in-place treatment.
- The usual `architecture.md`/README sweep for restated behavior.

## Delivery plan

- **PR 1 (this PR): the proposal.** Docs only, opened for maintainer
  ratification of decisions 1–4 and reviewer input.
- **PR 2: the implementation**, gated on decisions 1–4 flipping to
  Accepted. Both surfaces, regression tests, the decision-log entry and
  spec edits above, and deletion of this file per the shipping
  checklist. One PR — the two surfaces share the gate helper and the
  docs story, and neither is independently shippable without
  re-touching the same spec paragraphs. Recommended implementer:
  `claude-opus-5 · effort: high` — the change is two guarded early
  returns plus tests once the decisions settle, and more capability
  would not change the diff; the judgment lives in this proposal.

## Out of scope

- The configured-but-invalid username case (decision 4): KovaaK's
  unknown-user error still lands as the same two generic red toasts.
  Deferred because its detection requires a network round-trip and a
  per-result reason, not a pre-flight gate — a different mechanism in
  its own follow-up once this ships; the decision-log entry names it as
  open so the deferral cannot silently rot.
- The Playlists overview page: cache-only, no toasts, and its "0/N
  cached" cells are a different (already quiet) idiom. No change.
- Background refresh chains (score-aware Timer, warmup worker): already
  console-only per the 2026-08-03 background-diagnostics decision, and
  an unset username short-circuits them offline today.
- Steam-ID-only operation: the service requires a username by design;
  this proposal does not revisit that.
- Settings discoverability for first-run users (a Home setup card,
  skip semantics): owned by the deferred setup-flow proposal tracked on
  the roadmap, not here.

## Testing

- `tests/test_playlist_pages.py`: with a monkeypatched empty username,
  `load_playlist_scenario_rows` returns rows whose position columns
  are all N/A with every pending flag cleared, a `None` generation
  token, a disabled interval, and a status line carrying the Settings
  anchor — and registers no fill (the service registry stays empty, so
  no later drain can toast). With a username set, the existing
  fill-start behavior is asserted unchanged.
- Home tests (`tests/test_home_rank_format.py` or a sibling):
  `refresh_rank` with an empty username returns `no_update` for the
  value and the decision-3 toast payload (title, color, message), with
  two consecutive clicks carrying distinct ids so both render; with a
  username set, the three existing outcomes (green fresh, yellow
  stale, red failure) are untouched.
- Docs gates: `tests/test_docs.py` (Status line, section order, link
  targets) plus the standard local validation suite on both PRs.
