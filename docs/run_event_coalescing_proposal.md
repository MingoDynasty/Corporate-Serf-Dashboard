# Run Event Coalescing Proposal

> **Status:** Proposed — drafted 2026-07-06 from approach A2 of the vault
> planning note (consumption semantics verified 2026-07-05, TODO Home item 6
> from the 2026-07-04 whole-project audit triage). Code citations verified at
> `24ac3e3`.

Returning to Home after playing with another page open replays the queued run
events one interval-tick at a time — the graph rebuilds N times, the scenario
dropdown pinballs through played-scenario history, and N stale toast batches
fire. Fix: drain the entire `message_queue` in one tick inside a single
consumer, rebuild the plot once from final state, and show one notification.

## Problem (current behavior, verified)

Consumption is one message per tick, split across two callbacks in
`source/pages/home.py`:

- `check_for_new_data` (`home.py:85-108`) fires per `interval-component` tick
  and **peeks** at `message_queue[0]` (`:103`):
  - head scenario == selected → sets `do_update = True` (no pop);
  - head ≠ selected, auto-change ON → flips the scenario dropdown to the
    head's scenario and sets `do_update` (no pop);
  - head ≠ selected, auto-change OFF → **pops and discards one** message per
    tick (`:106`).
- `generate_graph` (`home.py:259-452`) pops **exactly one** message
  (`:380-381`) and builds 1–2 toasts from it; the plot itself is always
  rebuilt in full from the in-memory DB.

The interval lives in Home's layout (`home.py:548-552`), so neither callback
runs while the user is on another page — or when no browser tab is open at
all. Meanwhile the watchdog thread keeps appending one `NewFileMessage` per
run (`source/my_watchdog/file_watchdog.py:95`, `:141`, `:169`), so the queue
grows unboundedly until Home is next mounted, then replays at one message per
`polling_interval` tick.

**Load-bearing fact:** the watchdog loads every run into the DB at detection
time (`file_watchdog.py:105`, `:151`, `:179`), independent of the queue. The
queue's *only* consumers are (a) the auto-change-scenario target and (b) toast
content. Coalescing risks no plot data; it is purely a question of where the
dropdown lands and what gets toasted.

## Target design

1. **Single consumer.** `check_for_new_data` drains the entire queue each
   tick and writes a summary payload into the store that is today's boolean
   `do_update`. `generate_graph` never touches `message_queue` — it only
   reads the payload for toast content. The store's other listeners
   (`get_scenario_num_runs` at `home.py:119`, `get_scenario_rank` at `:221`)
   keep using it as a bare trigger, unchanged.
2. **Atomic-per-item drain.** `popleft()` in a loop under
   `try/except IndexError` — never len-then-pop. Consistent with the
   "Unsynchronized shared in-memory stores" entry in
   [`tech_debt.md`](./tech_debt.md) (`deque` append/popleft are atomic; no
   lock added here), and it removes the existing two-tab `IndexError` race.
3. **Landing policy.** Auto-change ON: land on the *latest* drained message's
   scenario — the most recent thing the user played — flipping the dropdown
   at most once. The flip re-triggers `check_for_new_data` (the dropdown is
   both an output and an input today); the second pass sees an empty queue
   and returns `no_update`, so there is no loop. Auto-change OFF: stay on the
   selected scenario; non-matching messages are discarded in bulk (today's
   behavior, minus the wasted ticks).
4. **Payload shape.** JSON-serializable, carrying only what the toasts
   consume:

   ```json
   {
     "count": 3,
     "latest": {
       "scenario_name": "...",
       "sensitivity": "34.64 cm/360",
       "nth_score": 2,
       "score": 812.4,
       "previous_high_score": 830.1
     }
   }
   ```

   `count` is the number of drained messages for the landing scenario;
   `datetime_created` is dropped (unused by any toast). When nothing relevant
   was drained, the callback returns `no_update` — no rebuild, no toast, same
   as today's silent-discard path.
5. **Toast policy.** `count == 1`: today's toasts, verbatim — live one-run
   behavior is unchanged. `count > 1`: exactly one summary toast — "N new
   runs while you were away" plus the latest run's placement and (when the
   threshold-notification switch is on and `previous_high_score` is valid)
   its threshold verdict. The verdict comes from the **latest run only**,
   mirroring the current per-run meaning; per-run review after the fact is
   [`run_history_proposal.md`](./run_history_proposal.md)'s job, so the
   summary stays minimal by design. The latest message's `nth_score` is
   already accurate: the watchdog computed it against a DB that contained all
   earlier backlog runs.
6. **Trigger discipline in `generate_graph`.** Toasts are built only when the
   payload store is among `ctx.triggered` (precedent: `_rank_allows_network`,
   `home.py:172-174`) *and* the payload's scenario matches the selected
   scenario. This is what dissolves adjacent defects 1 and 2 below.

## Rejected alternatives

- **Coalesce at the producer** (latest-per-scenario map in the watchdog):
  changes live-session semantics — two quick runs inside one tick would drop
  a toast even while actively watching — and the deque isn't the problem;
  the consumer is.
- **Discard-on-mount:** not a distinct mechanism — plots come from the DB, so
  this is just the design above with the most aggressive toast policy.
- **Consume globally in the app shell:** auto-change and the plot need Home
  mounted anyway, and the queue still accumulates when no browser is open —
  Home-side drain-coalescing is required regardless. Possible UX polish
  later, out of scope here.
- **Push (websocket/SSE) instead of polling:** architectural rework of the
  documented pull model ([`architecture.md`](./architecture.md)), and a
  reconnecting client still faces a backlog, so coalescing is needed anyway.

## Adjacent defects absorbed (no separate fixes needed)

1. **Cross-scenario threshold toast.** The top-N toast checks
   `selected_scenario == message_data.scenario_name` (`home.py:383`) but the
   threshold block (`:402-439`) does not — a queued message from scenario A
   can be judged against scenario B's high score. Fixed by design §6.
2. **`do_update` never resets.** It is set truthy once and stays, so any
   later control change (date picker, top-N) with a non-empty queue silently
   pops and toasts a message it didn't cause (`:380`). Fixed by §1 + §6.
3. **len-then-pop race.** `check_for_new_data` checks `len()` then pops; two
   open Home tabs can race to an `IndexError`. Fixed by §2.

## Blast radius

| Surface | Change |
| ------- | ------ |
| `source/pages/home.py` | The whole diff: drain + payload in `check_for_new_data`, queue access removed from `generate_graph`, toast policy, trigger discipline. |
| `source/my_queue/message_queue.py`, `source/my_watchdog/file_watchdog.py` | No change — producer and structure untouched. |
| [`architecture.md`](./architecture.md) | Shipping PR updates the data-flow description: "Check peeks / Graph poplefts" becomes "Check drains and summarizes; Graph reads the payload", and "drains the queue each tick" gains its now-true meaning. |
| Tests | New — no tests cover these callbacks today. See test plan. |
| Docs lifecycle | On ship: distill into `decision_log.md`, delete this file, add the user-facing rationale to `product.md` (AGENTS.md "Shipping a proposal"). No roadmap entry — this is a defect fix, not a milestone. |

## Acceptance criteria

1. Backlog of N messages for one scenario: returning to Home produces exactly
   one plot rebuild trigger and one toast batch; the queue is empty after the
   first tick.
2. Multi-scenario backlog, auto-change ON: the dropdown moves once, directly
   to the latest message's scenario — no pinballing through history.
3. Auto-change OFF, mixed backlog: non-matching messages are discarded in one
   tick; matching ones produce one summary toast; nothing relevant → no
   rebuild, no toast.
4. Single live run (`count == 1`): toast output is byte-identical to today's.
5. A threshold verdict is never computed against a different scenario's high
   score (defect 1 regression test).
6. Changing the date picker or top-N with a non-empty queue neither consumes
   messages nor toasts (defect 2 regression test).
7. Concurrent drains cannot raise `IndexError` (defect 3 — drain loop is
   `popleft` under `try/except`).
8. Full merge bar green (ruff format/check, mypy, compileall, pytest) locally
   and in CI.

## Test plan

Extract the drain-and-summarize step into a small pure helper (e.g.
`_drain_run_events(selected_scenario, auto_change) -> (target_scenario,
payload | None)`) — a seam that also improves the production design (single
place owning consumption), per the AGENTS.md testing philosophy. Toast
construction from a payload likewise becomes a directly callable helper.

- **Drain semantics:** seeded real `deque` (monkeypatch precedent:
  `tests/test_file_watchdog_rank_refresh.py:42`) — single-scenario backlog,
  multi-scenario backlog with auto-change ON (lands on latest) and OFF
  (discards non-matching), empty queue, queue emptied after drain.
- **Payload contents:** count and latest-run fields correct; `no_update`
  when nothing relevant; payload is JSON-serializable.
- **Toast policy:** `count == 1` reproduces today's exact toasts (including
  the threshold pass/fail and "Graph updated!" fallback branches);
  `count > 1` produces exactly one summary toast; threshold verdict uses the
  latest run only; scenario-mismatch produces no toast (defect 1).
- **Trigger discipline:** `generate_graph` with a stale payload and a
  control-change trigger produces no toast (defect 2).
- **Race:** drain loop tolerates a concurrent consumer emptying the queue
  mid-drain (simulated by a deque fake whose `popleft` raises after k items).

## Decision points needing sign-off

1. **Store id.** Keep the `do_update` id with payload data (smallest diff) vs
   rename to something honest like `run-events` (touches the four references
   in `home.py` only — the id is not persisted, so no migration concern).
   Proposed: rename.
2. **Summary toast copy for cross-scenario backlogs.** Proposed: omit any
   "across M scenarios" suffix — runs from non-landing scenarios are absorbed
   silently (their data is in the plots regardless), and after-the-fact
   review belongs to Run History. Alternative: append the suffix for a hint
   of what was absorbed.

Everything else is mechanical once these are fixed.

## Out of scope

- Producer-side changes (`message_queue` structure, watchdog behavior).
- App-shell/global consumption and any push transport (rejected above).
- Store locking — the "Unsynchronized shared in-memory stores" entry in
  [`tech_debt.md`](./tech_debt.md) stands on its own.
- Run History ([`run_history_proposal.md`](./run_history_proposal.md)) — the
  designated home for reviewing missed runs; this proposal deliberately keeps
  the summary toast minimal rather than pre-building that feature.
