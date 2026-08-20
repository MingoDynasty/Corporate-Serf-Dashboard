# Run Notifications Master Switch

Status: Proposed
Date: 2026-08-20

## TL;DR

Every run the app notices produces a toast, and there is no way to turn that
off. The one notification switch that exists controls only whether a run is
judged against the score threshold, and its wording wrongly suggests it
silences run toasts entirely. This proposal adds a single master switch to
Chart options that turns all run toasts off, and corrects the misleading
wording on the existing switch.

## Decisions needed

### D1 — Does the master switch silence the backlog digest too?

Status: Open

**Recommendation: yes.** The "While you were away" digest is the same
notification family as the live run toast: it shares the run-verdict toast id,
it is built by the same function, and it reports the same kind of event. A
person turning run notifications off is saying "do not toast me about runs";
a digest that survives the off switch would read as a bug, not a feature.
Choosing differently would preserve a rare catch-up toast at the cost of an
off switch that is not quite off.

### D2 — Labels and help text

Status: Open

UI copy is a maintainer decision. Recommended wording (app copy, so short
sentences and no em dashes):

- New inspector group **Notifications**, holding the master switch.
- Master switch label **Run Notifications**; help text: "Shows a toast after
  each new run. Turn this off to update the chart silently."
- The existing switch renamed **Score Threshold Verdict**; help text: "Judges
  each new run against the score threshold. The run notification then reports
  pass or fail." It stays in the Score Threshold group, beside the percentage
  it depends on.

"Verdict" is already the app's word for what titles a run toast; the README
and the code both use it. The consequence of choosing different wording is
copy only — the wiring is identical.

---

Ratified by the maintainer in conversation (2026-08-20): the feature itself
(a user-facing switch that can turn run toasts off), bundling the
threshold-switch copy correction into the same implementation PR, and
deferring app-wide notifications entirely (see Out of scope). Everything
else, including the recommendations above and the mechanical guidance below,
is open to review challenge.

## Problem

The run toast is built by `_build_run_event_notification` in
`source/pages/home.py`, inside the `generate_graph` callback, and comes in
three shapes sharing one replaceable toast id:

- a **threshold verdict** (pass or fail against the score-threshold goal),
  when the Score Threshold Notification switch is on, a goal percentage is
  set, and the scenario has a previous high score to judge against;
- a **top-N placement** toast ("New 3rd-best score") — fires unconditionally
  when a run places, with no switch governing it;
- the **"While you were away" backlog digest** when several runs accrued —
  also unconditional; with no verdict it still fires as a neutral digest.

So there is currently no way to silence run toasts. The one switch that
sounds like it does ("Score Threshold Notification", inspector group "Score
Threshold") decides only whether a run is judged; placement toasts and
digests fire regardless. A standing code comment beside that switch (dated
2026-08-08, from the notification redesign) flags exactly this: the copy
reads as a wholesale gate for run notifications when it is not, deferred
"with the rest of the group's copy". This proposal is that revisit, for the
two strings it touches.

Other toast families are deliberately not part of the problem: run-import
failures, rank-refresh feedback, and the Steam-ID mismatch notice are error
or action feedback, not per-run verdicts.

## Design

**The switch.** One new `dmc.Switch` (`run-notification-switch`) in the Chart
options inspector, default on, `persistence=True` like every sibling control.
Default on because current behavior stays the default; a toggle nobody flips
changes nothing.

**The wiring.** One new `Input` on `generate_graph`; the flag threads into
`_build_run_event_notification`, which returns `None` first thing when the
switch is off. Gating inside that function keeps it the single place run
toasts are born — the live and backlog paths both flow through it — and keeps
the guard a pure-function behavior the existing test style covers directly.

**What off means.** Only the toast is suppressed. The plot still updates,
scenario auto-switch still follows a new run, and every other toast family is
untouched.

**Interplay with the existing switch.** The master switch gates the family;
the threshold switch keeps deciding whether a judged verdict headlines the
toast. Master off means silence regardless of the threshold switch. Master on
with the threshold switch off reproduces today's judging-off behavior:
placement toasts and neutral digests only.

**Storage.** Browser-local Dash persistence, exactly like the other Chart
options controls. Not `data/settings.json`, which is deliberately scoped to
the stats directory and the KovaaK's identity behind a Save model, and not
`config.toml`, which holds human-owned boot facts. This is the same placement
rule the scenario point customization proposal ratified for its controls: the
inspector owns browser-persisted presentation preferences.

**Inspector placement.** The Notifications group goes at the end of the
inspector, after Score Threshold. The ratified point customization proposal
inserts its Run Data Points group between Overlays and Score Threshold; the
two changes add distinct groups, so whichever implementation PR merges second
rebases over a trivial textual conflict with no semantic interaction.

**Copy correction.** The two strings in D2 change, and the 2026-08-08 code
comment they resolve is removed.

## Delivery plan

One implementation PR: the switch, the wiring and guard, the copy correction,
tests, and the proposal-shipping documentation cleanup (decision-log
distillation if the maintainer wants one, the architecture.md inspector
sentence, the README run-notifications bullet, product.md, roadmap). No hard
dependency on other in-flight work; the point customization implementation PR
is a soft ordering dependency only, through the shared inspector layout
function.

## Out of scope

- **App-wide notifications.** Run toasts still appear only on the Scenario
  Performance page, because the producing interval, store, and preferences
  are mounted in that page's layout even though the toast container is
  shell-hosted. Making the producer app-wide is a redesign of the
  queue-to-UI flow with its own product questions (judging runs against
  their own scenario rather than the selected one, and what becomes of the
  backlog digest). Deliberately deferred; the maintainer is still weighing
  it, and nothing here forecloses it — the switch gates toast production
  wherever that production later runs, and Dash persistence survives a
  same-id component move.
- **Per-family notification preferences.** No toggles for import failures,
  rank-refresh feedback, or other toast families.
- **The wider copy sweep.** The deferred all-messaging review of shipped
  strings stays deferred; only the two strings named in D2 change.
- **Toast content and mechanics.** No change to toast wording beyond D2, ids,
  replacement semantics, or lifetimes.

## Testing

- Unit tests beside the existing ones in `tests/test_home_run_events.py`:
  with the switch off, `_build_run_event_notification` returns `None` for all
  three shapes — live threshold verdict, live placement, and backlog digest;
  with it on, the existing tests already pin current behavior.
- A callback-level case: `generate_graph` sends no notification and leaves
  the toast-lifetime counter untouched when run events fire with the switch
  off.
- A layout case: the switch mounts in its group, default on, persistence
  enabled.
- The standard local gates (pytest, ruff format, ruff check, mypy,
  compileall).
