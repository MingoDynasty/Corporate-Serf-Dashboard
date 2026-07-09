# Tech Debt

Running list of code smells, minor bugs, refactors, and UI/UX paper cuts worth cleaning up eventually. Items here are not blocking any active milestone; they're tracked here so they don't get lost between sessions.

## How To Use This Doc

- Add an entry whenever a small issue is noticed but isn't worth derailing the current task.
- Keep entries brief: 1-3 lines, with file/line if applicable.
- Group items loosely by category.
- When an item is fixed, remove it. The git history is the audit trail.
- For larger refactors, prefer a proper proposal doc instead of an entry here.

---

## Bugs

*(none currently tracked)*

## Code Smells

## Refactors

### Linear search to binary search for nth-place score

`source/my_watchdog/file_watchdog.py` has a `TODO` in the run processing path indicating that the nth-place score is calculated via linear search. It could be optimized to binary search since the data is sorted.

Low priority: runs are processed one at a time and the data sets are not large enough for the current approach to be a performance problem.

### Unsynchronized shared in-memory stores

The watchdog observer thread writes `kovaaks_database` and `run_database`
(module globals in `source/kovaaks/data_service.py`) while Dash callbacks read
them from server threads, with no lock. `message_queue` is a `deque` (its
append/popleft are atomic), but the stores themselves have no synchronization.
Fine in practice for a single local user; worth a lock or a serialized writer
if corruption is ever observed or the write paths grow.

### Duplicated plot-building logic

`generate_sensitivity_plot` and `generate_time_plot` in
`source/plot/plot_service.py` share most of their structure (empty-data guard,
scatter+line traces, hover templates, legend setup, rank overlays). A shared
helper taking axis descriptors would remove the duplication.

### Decompose large home-page callbacks

`source/pages/home.py` callbacks mix UI wiring, query orchestration, plotting
decisions, and notification composition. Extract pure functions (filter
parsing, graph data preparation, notification derivation) to make them
independently testable.

## Tooling

### Single-command local quality gate

CI now enforces the five-command merge bar. Add one local entry point (task
runner or script) only if repeatedly typing the commands becomes burdensome.

## UI/UX

### Dropdown UX consistency pass — revisit after the overview ships

The three playlist dropdowns intentionally differ by role today (Home:
clearable persisted filter; playlist pages: non-clearable navigator,
transitional on `/playlists`; Aim Training Journey: `MultiSelect` comparison
picker). Once the playlist-level overview replaces the transitional navigator,
revisit whether the survivors should share visual/interaction conventions (a
shared props preset), beyond the shared code-valued options contract from the
playlist re-key work.

### Audit static inline styles

Scan `source/` for static inline style dictionaries that would be clearer as semantic classes in `assets/stylesheet.css`, especially styles toggled by callbacks. Keep runtime-computed values and small, highly local layout adjustments inline; migrate incrementally and verify theme and responsive behavior.

### Watch for `is_scenario_in_database` early-return pattern

`source/pages/home.py` previously had a bug where the rank callback short-circuited with `is_scenario_in_database(selected_scenario)`, which silently hid rank data for scenarios the user had not played locally. Fixed in PR #9.

When building new UI features that consume `get_scenario_rank_info(...)`, grep for similar "is this in the local database" guards and confirm they do not inadvertently block lookups for unplayed scenarios.

This is not a current bug; it is a code-pattern reminder so the same mistake does not recur.

## Performance

*(none currently tracked)*

## Documentation

### Refresh stale example screenshot

`docs/example.png` — README screenshot from before the rank UI, deliberately
kept until replaced. Recapture next time the app is running with real data.
