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

### Unguarded KovaaK's calls escape into the Dash import callback

`load_playlist_from_code` (`source/kovaaks/data_service.py`) has two spots
where an exception escapes to the import callback
(`source/pages/playlists.py`, which has no safety net) instead of returning
the documented refusal:

- The `get_playlist_data(...)` search call itself. If KovaaK's is fully down
  (`ConnectionError` after retries), returns a non-429 HTTP error, or sends
  bad JSON / an off-shape response (`ValidationError`), it raises — and the
  Evxl fallback never gets a chance, since that fires only on the two refusal
  branches.
- The `PlaylistData` build from the single-record search result. A
  blank/whitespace `playlistCode` raises a pydantic `ValidationError`.

Both are pre-existing and were left alone in PR #142 to honor its no-drive-by
constraint; the Evxl fallback path was guarded for the second case there.
Cheap fix for the build: wrap it and reuse the "Invalid playlist data
returned by API" message. Widening the fallback to also fire when the search
*raises* is a design change, not a bug fix — it needs owner sign-off.

## Code Smells

## Refactors

### Split Evxl out of the `kovaaks` package

`EvxlPlaylist`/`EvxlPlaylistByCodeResponse` (`source/kovaaks/api_models.py`) and
`EVXL_PLAYLIST_BY_CODE_URL`/`get_evxl_playlist` (`source/kovaaks/api_service.py`)
are a third-party service living in KovaaK's-named modules. Deliberately left
there: `get_evxl_playlist` reuses the private `_get_with_retry` (thread-local
sessions, timeout config, the network-success signal), so a `source/evxl`
package would either reach into a private helper and depend on `kovaaks`
backwards, or require extracting a neutral shared HTTP client first.

Revisit when Evxl gains a **second** runtime endpoint — then extract
`source/http_client.py` and `source/evxl/` together (and update the
architecture.md module map). Not worth it for one fallback call. Note
`scripts/benchmark_importer/models.py` has its own duplicate Evxl models; a
split should decide whether they converge.

## Tooling

### Single-command local quality gate

CI enforces four of the five standard checks (ruff format, ruff lint, mypy,
pytest); `compileall` runs only in the local pre-handoff validation. Add one
local entry point (task runner or script) only if repeatedly typing the five
commands becomes burdensome.

## UI/UX

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
