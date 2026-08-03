# Notification System Proposal

Status: Proposed
Date: 2026-07-09 (refreshed 2026-08-03 against main after PRs #83–#193)

## TL;DR

During normal play the dashboard buries its useful toasts in noise: red
errors about an unconfigured username on every scenario switch, duplicate
toasts for a single run, and a "Graph updated!" toast that carries no
information. The fix is one delivery path with a routing policy: persistent
conditions render in place instead of re-toasting, passive background
activity stays quiet, each run produces at most one verdict toast, and
titles carry the verdict. The redesign ships as three small PRs, and the
first one alone resolves the original audit complaint.

## Decisions needed

1. **Adopt the routing policy and one-toast-per-run design.** Recommended:
   yes — the policy (persistent conditions in-place, passive activity
   quiet, one run one toast, user-initiated actions always get their
   result) is the product call everything below executes. Choosing
   differently means re-judging the inventory verdicts row by row.
2. **Sequencing: queue this as the next milestone after the in-flight
   settings-detection work** (the `roadmap.md` edit in this PR does so),
   ahead of run history and score trend. Recommended: yes — three small
   PRs, kills a daily-use noise complaint, and the background-delivery fix
   (PR #115) made the formerly dead timeout errors *start rendering*, so
   the noise is worse than when the audit ran. Deferring keeps that noise
   through the next milestone.

## Problem

The app has grown **two independent notification subsystems**, and the split is
the root cause of the noise reported in the UI audit:

- **System A — logging-driven.** A Python logger (`dash_logger`) routes
  `logging` records into DMC notifications through the in-repo
  `QueueingNotificationsLogHandler` (`utilities/dash_logging.py`; it replaced
  the `dash-extensions` `NotificationsLogHandler` bridge in PR #115). Inside a
  Dash callback the record rides the response via `ctx.updated_props`; on a
  plain thread (watchdog, Timer chains, the warmup worker) it is queued
  module-level and drained by `flush_background_notifications` on Home's poll
  interval. Every record gets a fresh `uuid` id, so these **stack rather than
  replace**; titles are the generic "Info/Warning/Error"; and the log *level*
  is the only routing decision — any `dash_logger` call is a toast, whatever
  its subject. Background records render only while Home is open, so they can
  arrive minutes late as a batch on the next Home visit.
- **System B — callback-driven.** Explicit `sendNotifications` on the shell's
  `dmc.NotificationContainer`, fed by payload dicts in `home.py`,
  `playlists.py`, and `playlist_scenarios.py`. These use **stable ids, which
  suppress duplicates**: DMC's `show` action silently ignores a payload whose
  id is already on screen (it does *not* replace it — replacement needs the
  separate `update` action, see D5). Custom titles, colors, and icons.

Two id conventions, two title vocabularies, two delivery latencies. During a
play session System A piles up while System B at least suppresses repeats.
The audit found four System A error toasts that could never render (the
watchdog's "Could not start position update" and the three rank-timer
messages); PR #115 fixed delivery — so **those red generic "Error" toasts now
actually appear**, batched onto the next Home visit. The delivery bug is gone
and the noise is correspondingly worse.

System B has stacking sources of its own: the top-N toast and the
score-threshold toast use *different* stable ids, so a single run that
qualifies for both fires two stacked toasts — and the "Graph updated!" fallback
fires whenever a run is not threshold-judged, *independent of top-N*, so a
top-N run with the threshold switch off also fires two.

The most visible symptom: with the KovaaK's username unset (**the default**),
an unset username is a *supported* state — the app runs fully offline, per the
2026-08-01 "No Username Stays Fully Offline" decision — yet every
network-allowed rank render (scenario switch, new run) reports that state as a
red **Error** toast. It auto-closes after 8s, but re-fires constantly and
stacks (unique ids), so it reads as a persistent wall of red. Since the audit,
the username moved from `config.toml` into the app-owned settings store with a
Settings page (PRs #181–#184), and identity *detection* is in flight
([settings_detection_proposal.md](./settings_detection_proposal.md)) — the
unset state will get rarer and easier to fix, but it remains supported and
must stop being an error. That same 2026-08-01 entry explicitly deferred
"treat leaderboard-features-off as a normal quiet state rather than a red
error, pointing at how to enable it" until a settings page existed to point
at; the settings page now exists, and this proposal's inventory row 1 is that
deferred kernel's toast half.

## Goals / non-goals

**Goals**
- One delivery path with one set of conventions.
- Passive, automatic activity is quiet by default; toasts are reserved for
  achievements, coaching, and the results of user-initiated actions.
- One run produces at most one toast.
- Routing decided per event by policy, never implicitly by log level.
- Titles that carry the verdict; copy that leads with the scenario.

**Non-goals**
- Persistent/reviewable notification history — that is the separate
  [Run History](./run_history_proposal.md) work; this proposal keeps toasts
  ephemeral.
- Changing what counts as a top-N score, or the score-threshold verdict rule
  (settled 2026-07-08 in `decision_log.md`).
- New background→UI plumbing for *rank* events (see Open questions). The one
  typed queue PR 2 adds (row 18) replaces existing delivery, it does not add
  a new event source.
- Skipping the futile no-username progressive position fill on playlist pages
  — the other half of the deferred quiet-state kernel; same spirit, separate
  in-page-status change, tracked by the 2026-08-01 decision entry.

## Current inventory

Re-verified row by row against post-#193 main on 2026-08-03. Rows 1–17 are
the original audit; rows 18–21 are producers added since (marked *new*).

| # | Notification | Fires when | System | Renders? | Verdict |
|---|---|---|---|---|---|
| 1 | 🔴 "KovaaK's username is not configured" | Every scenario switch / new run, username unset (default) | A | yes | **Remove toast**; inline hint on the Position field pointing at Settings + one startup console INFO |
| 2 | 🔴 Rank fetch/resolve failed | Scenario switch / run, transient API failure | A | yes | **Remove toast**; inline field state, Refresh is the retry |
| 3 | 🟡 Steam-ID mismatch | Scenario switch when `steam_id` disagrees | A | yes | **Keep, once per app session**, persistent until dismissed |
| 4 | 🟡 "No scenario data found" | Selecting an unplayed scenario | A | yes | **Remove** (on-canvas empty state already covers it) |
| 5 | 🟡 "No scenario data for the given date range" | Date filter empties the plot (two call sites since the figure-builder split) | A | yes | **Remove** (same) |
| 6 | 🔴 "Position refresh for X failed" | Manual Refresh errors | A | yes | **Keep → move to B** |
| 7 | 🟡 "Insufficient data for playlist X" | Journey page, selected playlist has no data | A | yes | **Modify → in-page empty state**, no toast |
| 8 | 🔴 "Could not start position update for X" | Watchdog fails to schedule refresh | A | yes, queued — next Home tick | **Delete** (console log stays) |
| 9 | 🔴 "Position update timed out / misconfigured / failed" | Rank-freshness timer chain | A | yes, queued — next Home tick | **Delete** (console log stays) |
| 10 | 🟢 New top-N score | Run makes top-N for its sensitivity | B | yes | **Merge into one run-verdict toast** (D5) + rewrite copy |
| 11 | 🟢/🟡 Score threshold pass/fail | Threshold switch on + prior PB exists | B | yes | **Merge into one run-verdict toast** (D5) |
| 12 | 🔵 "Graph updated!" | Any run not threshold-judged (co-fires with the top-N toast, which does not suppress it) | B | yes | **Remove** |
| 13 | 🔵/🟢/🟡 Backlog run summary | Runs accrued while Home was closed | B | yes | **Keep** |
| 14 | 🟢/🟠/🔴 Playlist import result (success / imported-but-hidden / failure) | Overview-page import modal at `/playlists` | B | yes | **Keep** |
| 15 | 🟡 Startup playlist warnings | Duplicate playlist codes at boot | B | yes | **Keep, make persistent** (no autoClose — fires when nobody may be looking) |
| 16 | 🟢/🔴 Playlist delete result | Overview-page delete confirmation | B | yes | **Keep** |
| 17 | 🟢/🔴 Superseded-file cleanup result | Overview-page cleanup confirmation | B | yes | **Keep** |
| 18 | 🔴 "Could not process a new run file" (*new*, PR #115) | A run CSV fails to import on the watchdog thread | A | yes, queued — next Home tick | **Keep → typed queue** (D4): the user's run silently vanished; they would act on it |
| 19 | 🔴 "Percentile update stopped: username may be misconfigured" (*new*, warmup arc) | Warmup worker hits a fatal username error | A | yes, queued — next Home tick | **Remove toast**; the Playlists status strip already shows the fatal state in place |
| 20 | 🟢 "Refreshed position for X." (*new*) | Manual Refresh succeeds with a fresh fetch | B | yes | **Keep**; D6 retitle (title is literally "Notification") |
| 21 | 🟡/🔴 Progressive-fill outage summary (*new*, PR #127) | A playlist-page position fill ends interrupted/failed | B | yes | **Keep** (settled 2026-07-15 design; one-shot aggregate, policy-conformant) |

Net effect: during normal play with the default config, the only toasts are the
per-run verdict, the backlog summary, and the results of things the user
clicked. Nothing red unless something the user asked for failed — or a run of
theirs failed to record (row 18), which is precisely when red is earned.

## Design decisions

### D1. One delivery path: System B; retire System A

Consolidate on `sendNotifications` / `dmc.NotificationContainer` (native DMC,
stable ids, dedupes). Python `logging` stays as the console/file record — it is
the developer-facing log and the eventual Run History seed — but is **decoupled
from the toast layer**. After the surviving live toasts (#3, #6) move to
System B, row 18 moves to its typed queue (D4), and the rest are dropped,
deleted, or moved in-page, `dash_logging.py` — the handler, the module-level
queue, and `drain_background_notifications` — plus Home's
`flush_background_notifications` callback have no remaining UI consumers and
are removed (`tests/test_dash_logging_background.py`, which covers exactly
that machinery, goes with them).

The decisive argument: **a log level is not a routing policy.** The bridge
makes every `dash_logger` call a toast, with the severity chosen at the call
site standing in for the D2 judgment that should be made per event — that is
how rows 1, 9, and 19 became red walls. The uuid-per-record stacking, the
generic Info/Warning/Error titles, and the Home-gated batch delivery of
background records are each independently disqualifying for a user-facing
surface. (The original audit's strongest argument — records from background
threads silently never rendered — was fixed by PR #115's queue; what the fix
delivered is late batches of generic red toasts, which is the same problem
promoted from invisible to visible.)

### D2. Routing policy — who gets a toast

A decision rule so future notifications have an obvious home:

- **Persistent condition** (misconfiguration, missing/empty data, degraded
  feature) → **in-place UI** at the point of impact: field state, on-canvas
  empty state, the Playlists warmup status strip (which is why row 19's toast
  is a redundant second copy). Never a toast — conditions don't stop being
  true when the toast expires, and re-toasting per trigger is the noise
  machine being removed. Two named exceptions, both persistent conditions
  with no natural in-place home, both surfaced once per lifecycle rather
  than per trigger: the Steam-ID mismatch (#3) gets **one** persistent toast
  per app session (server-side guard), not one per scenario switch; the
  startup playlist warnings (#15) get one persistent toast batch per boot.
- **Automatic failure** (rank fetch failing during passive navigation) → **no
  toast**; the field state conveys it. Console `logger.warning` retained.
- **User-initiated failure** (Import, manual Refresh) → **error toast** — the
  user asked and deserves the result. A failed run-file import (row 18) sits
  here too: playing the run *was* the user's act, and nothing else tells them
  it didn't record.
- **Achievement / coaching** (run verdict) → one toast per run (D5).
- **Diagnostic** (thread failures, timeouts with automatic fallback) →
  **console log only**.

Litmus tests, in order: *Is it a state rather than an event?* → in-place.
*Is it already visible somewhere?* (plot point, Position field, empty-state
canvas, warmup status strip) → nothing. *Would the user act differently for
having seen it right now?* No → log, not toast.

### D3. Ambient state lives in the UI, not in toasts

The empty-plot already renders "No local runs found" / "No runs in this date
range" on-canvas, and the Position field already shows `N/A` when rank is
unavailable. The parallel toasts (#1, #4, #5) are redundant second copies.
Remove them, and make the Position field's `N/A` **self-explanatory** with an
inline state or tooltip:

- Username unset → `N/A` with hint "set your KovaaK's username in Settings to
  enable rank lookups" — pointing at the `/settings` page, the same pattern as
  Home's existing no-stats-directory hint. (The audit-era copy pointed at
  `config.toml`; the username has since moved to the app-owned settings store,
  PRs #181–#184, and the in-flight detection work will offer a verified name
  there. This row delivers the toast half of the quiet-state kernel the
  2026-08-01 totals-rejection entry deferred until a settings page existed.)
- Lookup failed → `N/A` with hint "lookup failed — Refresh to retry".

Exact wording/affordance (trailing text vs. tooltip) is a build-time detail;
the decision is that the field explains itself instead of toasting.

### D4. No generic toasts from background threads

`sendNotifications` is a callback output and cannot be driven from the
watchdog or timer threads. The rule: **background threads never drive UI
outputs; they publish to typed shared state that interval callbacks poll.**
The sanctioned channels today: `message_queue` (a `deque[NewFileMessage]` —
run events only; its consumer assumes run-specific fields), the startup
playlist-warning queue (boot warnings, drained by a dedicated Home interval —
the pattern to copy), and the JSON caches (the rank pipeline: Timer writes,
cache-only interval reads surface within ~1s). None is a general event bus —
a background event that fits none of them needs its own typed queue or polled
state, not a schema graft.

System A's module-level notification queue is the anti-pattern this rule
exists to prevent: a *generic* level-driven channel that turns any log record
into UI. It is deleted with System A. The one background toast that survives
the verdicts, row 18's run-import failure, gets a small **typed** replacement
in PR 2: a module-level deque of import-failure messages in the watchdog,
drained into one red toast by a Home interval callback, exactly the startup
playlist-warning shape. Home-gated delivery is acceptable for it — the run's
absence is a Home-visible fact, and today's delivery is already Home-gated.
Rows 8–9 and 19 become console-only (delete the toast calls, keep the
`logger` siblings). Document the rule in `docs/architecture.md` so the
level-driven-bridge mistake cannot recur. Surfacing background rank events as
real toasts is deferred (Open questions) — if it happens, it reuses this
typed-queue pattern.

### D5. One run, one toast

Today a run that both places top-N and gets a threshold verdict fires **two**
stacked toasts (#10 + #11 have different ids). Merge them: a single per-run
**run-verdict toast** under one stable id (e.g. `run-verdict`), so consecutive
runs replace instead of stack. When both qualify, the threshold verdict is the
headline and the top-N placement a trailing detail. A run that qualifies for
neither emits nothing (the new plot point is the confirmation — #12 is
removed). The backlog summary (#13) already follows this one-toast shape and
**shares the `run-verdict` id**: a new live run replaces the catch-up digest,
which is strictly staler information.

**Replace mechanics (DMC 2.8.0, the locked version — re-verified 2026-08-03):**
a bare `show` cannot replace — the Mantine store ignores `show` for an id
already on screen, and `update` is a no-op for an id that is not. Neither
alone is an upsert, so each run-verdict emission sends **both actions with the
same id and payload** (`update` then `show`): whichever matches the toast's
current state applies and the other is a no-op.

The upsert must also grant a **fresh full lifetime**: Mantine's auto-close
timer effect is keyed on the resolved `autoClose` duration only, so an
`update` carrying the same duration leaves the original timer running — a run
landing near the old toast's expiry would flash for milliseconds. Each
emission therefore alternates `autoClose` between two indistinguishable
durations (e.g. 8000/8001 ms), forcing the duration-keyed effect to cancel and
re-arm the timer. The alternation state is **per browser client**: a
`dcc.Store` sequence flipped on each emission (`generate_graph` gains a
`State`/`Output` pair on it, and the pure builders take the sequence as an
argument). A module-global toggle would be wrong — each tab runs its own
callback stream and `NotificationContainer`, so one tab's flip could hand
another tab the duration it is already displaying, leaving the old timer
running. The Store's **lifecycle must match the host's**: it lives in
`app_shell.py` beside the `NotificationContainer`, not in Home's page layout —
toasts survive page navigation (the container is shell-hosted) while a
page-layout memory Store resets on remount, which could reissue the visible
toast's duration after a navigate-away-and-back. PR 3 must carry a regression
test for the replace cases — a second run's toast replacing a visible one, a
live run replacing the backlog digest, and an emission after navigating away
and back while a toast is active — asserting with **elapsed time** that the
replacement gets a full lifetime, not merely that the payload changed. (The
test doubles as an upgrade guard: the mechanism depends on the timer effect's
duration dependency, which a future DMC/Mantine version could change.)

### D6. Presentation standards

- Stable, semantic notification ids; dedupe/replace by id.
- **Title carries the verdict** — title + color must tell the whole story from
  across the room. Never the literal word "Notification" (today's offenders:
  the top-N toast and the row-20 refresh confirmation).
- **Message leads with the scenario**; sensitivity is a trailing qualifier
  (top-N is per-sensitivity, so it matters, but it is never the subject).
- Consistent `autoClose`: one nominal duration — expressed at runtime as two
  indistinguishable values by the D5 timer-reset alternation — with two
  deliberate exceptions that persist until dismissed: the Steam-ID mismatch
  (#3) and startup playlist warnings (#15), both of which fire when the user
  may not be looking.
- Copy shapes (final wording is a build-time detail; the shape is the
  decision):
  - Top-N only: title `New 2nd-best score` (1st: `New best score`), message
    `VT Pasu Rasp — 3421.50 at 32.0 cm/360`.
  - Threshold pass: title `Threshold passed`, message
    `VT Pasu Rasp — 941.20, 97.3% of PB. Ready to move on.`
  - Threshold fail: title `Below threshold`, message
    `VT Pasu Rasp — 899.10, 92.9% of PB — need 95.0%. Keep grinding...`
    (the target % is included: one extra number with real motivational value).
  - Both, threshold pass: title `Threshold passed`, message
    `VT Pasu Rasp — 941.20, 97.3% of PB. Also your 2nd-best at 32.0 cm/360.`
  - Both, threshold fail (reachable: a top-N run below a <100% goal, or a new
    PB below a >100% goal): title `Below threshold`, message
    `VT Pasu Rasp — 899.10, 92.9% of PB — need 95.0%. Still your 2nd-best at
    32.0 cm/360. Keep grinding...` The new-PB-that-fails variant keeps the
    `Below threshold` title — the title is the verdict, and there is no PB
    retitle (coherence note below).
  - Backlog, judged latest run: title `While you were away`, message
    `6 new VT Pasu Rasp runs. Latest: 941.20 — 97.3% of PB, passed threshold.`
  - Backlog, verdict-less latest run (threshold switch off, or
    `previous_high_score=None` on a new scenario/sensitivity — no denominator
    for % of PB): neutral color, title `While you were away`, message
    `6 new VT Pasu Rasp runs. Latest: 941.20 at 32.0 cm/360.` (The existing
    variant logic carries over; this is copy-only alignment.)
  - Migrated or retitled System A/B survivors get titles now so PRs 2–3 don't
    guess: #3 `Steam ID mismatch`, #6 `Position refresh failed`, #18
    `Run not recorded`, #20 `Position refreshed`.
- The PR 3 copy pass sweeps every surviving toast's title against this
  standard (the playlist toasts' "Playlist Warning" et al. included).

**PB coherence note:** a new overall PB necessarily places 1st within its
sensitivity, so the run-verdict toast already fires for every PB that produces
a run event on the selected scenario (with automatic scenario switching off,
PBs on non-selected scenarios are discarded per the 2026-07-06 coalesce
decision and get no toast — unchanged behavior). The recorded
"no dedicated PB toast" decision (`product.md`) is therefore coherent and
stands. Deliberately *not* retitling the 1st-place case to "New personal
best!" — that would effectively create the PB toast the decision declined.

## Concrete changes

Grouped by file; each maps to inventory rows above.

- **`utilities/dash_logging.py`** — delete after consumers migrate (D1): the
  `QueueingNotificationsLogHandler`, the module queue,
  `drain_background_notifications`, and `get_dash_logger` all go.
- **`utilities/notifications.py`** (new, small) — one payload builder, e.g.
  `toast(id, title, message, *, color, icon, auto_close)`, so shape/convention
  lives in one place. A function, not a framework; the pure builder pattern in
  `home.py` (`_build_run_event_notifications`) stays and calls it.
- **`app_shell.py`** — the single `dmc.NotificationContainer` remains the only
  host (the audit-era `log_handler.embed()` is already gone since PR #115).
  Add the per-client toast-lifetime `dcc.Store` beside it (D5) — shell-hosted
  so its lifecycle matches the container's across page navigation.
- **`pages/home.py`**
  - Delete `flush_background_notifications` (dies with System A's queue); add
    the small drain callback for the row-18 typed queue (D4) in its place.
  - `_emit_rank_messages` / `get_scenario_rank`: stop toasting on the passive
    path (#1, #2). Return the inline field states from D3 instead of bare
    `N/A`. Steam-ID mismatch (#3) becomes a once-per-session System B toast
    (module-level seen-flag guard; sound under Waitress's single-process thread
    pool, and the stable id makes the check-and-set race benign) —
    `get_scenario_rank` gains its own guarded `sendNotifications` output
    (`allow_duplicate=True`) so the mismatch fires on the passive path, not
    only on manual Refresh. Because this callback must keep running on page
    load (it renders the initial rank), the duplicate output requires
    `prevent_initial_call="initial_duplicate"` — Dash (4.4.0 today) refuses to
    register an `allow_duplicate` output otherwise, and plain
    `prevent_initial_call=True` would lose the initial render.
  - `refresh_rank` (#6, #20): emit the failure through the callback's existing
    `sendNotifications` output (added for the row-20 success toast since the
    audit) instead of `dash_logger`, on **both** failure paths: expected
    failures come back as `ScenarioRankInfo.error_message` (no raise),
    unexpected bugs raise — each must produce the toast. On failure the rank
    output returns `no_update` so the displayed value stays put — usually the
    cached position, but `N/A` when none was ever shown (default config, first
    failure) — replacing today's behavior of flashing `N/A` until the next
    ~1s cache-only tick restores it. The toast copy is therefore the
    always-true "Couldn't refresh — position unchanged.", not "showing cached
    position". Retitle the success toast per D6.
  - `generate_graph`: return `no_update` for the no-data branches (#4, #5 —
    note #5 now fires from two call sites in `_build_scenario_figure`);
    replace `_build_run_event_notifications`' two-toast output with the single
    merged run-verdict toast (D5); drop the "Graph updated!" fallback (#12).
    This callback gains the `State`/`Output` pair on the shell-hosted
    toast-lifetime `dcc.Store` (see the `app_shell.py` item) for the D5
    autoClose alternation.
  - Drop the `get_dash_logger` import and the `dash_logger` module-global.
- **`pages/aim_training_journey.py`** — replace the toast (#7) with an in-page
  empty state where the chart renders, mirroring Home's on-canvas pattern.
  Drop the `get_dash_logger` import and module-global.
- **`my_watchdog/file_watchdog.py`** — delete the `dash_logger.error` for the
  schedule failure (#8); keep `logger.exception`. Replace the run-import
  failure toast (#18) with an append to the new typed import-failure queue.
  Drop the `get_dash_logger` import and module-global.
- **`kovaaks/api_service.py`** — delete the three `dash_logger.error` calls in
  `_notify_exhaustion` / `_run_attempt` (#9); keep the `logger` siblings. Drop
  the now-unused `dash_logger` import.
- **`kovaaks/percentile_warmup_service.py`** — delete the fatal-state toast
  (#19); keep the `logger.warning`. The Playlists overview status strip
  already renders the fatal state in place.
- **`pages/playlists.py` / `pages/playlist_scenarios.py`** — no routing
  changes (rows 14–17, 21 keep their verdicts); PR 3's copy pass touches
  titles only.
- **`docs/architecture.md`** — document the D4 rule (background threads never
  drive UI outputs; they publish to typed polled state — no generic
  level-driven bridge), and rewrite the `utilities/` module-map entry
  describing `dash_logging` ("routes `logging` to on-screen Mantine
  notifications; records logged outside a callback context are queued…"),
  which deleting `dash_logging.py` falsifies — `test_docs.py` gates dangling
  links, not stale prose, so nothing else catches it.
- **`docs/specs/scenario_rank.md`** — the spec (created since the audit)
  states that background refresh failures notify the UI through
  `dash_logger.error(...)` and describes the queue path; update those
  statements when the toasts become console-only in PRs 1–2.
- **`pyproject.toml`** — **`dash-extensions` stays**: `app.py` imports
  `DashProxy` from `dash_extensions.enrich` (the app framework itself), and
  only `dash_logging.py`'s `context_value` import goes away with the module.

## Build sequencing — three reviewable PRs

1. **Noise kill.** Remove the #1/#2/#4/#5/#12 toasts, add the inline
   Position-field states, add the one-time startup console INFO for the
   unset username (row 1), and remove the warmup fatal toast (#19 — its
   in-page status already exists). Touch up `product.md`'s run-notifications
   paragraph (the "Graph updated!" description becomes false here) and the
   `scenario_rank.md` spec lines PR 1 falsifies. Resolves the audit
   complaint by itself; smallest reviewable unit. (The #8/#9 dead-diagnostic
   deletions are low-risk and can ride along or land first as an independent
   commit.)
2. **System consolidation.** Delete System A (handler, queue, drain callback,
   `tests/test_dash_logging_background.py`), migrate #3 (once-per-session)
   and #6 to System B, add the row-18 typed import-failure queue, move #7
   in-page, add the `toast()` builder, document the D4 rule in
   `architecture.md`, finish the spec update.
3. **Copy rework.** The merged run-verdict toast (D5) and the D6 copy shapes;
   align the backlog summary (a full copy rewrite, not a no-op — see Migration
   notes); make #15 persistent; sweep surviving titles (#14–#17, #20, #21).
   This is the shipping PR for docs: distill this file into the
   `decision_log.md` entry, finish the `product.md` rewrite, and delete this
   proposal here.

## Migration notes

- **Tests.** Breakage spans six files plus one coverage gap — update each in
  the PR that breaks it:
  - **PR 1** (removes #12 and the passive rank toasts): in
    `tests/test_home_run_events.py`, every assertion on the `"Graph updated!"`
    message and `graph-updated-notification` id
    (`test_single_run_notifications_preserve_top_n_and_fallback_toasts`,
    `test_single_run_threshold_notification_ignores_empty_percentage`,
    `test_generate_graph_skips_threshold_features_when_percentage_is_empty`);
    the "neither top-N nor threshold" case then asserts an empty list. In
    `tests/test_home_rank_format.py`, the cases that monkeypatch
    `home.dash_logger` to assert passive-path rank toasts — rewrite against
    the inline Position-field states of D3. In
    `tests/test_home_build_scenario_figure.py`, the date-range warning
    assertions (#5, both call sites). No test asserts the #19 toast (only the
    in-page status string in `test_playlist_pages.py`), so its removal breaks
    nothing.
  - **PR 1 or 2** (whichever deletes the #8/#9 calls):
    `tests/test_file_watchdog_rank_refresh.py` and
    `tests/test_scenario_rank_freshness.py` monkeypatch `dash_logger` and
    assert those messages. Rewrite against the retained console `logger`
    calls.
  - **PR 2** (System A deletion, row-18 queue, Journey in-page state):
    `tests/test_dash_logging_background.py` is deleted with the module it
    covers; `tests/test_crash_logging.py` asserts the row-18 message through
    the System A queue — rewrite against the typed import-failure queue; any
    remaining `dash_logger` monkeypatches vanish with the module; the Journey
    page has no dedicated coverage today (only a tangential touch in
    `test_playlist_pages.py`), so the in-page empty state needs **net-new**
    regression tests.
  - **PR 3** (D5 merge + D6 copy): the `new-top-n-score-notification` /
    `score-threshold-notification` ids and two-toast-per-run shape in the
    remaining `test_single_run_*` cases, **and the four `test_backlog_*`
    functions** — the backlog realignment changes the
    `run-summary-notification` id (now `run-verdict`, D5) and rewrites the
    exact copy those tests assert. D5's "already follows this one-toast shape"
    refers to toast *count* only; the backlog copy and id both change. Plus
    the new D5 lifetime/upsert regression tests.
- **Docs on ship.** `product.md`'s "Run notifications" paragraph is touched
  twice: PR 1 removes the "Graph updated!" description, PR 3 rewrites it for
  the merged toast. The `scenario_rank.md` spec is touched by PRs 1–2 as its
  statements are falsified. PR 3 is the distill-and-delete PR for this file
  (`decision_log.md` entry + deletion); `tests/test_docs.py` fails on dangling
  links if any doc still references it then — including the `roadmap.md`
  entry for this work, which the same sweep removes.
- **Behavior parity.** Retiring System A loses nothing that currently renders
  except the toasts intentionally removed (#1/#2/#4/#5/#8/#9/#19); row 18 is
  the only background toast that must keep rendering, and its typed queue
  preserves today's Home-gated delivery timing.

## Open questions (defer to build time)

- **Do background rank events deserve a real toast?** "Your rank updated after
  that PB" and "Position update timed out" become console-only under D4.
  Surfacing them needs a D4-conformant channel — a dedicated typed event queue
  or polled cache state, *not* the run-specific `message_queue`; the row-18
  import-failure queue is the pattern (and could generalize) if this is ever
  wanted. Pairs naturally with the rank-improved addition below — decide
  together, not piecemeal.
- **Manual Refresh error color.** Keep red, or soften to a neutral yellow?
  The copy is settled ("Couldn't refresh — position unchanged.", always true
  since the failure path returns `no_update` — see the `refresh_rank` item in
  Concrete changes); only the severity styling remains open.

## Future / optional (scope additions, not committed)

- **"Rank improved" toast.** When the background poll lands a better position,
  the UI updates silently on the next tick; a one-shot "You're now 1,240th (up
  from 1,310)" would close the loop on a PB. Requires a D4-conformant channel
  (typed event queue or polled cache state).
- **"Last run" line on Home.** A persistent one-row readout near the plot
  (latest run's score, % of PB, verdict), replaced on each run — the toast's
  content with no expiry. Deliberately deferred: it is Run History's session
  view in miniature and should be designed in that work's context, not bolted
  on here.

## Provenance & review history

The 2026-07-09 original was cross-validated before opening: an independent
cold author received only the problem statement and fact inventory (no
verdicts) and converged on the same architecture and routing policy; its
divergences were triaged and folded in. A two-pass cold deep review (internal
consistency, then external verification against the code) completed
2026-07-10; all findings triaged and applied. A further mechanism re-review
(DMC show/update semantics, Dash duplicate-output rules) was verified against
the installed packages and applied the same day.

The 2026-08-03 refresh re-verified the inventory row by row against main
after PRs #83–#193. Material deltas folded in: background-thread delivery now
works via a queueing handler (PR #115), so the formerly dead rows 8–9 render;
the username moved to the app-owned settings store with a Settings page
(PRs #181–#184) and identity detection is in flight; four producers added
since the audit became rows 18–21; the delivery-mechanism prose, per-file
change list, PR sequencing, and test migration map were updated to match.
The routing policy, inventory verdicts 1–17, and the D5/D6 mechanics were
re-confirmed unchanged (DMC still locked at 2.8.0).
