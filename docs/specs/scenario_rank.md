# Scenario Rank

The dashboard looks up where the player currently places on a scenario's
global KovaaK's leaderboard and how that placement compares with everyone
else on the board. Placements are cached for a week and re-checked
automatically after a new personal best, so the display stays current
without hammering the API. When KovaaK's is slow or unavailable the app
keeps showing the best data it already has rather than erroring, and with
no username configured it makes no network calls at all. During normal
play the field explains its own state beside the value rather than
interrupting with a pop-up notification. A Refresh the player clicks
still answers with one, because they asked for it. So does a Steam ID
that disagrees with the account KovaaK's found — once per app session,
because the field has nowhere to say it.

Statements below describe what the app does today and link the
[decision log](../decision_log.md) entries that set them — rationale lives
in those entries, not here. A statement with no link is an implementation
fact that no decision-log entry governs. Runtime structure is mapped in
[architecture.md](../architecture.md); endpoint behavior and quirks in
[kovaaks_api_notes.md](../kovaaks_api_notes.md). In user-facing text,
leaderboard placement is worded "Position", never "Rank" (which means
benchmark tier) — see the
[2026-07-06 verbiage entry](../decision_log.md#2026-07-06-one-word-per-concept-in-leaderboard-verbiage).

## Data sources and identity

- Current rank comes from `/leaderboard/scores/global`.
  `/user/scenario/total-play` is metadata/upsert only — it hydrates
  `scenarioName -> leaderboardId` mappings for played scenarios and is never
  trusted for score or rank
  ([2026-04-27](../decision_log.md#2026-04-27-treat-total-play-as-metadata-only)).
- `scenarioName -> leaderboardId` resolution reads the permanent mapping
  cache, which is seeded at startup from the leaderboard IDs embedded in the
  bundled benchmark corpus
  ([2026-07-20](../decision_log.md#2026-07-20-seed-leaderboard-ids-from-the-bundled-benchmark-corpus))
  and served through an mtime-revalidated in-memory mirror
  ([2026-07-18](../decision_log.md#2026-07-18-leaderboard-mapping-reads-through-an-mtime-revalidated-in-memory-mirror)).
  `/scenario/popular` is the exact-name fallback for names the cache and
  `total-play` hydration cannot resolve.
- When `steam_id` is configured it is preferred for leaderboard identity
  matching; if Steam ID matching fails but exact username matching succeeds,
  the rank result is kept and a transient (never cached) warning is attached
  ([2026-04-27](../decision_log.md#2026-04-27-prefer-steam-id-matching-when-configured)).
  A mismatch is a persistent condition with no in-place home, so it gets one
  toast per app session — fired by the first passive render that observes it
  (scenario switch, new run, interval tick), titled "Steam ID mismatch", and
  persistent until dismissed. Later renders carry it silently, and a manual
  Refresh that merely re-observes the mismatch still reports a clean refresh:
  the fetch succeeded. A render nothing triggered — the duplicate-output fire
  Dash can make on page load — renders the value without spending the
  session's one toast.
- An empty `kovaaks_username` keeps the app fully offline: the rank service
  short-circuits before any network call
  ([2026-08-01](../decision_log.md#2026-08-01-no-username-stays-fully-offline--user-independent-totals-rejected)).

## Domain model

- UI code consumes `ScenarioRankInfo` and avoids endpoint-specific logic
  ([2026-04-27](../decision_log.md#2026-04-27-keep-kovaaks-api-details-behind-scenariorankinfo)).
- `ScenarioRankStatus` uses `StrEnum` with stable JSON values (`RANKED`,
  `UNRANKED`, `UNKNOWN`).
- Percentile is display-only metadata, derived with the midpoint formula from
  rank plus leaderboard total when rank info is returned; it is not stored in
  the rank cache
  ([2026-04-27](../decision_log.md#2026-04-27-use-the-midpoint-percentile-formula)).

## Caching

- Rank, leaderboard-total, and name-to-ID caches are JSON files under
  `data/cache/`
  ([2026-04-27](../decision_log.md#2026-04-27-use-json-files-for-runtime-api-caches),
  root relocated by
  [2026-07-11](../decision_log.md#2026-07-11-move-the-api-cache-under-datacache)),
  subject to the cache conventions in [AGENTS.md](../../AGENTS.md).
- `scenario_rank_cache_ttl_hours` and `leaderboard_total_cache_ttl_hours`
  both default to `168`
  ([2026-04-29](../decision_log.md#2026-04-29-cache-leaderboard-totals-for-one-week)).
- Every automatic rank-cache write routes through one process-locked
  monotonic writer, so a lower score or transient `UNRANKED` result never
  replaces a known better value; only a user-clicked Refresh is
  board-authoritative and may write a lower score or `UNRANKED`
  ([2026-07-01](../decision_log.md#2026-07-01-keep-scenario-rank-consistent-with-score-aware-refreshes)).

## HTTP behavior

- `kovaaks_api_timeout_seconds` defaults to `30`, one shared timeout for all
  KovaaK's requests
  ([2026-07-13](../decision_log.md#2026-07-13-kovaaks-timeout-is-30s-configurable-read-timeouts-are-not-retried)).
- Read timeouts fail immediately and are never retried; connection errors and
  HTTP 429 (honoring a capped `Retry-After`) retry once
  ([2026-04-28](../decision_log.md#2026-04-28-retry-kovaaks-get-transient-failures-once)
  as amended by
  [2026-07-13](../decision_log.md#2026-07-13-kovaaks-timeout-is-30s-configurable-read-timeouts-are-not-retried)).
- Requests reuse thread-local `requests.Session` objects
  ([2026-04-29](../decision_log.md#2026-04-29-use-thread-local-sessions-for-kovaaks-get-requests))
  and go through the hand-rolled retry helper, not urllib3 `Retry`
  ([2026-06-21](../decision_log.md#2026-06-21-keep-the-hand-rolled-get-retry-defer-urllib3-retry-migration)).

## Refresh behavior

- A new local high score triggers a bounded score-aware background refresh
  through a daemon `threading.Timer` chain (2/4/8/16/32 s), which accepts the
  leaderboard as caught up only when its score reaches the two-decimal floor
  of the local score; an exhausted chain leaves the previous cache untouched
  ([2026-07-01](../decision_log.md#2026-07-01-keep-scenario-rank-consistent-with-score-aware-refreshes)).
- The Home rank widget passively re-reads the rank and total caches on its
  existing interval — TTL ignored, no network calls
  ([2026-07-01](../decision_log.md#2026-07-01-keep-scenario-rank-consistent-with-score-aware-refreshes)).
- Background refresh failures are recorded in the console/file logs only;
  they produce no UI notification. The chain degrades silently — the widget
  keeps serving the cached value it already shows, and an exhausted chain is
  corrected only by the next successful lookup (a later PB, a manual Refresh,
  or a foreground fetch after the rank-cache TTL expires). An invalid username
  stops the chain outright, but is still reported by the foreground lookup the
  same run event triggers, not by the chain
  ([2026-08-03](../decision_log.md#2026-08-03-background-rank-diagnostics-are-console-only)).

## Failure handling

- Expected KovaaK's API/domain failures in the service layer become
  `ScenarioRankInfo(status=UNKNOWN, error_message=...)`
  ([2026-04-27](../decision_log.md#2026-04-27-keep-kovaaks-api-details-behind-scenariorankinfo)).
- Exception: a rank-fetch failure with a resolved leaderboard — unreachable
  endpoint or schema-invalid response — falls back to the last cached rank
  (TTL ignored, read-only) tagged with a `warning_message` and
  `served_stale=True`, so the value survives the failure; it becomes
  `UNKNOWN` only when nothing is cached. `force_refresh=True` inherits the
  same fallback
  ([2026-07-12](../decision_log.md#2026-07-12-rank-fetch-failure-degrades-to-the-last-cached-rank)).
- Passive renders never toast. The Home Position field carries its own
  explanation instead: `N/A` plus a link to the Settings page when no
  username is configured, `N/A` plus "lookup failed, Refresh to retry" when
  the lookup failed with nothing cached, and the cached value plus "from
  cache, Refresh to update" when a failed fetch was served from cache. The
  hint the last network-backed render concluded is reused by the cache-only
  interval path, which cannot see a failure that already happened, so the
  affordance does not blink off between ticks. That hint is tied to the value
  it explained: when a background writer (the warmup worker, the score-aware
  refresh Timer) moves the cache on, the interval reads a different value and
  the hint is retired rather than left contradicting a position that has
  since arrived.
- Manual Refresh answers with a toast whatever happens — the user asked for
  it — and all three outcomes come off the callback's own notification
  output. A hard failure (an `error_message` result or a raised exception) is
  red, titled "Position refresh failed", and leaves the displayed value
  untouched rather than flashing `N/A`, so its copy "Couldn't refresh —
  position unchanged." is true whether a cached position was on screen or
  not. A served-stale result is yellow, and its value carries the same
  "from cache, Refresh to update" affordance a passive render would give it.
  Only a genuinely fresh result gets the green confirmation, which keeps a
  fresh id per click so back-to-back refreshes each answer.
- Leaderboard total enrichment is best-effort: if the total lookup fails, the
  valid rank/unranked result is preserved
  ([2026-04-27](../decision_log.md#2026-04-27-make-leaderboard-total-enrichment-best-effort)).
- Unexpected application bugs may still raise and are handled by
  UI/background safety nets — the expected/unexpected boundary is set by
  the same entry that reserves `UNKNOWN` for expected failures
  ([2026-04-27](../decision_log.md#2026-04-27-keep-kovaaks-api-details-behind-scenariorankinfo)).
