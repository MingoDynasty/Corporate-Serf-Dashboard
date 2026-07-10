# Decision Log

Durable project decisions that future contributors and agents should preserve unless a newer entry supersedes them.

Use this log for decisions that are hard to reverse, cross-cutting, based on external API behavior, or likely to be questioned later. Do not record every small implementation choice.

When a decision changes, keep the old entry and mark it `Superseded`. Add a new entry explaining what changed, why, and any migration notes.

## Status Values

- `Proposed`: under consideration, not yet agreed.
- `Accepted`: current agreed decision.
- `Superseded`: replaced by a newer decision.
- `Rejected`: considered and intentionally not chosen.

## 2026-07-09: Load Configuration Lazily At Application Startup

Status: Accepted

Decision: Configuration is loaded and cached through `get_config()` instead of
at module import. `main()` owns the initial load and translates expected file,
decode, TOML, and validation failures into the existing concise startup error
before loading playlists or initializing runtime services. Other modules resolve
the cached configuration only inside function bodies.

Why: Import-time loading forced pytest to overwrite the real repo-root
`config.toml`, keeping its backup only in process memory. Abnormal termination
could permanently replace a user's configuration, and concurrent test sessions
could corrupt each other's backup/restore chain. A lazy production accessor makes
modules import-safe and gives tests an in-process seam without adding a test-only
environment-variable override.

Consequences: Tests monkeypatch the config loader and clear the accessor cache;
they never modify the real `config.toml`. `get_config()` propagates load errors,
while the executable startup boundary alone prints the user-facing message and
exits. Playlist loading happens in `main()` after configuration validation so a
bad config still produces exactly one clean error with no prior warning output.

## 2026-07-09: Accept Unsynchronized In-Memory Stores (Single-Writer)

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

## 2026-07-08: Judge Score-Threshold Notifications Against The Previous PB

Status: Accepted

Decision: Score-threshold notification verdicts compare in score space against
the personal best the run was chasing:
`score >= previous_high_score * score_threshold_percentage / 100`. The overlay
line still uses the current post-run personal best for the same percentage
setting.

Why: The toast already displays the run's percentage against the previous PB.
Using the post-run PB for the verdict made goals above 100% unreachable,
because a new PB moved the target upward before the run was judged. Keeping the
comparison in score space preserves the exact-threshold `>=` boundary; the
displayed-ratio form can round `820 / 800 * 100` below `102.5` and turn an
exact hit into a failure.

Consequences: Goals above 100% now pass when a run beats the previous PB by
the configured margin. New-scenario and new-sensitivity events still carry
`previous_high_score=None`, so they remain verdict-less. Backlog summaries keep
judging only the batch's latest run; fuller historical pass/fail review belongs
to run history.

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

## 2026-07-07: Use Playlist Codes As Playlist Identity

Status: Accepted

Decision: Treat KovaaK's playlist `code` as the app's playlist identity everywhere: the in-memory `playlist_database` key, route value, selector value, import duplicate check, and import filename suffix. Playlist names are display-only labels. Selectors receive finished `{label, value}` options from the service; labels become `Name (CODE)` only when duplicate names need disambiguation.

Why: KovaaK's playlist names are not unique, so name-keyed storage silently dropped later same-named playlists and made those playlists unreachable even by their stable code routes. Codes are already user-facing through share-code imports and `/playlists/{playlistCode}` URLs, so they are the stable identity to preserve.

Consequences: The startup loader scans top-level JSON files from `resources/playlists/` first and `data/playlists/` second, sorted within each root by `(filename.casefold(), filename)`. The first occurrence of a code wins; duplicate-code files are skipped with a warning naming both files, and startup warnings are buffered until the UI mounts so they become visible notifications instead of being dropped outside Dash callback context. This supersedes the 2026-07-05 proposal call that user-root files should win: the final rule is bundled-wins because bundled benchmark files carry rank data and share-code imports do not. New imports write atomically to `data/playlists/{sanitized name} [{code}].json`; importing an existing code is refused with a user-visible message naming the existing playlist. The `data/playlists/` root may be absent on clean checkouts and is created on first import. Legacy user imports under `resources/playlists/` are a clean break, not migrated; owners preview and remove ignored legacy files manually with `git clean -Xn resources/playlists` then `git clean -Xf resources/playlists`, re-importing anything still wanted by share code.

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

## 2026-06-21: Keep The Hand-Rolled GET Retry; Defer urllib3 `Retry` Migration

Status: Accepted

Decision: Keep the hand-rolled retry helpers in `source/kovaaks/api_service.py`
(`_get_with_retry`, `_retry_after_seconds`) instead of mounting a urllib3
`HTTPAdapter(max_retries=Retry(...))` on the thread-local sessions. Reconsider
only when requirements grow past one retry (exponential backoff with jitter, a
broader `status_forcelist` such as 503, separate connect/read budgets).

Why: The happy path maps cleanly onto urllib3 `Retry`, but a faithful migration
is not a clean delete. It would lose the 0.5s default delay on a 429 without
`Retry-After` (urllib3 sleeps 0s on the first retry), change the exhaustion
exception types the tests assert on (`HTTPError`/bare timeout become
`RetryError`/wrapped `ConnectionError`), downgrade recovered-retry logging from
WARNING to a DEBUG line on urllib3's logger, and still require a wrapper for the
per-request timeout default. Preserving the 5s `Retry-After` cap needs
`retry_after_max`, which requires pinning `urllib3>=2.6` — currently only a
transitive dependency. Net-neutral complexity plus a full test rewrite does not
clear the bar for replacing working, ratified code.

Consequences: The retry layer stays per-request and hand-rolled; the score-aware
rank refresh loop sits on top of it and relies on its contract (one inner retry,
bounded sleeps). If migrating later, the minimal-drift recipe is: one
module-level `Retry(total=1, status=1, connect=1, read=1, status_forcelist=[429],
allowed_methods={"GET"}, retry_after_max=5, raise_on_status=False)` mounted on
both schemes of each thread-local session, a thin wrapper retained for the
timeout default and WARNING log, and an explicit `urllib3>=2.6` floor. The full
analysis lives in git history as `docs/api_retry_urllib3_migration_proposal.md`.

## 2026-07-03: Playlists Routes Are Stable; The Bare-Route Selector Is Transitional

Status: Accepted

Decision: The playlists feature owns two routes: `/playlists` (navbar
destination) and `/playlists/{playlistCode}` (per-playlist scenario table).
The per-playlist route and its `playlistCode` URL identity are stable
contracts. The current content of the bare route — a selector dropdown plus an
empty prompt — is transitional scaffolding from milestone 1: when the
playlist-level overview (roadmap milestone 2) ships, the overview replaces the
bare-route content, overview rows navigate to `/playlists/{playlistCode}`, and
the selector dropdowns are removed from both pages.

Why: A single canonical landing route keeps the navbar destination stable
across milestones, and the human-readable playlist code is already user-facing
via the import flow. The overview is a strictly richer playlist picker than a
name-only dropdown (it surfaces last-played, aggregate percentile, and similar
metadata), so keeping the selector after it ships would be scaffolding
outliving its purpose. Distilled from the milestone-1 playlist scenarios
proposal (shipped in PRs #12, #15, #16).

Consequences: Keep the selector wiring separate enough that its removal is a
clean delete, not a refactor. Post-overview, switching playlists means
navigating back to `/playlists` and clicking a row, so the overview needs
visible row-click affordances (cursor, hover tint, full-row target). Do not
bake the selector into the per-playlist page in a way that blocks removal.

## 2026-06-20: Reference dash-ag-grid Grid Functions By Bare Name

Status: Accepted

Decision: In dash-ag-grid `{"function": "..."}` strings (`valueFormatter`, `tooltipValueGetter`, `comparator`, `valueGetter`, etc.), reference functions from the `assets/dashAgGridFunctions.js` registry by their **bare name** — `relativeTime(params.value, "Never")`, `nullsLastComparator` — never with a `dagfuncs.` prefix.

Why: dash-ag-grid (35.2.0) does not run these strings as a browser-global eval. It parses each to an AST and evaluates it against a constructed scope that spreads the contents of `window.dashAgGridFunctions` in as bare names (alongside `params`, `agGrid`, `d3`, `dash_clientside`). There is no `dagfuncs` object in that scope — the identifier never appears in the dash-ag-grid bundle — so `dagfuncs.X(...)` resolves to undefined and the expression **silently fails**: the cell renders the raw field value, or the comparator falls back to AG Grid's default sort, with no console error. The `assets/` file's `var dagfuncs = (window.dashAgGridFunctions = ...)` alias is only for *defining* the registry functions.

Consequences: Plain Dash `clientside_callback`s are different — they run in real browser global scope, so there use the full `window.dashAgGridFunctions.X(...)` path (e.g. the home page's "Last played" relative-time callback). This decision corrected two silent bugs: the grid "Last Played" `valueFormatter`/`tooltipValueGetter` (PR #17) and the `NULLS LAST` comparator on all sortable columns (PR #19), the latter broken since the 2026-04-29 "Use Controlled AG Grid JS For Null-Aware Sorting" entry. Verified by decompiling the installed bundle and by a live browser test.

## 2026-06-20: Interim Merge Bar Until Lint/Format Cleanup

Status: Superseded by the 2026-07-03 ruff-only tooling decision

Decision: Until the lint/format cleanup lands, the merge bar is: `uv run pytest` and `uv run mypy source` must be **green**, and `uv run pylint source` plus `black --check`/`isort --check` must **not regress versus `main`** (no new findings in the files a change touches). The absolute CLAUDE.md bar (pylint `fail-under = 10`, black/isort clean) is the target, not yet current reality.

Why: As of 2026-06-20 `main` is green on pytest and mypy (the latter since PR #18 deleted a dead `mypy.ini` that was shadowing `[tool.mypy]`), but not on pylint (9.22/10 — missing docstrings, TODOs, broad-except, too-many-*), `black --check` (3 files), or `isort --check` (2 files). Those are pre-existing and reproduce on the committed LF blobs (not a CRLF flap). There is no CI, so the gates are an honour-system check; blocking feature PRs on an absolute bar `main` itself cannot meet is incoherent, while a baseline-comparison bar keeps shipping unblocked without growing the debt.

Consequences: Reviewers compare pylint/black/isort output for the changed files against the `main` baseline rather than requiring a green absolute run; pytest and mypy are hard green gates. The remaining pylint cleanup is deferred tech debt (~115 findings on `main`, dominated by missing docstrings, plus fix-or-disable calls on `too-many-*`, `broad-except`, `fixme`, and similar); the `black`/`isort` deltas are a few files. Remove this interim framing once pylint and the formatters are green on `main`.

## 2026-07-03: Consolidate Formatting And Linting On Ruff

Status: Accepted

Decision: Use ruff as the sole formatter and linter, with mypy and pytest retained as separate gates. Ruff formats at 88 characters and enforces a 120-character hard ceiling through `E501`. Lint `source/` and `tests/`, but exclude `scripts/`; tests are exempt from missing-docstring, design-metric, and unused-argument rules. Require docstrings in `source/`, leave deliberate TODOs unenforced, and keep preview mode disabled. Local pre-commit hooks enforce ruff check and format; mypy, pytest, and the inexpensive CPython `compileall` syntax check remain manual validation because the project has no CI.

Why: The previous black, isort, and pylint configuration described conflicting line lengths, duplicated responsibilities, and could not meet its own score gate while intentional TODOs remained. One pinned ruff configuration provides a green, deterministic format/lint bar without a score or `fail-under`, while preserving the established 88-character formatting and keeping tests and replacement-bound scripts free from low-value lint churn.

Consequences: Pylint, black, and isort are no longer direct dependencies or configured tools. Black and isort remain transitive lockfile dependencies of `datamodel-code-generator`. Accepted enforcement losses are: no ruff equivalents for duplicate-code, too-many-instance-attributes, or too-many-lines; preview-only rules for unspecified-encoding, too-many-locals, too-many-positional-arguments, too-many-boolean-expressions, and too-many-nested-blocks remain disabled; and `no-else-return` is outside the selected rule families. The two current encoding omissions and the current unnecessary `else` were fixed once during migration, but are not ongoing gates. Keep the pre-commit ruff revision synchronized with the ruff version in `uv.lock`, and add CI or a single-command task runner separately.

## 2026-07-03: CI Runs The Merge Bar On Every PR

Status: Superseded in part by the 2026-07-06 cross-repo Python v2 tooling decision

Decision: A single GitHub Actions `gates` job runs the repository merge bar on
every pull request and push to `main`: ruff format check, ruff lint, mypy,
CPython `compileall`, and pytest. It runs on `windows-latest`, validates the
lockfile with `uv sync --locked`, and executes each gate with
`uv run --no-sync`. Python and uv are pinned, action dependencies use immutable
full commit SHAs, the workflow token has read-only contents access, and
superseded runs on the same ref are cancelled.

Why: This fulfills the deferred CI consequence of the 2026-07-03 ruff
consolidation decision. An executable merge bar catches stale lockfiles,
formatting drift, type errors, syntax errors, and regressions consistently,
including on doc-only changes where the docs hygiene tests still matter.
Windows matches the supported development and runtime environment.

Consequences: `.github/workflows/gates.yml` is the canonical executable list of
gates. Local pre-handoff validation remains unchanged because it is the fastest
feedback path. A local single-command task runner remains optional rather than
part of this decision. After the workflow has established a short green
history, the repository owner should mark the `gates` check required on
`main`; branch protection is intentionally outside the workflow.

## 2026-07-06: Adopt The Cross-Repo Python V2 Tooling Spec

Status: Accepted

Supersedes: The workflow shape, command set, tool and runtime pin placement,
and concurrency behavior in the 2026-07-03 CI decision. Windows execution,
locked dependency sync, SHA-pinned actions, read-only contents permission, and
the broader local pre-handoff validation remain in force.

Decision: Use the canonical `tooling-spec: python-v2` workflow at
`.github/workflows/ci.yml`. Its matrix-backed `test (windows-latest)` job runs
`uv sync --locked`, ruff format, ruff lint, bare mypy, and bare pytest.
`pyproject.toml` owns the required uv version (`==0.11.26`), pytest discovery
and options, and mypy's `source/` scope. The workflow no longer overrides Git
line endings, cancels superseded runs, caches uv, pins Python or uv through
`setup-uv`, or runs `compileall`.

Why: The cross-repo spec keeps local and CI invocations aligned through project
configuration and gives repositories one recognizable CI shape. Moving the uv,
pytest, and mypy defaults into `pyproject.toml` makes the bare commands
authoritative in every environment instead of relying on workflow-only flags.

Consequences: Local pre-handoff validation still includes `compileall`, while
CI has four named checks inside the single Windows matrix job. CI resolves a
compatible interpreter from `requires-python = ">=3.14"`; this migration does
not add a `.python-version` pin. The required branch-protection check changes
from `gates` to `test (windows-latest)` and must be updated by the repository
owner at merge time. Add a minimal `.gitattributes` only if a runner actually
reports line-ending format drift; the migration's first CI run did not.

## 2026-06-21: Relative ("Humanized") Last-Played Timestamps

Status: Superseded in part by the 2026-06-30 home empty-state decision

Decision: "Last played" renders as a relative, humanized string ("5 minutes ago") in both the home Scenario Stats block and the playlists grid, with the exact timestamp shown on hover (`%Y-%m-%d %I:%M:%S %p`). Formatting lives in a single shared pair of pure JS helpers (`relativeTime`/`absoluteTime`) in `assets/dashAgGridFunctions.js`. Rules: a single rounded unit, never compound — just now (≤60s, including ≤0 / future) → N minutes → N hours → N days → N months → N years, with months/years calendar-based and a `max(0, …)` clamp (no `Intl` dependency, no "over"/"about" prefix). The value stays relative all the way (no absolute-date cutover) because it is a staleness gauge, not a reference date. Timestamps are epoch **seconds** end-to-end (the JS multiplies by 1000). Sentinels: "Never" on the grid (in a playlist but never played), "N/A" on home (no selection / not in DB) — never blank. The home value self-updates via a dedicated 30s `dcc.Interval` (decoupled from `polling_interval`); the grid live-ticks via a dedicated interval + `refreshCells({force: true, columns: ['last_played_sort']})`.

Why: A relative string answers "how stale is this?" directly, while the tooltip preserves the exact instant. Hand-rolled formatting (~30 lines) is simpler than `Intl` for an English-only app and fully controls the edges; calendar-based month/year math matches what a human reading two dates would say and avoids day-division boundary fudges.

Consequences: Shipped in PRs #17/#19 (Phase 1: shared helpers, home self-update, grid render-on-load) and #23 (Phase 2: grid live-ticking). Exact-timestamp access is hover-only (tooltip), consciously waived for this local single-user app. For how grid colDef `{"function": ...}` strings invoke these helpers, see the 2026-06-20 "Reference dash-ag-grid Grid Functions By Bare Name" entry. This entry distills and replaces `docs/relative_timestamp_proposal.md`, now deleted.

## 2026-06-30: Model Home Last-Played Empty States Explicitly

Status: Accepted

Supersedes: The home sentinel and hover-only tooltip interaction in the 2026-06-21 relative timestamp decision. The playlist-grid behavior and shared timestamp formatting rules remain unchanged.

Decision: Home Scenario Stats distinguishes three "Last played" states: no scenario selected renders `—`; a selected scenario with no local play data renders `Never`; and a selected scenario with play data renders the relative timestamp. Only a real timestamp receives the dotted underline and `cursor: help` affordance. Its exact local timestamp (`%Y-%m-%d %I:%M:%S %p`) is available by hover, keyboard focus, or touch. Empty states are not focusable and disable the tooltip entirely.

Why: `—` communicates an unselected field without implying missing or failed data, while `Never` communicates a known selected scenario with no recorded plays. Showing the affordance only when more information exists keeps the interaction honest and avoids a tooltip that merely repeats an empty-state value.

Consequences: The home callback owns the empty-state value and tooltip affordance alongside the raw timestamp. The clientside relative-time callback continues to own the live-updating visible timestamp. A selected scenario missing from the local database is treated as having no local play data; temporary loading or error states must not be mapped to `Never`.

## 2026-07-01: Keep Scenario Rank Consistent With Score-Aware Refreshes

Status: Accepted

Supersedes: The `ThreadPoolExecutor(max_workers=2)` high-score refresh and the
decision not to provide manual rank refresh in the original scenario rank
proposal (since distilled into this log and deleted).

Decision: After a local high score, run a bounded score-aware refresh using a
daemon `threading.Timer` chain with delays of 2, 4, 8, 16, and 32 seconds. Accept
the leaderboard as caught up only when its score reaches the two-decimal floor of
the local score. Route every automatic rank-cache write through one process-locked
monotonic writer so a lower score or transient `UNRANKED` result cannot replace a
known better value. The home rank widget passively re-reads rank and total caches
on its existing interval without making network calls, including when those cache
files are older than their normal TTLs. A user-clicked Refresh performs one
authoritative fetch and may deliberately write a lower score or `UNRANKED` result.

Why: KovaaK's leaderboard updates are eventually consistent, so the old single
post-PB fetch could persist lagging data for the week-long cache TTL. Timer
attempts keep delayed work off a bounded executor, centralized write arbitration
prevents loop/read races, and the cache-only UI poll surfaces successful background
writes within about one second. Automatic rechecks after the bounded window would
hammer permanently divergent offline/server-down scores; explicit Refresh gives
the user a bounded escape hatch instead.

Consequences: Automatic rank displays move forward by score and never flicker from
a known rank to `UNRANKED`; explicit Refresh is board-authoritative and can move
backward after a leaderboard reset. Interval ticks resolve only cached leaderboard
IDs, read rank and total files independent of TTL, emit no repeated warning/error
toasts, and make zero KovaaK's requests. A refresh loop that exhausts leaves the
previous cache untouched and asks the user to click Refresh. The retry schedule is
a code constant, not configuration.

## 2026-07-03: Import Benchmarks From Evxl And KovaaK's

Status: Accepted

Decision: The benchmark importer uses Evxl to resolve playlist names and codes,
and KovaaK's to fetch benchmark rank thresholds. In project terminology, a
*playlist* is a bare scenario list without rank data; a *benchmark* is a
playlist plus rank thresholds and colors. Generated benchmark JSON carries a
`generated_from` provenance stamp containing the Evxl sharecode, KovaaK's
benchmark ID, ordered rank-color pairs, generation timestamp, and generator
name.

Why: KovaaK's playlist search cannot resolve every known sharecode, while Evxl's
exact-code endpoint can; Evxl does not expose the per-scenario rank thresholds,
so KovaaK's remains authoritative for those values. The terminology distinguishes
the app's playlist import from the richer files produced by the importer.
Provenance makes the upstream inputs inspectable and allows generated files to be
checked for stale or mismatched benchmark metadata.

Consequences: Keep Evxl-specific resolution and snapshot handling in
`scripts/benchmark_importer/` unless an app-side feature explicitly adopts that
dependency. Preserve rank-color order when comparing provenance because colors
pair positionally with KovaaK's thresholds. Conflicting duplicate Evxl
sharecodes must be skipped and reported rather than resolved first-wins because
a missing benchmark is visible and recoverable, while silently pairing the wrong
rank thresholds is not. KovaaK's threshold changes under an unchanged benchmark
ID remain invisible to provenance checks and require an explicit forced refresh.

## 2026-07-06: Coalesce Pending Home Run Events

Status: Accepted

Decision: Home's `check_for_new_data` callback is the sole consumer of the
process-wide run-event deque. On each invocation it drains all pending messages,
lands on the most recently played scenario when automatic scenario switching is
enabled, and publishes a JSON-safe `run-events` summary for that scenario.
`generate_graph` rebuilds from the already-current in-memory stores and creates
toasts from that summary only when `run-events` triggered it. A single run keeps
the existing per-run toast behavior; a backlog produces one scenario-named
summary based on the latest matching run. The watchdog must successfully load a
run into the stores before enqueueing its message. The supported usage model is
one active Home tab; extra tabs remain crash-safe but unsynchronized.

Why: Home's interval does not run while the page is unmounted, so queued events
previously replayed one tick at a time on return. That rebuilt the same final
plot repeatedly, moved the scenario dropdown through stale history, and emitted
stale toast batches. Enqueue-before-load also allowed a consumer to rebuild
before the corresponding run was queryable, or to toast a run whose second parse
failed.

Consequences: A backlog is consumed in one tick, produces at most one dropdown
change and one toast batch, and cannot expose a message without queryable run
data. Mixed-scenario counts describe only the landing scenario. Nonmatching
events are discarded when automatic switching is off, preserving the previous
policy without wasting ticks. Coherent multi-tab delivery would require a
broadcast or push transport and remains outside this local single-user design.

## 2026-07-06: One Word Per Concept In Leaderboard Verbiage

Status: Accepted

Decision: "Rank" was used for both benchmark tiers (Bronze/Silver/..., Rank
Overlay) and leaderboard placement (Home "Rank:", grid "Current Rank"),
mirroring a split in the ecosystem (KovaaK's leaderboards: rank = position;
Voltaic/Aimlabs: rank = tier). In user-facing text, **Rank** means tier only,
**Position** means leaderboard placement ("Total Players" for board size), and
**PB** prefixes stats of the personal-best run (PB Score, PB cm/360, PB
Accuracy). "Unranked" is retained as KovaaK's own term for having no leaderboard
entry.

Consequences: Labels, plot annotations, and toasts follow the invariant.
Internal identifiers, component ids, and row field names keep their old names
because this is a label-only rename. New UI text must not reintroduce "rank" for
leaderboard placement.

## 2026-07-06: Let The Playlist Scenarios Grid Own Vertical Scrolling

Status: Accepted

Decision: Bound the playlist scenarios page to the Mantine AppShell content
viewport and let the AG Grid use its normal layout with an internal vertical
scrollbar. The page Stack and Dash Loading wrappers form a flex column, and the
grid fills the remaining space with a 300px minimum height. Keep the existing
content-based column sizing and capped flexible Scenario column.

Why: `domLayout: autoHeight` expanded the grid to every row, so the document
scrolled and carried the column headers out of view on large playlists. A
bounded grid keeps the headers visible while the user sorts and scans scenarios
deep in the playlist, and restores row virtualization.

Consequences: Short playlists show empty grid body below their final row instead
of collapsing the grid. Very short windows may still scroll the page to preserve
the 300px usable minimum. The layout tracks AppShell header and padding variables
instead of duplicating their pixel values.
