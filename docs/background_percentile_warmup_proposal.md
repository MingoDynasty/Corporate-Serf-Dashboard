# Proposal: background percentile warmup for the playlists overview

Status: Proposed

## Problem

On first app load (or any cold cache) the playlists overview at `/playlists`
shows almost no percentile data: its rows are deliberately cache-only
(`allow_network=False`), and the rank cache only warms when the user drills
into individual playlists. Until then the median/lowest percentile aggregates
are computed over a biased sample — whichever playlists happen to have been
drilled into — which skews them in confusing directions despite the
`· cached/total` coverage suffix.

The fix is a background warmer that fills the rank + totals caches for exactly
the scenarios the overview can display, slowly and politely, without blocking
any user-facing path.

## Sizing (measured 2026-07-12)

- One scenario costs two API calls: rank (`/leaderboard/scores/global` with
  `usernameSearch`) measured at 2.3–9.2 s (avg ~4.8 s, n=4), and leaderboard
  total (~0.4–0.6 s, one 4 s outlier). ~6–8 s per scenario; the API's own
  latency does most of the throttling.
- Reference user: 865 unique scenarios played locally; 126 of them in the
  current visible-playlist set (the actual queue); 638 if every bundled Evxl
  benchmark (2,629 unique scenarios) were unhidden.
- Cold warm of the default visible set ≈ 15 min. Pathological
  all-benchmarks-visible ≈ 75 min. Steady-state restart top-up (168 h TTL,
  daily restart) ≈ 2 min/day.

## Decisions (register)

- **R1 — One background worker.** A single daemon thread, started after CSV
  ingest completes (it needs the played set), processes a queue of scenario
  names sequentially with a small politeness gap (~2 s) between network items.
  No parallelism: sequential fetches at ~6–8 s/scenario are inherently gentle
  (<0.4 req/s sustained).
- **R2 — Queue scope = played ∩ visible.** Only scenarios that appear in a
  visible playlist and have local runs are enqueued: nothing else can
  contribute a percentile to the overview (the aggregator skips unplayed
  scenarios; hidden playlists aren't rendered). The Home page's on-demand
  fetch covers everything outside this set. This bounds the worst case at
  "played and visible", not the user's full history.
- **R3 — Playlist-completion ordering.** The startup queue is grouped by
  playlist (most recently played first); within a playlist, scenarios with no
  displayable percentile come first, then by last-played recency. Completing
  one playlist at a time flips overview rows from "partial" to "trustworthy"
  one by one, instead of leaving every row partially covered for the whole
  warm.
- **R4 — "Needs work" = rank or total missing/stale.** A scenario is skipped
  at dequeue only if its rank cache is TTL-fresh AND its totals cache exists.
  Percentile needs both files; a rank-only check would leave permanent N/A
  holes wherever a totals fetch once failed.
- **R5 — Dequeue-time freshness check is the universal dedup.** Every pop
  re-checks R4 and skips satisfied items in microseconds (file stats, no
  network). All duplication — unhide spam, races with interactive fetches,
  tail requeues — resolves here. The queue needs no uniqueness invariant, no
  promotion, no scanning: a dumb deque.
- **R6 — Unhide and import prepend, unconditionally.** When the user unhides
  a playlist or imports one (imports are auto-visible), its played scenarios
  are batch-prepended (most recent user action first). No in-queue dedup (R5
  makes duplicates free) and no removal when a playlist is hidden or deleted
  (worst case: one playlist of fetches whose results are cached for later).
  Visibility changes are the primary onboarding flow — first-run users
  immediately unhide the benchmarks they care about — so this hook is core.
- **R7 — Interactive traffic bypasses the queue and preempts the worker.**
  Drill-in loads (see coordination below) and the Home refresh button fetch
  directly, as today. A module-level "interactive activity" signal
  (last-started / last-succeeded timestamps in `api_service`) is bumped by
  those paths; the worker sleeps while activity is recent, so user-facing
  bursts get full API bandwidth. Existing monotonic rank writes under
  `_rank_save_lock` make concurrent writers safe; the worst race is one
  duplicate in-flight request.
- **R8 — Single TTL.** v1 keeps `scenario_rank_cache_ttl_hours` (168 h) for
  both interactive and background freshness. A separate longer background TTL
  is a real lever (percentile drift is glacial) but only pays once the visible
  set grows several-fold; it's a one-line config addition when needed.
- **R9 — Transient failures: tail requeue + escalating global backoff.**
  Timeouts, connection errors, 5xx, and post-retry 429s send the item to the
  tail and sleep the worker on an escalating schedule (30 s → 2 m → 5 m →
  15 m → 30 m cap), reset on any success. During an outage the worker
  converges to ~1 probe per 30 min, which doubles as the recovery detector.
  Tail (not head) requeue keeps one flaky scenario from blocking the queue
  behind its own backoffs. Per-item cap: 3 transient attempts per session,
  then drop (the next restart retries). A success on the interactive path
  also wakes the worker early (R7 signal).
- **R10 — Permanent failures skip immediately.** Unresolvable leaderboard IDs
  and validation failures are logged and dropped without retries; a restart
  re-probes each once (accepted cost; a negative-resolution cache is a future
  lever, not v1).
- **R11 — Fatal failures stop the queue.** `UnknownKovaaksUserError` means
  every remaining item would fail identically: stop the worker and emit one
  `dash_logger.error`, mirroring the rank-freshness Timer chain.
- **R12 — Status line: remaining-only.** The overview page shows
  "Updating percentile data: N remaining (~ETA)" where N counts unique names
  in the queue (spam-proof) and ETA = N × recent average pace; during outage
  backoff it shows a paused note with the retry time. No done/total: the
  denominator is dynamic (unhides grow it, dedup shrinks it), so a ratio
  would visibly run backward. Transient failures never toast — a deliberate
  deviation from the "background failures notify via `dash_logger.error`"
  convention, because an outage is ambient state, not an event; only R11
  notifies.
- **R13 — Live overview refresh while warming.** A `dcc.Interval` on the
  overview page, enabled only while the queue is non-empty, re-runs the
  normal cache-only row build each tick so rows fill in as the user watches.
  Full rebuild from disk cache — deliberately NOT the progressive-fill
  registry/rowTransaction transport, which streams in-memory generation
  state; the overview's data plane is the disk cache and its build is
  already cheap.
- **R14 — Layering: the worker sits at the Timer-chain layer.** It calls
  `resolve_leaderboard_id` / `fetch_scenario_rank` / totals directly and
  classifies exceptions itself (the `_run_attempt` precedent), because the UI
  entry point deliberately flattens failures into UNKNOWN. Partial success
  composes: if the rank saved but the totals call failed, the retry only
  re-pays the cheap totals call.
- **R15 — Kill switch.** `percentile_warmup_enabled` (config.toml, default
  true) disables the warmer only — never interactive fetches.
- **R16 — Testability.** The worker is a pure "process one item" step
  function with injected pacing/sleep, driven by a thin thread loop — the
  split is the better production design, not a test-only seam.
- **R17 — Logging.** DEBUG per item, INFO per playlist batch and per state
  change (backoff entered/exited, fatal stop), one INFO summary at
  completion.

## Coordination with `playlist_progressive_fill_proposal.md`

That proposal (drafted in parallel) owns the drill-in page
(`/playlists/<code>`): two-phase load, pending placeholders, registry +
interval drain, per-generation progress. This proposal owns the ambient queue
and the overview page. They compose through the disk cache with no new shared
state: progressive fill's phase 2 warms a playlist → R5 skips those
scenarios; the warmer's results make phase 2 near-instant (its R2 relies on
cache-fresh completing in milliseconds).

Contract points:

1. The R7 activity signal is the one integration: progressive-fill phase-2
   workers (its R11) and the Home refresh bump it; whichever PR lands first
   defines the ~5-line primitive.
2. The overview deliberately does not reuse the progressive-fill registry
   transport (R13 here); different data planes.
3. Status lines share a phrase family but deliberately different counters:
   done/total there (static per-generation total), remaining-only here
   (dynamic queue). Not a consistency bug.
4. Notification conventions align (no per-scenario spam). A misconfigured
   username can produce both its fill-summary toast and R11's fatal toast;
   rare and self-explaining, accepted.
5. R15's kill switch never disables progressive fill (user-initiated
   traffic).
6. Its two speed-fix dependencies already merged (PR #113 total-play
   hydration hoist, PR #112 stale-rank fallback), so neither proposal has a
   sequencing constraint left; the warmer additionally hydrates the
   leaderboard-id mapping once up front on its own.

(Referenced by filename, not linked: the two proposals live on separate
branches until merged, and `tests/test_docs.py` fails dangling relative
links.)

## Edge cases (deliberate)

- Hide/unhide spam: duplicates are free (R5) and invisible in the counter
  (R12's unique-name count). A head-batch-comparison guard was considered and
  rejected: it stops firing the moment the worker consumes one item of the
  batch (timing-dependent behavior) while defending against a cost that is
  already zero.
- Unhide racing an in-flight fetch: the single worker serializes; the
  duplicate is freshness-skipped after the in-flight item saves. If the
  in-flight fetch failed, the duplicate acts as a free retry.
- Scenario played for the first time mid-session: the watchdog's new-scenario
  path already schedules the Timer-chain refresh (`file_watchdog.py`), so the
  queue never needs mid-session additions from gameplay.
- A playlist repeats a scenario (progressive fill's R6): the second
  occurrence freshness-skips.
- Cached UNRANKED: fresh → skipped; correct (the user isn't on that board; a
  new local score routes through the Timer chain).
- Debug mode: `app.py` runs `use_reloader=False`, so the worker starts once,
  like the watchdog observer.
- Shutdown mid-warm: the daemon thread dies; atomic cache writes can't tear;
  the next startup rebuilds the queue from staleness. No persisted queue
  state.
- Empty stats directory (brand-new user): the queue is empty; nothing to warm
  and nothing to display anyway. "Cleared local stats but has KovaaK's
  history" is explicitly unsupported.

## Out of scope

- Drill-in page UX (progressive fill proposal).
- Home page rank display.
- Second/background TTL tier (R8) and negative-resolution cache (R10) —
  documented levers, not v1.
- Queue persistence across restarts.

## Rejected alternatives

- Bulk-seeding ranks from `/user/scenario/total-play`: halves the calls, but
  the endpoint lags the leaderboard (decision log: metadata/upsert only) and
  lacks per-leaderboard totals, so per-scenario calls remain; not worth a
  provisional trust tier in the rank cache.
- A mutable priority queue with runtime priorities: user actions already
  bypass the queue (R7); prepend + dequeue-time freshness (R5/R6) delivers
  the same semantics with a dumb deque.
- Warming the user's full played history: no UI surface consumes it (R2).
