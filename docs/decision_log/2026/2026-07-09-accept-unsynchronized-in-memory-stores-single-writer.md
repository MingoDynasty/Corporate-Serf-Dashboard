# 2026-07-09: Accept Unsynchronized In-Memory Stores (Single-Writer)

Status: Accepted

Decision: The module-global in-memory stores in `source/kovaaks/data_service.py`
(`kovaaks_database`, `run_database`, and `playlist_database`) remain
unsynchronized. No lock is added. This is a reviewed acceptance, not an
oversight.

Why: Design review (2026-07-09) verified the structural guarantees that bound
the risk. After startup, the watchdog observer thread is the only writer to
`kovaaks_database`/`run_database` (the startup bulk load is single-threaded,
before the observer and server exist), so writer-writer corruption cannot
occur. The top-level `kovaaks_database` dict is read via GIL-atomic lookups;
the one reader that iterates it (`get_scenario_stats_snapshot`, PR #78)
snapshots with a single C-level `list()` call that a concurrent insert cannot
break, and PR #78 also made the writer replace `ScenarioStats` objects instead
of mutating fields in place, so a reader that binds one sees field-consistent
values. The remaining exposure is server-thread readers iterating nested
`sortedcontainers` structures (and the journey page walking `run_database`)
mid-`add()`: worst case is a skipped or duplicated point, or a rare exception,
in one render. Dash contains callback exceptions and no path writes torn state
back. Self-healing has two cadences: home-page consumers re-render on the
polling interval, so races there clear within about a second; the journey,
playlist grid, and playlist overview pages rebuild store-derived data only on
navigation or control interaction (their intervals only re-tick relative
timestamps), so a raced render there can persist until the next interaction.
Both cadences stay within the accepted class — a wrong or failed render, never
corrupted state. The load-before-notify
ordering in `_enqueue_after_loading` guarantees a drained message's run is
already fully visible in the stores. `playlist_database` carried the same
class between server threads (the import callback's insert vs. `.values()`
iterations under Waitress's worker pool) until PR #78 converted its iterating
readers to the same `list()` snapshot pattern, leaving only atomic containment
checks and single-key lookups exposed — which are safe. A coarse lock
was rejected because it imposes permanent accessor discipline — silent when
violated — against a self-healing one-frame glitch; a single-writer ingest
redesign was rejected as not worth reworking the load-before-notify contract
on its own.

Consequences: Two lists govern when this decision ends. Hazard triggers (add
synchronization, or implement the single-writer ingest redesign): a store-race
exception or corruption actually observed in logs; a genuine second writer to
these stores (for example runtime playlist reload or a background recompute);
a move to free-threaded (no-GIL) CPython, which weakens the per-bytecode
atomicity and pure-Python `sortedcontainers` invariants this acceptance leans
on. Resolving events (the problem dissolves as a side effect): a SQLite
migration, or an ingest rework undertaken for other reasons (which should then
adopt the single-writer design). For the SQLite path, file-backed WAL is the
chosen shape — a design choice, not the only technically viable one. In-memory
variants can be shared across threads (a single serialized connection via
`check_same_thread=False`, or one shared database via `cache=shared` or SQLite
3.36+'s `memdb` VFS), while a naive connection-per-thread `:memory:` setup
silently gives each thread a separate empty database. The shared variants are
rejected because WAL does not support in-memory databases, so each of them
forfeits concurrent snapshot-isolated readers and reintroduces reader-writer
serialization or a discouraged mode; file-backed is also the only shape that
serves the persistence and startup-scan justifications that would motivate the
migration in the first place. Run History adds more reader iteration over `run_database` but no
writers; it stays within this acceptance. New readers that iterate a shared
store dict should follow the established snapshot pattern — one C-level
`list()` call before iterating (see `get_scenario_stats_snapshot`). That
pattern is deliberately not extended to the nested `sortedcontainers`
structures, where `list()` is itself Python-level iteration and offers no
atomicity; those remain the accepted self-healing class above.
