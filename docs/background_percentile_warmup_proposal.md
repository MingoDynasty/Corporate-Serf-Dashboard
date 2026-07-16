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
  (<0.4 req/s sustained). The worker lives for the app's lifetime: when the
  queue and in-flight work drain, it blocks on a condition variable, and the
  R6 enqueue hooks signal that condition — an unhide hours after the queue
  emptied wakes the same worker; nothing is restarted.
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
- **R4 — Completion = fresh UNRANKED, or fresh RANKED plus fresh total.** A
  scenario is skipped at dequeue if its rank cache is TTL-fresh UNRANKED, or
  TTL-fresh RANKED with a TTL-fresh totals cache
  (`leaderboard_total_cache_ttl_hours`). Percentile needs rank and total
  together, but only for RANKED entries — the overview derives percentiles
  exclusively from RANKED cache entries, so totals buy nothing for a fresh
  UNRANKED. (The drill-in page does show totals on unranked rows; that is
  the shipped fill's on-demand territory.) For RANKED entries, a rank-only
  check would leave permanent N/A holes wherever a totals fetch once failed,
  and because the overview's cache-only read path serves totals regardless
  of age, a stale totals file would otherwise never be repaired. The
  asymmetry is cheap: a fresh-RANKED/stale-totals item re-pays only the
  ~0.5 s totals call (R14).
- **R5 — The dequeue-time check is the universal dedup.** Every pop consults
  two things: the R4 cache predicate, and a per-session outcome map keyed by
  scenario name holding transient attempt counts and terminal outcomes
  (permanent failure, read-timeout drop, cap exhaustion). Satisfied or
  terminal names skip in microseconds (file stats plus a dict lookup, no
  network), so duplication from any source — unhide spam, races with
  interactive fetches, tail requeues — resolves here, and failure duplicates
  can neither re-fire requests nor evade the R9 cap. The queue itself needs
  no uniqueness invariant, no promotion, no scanning: a dumb deque.
- **R6 — Unhide and import prepend, unconditionally.** When the user unhides
  a playlist or imports one (imports are auto-visible), its played scenarios
  are batch-prepended (most recent user action first). No in-queue dedup (R5
  makes duplicates free) and no removal when a playlist is hidden or deleted
  (worst case: one playlist of fetches whose results are cached for later).
  Visibility changes are the primary onboarding flow — first-run users
  immediately unhide the benchmarks they care about — so this hook is core.
- **R7 — Interactive traffic bypasses the queue and preempts the worker.**
  Drill-in loads (see coordination below) and the Home refresh button fetch
  directly, as today. The module-level signal in `api_service` (shipped with
  PR #127: `record_interactive_activity()` / `get_api_activity_timestamps()`;
  the worker consumes it as-is) carries two timestamps with deliberately
  split semantics:
  - *last interactive activity* — bumped per interactive lookup, cache hits
    included (it means only "the user is active, stay out of the way");
    drives the worker's yielding.
  - *last network success* — bumped only on a real HTTP success in the
    shared GET helper, never on cache-served returns; drives the
    outage-backoff wake (R9). A cache hit is not evidence KovaaK's
    recovered: interactive lookups over a warm cache make zero HTTP
    requests.

  Existing monotonic rank writes under `_rank_save_lock` make concurrent
  writers safe; the worst race is one duplicate in-flight request.
- **R8 — Single TTL.** v1 keeps `scenario_rank_cache_ttl_hours` (168 h) for
  both interactive and background freshness. A separate longer background TTL
  is a real lever (percentile drift is glacial) but only pays once the visible
  set grows several-fold; it's a one-line config addition when needed.
- **R9 — Transient failures: tail requeue + escalating global backoff.**
  Connection errors (including connect timeouts), 5xx, and post-retry 429s
  send the item to the tail and sleep the worker on an escalating schedule
  (30 s → 2 m → 5 m → 15 m → 30 m cap), reset on any success. Read timeouts
  are the deliberate exception, honoring the 2026-07-13 no-ReadTimeout-retry
  decision: the server may still be processing that exact query, so the item
  is marked terminal in the R5 outcome map (the next restart re-probes it) —
  but the failure still trips the same global backoff, because a read timeout is the
  primary symptom of a KovaaK's slow spell and the worker should slow down,
  not plow through the queue timing out item after item. During an outage
  the worker converges to ~1 probe per 30 min, which doubles as the recovery
  detector.
  Tail (not head) requeue keeps one flaky scenario from blocking the queue
  behind its own backoffs. Per-item cap: 3 transient attempts per session,
  counted in the R5 outcome map by scenario name (duplicates share the same
  budget), then mark terminal (the next restart retries). Backoff sleeps are
  sliced (~10 s chunks), each slice re-reading R7's *last network success*
  timestamp, so any real HTTP success — the worker's own probes or another
  path's — wakes the worker within one slice; cache-served results never do.
  Sliced polling rather than a notification bridge is deliberate: the
  shipped primitive exposes read-only timestamps, and having `api_service`
  signal the worker's condition variable would invert the coupling.
- **R10 — Permanent failures skip immediately.** Unresolvable leaderboard IDs
  and validation failures are logged and marked terminal in the R5 outcome
  map without retries; a restart
  re-probes each once (accepted cost; a negative-resolution cache is a future
  lever, not v1).
- **R11 — Fatal failures stop the queue.** `UnknownKovaaksUserError` means
  every remaining item would fail identically: the worker stops, records the
  fatal state in its module-level progress state (surfaced by the R12 status
  line), and emits one `dash_logger.error`. Background-thread `dash_logger`
  calls are safe since the drained-queue fix: records logged without a
  callback context are queued and delivered by the Home interval drain
  (`flush_background_notifications`), the same route the rank-freshness
  Timer chain uses.
- **R12 — Status line: remaining-only.** The overview page shows
  "Updating percentile data: N remaining (~ETA)" where N counts unique
  non-terminal names queued or in flight (spam-proof) and ETA = N × recent
  average pace; during outage
  backoff it shows a paused note with the retry time. No done/total: the
  denominator is dynamic (unhides grow it, dedup shrinks it), so a ratio
  would visibly run backward. Transient failures never toast — a deliberate
  deviation from the "background failures notify via `dash_logger.error`"
  convention, because an outage is ambient state, not an event; only R11
  notifies.
- **R13 — Live overview refresh while warming.** A `dcc.Interval` on the
  overview page, enabled while the worker is busy — queued items or an item
  in flight; queue emptiness alone is not idleness, because the final item
  is popped before its fetch completes — re-runs the normal cache-only row
  build each tick so rows fill in as the user watches. On observing the
  worker go idle, the callback performs one last rebuild before disabling
  itself, so the final cache write is never left invisible. Full rebuild
  from disk cache — deliberately NOT the progressive-fill
  registry/rowTransaction transport, which streams in-memory generation
  state; the overview's data plane is the disk cache and its build is
  already cheap.
- **R14 — Layering: the worker sits at the Timer-chain layer.** It calls
  `resolve_leaderboard_id` / `fetch_scenario_rank` / totals directly and
  classifies exceptions itself (the `_run_attempt` precedent), because the UI
  entry point deliberately flattens failures into UNKNOWN. Partial success
  composes: if the rank saved but the totals call failed, the retry only
  re-pays the cheap totals call. The PR #112 stale-rank fallback lives above
  this layer (in `get_scenario_rank_info`), so the worker still sees raw
  exceptions — correct, since its job is repairing the cache, not serving
  degraded reads.
- **R15 — Kill switch, and off-by-configuration.** `percentile_warmup_enabled`
  (config.toml, default true) disables the warmer only — never interactive
  fetches. Independently, a falsey `kovaaks_username` disables the warmer
  identically: no startup enumeration, no network work, and the R6 enqueue
  hooks no-op. An empty username is the documented fully-offline
  configuration (README), which must stay offline regardless of the warmup
  default — and the worker's resolution fallback would otherwise still
  reach the scenario-search endpoint without a username. R11 covers only an
  API-confirmed invalid username; an unset one never reaches the network.
- **R16 — Testability.** The worker is a pure "process one item" step
  function with injected pacing/sleep, driven by a thin thread loop — the
  split is the better production design, not a test-only seam.
- **R17 — Logging.** DEBUG per item, INFO per playlist batch and per state
  change (backoff entered/exited, fatal stop), one INFO summary at
  completion.

## Coordination with progressive fill (shipped: PRs #114/#127)

The progressive-fill design (drafted in parallel with this proposal, now
shipped) owns the drill-in page (`/playlists/<code>`): two-phase load,
pending placeholders, registry + interval drain, per-generation progress.
Its durable record is the 2026-07-15 entry "Stream Playlist Positions With
Generation-Scoped Progressive Fill" in [decision_log.md](decision_log.md).
This proposal owns the ambient queue and the overview page. They compose
through the disk cache with no new shared state: a drill-in's phase 2 warms
a playlist → R5 skips those scenarios; the warmer's results make phase 2
near-instant (cache-fresh lookups complete in milliseconds without network).

Contract points:

1. The R7 signal is the one integration, and it shipped with PR #127
   (`record_interactive_activity()` / `get_api_activity_timestamps()` in
   `api_service.py`) with exactly R7's split semantics — the split came from
   a PR #114 review finding that a cache hit must not wake the worker from
   outage backoff. The worker consumes the primitive as-is; nothing is left
   to define.
2. The overview deliberately does not reuse the progressive-fill registry
   transport (R13 here); different data planes.
3. Status lines share a phrase family but deliberately different counters:
   done/total there (static per-generation total), remaining-only here
   (dynamic queue). Not a consistency bug.
4. Notification conventions align (no per-scenario spam). A misconfigured
   username can produce both the fill-summary toast and R11's fatal toast;
   rare and self-explaining, accepted.
5. R15's kill switch never disables progressive fill (user-initiated
   traffic).
6. Both former speed-fix dependencies merged as well (PR #113 total-play
   hydration hoist, PR #112 stale-rank fallback); the warmer additionally
   hydrates the leaderboard-id mapping once up front on its own.

## Edge cases (deliberate)

- Hide/unhide spam: duplicates are free (R5) and invisible in the counter
  (R12's unique-name count). A head-batch-comparison guard was considered and
  rejected: it stops firing the moment the worker consumes one item of the
  batch (timing-dependent behavior) while defending against a cost that is
  already zero.
- Unhide racing an in-flight fetch: the single worker serializes; the
  duplicate is freshness-skipped after the in-flight item saves. If the
  in-flight fetch failed transiently, the duplicate acts as a free retry —
  counted against the same per-name budget in the R5 outcome map; terminal
  names skip instead.
- Scenario played for the first time mid-session: the watchdog's new-scenario
  path already schedules the Timer-chain refresh (`file_watchdog.py`), so the
  queue never needs mid-session additions from gameplay.
- A playlist repeats a scenario (the shipped fill keys grid rows by playlist
  position for the same reason): the second occurrence freshness-skips.
- Cached UNRANKED: fresh → skipped without a totals fetch (R4's UNRANKED
  arm); correct (the user isn't on that board, and the overview renders no
  percentile for it; a new local score routes through the Timer chain).
- Debug mode: `app.py` runs `use_reloader=False`, so the worker starts once,
  like the watchdog observer.
- Shutdown mid-warm: the daemon thread dies; atomic cache writes can't tear;
  the next startup rebuilds the queue from staleness. No persisted queue
  state.
- Empty stats directory (brand-new user): the queue is empty; nothing to warm
  and nothing to display anyway. "Cleared local stats but has KovaaK's
  history" is explicitly unsupported.

## Out of scope

- Drill-in page UX (shipped progressive fill; see the decision log).
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
