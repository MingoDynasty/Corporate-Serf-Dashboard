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
while its toast is still up replaces that toast in place, so a retry keeps
its answer on screen instead of being silently dropped. Reports about
different subjects still stack side by side, and a success also clears the
leftover failure message it answers.

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
  replace-in-place (`upsert_toast`).** Recommended: convert the three
  per-action failure toasts (`imported-playlist-failed-notification`,
  `deleted-playlist-failed-notification`,
  `superseded-cleanup-failed-notification`), the two refusal toasts
  (`visibility-refused-notification`,
  `setup-card-skip-refused-notification`), the constant-copy
  `superseded-cleanup-successful-notification`, and
  `rank-refresh-username-unset-{uuid}` (today a unique-id stacker whose
  repeats are byte-identical) to single-id upsert channels. The rank-refresh
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
  documented anti-pattern. Ratifying D2 also ratifies its two supporting
  mechanics in Design: the per-channel lifetime sequence, without which a
  retry's timer restart silently fails whenever channels interleave, and
  success-clears-failure, without which a stale failure toast outlives the
  success that answers it. Be clear-eyed about what upsert delivers: the
  replacement restarts the 8 s timer, but at the moment of the click nothing
  visibly changes — no re-animation, no new text. The honest claim is an
  invariant, not an animation: while the user keeps retrying, the answer
  stays on screen, where the status quo lets it vanish mid-retry or drops
  the retry's answer entirely. If stronger per-click feedback is wanted, the
  alternative is distinguishing copy — an attempt count such as "(attempt
  2)" appended on repeat — which buys a visible mutation at the cost of new
  user-facing strings (a Copy block) and per-callback attempt state; not
  recommended, but it is a real option and the material difference is
  exactly that visibility. Keeping the stable ids (status quo) remains the
  do-nothing alternative: a retry inside the 8 s window then gets no answer
  at all, the same dead-UI failure the import bug exhibits.

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
   place via `upsert_toast` so the timer restarts and the toast stays up
   while its condition keeps recurring. Identity follows the semantic lane.
   An operation's problem lane is one channel: its mutually exclusive
   outcome flavors share a single id with a payload that differs
   (hard-failure and served-stale are one channel), so two contradictory
   claims about the same latest attempt can never be on screen together.
   Success lanes and standing-condition lanes are their own channels, keyed
   by subject when independent subjects can be in flight at once (per
   scenario, per playlist code). Lanes interact only through explicit
   cross-clears: when the operation behind a problem lane reports success,
   the success emission clears that problem channel, so a stale failure
   never outlives the answer that supersedes it.
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
- Per-channel lifetime state. `upsert_toast`'s timer restart works by
  alternating between two indistinguishable `autoClose` values, and Mantine
  re-arms only when the value differs from the one the toast is showing —
  so the alternation must be sequenced per notification id, not globally. A
  single shared counter breaks under interleaving: channel A at sequence 0
  (8000), channel B at 1 (8001), channel A's retry at 2 (8000 again) — the
  retry's timer silently fails to restart. The `toast-lifetime-sequence`
  store therefore becomes a dict keyed by notification id, `run-verdict`'s
  existing scalar usage migrates onto it so there is one mechanism, and
  each converting callback gains a State and an `allow_duplicate` Output on
  that store. Subject-keyed channels put their dynamic ids in the same
  dict; it grows by one small entry per subject seen in a session, which
  is negligible for a per-client memory store. Accepted limitation: two concurrent callbacks can race the
  dict write and lose one bump, which degrades that single retry to today's
  no-restart behavior — rare, and never worse than the status quo.
- Success clears the failure channel. A failure channel claims to show the
  latest attempt's outcome, so a successful retry must not leave the
  previous failure on screen beside the green success toast. Each success
  emission (including the orange split outcome, whose import did land) also
  sends a `hide` for its operation's failure channel ids: import success
  hides `imported-playlist-failed-notification`, delete success hides
  `deleted-playlist-failed-notification`, cleanup success hides
  `superseded-cleanup-failed-notification`, and rank-refresh success hides
  the merged `rank-refresh-problem` channel. Mechanism note: in
  dash-mantine-components 2.8.0 hiding is not a `sendNotifications` action
  but the container's separate hide prop, whose effect runs after the send
  effect (the 2026-08-03 quiet-notification-layer decision-log entry records
  why a hide-then-show of one id therefore cannot work). That ordering is harmless
  here because the hidden id and the shown id always differ; the
  implementation PR still verifies that hiding an id that is not on screen
  is a clean no-op before relying on it. Alternative rejected: widening
  channel identity to span all outcomes of an operation (one id for failure
  and success alike) would make two consecutive distinct successes replace
  each other, breaking rule 1 for the success toasts.
- Keep unchanged: `run-verdict` (already rule 2, ratified),
  `run-import-failure` (already rule 3), and `steam-id-mismatch` and
  `startup-playlist-warning-{n}` (rule 4 instances, the latter already
  unique per warning).
- Spec work in the implementation PR: add the policy to
  `docs/specs/notifications.md` — listing `run-import-failure`'s cross-tick
  swallowing as an explicit accepted exception rather than implying the
  inventory conforms in full — re-annotate the inventory rows with their
  pattern, and update every spec that owns a converting toast's behavior:
  the notifications, playlists, and rank specs, plus `docs/specs/settings.md`
  (its setup-card section owns the `setup-card-skip-refused-notification`
  refusal semantics).

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
  report exists. If it ever surfaces, the fix is upsert, not uuids.
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
- **PR 2 (implementation, after D1/D2 are ruled):** the four subject-keyed
  channel conversions (three playlist successes keyed by canonical code,
  refresh success keyed by scenario), the seven single-id channel
  conversions, the merged rank problem channel, the per-channel lifetime
  store, the success-clears-failure wiring, test updates, the spec
  additions above, and the proposal-shipping checklist including deleting
  this file. Single small PR; no dependency beyond ratification.
  Kickoff prompt recommendation per convention: Opus 5 at effort high — the
  changes are mechanical id and wiring edits with a test tail, and added
  model capability beyond that would not change the outcome.

## Testing

- This PR: `tests/test_docs.py` gates the Status line, section order, and
  link integrity.
- Implementation PR: update the tests that assert the fixed toast ids;
  regression-test that imports of two different playlists emit toasts with
  distinct subject keys (the reported bug) while an import, delete, and
  re-import of one playlist re-emits the same subject-keyed id (replacement,
  not a stack); assert the failure and refusal paths emit
  `upsert_toast`'s update+show pair and bump their own channel's sequence;
  regression-test the interleaving case (channel A, channel B, channel A
  again — A's second emission must carry a different `autoClose` than its
  first); assert each success path also hides its operation's failure
  channel ids; cover the rank family's new shape (a hard failure followed
  by a served-stale retry emits the same channel id, two refreshes of one
  scenario emit the same subject-keyed id while two scenarios emit
  different ids, and a refresh success hides the problem channel); run the
  standard five local gates.
