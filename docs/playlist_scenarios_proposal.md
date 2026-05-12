# Playlist Scenarios Overview Proposal v4

## Summary

Build M1 as a new playlist scenario table page that turns existing rank, total, and percentile data into a training-priority view.

Sub-M1a should ship first and stay focused on page architecture plus rank fanout:

- Routes:
  - `/playlists` — selector dropdown + empty prompt; redirects to `/playlists/{playlistCode}` on selection
  - `/playlists/{playlistCode}` — per-playlist scenarios table
- Playlist selector synced with URL
- Table columns: Scenario, Rank, Total, Percentile
- Sortable table via Dash AG Grid
- Cold-cache loads wrapped in `dcc.Loading`
- Per-row failures degrade to `N/A`, not page failure

A new navbar entry "Playlists" lands on `/playlists`. The bare-route selector is M1's transitional mechanism for picking a playlist; when M2 ships, that page becomes the playlist-level overview (selector removed) and overview rows become clickable links to `/playlists/{playlistCode}`. The per-playlist route is stable across milestones.

M0 API retry support has shipped, so M1 can rely on the existing `_get_with_retry(...)` behavior for transient 429s.

## Key Changes

- Add a new playlist scenarios page registered with Dash pages.
- Use `playlistCode` as the canonical URL identifier.
- Register both routes for M1:
  - `/playlists` — selector + empty prompt; redirects to `/playlists/{playlistCode}` on selection. Content evolves to M2's overview when M2 ships.
  - `/playlists/{playlistCode}` — per-playlist scenarios table. Stable across milestones.
- Add a navbar entry "Playlists" → `/playlists`. Stays as the single "Playlists" entry across M1 and M2.
- Refactor playlist data access so the app can look up playlists by code, not only by display name.
- Preserve full `PlaylistData` in memory so helpers can access name, code, and scenarios without parallel mappings.
- Add a dedicated playlist-row builder service, for example `build_playlist_scenario_rank_rows(...)`, so UI callbacks do not own fanout/concurrency details.
- Use `ThreadPoolExecutor(max_workers=4)` for playlist table rank lookups, separate from the existing watchdog rank refresh executor.
- Add `dash-ag-grid` as a project dependency.

### Worker count rationale

Four workers gives ~2-second worst case for a 40-scenario cold cache (40 scenarios × 2 calls per scenario × ~100ms per call ÷ 4 workers ≈ 2 seconds), while keeping API load modest. Most usage will hit warm caches and complete near-instantly. The worker count is a default, not a precious value — adjustable if observed latency or rate-limiting suggests otherwise.

## Table Behavior

- Use Dash AG Grid for sorting.
- No default sort; initial row order follows the playlist scenario order.
- Store display values separately from sort values:
  - display: `"11,290"`, `"63,892"`, `"82.33%"`
  - sort: `11290`, `63892`, `82.33`
- Missing sort values sort last when users sort a column.
- Ranked rows display:
  - Rank: `11,290`
  - Total: `63,892`
  - Percentile: `82.33%`
- Unranked rows display:
  - Rank: `Unranked`
  - Total: `63,892` when available, otherwise `N/A`
  - Percentile: `N/A`
- Unknown/error rows display `N/A` for rank, total, and percentile.
- One scenario failure must not prevent the rest of the table from rendering.

## Sub-Milestones

### Sub-M1a Core

Page architecture and the four columns that depend only on existing rank infrastructure.

Columns:

- Scenario
- Rank
- Total
- Percentile

Plus: registration of both routes (`/playlists` bare, `/playlists/{playlistCode}` parameterized), navbar entry, playlist selector with URL sync (selector lives at bare `/playlists` and on the parameterized route for in-place switching during M1's lifetime), AG Grid table, rank fanout via `ThreadPoolExecutor(max_workers=4)`, `dcc.Loading` wrapper, row-level failure handling.

### Sub-M1b Local Stats

Add columns sourced from existing local helpers:

- Last Played (`get_scenario_stats`)
- Runs (`get_scenario_stats`)
- High Score (`get_high_score`)

Pure UI extension on top of Sub-M1a — no new fanout, no new data plumbing.

### Sub-M1c PB Metadata

Add columns sourced from the personal-best run file:

- cm360 (from PB run's `attributes.cm360`)
- Accuracy (from PB run's `attributes.accuracyDamage`)

Requires identifying the local run with the highest score for a given scenario and pulling PB-specific metadata from that run. The local CSV data does not expose KovaaK's full API `attributes` object, so implementation uses parsed local equivalents:

- PB cm360 is available when the PB file uses `cm/360` as the sensitivity scale.
- PB Accuracy uses damage accuracy when `Damage Done / Damage Possible` is available, with hit accuracy as a fallback for older or incomplete files.

## Out of Scope For M1a

- color-coded percentile
- trend column
- next-rank threshold
- row click drilldown
- playlist-level summary
- progressive per-cell updates

## M2 Transition Notes

Forward-looking notes for when M2 ships, captured here so M1 implementation doesn't treat transitional pieces as permanent:

- The bare `/playlists` content (selector + empty prompt) is replaced by M2's playlist-level overview.
- The selector dropdown is removed when M2 ships. M2's overview becomes the canonical way to pick a playlist — richer than a name-only dropdown because it surfaces metadata (last played, average percentile, etc.) that drives discovery, including the "haven't played in 6 months" use case a name dropdown can't help with.
- The per-playlist route `/playlists/{playlistCode}` is unchanged. M2's overview rows navigate to it by setting `playlistCode` in the URL.
- The selector dropdown on the per-playlist page is also removed post-M2. Switching playlists then means navigating back to `/playlists` (M2 overview) and clicking another row. Implementation should keep the selector code separate enough that removal is a clean delete, not a refactor.
- M2 will need to make overview rows visibly clickable (cursor pointer on hover, row hover tint, full-row click target, helper text). Those are M2's concerns; mentioned here only so M1 doesn't accidentally bake the M1 selector into the per-playlist page in a way that would block their removal.

## Trade-Offs

| Decision | Alternative | Reason |
|---|---|---|
| Two pages (M1 then M2) | Combined page with both views | Each page does one thing well; M1 ships standalone in days; M2 designed independently. |
| `playlistCode` in URL | `playlistId` (numeric) | Human-readable, already user-facing via import flow. Falls back to `playlistId` only if encoding becomes an issue. |
| `/playlists` evolves M1 → M2 | Decoupled routes (e.g., `/scenarios` for M1, `/playlists` for M2) | Single canonical landing route; navbar destination stable across milestones; M2 is purely additive at the URL parameter level (overview rows link to M1's existing `/playlists/{playlistCode}`). |
| Selector dropped post-M2 | Keep selector permanently for in-place switching | M2's overview is a strictly richer playlist picker — surfaces metadata, not just names. Keeping the selector would be M1 scaffolding outliving its purpose, plus duplicate the playlist-picking mechanism. |
| AG Grid | DataTable / dmc.Table | DataTable is deprecated; dmc.Table lacks sorting. AG Grid is the dmc-recommended path for interactive tables. |
| Render-when-ready | Progressive cell updates | Simpler implementation; ~2-second worst case is acceptable for a one-time event. Progressive is a v2 polish. |
| 4 workers | 8 / 16 workers | 2-second worst case is well inside acceptable. No UX win from going higher. Lower API load is the better citizen. |
| No default sort | Default sort by percentile ascending | Removes implicit prescription; matches existing scenario-dropdown order; user clicks once for any sort. |
| UNRANKED sorts last (NULLS LAST) | Hide / dedicated section / sort first | Faithful to data; doesn't nudge or marginalize. |
| Display vs sort values separated | Single formatted string per cell | AG Grid sorts on the data it's given; pre-formatted strings sort lexicographically wrong. Required for correct numeric sorting. |

## Test Plan

- Add service tests for playlist lookup by code and row building.
- Add row-formatting tests for ranked, unranked with total, unranked without total, and unknown/error rows.
- Add tests confirming numeric sort fields are separate from formatted display strings.
- Add a concurrency/failure test showing one failed rank lookup produces an `N/A` row while other rows still render.
- Add a route/page smoke test for both `/playlists` (bare, shows selector + empty prompt) and `/playlists/{playlistCode}` (with code, shows table) if current Dash test structure supports it.
- Run:
  - `uv run pytest tests`
  - `uv run ruff check source tests`
  - `uv run python -m compileall source tests`

## Assumptions

- M1 ships incrementally across sub-milestones rather than as one large change.
- `dash-ag-grid` will be added as a project dependency.
- The first page version renders complete table data in one shot rather than progressively updating rows.
- Playlist code remains the URL identity, while playlist name remains display text.
- The proposal document should replace the current M1 proposal content once file edits are allowed.
