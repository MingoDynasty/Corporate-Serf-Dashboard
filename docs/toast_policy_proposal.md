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
as the app's standing toast policy, splitting the toasts along one test. A
toast whose repeats always read differently stacks as separate messages. A
toast whose repeats could read the same replaces its predecessor in place, so
a retry keeps its answer on screen instead of being silently dropped, and a
success also clears the leftover failure message it answers.

## Decisions needed

- **D1 — Adopt the event / channel / burst policy as the standing rule.**
  Recommended: yes, recorded in `docs/specs/notifications.md` so every future
  toast picks its id pattern deliberately. Choosing differently means each new
  toast re-litigates the choice ad hoc, which is how today's mixed inventory
  (three patterns, no stated rule) came to be.
- **D2 — Toasts whose repeats can carry identical copy become
  replace-in-place (`upsert_toast`).** Recommended: convert the three
  per-action failure toasts (`imported-playlist-failed-notification`,
  `deleted-playlist-failed-notification`,
  `superseded-cleanup-failed-notification`), the four refusal toasts
  (`rank-refresh-failed`, `rank-refresh-stale`,
  `visibility-refused-notification`,
  `setup-card-skip-refused-notification`), the constant-copy
  `superseded-cleanup-successful-notification`, and
  `rank-refresh-username-unset-{uuid}` (today a unique-id stacker whose
  repeats are byte-identical) to the upsert pattern. These are the toasts
  whose repeats can carry identical text — most because a user retries
  against them (the failed-import modal deliberately keeps the pasted code
  for a quick resubmit), and stacking identical toasts is the literature's
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
  at all, the same dead-UI failure the import bug exhibits. The success-side
  conversions in the Design section follow from D1 directly.

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
lacks is the rule for which one a new toast should use, and twelve toasts sit
on the wrong side of that rule today.

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

1. **Event toasts** — each emission reports a distinct user action's outcome
   (an import, a delete). Unique id per emission (`-{uuid}` suffix), so
   occurrences stack. Stacking is only legal when the copy distinguishes the
   occurrences: the message must name its subject, and a toast whose repeats
   can carry identical text (every retryable failure) is not an event toast —
   it is a channel toast, rule 2.
2. **Channel toasts** — the toast is the current state of one ongoing thing
   (the latest run's verdict, the latest attempt's failure). One stable id,
   replaced in place via `upsert_toast` so the timer restarts and the toast
   stays up while its condition keeps recurring. When the operation behind a
   failure channel also reports success, the success emission clears that
   failure channel, so a stale failure never outlives the answer that
   supersedes it.
3. **Burst toasts** — many same-type events where the aggregate is the
   message ("3 new run files could not be processed"). Fold into one summary
   carrying a count, and point at where the individual events are recorded.
4. A standing condition the user must notice once (a config mismatch, a
   startup warning) may additionally be persistent (`auto_close=False`) and
   process- or session-gated; that is orthogonal to 1–3.

**Mechanical application to today's inventory:**

- Convert to event toasts (rule 1), the `rank-refresh-notification-{uuid}`
  pattern: the three success toasts whose copy names their subject —
  `imported-playlist-successful-notification`,
  `imported-playlist-visibility-failed-notification` (the import did land;
  occurrences are distinct playlists), and
  `deleted-playlist-successful-notification`. Their occurrences cannot
  repeat with identical text: each names its playlist, and the same playlist
  cannot succeed twice inside one toast lifetime. Only the import success
  has a reachable swallowing window today; the delete success converts for
  uniformity under D1.
- Convert to channel toasts (rule 2), pending D2: the three per-action
  failure toasts, the four refusal toasts,
  `superseded-cleanup-successful-notification`, and
  `rank-refresh-username-unset-{uuid}`. The failures and refusals are
  retried — the failed-import modal deliberately keeps the pasted code for
  resubmission — and a retry of the same input reproduces the same message,
  so they fail rule 1's distinguishability test; the toast instead reflects
  the latest attempt's outcome, which the serial modal workflows make
  unambiguous. The cleanup success fails the same test differently: its
  title and message are constant ("Leftover files deleted" / "Deleted
  leftover playlist files."), and while a second cleanup inside one toast
  lifetime is practically unreachable, the policy classifies by copy, not
  by reachability — as a channel it needs no new copy and no observable
  behavior changes. The username-unset toast is today's one uuid stacker
  with byte-identical repeats (spam-clicking Refresh with no username
  stacks identical blue toasts), so it moves to a stable channel id under
  the same test.
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
  that store. Accepted limitation: two concurrent callbacks can race the
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
  `rank-refresh-failed` and `rank-refresh-stale`. Mechanism note: in
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
  `run-import-failure` (already rule 3), `steam-id-mismatch` and
  `startup-playlist-warning-{n}` (rule 4 instances, the latter already
  unique per warning), and `rank-refresh-notification-{uuid}` (already an
  event toast with subject-naming copy).
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
- **PR 2 (implementation, after D1/D2 are ruled):** the three event-toast id
  conversions, the nine upsert conversions (or fewer, per D2), the
  per-channel lifetime store, the success-clears-failure wiring, test
  updates, the spec additions above, and the proposal-shipping checklist
  including deleting this file. Single small PR; no dependency beyond
  ratification.
  Kickoff prompt recommendation per convention: Opus 5 at effort high — the
  changes are mechanical id and wiring edits with a test tail, and added
  model capability beyond that would not change the outcome.

## Testing

- This PR: `tests/test_docs.py` gates the Status line, section order, and
  link integrity.
- Implementation PR: update the tests that assert the fixed toast ids;
  regression-test that two successive import successes emit toasts with
  distinct ids (the reported bug); assert the failure and refusal paths emit
  `upsert_toast`'s update+show pair and bump their own channel's sequence;
  regression-test the interleaving case (channel A, channel B, channel A
  again — A's second emission must carry a different `autoClose` than its
  first); assert each success path also hides its operation's failure
  channel ids; run the standard five local gates.
