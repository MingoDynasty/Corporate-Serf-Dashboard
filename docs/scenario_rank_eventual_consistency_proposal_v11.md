# Scenario Rank Eventual Consistency Proposal (v11)

> v11 closes a leak in v10's `allow_network=False` path. `get_scenario_rank_info`
> does network in two places *besides* the rank fetch — `resolve_leaderboard_id`
> (hydrate / `search_scenario_exact` on a mapping-cache miss) and
> `_with_leaderboard_total` (fetches a stale total) — so v10's flag would still
> leak HTTP on an interval tick. v11 makes `allow_network=False` a **dedicated
> cache-only branch** that returns *before* `resolve_leaderboard_id`, composing
> only the pure-cache readers (`get_cached_leaderboard_id`,
> `get_cached_scenario_rank`, `get_cached_leaderboard_total`): `UNKNOWN` on a hard
> miss, percentile omitted if the total isn't cached, zero HTTP. The cache-only
> test asserts zero `_session_get` calls, not just "no rank fetch."
>
> (v10 fixed two lazy-staleness + interval-polling gaps: UNRANKED self-heal, and
> splitting the rank callback by trigger so the interval tick renders cache-only.
> v9 was the big simplification: centralized monotonic write replacing the
> in-flight loop counter, the lazy staleness check, the shorter `(2,4,8,16,32)`
> schedule, and adaptive interval polling. Full deltas in git.)

## Summary

After a new local high score, the KovaaK's leaderboard endpoint can lag behind
the uploaded score — usually by a few seconds, occasionally longer. The existing
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

```python
ATTEMPT_DELAYS_SECONDS = (2, 4, 8, 16, 32)   # cumulative 2/6/14/30/62s, ~1 min
```

Five attempts, perfectly doubling, ~62s total. Rationale:

- **Dense and early.** KovaaK's usually catches up within a few seconds, so the
  bulk of the value is in the first two attempts (at 2s and 6s). A long first
  delay would just make the user wait for data that was already ready.
- **Mild exponential, no jitter.** The standard backoff-with-jitter pattern
  (AWS/Google) exists to desynchronize *many clients* and avoid a thundering
  herd. We are a *single local client* polling for eventual consistency — there
  is no herd — so jitter would be cargo-culting. The exponential *shape* still
  helps: if the board hasn't caught up by ~14s it is likely a slower case, so
  growing the gap avoids needless calls. The closest analogue is a cloud-SDK
  "waiter" (poll at short, growing intervals up to a cap), not failure-retry.
- **~1 minute cap.** Past ~60s it is almost certainly a transient network issue
  or KovaaK's being down — both rare and not a timing tweak away. A short window
  also means a *second* PB (which requires playing another ~60s run) can rarely
  land mid-retry, naturally limiting overlapping loops — though we do not rely on
  that for correctness; the centralized monotonic write handles overlap anyway.
- **62 vs 60 is noise**; the legible perfect-doubling sequence is worth 2s.

The trade-off of a short window: a genuinely slow KovaaK's update (>62s) exhausts
the loop instead of eventually succeeding. The [lazy staleness
check](#lazy-staleness-check) is the safety net that makes this safe — the next
view re-fetches because the cached score is below the local high — so an
exhaustion is self-healing rather than sticky.

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
    +-- schedule attempt #0 at now + 2s via threading.Timer
            |
            v
    on each scheduled tick (whole body wrapped in a broad guard):
        result = fetch_scenario_rank(...)
        if _score_is_fresh(result, expected_score):
            if _save_rank_monotonic(...):    # forward-only; never regress
                force-refresh leaderboard total
            done
        elif attempts_remaining > 0:
            schedule next attempt
        else:
            validate username; emit accurate dash_logger.error; preserve cache
```

The read path (`get_scenario_rank_info`) writes through the *same*
`_save_rank_monotonic`, so it can no longer clobber the cache during the window —
no coordination between the loop and the read path is needed.

### Why a new function (in `api_service.py`)

The freshness loop lives as a new function inside
[`api_service.py`](../source/kovaaks/api_service.py), alongside the low-level
pieces it composes. It is *not* a new module — there is no meaningful seam
between "fetch rank" and "poll until rank is fresh"; they share the same cache
files, the same HTTP client, and the same `resolve_leaderboard_id` mapping. A
separate module would only add an import boundary without isolating anything.

The reason it is a *separate function* rather than a flag on
[`get_scenario_rank_info`](../source/kovaaks/api_service.py:834) is **polling
behavior**, not cache-write semantics:

- `get_scenario_rank_info` is a synchronous, single "give me current truth"
  lookup: it fetches at most once and returns.
- The freshness loop must *poll over time* — schedule attempt #0, then re-check
  on a Timer chain until the board catches up or the schedule exhausts. Folding a
  multi-attempt background poll into a synchronous lookup would overload one
  function with two very different control flows.

Cache-write *gating* is no longer what separates them. In v9 both paths persist
through the same `_save_rank_monotonic` (see [Cache Write
Gating](#cache-write-gating)), so neither can regress the cache; the split is
purely "one fetch" vs. "poll until fresh."

So the new function composes the existing low-level pieces directly, bypassing
`get_scenario_rank_info` entirely:

- `fetch_scenario_rank` (HTTP fetch)
- `_save_rank_monotonic` (forward-only conditional write, shared with the read
  path)
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
that needs a synchronous fetch (e.g. a manual-refresh button, should we add one)
can call `get_scenario_rank_info(force_refresh=True)` directly — its write goes
through `_save_rank_monotonic` like every other, so it cannot regress a running
loop's higher score. Keeping a dedicated wrapper around for a hypothetical second
caller is a YAGNI trap: it would sit unused, and a future caller is one trivial
line away regardless.

This leaves two clearly distinguished rank operations:

| Operation | Function | Cache write | Returns | Use |
|---|---|---|---|---|
| Read current truth | `get_scenario_rank_info` (optionally `force_refresh=True`) | Forward-only via `_save_rank_monotonic` (never regresses the cache) | `ScenarioRankInfo` synchronously | UI lookups; any future on-demand "refresh now" |
| Poll until fresh after a PB | `schedule_rank_freshness_refresh` | Forward-only via `_save_rank_monotonic`, only on a `_score_is_fresh` result | `None` (fire-and-forget) | Watchdog post-high-score |

### Why `threading.Timer` instead of the executor

A `threading.Timer` is itself a thread that sleeps until its delay elapses, so
this choice does **not** eliminate sleeping threads — it is not free in that
sense, and the doc should not pretend otherwise. What it buys is keeping the
~1-minute poll **off the bounded `rank_refresh_executor` (`max_workers=2`)**.
If two PBs across two scenarios both entered the loop using `time.sleep(...)` on
those two worker threads, the pool would be fully occupied for the whole window
and a third scenario's refresh would queue behind them.

The cost of Timer is one daemon thread per *pending* attempt. That count is
bounded by the number of distinct scenarios producing PBs inside the ~1-minute
window — realistically a handful — and each thread is short-lived relative to
nothing useful being blocked. That is an acceptable trade.

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
case is `<number of PBs in ~1 min> × 5 attempts`, but in practice loops exit
early on attempt 1 or 2 once the API catches up. Realistic count is closer to
N+1 calls, not 5N. And because a run takes roughly as long as the whole retry
window, a second PB rarely lands while the first loop is still polling. The inner
`_get_with_retry` handles any 429 backoff that might still result.

## Cache Write Gating

This is the most important behavior difference from today's code, and in v9 it is
**one rule in one place**: every writer of the rank cache goes through
`_save_rank_monotonic`, which only ever moves a scenario's cached rank *forward*.
There is no "read path writes unconditionally" behavior left to reconcile — so
there is no in-flight counter, no call-site-ordering requirement, and no
per-writer gating sprinkled across the code (all of which v6–v8 needed).

Both writers funnel through it:

- The **freshness loop** calls it only after `_score_is_fresh` passes (it has
  already decided the fetched score is caught up). On retry exhaustion it writes
  nothing, leaving the existing cache untouched.
- The **read path** (`get_scenario_rank_info`) calls it for every fetch it would
  have persisted — the cache-miss/`force_refresh` save and the cache-hit
  `scenario_name` backfill. It still *returns* whatever it fetched for display;
  the monotonic rule only governs what gets *persisted*.

Because a rejected write never touches the file — no write, no `mtime` refresh —
a lagging read-path fetch during the freshness window can neither clobber a higher
cached score nor extend a stale entry's TTL. That is exactly the job the v6
in-flight counter did, now handled by the write rule itself.

### Centralized monotonic write

`_save_rank_monotonic` makes "a scenario's saved rank never goes backwards" hold
across **every** writer and every race. A single process-wide lock makes
read-compare-write atomic; saves are infrequent and fast (one small file write),
so a single global lock is simpler than per-leaderboard locks and has no
meaningful contention cost.

```python
_rank_save_lock = threading.Lock()


def _save_rank_monotonic(
    leaderboard_id: int,
    username: str,
    candidate: ScenarioRankInfo,
) -> bool:
    """The single rank-cache writer, shared by the read path and the loop.

    Writes `candidate` only if it is a forward move; returns True when it wrote,
    False when it preserved a better existing entry. The lock makes
    read-compare-write atomic across concurrent writers for the same leaderboard.
    """
    with _rank_save_lock:
        existing = _cached_rank(leaderboard_id, username)  # TTL-independent
        if existing is not None and not _is_forward(existing, candidate):
            return False
        save_scenario_rank(leaderboard_id, username, candidate)
        return True


def _is_forward(existing: ScenarioRankInfo, candidate: ScenarioRankInfo) -> bool:
    """True unless `candidate` would regress the cache."""
    existing_ranked = existing.status == ScenarioRankStatus.RANKED
    candidate_ranked = candidate.status == ScenarioRankStatus.RANKED
    if existing_ranked and not candidate_ranked:
        return False  # never overwrite a known rank with UNRANKED/UNKNOWN
    if candidate_ranked and not existing_ranked:
        return True   # a real rank supersedes a cached UNRANKED
    if existing_ranked and candidate_ranked:
        if existing.score is not None and candidate.score is not None:
            # Equal is allowed (idempotent re-confirm / scenario_name backfill);
            # only a strictly lower score beyond tolerance is a regression.
            return candidate.score >= existing.score - SCORE_FRESHNESS_TOLERANCE
        return True
    return True  # both non-RANKED: nothing to protect
```

`_cached_rank` reads the stored entry directly from the rank cache file
**independent of TTL** (the comparison cares about the persisted value, not its
age) — a thin read over `_read_json(_rank_cache_file(...))` returning a
`ScenarioRankInfo`, or `get_cached_scenario_rank(..., cache_ttl_hours=<effectively
unbounded>)`.

Rule rationale:

- **RANKED never regresses to UNRANKED/UNKNOWN.** KovaaK's stores a high-water
  mark; a transient UNRANKED (an API hiccup, or a lagging read right after a PB)
  must not erase a known rank. The rare genuine de-rank is acceptable to show
  briefly stale rather than flicker to "Unranked."
- **A lower RANKED score is rejected** (beyond the 2-dp tolerance) — this is the
  loop-vs-loop *and* read-vs-loop regression guard, in one comparison.
- **Equal or higher is written**, refreshing `mtime`. Equal writes are how the
  cache-hit `scenario_name` backfill persists (same score, now carrying the name)
  and how a successful loop re-confirms freshness.

The one case the rule cannot catch *at write time* is a brand-new scenario with
an *empty* cache: nothing to compare against, so a lagging read-path `UNRANKED` is
written. The freshness loop corrects it on success. If the loop exhausts before
KovaaK's catches up, that stale `UNRANKED` would otherwise sit until the 168h TTL
— so the [lazy staleness check](#lazy-staleness-check) explicitly treats a cached
`UNRANKED`-with-a-known-local-high as stale and rechecks it on the next read
(this is the v10 fix; v9's rule only covered cached RANKED and would have let the
`UNRANKED` stick).

The forced leaderboard-total refresh runs only when the save actually happened
(`_save_rank_monotonic` returned `True`). A skipped (regression-avoided) save
means a fresher writer already wrote the rank and forced its own total refresh, so
repeating it would be a wasted API call.

### Lazy staleness check

The short retry schedule means a genuinely slow KovaaK's update can exhaust the
loop, leaving a fresh-by-TTL but content-stale entry that a normal view would not
re-fetch (the 168h TTL hasn't expired). The read path closes that with a cheap
comparison: **if the cache disagrees with the known local high score, treat the
entry as stale and re-fetch**, regardless of TTL. "Disagrees" means either a
cached RANKED score below the local high, *or* a cached `UNRANKED` while a local
high exists (we have local evidence a rank should exist):

```python
def _is_lazily_stale(
    cached: ScenarioRankInfo,
    local_high_score: float | None,
) -> bool:
    if local_high_score is None:
        return False
    if cached.status == ScenarioRankStatus.RANKED:
        return (
            cached.score is not None
            and cached.score < local_high_score - SCORE_FRESHNESS_TOLERANCE
        )
    if cached.status == ScenarioRankStatus.UNRANKED:
        return True  # have a local high but the board shows no rank → recheck
    return False
```

The `UNRANKED` branch is the v10 fix for the cold-cache stick described under
[Cache Write Gating](#cache-write-gating). A genuinely-unranked-but-locally-played
scenario (e.g. played offline, never uploaded) will recheck on each user-driven
read — bounded, because the recheck only happens on user/run reads, not the
interval tick (see [UI Behavior](#ui-behavior)). If even that proves wasteful, a
`fetched_at`-age throttle is a cheap follow-up; not needed initially.

### Two read modes: `allow_network`

The lazy re-fetch only makes sense for *user-driven* reads (a scenario switch, a
new run). The 1s UI poll must **never** trigger it — otherwise every tick would
fetch in the Dash thread while the cache is below the local high. So
`get_scenario_rank_info` gains an `allow_network: bool = True` parameter:

- `allow_network=True` (dropdown / `do_update` / initial load): full behavior —
  resolve the leaderboard (may hydrate / `search_scenario_exact`), serve the cache
  hit unless `_is_lazily_stale` (else fall through and fetch), fetch on a cache
  miss, and enrich with a fresh total. The result persists via
  `_save_rank_monotonic`, which still rejects it if the board is still lagging.
- `allow_network=False` (the interval poll): a **dedicated cache-only branch that
  returns *before* `resolve_leaderboard_id`.** This matters because two parts of
  the normal flow do network *besides* the rank fetch — `resolve_leaderboard_id`
  hydrates / calls `search_scenario_exact` on a mapping-cache miss
  ([`api_service.py:877`](../source/kovaaks/api_service.py:877)), and
  `_with_leaderboard_total` fetches a stale total
  ([`api_service.py:919`](../source/kovaaks/api_service.py:919)) — so a flag
  threaded through that flow would still leak HTTP on a tick. The cache-only
  branch composes only pure-cache readers:

```python
if not allow_network:
    leaderboard_id = get_cached_leaderboard_id(scenario_name)   # mapping cache only
    if leaderboard_id is None:
        return ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN, ...)  # can't resolve w/o network
    cached = get_cached_scenario_rank(leaderboard_id, username, rank_cache_ttl_hours)
    if cached is None:
        return ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN, ...)  # nothing cached; won't fetch
    total = get_cached_leaderboard_total(leaderboard_id, leaderboard_total_cache_ttl_hours)
    if total is not None:
        cached = _with_percentile(cached.model_copy(update={"total_players": total}))
    return _with_derived_rank_warning(cached, username, steam_id)  # config-derived; no network
```

  It returns `UNKNOWN` on any hard miss (unresolved mapping or no cached rank),
  **omits the percentile** rather than fetching when the total isn't cached, and
  skips the `scenario_name` backfill write — cache-only is read-only. Net: zero
  HTTP. (`_is_lazily_stale` is not consulted here; staleness only matters when we
  *can* act on it, i.e. on `allow_network=True` reads.)

It also gains `local_high_score: float | None = None` (used only when
`allow_network=True`):

- **Passed in, not imported.** The local high comes from
  `get_high_score(scenario_name)` in
  [`data_service.py`](../source/kovaaks/data_service.py:138), but `data_service`
  already imports `api_service` one-way, so `api_service` importing it back would
  create a cycle. The `home.py` rank callback supplies the value instead.
- **Reuses `SCORE_FRESHNESS_TOLERANCE`** — the comparison is the same
  board-vs-CSV 2-dp relationship as the freshness check.

This is what makes the short schedule safe: an exhausted loop is no longer sticky.
The next user-driven view sees `cached < local_high` (or `UNRANKED` + local high),
re-fetches, and once KovaaK's has caught up `_save_rank_monotonic` persists the
fresh value — independent of the loop. Cost is bounded to user/run reads (the
interval poll never fetches), and `_save_rank_monotonic` rejects every lagging
result, so none of those fetches can corrupt the cache.

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
ATTEMPT_DELAYS_SECONDS = (2, 4, 8, 16, 32)  # cumulative 2/6/14/30/62s, ~1 min
SCORE_FRESHNESS_TOLERANCE = 0.01


def schedule_rank_freshness_refresh(
    scenario_name: str,
    username: str,
    steam_id: str | None,
    expected_score: float,
    metadata_cache_ttl_hours: int = 24,
) -> None:
    """Start a bounded score-aware rank refresh for a newly observed high score.

    Fire-and-forget: schedules attempt #0 and returns. On a fresh, non-regressing
    result it persists via _save_rank_monotonic and force-refreshes the
    leaderboard total so the displayed percentile stays pinned to KovaaK's truth.
    """
    _schedule_attempt(
        scenario_name, username, steam_id, expected_score,
        metadata_cache_ttl_hours, attempt_index=0,
    )
```

There is no loop registry to maintain: because both the loop and the read path
write through `_save_rank_monotonic`, the read path can no longer clobber the
cache during the window, so the loop does not need to announce itself as active.
(If `_schedule_attempt` raises — e.g. `Timer.start` hits the OS thread limit — it
propagates to the watchdog adapter, which swallows it; see below.)

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
    # Rank refresh is best-effort: a failure to schedule the first timer
    # (e.g. OS thread-limit on Timer.start) must not escape into the watchdog
    # thread, so swallow and log it. Call-site order vs. message_queue.append no
    # longer matters in v9 — the read path can't clobber the cache regardless —
    # so this can sit at its natural position after ingestion.
    try:
        schedule_rank_freshness_refresh(
            scenario_name,
            config.kovaaks_username,
            config.steam_id,
            expected_score,
            config.scenario_metadata_cache_ttl_hours,
        )
    except Exception:  # noqa: BLE001 — best-effort; never disrupt ingestion
        logger.exception("Failed to schedule rank refresh for %s", scenario_name)
        dash_logger.error(f"Could not start rank update for {scenario_name}.")
```

The shared `rank_refresh_executor` (`ThreadPoolExecutor(max_workers=2)`) in
`file_watchdog.py` was created solely for the single-shot post-PB refresh. With
scheduling now handled by `threading.Timer` inside the freshness function, it
has no remaining users. **Remove it** along with `_handle_rank_refresh_result`
(its all-exceptions notification is replaced by the broad guard inside
`_run_attempt`). Scheduling is no longer the watchdog's concern; it just fires
`schedule_rank_freshness_refresh` and returns.

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
            if _save_rank_monotonic(leaderboard_id, username, rank_info):
                # Force-refresh the total only when we actually wrote. Failure is
                # non-fatal: the rank save still stands.
                try:
                    _with_leaderboard_total(rank_info, leaderboard_total_cache_ttl_hours=0)
                except Exception:  # noqa: BLE001
                    logger.warning("Total refresh failed after fresh rank", exc_info=True)
            return  # success (or superseded by a fresher write); exit loop

        next_index = attempt_index + 1
        if next_index >= len(ATTEMPT_DELAYS_SECONDS):
            _notify_exhaustion(scenario_name, username, metadata_cache_ttl_hours)
            return  # exhausted; exit loop without writing cache

        _schedule_attempt(
            scenario_name, username, steam_id, expected_score,
            metadata_cache_ttl_hours, next_index,
        )
    except Exception:  # noqa: BLE001 — last-resort guard for the Timer thread
        logger.exception("Unexpected error during rank refresh for %s", scenario_name)
        dash_logger.error(f"Rank update for {scenario_name} failed unexpectedly.")
        # Do not reschedule: an unexpected error will most likely recur.


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

**Requirement.** When the user PBs, they look at the dashboard between runs and
expect to see the new rank. Showing it a few seconds late (KovaaK's eventual
consistency) is fine — that lag is outside our control. Showing it only after the
user plays *another run* is **not** acceptable.

The local high score updates immediately (it comes from the local DB on the PB's
own `do_update`). The lagging value is the *rank*, which depends on KovaaK's. So
the requirement is specifically: the rank widget must reflect the freshness loop's
cache write without waiting for the next run.

**Why today's wiring doesn't.** The rank text is rendered by
[`get_scenario_rank`](../source/pages/home.py:130), whose only inputs are the
`do_update` store and the scenario dropdown. `do_update` is **not** a periodic
tick: [`check_for_new_data`](../source/pages/home.py:85) runs on the 1s interval
but flips `do_update` only when `message_queue` holds an entry for the selected
scenario. So the widget re-renders on the next run or a scenario re-selection —
never on a plain timer. The freshness loop writes the cache in the background, but
nothing re-renders until the user acts. That is the gap to close.

**Approach: adaptive interval polling** (not SSE, not blocking).

The fix is to split the rank callback's two jobs — *render from cache* and
*refresh from network* — by which input triggered it, via `ctx.triggered_id`.

- **Add the interval as an Input.** Add `Input("interval-component", "n_intervals")`
  to [`get_scenario_rank`](../source/pages/home.py:130). The widget then re-reads
  the cache each tick and reflects the loop's background write within ~1s — no
  extra run needed.
- **The interval tick renders cache-only.** When `ctx.triggered_id` is the
  interval, call `get_scenario_rank_info(..., allow_network=False)`, whose
  dedicated cache-only branch reads only `get_cached_leaderboard_id` /
  `get_cached_scenario_rank` / `get_cached_leaderboard_total` and makes **zero
  HTTP** — not just skipping the rank fetch but also the leaderboard-id resolve and
  the total enrichment, both of which can otherwise network (see [Two read
  modes](#two-read-modes-allow_network)). A 1s poll must not do network I/O in the
  Dash thread; without this branch, the lazy-staleness path would fetch on *every*
  tick while the cache sits below the local high during the window (the v9 bug).
- **Dropdown / `do_update` triggers do the full read** (`allow_network=True`):
  these are discrete, low-frequency events (a scenario switch, or a new run ~once
  a minute), so a lazy-staleness fetch here is fine and not a hammering risk. This
  is where a stale cache (RANKED-low or stuck `UNRANKED`) heals.
- **Decouple notifications from the poll.** `get_scenario_rank` emits
  `dash_logger.warning`/`error` from `warning_message`/`error_message`
  ([home.py:152-157](../source/pages/home.py:152)). Firing those every second
  would spam toasts for users in a persistent warning/error state (e.g. Steam-ID
  mismatch), so the emission must be guarded to fire only on *change*, not every
  tick.
- **`dcc.Loading`** ([home.py:542](../source/pages/home.py:542)) still shows the
  spinner during the rare in-line fetch on a dropdown/`do_update` read; cache-only
  ticks don't spin.
- **Optional adaptive cadence.** To avoid idle polling, the interval can be
  enabled/sped up only while a freshness loop is in flight and disabled when idle
  (`dcc.Interval.disabled`/`interval` are settable from a callback). Not required
  for correctness — a per-tick cache read is cheap — but it trims idle load.

**Residual, stated honestly.** If the user passively watches one scenario after a
*rare* loop exhaustion (>62s lag) without re-selecting or playing a run, the
cache-only ticks keep showing the stale value until they act — a re-selection or
the next run triggers the lazy re-fetch. Given how rare >62s lag is, and that a
grinding user produces a `do_update` roughly every ~60s, this is an acceptable
trade for keeping the poll strictly cache-only.

**Why not SSE or full-block.** SSE has no native Dash support; it would mean a
`dash-extensions` dependency plus clientside glue — overkill for a local
single-user tool and unjustified until this is ever multi-user. A callback that
*blocks* until the eventually-consistent data arrives would hold a server thread
for the whole retry window and freeze the UI — a non-starter. Interval polling
gives the "updates organically as each piece lands" feel of SSE with none of the
infrastructure: each widget re-reads its own cache on the shared interval.

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
| API never reports the new score within ~62s | Loop exhausts; previous cache preserved. `_notify_exhaustion` validates the username, then emits "still catching up" (valid user) via `dash_logger.error`. **Not sticky:** the [lazy staleness check](#lazy-staleness-check) re-fetches on the next *user-driven* view (cached RANKED below local high, or cached `UNRANKED` with a local high), so the rank self-heals once KovaaK's catches up. The interval poll itself stays cache-only. |
| API reports `RANKED` with score *higher* than expected | Accept as fresh. `_save_rank_monotonic` writes it and the loop exits. |
| API reports `UNRANKED` | Not fresh — do not write. Continue retries. After exhaustion, `_notify_exhaustion` distinguishes lag from a misconfigured username. Previous cache preserved. |
| Multiple PBs for the same scenario in succession | Each schedules its own independent loop. `_save_rank_monotonic` prevents a slower lower-score loop from overwriting a higher score already cached by a faster one — no read-path suppression to manage. A short retry window also makes overlap rare (a second PB needs another ~60s run). |
| UI read callback (`get_scenario_rank`) fires during the freshness window | Interval-triggered ticks render cache-only (`allow_network=False`) — no fetch. A dropdown/`do_update`-triggered read may fetch the lagging value and *display* it for that render, but its write goes through `_save_rank_monotonic`, which rejects the lower/UNRANKED result — cache not clobbered, `mtime` not refreshed. No counter or coordination needed. |
| Interval tick while the cache is below the local high (mid-window) | Cache-only branch: reads only `get_cached_*` helpers — zero HTTP, including no leaderboard-id resolve and no total fetch — and serves the current cached value. The Timer loop is the only fetcher during the window; the tick just picks up whatever the loop last wrote. (This is the v9 per-tick-fetch bug, fixed; v11 closes the resolve/total leaks v10 missed.) |
| Interval tick when the rank or mapping cache is cold (e.g. first paint raced the loop) | Cache-only branch returns `UNKNOWN` (no resolve, no fetch). Harmless — the initial-load/dropdown render (`allow_network=True`) populates the caches, and `ctx.triggered_id` is `None` on initial load so that first paint networks. |
| `fetch_scenario_rank` raises `RequestException` | Treat as transient; continue retries. The inner `_get_with_retry` has already retried once at the HTTP layer. |
| `resolve_leaderboard_id` raises `UnknownKovaaksUserError` | Terminal. Stop the loop immediately; emit a "username may be misconfigured" `dash_logger.error`. No retries. |
| `resolve_leaderboard_id` raises `requests.RequestException` (e.g. `search_scenario_exact` network blip on the first-PB cold-cache path) | Transient. Treat like a failed fetch: continue retries, exhaust if it never resolves. Distinct from a resolved `None`. |
| `resolve_leaderboard_id` returns `None` | Terminal: the scenario has no leaderboard on KovaaK's (normal for local/custom scenarios). Stop the loop with a `logger.warning` only — **no `dash_logger` toast**, which would cry wolf on every PB of an unranked custom scenario. |
| Any unexpected exception inside an attempt | Caught by the broad guard. Logged with traceback; emits a generic `dash_logger.error`. Loop stops (no reschedule). |
| App shuts down mid-loop | Daemon Timers die with the process. Next app start relies on the long cache TTL until either the cache expires or a new PB triggers a new freshness refresh. Acceptable. |
| User configures `kovaaks_username = ""` mid-session | New PBs no-op the refresh path. Existing in-flight Timer chains finish under their original username — harmless. |
| Multiple scenarios in flight | Each is independent. Bounded by how many distinct scenarios produce PBs in the ~1-min window — realistically a handful of pending Timer threads. |
| Test environments without network | `fetch_scenario_rank` raises; loop retries then exhausts; `_notify_exhaustion`'s validation also fails transiently and falls back to the generic message; no cache changes. Safe. |
| Rank save succeeds but leaderboard total fetch fails | Rank cache is updated; total cache is left as-is. Displayed percentile may briefly use the previous total. Logged as a warning. Strict improvement over today's behavior. |
| `schedule_rank_freshness_refresh` raises (e.g. `Timer.start` hits the OS thread limit) | Propagates to `_refresh_rank_after_high_score`, which catches it, logs, emits one `dash_logger.error`, and returns. CSV ingestion and the PB toast proceed normally; no rank refresh runs for this PB. |
| Loop exhausts, then the user re-opens the scenario after KovaaK's caught up | The re-selection is a `allow_network=True` read; `get_scenario_rank_info` sees the cache disagrees with the local high (RANKED-low *or* stuck `UNRANKED`), re-fetches the now-fresh value, and `_save_rank_monotonic` persists it. Self-healing without a new PB. |

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
- **Monotonic write: an older/lower loop cannot overwrite a higher cached
  score.** Seed the rank cache with `score=110`; run an attempt that fetches
  `score=100` and passes freshness (`expected_score=100`); assert
  `_save_rank_monotonic` returns `False`, the cache file still reads `110`, and
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
**Centralized monotonic write (`_save_rank_monotonic` / `_is_forward`)** —
table-driven over candidate-vs-existing:

- empty cache + any candidate → writes;
- existing RANKED higher, candidate RANKED lower (beyond tolerance) → rejected;
- existing RANKED, candidate UNRANKED → rejected (never regress a known rank);
- existing UNRANKED, candidate RANKED → writes;
- equal score (within tolerance) → writes (idempotent; e.g. `scenario_name`
  backfill persists and refreshes `mtime`).

**Read path goes through the monotonic write (no clobber during the window):**
seed the cache with `score=110`; call `get_scenario_rank_info` on a path that
fetches a lagging `score=100`; assert it **returns** the fetched value for
display but the cache file still reads `110` and its `mtime` did **not** advance
(rejected write touches nothing).

**Lazy staleness check (`_is_lazily_stale` + read path), `allow_network=True`:**
- cached RANKED `score=100`, `local_high_score=110` → re-fetches;
- cached RANKED `score=100`, `local_high_score=100` (or `None`) → serves cache, no
  fetch (reuses `SCORE_FRESHNESS_TOLERANCE` at the boundary);
- **cached `UNRANKED` with `local_high_score=110` → re-fetches** (the v10 fix);
- cached `UNRANKED` with `local_high_score=None` → serves cache, no fetch.

**Interval poll is cache-only — assert ZERO HTTP (`allow_network=False`):** mock
the single HTTP chokepoint `_session_get` (or `_get_with_retry`) and assert it is
**never called** across these cases, rather than only checking `fetch_scenario_rank`
(which would miss the resolve and total-fetch leaks v10 had):
- cached value that *would* be lazily stale (RANKED below local high, or
  `UNRANKED` + local high) → serves the cached value, no HTTP;
- **mapping-cache miss** (`get_cached_leaderboard_id` returns `None`) → returns
  `UNKNOWN`, does **not** hydrate or call `search_scenario_exact`;
- **rank-cache miss** → returns `UNKNOWN`, no fetch;
- **stale/absent total cache** → returns the rank with the percentile omitted,
  does **not** call `fetch_leaderboard_total`.

Pairs with a `home.py`-level test that the interval-triggered branch passes
`allow_network=False` and the dropdown/`do_update`/initial-load branch passes
`True` (assert via `ctx.triggered_id`).

Watchdog-level tests: assert that
[`NewFileHandler.on_created`](../source/my_watchdog/file_watchdog.py) calls
`schedule_rank_freshness_refresh` with `expected_score=run_data.score` on
new-high-score paths, and not on non-PB paths.

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
   (`ATTEMPT_DELAYS_SECONDS`, `SCORE_FRESHNESS_TOLERANCE`), `_rank_save_lock`, and
   the functions `_save_rank_monotonic`, `_is_forward`, `_cached_rank`,
   `_is_lazily_stale`, `_score_is_fresh`, `schedule_rank_freshness_refresh`,
   `_run_attempt`, `_schedule_attempt`, and `_notify_exhaustion`.
2. Route the read path's writes through `_save_rank_monotonic` in
   `get_scenario_rank_info`: the cache-miss/`force_refresh` save at
   [`api_service.py:949`](../source/kovaaks/api_service.py:949) and the cache-hit
   `scenario_name` backfill at
   [`api_service.py:906`](../source/kovaaks/api_service.py:906) (in-memory
   `scenario_name` attach stays unconditional; only the write is conditional).
3. Add the lazy staleness check to `get_scenario_rank_info`: new
   `local_high_score: float | None = None` and `allow_network: bool = True`
   parameters.
   - `allow_network=False` → a **dedicated cache-only branch placed before
     `resolve_leaderboard_id`** that reads only `get_cached_leaderboard_id`,
     `get_cached_scenario_rank`, and `get_cached_leaderboard_total`: `UNKNOWN` on a
     mapping or rank miss, percentile omitted (via `_with_percentile`) when the
     total isn't cached, no backfill write, zero HTTP. It must NOT call
     `resolve_leaderboard_id` or `_with_leaderboard_total` (both can network).
   - `allow_network=True` → existing flow; a cache hit falls through to the fetch
     path when `_is_lazily_stale(cached, local_high_score)` (covers
     RANKED-below-local-high and `UNRANKED`-with-local-high).
   In `home.py`'s rank callback, pass `get_high_score(selected_scenario)` and set
   `allow_network = ctx.triggered_id != "interval-component"`.
4. Delete `refresh_scenario_rank` from `api_service.py`. Confirm it has no
   remaining callers (its only caller was the watchdog, updated in step 5).
5. In `file_watchdog.py`, rewrite `_refresh_rank_after_high_score` to take and
   thread `expected_score` (= `run_data.score`) into `schedule_rank_freshness_refresh`,
   wrapping that call in a try/except that logs + emits one `dash_logger.error`
   and returns (best-effort; a `Timer.start` failure must not escape the watchdog
   thread). Update the three PB call sites (new scenario; new sensitivity with new
   PB; existing scenario with new PB) to thread `expected_score` through. Call-site
   order vs. `message_queue.append` no longer matters.
6. Remove the now-unused `rank_refresh_executor` and `_handle_rank_refresh_result`
   from `file_watchdog.py`.
7. Add the UI polling in `home.py`: add `Input("interval-component", "n_intervals")`
   to `get_scenario_rank`; branch on `ctx.triggered_id` to pass
   `allow_network=False` for the interval tick and `True` otherwise; and guard the
   `dash_logger` warning/error emission to fire only on change (not every tick).
8. Add unit tests: `_save_rank_monotonic`/`_is_forward` rule table, read-path
   no-clobber, lazy staleness (incl. the `UNRANKED`-with-local-high branch),
   `allow_network=False` cache-only (no fetch), the `home.py` trigger-branching,
   error-classification, and exhaustion-message cases above.
9. Smoke-test by intentionally returning stale scores from a patched
   `fetch_scenario_rank` to confirm retries fire on schedule and the cache
   stays untouched on exhaustion.

## Resolved Decisions

- **One centralized monotonic write, shared by every writer (v9).** Both the UI
  read path and the freshness loop persist through `_save_rank_monotonic`, which
  only ever moves a cached rank forward (never a lower score, never
  RANKED→UNRANKED). A rejected write never touches the file, so the read path can
  no longer clobber the cache or refresh a stale entry's `mtime` during the
  window. This **replaces** the v6–v8 in-flight loop counter, its lifecycle, and
  the call-site-ordering requirement — all deleted. Concurrency (loop-vs-loop and
  read-vs-loop) collapses to one score comparison under one process-wide lock;
  deliberately lighter than supersession or a coordination registry.
- **Lazy staleness check makes the short schedule safe (v9; UNRANKED added v10).**
  The read path re-fetches when the cache disagrees with the known local high —
  a cached RANKED score below it, *or* a cached `UNRANKED` while a local high
  exists (v10; v9 covered only RANKED and would have let a cold-cache `UNRANKED`
  stick for 168h). So an exhausted loop self-heals on the next user-driven view
  rather than sitting stale. The local high is *passed in*, not imported
  (`data_service` already imports `api_service` one-way).
- The freshness loop is a separate function in `api_service.py` — not a flag on
  `get_scenario_rank_info`, not a new module. The split is **polling vs. one
  fetch**: it schedules a Timer chain and re-checks over time, which a synchronous
  lookup does not do. Cache-write gating no longer differentiates them — both use
  `_save_rank_monotonic`.
- **Schedule shortened to `(2, 4, 8, 16, 32)` (~62s, v9).** KovaaK's usually
  catches up within seconds; past ~60s it is almost certainly down or a transient
  network issue. No jitter — that pattern exists to desynchronize *many* clients,
  and we are a single local client polling for eventual consistency.
- **UI updates via adaptive interval polling, not SSE or blocking (v9; split by
  trigger v10; cache-only branch v11).** The rank widget re-reads the cache on the
  existing `dcc.Interval`, reflecting the loop's write within ~1s without waiting
  for another run. The two jobs are split by `ctx.triggered_id`: the **interval
  tick is cache-only** (`allow_network=False`), while lazy network refresh happens
  only on dropdown/`do_update` triggers. "Cache-only" is enforced by a dedicated
  branch that returns before `resolve_leaderboard_id` and reads only the
  `get_cached_*` helpers — covering *all three* network subpaths (resolve, rank
  fetch, total fetch), not just the rank fetch (v11; v10's flag still leaked HTTP
  via resolve and total enrichment). Without the split, the lazy-staleness path
  would fetch on every 1s tick while the cache sits below the local high (the v9
  bug). The warning/error emission is guarded to fire on change, not every tick.
  SSE is unjustified for a local single-user tool.
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
  cache self-heals on the next user-driven view of a stale scenario (a cache
  miss/expiry on a dropdown/`do_update` read triggers a fresh read-through via
  `get_scenario_rank_info`; interval ticks stay cache-only), and PBs already
  trigger the freshness loop. An on-demand "refresh now" button only buys
  immediacy for the niche case of wanting fresher-than-cached data without
  having set a PB — not worth the UI surface yet. If added later it can reuse
  `get_scenario_rank_info(force_refresh=True)` (no new backend function needed),
  and `_save_rank_monotonic` already protects it: that force-refresh writes
  through the same forward-only rule, so it cannot regress a running loop's higher
  score.
- **Rank cache TTL: unchanged at 168h.** Kept as-is for now. Revisit only if
  real staleness complaints surface. New PBs remain the primary refresh signal,
  and that path is exactly what this proposal makes reliable.

## What's Not Changing

- `get_scenario_rank_info` keeps its read/display behavior and still returns the
  fetched/cached rank either way. The changes are internal: its two rank-cache
  writes now go through `_save_rank_monotonic` (forward-only), and it gains
  `local_high_score` and `allow_network` parameters for the [lazy staleness
  check](#lazy-staleness-check) (the latter lets the interval poll stay
  cache-only).
- `save_scenario_rank` itself is unchanged (it still does the unconditional file
  write); `_save_rank_monotonic` wraps it with the forward-only check that every
  writer now goes through.
- The 168h `scenario_rank_cache_ttl_hours` default is unchanged. New PBs
  remain the primary refresh signal.
- The
  [`_get_with_retry`](../source/kovaaks/api_service.py:113) HTTP-level retry
  is unchanged. It handles per-request 429s and transient failures; the new
  code handles cross-request eventual-consistency lag. The two are
  deliberately separate concerns.
- `ScenarioRankInfo` and other API models are unchanged. `score` is already
  populated by `fetch_scenario_rank`.
