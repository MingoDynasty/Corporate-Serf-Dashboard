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

### Mixed naive/aware datetime usage in `_is_cache_fresh`

`source/kovaaks/api_service.py::_is_cache_fresh` uses naive datetimes (`datetime.fromtimestamp(...)` and `datetime.now()`) for the TTL comparison, while elsewhere in the same file we use timezone-aware `datetime.now(UTC)` for serialization.

Both work in their respective contexts, but the inconsistency is a small surface area for future bugs if someone unfamiliar refactors one side. Normalize on `datetime.now(UTC)` and `datetime.fromtimestamp(..., UTC)` for consistency.

## Refactors

### Linear search to binary search for nth-place score

`source/my_watchdog/file_watchdog.py` has a `TODO` in the run processing path indicating that the nth-place score is calculated via linear search. It could be optimized to binary search since the data is sorted.

Low priority: runs are processed one at a time and the data sets are not large enough for the current approach to be a performance problem.

## UI/UX

### Watch for `is_scenario_in_database` early-return pattern

`source/pages/home.py` previously had a bug where the rank callback short-circuited with `is_scenario_in_database(selected_scenario)`, which silently hid rank data for scenarios the user had not played locally. Fixed in PR #9.

When building new UI features that consume `get_scenario_rank_info(...)`, such as the M1 playlist scenarios table, grep for similar "is this in the local database" guards and confirm they do not inadvertently block lookups for unplayed scenarios.

This is not a current bug; it is a code-pattern reminder so the same mistake does not recur.

## Performance

*(none currently tracked)*

## Documentation

*(none currently tracked)*
