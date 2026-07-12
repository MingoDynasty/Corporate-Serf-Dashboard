# Proposal: progressive fill for the playlist scenarios page

Status: Proposed

## Problem

Opening `/playlists/<code>` blocks a single callback
(`load_playlist_scenario_rows`) on every scenario's KovaaK's lookups before
the grid shows anything — minutes on a cold cache or flaky API, behind a bare
`dcc.Loading` spinner. Yet six of the nine columns are built entirely from
local data, and the three network columns (Position / Total Players /
Percentile) have long-TTL disk caches. The page should paint instantly from
what it knows and stream in what it doesn't, with visible progress.

## Decisions (register)

- **R1 — Two-phase load.** Phase 1: the row-load callback builds all rows
  with cache-only rank reads (`get_scenario_rank_info(allow_network=False)`,
  the overview page's path) plus local stats, and returns immediately.
  Phase 2: a server-side daemon thread re-runs the normal network path and
  streams per-row updates to the grid.
- **R2 — Phase 2 covers all scenarios through the existing network path.**
  It runs `get_scenario_rank_info(allow_network=True)` for every scenario:
  cache-fresh scenarios complete in milliseconds without network, so
  freshness semantics stay byte-identical to today's blocking load
  (TTL-expired entries refresh, fresh ones don't). No bespoke "which rows
  are stale" logic to maintain.
- **R3 — Pending vs. N/A.** A network cell (Position / Total Players /
  Percentile) renders a dimmed ellipsis placeholder (semantic CSS class,
  visually distinct from a final "N/A") when its value is None and the row
  has not yet been resolved by the current generation; once resolved,
  placeholders become values or "N/A". "…" always means "still being
  decided", "N/A" always means "decided: unavailable". The rule is per-cell
  and status-independent: e.g. a cached-UNRANKED row shows "Unranked" in
  Position immediately while Percentile shows "…" until resolution (phase 2
  may flip UNRANKED to RANKED). Rows whose three network cells are all
  populated render normally and may update silently in place.
- **R4 — Progress counter.** The existing status Text
  (`playlist-scenarios-status`) shows
  `Updating positions from KovaaK's… done/total` (total = all scenarios,
  per R2) while phase 2 runs. On a clean completion it clears; on a degraded
  completion (any UNKNOWN or stale-served rows, per R9) it settles to a
  compact persistent summary — e.g.
  `2 of 34 positions unavailable · 30 from cache — KovaaK's unreachable` —
  until the next fill. The R9 toast is transient; a degraded page must not
  look identical to a fresh one ten seconds later. All-fresh playlists
  complete within roughly one interval tick; a brief counter flash is
  accepted.
- **R5 — Transport: registry + interval drain.** A module-level registry in
  the service layer, guarded by a lock:
  `{generation_id: {pending row updates, done_count, unknown_count,
  stale_count, total, complete, cancel Event}}`. A `dcc.Interval` (~1 s)
  drains pending updates and applies them via the grid's `rowTransaction`
  (update-only). Each pending update is a **complete row dict** rebuilt via
  `format_playlist_scenario_rank_row` (workers re-read local stats per
  scenario, as today's `as_completed` loop does) — AG Grid update
  transactions swap row data wholesale, they never merge, so partial
  rank-field patches would blank the local columns. The worker classifies
  each scenario's outcome (fresh / served-stale / unknown) from the
  `ScenarioRankInfo` **before** flattening it into the row dict — the
  formatter discards rank metadata — and bumps the generation's counters
  under the lock; the drain reads counters, never re-deriving outcomes from
  row content. This registry+drain shape is the established in-repo pattern
  (watchdog `message_queue` → Home interval drain); single-user app, so
  module-level state is acceptable.
- **R6 — Row identity = generation + position.** `getRowId` returns
  `generation_token + ':' + playlist_order` (phase 1 stamps both into every
  row; playlist_order exists because playlists may repeat a scenario). The
  generation namespace is what makes any stale in-flight transaction inert —
  from a previously open playlist *or from a cancelled fill of the same
  playlist after a quick reopen*, where playlist-scoped ids would collide:
  AG Grid matches update items by row id, replaces matched rows wholesale,
  and skips ids not present, and no other generation's ids can exist in the
  current grid. Registry-side token checks (R7) cannot revoke a drain
  response already in flight over HTTP; row-id namespacing is what closes
  that window. The playlist code is deliberately not part of the id — a
  generation token is minted per page open, so it already uniquely implies
  the playlist.
- **R7 — Generation tokens, cancellation, tombstones.** Each page open mints
  a token held in its own `dcc.Store` (`playlist-scenarios-generation` —
  separate from `playlist-scenarios-code`, whose bare-string contract other
  callbacks rely on); the drain callback sends it, and registry reads AND
  writes are token-checked (a straggling worker of a cancelled generation
  cannot resurrect an evicted key). Starting a new load cancels **all**
  other live generations (single-user app; there is no tab identity
  server-side); workers check the cancel Event before each scenario fetch,
  so an abandoned load stops within one in-flight scenario per worker.
  Terminal generations (complete or cancelled) remain in the registry as
  tombstones — final counts plus the terminal flag — so the owning drain can
  observe the end state, perform a final drain, and settle its status line;
  tombstones are evicted by the next page-load sweep.
- **R8 — Interval lifecycle: enable-only.** The drain interval renders
  `disabled=True`; the phase-1 callback enables it when it starts phase 2,
  and it stays enabled for the life of the page instance — nothing ever sets
  `disabled=True` back. After the drain observes a terminal tombstone,
  subsequent ticks are `no_update` no-ops (one dict lookup per second, local
  single-user app). Never disabling eliminates by construction the
  cross-navigation race where a stale `disabled=True` response lands after
  the next page's phase 1 enabled the interval, which would otherwise stall
  that fill permanently. The drain callback is idempotent, mutates the
  registry only by draining its own token's pending queue, and returns
  `no_update` everywhere on an unknown or missing token — which also makes
  it safe against DashProxy's known spurious initial-load fire.
- **R9 — Failure display: aggregated three-tier summary.** A scenario whose
  refresh fails keeps existing UNKNOWN → "N/A" semantics in its row; there
  is never per-scenario toast spam. On completion the **drain callback** —
  not the phase-2 thread, which has no callback context (`set_props`-based
  `dash_logger` raises `LookupError` from a plain thread) — emits at most
  one summary via the notification container's `sendNotifications` output,
  with a per-fill unique notification id (dmc silently swallows a "show"
  with a duplicate id). Tiers mirror the PR #112 three-tier toast model,
  aggregated: any scenario ended UNKNOWN → red
  "Couldn't update K of N positions" (K counts only UNKNOWN rows), with
  "; M more served from cache" appended whenever stale-serves also
  occurred; otherwise any scenario served stale → yellow
  "M of N positions served from cache — KovaaK's was unreachable";
  all fresh → no toast (phase 2 is automatic, and green is reserved for
  manual refreshes per the #112 model). K and M come from the R5 generation
  counters, and stale-serve classification is **structural, not textual**:
  the #112 fallback path gains a transient `served_stale` marker on the
  returned `ScenarioRankInfo` (never persisted — the fallback path performs
  no cache writes, and the field defaults to None so `exclude_none` drops it
  from every other save). Inferring staleness from `warning_message` is
  forbidden: that field is overloaded by the Steam-ID mismatch warning, and
  #112 appends staleness text after any mismatch text, so presence-sniffing
  would misreport a mismatch as an outage. The red tier must never mask
  the stale count: once the background percentile warmup is ambient,
  UNKNOWN requires an empty cache (rare) while an outage presents almost
  entirely as stale-serves — M, in both tiers and in the settled R4 status
  line, IS the outage signal in the warmed steady state.
- **R10 — Drop `dcc.Loading` on this grid.** Phase 1 is near-instant, and
  interval-driven prop updates would flicker the overlay every tick. The
  pending placeholders (R3) plus the counter (R4) replace the spinner as the
  loading affordance.
- **R11 — Phase-2 execution.** The phase-1 callback registers the generation
  and starts one daemon thread (like the rank-freshness timers) just before
  returning — registering after the rows are built, so the R8 unknown-token
  guard cannot race a drain against a not-yet-rendered grid. The thread
  keeps the post-PR-#113 structure: hydrate the leaderboard-id mapping once
  up front, then run the same 4-worker pool (`PLAYLIST_RANK_MAX_WORKERS`)
  with per-scenario `allow_hydration=False` lookups, writing results into
  the registry instead of a return list.
- **R12 — No persistence.** The registry is in-memory only. A page reload or
  app restart simply starts a new generation; phase-2 results already written
  to the normal disk caches are free progress for the next open.
- **R13 — Interactive-activity signal (coordination).** Phase-2 workers bump
  the shared module-level "interactive activity" signal in `api_service` —
  two timestamps: last interactive fetch started, last succeeded — so the
  background percentile warmup worker (see Coordination below) yields to
  user-facing bursts and wakes early from outage backoff. Whichever PR lands
  first defines the ~5-line primitive; the other adopts it.

## Edge cases (deliberate)

- Reopen the same playlist (or another) mid-fill → new generation; all
  previous live generations are cancelled per R7.
- Two browser tabs → single-user assumption: the second open cancels the
  first tab's fill; the first tab's drain observes the cancelled tombstone,
  settles, and idles. Its already-rendered rows stay visible.
- Sorting mid-fill: AG Grid re-applies the active sort to updated rows
  (doc-verified), so rows may reposition as values land. Accepted for v1;
  `suppressModelUpdateAfterUpdateTransaction` exists as an opt-out if it
  ever bites.
- Column autosize measures phase-1 placeholder content, so filled-in values
  keep placeholder-era widths. Accepted for v1 — headers plus the network
  columns' minWidths absorb it.
- Scenario-name clicks navigate from phase 1 onward (the name column is
  local; the existing `cellClicked` callback is unchanged).
- An in-flight drain response that lands after a reopen can still write a
  stale status line or toast — row ids (R6) guard only the grid. Accepted:
  the status text self-heals on the next live tick (≤1 s), and the toast
  carries a superseded generation's summary at worst once, immediately
  followed by the live fill's own lifecycle.

## Out of scope

- Home page rank display and the Playlists overview page (the overview is
  covered by the background-percentile-warmup proposal — see Coordination).
- Staleness indicators (e.g. `fetched_at` tooltips) on served cached values.
- Retry/backoff tuning and per-load network deadlines.

## Coordination

`background_percentile_warmup_proposal.md` (drafted in parallel on branch
claude/playlist-percentile-initial-load-a3bd99; named by filename, not
linked, until both merge) owns the ambient single-worker cache warmer and
the overview page; this proposal owns the drill-in page. They compose
through the disk cache with no new shared state: phase 2 warming a playlist
lets the warmer's dequeue-time freshness check skip those scenarios, and a
warmed playlist makes phase 2 near-instant (R2 relies on cache-fresh
completing in milliseconds). The single code-level integration point is the
R13 activity signal. Deliberate non-unifications, documented on both sides:
the overview does not reuse this proposal's registry/rowTransaction
transport (different data planes); status-line counters differ (done/total
here is a static per-generation total, remaining-only there is a dynamic
queue); the warmer's kill switch never disables phase 2 (user-initiated
traffic).

## Dependencies / sequencing

None remaining: the two speed-fix PRs this design assumed have merged —
PR #113 (total-play hydration hoisted out of the per-scenario path, which
phase 2 preserves per R11) and PR #112 (stale-rank fallback with the
three-tier toast model R9 mirrors).

Rejected alternatives: a chained second callback returning all rows at once
(no counter, results still land as one lump after minutes); Dash native
background callbacks (require a diskcache/celery manager — heavier than the
in-repo interval-drain pattern for a single-user local app).
