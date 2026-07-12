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
- **R3 — Pending vs. N/A.** Phase-1 cells missing a value render a dimmed
  ellipsis placeholder (semantic CSS class, visually distinct from a final
  "N/A"). Rows whose three network columns are all present render normally
  and may update silently in place. After phase 2 resolves a scenario,
  placeholders become values or "N/A" — "…" always means "still being
  decided", "N/A" always means "decided: unavailable".
- **R4 — Progress counter.** The existing status Text
  (`playlist-scenarios-status`) shows
  `Updating positions from KovaaK's… done/total` (total = all scenarios,
  per R2) while phase 2 runs, and clears on completion. All-fresh playlists
  complete within roughly one interval tick; a brief counter flash is
  accepted.
- **R5 — Transport: registry + interval drain.** A module-level registry in
  the service layer, guarded by a lock:
  `{generation_id: {pending row updates, done_count, total, complete,
  cancel Event}}`. A `dcc.Interval` (~1 s) drains pending updates and applies
  them via the grid's `rowTransaction` (update-only). This is the established
  in-repo pattern (watchdog `message_queue` → Home interval drain);
  single-user app, so module-level state is acceptable.
- **R6 — Row identity = playlist position.** `getRowId` returns the
  stringified `playlist_order` index, not the scenario name — playlists may
  repeat a scenario.
- **R7 — Generation tokens + cancellation.** Each page open mints a token,
  stored in the layout alongside the playlist code; the drain callback sends
  it, and registry reads are token-checked. Starting a new load sets the
  previous generation's cancel Event; workers check it before each scenario
  fetch, so an abandoned load stops within one in-flight scenario per worker.
  Completed or cancelled generations are evicted.
- **R8 — Interval lifecycle.** The drain interval renders `disabled=True`;
  the phase-1 callback enables it when phase 2 starts, and the drain callback
  disables it when the registry reports complete. The drain callback is
  read-only and idempotent: an unknown or missing token returns `no_update`
  everywhere, which also makes it safe against DashProxy's known
  initial-load duplicate fire.
- **R9 — Failure display.** A scenario whose refresh fails keeps existing
  UNKNOWN → "N/A" semantics in its row. If any scenario failed, one summary
  notification ("Couldn't update K of N positions from KovaaK's") goes
  through the existing notification path when the fill completes — never
  per-scenario spam.
- **R10 — Drop `dcc.Loading` on this grid.** Phase 1 is near-instant, and
  interval-driven prop updates would flicker the overlay every tick. The
  pending placeholders (R3) plus the counter (R4) replace the spinner as the
  loading affordance.
- **R11 — Phase-2 execution.** The phase-1 callback starts one daemon thread
  (like the rank-freshness timers) just before returning; that thread runs
  the same 4-worker pool (`PLAYLIST_RANK_MAX_WORKERS`) used today, writing
  results into the registry instead of a return list.
- **R12 — No persistence.** The registry is in-memory only. A page reload or
  app restart simply starts a new generation; phase-2 results already written
  to the normal disk caches are free progress for the next open.

## Edge cases (deliberate)

- Reopen the same playlist (or another) mid-fill → new generation; the old
  one is cancelled per R7.
- Two browser tabs → single-user assumption: the registry may hold two live
  generations; each tab's drain callback only touches its own token, and
  unknown tokens no-op.
- Sorting mid-fill: AG Grid transaction updates under an active sort may
  reposition rows as values land. Accepted for v1 — verify actual
  `rowTransaction` re-sort behavior against dash-ag-grid docs during build;
  revisit only if rows visibly jump under the cursor.
- Scenario-name clicks navigate from phase 1 onward (the name column is
  local; the existing `cellClicked` callback is unchanged).

## Out of scope

- Home page rank display and the Playlists overview page.
- Staleness indicators (e.g. `fetched_at` tooltips) on served cached values.
- Retry/backoff tuning and per-load network deadlines.

## Dependencies / sequencing

Build after the two speed-fix PRs merge (kickoff prompts
`ignore/prompts/hoist-total-play-hydration-prompt.md` and
`ignore/prompts/stale-rank-fallback-prompt.md`): the hydration hoist removes
the per-scenario total-play multiplier phase 2 would otherwise inherit, and
the stale-rank fallback reduces how often phase 2 lands on "N/A".

Rejected alternatives: a chained second callback returning all rows at once
(no counter, results still land as one lump after minutes); Dash native
background callbacks (require a diskcache/celery manager — heavier than the
in-repo interval-drain pattern for a single-user local app).
