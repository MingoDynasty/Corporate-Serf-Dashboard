# Scenario Rank Eventual Consistency Proposal (v8)

> v8 changes over v7: fix two consistency bugs in v7's own additions.
> (1) `_refresh_rank_after_high_score` now catches and logs scheduling failures
> (`dash_logger.error`) instead of letting them propagate — required because v7
> moved it ahead of `message_queue.append`, so a re-raise would otherwise block
> CSV ingestion and the PB toast. (2) The cache-hit backfill now updates the
> in-memory `scenario_name` whenever it is `None` and gates *only* the persist on
> `_has_active_rank_loop`, matching the prose (display still gets `scenario_name`;
> only the write is suppressed during a loop).
>
> (Earlier: v7 tightened read-path arbitration — call-site ordering + guard the
> cache-hit backfill; v6 added the in-flight loop counter and warning-only
> unresolved-leaderboard. Full deltas in git.)

## Summary

After a new local high score, the KovaaK's leaderboard endpoint can lag behind
the uploaded score by tens of seconds to several minutes. The existing
background refresh path
([`_refresh_rank_after_high_score`](../source/my_watchdog/file_watchdog.py)) fires
exactly once, so a single unlucky timing can cache stale or `UNRANKED` data
until the long `scenario_rank_cache_ttl_hours` (default 168h) expires.

The fix is to convert that single-shot refresh into a **bounded score-aware
poll**: keep refreshing until the returned leaderboard `score` is at least the
local high score, with a hard ceiling on attempts. Cache writes are gated on
freshness *and* guarded against regression, and the background scheduler never
lets an error die silently.

## Current Code Path

Refresh on high score today:

1. [`NewFileHandler.on_created`](../source/my_watchdog/file_watchdog.py) sees a
   CSV file, detects a new high score.
2. [`_refresh_rank_after_high_score`](../source/my_watchdog/file_watchdog.py:39)
   submits `refresh_scenario_rank` to a shared `ThreadPoolExecutor(max_workers=2)`.
3. [`refresh_scenario_rank`](../source/kovaaks/api_service.py:957) calls
   [`get_scenario_rank_info`](../source/kovaaks/api_service.py:834) with
   `force_refresh=True`.
4. `get_scenario_rank_info` calls
   [`fetch_scenario_rank`](../source/kovaaks/api_service.py:800), then
   unconditionally calls
   [`save_scenario_rank`](../source/kovaaks/api_service.py:611) (line 949) and
   `save_leaderboard_total`.

Steps 3 and 4 are the problem. They run exactly once, and step 4 has no concept
of "the returned data might be stale" — whatever comes back from KovaaK's wins
and is persisted for 168 hours.

## Freshness Condition

The right test is the returned `score`, not the rank number:

```python
SCORE_FRESHNESS_TOLERANCE = 0.01

def _score_is_fresh(rank_info: ScenarioRankInfo, expected_score: float) -> bool:
    return (
        rank_info.status == ScenarioRankStatus.RANKED
        and rank_info.score is not None
        and rank_info.score >= expected_score - SCORE_FRESHNESS_TOLERANCE
    )
```

Why score-based, not rank-based:

- The user's rank can stay the same after a PB if the score doesn't pass
  another player. Rank-equality is therefore not a freshness signal.
- `RankingPlayer.score` from
  [`/leaderboard/scores/global`](../source/kovaaks/api_service.py:179) is
  exactly what `fetch_scenario_rank` already captures into
  `ScenarioRankInfo.score`
  ([`api_service.py:828`](../source/kovaaks/api_service.py:828)).
  No new endpoint or model work needed.

### Why the tolerance is one-sided

The tolerance is applied only as downward slack on the threshold
(`expected_score - 0.01`), never as a symmetric `±` band. This is deliberate.

The tolerance exists for exactly one purpose: absorbing KovaaK's **truncation
of leaderboard scores to two decimal places**. The leaderboard endpoint reports
the user's score floored to `0.01`, so a fully caught-up board score sits
*marginally below* the local CSV value by up to (just under) one hundredth —
e.g. local `913.419861` is reported as `913.41`, never `913.42`. This was
verified empirically against real data (see [Testing](#testing)): across 445 of
the user's ranked scenarios the board score is the local score truncated to 2
dp, with a maximum observed shortfall of `0.00999`.

`0.01` is therefore sized to *exactly one truncation step* — not merely
float noise, and not "well below any meaningful precision." The value must stay
`>= 0.01`: tightening it (e.g. to `0.001`, on the mistaken belief that `0.01` is
loose) would reintroduce the bug, because a genuinely caught-up board would then
be rejected as stale and every PB on such a scenario would poll to exhaustion.
The guarantee holds structurally because 2-dp truncation error is always
strictly `< 0.01`, so `board >= expected - 0.01` is satisfied for every
caught-up score (worst-case real margin ~6e-6; float noise at these magnitudes
is ~1e-10, far below it).

A score **higher** than expected must always be accepted, so the upper bound
stays open:

- KovaaK's stores a player's *personal best* on a leaderboard, and
  `fetch_scenario_rank` filters to the exact matched player by Steam ID /
  username ([`api_service.py:816`](../source/kovaaks/api_service.py:816)). So
  `rank_info.score` is definitively the user's own high-water mark — never
  another player's.
- A higher server score therefore means the user has a better score on
  KovaaK's than the local CSV reflects (e.g. played on another machine, or the
  local DB is missing a run). It still satisfies the guarantee we care about:
  *the leaderboard now reflects at least the new high score.* The rank and
  percentile we read are valid to display.

A symmetric `±` band would add an upper rejection, causing the loop to keep
polling past a perfectly valid (higher) result and potentially exhaust all
attempts without ever writing the cache. The asymmetry is the point: lenient
below (rounding noise), unbounded above (a higher PB is more than caught up).

## Retry Schedule

Schedule: `30s, 60s, 120s, 240s, 300s`. Total wall-clock budget: ~12.5 minutes.

Rationale:

- 30s first delay gives KovaaK's a head start; the API often catches up within
  the first attempt.
- Exponential-ish backoff up to a 5-minute ceiling, since fixed long polls
  waste time when the API is fast and fixed short polls hammer when it is slow.
- 12.5 minutes is generous enough that if it doesn't resolve, the issue isn't
  a timing tweak away.

Each attempt makes one `fetch_scenario_rank` call. The inner
[`_get_with_retry`](../source/kovaaks/api_service.py:113) already handles 429s
and transient network errors with a single retry, so the outer loop never has
to think about HTTP-level politeness — the two concerns are deliberately
layered.

Keep the schedule as a module-level constant rather than a config value for the
initial release. Tunable only if real telemetry says it matters.

## Architecture

```text
file_watchdog (new high score detected)
    |
    v
schedule_rank_freshness_refresh(scenario, expected_score)
    |
    +-- mark scenario's loop active   # read path stops persisting its own fetch
    +-- schedule attempt #0 at now + 30s via threading.Timer
            |
            v
    on each scheduled tick (broad guard; chain marks the loop done on the
                            tick that terminates it — via _run_attempt's finally):
        result = fetch_scenario_rank(...)
        if _score_is_fresh(result, expected_score):
            if _save_rank_if_fresher(...):   # monotonic: never regress
                force-refresh leaderboard total
            done                              # terminal -> mark loop done
        elif attempts_remaining > 0:
            schedule next attempt             # NOT terminal -> loop stays active
        else:
            validate username; emit accurate dash_logger.error; preserve cache
                                              # terminal -> mark loop done
```

### Why a new function (in `api_service.py`), gated on cache writes

The freshness loop lives as a new function inside
[`api_service.py`](../source/kovaaks/api_service.py), alongside the low-level
pieces it composes. It is *not* a new module — there is no meaningful seam
between "fetch rank" and "poll until rank is fresh"; they share the same cache
files, the same HTTP client, and the same `resolve_leaderboard_id` mapping. A
separate module would only add an import boundary without isolating anything.

The reason it is a *separate function* rather than a flag on
[`get_scenario_rank_info`](../source/kovaaks/api_service.py:834) is **cache-write
semantics**, not async behavior:

- `get_scenario_rank_info` writes whatever the API returns to the rank cache,
  without conditioning on freshness
  ([`api_service.py:949`](../source/kovaaks/api_service.py:949)). That is correct
  for a read-through "give me current truth" lookup. (The v7 read-path
  arbitration adds an *external* gate — skip the write while a loop owns the
  scenario — but it does not give the function any freshness-based write logic of
  its own; that orthogonal gate is the point of the next two sections.)
- The freshness loop must do the opposite: write *only* when the result passes
  `_score_is_fresh` **and** would not regress a higher score already cached, and
  otherwise leave the existing cache untouched. Folding that conditional-write
  behavior into `get_scenario_rank_info` would make a single function mean two
  contradictory things about its own cache.

So the new function composes the existing low-level pieces directly, bypassing
`get_scenario_rank_info` entirely:

- `fetch_scenario_rank` (HTTP fetch)
- `_save_rank_if_fresher` (monotonic, regression-safe wrapper over
  `save_scenario_rank`)
- `_with_leaderboard_total` (forced total refresh)
- `resolve_leaderboard_id` (scenario → leaderboardId)

The existing thin wrapper
[`refresh_scenario_rank`](../source/kovaaks/api_service.py:957) (which is just
`get_scenario_rank_info(force_refresh=True, rank_cache_ttl_hours=0)`) is
**deleted** as part of this change — see [Removing
`refresh_scenario_rank`](#removing-refresh_scenario_rank) below.

### Removing `refresh_scenario_rank`

`refresh_scenario_rank` exists today only to serve the watchdog's single-shot
post-PB refresh. After this change the watchdog calls
`schedule_rank_freshness_refresh` instead, so `refresh_scenario_rank` has no
callers. Delete it.

The capability it provided — "bypass the cache and fetch current truth right
now" — is not lost. It was always a one-line wrapper, and any future caller
that needs a synchronous, cache-overwriting fetch (e.g. a manual-refresh button,
should we add one) can call `get_scenario_rank_info(force_refresh=True)` directly
— which now also inherits the read-path arbitration, so it overwrites the cache
*unless* a freshness loop is mid-flight for that scenario. Keeping a dedicated
wrapper around for a hypothetical second caller is a YAGNI trap: it would sit
unused, and a future caller is one trivial line away regardless.

This leaves two clearly distinguished rank operations:

| Operation | Function | Cache write | Returns | Use |
|---|---|---|---|---|
| Read current truth | `get_scenario_rank_info` (optionally `force_refresh=True`) | Unconditional, **except suppressed while a freshness loop is active** for the scenario ([read-path arbitration](#read-path-arbitration-in-flight-loop-counter)) | `ScenarioRankInfo` synchronously | UI lookups; any future on-demand "refresh now" |
| Poll until fresh after a PB | `schedule_rank_freshness_refresh` | Gated on `_score_is_fresh` + monotonic guard | `None` (fire-and-forget) | Watchdog post-high-score |

### Why `threading.Timer` instead of the executor

A `threading.Timer` is itself a thread that sleeps until its delay elapses, so
this choice does **not** eliminate sleeping threads — it is not free in that
sense, and the doc should not pretend otherwise. What it buys is keeping the
12.5-minute poll **off the bounded `rank_refresh_executor` (`max_workers=2`)**.
If two PBs across two scenarios both entered the loop using `time.sleep(...)` on
those two worker threads, the pool would be fully occupied for the whole window
and a third scenario's refresh would queue behind them.

The cost of Timer is one daemon thread per *pending* attempt. That count is
bounded by the number of distinct scenarios producing PBs inside a 12.5-minute
window — realistically well under ten — and each thread is short-lived relative
to nothing useful being blocked. That is an acceptable trade.

If a single thread for all pending refreshes were ever desired, a
`sched.scheduler` driven by one dedicated thread is the alternative. It is not
worth the extra machinery at this scale. Use Timer for the initial release.

### Independent loops per high score event

When multiple PBs land for the same scenario in quick succession (e.g. a
grinding session), each event schedules its own independent Timer chain. They
do not coordinate up front — there is no supersession or shared registry of
pending loops.

Independence alone is **not** sufficient to prevent cache regression. KovaaK's
stores the user's high-water mark, so each *fetch* is monotonic over time, but
the order in which two loops *write* the cache is not guaranteed to match the
order in which they fetched. Consider PB-1=100 (loop A) and PB-2=110 (loop B):

1. Loop A fetches while the API still reflects 100, passes `100 >= 100`, and is
   then preempted by the scheduler *before* it writes.
2. Loop B fetches after the API advances to 110, passes, and writes 110. The
   cache is now correct.
3. Loop A resumes and writes its stale `score=100` result, **regressing** the
   cache.

The window is tiny (the gap between one loop's fetch returning and its file
write), but it is real. The guard against it is a **monotonic conditional
save**, described next — not coordination between loops. This keeps the
"independent, uncoordinated loops" design while making the no-regression
property actually hold.

Cost of this simplicity: more API calls during dense grinding sessions. Worst
case is `<number of PBs in 12 min> × 5 attempts`, but in practice loops exit
early on attempt 1 or 2 once the API catches up. Realistic count is closer to
N+1 calls, not 5N. The inner `_get_with_retry` handles any 429 backoff that
might still result.

## Cache Write Gating

This is the most important behavior difference from today's code.

The freshness loop:

- Calls `_save_rank_if_fresher` — which writes via `save_scenario_rank` **only**
  when the result satisfies `_score_is_fresh` *and* does not lower a higher
  score already cached.
- Never overwrites an existing cached entry with a result that is older,
  lower-scored, or `UNRANKED` while retries remain.
- On retry exhaustion: preserves the existing cache entry as-is. Does not
  touch it. Does not write `UNKNOWN`. If no prior entry exists, leaves the
  cache empty so normal lookup paths can decide what to display.

This is enforced structurally by *not* going through `get_scenario_rank_info`
in the freshness path. The new function calls `fetch_scenario_rank` directly,
inspects the result, and only invokes the conditional save on success.

### Monotonic conditional save

`_save_rank_if_fresher` makes the "saved scores never go backwards" invariant
hold even when two loops race on the same leaderboard. A single process-wide
lock makes the read-compare-write atomic; saves are infrequent and fast (one
small file write), so a single global lock is simpler than per-leaderboard
locks and has no meaningful contention cost.

```python
_rank_save_lock = threading.Lock()


def _save_rank_if_fresher(
    leaderboard_id: int,
    username: str,
    rank_info: ScenarioRankInfo,
) -> bool:
    """Persist a freshly-verified rank unless it would regress the cache.

    Returns True when the write happened, False when an existing higher score
    was preserved. The lock makes read-compare-write atomic across concurrent
    freshness loops for the same leaderboard.
    """
    with _rank_save_lock:
        existing_score = _cached_rank_score(leaderboard_id, username)
        new_score = rank_info.score
        if (
            existing_score is not None
            and new_score is not None
            and existing_score > new_score
        ):
            return False  # a higher score is already cached; do not regress
        save_scenario_rank(leaderboard_id, username, rank_info)
        return True
```

`_cached_rank_score` reads the stored score directly from the rank cache file
**independent of TTL** (the comparison cares about the persisted value, not its
age). It can be a thin read over `_read_json(_rank_cache_file(...))` returning
`score`, or `get_cached_scenario_rank(..., cache_ttl_hours=<effectively
unbounded>).score`; the former is clearer.

**Scope of the no-regression guarantee.** The monotonic save protects
loop-versus-loop races, but it is *not* the only writer of the rank cache. The
UI read path [`get_scenario_rank_info`](../source/kovaaks/api_service.py:834)
writes unconditionally and *without* `_rank_save_lock` on a cache miss/expiry
([`api_service.py:949`](../source/kovaaks/api_service.py:949)) — and that write
is exactly the hazard this whole proposal exists to stop. After a PB, `do_update`
fires [`get_scenario_rank`](../source/pages/home.py:131); on a cold or expired
cache the read path fetches the *lagging* leaderboard value (`UNRANKED` or a
lower score) and persists it, possibly seconds after the PB and well before the
freshness loop's first attempt at +30s. Because that write refreshes the cache
mtime, later views inside the 168h TTL return the stale value without
re-fetching; the loop repairs it on a successful save, but on exhaustion or
app-exit mid-loop the stale entry survives the full TTL.

(v5 wrongly called this read-path write "freshly-fetched server truth
(monotonic from KovaaK's)" and therefore safe. It is *not* monotonic — the whole
premise of this proposal is that the leaderboard endpoint lags a fresh PB, so the
read path's fetch can be lower than the local high.)

The fix is **read-path arbitration via an in-flight loop counter** (next
subsection): while a freshness loop owns a scenario, the read path still
*displays* its fetch but does not *persist* it, leaving the loop's gated,
monotonic save as the sole cache writer for that scenario during the window. This
also subsumes the earlier **deferred manual-refresh button** concern: any future
`get_scenario_rank_info(force_refresh=True)` caller reaches the same guarded save
at line 949, so it too is suppressed while a loop is active and cannot regress a
running loop's higher score.

The forced leaderboard-total refresh runs only when the save actually happened.
A skipped (regression-avoided) save means a fresher loop already wrote the rank
and forced its own total refresh, so repeating it would be a wasted API call.

### Read-path arbitration (in-flight loop counter)

`_save_rank_if_fresher` stops one loop from regressing another, but it does not
stop the UI read path from persisting a lagging fetch during the window (the
hazard described above). A small in-flight registry closes that: a process-wide
counter of scenarios with a live freshness loop, consulted by the read path
before it persists.

```python
_active_loops_lock = threading.Lock()
_active_rank_loops: collections.Counter[tuple[str, str]] = collections.Counter()


def _mark_loop_active(username: str, scenario_name: str) -> None:
    with _active_loops_lock:
        _active_rank_loops[(username, scenario_name)] += 1


def _mark_loop_done(username: str, scenario_name: str) -> None:
    with _active_loops_lock:
        key = (username, scenario_name)
        _active_rank_loops[key] -= 1
        if _active_rank_loops[key] <= 0:
            del _active_rank_loops[key]


def _has_active_rank_loop(username: str, scenario_name: str) -> bool:
    with _active_loops_lock:
        return _active_rank_loops[(username, scenario_name)] > 0
```

Design notes:

- **Keyed by `(username, scenario_name)`, not `leaderboard_id`.** A loop is
  scheduled before it has resolved a leaderboard id, but it already knows the
  scenario name — and so does the read path (it is the dropdown selection / the
  callback argument). Keying on the name lets both sides agree without waiting
  for resolution. One scenario maps to one leaderboard, so the two keyings are
  equivalent in practice.
- **A counter, not a set.** Dense grinding can start several loops for the same
  scenario; the read path must stay suppressed until the *last* of them
  finishes.
- **Lifecycle: increment once, decrement once per chain.**
  `schedule_rank_freshness_refresh` increments before scheduling attempt #0.
  Whether that actually covers the window from PB detection depends on the
  watchdog marking active before it makes the run UI-visible — see [Call-site
  ordering](#call-site-ordering-mark-active-before-the-run-is-ui-visible). Each
  chain decrements exactly once, on whichever attempt *terminates* it — success,
  exhaustion, a terminal error, or the broad guard — and never when an attempt
  reschedules. The `_run_attempt` pseudocode enforces this with a `rescheduled`
  flag and a `finally` (see [API Shape](#api-shape)).

The read path skips **both** of its rank-cache writes while a loop is active, not
just the cache-miss save. Concretely:

- The cache-miss/`force_refresh` save at
  [`api_service.py:949`](../source/kovaaks/api_service.py:949):

```python
rank_info = rank_info.model_copy(update={"scenario_name": scenario_name})
if not _has_active_rank_loop(username, scenario_name):
    save_scenario_rank(leaderboard_id, username, rank_info)
# Total attach + warning derivation are unchanged; the fetched rank is still
# returned for display whether or not it was persisted.
```

- The cache-*hit* `scenario_name` backfill at
  [`api_service.py:906`](../source/kovaaks/api_service.py:906):

```python
if cached_rank.scenario_name is None:
    # Always attach scenario_name in memory (display/return path)...
    cached_rank = cached_rank.model_copy(update={"scenario_name": scenario_name})
    # ...but only persist when no loop owns the scenario.
    if not _has_active_rank_loop(username, scenario_name):
        save_scenario_rank(leaderboard_id, username, cached_rank)
```

The backfill never *lowers* the score (it re-writes the cached value), but it
does refresh the file `mtime`, which would extend a stale entry's 168h TTL right
when a PB has made it stale — defeating the very TTL-expiry that would otherwise
let the stale entry self-heal on the next view. Guarding it keeps the invariant
clean: **no read-path write touches the rank cache while a loop owns the
scenario.** (This only ever fires for legacy entries written before
`scenario_name` existed, so it is a minor, transitional case — but guarding it is
one extra clause and removes the inconsistency.) For display, the in-memory
`model_copy` still attaches `scenario_name`; only the persistence is skipped.

The check is **advisory**: there is a tiny window between `_has_active_rank_loop`
returning `False` and the save in which a loop could start and the read path
could still persist one lagging value. The consequence is benign — the loop's
monotonic save remains authoritative and corrects the cache on its next
successful attempt, after which the read path is suppressed. Making it airtight
would mean holding `_active_loops_lock` across the file write (lock-ordering it
ahead of `_CACHE_IO_LOCK`); not worth the nesting for a race the existing
machinery already heals. `_active_loops_lock` is never nested with
`_rank_save_lock` or `_CACHE_IO_LOCK`, so it introduces no deadlock risk.

### Leaderboard Total Refresh

On every successful freshness save, also force a fresh fetch of the
leaderboard total — bypassing its normal `leaderboard_total_cache_ttl_hours`
TTL — and overwrite
[`leaderboard/totals/{leaderboard_id}.json`](../source/kovaaks/api_service.py:625).

Why force a refresh even though the total moves slowly:

- The displayed percentile is derived as
  `((total - rank + 0.5) / total) * 100`. Both inputs need to be current for
  the displayed percentile to match KovaaK's own reported percentile, which is
  the value the user compares against.
- The total cache's default TTL is 168 hours. Without forcing a refresh on PB,
  the percentile shown next to a brand-new rank could be derived from a
  total-player count that is up to a week stale, producing a small but
  visible drift from KovaaK's website.
- A PB is a natural moment to spend one extra API call. The user is actively
  watching the rank widget and percentile, so the marginal call is worth the
  accuracy.

Implementation: pass `leaderboard_total_cache_ttl_hours=0` to
[`_with_leaderboard_total`](../source/kovaaks/api_service.py:711) inside the
freshness path. That bypasses the cache freshness check and triggers
[`fetch_leaderboard_total`](../source/kovaaks/api_service.py:660) +
[`save_leaderboard_total`](../source/kovaaks/api_service.py:648).

The freshness function does not expose the total TTL as a parameter — it always
forces a refresh on a successful save. Callers (e.g. the watchdog) don't need to
thread `config.leaderboard_total_cache_ttl_hours` through to the freshness path.

If the total fetch itself fails (transient API failure), the rank save still
succeeds. The user sees the new rank without an updated total/percentile until
the next normal lookup refreshes the total. This is a strict improvement over
today's behavior, where the rank also fails to update.

## Error Handling

The background loop must never let an error vanish. Today's executor path wraps
every refresh in [`_handle_rank_refresh_result`](../source/my_watchdog/file_watchdog.py:31),
which catches **any** `Exception` from the background work and surfaces it via
`dash_logger.error`. Moving scheduling to Timers must preserve that safety net,
because an exception raised inside a Timer's target dies in that Timer thread
with no UI signal.

Two distinct error classes, handled differently:

- **Transient (retry):** a `requests.RequestException` from *either*
  `resolve_leaderboard_id` **or** `fetch_scenario_rank` is treated as "not yet";
  the loop continues to its next scheduled attempt. The inner `_get_with_retry`
  has already retried once at the HTTP layer. `resolve_leaderboard_id` is
  included deliberately: the **new-scenario / first-PB path** has no cached
  leaderboard mapping yet, so resolution must hit the network
  (`search_scenario_exact`), and a blip there must retry rather than terminate.
  This is distinct from `resolve_leaderboard_id` returning `None`, which is
  terminal (the scenario genuinely has no leaderboard — see below).
- **Terminal (stop + notify):** anything that will fail identically on retry —
  most notably `UnknownKovaaksUserError` from
  [`resolve_leaderboard_id`](../source/kovaaks/api_service.py:540) (it can
  propagate from the total-play hydration path; `get_scenario_rank_info` already
  wraps it at [`api_service.py:870`](../source/kovaaks/api_service.py:870)), and
  any unexpected exception. These stop the loop and emit `dash_logger.error`.
  Retrying a bad username five times would just delay the same failure.

A third, quieter case sits between these: `resolve_leaderboard_id` returning
`None` (the scenario has no KovaaK's leaderboard at all). This stops the loop but
is **logged at warning level only, with no `dash_logger` toast.** `None` is the
normal state for local/custom scenarios that were never uploaded to KovaaK's, so
a user-facing notification on every such PB would cry wolf. "Never die silently"
is satisfied by the log line; toasts are reserved for conditions the user can act
on (a misconfigured username) or genuinely unexpected failures.

The entire attempt body is therefore wrapped in a broad last-resort guard so no
Timer thread can die silently.

## API Shape

New function in `source/kovaaks/api_service.py` (alongside `fetch_scenario_rank`,
`save_scenario_rank`, and `_with_leaderboard_total`, which it composes):

```python
ATTEMPT_DELAYS_SECONDS = (30, 60, 120, 240, 300)  # ~12.5 min total
SCORE_FRESHNESS_TOLERANCE = 0.01


def schedule_rank_freshness_refresh(
    scenario_name: str,
    username: str,
    steam_id: str | None,
    expected_score: float,
    metadata_cache_ttl_hours: int = 24,
) -> None:
    """Start a bounded score-aware rank refresh for a newly observed high score.

    On a successful (non-regressing) save, also force-refreshes the leaderboard
    total so the displayed percentile stays pinned to KovaaK's truth.
    """
    # Mark the loop active *before* scheduling so the read path stops persisting
    # its own (possibly lagging) fetch from the first attempt at +30s onward. The
    # chain releases this in _run_attempt's finally (see below). NOTE: this only
    # covers the window from PB detection if the watchdog calls this function
    # before it makes the new run UI-visible — see "Call-site ordering" below.
    _mark_loop_active(username, scenario_name)
    try:
        _schedule_attempt(
            scenario_name, username, steam_id, expected_score,
            metadata_cache_ttl_hours, attempt_index=0,
        )
    except Exception:  # noqa: BLE001 — failed to even schedule the first tick
        _mark_loop_done(username, scenario_name)  # don't leak the increment
        raise  # the watchdog adapter (_refresh_rank_after_high_score) swallows this
```

The re-raise is deliberate: `schedule_rank_freshness_refresh` must signal that it
failed to start (and release the counter it just took), but it is *not* its job
to decide whether that failure is fatal. The watchdog adapter does — see below.

Called from
[`_refresh_rank_after_high_score`](../source/my_watchdog/file_watchdog.py:39),
which gains an `expected_score` argument. The watchdog already knows the new
high score (`run_data.score`) at the point it decides to call the refresh, so
threading the value through is mechanical.

The existing `_refresh_rank_after_high_score` becomes:

```python
def _refresh_rank_after_high_score(scenario_name: str, expected_score: float) -> None:
    if not config.kovaaks_username:
        return
    # Rank refresh is best-effort and now runs *before* message_queue.append /
    # load_csv_file_into_database on the PB path (see Call-site ordering). A
    # failure to schedule the first timer (e.g. OS thread-limit on Timer.start)
    # must NOT block CSV ingestion or the PB toast, so swallow and log it here.
    try:
        schedule_rank_freshness_refresh(
            scenario_name,
            config.kovaaks_username,
            config.steam_id,
            expected_score,
            config.scenario_metadata_cache_ttl_hours,
        )
    except Exception:  # noqa: BLE001 — best-effort; never block ingestion
        logger.exception("Failed to schedule rank refresh for %s", scenario_name)
        dash_logger.error(f"Could not start rank update for {scenario_name}.")
```

This is the layer that makes the scheduling "best-effort": `schedule_rank_freshness_refresh`
reports failure by raising (and has already released its counter), and
`_refresh_rank_after_high_score` decides that failure is non-fatal — log it,
surface it once via `dash_logger.error`, and return so the run is still recorded
and the PB toast still fires.

The shared `rank_refresh_executor` (`ThreadPoolExecutor(max_workers=2)`) in
`file_watchdog.py` was created solely for the single-shot post-PB refresh. With
scheduling now handled by `threading.Timer` inside the freshness function, it
has no remaining users. **Remove it** along with `_handle_rank_refresh_result`
(its all-exceptions notification is replaced by the broad guard inside
`_run_attempt`). Scheduling is no longer the watchdog's concern; it just fires
`schedule_rank_freshness_refresh` and returns.

#### Call-site ordering (mark active before the run is UI-visible)

The in-flight guard only protects the read path if the loop is marked active
*before* the new run becomes visible to the UI. Today every PB call site appends
to `message_queue` first and schedules the refresh last
([`file_watchdog.py:84`](../source/my_watchdog/file_watchdog.py:84) then
[`:95`](../source/my_watchdog/file_watchdog.py:95)). The 1s interval callback
[`check_for_new_data`](../source/pages/home.py:85) can observe that queue entry,
flip `do_update`, and fire [`get_scenario_rank`](../source/pages/home.py:131) in
the gap **before** `_mark_loop_active` runs — so the read path persists a lagging
fetch and the guard never fired. (In practice the local mark usually wins the
race against the read path's networked fetch, but "usually" is not the
guarantee.)

The fix is an ordering requirement at each PB call site: call
`_refresh_rank_after_high_score(...)` (which marks the loop active) **before** the
`message_queue.append(...)` for that run. The CSV-load can stay where it is — the
freshness loop does not read the local DB. Concretely, each of the three PB paths
(new scenario; new sensitivity with new PB; existing scenario with new PB)
becomes:

```python
if is_new_high_score:                       # unconditional in the new-scenario case
    _refresh_rank_after_high_score(run_data.scenario, run_data.score)
message_queue.append(NewFileMessage(...))   # only now is the run UI-visible
load_csv_file_into_database(file)
```

`_refresh_rank_after_high_score` only marks/schedules; it is non-blocking
(microseconds), so moving it ahead of the append does not delay the PB toast.
Crucially it also **swallows scheduling failures** (it catches anything
`schedule_rank_freshness_refresh` raises, logs it, and surfaces one
`dash_logger.error` — see its body above). Because it is now on the hot path
before ingestion, that guard is what guarantees a failed `Timer.start` cannot
prevent the `message_queue.append` / `load_csv_file_into_database` below it from
running.

### Pseudocode for one attempt

```python
def _run_attempt(
    scenario_name: str,
    username: str,
    steam_id: str | None,
    expected_score: float,
    metadata_cache_ttl_hours: int,
    attempt_index: int,
) -> None:
    # Broad last-resort guard: a Timer thread must never die silently.
    rescheduled = False
    try:
        rank_info = None
        try:
            leaderboard_id = resolve_leaderboard_id(
                scenario_name, username, metadata_cache_ttl_hours,
            )
        except UnknownKovaaksUserError as exc:
            logger.warning("Rank refresh stopped for %s: %s", scenario_name, exc)
            dash_logger.error(
                f"Rank update for {scenario_name} failed: "
                "KovaaK's username may be misconfigured."
            )
            return  # terminal: do not retry a bad username
        except requests.RequestException:
            # Transient: resolve_leaderboard_id swallows its own hydration
            # RequestExceptions, but search_scenario_exact (the cold-cache,
            # first-PB path) can still raise. Fall through to the retry tail
            # rather than letting the broad guard kill the loop.
            logger.warning(
                "Transient failure resolving leaderboard for %s; will retry",
                scenario_name, exc_info=True,
            )
            leaderboard_id = None  # NOT terminal — distinct from a resolved None
        else:
            if leaderboard_id is None:
                logger.warning("Could not resolve leaderboard for %s", scenario_name)
                return  # terminal: scenario genuinely has no leaderboard
            try:
                rank_info = fetch_scenario_rank(leaderboard_id, username, steam_id)
            except requests.RequestException:
                rank_info = None  # transient; fall through to retry

        if rank_info is not None and _score_is_fresh(rank_info, expected_score):
            rank_info = rank_info.model_copy(update={"scenario_name": scenario_name})
            if _save_rank_if_fresher(leaderboard_id, username, rank_info):
                # Force-refresh the total only when we actually wrote. Failure is
                # non-fatal: the rank save still stands.
                try:
                    _with_leaderboard_total(rank_info, leaderboard_total_cache_ttl_hours=0)
                except Exception:  # noqa: BLE001
                    logger.warning("Total refresh failed after fresh rank", exc_info=True)
            return  # success (or superseded by a fresher save); exit loop

        next_index = attempt_index + 1
        if next_index >= len(ATTEMPT_DELAYS_SECONDS):
            _notify_exhaustion(scenario_name, username, metadata_cache_ttl_hours)
            return  # exhausted; exit loop without writing cache

        _schedule_attempt(
            scenario_name, username, steam_id, expected_score,
            metadata_cache_ttl_hours, next_index,
        )
        rescheduled = True  # chain continues; the next tick owns the decrement
    except Exception:  # noqa: BLE001 — last-resort guard for the Timer thread
        logger.exception("Unexpected error during rank refresh for %s", scenario_name)
        dash_logger.error(f"Rank update for {scenario_name} failed unexpectedly.")
        # Do not reschedule: an unexpected error will most likely recur.
    finally:
        # Exactly one decrement per chain. Every terminal exit (success,
        # exhaustion, terminal error, broad guard) reaches here with
        # rescheduled=False; a rescheduled tick skips it. If _schedule_attempt
        # itself raised, rescheduled is still False, so the chain is correctly
        # released here.
        if not rescheduled:
            _mark_loop_done(username, scenario_name)


def _notify_exhaustion(
    scenario_name: str, username: str, metadata_cache_ttl_hours: int,
) -> None:
    logger.warning("Rank freshness refresh exhausted for %s", scenario_name)
    # Always validate on exhaustion (one call, failure path only) to choose an
    # accurate message: distinguish genuine API lag from a misconfigured
    # username. We do not track whether a RANKED result was ever seen to skip
    # this call — that state isn't worth threading through the Timer chain for a
    # single saved call on a rare path (see Resolved Decisions).
    try:
        get_user_scenario_total_play(username, metadata_cache_ttl_hours)
    except UnknownKovaaksUserError:
        dash_logger.error(
            f"Rank update for {scenario_name} failed: "
            "KovaaK's username may be misconfigured."
        )
        return
    except requests.RequestException:
        pass  # validation unavailable; fall back to the generic message
    dash_logger.error(
        f"Rank update timed out for {scenario_name}. KovaaK's may still be catching up."
    )


def _schedule_attempt(..., attempt_index: int) -> None:
    delay = ATTEMPT_DELAYS_SECONDS[attempt_index]
    timer = threading.Timer(delay, _run_attempt, args=(...,))
    timer.daemon = True
    timer.start()
```

## UI Behavior

Minimum viable:

- Keep displaying the previously cached rank during the freshness loop.
- The existing
  [`dcc.Loading`](../source/pages/home.py:542) wrapping the rank text remains
  as-is. It only spins when the UI callback is running, which is the right
  behavior — the freshness loop runs in the background and the rank widget keeps
  showing the cached value until the callback re-runs (see the trigger note
  below).
- No new "Updating..." text. The user has already seen the PB notification
  toast; the rank widget can lag behind by a minute or two without being
  confusing.

### How (and when) the widget actually picks up the refreshed cache

The freshness loop only writes the cache; it does not push to the UI. The rank
text is rendered by [`get_scenario_rank`](../source/pages/home.py:130), whose
only inputs are the `do_update` store and the scenario dropdown. `do_update` is
**not** a periodic tick: [`check_for_new_data`](../source/pages/home.py:85) runs
on the 1s interval but flips `do_update` only when `message_queue` holds an entry
for the *currently-selected* scenario (or auto-switch changes the dropdown). So
the rank widget re-renders on **the next run for the selected scenario, or on a
scenario re-selection** — never on a plain timer.

Consequences:

- **During an active grind on the same scenario:** self-heals. The next rep
  flips `do_update`, the callback re-reads the now-fresh cache, and the updated
  rank appears. (It updates on the first rep *after* the loop's successful save,
  not instantly.)
- **Residual gap — the last PB before stopping or switching away:** the loop
  writes the correct cache 30s–12min later, but nothing re-renders, so the
  widget shows the stale rank until the user re-selects that scenario. Narrow,
  but real. The proposal's earlier "next polling tick" framing was inaccurate:
  there is no periodic re-read of the rank cache.

This is acceptable for the minimum-viable cut (the cache is *correct* the moment
the user next looks; no blocking fetch happens in the callback). If live update
is wanted, the scoped fix is to give the rank callback its own periodic trigger
— add `Input("interval-component", "n_intervals")` to `get_scenario_rank` so it
re-reads the (cheap, cache-only) rank each tick. **Caveat:** that callback also
emits `dash_logger.warning`/`error` for `warning_message`/`error_message`
([home.py:152-157](../source/pages/home.py:152)); firing it every second would
spam those toasts for users in a persistent warning/error state (e.g. Steam-ID
mismatch). So the live-update variant must first move or guard that notification
emission so it fires only on change, not on every tick. Deferred unless the
residual gap proves annoying in practice.

Failure surfaces via `dash_logger.error(...)` directly from the freshness
function — the same `dash_logger` channel the watchdog uses today. There are
three trigger points, all non-blocking: a terminal bad-username error, an
unexpected exception caught by the broad guard, and retry exhaustion (with the
message tuned by the username-validation check). An unresolved leaderboard
(`resolve_leaderboard_id` → `None`) is **not** one of them: it stops the loop
with a `logger.warning` only, no toast (see [Error Handling](#error-handling)).
The old `_handle_rank_refresh_result` callback is removed because the freshness
function now emits these notifications itself.

## Failure Modes And Edge Cases

| Case | Behavior |
|---|---|
| API never reports the new score within 12.5 min | Preserve previous cache. `_notify_exhaustion` validates the username, then emits "still catching up" (valid user) via `dash_logger.error`. User sees stale rank with no spinner. |
| API reports `RANKED` with score *higher* than expected | Accept as fresh. Save (monotonic) and exit loop. |
| API reports `UNRANKED` | Do not save. Continue retries. After exhaustion, `_notify_exhaustion` distinguishes lag from a misconfigured username. Previous cache preserved. |
| Multiple PBs for the same scenario in succession | Each schedules its own independent loop. The monotonic `_save_rank_if_fresher` prevents a slower lower-score loop from overwriting a higher score already cached by a faster loop. The in-flight counter holds the read path suppressed until the *last* of these loops finishes. |
| UI read callback (`get_scenario_rank`) fires during the freshness window (new-scenario + auto-switch, or expired cache + PB) | Read path fetches the lagging value and *displays* it, but **does not persist** it — `_has_active_rank_loop` is true. The loop's gated, monotonic save is the only writer until it finishes. Closes the v5 read-path stale-write hole. |
| `fetch_scenario_rank` raises `RequestException` | Treat as transient; continue retries. The inner `_get_with_retry` has already retried once at the HTTP layer. |
| `resolve_leaderboard_id` raises `UnknownKovaaksUserError` | Terminal. Stop the loop immediately; emit a "username may be misconfigured" `dash_logger.error`. No retries. |
| `resolve_leaderboard_id` raises `requests.RequestException` (e.g. `search_scenario_exact` network blip on the first-PB cold-cache path) | Transient. Treat like a failed fetch: continue retries, exhaust if it never resolves. Distinct from a resolved `None`. |
| `resolve_leaderboard_id` returns `None` | Terminal: the scenario has no leaderboard on KovaaK's (normal for local/custom scenarios). Stop the loop with a `logger.warning` only — **no `dash_logger` toast**, which would cry wolf on every PB of an unranked custom scenario. |
| Any unexpected exception inside an attempt | Caught by the broad guard. Logged with traceback; emits a generic `dash_logger.error`. Loop stops (no reschedule). |
| App shuts down mid-loop | Daemon Timers die with the process. Next app start relies on the long cache TTL until either the cache expires or a new PB triggers a new freshness refresh. Acceptable. |
| User configures `kovaaks_username = ""` mid-session | New PBs no-op the refresh path. Existing in-flight Timer chains finish under their original username — harmless. |
| Multiple scenarios in flight | Each is independent. Bounded by how many distinct scenarios produce PBs in a 12.5-min window — realistically <10, so <10 pending Timer threads. |
| Test environments without network | `fetch_scenario_rank` raises; loop retries then exhausts; `_notify_exhaustion`'s validation also fails transiently and falls back to the generic message; no cache changes. Safe. |
| Rank save succeeds but leaderboard total fetch fails | Rank cache is updated; total cache is left as-is. Displayed percentile may briefly use the previous total. Logged as a warning. Strict improvement over today's behavior. |
| `schedule_rank_freshness_refresh` raises (e.g. `Timer.start` hits the OS thread limit) | `schedule_rank_freshness_refresh` releases its counter and re-raises; `_refresh_rank_after_high_score` catches it, logs, emits one `dash_logger.error`, and returns. CSV ingestion and the PB toast proceed normally; no rank refresh runs for this PB. |

## Testing

Unit tests for the freshness function in `api_service.py`, mocking
`fetch_scenario_rank` and `threading.Timer`:

- Accepts a `RANKED` result when `api_score == expected_score`.
- Accepts a `RANKED` result when `api_score > expected_score`.
- Accepts a `RANKED` result within tolerance (`expected - 0.005`).
- Retries when API returns `UNRANKED`, then accepts a later fresh result.
- Retries when API returns a lower stale score, then accepts a later fresh
  result.
- Does not call `save_scenario_rank` on any stale result.
- Calls `save_scenario_rank` exactly once on the first fresh result.
- **Monotonic save: an older/lower loop cannot overwrite a higher cached
  score.** Seed the rank cache with `score=110`; run an attempt that fetches
  `score=100` and passes freshness (`expected_score=100`); assert
  `_save_rank_if_fresher` returns `False`, the cache file still reads `110`, and
  the forced total refresh is *not* triggered.
- On a fresh, non-regressing result, force-refreshes the leaderboard total cache
  even when the existing total cache file is within its normal TTL. Verify
  `cache/leaderboard/totals/{leaderboard_id}.json` is overwritten (e.g. by
  asserting its `mtime` advances, or by seeding it with a known sentinel value
  and confirming the sentinel is replaced).
- A `fetch_leaderboard_total` failure on the success path does not block the
  rank save and does not raise out of `_run_attempt`.
- **Resolver/unknown-user errors surface cleanly:** `resolve_leaderboard_id`
  raising `UnknownKovaaksUserError` stops the loop on the first attempt, emits a
  "username may be misconfigured" `dash_logger.error`, and schedules no further
  Timer.
- **Transient resolver error retries (no notify, no write):** mock
  `resolve_leaderboard_id` raising `requests.RequestException` on the first
  attempt; assert it **schedules the next attempt**, emits **no** `dash_logger`
  notification (it is not the broad guard, not terminal), and writes **nothing**
  to the rank cache. On a later attempt where resolution succeeds and the score
  is fresh, it saves normally. This is the branch v6 fixed but v5 left untested.
- **Unresolved leaderboard is warning-only:** `resolve_leaderboard_id` returning
  `None` stops the loop, schedules no further Timer, writes nothing, and emits a
  `logger.warning` but **no `dash_logger` toast** — distinct from both the
  transient-`RequestException` branch (which retries) and the
  `UnknownKovaaksUserError` branch (which toasts).
- **Broad guard:** an unexpected exception inside an attempt is caught, logged
  with a traceback, surfaces via `dash_logger.error`, and does not reschedule.
- Exhausts all 5 attempts when API never catches up; previous rank cache file
  is byte-for-byte unchanged after the run, and the leaderboard total cache is
  also untouched.
- **Exhaustion message branches:** with a valid username the exhaustion
  notification says "may still be catching up"; with an invalid username
  (`get_user_scenario_total_play` raises `UnknownKovaaksUserError`) it says
  "username may be misconfigured."
- Two concurrent loops for the same scenario at different expected scores both
  exit cleanly when the API catches up (no cache corruption, no exception, no
  regression of the higher score).
- **Read-path suppression while a loop is active, both write sites (the v6/v7
  fix):** with `_has_active_rank_loop(username, scenario)` true, assert
  `get_scenario_rank_info` persists nothing — neither (a) the cache-miss/`force_refresh`
  save (seed an empty cache, fetch a lagging value, assert no `save_scenario_rank`
  and the cache file stays absent) nor (b) the cache-hit `scenario_name` backfill
  (seed a fresh cached entry with `scenario_name=None`, assert the file `mtime`
  does **not** advance). With no active loop, both paths persist as before.
- **In-flight counter lifecycle:** `schedule_rank_freshness_refresh` marks the
  scenario active; the counter returns to empty after a terminal exit (assert for
  each of success, exhaustion, terminal error, and broad guard) and stays
  non-zero across a reschedule. Two overlapping loops for one scenario drop the
  count to zero only after **both** finish, so the read path stays suppressed
  until the last one exits.

Watchdog-level tests: assert that
[`NewFileHandler.on_created`](../source/my_watchdog/file_watchdog.py) calls
the new `schedule_rank_freshness_refresh` with `expected_score=run_data.score`
on new-high-score paths, and not on non-PB paths. **Plus a call-site-ordering
test that fails against the current code:** with `schedule_rank_freshness_refresh`
and `message_queue.append` both mocked, assert the refresh (active mark) is
invoked **before** the append on every PB path — e.g. record call order on a
shared mock and assert `schedule_rank_freshness_refresh` precedes `append`.

**Scheduling failure does not block ingestion:** patch
`schedule_rank_freshness_refresh` to raise; assert `on_created` still calls
`message_queue.append` and `load_csv_file_into_database`, that one
`dash_logger.error` is emitted, and that the exception does not propagate out of
`on_created`.

Avoid live API tests in CI. The freshness gating, monotonic save, error
classification, and Timer chaining are the new risk surface; the underlying HTTP
call is already covered by
[`test_api_service.py`](../tests/test_api_service.py).

### Verifying the score-precision assumption (offline)

The freshness test assumes the leaderboard `score` is directly comparable to the
local CSV `score` within the `0.01` tolerance. This is not unit-tested (it is a
property of KovaaK's data, not our code), but it can be checked offline against
real cached data and **should be re-checked if KovaaK's ever changes score
formatting**. Method: for each `RANKED` rank-cache entry
(`cache/leaderboard/user_rank/<user>/<id>.json` → `score`), join it with the
local high score for the same scenario (max `Score:` across that scenario's
stats CSVs) and measure `local_high - board_score`.

Observed result (445 ranked scenarios on the author's machine): 443 within
`±0.01`; the board score is consistently the local score **truncated to 2 dp**
(max shortfall `0.00999`, e.g. local `913.419861` → board `913.41`). The 2
outliers had the local score genuinely ahead of the board by `+5.1` and `+180`
— real leaderboard staleness, i.e. exactly the lag this proposal polls through,
not a precision artifact. Conclusion: the tolerance is correctly sized to one
truncation step and the assumption holds (see [Why the tolerance is
one-sided](#why-the-tolerance-is-one-sided)).

Manual end-to-end verification: copy a CSV file into the watched stats
directory with the `Score:` field manually adjusted. Setting the score above
the current local high score should trigger the polling path; the cache file
under `cache/leaderboard/user_rank/<username>/<leaderboard_id>.json` should
remain unchanged until KovaaK's API actually reflects a matching or higher
score (or until exhaustion).

## Implementation Steps

1. Add to `source/kovaaks/api_service.py`: the module constants
   (`ATTEMPT_DELAYS_SECONDS`, `SCORE_FRESHNESS_TOLERANCE`), the locks
   (`_rank_save_lock`, `_active_loops_lock`), the in-flight registry
   (`_active_rank_loops` + `_mark_loop_active` / `_mark_loop_done` /
   `_has_active_rank_loop`), and the functions `schedule_rank_freshness_refresh`,
   `_run_attempt`, `_schedule_attempt`, `_notify_exhaustion`, `_score_is_fresh`,
   `_save_rank_if_fresher`, and `_cached_rank_score`.
2. Guard **both** read-path rank-cache writes in `get_scenario_rank_info` with
   `if not _has_active_rank_loop(username, scenario_name):` — the
   cache-miss/`force_refresh` save at
   [`api_service.py:949`](../source/kovaaks/api_service.py:949) **and** the
   cache-hit `scenario_name` backfill at
   [`api_service.py:906`](../source/kovaaks/api_service.py:906). The fetched/cached
   rank is still returned for display; only the persistence is skipped.
3. Delete `refresh_scenario_rank` from `api_service.py`. Confirm it has no
   remaining callers (its only caller was the watchdog, updated in step 4).
4. In `file_watchdog.py`, rewrite `_refresh_rank_after_high_score` to take and
   thread `expected_score` (= `run_data.score`) into `schedule_rank_freshness_refresh`,
   **wrapping that call in a try/except that logs + emits one `dash_logger.error`
   and returns** (best-effort; a `Timer.start` failure must not block ingestion).
   Update the three PB call sites (new scenario; new sensitivity with new PB;
   existing scenario with new PB). **Order matters:** call
   `_refresh_rank_after_high_score(...)` *before* the `message_queue.append(...)`
   for that run, so the loop is marked active before the run is UI-visible (see
   [Call-site ordering](#call-site-ordering-mark-active-before-the-run-is-ui-visible)).
5. Remove the now-unused `rank_refresh_executor` and `_handle_rank_refresh_result`
   from `file_watchdog.py`.
6. Add unit tests for the freshness function, including the monotonic-save,
   read-path-suppression (both write sites), in-flight-counter lifecycle,
   call-site-ordering (active mark precedes the queue append),
   error-classification, and exhaustion-message cases above.
7. Smoke-test by intentionally returning stale scores from a patched
   `fetch_scenario_rank` to confirm retries fire on schedule and the cache
   stays untouched on exhaustion.

## Resolved Decisions

- The freshness loop is a new function in `api_service.py`, not a new module.
  It bypasses `get_scenario_rank_info` because it needs gated, regression-safe
  cache writes (write only on a fresh result that does not lower the cached
  score), which is the opposite of that function's unconditional write-through
  behavior.
- **The read path is arbitrated against in-flight loops, not just other loops.**
  The monotonic save only covers loop-versus-loop; the bigger hazard is the UI
  read-through (`get_scenario_rank_info`) persisting a lagging fetch right after a
  PB. A process-wide in-flight counter keyed by `(username, scenario_name)` lets
  the read path skip its own save while a freshness loop owns the scenario, so
  the loop's gated save is the sole writer during the window. This is the v6 fix
  for a hole v5 left open; see [Read-path
  arbitration](#read-path-arbitration-in-flight-loop-counter). Both read-path
  writes (cache-miss save *and* cache-hit `scenario_name` backfill) are gated, so
  no read-path write touches the rank cache while a loop is active (v7).
- **The watchdog marks the loop active before the run is UI-visible (v7).** The
  in-flight guard is only effective if `_mark_loop_active` runs before the new run
  reaches the UI. Each PB call site therefore calls `_refresh_rank_after_high_score`
  *before* `message_queue.append`, closing the race where the 1s interval callback
  could fire the read path in the gap. See [Call-site
  ordering](#call-site-ordering-mark-active-before-the-run-is-ui-visible).
- **Concurrency is handled by a monotonic conditional save, not supersession.**
  `_save_rank_if_fresher` under a process-wide lock prevents a slower
  lower-score loop from clobbering a higher score, while keeping the
  "independent, uncoordinated loops" design. This is deliberately lighter than
  cancelling/superseding pending loops.
- **Background errors never die silently.** A terminal `UnknownKovaaksUserError`
  stops the loop and notifies; transient `RequestException` (from resolve or
  fetch) retries; everything else is caught by a broad last-resort guard that
  logs and notifies. The one terminal case that is logged but **not** toasted is
  an unresolved leaderboard (`resolve_leaderboard_id` → `None`): it is the normal
  state for local/custom scenarios, so a toast would cry wolf (see [Error
  Handling](#error-handling)). This restores the all-exceptions safety the old
  executor callback provided without manufacturing false alarms.
- **Timer trade-off acknowledged honestly.** A `threading.Timer` is a sleeping
  thread; the win is keeping the long poll off the bounded executor, at the cost
  of one daemon thread per pending attempt (bounded, acceptable).
- `refresh_scenario_rank` is deleted. Its only caller (the watchdog) now uses
  `schedule_rank_freshness_refresh`. The "fetch current truth now" capability
  is preserved as `get_scenario_rank_info(force_refresh=True)`, a single line
  away for any future caller.
- Retry schedule constants live as module-level constants in `api_service.py`,
  not in `config.toml`. The user should not need to tune this.
- The watchdog passes `expected_score` at all three call sites, including the
  "new scenario" path
  ([`file_watchdog.py:95`](../source/my_watchdog/file_watchdog.py:95)). A new
  scenario is logically a PB-from-nothing.
- No "rank is being checked" notification is emitted on attempt #0. The user
  already saw the PB toast. Only terminal/unexpected failure and
  after-exhaustion are surfaced via `dash_logger.error(...)`.
- On exhaustion, `_notify_exhaustion` **always** runs a single total-play
  validation to distinguish genuine API lag from a misconfigured username, so
  the user-facing message is accurate. This is one extra call on the failure
  path only. We deliberately do *not* skip it when a RANKED result was seen
  earlier (which would prove the username valid): tracking that would mean
  threading mutable state through the fire-and-forget Timer chain, a permanent
  complexity cost to save one call on a rare path. Simplicity wins here.
- **Manual-refresh button: deferred.** Not built in this change. The 168h rank
  cache self-heals on the next view of a stale scenario (any cache miss/expiry
  triggers a fresh read-through via `get_scenario_rank_info`), and PBs already
  trigger the freshness loop. An on-demand "refresh now" button only buys
  immediacy for the niche case of wanting fresher-than-cached data without
  having set a PB — not worth the UI surface yet. If added later it can reuse
  `get_scenario_rank_info(force_refresh=True)` (no new backend function needed),
  and the [read-path arbitration](#read-path-arbitration-in-flight-loop-counter)
  already protects it: that force-refresh reaches the same guarded save at line
  949, so it is suppressed while a freshness loop is in flight and cannot regress
  a running loop's higher score.
- **Rank cache TTL: unchanged at 168h.** Kept as-is for now. Revisit only if
  real staleness complaints surface. New PBs remain the primary refresh signal,
  and that path is exactly what this proposal makes reliable.

## What's Not Changing

- `get_scenario_rank_info` keeps its read/display behavior. The *only* change is
  that **both** of its rank-cache writes — the cache-miss/`force_refresh` save and
  the cache-hit `scenario_name` backfill — now skip while a freshness loop is
  active for that scenario
  ([read-path arbitration](#read-path-arbitration-in-flight-loop-counter)). It
  still returns the fetched/cached rank for display either way; only the
  persistence is gated.
- `save_scenario_rank` itself is unchanged; the freshness path wraps it with
  `_save_rank_if_fresher` rather than modifying its unconditional behavior,
  which the read-through path still relies on.
- The 168h `scenario_rank_cache_ttl_hours` default is unchanged. New PBs
  remain the primary refresh signal.
- The
  [`_get_with_retry`](../source/kovaaks/api_service.py:113) HTTP-level retry
  is unchanged. It handles per-request 429s and transient failures; the new
  code handles cross-request eventual-consistency lag. The two are
  deliberately separate concerns.
- `ScenarioRankInfo` and other API models are unchanged. `score` is already
  populated by `fetch_scenario_rank`.
