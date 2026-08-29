# Toast Stacking Policy

Status: Proposed
Date: 2026-08-28

## TL;DR

Importing a second playlist while the first import's toast is still on screen
shows nothing, because most toasts reuse a fixed id and the notification
library silently drops a duplicate — so the user reasonably concludes the
second import failed. A survey of design systems, UX literature, and
production apps converged on one decision rule: distinct actions get separate
stacked toasts, updates to one ongoing thing replace each other in place, and
bursts of the same event fold into one summary. This proposal adopts that rule
as the app's standing toast policy. The classifying test is recurrence: every
toast is keyed to the thing it reports, and a report that can happen again
while its toast is still up replaces that toast with a visible re-entry, so
a retry pops its answer back onto the screen instead of being silently
dropped. Reports about different subjects still stack side by side, and a
success also clears the leftover failure message it answers.

## Decisions needed

- **D1 — Adopt the event / channel / burst policy as the standing rule.**
  Recommended: yes, recorded in `docs/specs/notifications.md` so every future
  toast picks its id pattern deliberately. The classifier is two questions,
  not copy inspection alone. First: can the reported fact recur inside one
  toast lifetime, judged against the complete supported workflow including
  inverse actions that make the same subject eligible again (a deleted
  playlist can be re-imported at once)? A fact that cannot recur is an event
  toast (unique id, plain show, stacks, no sequence wiring). A fact that can
  recur is a channel. Second: what is the channel's identity? Identity
  follows the semantic lane. An operation's problem lane is one channel: its
  mutually exclusive outcome flavors (a red hard failure, a yellow
  served-stale) share a single id, so two contradictory claims about the
  same latest attempt can never be on screen together. Success lanes and
  standing-condition lanes are their own channels, keyed by subject when
  independent subjects can be in flight at once (one refresh-success channel
  per scenario, one import-success channel per playlist code); lanes
  interact only through explicit cross-clears, such as a success clearing
  its operation's problem lane. Choosing differently means each new toast
  re-litigates the choice ad hoc, which is how today's mixed inventory
  (three patterns, no stated rule) came to be.
- **D2 — Toasts whose repeats can carry identical copy become
  replace-in-place channels.** Recommended: convert the three
  per-action failure toasts (`imported-playlist-failed-notification`,
  `deleted-playlist-failed-notification`,
  `superseded-cleanup-failed-notification`), the two refusal toasts
  (`visibility-refused-notification`,
  `setup-card-skip-refused-notification`), the constant-copy
  `superseded-cleanup-successful-notification`, and
  `rank-refresh-username-unset-{uuid}` (today a unique-id stacker whose
  repeats are byte-identical) to single-identity channels. The rank-refresh
  family gets the same treatment in its own shape: today's
  `rank-refresh-failed` and `rank-refresh-stale` merge into one problem
  channel whose payload carries the outcome (red hard-failure or yellow
  served-stale), so one attempt's verdict always replaces the previous
  attempt's instead of sitting beside it, and the green
  `rank-refresh-notification-{uuid}` success becomes a channel keyed by
  scenario, so re-refreshing the same scenario replaces its own toast while
  refreshes of different scenarios still stack. The three playlist success
  toasts become channels keyed by canonical playlist code for the same
  reason: the supported delete-then-re-import cycle lets the same playlist
  succeed twice inside one lifetime with byte-identical copy, so recurrence
  — judged by possibility, exactly as for the cleanup success — puts them
  in the channel bucket, while distinct playlists still stack because their
  keys differ, which is all the reported bug's fix requires. These are the toasts whose
  repeats can carry identical text — most because a user retries against
  them (the failed-import modal deliberately keeps the pasted code for a
  quick resubmit), and stacking identical toasts is the literature's
  documented anti-pattern. The recommended replacement mechanism is
  **hide-and-reshow**, verified by a live POC against the installed
  dash-mantine-components 2.8.0 on 2026-08-29 (findings comment on PR #257;
  harness under `ignore/scripts/toast_hide_reshow_poc/`): each emission
  shows a fresh instance id and hides the channel's previous instance in
  the same response, so every retry visibly re-pops the toast with the
  full entry animation and a structurally fresh 8 s lifetime — the
  measured numbers are in Design. Ratifying D2 also ratifies its two
  supporting mechanics there: the per-channel instance registry (the store
  that knows which instance id to hide), and success-clears-failure,
  without which a stale failure toast outlives the success that answers
  it. Alternatives, in the order they fell: plain upsert (the update+show
  pair with the alternating `autoClose`) restarts the timer with zero
  visible change — a retried click reads as a dead click while the toast
  silently extends — and survives only as the fallback if the maintainer
  prefers stillness over motion; attempt-count copy ("(attempt 2)"
  appended on repeat) bought that visibility at the cost of new
  user-facing strings and per-callback counters, and is strictly dominated
  now that hide-and-reshow delivers the visibility with no copy; keeping
  the stable ids (status quo) remains the do-nothing alternative, where a
  retry inside the 8 s window gets no answer at all, the dead-UI failure
  the import bug exhibits.
- **D3 — Retire `upsert_toast`: `run-verdict` migrates to hide-and-reshow
  too.** Recommended: yes. With every D2 channel on hide-and-reshow, the
  alternating-`autoClose` trick exists for one toast only; migrating
  `run-verdict` deletes the trick and its sequence semantics outright and
  leaves one replacement mechanism app-wide. The ratified run-verdict
  contract is preserved — one run, one toast, the newest verdict replacing
  whatever is on screen — but each new verdict now re-enters with the pop
  animation instead of morphing in place, which is a small visible change
  to shipped behavior and is why this is its own decision. Choosing
  differently keeps two replacement mechanisms alive indefinitely for one
  toast's benefit.

## Problem

dash-mantine-components 2.8.0 silently ignores a `show` action whose
notification id is already on screen (documented on `toast()` in
`source/utilities/notifications.py`). Most of the app's toasts use fixed,
semantic ids, so any two emissions of the same toast within one 8-second
lifetime lose the second one. Observed concretely: importing playlist B while
playlist A's green "Playlist imported" toast is still visible produces no
feedback at all, which reads as a failed import. The red import-failure toast
has the same window, and it is easier to hit than it looks: a failed import
leaves the modal open with the pasted code intact for correction, so a quick
retry that fails again inside 8 seconds also answers with nothing.

The inventory in `docs/specs/notifications.md` shows three id patterns already
in use, each chosen locally without a stated rule:

- fixed ids that dedupe (most toasts, including all seven per-action outcome
  toasts on the playlists overview);
- unique-per-emission ids that stack (`rank-refresh-notification-{uuid}`,
  added precisely because "``show`` silently ignores a duplicate id … which
  would eat the 'done' cue on back-to-back refreshes");
- one replace-in-place channel (`run-verdict` via `upsert_toast`, "one run,
  one toast", the newest verdict replacing the old — a ratified design, see
  the 2026-08-03 decision-log entry), plus one fold-into-summary burst toast
  (`run-import-failure` batches a poll tick's failures into one message).

So the codebase has already invented all three industry patterns; what it
lacks is the rule for which one a new toast should use, and thirteen toasts
sit on the wrong side of that rule today.

## Research

Surveyed 2026-08-28 (design-system pages, library docs and sources, UX
literature, OS notification guidance). Condensed to the load-bearing
evidence; practices here drift over time, so treat the date as part of every
claim.

**Design systems allow stacking, with hard caps; Material alone replaces.**
Fluent 2 caps visible toasts at four; Salesforce Lightning shows at most
three and queues the rest FIFO; Carbon stacks newest-on-top; Atlassian's
flag group stacks with only the newest fully visible; Shopify Polaris
explicitly blesses "multiple toast messages … about distinct actions"
(<https://fluent2.microsoft.design/components/web/react/core/toast/usage>,
<https://developer.salesforce.com/docs/platform/lightning-component-reference/guide/lightning-toast-container.html>,
<https://carbondesignsystem.com/components/notification/usage/>,
<https://atlassian.design/components/flag/flag-group>). Material Design is
the lone replace camp: one snackbar at a time, a new one animating the old
out (<https://m3.material.io/components/snackbar/guidelines>) — which is why
Gmail behaves that way. GitHub's Primer deprecated toasts outright on
accessibility grounds and recommends banners and inline messages
(<https://primer.style/accessibility/patterns/accessible-notifications-and-messages/>).

**Library defaults agree on small visible caps.** Mantine notifications —
this app's library — defaults to five visible with overflow queued; sonner
shows three with older toasts collapsed behind the newest; notistack caps at
three and drops the oldest; VS Code shows three plus a notification-center
bell (<https://mantine.dev/x/notifications/>,
<https://sonner.emilkowal.ski/toaster>, <https://notistack.com/api-reference>,
<https://github.com/Microsoft/vscode/issues/44319>). Mantine's queue is this
app's built-in flood backstop.

**Combining events into one message is the OS-layer pattern.** Android
requires a group summary and force-bundles four or more notifications from
one app; macOS groups per app; new Outlook collapses a burst window into one
alert
(<https://developer.android.com/develop/ui/views/notifications/group>,
<https://support.apple.com/en-nz/guide/mac-help/mchl2fb1258f/mac>). The
recurring constraints: never batch individually-actionable events, and keep
the individual events reachable somewhere so the summary is a door, not a
wall. In-app toast combining is rare; the common in-app form is a running
count folded into a single message — which `run-import-failure` already does.

**The critical literature contributes the two hazards the policy must dodge.**
Replacing a toast with identical text reads as a dead UI — archive two Gmail
emails quickly and the toast "won't appear to update," so the second action
seems ignored
(<https://adamsilver.io/blog/the-problem-with-toast-messages-and-what-to-do-instead/>).
And stacking identical messages is the canonical failure (a Hacker News
thread's example: deleting ten YouTube comments produced twenty-plus
lingering toasts, <https://news.ycombinator.com/item?id=41298794>). Together
they yield the sharpest heuristic found anywhere in the survey: **if two
stacked toasts could carry identical text, they should not be two toasts** —
either the text must distinguish them or the second should replace the first
with a restarted timer. Also noted for completeness: NN/g and Polaris
discourage error *toasts* generally in favor of persistent surfaces
(<https://www.nngroup.com/articles/indicators-validations-notifications/>);
see Out of scope.

## Design

**The policy (D1), as it would read in the notifications spec:**

1. **Event toasts** — the reported fact cannot recur inside one toast
   lifetime, judged against the complete supported workflow including
   inverse actions that make the subject eligible again. Unique id per
   emission (`-{uuid}` suffix), plain `show`, occurrences stack, and the
   emitting callback needs no sequence wiring. Applying that test today
   leaves this bucket empty — every current toast's fact can recur through
   some supported cycle — so the rule exists to classify future toasts, and
   any claim that a fact cannot recur must survive the inverse-action check
   (delete-then-re-import defeats the naive claim for import success).
2. **Channel toasts** — the toast is the current state of one ongoing thing
   (the latest run's verdict, the latest attempt's outcome). Replaced in
   place by hide-and-reshow (the mechanism bullet below): each emission
   visibly re-enters with a structurally fresh lifetime, so the toast stays
   up and every recurrence visibly answers. Identity follows the semantic
   lane.
   An operation's problem lane is one channel: its mutually exclusive
   outcome flavors share a single id with a payload that differs
   (hard-failure and served-stale are one channel), so two contradictory
   claims about the same latest attempt can never be on screen together.
   Success lanes and standing-condition lanes are their own channels, keyed
   by subject when independent subjects can be in flight at once (per
   scenario, per playlist code). The mutual-exclusion clause is
   deliberately problem-lane-only: success flavors of one operation (a
   green full success and an orange partial success) may keep distinct
   channels, accepting the narrow cross-flavor window a re-attempt can
   open — do not re-litigate this when applying the rule to a new toast.
   Lanes interact only through explicit cross-clears: when the operation
   behind a problem lane reports success, the success emission clears that
   problem channel — and any standing-condition channel the success
   falsifies — so a stale claim never outlives the answer that supersedes
   it.
3. **Burst toasts** — many same-type events where the aggregate is the
   message ("3 new run files could not be processed"). Fold into one summary
   carrying a count, and point at where the individual events are recorded.
4. A standing condition the user must notice once (a config mismatch, a
   startup warning) may additionally be persistent (`auto_close=False`) and
   process- or session-gated; that is orthogonal to 1–3.

**Mechanical application to today's inventory:**

- Convert to subject-keyed channel toasts (rule 2), keyed by canonical
  playlist code: `imported-playlist-successful-{code}`,
  `imported-playlist-visibility-failed-{code}` (the import did land;
  occurrences are distinct playlists), and
  `deleted-playlist-successful-{code}`. Distinct playlists get distinct
  keys, so back-to-back imports of different playlists stack — the reported
  bug's fix. But these facts can recur for one subject: the supported
  delete-then-re-import cycle can produce two byte-identical import
  successes (or delete successes) inside one lifetime, and the delete
  dialog itself promises re-import by share code. On recurrence the
  subject-keyed replacement absorbs the repeat instead of stacking
  duplicates. Key by the canonical stored code, never the pasted input,
  which can differ in case.
- Convert to single-id channel toasts (rule 2), pending D2: the three
  per-action failure toasts, the two refusal toasts,
  `superseded-cleanup-successful-notification`, and
  `rank-refresh-username-unset-{uuid}`. The failures and refusals are
  retried — the failed-import modal deliberately keeps the pasted code for
  resubmission — and a retry of the same input reproduces the same message,
  so they fail rule 1's recurrence test; the toast instead reflects the
  latest attempt's outcome, which the serial modal workflows make
  unambiguous. The cleanup success fails the same test differently: its
  title and message are constant ("Leftover files deleted" / "Deleted
  leftover playlist files."), and while a second cleanup inside one toast
  lifetime is practically unreachable, the policy classifies by what can
  recur, not by likelihood — as a channel it needs no new copy and no
  observable behavior changes. The username-unset toast is a uuid stacker
  with byte-identical repeats (spam-clicking Refresh with no username
  stacks identical blue toasts), so it moves to a stable channel id under
  the same test.
- Restructure the rank-refresh family (rule 2's lane and keying clauses),
  pending D2. The two failure outcomes merge into one attempt-slot channel
  (proposed id `rank-refresh-problem`; toast ids are internal, so the
  rename is free): they already share the title "Position refresh failed"
  and differ only in payload (red "Couldn't refresh — position unchanged."
  versus yellow "Couldn't refresh — showing the cached position."), and as
  separate ids a hard failure followed by a served-stale retry leaves both
  on screen making contradictory claims about the latest attempt. As one
  channel, each attempt's verdict replaces the previous one by
  construction. The green success toast becomes a subject-keyed channel
  (id derived from the scenario, e.g. `rank-refresh-success-{scenario}`;
  derivation must be a stable, collision-free function of the scenario
  name — an implementation detail to pin in the kickoff): its copy is
  byte-identical for repeats of the same scenario, so uuid stacking
  violated rule 1, while different scenarios remain distinct facts that
  stack. This preserves the original purpose of the uuid pattern — the
  "done" cue on back-to-back refreshes survives, as a timer-restarting
  replacement instead of a stack of duplicates. Existing strings are
  carried unchanged; the merge introduces no new copy.
- The hide-and-reshow mechanism, POC-verified live on 2026-08-29 (findings
  comment on PR #257; harness and captured frames under
  `ignore/scripts/toast_hide_reshow_poc/`). A channel emission shows a
  fresh unique instance id and lists the channel's previous instance id in
  the container's hide prop in the same callback response. The hide effect
  runs after the send effect (the 2026-08-03 ordering), which is exactly
  why differing ids work: the new instance entered with the full animation
  (opacity 0 to 1, ~440 px slide over ~135 ms, first paint ~31 ms after the
  click) while the old one animated out — a ~250 ms crossfade with
  complementary opacities that reads as replacement, never as stacked
  duplicates. The new instance's lifetime is structurally fresh — measured
  ~8.0 s from its own show even when replacing at 7.5 s — so the
  alternating-`autoClose` trick is unnecessary on these channels (and
  deleted outright under D3). Hiding an absent or already-closed id is a
  measured clean no-op with a clean console. Rapid repeats (three clicks
  inside a second) stayed stable with no orphans, and the final stack
  layout after a mid-stack replacement was byte-identical. Supporting
  state: the `toast-lifetime-sequence` store becomes a per-channel
  instance registry — a dict mapping each logical channel key
  (subject-keyed channels use their dynamic keys) to its current instance
  id, where an instance id is the channel key plus a per-emission unique
  suffix — read to know what to hide, written on each emission, with a
  State and an `allow_duplicate` Output in each emitting callback; it grows one
  small entry per channel seen in a session, negligible for a per-client
  memory store. Accepted limitation: two concurrent callbacks can race the
  registry and lose one write, leaving one stale instance to expire on its
  own timer beside the new one for up to 8 s — rare, transient,
  self-healing. Accepted cosmetics from the POC: a toast that arrived as a
  replacement auto-closes without its own exit fade (it pops out at full
  opacity), and bystander toasts bounce upward for roughly 280 ms during a
  replacement.
- Success clears the failure channel. A failure channel claims to show the
  latest attempt's outcome, so a successful retry must not leave the
  previous failure on screen beside the green success toast. Each success
  emission (including the orange split outcome, whose import did land) also
  sends a `hide` for its operation's failure channel ids: import success
  hides `imported-playlist-failed-notification`, delete success hides
  `deleted-playlist-failed-notification`, cleanup success hides
  `superseded-cleanup-failed-notification`, and rank-refresh success hides
  the merged `rank-refresh-problem` channel and the username-unset channel
  (a success proves a username is configured, so the blue claim cannot
  still stand — reachable when the user sets the username in Settings and
  refreshes again inside one lifetime). Cross-clears ride the same hide
  prop as the mechanism itself: the emission looks up the target channel's
  current instance id in the registry and appends it to the hide list.
  Hiding an id that is not on screen is a clean no-op — measured in the
  POC, no longer an open verification item. Alternative rejected: widening
  channel identity to span all outcomes of an operation (one id for failure
  and success alike) would make two consecutive distinct successes replace
  each other, breaking rule 1 for the success toasts.
- Keep unchanged in contract: `run-verdict` (rule 2, ratified — its
  replacement mechanism migrates to hide-and-reshow under D3, its
  one-run-one-toast contract untouched), `run-import-failure` (already
  rule 3), and `steam-id-mismatch` and `startup-playlist-warning-{n}`
  (rule 4 instances, the latter already unique per warning).
- Spec work in the implementation PR: add the policy to
  `docs/specs/notifications.md` — listing `run-import-failure`'s cross-tick
  swallowing as an explicit accepted exception rather than implying the
  inventory conforms in full — re-annotate the inventory rows with their
  pattern, and update every spec that owns a converting toast's behavior:
  the notifications, playlists, and rank specs, plus `docs/specs/settings.md`
  (its setup-card section owns the `setup-card-skip-refused-notification`
  refusal semantics). The conversions supersede ratified clauses, so per
  convention the old decisions stay and get supersession markers in
  `docs/decision_log.md`: the 2026-08-03 entry's per-click-id
  presentation-standard exception and its distinct-rank-ids rationale, and
  the 2026-08-09 unset-username entry's per-click blue-toast clause.

**Copy:** none under the recommended design. No user-facing string is added
or edited; only notification ids and replacement/timer semantics change.
(Stated explicitly because the copy-block convention requires proposals to
gather any strings they touch.) The one path that would change this is D2's
attempt-count alternative: choosing it introduces new strings, and this
block must then be amended with the exact copy before implementation.

## Out of scope

- `run-import-failure`'s own cross-tick swallowing (a second batch inside
  8 s is dropped). Accepted for now: it is a background burst channel where
  anti-flood wins, the folded copy already points at debug.log, and no user
  report exists. If it ever surfaces, the fix is a replacement channel, not
  uuids.
- The research's broader "error toasts should be banners" position. This
  app's red toasts report transient outcomes of just-clicked actions in a
  single-user desktop app; re-platforming them onto persistent surfaces is a
  much larger question, deliberately not opened here.
- All copy changes, including the app-wide messaging sweep tracked in the
  em-dash proposal (PR #247).
- Mantine's visible-toast `limit` and queueing defaults stay untouched.
- No roadmap entry: this is a UX-consistency fix, below the roadmap's
  product-milestone granularity.

## Delivery plan

- **PR 1 (this PR):** the proposal.
- **PR 2 (implementation, after D1/D2/D3 are ruled):** the hide-and-reshow
  helper and instance registry, the four subject-keyed channel conversions
  (three playlist successes keyed by canonical code, refresh success keyed
  by scenario), the seven single-identity channel conversions, the merged
  rank problem channel, the success-clears wiring, the `run-verdict`
  migration and `upsert_toast` deletion (per D3), test updates, the spec
  additions above, and the proposal-shipping checklist including deleting
  this file. Single small PR; no dependency beyond ratification.
  Kickoff prompt recommendation per convention: Opus 5 at effort high — the
  changes are mechanical id and wiring edits with a test tail, and added
  model capability beyond that would not change the outcome.

## Testing

- This PR: `tests/test_docs.py` gates the Status line, section order, and
  link integrity.
- Implementation PR: update the tests that assert the fixed toast ids;
  regression-test that imports of two different playlists emit instances
  under distinct channel keys with no cross-hide (the reported bug) while
  an import, delete, and re-import of one playlist emits under the same
  channel key and hides the prior instance (replacement, not a stack);
  assert every channel emission pairs a fresh-instance show with a hide of
  the registry's previous instance and rotates the registry entry; assert
  each success path's hide list also carries its operation's problem
  channel (and, for rank refresh, the username-unset channel); cover the
  rank family (a hard failure followed by a served-stale retry emits under
  the one problem key, two refreshes of one scenario share a channel key
  while two scenarios do not); assert `run-verdict` rides the same
  mechanism and that `upsert_toast` is gone (per D3). The POC's
  browser-level findings are evidence, not gates — unit tests assert
  emission shapes and registry state. Run the standard five local gates.
