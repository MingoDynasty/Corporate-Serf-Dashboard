# In-Memory Store Synchronization Proposal

**Status:** Proposed — decision-first. "Do nothing (and say why)" is a
first-class option here, not a placeholder. The purpose is to make a deliberate,
recorded call on a latent concurrency question rather than leave it implicit.

## Problem

The watchdog observer thread mutates two module-global stores in
`source/kovaaks/data_service.py` while Dash server threads read them, with no
synchronization:

- `kovaaks_database` — a plain `dict` keyed by scenario name.
- `run_database` — a `SortedList` ordered by time.

Writes happen on the observer thread through `load_csv_file_into_database`
(called from `file_watchdog.NewFileHandler.on_created`): `dict` inserts,
`SortedList.add`, and in-place `ScenarioStats` updates. Reads happen on server
threads throughout `home.py` and the journey/playlist services
(`get_scenario_stats`, `get_sensitivities_vs_runs_filtered`, `get_time_vs_runs`,
`get_aim_training_journey_for_playlist`, …), several of which *iterate* the
stores.

`message_queue` is a `deque`, whose `append`/`popleft` are atomic, so the
watchdog→UI *notification* hand-off is safe. `playlist_database` mutations are
serialized for *file* I/O by `_PLAYLIST_IO_LOCK`, but that lock does not guard
the in-memory dict. The two live stores above have no guard at all.

The concrete failure mode is a read racing a write: e.g.
`RuntimeError: dictionary changed size during iteration`, or a `SortedList`
observed mid-`add`. It has not been observed in practice — one local user,
runs land seconds apart, reads are fast — so the probability is low, but it is a
real latent correctness bug, not a stylistic nit.

## Options

**A — Accept and document.**
Keep the current lock-free model; add a short code comment and/or a
`decision_log.md` entry stating the risk is knowingly accepted for the
single-user local case. Cheapest, and honest given zero observed incidents. The
tech-debt entry already leans this way ("Fine in practice… worth a lock if
corruption is ever observed").

**B — One coarse `RLock` around store access.**
Add a module-level lock; acquire it in every mutation and every read/iteration
of the two stores. Simple and correct if applied consistently. Costs: an
accessor discipline (every current and future read site must take the lock —
easy to forget, giving partial protection), and minor contention. Best fit
*if* we keep today's threading model but want a guarantee.

**C — Snapshot-on-read / atomic swap.**
Writers build updated state and atomically rebind the global; readers grab the
current reference and read it without locking. Avoids reader-side locking on the
hot path, but is fiddly with `SortedList`/nested `dict` mutation (you must copy
enough to keep snapshots immutable) and adds real complexity.

**D — Single-writer stores (recommended if we act).**
Make the server thread the *only* writer. The watchdog stops loading into the
stores; instead it enqueues the raw file path (or parsed `RunData`) onto a
queue, and a home-page callback drains it and applies it into the stores on the
server thread — the same thread that reads them. Cross-thread store writes
disappear, so no lock is needed. This is architecturally the cleanest, but it
**changes the ingest contract**: today `architecture.md` documents that "the run
is loaded into the stores before its message becomes visible," and the watchdog
owns both the load and the high-score rank-refresh scheduling. Under D the load
moves UI-side and that ordering invariant is redesigned.

## Recommendation

Two defensible endpoints:

- **A** — accept and document. Given no observed corruption, a single user, and
  a write path that is *not* growing (the planned Run History feature adds reads
  over `run_database`, not writers), this is a legitimate close.
- **D** — if we want to remove the race by construction rather than by lock
  discipline, single-writer stores are the cleanest long-term shape.

Treat **B** as the pragmatic fallback if we want a guarantee without reshaping
ingest. Avoid **C** unless a profiler later says reader locking hurts.

Recommend **A now**, revisit toward **D** *only* if the ingest/threading model
is being reworked for another reason (so we don't pay the invariant-change cost
for this alone).

## Interactions / constraints

- `architecture.md` "Runtime data flow" documents the current write-before-
  message-visible ordering; Option D rewrites that section and the module map's
  watchdog responsibilities.
- Any lock must avoid deadlock with `_CACHE_IO_LOCK` (`api_service.py`) and
  `_PLAYLIST_IO_LOCK` — never hold two across a call into the other.
- `initialize_kovaaks_data` populates the stores at startup before the observer
  starts, so startup is single-threaded and unaffected either way.

## Open questions (decide at build time)

- Has corruption ever actually been seen? (No evidence to date — if it stays
  that way, A holds.)
- Is preemptive complexity justified for a single-user tool, or do we wait for a
  trigger (observed corruption, or a real second writer)?
- If D: where does the high-score rank-refresh scheduling move, and how do we
  preserve the "loaded before visible" guarantee the UI relies on?
