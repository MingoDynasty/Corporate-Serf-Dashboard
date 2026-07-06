# Run Event Coalescing Proposal

> **Status:** Proposed — drafted 2026-07-06 from approach A2 of the vault
> planning note (consumption semantics verified 2026-07-05, TODO Home item 6
> from the 2026-07-04 whole-project audit triage); revised through review
> round 1 (2026-07-06, Codex) and both decision points settled by the user
> the same day; all in PR #60. Code citations verified at `24ac3e3`. No open
> decision points remain.

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

**Load-bearing fact (corrected in round 1):** the watchdog loads every run
into the DB at detection time (`file_watchdog.py:105`, `:151`, `:179`),
independent of the queue — the queue's *only* consumers are (a) the
auto-change-scenario target and (b) toast content. But the *ordering* is
currently enqueue-first, load-after (append at `:95`/`:141`/`:169` precedes
the load at each site; [`architecture.md`](./architecture.md) documents this
order explicitly), so a drain landing in that window rebuilds without the
newest run — and no second trigger ever comes. Worse,
`load_csv_file_into_database` re-extracts the CSV and silently returns on
failure (`data_service.py:308-311`), so today a message can exist for a run
that never entered the DB at all. §7 inverts the ordering so that
message-visible implies run-queryable; with that fixed, coalescing risks no
plot data — it is purely a question of where the dropdown lands and what
gets toasted.

## Target design

1. **Single consumer.** `check_for_new_data` drains the entire queue each
   tick and writes a summary payload into the store that is today's boolean
   `do_update` — renamed to **`run-events`** (settled 2026-07-06, user
   decision: the id should say what the store now carries; it touches four
   references in `home.py` only and is not persisted, so there is no
   migration concern). `generate_graph` never touches `message_queue` — it
   only reads the payload for toast content. The store's other listeners
   (`get_scenario_num_runs` at `home.py:119`, `get_scenario_rank` at `:221`)
   keep using it as a bare trigger, unchanged.
2. **Atomic batch drain.** `popleft()` in a loop under `try/except
   IndexError` — never len-then-pop — wrapped in a module-level
   `threading.Lock` so the *batch* is atomic, not just each item (round 1:
   per-item atomicity alone lets two Home tabs each drain part of the
   backlog, producing two partial summaries and possibly two different
   landing scenarios). With the lock, semantics are winner-takes-all: exactly
   one consumer gets the whole backlog and its summary; a concurrent tab's
   tick sees an empty queue and no-ops. The lock guards only this drain loop
   (memory-only, no I/O) — it is not the store-locking work deferred in
   [`tech_debt.md`](./tech_debt.md)'s "Unsynchronized shared in-memory
   stores" entry, whose producer-side `deque.append` remains lock-free and
   safe against `popleft`. Settled 2026-07-06 (user decision): the lock is
   adopted; the round-1 alternative — no lock, guarantees documented for a
   single active Home consumer — was declined because the two-tab case is
   exactly when a backlog exists, the failure mode is user-visible
   confusion, and the lock costs three lines and microseconds. Known limit,
   accepted: the losing tab gets no trigger that tick and catches up on its
   own next input; full multi-tab sync is out of scope.
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
   behavior is unchanged. `count > 1`: exactly one summary toast whose copy
   is **scenario-named**: "N new {scenario} runs while you were away" plus
   the latest run's placement and (when the threshold-notification switch is
   on and `previous_high_score` is valid) its threshold verdict. Naming the
   scenario keeps the count honest (round 1): `count` covers the landing
   scenario only, so a generic "N new runs" would undercount a mixed backlog
   — five runs across scenarios must not read as "2 new runs". The verdict
   comes from the **latest run only**, mirroring the current per-run
   meaning; per-run review after the fact is
   [`run_history_proposal.md`](./run_history_proposal.md)'s job, so the
   summary stays minimal by design. The latest message's `nth_score` is
   already accurate: the watchdog computed it against a DB that contained all
   earlier backlog runs (still true after §7 — nth is computed before the
   load either way).
6. **Trigger discipline in `generate_graph`.** Toasts are built only when the
   payload store is among `ctx.triggered` (precedent: `_rank_allows_network`,
   `home.py:172-174`) *and* the payload's scenario matches the selected
   scenario. This is what dissolves adjacent defects 1 and 2 below.
7. **Producer ordering: load before enqueue (round 1).** The watchdog
   currently appends the message *before* loading the run
   (`file_watchdog.py:95→105`, `:141→151`, `:169→179`). Invert all three
   sites: load first, enqueue only on success. `load_csv_file_into_database`
   returns `bool` (`True` when the run was added) instead of `None`; the
   only other caller — the startup bulk loader at `data_service.py:293` —
   ignores the return value, so the change is backward-compatible. This
   guarantees a drained message's run is queryable in the DB (the plot can
   never rebuild "behind" its own toast) and stops enqueuing messages for
   runs whose load silently failed. This is a pre-existing race that today's
   one-per-tick consumer inherits identically — fixed here because the
   proposal's "rebuild once from final state" guarantee depends on it.

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
| `source/pages/home.py` | The bulk of the diff: locked drain + payload in `check_for_new_data`, queue access removed from `generate_graph`, toast policy, trigger discipline. |
| `source/my_watchdog/file_watchdog.py` | Round 1: the three enqueue/load sites reorder to load-then-enqueue-on-success (§7). |
| `source/kovaaks/data_service.py` | Round 1: `load_csv_file_into_database` returns `bool`; no caller-breaking change. |
| `source/my_queue/message_queue.py` | No change — the deque structure is untouched. |
| [`architecture.md`](./architecture.md) | Shipping PR updates the data-flow description: "Check peeks / Graph poplefts" becomes "Check drains and summarizes; Graph reads the payload"; "drains the queue each tick" gains its now-true meaning; and the "message is appended *before* the run is loaded" sentence flips to the new ordering. |
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
5. The summary toast names the scenario its count covers ("N new {scenario}
   runs…"); a mixed backlog is never presented as a generic undercount.
6. A threshold verdict is never computed against a different scenario's high
   score (defect 1 regression test).
7. Changing the date picker or top-N with a non-empty queue neither consumes
   messages nor toasts (defect 2 regression test).
8. Two concurrent drains split nothing: one consumer receives the entire
   backlog and the single summary, the other no-ops — and no `IndexError` is
   possible (defect 3).
9. A message drained from the queue always corresponds to a run already
   queryable in the DB; a run whose load fails produces one warning and no
   message (§7 regression tests).
10. Full merge bar green (ruff format/check, mypy, compileall, pytest)
    locally and in CI.

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
- **Batch atomicity:** two threads calling the drain helper against one
  seeded queue — exactly one receives all messages, the other receives none
  (lock test); the `try/except` idiom still tolerates a fake whose `popleft`
  raises mid-drain.
- **Producer ordering (§7):** `load_csv_file_into_database` returns `True`
  on success / `False` on extract failure; watchdog enqueues only on `True`
  (monkeypatch precedent: `tests/test_file_watchdog_rank_refresh.py:42-46`
  already fakes both the queue and the loader); a failing load produces a
  warning and no message.

## Review round

Round 1 (2026-07-06, Codex, PR #60): three findings, all incorporated.
**(P1)** The "rebuild from final state" claim assumed load-before-visible,
but the watchdog enqueues first and loads after — and a silent load failure
could already leave a message with no run behind it. Resolved by §7
(producer reorders to load-then-enqueue-on-success; producer added to blast
radius and tests; the Problem section's load-bearing fact corrected).
**(P2, atomicity)** Per-item atomicity let two Home tabs each drain part of
one backlog. Resolved by locking the batch drain (§2) — winner-takes-all —
with the reviewer's documentation-only alternative preserved as decision
point 2. **(P2, wording)** Generic "N new runs" copy undercounted mixed
backlogs since `count` is landing-scenario-only. Resolved by
scenario-named copy (§5), which also settled the draft's original
cross-scenario-suffix decision point.

Follow-up (2026-07-06, user decisions): both open decision points settled —
the store is renamed to `run-events` (§1), and the batch-drain lock is
adopted over the documentation-only alternative (§2). No open decision
points remain; the rest is mechanical.

## Out of scope

- Producer-side changes beyond §7's enqueue-ordering fix: the `message_queue`
  structure and the watchdog's detection/notification behavior are untouched.
- App-shell/global consumption and any push transport (rejected above).
- Store locking — the "Unsynchronized shared in-memory stores" entry in
  [`tech_debt.md`](./tech_debt.md) stands on its own.
- Run History ([`run_history_proposal.md`](./run_history_proposal.md)) — the
  designated home for reviewing missed runs; this proposal deliberately keeps
  the summary toast minimal rather than pre-building that feature.
