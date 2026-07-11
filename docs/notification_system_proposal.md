# Notification System Proposal

> **Status:** Proposed — awaiting agreement. Scope is the toast/notification
> layer only (delivery mechanism, routing policy, and per-notification copy).
> No change to run capture, plotting, or the rank pipeline's data. Distill into
> `decision_log.md` and delete this file in the shipping PR.
>
> Design was cross-validated: an independent cold author received only the
> problem statement and fact inventory (no verdicts) and converged on the same
> architecture and routing policy; its divergences were triaged and folded in.
> A two-pass cold deep review (internal consistency, then external verification
> against the code) completed 2026-07-10; all findings triaged and applied. A
> further mechanism re-review (DMC show/update semantics, Dash duplicate-output
> rules) was verified against the installed packages and applied the same day.

## Problem

The app has grown **two independent notification subsystems**, and the split is
the root cause of the noise reported in the UI audit:

- **System A — logging-driven.** A Python logger (`dash_logger`) routes
  `logging` records through `dash-extensions`' `NotificationsLogHandler` into
  DMC notifications (`utilities/dash_logging.py`, mounted via
  `log_handler.embed()` in `app_shell.py`). Every message gets a fresh `uuid`
  id, so these **stack rather than replace**; titles are the generic
  "Info/Warning/Error". Crucially, `emit()` only works inside a Dash callback —
  it swallows `MissingCallbackContextException` — so **anything logged from a
  background thread silently never renders**.
- **System B — callback-driven.** Explicit `sendNotifications` on
  `dmc.NotificationContainer` (`app_shell.py`), fed by dicts in `home.py`. These
  use **stable ids, which suppress duplicates**: DMC's `show` action silently
  ignores a payload whose id is already on screen (it does *not* replace it —
  replacement needs the separate `update` action, see D5). Custom titles,
  colors, and icons.

Two host components, two id conventions, two title vocabularies, two auto-close
defaults. During a play session System A piles up while System B at least
suppresses repeats. Worse, **four of System A's error toasts are dead code**: the watchdog's
"Could not start position update" and the three `api_service.py` rank-timer
messages ("Position update timed out / misconfigured / failed unexpectedly")
all fire from `threading.Timer` daemon threads or the watchdog observer thread,
outside any callback context, so they can never appear despite reading like
user-facing errors.

System B has stacking sources of its own: the top-N toast and the
score-threshold toast use *different* stable ids, so a single run that
qualifies for both fires two stacked toasts — and the "Graph updated!" fallback
fires whenever a run is not threshold-judged, *independent of top-N*, so a
top-N run with the threshold switch off also fires two.

The most visible symptom: with `kovaaks_username` unset (**the default**), an
unset username is a *supported* state — `example.toml` says "Leave unset or
empty to disable scenario rank lookups" — yet the rank lookup still runs on
every scenario switch and every new run, and reports the result as a red
**Error** toast. It auto-closes after 8s, but re-fires constantly and stacks
(unique ids), so it reads as a persistent wall of red.

## Goals / non-goals

**Goals**
- One delivery path with one set of conventions.
- Passive, automatic activity is quiet by default; toasts are reserved for
  achievements, coaching, and the results of user-initiated actions.
- One run produces at most one toast.
- No toast that cannot actually render.
- Titles that carry the verdict; copy that leads with the scenario.

**Non-goals**
- Persistent/reviewable notification history — that is the separate
  [Run History](./run_history_proposal.md) work; this proposal keeps toasts
  ephemeral.
- Changing what counts as a top-N score, or the score-threshold verdict rule
  (settled 2026-07-08 in `decision_log.md`).
- New background→UI plumbing for rank events (see Open questions).

## Current inventory

| # | Notification | Fires when | System | Renders? | Verdict |
|---|---|---|---|---|---|
| 1 | 🔴 "KovaaK's username is not configured" | Every scenario switch / new run, username unset (default) | A | yes | **Remove toast**; inline hint on the Position field + one startup console INFO |
| 2 | 🔴 Rank fetch/resolve failed | Scenario switch / run, transient API failure | A | yes | **Remove toast**; inline field state, Refresh is the retry |
| 3 | 🟡 Steam-ID mismatch | Scenario switch when `steam_id` disagrees | A | yes | **Keep, once per app session**, persistent until dismissed |
| 4 | 🟡 "No scenario data found" | Selecting an unplayed scenario | A | yes | **Remove** (on-canvas empty state already covers it) |
| 5 | 🟡 "No scenario data for the given date range" | Date filter empties the plot | A | yes | **Remove** (same) |
| 6 | 🔴 "Position refresh for X failed" | Manual Refresh errors | A | yes | **Keep → move to B** |
| 7 | 🟡 "Insufficient data for playlist X" | Journey page, selected playlist has no data | A | yes | **Modify → in-page empty state**, no toast |
| 8 | 🔴 "Could not start position update for X" | Watchdog fails to schedule refresh | A | **no (dead)** | **Delete** |
| 9 | 🔴 "Position update timed out / misconfigured / failed" | Rank-freshness timer chain | A | **no (dead)** | **Delete** |
| 10 | 🟢 New top-N score | Run makes top-N for its sensitivity | B | yes | **Merge into one run-verdict toast** (D5) + rewrite copy |
| 11 | 🟢/🟡 Score threshold pass/fail | Threshold switch on + prior PB exists | B | yes | **Merge into one run-verdict toast** (D5) |
| 12 | 🔵 "Graph updated!" | Any run not threshold-judged (co-fires with the top-N toast, which does not suppress it) | B | yes | **Remove** |
| 13 | 🔵/🟢/🟡 Backlog run summary | Runs accrued while Home was closed | B | yes | **Keep** |
| 14 | 🟢/🔴 Playlist import result | Import button | B | yes | **Keep** |
| 15 | 🟡 Startup playlist warnings | Duplicate playlist codes at boot | B | yes | **Keep, make persistent** (no autoClose — fires when nobody may be looking) |

Net effect: during normal play with the default config, the only toasts are the
per-run verdict, the backlog summary, and the results of things the user
clicked. Nothing red unless something the user asked for failed.

## Design decisions

### D1. One delivery path: System B; retire System A

Consolidate on `sendNotifications` / `dmc.NotificationContainer` (native DMC,
stable ids, dedupes). Python `logging` stays as the console/file record — it is
the developer-facing log and the eventual Run History seed — but is **decoupled
from the toast layer**. After the surviving live toasts (#3, #6) move to
System B and the rest are dropped, deleted, or moved in-page,
`dash_logging.py`, `log_handler.embed()`, and the `dash-extensions` logging
bridge have no remaining UI consumers and are removed.

Beyond the uuid-stacking and title vocabulary, the decisive argument is that
System A is a **silent-failure trap**: rows 8–9 were "implemented" and never
rendered once, because the handler swallows the missing-context exception. Any
future contributor who logs from the watchdog or a Timer hits the same
invisible hole.

### D2. Routing policy — who gets a toast

A decision rule so future notifications have an obvious home:

- **Persistent condition** (misconfiguration, missing/empty data, degraded
  feature) → **in-place UI** at the point of impact: field state, on-canvas
  empty state. Never a toast — conditions don't stop being true when the toast
  expires, and re-toasting per trigger is the noise machine being removed.
  Two named exceptions, both persistent conditions with no natural in-place
  home, both surfaced once per lifecycle rather than per trigger: the Steam-ID
  mismatch (#3) gets **one** persistent toast per app session (server-side
  guard), not one per scenario switch; the startup playlist warnings (#15) get
  one persistent toast batch per boot.
- **Automatic failure** (rank fetch failing during passive navigation) → **no
  toast**; the field state conveys it. Console `logger.warning` retained.
- **User-initiated failure** (Import, manual Refresh) → **error toast** — the
  user asked and deserves the result. (The routing is settled; whether the
  manual-Refresh failure stays red or softens is the styling question in Open
  questions.)
- **Achievement / coaching** (run verdict) → one toast per run (D5).
- **Diagnostic** (thread failures, timeouts with automatic fallback) →
  **console log only**.

Litmus tests, in order: *Is it a state rather than an event?* → in-place.
*Is it already visible somewhere?* (plot point, Position field, empty-state
canvas) → nothing. *Would the user act differently for having seen it right
now?* No → log, not toast.

### D3. Ambient state lives in the UI, not in toasts

The empty-plot already renders "No local runs found" / "No runs in this date
range" on-canvas, and the Position field already shows `N/A` when rank is
unavailable. The parallel toasts (#1, #4, #5) are redundant second copies.
Remove them, and make the Position field's `N/A` **self-explanatory** with an
inline state or tooltip:

- Username unset → `N/A` with hint "set `kovaaks_username` in `config.toml` to
  enable rank lookups" (note: username lives in `config.toml`, not the Settings
  modal — copy must say so).
- Lookup failed → `N/A` with hint "lookup failed — Refresh to retry".

Exact wording/affordance (trailing text vs. tooltip) is a build-time detail;
the decision is that the field explains itself instead of toasting.

### D4. No fake toasts from background threads

`sendNotifications`, like the old logging bridge, is a callback output and
cannot be driven from the watchdog or timer threads. The rule: **background
threads never drive UI outputs; they publish to shared state that interval
callbacks poll.** Two sanctioned channels exist today, each with its own
schema: `message_queue` (a `deque[NewFileMessage]` — run events only; its
consumer assumes run-specific fields) and the JSON caches (the rank pipeline:
Timer writes, cache-only interval reads surface within ~1s). The run queue is
*not* a general event bus — a future background event that is neither a run
nor a cache write needs its own typed queue or polled state, not a schema
graft onto `NewFileMessage`. After the verdicts above, nothing on a background
thread needs a toast, so rows 8–9 become console-only (delete the toast calls,
keep the `logger.warning`/`logger.exception` siblings). Document the rule in
`docs/architecture.md` so the row-8/9 mistake cannot recur. Surfacing
background rank events as real toasts is deferred (Open questions).

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

**Replace mechanics (DMC 2.8.0):** a bare `show` cannot replace — the Mantine
store ignores `show` for an id already on screen, and `update` is a no-op for
an id that is not. Neither alone is an upsert, so each run-verdict emission
sends **both actions with the same id and payload** (`update` then `show`):
whichever matches the toast's current state applies and the other is a no-op.

The upsert must also grant a **fresh full lifetime**: Mantine's auto-close
timer effect is keyed on the resolved `autoClose` duration only, so an
`update` carrying the same duration leaves the original timer running — a run
landing near the old toast's expiry would flash for milliseconds. Each
emission therefore alternates `autoClose` between two indistinguishable
durations (e.g. 8000/8001 ms), forcing the duration-keyed effect to cancel and
re-arm the timer. PR 3 must carry a regression test for both replace cases —
a second run's toast replacing a visible one, and a live run replacing the
backlog digest — asserting with **elapsed time** that the replacement gets a
full lifetime, not merely that the payload changed. (The test doubles as an
upgrade guard: the mechanism depends on the timer effect's duration
dependency, which a future DMC/Mantine version could change.)

### D6. Presentation standards

- Stable, semantic notification ids; dedupe/replace by id.
- **Title carries the verdict** — title + color must tell the whole story from
  across the room. Never the literal word "Notification".
- **Message leads with the scenario**; sensitivity is a trailing qualifier
  (top-N is per-sensitivity, so it matters, but it is never the subject).
- Consistent `autoClose` (one constant), with two deliberate exceptions that
  persist until dismissed: the Steam-ID mismatch (#3) and startup playlist
  warnings (#15), both of which fire when the user may not be looking.
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
  - Migrated System A survivors get titles now so PR 2 doesn't guess: #3
    `Steam ID mismatch`, #6 `Position refresh failed`.

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

- **`utilities/dash_logging.py`** — delete after consumers migrate (D1).
- **`utilities/notifications.py`** (new, small) — one payload builder, e.g.
  `toast(id, title, message, *, color, icon, auto_close)`, so shape/convention
  lives in one place. A function, not a framework; the pure builder pattern in
  `home.py` (`_build_run_event_notifications`) stays and calls it.
- **`app_shell.py`** — drop `log_handler.embed()` and its import; the single
  `dmc.NotificationContainer` remains the only host.
- **`pages/home.py`**
  - `_emit_rank_messages` / `get_scenario_rank`: stop toasting on the passive
    path (#1, #2). Return the inline field states from D3 instead of bare
    `N/A`. Steam-ID mismatch (#3) becomes a once-per-session System B toast
    (module-level seen-flag guard; sound under Waitress's single-process thread
    pool, and the stable id makes the check-and-set race benign) —
    `get_scenario_rank` gains its own guarded `sendNotifications` output
    (`allow_duplicate=True`) so the mismatch fires on the passive path, not
    only on manual Refresh. Because this callback must keep running on page
    load (it renders the initial rank), the duplicate output requires
    `prevent_initial_call="initial_duplicate"` — Dash 4.3 refuses to register
    an `allow_duplicate` output otherwise, and plain
    `prevent_initial_call=True` would lose the initial render.
  - `refresh_rank` (#6): emit the failure via a `sendNotifications` output
    (`allow_duplicate=True`, `prevent_initial_call=True` — already set) instead
    of `dash_logger`, on **both** failure paths: expected failures come back as
    `ScenarioRankInfo.error_message` (no raise), unexpected bugs raise — each
    must produce the toast. On failure the rank output returns `no_update` so
    the displayed value stays put — usually the cached position, but `N/A`
    when none was ever shown (default config, first failure) — replacing
    today's behavior of flashing `N/A` until the next ~1s cache-only tick
    restores it. The toast copy is therefore the always-true
    "Couldn't refresh — position unchanged.", not "showing cached position".
  - `generate_graph`: return `no_update` for the no-data branches (#4, #5);
    replace `_build_run_event_notifications`' two-toast output with the single
    merged run-verdict toast (D5); drop the "Graph updated!" fallback (#12).
  - Drop the `get_dash_logger` import and the `dash_logger` module-global.
- **`pages/aim_training_journey.py`** — replace the toast (#7) with an in-page
  empty state where the chart renders, mirroring Home's on-canvas pattern.
  Drop the `get_dash_logger` import and module-global.
- **`my_watchdog/file_watchdog.py`** — delete the dead `dash_logger.error`
  (#8); keep `logger.exception`. Drop the `get_dash_logger` import and
  module-global.
- **`kovaaks/api_service.py`** — delete the three dead `dash_logger.error`
  calls in `_notify_exhaustion` / `_run_attempt` (#9); keep the `logger`
  siblings. Drop the now-unused `dash_logger` import.
- **`docs/architecture.md`** — document the D4 rule (background threads never
  drive UI outputs; they publish to polled shared state — no toast calls from
  background threads), and remove/rewrite the `utilities/` module-map entry
  describing `dash_logging` ("routes `logging` to on-screen Mantine
  notifications"), which deleting `dash_logging.py` falsifies —
  `test_docs.py` gates dangling links, not stale prose, so nothing else
  catches it.
- **`pyproject.toml`** — **`dash-extensions` stays**: `app.py` imports
  `DashProxy` from `dash_extensions.enrich` (the app framework itself), so the
  logging bridge was never its sole use. Only the
  `NotificationsLogHandler` usage goes away.

## Build sequencing — three reviewable PRs

1. **Noise kill.** Remove the #1/#2/#4/#5/#12 toasts, add the inline
   Position-field states, and add the one-time startup console INFO for the
   unset username (inventory row 1). Touch up `product.md`'s run-notifications paragraph
   (the "Graph updated!" description becomes false here). Resolves the audit
   complaint by itself; smallest reviewable unit. (The #8/#9 dead-call
   deletions are zero-risk and can ride along or land first as an independent
   commit.)
2. **System consolidation.** Delete System A, migrate #3 (once-per-session)
   and #6 to System B, move #7 in-page, add the `toast()` builder, document
   the D4 rule in `architecture.md`.
3. **Copy rework.** The merged run-verdict toast (D5) and the D6 copy shapes;
   align the backlog summary (a full copy rewrite, not a no-op — see Migration
   notes); make #15 persistent. This is the shipping PR for docs: distill this
   file into the `decision_log.md` entry, finish the `product.md` rewrite, and
   delete this proposal here.

## Migration notes

- **Tests.** About twelve functions in `tests/test_home_run_events.py` break,
  split across two PRs — update them in the PR that breaks them:
  - **PR 1** (removes #12): every assertion on the `"Graph updated!"` message
    and `graph-updated-notification` id
    (`test_single_run_notifications_preserve_top_n_and_fallback_toasts`,
    `test_single_run_threshold_notification_ignores_empty_percentage`,
    `test_generate_graph_skips_threshold_features_when_percentage_is_empty`);
    the "neither top-N nor threshold" case then asserts an empty list.
  - **PR 3** (D5 merge + D6 copy): the `new-top-n-score-notification` /
    `score-threshold-notification` ids and two-toast-per-run shape in the
    remaining `test_single_run_*` cases, **and the four `test_backlog_*`
    functions** — the backlog realignment changes the
    `run-summary-notification` id (now `run-verdict`, D5) and rewrites the
    exact copy those tests assert. D5's "already follows this one-toast shape"
    refers to toast *count* only; the backlog copy and id both change.
- **Docs on ship.** `product.md`'s "Run notifications" paragraph is touched
  twice: PR 1 removes the "Graph updated!" description, PR 3 rewrites it for
  the merged toast. PR 3 is the distill-and-delete PR for this file
  (`decision_log.md` entry + deletion); `tests/test_docs.py` fails on dangling
  links if any doc still references it then.
- **Behavior parity.** Retiring System A loses nothing that currently renders
  except the passive rank/no-data toasts being intentionally removed; the four
  dead toasts were never visible.

## Open questions (defer to build time)

- **Do background rank events deserve a real toast?** "Your rank updated after
  that PB" and "Position update timed out" are currently invisible. Surfacing
  them needs a D4-conformant channel — a dedicated typed event queue or polled
  cache state, *not* the run-specific `message_queue`. Pairs naturally with the
  rank-improved addition below — decide together, not piecemeal.
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
