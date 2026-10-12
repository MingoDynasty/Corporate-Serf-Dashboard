# 2026-08-03: One Quiet Notification Layer With Verdict-Carrying Copy

Status: Accepted; three clauses are superseded by the 2026-08-31
["Repeatable Toasts Replace In Place With A Visible Re-Entry"](2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry.md)
entry -- the per-click-id exception to the stable-id rule, the distinct-ids
rationale for the two refresh-failure toasts, and the absolute reading of "at
most one run-verdict toast is visible at a time". Each is marked in place below.
Everything else here stands, including the routing policy that decides which
events toast at all.

The dashboard now stays quiet during normal play. Toasts are reserved for
things the user did, achievements worth interrupting for, and failures they
would act on; a condition that stays true explains itself where it happens
instead of popping up again on every trigger. Each run produces at most one
toast, its title states the verdict, and a newer run replaces the one on
screen rather than stacking beside it.

Predecessor: the
[2026-08-03 background-diagnostics entry](2026-08-03-background-rank-diagnostics-are-console-only.md)
deleted four toasts under this policy before the policy itself was recorded;
that entry stands unchanged and this one supersedes nothing. Shipped in
PRs #194, #196, #198, and #200; design in #82 and #195.

**One delivery path.** The app had two notification subsystems. The
logging-driven one routed Python `logging` records into Mantine toasts through
an in-repo handler, and it is deleted: the handler, its module-level queue, its
drain callback, and the tests covering that machinery. `logging` remains the
console and file record; it no longer reaches the screen. The decisive argument
is that **a log level is not a routing policy** — the bridge made every
`dash_logger` call a toast, with a severity picked at the call site standing in
for a judgment that belongs to the event. It also gave every record a fresh
`uuid` id, so records stacked instead of replacing, under generic
"Info/Warning/Error" titles. Everything now goes through `sendNotifications` on
the shell's one `dmc.NotificationContainer`, fed by payloads from the
`utilities/notifications.py` builder.

**Routing policy — who gets a toast.** Decided per event, in this order:

- *Persistent condition* (misconfiguration, missing data, degraded feature) →
  **in-place UI** at the point of impact, never a toast. Conditions do not stop
  being true when a toast expires. Two named exceptions, both persistent
  conditions with no in-place home, both surfaced once per lifecycle rather
  than once per trigger: the Steam-ID mismatch gets one toast per app session,
  and the startup playlist warnings one batch per boot. Both persist until
  dismissed.
- *Automatic failure* during passive navigation → **no toast**; the field state
  conveys it, with a console `logger.warning` retained.
- *User-initiated failure* (Import, manual Refresh) → **error toast**; the user
  asked and deserves the result. A run file that failed to import sits here
  too: playing the run was the user's act, and nothing else tells them it never
  recorded.
- *Achievement / coaching* → one toast per run.
- *Diagnostic* (thread failures, timeouts with automatic fallback) → **console
  log only**.

Litmus tests, in order: is it a state rather than an event? → in-place. Is it
already visible somewhere (plot point, Position field, empty-state canvas,
warmup status strip)? → nothing. Would the user act differently for having seen
it right now? No → log, not toast.

**Background threads never drive UI outputs.** They publish to typed shared
state that an interval callback polls. There is deliberately no general event
bus: each channel carries one kind of event and its consumer decides what the
user sees. The deleted level-driven queue is the anti-pattern the rule exists
to prevent. The one background toast that survived the routing verdicts — the
run-import failure — got its own typed deque rather than a field grafted onto
the run-event queue. The sanctioned channels are enumerated in
[architecture.md](../../architecture.md).

**One run, one toast.** Every run verdict and the catch-up digest share the
stable id `run-verdict`. When a run both places top-N and earns a threshold
verdict, the threshold verdict is the headline and the placement a trailing
detail; a run that earns neither emits nothing, because the new point on the
plot is the confirmation that it landed. Four behaviors are normative, and the
mechanism is not:

- at most one run-verdict toast is visible at a time (as amended 2026-08-31:
  true once a response has been applied -- during the ~250 ms replacement
  crossfade the outgoing instance is still animating out);
- a later verdict replaces the visible one, the backlog digest included;
- the replacement receives a full toast lifetime, never the remainder of the
  old timer;
- all of the above holds per browser client and survives page navigation.

The mechanism that satisfies them on DMC 2.8.0, verified against the shipped
bundle: a bare `show` cannot replace (the store ignores it for an id already on
screen) and `update` is a no-op for an id that is not, so each emission sends
**both actions with the same id and payload** and whichever matches applies.
Mantine's auto-close timer is a React effect keyed on the resolved duration
alone, so an `update` carrying the same duration leaves the original timer
running; the payload therefore alternates between two indistinguishable
durations (8000/8001 ms) to force the effect to cancel and re-arm. The
alternation counter is a `dcc.Store` in `app_shell.py` beside the container,
**not** in Home's page layout: a toast outlives the page that emitted it, and a
page-scoped store would reset on remount and hand a still-visible toast the
duration it is already displaying. `hide` cannot substitute — it is a separate
prop whose effect runs after the `sendNotifications` effect, so a hide-then-show
pair in one response would hide the toast it just showed.
`tests/test_home_run_verdict_lifetime.py` models those store semantics against a
clock and asserts the behaviors in elapsed time; it is the upgrade guard for
future DMC versions.

**Presentation standards.**

- Stable, semantic notification ids; dedupe or replace by id. One named
  exception: repeatable user-action results use a **per-click id** — the
  manual-refresh confirmation, where `show` with a reused id would swallow the
  second of two deliberate back-to-back results. *(Superseded 2026-08-31: the
  confirmation is a per-scenario channel and every repeatable result re-pops by
  showing a fresh instance id, so no toast carries a per-click id.)*
- **The title carries the verdict.** Title plus color tell the whole story from
  across the room; never the literal word "Notification".
- **The message leads with the scenario.** Sensitivity is a trailing qualifier:
  top-N is per-sensitivity, so it matters, but it is never the subject.
- One nominal `autoClose` duration, with two deliberate exceptions that persist
  until dismissed — the Steam-ID mismatch and the startup playlist warnings,
  both of which fire when the user may not be looking.
- A failing threshold verdict names the target it missed: one extra number with
  real motivational value.
- No "New personal best!" retitle. A new overall PB necessarily places 1st
  within its sensitivity, so it already earns the run-verdict toast — titled
  "New best score" when unjudged, or carrying the threshold verdict when
  judged; retitling it would create by the back door the dedicated PB toast
  that `product.md` records as declined.

Two manual-refresh failure toasts deliberately share the title "Position
refresh failed" under distinct ids (red when nothing usable came back, yellow
when a cached position was served). They are mutually exclusive outcomes of one
click, and the distinct ids keep a later result from being swallowed by `show`'s
dedupe. *(Superseded 2026-08-31: being mutually exclusive is exactly why they
are now one `rank-refresh-problem` channel — under distinct ids a hard failure
followed by a served-stale retry left both on screen contradicting each other
about the same attempt.)* Softening the red to yellow is coupled to giving the
served-stale toast a title of its own — without that, only the color separates
them — and is left open in [tech_debt.md](../../tech_debt.md). *(Superseded in
part, for copy, 2026-09-14: the served-stale toast now has that title of its
own, "Refresh failed · position from cache", while the red hard failure keeps
"Position refresh failed"; the color question stays open. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out.md).)*
*(Superseded again, for copy, 2026-09-22: the served-stale title is now
"Refresh failed · data from cache", chosen by the maintainer over "Refresh
failed · from cache", and when the cached readout includes a total its
message reads "Couldn't refresh. The position and total shown are from
cache." A failed position request asks for no total, so that total predates
the click too, and once a partial refresh began reporting the total on its
own, naming only the position read as though the total had refreshed. With no
total on screen the message still names only the position, and the red hard
failure keeps its message because it never sees what the field shows. See
[scenario_rank.md](../../specs/scenario_rank.md#failure-handling).)*
*(Resolved 2026-09-27: the hard failure stays red. See
[The Manual-Refresh Hard Failure Stays Red](2026-09-27-the-manual-refresh-hard-failure-stays-red.md).)*

**Deliberately left open: do background rank events deserve a real toast?**
"Your rank updated after that PB" and "Position update timed out" are
console-only under the background-thread rule. Surfacing either needs a
conformant channel — a dedicated typed event queue or polled cache state, never
the run-specific `message_queue` — and the run-import-failure queue is the
pattern to copy if it is ever wanted. It pairs with the unbuilt "rank improved"
toast and should be decided with it, not piecemeal.
