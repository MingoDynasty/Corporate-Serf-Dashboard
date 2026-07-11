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

### Rank overlays assume monotonically ascending thresholds

`_add_rank_overlays` (`source/plot/plot_service.py`) index-walks `rank_data`
in rank order to pick the ranks bracketing the plotted score range, assuming
thresholds ascend with rank. Upstream KovaaK's data violates this on 3 of the
111 bundled benchmarks (8 scenarios total; found in the PR #90 review):
`Viscose benchmarks easier scenarios` — **default-visible** — has one
(`1w3ts reload Larger`: Hare 54 > Ermine 50), and the two hidden-by-default
TSK Static/Ultimate files carry the rest. Impact is cosmetic: for scores in
the inverted band, one dashed rank line can be omitted or a lower rank shown
as the floor. Fix shape: make the window selection robust to non-monotonic
thresholds (e.g. select by min/max over thresholds, or sort a copy by
threshold for the scan) — small, self-contained in `plot_service.py`, and
should not reorder the drawn rank ladder itself. The data is faithful
upstream truth (OQ-9: KovaaK's is authoritative) — the code, not the data,
is the fix site.

## Code Smells

## Refactors

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
