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
  streams per-row updates to the grid. One phase-2 run for one page open is
  a **fill**; the R7 generation token is a fill's identity, and "the fill"
  below always means the current generation's run.
- **R2 — Phase 2 covers all scenarios through the existing network path.**
  It runs `get_scenario_rank_info(allow_network=True)` for every scenario:
  cache-fresh scenarios complete in milliseconds without network, so
  freshness semantics stay byte-identical to today's blocking load
  (TTL-expired entries refresh, fresh ones don't). No bespoke "which rows
  are stale" logic to maintain.
- **R3 — Pending vs. N/A.** A network cell (Position / Total Players /
  Percentile) renders a dimmed **animated** ellipsis placeholder — cycling
  `.` → `..` → `…` via a pure-CSS `steps()` keyframe on the pending cell's
  semantic class (a `::after` `content` animation in
  `assets/stylesheet.css`; the base rule's static `…` is the automatic
  fallback in browsers that don't animate `content`), so pending reads as
  activity rather than truncation, with no custom cellRenderer. Pending is
  an **explicit per-cell flag** (`rank_pending`, `total_pending`,
  `percentile_pending`) stamped by phase 1 — never inferred from value
  nullity: the grid columns bind the `*_sort` fields, and `rank_sort` is
  legitimately None on a *resolved* UNRANKED row (display "Unranked"), so a
  `params.value == null` predicate cannot tell pending from resolved-N/A.
  A flagged cell's valueFormatter returns an empty string (suppressing the
  "N/A" display text) and its cellClass adds the pending class whose
  `::after` draws the dots; every row emitted by phase 2 or by cancellation
  finalization (R7) carries all three flags cleared. "…" always means
  "still being decided", "N/A" always means "decided: unavailable". The
  rule is per-cell and status-independent: e.g. a cached-UNRANKED row shows
  "Unranked" in Position immediately while Percentile shows "…" until
  resolution (phase 2 may flip UNRANKED to RANKED). Rows with no flagged
  cells render normally and may update silently in place.
- **R4 — Progress counter.** The existing status Text
  (`playlist-scenarios-status`) shows
  `Updating positions from KovaaK's… done/total` (total = all scenarios,
  per R2) while phase 2 runs. On a clean completion it clears; on a degraded
  completion (any UNKNOWN or stale-served rows, per R9) it settles to a
  compact persistent summary — e.g.
  `2 of 34 positions unavailable · 30 from cache — KovaaK's unreachable` —
  until the next fill; a cancelled fill settles to the interrupted variant,
  e.g. `Update interrupted · 12 of 34 refreshed` (R7 finalization). The R9
  toast is transient; a degraded page must not
  look identical to a fresh one ten seconds later. All-fresh playlists
  complete within roughly one interval tick; a brief counter flash is
  accepted.
- **R5 — Transport: registry + interval drain.** A module-level registry in
  the service layer, guarded by a lock:
  `{generation_id: {pending row updates, done_count, unknown_count,
  stale_count, total, playlist_code, unresolved indices,
  terminal flag (complete | cancelled), consumed flag, cancel Event}}` —
  the terminal-state fields' lifecycle is defined in R7. A `dcc.Interval`
  (~1 s)
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
  tombstones — final counters, the terminal flag, the playlist code, the
  set of unresolved row indices, and a **consumed flag** — so the owning
  drain can observe the end state through R8's terminal protocol.
  Retention is bounded, not immediate: all terminal tombstones — consumed
  or not — live in one retention set capped at a small fixed size, and the
  page-load sweep evicts only beyond the cap, consumed before unconsumed,
  oldest first within each class. Eviction on any faster trigger destroys
  state some tab still needs: an *unconsumed* tombstone lost in the
  sub-second window between cancellation and the owning tab's next tick
  (two quick page opens suffice) resurrects the permanent-pending bug, and
  a *consumed* one lost to another tab's sweep severs R8's reassertion
  healing while a superseded generation's response can still straggle in.
  Consumption shrinks a tombstone to a stub — final counters plus flags;
  the unresolved set and pending queue are dropped — so retained consumed
  tombstones cost almost nothing.
  A cancelled fill must not strand animated pending cells on a
  still-visible grid (the two-tab case): the consuming tick (R8)
  **finalizes** — rebuilds the tombstone's unresolved rows cache-only
  (`allow_network=False`, pending flags cleared; the cache may meanwhile
  hold the cancelled workers' banked fetches, so finalized cells can even
  improve), applies them as that tick's transaction, and settles the
  status to the interrupted variant (R4). Same-tab navigation destroys the
  old page — no drain ever ticks, its unconsumed tombstone ages out via
  the cap, and finalization costs nothing in the common case.
- **R8 — Interval lifecycle: enable-only.** The drain interval renders
  `disabled=True`; the phase-1 callback enables it when it starts phase 2,
  and it stays enabled for the life of the page instance — nothing ever sets
  `disabled=True` back. Terminal handling is a **two-stage protocol** keyed
  on the tombstone's consumed flag, checked and set atomically under the
  registry lock. The **consuming tick** — the first tick to observe
  terminality — flips the flag and performs the one-shots exactly once:
  drains any remaining pending updates, applies the R7 finalization
  transaction (cancelled fills), emits the R9 summary toast (completed
  fills), and writes the settled status. Every **post-consumption tick**
  only reasserts the settled status line — re-derived from the tombstone's
  final counters: cleared for a clean fill, the R4 degraded or interrupted
  summary otherwise — while row transactions and notifications stay
  `no_update`; without the flag, every terminal tick would repeat the
  finalization rebuild and the toast emission, and no state would say the
  work was done. Reassertion is a cheap constant write (local single-user
  app), and it is what heals a stale status written by a superseded
  generation's in-flight response *after* the current fill has settled —
  post-terminal `no_update` ticks would leave that stale text standing until
  the next page load. The healing exists only while the tombstone does —
  which is why R7 retains consumed tombstones in the bounded set instead of
  evicting them on the next sweep. Never disabling eliminates by
  construction the
  cross-navigation race where a stale `disabled=True` response lands after
  the next page's phase 1 enabled the interval, which would otherwise stall
  that fill permanently. The drain callback is idempotent, mutates the
  registry only under its own token — draining the pending queue and
  atomically flipping the consumed flag — and returns `no_update`
  everywhere on an unknown or missing token, which also makes it safe
  against DashProxy's known spurious initial-load fire.
- **R9 — Failure display: aggregated three-tier summary.** A scenario whose
  refresh fails keeps existing UNKNOWN → "N/A" semantics in its row; there
  is never per-scenario toast spam. On completion the **drain callback** —
  not the phase-2 thread: since PR #115, `dash_logger` records from plain
  threads are queued and flushed only by the Home page's interval, so a
  fill summary logged from the worker would surface on the wrong page,
  whenever Home is next visited — emits the summary exactly once, on R8's
  consuming tick, via the notification container's `sendNotifications`
  output, with a per-fill unique notification id. (dmc's silent
  duplicate-id suppression would additionally absorb an accidental
  re-send — defense in depth, not the mechanism; the consumed flag is the
  mechanism.) Tiers mirror the PR #112 three-tier toast model,
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
- **R13 — Interactive-activity signal (coordination).** A shared
  module-level signal in `api_service`, two timestamps with deliberately
  different semantics. *Last interactive activity* is bumped per
  interactive lookup — cache hits included, since it only means "the user
  is active, stay out of the way" — and drives the warmup worker's
  yielding. *Last network success* is bumped only inside the real HTTP
  request-success path and is what wakes the warmer from outage backoff.
  R2 makes the distinction load-bearing: a warm-cache page open performs
  zero requests, and letting its cache hits signal recovery would wake the
  warmer without any evidence KovaaK's recovered. Whichever PR lands first
  defines the primitive; the other adopts it.

## Edge cases (deliberate)

- Reopen the same playlist (or another) mid-fill → new generation; all
  previous live generations are cancelled per R7.
- Two browser tabs → single-user assumption: the second open cancels the
  first tab's fill; the first tab's drain observes the cancelled tombstone,
  finalizes its unresolved rows, settles to the interrupted status, and
  idles (R7). Its rows stay visible with no cell left animating.
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
  stale status line or toast — row ids (R6) guard only the grid. The status
  line self-heals within one tick in *both* fill states: live ticks
  overwrite it, and post-terminal ticks reassert the settled text (R8). The
  toast residual is accepted: a superseded generation's summary may appear
  at most once and autocloses; the status line is the durable, authoritative
  surface. (Generation-gating the UI outputs client-side was considered and
  rejected: a new store + clientside compare-and-apply layer to close a
  thin local race that reassertion already bounds to one tick.)

## Out of scope

- Home page rank display and the Playlists overview page (the overview is
  covered by the background-percentile-warmup proposal — see Coordination).
- Staleness indicators (e.g. `fetched_at` tooltips) on served cached values.
- Retry/backoff tuning and per-load network deadlines.
- A `prefers-reduced-motion` override for the R3 animation — deliberately
  omitted: single-user app whose one user runs without that preference; a
  three-line CSS addition if the audience ever grows.

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
