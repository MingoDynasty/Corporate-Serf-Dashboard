# Codebase Improvement Proposals

This document summarizes improvement opportunities discovered during a full-pass review of the repository's Python application and helper scripts.

## High-priority correctness fixes

1. **Fix `NewFileMessage` construction bugs in file watcher flow**
   - `NewFileMessage.previous_high_score` is required, but the "new scenario" branch creates a message without that field.
   - `extract_data_from_file` is called with `Path(config.stats_dir, file)` even though `file` is already an absolute source path from watchdog events.
   - Recommendation: always pass `previous_high_score` and pass `file` directly.

2. **Standardize imports to package-qualified `source.*` paths**
   - Some modules import from `plot.*` or `utilities.*` instead of `source.plot.*` / `source.utilities.*`.
   - This can break when the app is launched from different working directories or entry points.

3. **Protect shared in-memory stores with synchronization primitives**
   - Watchdog thread writes to `kovaaks_database`, `run_database`, and `message_queue` while Dash callbacks read and mutate them.
   - Recommendation: introduce a central data repository service with `threading.Lock`/`RLock`, or route all mutations through a serialized worker.

## Architecture and maintainability improvements

4. **Introduce a repository/service layer for stateful data access**
   - Several modules directly access global dictionaries/lists.
   - Recommendation: wrap state in classes (`RunRepository`, `PlaylistRepository`) with explicit interfaces and typed return values.

5. **Split page callbacks into smaller, testable units**
   - `source/pages/home.py` combines UI wiring, query orchestration, plotting decisions, and notification composition in large callbacks.
   - Recommendation: extract pure functions for:
     - filter selection parsing,
     - graph data query preparation,
     - notification derivation.

6. **Refactor duplicated plot-building logic**
   - `generate_sensitivity_plot` and `generate_time_plot` share most steps (scatter+line, hover templates, legend setup, rank overlays).
   - Recommendation: create one generalized helper that accepts axis descriptors and input mapping.

7. **Separate app startup lifecycle concerns**
   - `main()` currently mixes initialization, observer startup, and server run in one block.
   - Recommendation: use `try/finally` to guarantee observer shutdown and isolate startup phases for easier testing.

## Reliability and error-handling improvements

8. **Make config loading explicit and user-friendly**
   - Config is loaded at import-time (`config = load_config()`), which hard-fails if `config.toml` is missing.
   - Recommendation: lazy-load config in startup with a clear validation error and suggested remediation.

9. **Harden API layer**
   - Add structured retry/backoff for transient failures.
   - Replace debug `print(...)` calls with logger usage.
   - Add narrow exception handling with actionable messages for users importing playlist codes.

10. **Normalize date/time handling for analytics and plotting**
    - Ensure timezone-aware datetimes where possible.
    - Keep internal datetime values typed consistently (vs mixing strings and datetimes early).

## Data and performance improvements

11. **Re-evaluate in-memory-only data model for larger histories**
    - Current comments already mention possible SQLite migration.
    - Recommendation: add an optional SQLite backend for runs and indexes (scenario, date, sensitivity) to support larger datasets and safer concurrent reads.

12. **Pre-compute/ cache expensive query slices**
    - Top-N filtering and date filtering recompute repeatedly in callback invocations.
    - Recommendation: memoize by `(scenario, top_n, date_bucket)` or maintain incrementally updated aggregates.

## Tooling and quality improvements

13. **Add automated tests for parser and ranking edge-cases**
    - Highest-value initial tests:
      - CSV parser robustness,
      - rank overlay selection boundaries,
      - notification logic for threshold and top-N messages,
      - playlist import duplicate/error handling.

14. **Add lint + type-check + format automation**
    - Add one command entry point (e.g. `make check` or task runner) for `ruff`/`black`/`mypy` and CI gating.

15. **Tighten type annotations and data contracts**
    - Add missing parameter and return types in callback functions and service helpers.
    - Replace broad `dict` return types with typed aliases or pydantic/dataclass models where practical.

## Suggested implementation order

1. Correctness fixes in watchdog + imports.
2. Shared-state synchronization.
3. Callback decomposition and plot refactor.
4. Tests and CI checks.
5. Optional persistent storage (SQLite) behind repository interface.
