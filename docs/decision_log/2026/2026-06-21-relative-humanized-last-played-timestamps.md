# 2026-06-21: Relative ("Humanized") Last-Played Timestamps

Status: Superseded in part by the 2026-06-30 home empty-state decision; for the exact absolute-string format (`%Y-%m-%d %I:%M:%S %p`), by the 2026-07-11 humanized absolute-format decision; and, for the grid sentinel's scope and the single-column `refreshCells` call, by the [2026-08-09 PB-sentinel decision](2026-08-09-pb-columns-keep-their-na-sentinel-even-for-timestamps.md)

**Superseded in part (2026-10-18).** [Last played leaves Scenario Stats](2026-10-18-last-played-leaves-scenario-stats-and-its-first-line-is-plain-text.md):
Run History's Scenario Stats card, the home block's successor, no longer
shows Last played. The playlist grids' Last Played column, and the shared
helpers and their rules, stand.

Decision: "Last played" renders as a relative, humanized string ("5 minutes ago") in both the home Scenario Stats block and the playlists grid, with the exact timestamp shown on hover (`%Y-%m-%d %I:%M:%S %p`). Formatting lives in a single shared pair of pure JS helpers (`relativeTime`/`absoluteTime`) in `assets/dashAgGridFunctions.js`. Rules: a single rounded unit, never compound — just now (≤60s, including ≤0 / future) → N minutes → N hours → N days → N months → N years, with months/years calendar-based and a `max(0, …)` clamp (no `Intl` dependency, no "over"/"about" prefix). The value stays relative all the way (no absolute-date cutover) because it is a staleness gauge, not a reference date. Timestamps are epoch **seconds** end-to-end (the JS multiplies by 1000). Sentinels: "Never" on the grid (in a playlist but never played), "N/A" on home (no selection / not in DB) — never blank. The home value self-updates via a dedicated 30s `dcc.Interval` (decoupled from `polling_interval`); the grid live-ticks via a dedicated interval + `refreshCells({force: true, columns: ['last_played_sort']})`.

Why: A relative string answers "how stale is this?" directly, while the tooltip preserves the exact instant. Hand-rolled formatting (~30 lines) is simpler than `Intl` for an English-only app and fully controls the edges; calendar-based month/year math matches what a human reading two dates would say and avoids day-division boundary fudges.

Consequences: Shipped in PRs #17/#19 (Phase 1: shared helpers, home self-update, grid render-on-load) and #23 (Phase 2: grid live-ticking). Exact-timestamp access is hover-only (tooltip), consciously waived for this local single-user app. For how grid colDef `{"function": ...}` strings invoke these helpers, see the 2026-06-20 "Reference dash-ag-grid Grid Functions By Bare Name" entry. This entry distills and replaces `docs/relative_timestamp_proposal.md`, now deleted.
