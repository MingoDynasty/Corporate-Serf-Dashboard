# Decision Log

Durable project decisions that future contributors and agents should preserve unless a newer entry supersedes them.

Use this log for decisions that are hard to reverse, cross-cutting, based on external API behavior, or likely to be questioned later. Do not record every small implementation choice.

When a decision changes, keep the old entry and mark it `Superseded`. Add a new entry explaining what changed, why, and any migration notes.

## Status Values

- `Proposed`: under consideration, not yet agreed.
- `Accepted`: current agreed decision.
- `Superseded`: replaced by a newer decision.
- `Rejected`: considered and intentionally not chosen.

## 2026-04-27: Use JSON Files For Runtime API Caches

Status: Accepted

Decision: Store current API cache data as JSON files under `cache/`.

Why: The current cache use cases are simple key-value lookups with short or medium TTLs. JSON keeps the implementation transparent, easy to inspect, and low-friction.

Consequences: Cache reads must tolerate missing, malformed, stale, or partially-written files. Cache writes should be atomic where practical. Reconsider SQLite when we need rank history, multi-record queries, or stronger transactional guarantees.

## 2026-06-22: Keep User Runtime Data Under `data/`

Status: Accepted

Decision: Store user/runtime app data under a repo-local ignored `data/` directory. New runtime logs belong under `data/logs/`. Existing API caches remain under `cache/` until a separate migration moves them.

Why: Logs are runtime artifacts, but they are not cache. A dedicated `data/` root keeps future runtime state such as logs, imported/custom playlists, and an eventual SQLite database grouped in one place without mixing it with source-controlled resources.

Consequences: Keep bundled/default playlists under `resources/playlists/`. Put future user-imported or user-created playlists under `data/playlists/`. If the existing API cache moves from `cache/` to `data/cache/`, handle it as a dedicated compatibility migration instead of silently changing paths.

## 2026-04-27: Treat `total-play` As Metadata Only

Status: Accepted

Decision: Use `/user/scenario/total-play` only to hydrate or upsert scenario metadata such as `scenarioName -> leaderboardId`.

Why: The endpoint can lag behind current leaderboard scores and ranks. `/leaderboard/scores/global` is the authoritative source for current rank.

Consequences: Current-rank lookup should not trust score or rank data from `total-play`. The endpoint remains useful for cache initialization and metadata discovery.

## 2026-04-27: Keep KovaaK's API Details Behind `ScenarioRankInfo`

Status: Accepted

Decision: UI code consumes `ScenarioRankInfo` and should not know which KovaaK's endpoint produced the data.

Why: Endpoint details, fallback behavior, cache rules, and expected API failures belong in the service layer. This keeps Dash callbacks focused on rendering.

Consequences: Expected KovaaK's API/domain failures should become `ScenarioRankInfo(status=UNKNOWN, error_message=...)` in `api_service.py`. UI code can render `RANKED`, `UNRANKED`, or `UNKNOWN` without duplicating endpoint logic.

## 2026-04-27: Prefer Steam ID Matching When Configured

Status: Accepted

Decision: When `steam_id` is configured, prefer it for leaderboard identity matching. If Steam ID matching fails but exact username matching succeeds, keep the rank result and surface a warning.

Why: `usernameSearch` can return partial matches. Steam ID is the strongest identity check, but a mistyped Steam ID should not hide otherwise valid exact-username rank data.

Consequences: The warning is transient and derived from current config each time rank info is returned. It should not be persisted in rank cache.

## 2026-04-27: Make Leaderboard Total Enrichment Best-Effort

Status: Accepted

Decision: Leaderboard total lookup should never invalidate a valid rank or unranked result.

Why: Total players and percentile are enrichment data. If total lookup fails because of network errors, malformed responses, validation failures, or cache I/O issues, showing the valid rank alone is better than falling back to `N/A`.

Consequences: `_with_leaderboard_total()` catches expected total-enrichment failures, logs them, and returns the original `ScenarioRankInfo`.

## 2026-04-29: Cache Leaderboard Totals For One Week

Status: Accepted

Decision: `leaderboard_total_cache_ttl_hours` defaults to `168`, matching `scenario_rank_cache_ttl_hours`.

Why: Leaderboard total player counts are expected to increase slowly. For large leaderboards, a mildly stale total count changes displayed percentile by less than the UI's two-decimal precision in most cases, while avoiding daily cold-cache total fetches across every playlist scenario.

Consequences: Total-count freshness remains configurable. If users notice stale total counts causing misleading displays, revisit the TTL or add a targeted refresh flow.

## 2026-04-27: Use The Midpoint Percentile Formula

Status: Accepted

Decision: Derive percentile with:

```python
percentile = ((total_players - rank + 0.5) / total_players) * 100
```

Why: This matches the KovaaK's-style percentile behavior we agreed to use.

Consequences: Percentile is display-only metadata derived when rank info is returned. It is not stored in rank cache. No tiny-leaderboard special casing is planned, so `rank 1 of 1` displays `50.00%`.

## 2026-04-27: Keep KovaaK's API Findings In A Dedicated Notes File

Status: Accepted

Decision: Track KovaaK's endpoint behavior, relied-upon fields, and discovered quirks in `docs/kovaaks_api_notes.md`.

Why: We are probing unofficial or lightly documented API behavior across multiple milestones. Keeping API lore in one living document helps future agents avoid rediscovering endpoint semantics from chat history.

Consequences: When new endpoint behavior or failure modes are discovered, update the notes file and add regression coverage when practical.

## 2026-04-28: Retry KovaaK's GET Transient Failures Once

Status: Accepted

Decision: KovaaK's GET requests should retry exactly once on HTTP `429 Too Many Requests`, `requests.Timeout`, and `requests.ConnectionError`. `429` retries should honor `Retry-After` when present and cap the wait.

Why: Playlist scenario overview can create bursty cold-cache rank and total lookups. KovaaK's can also occasionally exceed the current read timeout for one row while adjacent requests succeed. A single bounded retry handles transient failures without turning the retry helper into a full scheduler or hiding unrelated failures.

Consequences: Retry remains GET-only. Non-429 HTTP failures and unexpected exceptions continue through the existing service-layer error handling. Recovered retries are logged but are not user-facing notifications.

## 2026-04-29: Drive Playlist Table Loads From Mounted Route State

Status: Accepted

Decision: Playlist scenario table loads should be driven by state created in the mounted `/playlists/<playlist_code>` layout, not directly by selector changes or URL-change callbacks.

Why: When the playlist selector changes the route, Dash Pages can briefly have the old page instance responding to the URL update before the new route layout finishes mounting. If the expensive table load listens directly to that navigation event, one user selection can trigger duplicate cache/API loads.

Consequences: Keep the selector callback navigation-only. The route layout should publish the resolved playlist code through a lightweight mounted component, currently `dcc.Store(id="playlist-scenarios-code")`, and the table-loading callback should use that mounted state as its trigger.

## 2026-04-29: Use Controlled AG Grid JS For Null-Aware Sorting

Status: Accepted

Decision: Playlist scenario AG Grid tables may use repo-owned JavaScript comparators from `assets/dashAgGridFunctions.js` with `dangerously_allow_code=True` when AG Grid requires client-side sort behavior that Python cannot provide directly.

Why: AG Grid sorting runs in the browser. The playlist table needs `NULLS LAST` behavior for rank, total, and percentile columns so unknown values do not sort ahead of real numeric values.

Consequences: Only reference controlled functions committed under `assets/`. Do not generate JavaScript strings from user input. If additional custom grid behavior is needed, prefer adding named functions to `assets/dashAgGridFunctions.js` rather than embedding ad hoc code in page callbacks.

## 2026-04-29: Use Thread-Local Sessions For KovaaK's GET Requests

Status: Accepted

Decision: KovaaK's GET requests should go through a reusable `requests.Session` scoped to the current worker thread.

Why: Cold-cache playlist table loads make many small HTTPS calls. Reusing sessions lets Requests keep connections alive and avoid repeated TCP/TLS setup. Keeping sessions thread-local avoids sharing one mutable `Session` object across the playlist table's concurrent worker threads.

Consequences: `_get_with_retry()` should call the thread-local session wrapper instead of `requests.get(...)` directly. Tests should patch that wrapper when faking HTTP responses. If we later add async HTTP or a centralized rate limiter, revisit this decision.

## 2026-06-20: Reference dash-ag-grid Grid Functions By Bare Name

Status: Accepted

Decision: In dash-ag-grid `{"function": "..."}` strings (`valueFormatter`, `tooltipValueGetter`, `comparator`, `valueGetter`, etc.), reference functions from the `assets/dashAgGridFunctions.js` registry by their **bare name** — `relativeTime(params.value, "Never")`, `nullsLastComparator` — never with a `dagfuncs.` prefix.

Why: dash-ag-grid (35.2.0) does not run these strings as a browser-global eval. It parses each to an AST and evaluates it against a constructed scope that spreads the contents of `window.dashAgGridFunctions` in as bare names (alongside `params`, `agGrid`, `d3`, `dash_clientside`). There is no `dagfuncs` object in that scope — the identifier never appears in the dash-ag-grid bundle — so `dagfuncs.X(...)` resolves to undefined and the expression **silently fails**: the cell renders the raw field value, or the comparator falls back to AG Grid's default sort, with no console error. The `assets/` file's `var dagfuncs = (window.dashAgGridFunctions = ...)` alias is only for *defining* the registry functions.

Consequences: Plain Dash `clientside_callback`s are different — they run in real browser global scope, so there use the full `window.dashAgGridFunctions.X(...)` path (e.g. the home page's "Last played" relative-time callback). This decision corrected two silent bugs: the grid "Last Played" `valueFormatter`/`tooltipValueGetter` (PR #17) and the `NULLS LAST` comparator on all sortable columns (PR #19), the latter broken since the 2026-04-29 "Use Controlled AG Grid JS For Null-Aware Sorting" entry. Verified by decompiling the installed bundle and by a live browser test.

## 2026-06-20: Interim Merge Bar Until Lint/Format Cleanup

Status: Accepted

Decision: Until the lint/format cleanup lands, the merge bar is: `uv run pytest` and `uv run mypy source` must be **green**, and `uv run pylint source` plus `black --check`/`isort --check` must **not regress versus `main`** (no new findings in the files a change touches). The absolute CLAUDE.md bar (pylint `fail-under = 10`, black/isort clean) is the target, not yet current reality.

Why: As of 2026-06-20 `main` is green on pytest and mypy (the latter since PR #18 deleted a dead `mypy.ini` that was shadowing `[tool.mypy]`), but not on pylint (9.22/10 — missing docstrings, TODOs, broad-except, too-many-*), `black --check` (3 files), or `isort --check` (2 files). Those are pre-existing and reproduce on the committed LF blobs (not a CRLF flap). There is no CI, so the gates are an honour-system check; blocking feature PRs on an absolute bar `main` itself cannot meet is incoherent, while a baseline-comparison bar keeps shipping unblocked without growing the debt.

Consequences: Reviewers compare pylint/black/isort output for the changed files against the `main` baseline rather than requiring a green absolute run; pytest and mypy are hard green gates. The remaining pylint cleanup is deferred tech debt (~115 findings on `main`, dominated by missing docstrings, plus fix-or-disable calls on `too-many-*`, `broad-except`, `fixme`, and similar); the `black`/`isort` deltas are a few files. Remove this interim framing once pylint and the formatters are green on `main`.

## 2026-06-21: Relative ("Humanized") Last-Played Timestamps

Status: Accepted

Decision: "Last played" renders as a relative, humanized string ("5 minutes ago") in both the home Scenario Stats block and the playlists grid, with the exact timestamp shown on hover (`%Y-%m-%d %I:%M:%S %p`). Formatting lives in a single shared pair of pure JS helpers (`relativeTime`/`absoluteTime`) in `assets/dashAgGridFunctions.js`. Rules: a single rounded unit, never compound — just now (≤60s, including ≤0 / future) → N minutes → N hours → N days → N months → N years, with months/years calendar-based and a `max(0, …)` clamp (no `Intl` dependency, no "over"/"about" prefix). The value stays relative all the way (no absolute-date cutover) because it is a staleness gauge, not a reference date. Timestamps are epoch **seconds** end-to-end (the JS multiplies by 1000). Sentinels: "Never" on the grid (in a playlist but never played), "N/A" on home (no selection / not in DB) — never blank. The home value self-updates via a dedicated 30s `dcc.Interval` (decoupled from `polling_interval`); the grid live-ticks via a dedicated interval + `refreshCells({force: true, columns: ['last_played_sort']})`.

Why: A relative string answers "how stale is this?" directly, while the tooltip preserves the exact instant. Hand-rolled formatting (~30 lines) is simpler than `Intl` for an English-only app and fully controls the edges; calendar-based month/year math matches what a human reading two dates would say and avoids day-division boundary fudges.

Consequences: Shipped in PRs #17/#19 (Phase 1: shared helpers, home self-update, grid render-on-load) and #23 (Phase 2: grid live-ticking). Exact-timestamp access is hover-only (tooltip), consciously waived for this local single-user app. For how grid colDef `{"function": ...}` strings invoke these helpers, see the 2026-06-20 "Reference dash-ag-grid Grid Functions By Bare Name" entry. This entry distills and replaces `docs/relative_timestamp_proposal.md`, now deleted.
