# Scenario Rank Eventual Consistency Proposal

> **Status:** in review (v21) — verified against code, build-ready. This round folds in
> the deep correctness pass: **P1-A** an explicit Refresh can now clear a genuine de-rank
> (`allow_derank=force_refresh`) instead of it persisting forever; **P1-B** the cache-only
> interval read attaches the total via `get_cached_leaderboard_total` (not
> `_with_leaderboard_total`, which fetched on a total-cache miss → a per-tick GET); the
> v19 equal-score recency tie-break is **cut** (over-engineered); `_notify_exhaustion`
> drops the username-validation call and adds a free score-precision-drift diagnostic;
> the rollout is relaxed to two PRs. The register below is the review anchor; earlier
> revision history lives in git log.

## Requirements, Non-Goals, and Accepted Tradeoffs

The stable anchor — reviews and implementation are *against this*. A new finding should
either fit here or argue to change it, not silently re-derive it.

**Requirements (must be true):**
- **R1** — After a local PB, the displayed rank reflects the new score without replaying a run. Seconds of lag is fine; "only after another run" is not.
- **R2** — The cached rank never regresses to a *lower score*, and never flickers to UNRANKED from *automatic* paths (loop / interval / backfill). An explicit Refresh **may** clear a genuine de-rank (P1-A).
- **R3** — A single unlucky eventual-consistency timing must not cache stale/UNRANKED data for the full 168h TTL.
- **R4** — Background-refresh errors never die silently: terminal errors notify, transient errors retry, unexpected errors are caught.
- **R5** — The interval poll makes *zero* network calls per tick — for unresolved scenarios *and* expired rank/total caches.
- **R6** — Concurrent refreshes (loop-vs-loop, read-vs-loop) cannot corrupt the cache.

**Non-goals (explicitly not solving):**
- **N1** — Real-time/push (SSE). Interval polling suffices for a local single-user tool.
- **N2** — Auto-healing a *permanently* divergent cache (offline play / server down at PB time). That's the manual Refresh button's job, not an automatic recheck.
- **N3** — Sub-second rank-*number* accuracy at equal score (the cut v19 tie-break). Rank is a drifting snapshot.
- **N4** — Multi-user correctness or scaling.
- **N5** — Tuning the retry schedule via config; it's a module constant.

**Accepted tradeoffs (owned consequences):**
- **T1** — A KovaaK's update slower than ~62s exhausts the loop; the rank stays stale until the next PB / manual Refresh / TTL. We accept this over auto-rechecking.
- **T2** — During the freshness window a non-interval read may *fetch* a lagging value, but the cache won't regress and a fetched-worse *score* is never shown. (A fetch *exception* on such a read can still show N/A — it bypasses the monotonic write.)
- **T3** — Dense grinding (multiple PBs/min) costs extra API calls (~N+1), bounded by the retry window.
- **T4** — One daemon Timer thread per pending attempt (bounded, acceptable).
- **T5** — `board == floor2(local)` is single-sourced (445 scenarios, one machine). Mitigated by the exhaustion drift diagnostic (P2-C), not eliminated.
- **T6** — Each interval tick: 3 cache file reads + JSON parses under `_CACHE_IO_LOCK` — single-digit ms, not zero.

## Summary

After a new local high score, the KovaaK's leaderboard endpoint can lag behind
the uploaded score — usually by a few seconds, occasionally longer. The existing
background refresh path
([`_refresh_rank_after_high_score`](../source/my_watchdog/file_watchdog.py)) fires
exactly once, so a single unlucky timing can cache stale or `UNRANKED` data
until the long `scenario_rank_cache_ttl_hours` (default 168h) expires.

The fix is to convert that single-shot refresh into a **bounded score-aware
poll**: keep refreshing until the returned leaderboard `score` reaches the local
high score's 2-dp leaderboard value (KovaaK's truncates board scores to 2 dp, so
that floored value — not the full-precision local score — is the reachable target),
with a hard ceiling on attempts. Cache writes are gated on
freshness *and* guarded against regression, and the background scheduler never
lets an error die silently.

## Current Code Path

Refresh on high score today:

1. [`NewFileHandler.on_created`](../source/my_watchdog/file_watchdog.py) sees a
   CSV file, detects a new high score.
2. [`_refresh_rank_after_high_score`](../source/my_watchdog/file_watchdog.py)
   submits `refresh_scenario_rank` to a shared `ThreadPoolExecutor(max_workers=2)`.
3. [`refresh_scenario_rank`](../source/kovaaks/api_service.py) calls
   [`get_scenario_rank_info`](../source/kovaaks/api_service.py) with
   `force_refresh=True`.
4. `get_scenario_rank_info` calls
   [`fetch_scenario_rank`](../source/kovaaks/api_service.py), then
   unconditionally calls
   [`save_scenario_rank`](../source/kovaaks/api_service.py) and
   `save_leaderboard_total`.

Steps 3 and 4 are the problem. They run exactly once, and step 4 has no concept
of "the returned data might be stale" — whatever comes back from KovaaK's wins
and is persisted for 168 hours.

## Freshness Condition

The right test is the returned `score`, not the rank number:

```python
SCORE_EPSILON = 1e-6  # float round-trip noise only — NOT a one-cent tolerance


def _floor_2dp(value: float) -> float:
    """Truncate to 2 dp the way KovaaK's truncates leaderboard scores.

    Decimal, not ``math.floor(value * 100) / 100`` — the float multiply mis-floors
    boundary values (e.g. ``913.42 * 100 == 91341.99999...`` would floor to 913.41).
    """
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_FLOOR))


def _score_is_fresh(rank_info: ScenarioRankInfo, expected_score: float) -> bool:
    return (
        rank_info.status == ScenarioRankStatus.RANKED
        and rank_info.score is not None
        and rank_info.score >= _floor_2dp(expected_score) - SCORE_EPSILON
    )
```

Why score-based, not rank-based:

- The user's rank can stay the same after a PB if the score doesn't pass
  another player. Rank-equality is therefore not a freshness signal.
- `RankingPlayer.score` from
  [`/leaderboard/scores/global`](../source/kovaaks/api_service.py) is
  exactly what `fetch_scenario_rank` already captures into
  `ScenarioRankInfo.score`
  ([`api_service.py`](../source/kovaaks/api_service.py)).
  No new endpoint or model work needed.

### Why we floor the local score (instead of subtracting a tolerance)

The board does not report the local score exactly: KovaaK's **truncates leaderboard
scores to two decimal places**. So a fully caught-up board sits *marginally below*
the local CSV value by up to (just under) one hundredth — e.g. local `913.419861`
is reported as `913.41`, never `913.42`. Verified empirically against real data (see
[Testing](#testing)): across 445 of the user's ranked scenarios the board score is
the local score truncated to 2 dp, with a maximum observed shortfall of `0.00999`.

The freshness test is therefore "has the board reached the local score's 2-dp
floor?" — `board >= floor2(expected)`.

**v17 fix (P1).** Earlier drafts wrote this as `board >= expected - 0.01`,
subtracting a one-cent `SCORE_FRESHNESS_TOLERANCE` to absorb the truncation. That
subtractive form is too lenient by up to a full cent: it accepts `board == expected
- 0.01`, which is a *stale* one-cent-lower board value whenever `expected` lands
exactly on a 2-dp boundary (shortfall `== 0`). Concretely, a scenario that scores
`100.00` flat has a caught-up board of `100.00`, but `expected - 0.01 == 99.99` —
a previous, stale board value — would pass. The loop would then stop early and cache
a stale rank: exactly the failure this proposal exists to prevent. (Rare, because
most local scores are full-precision floats like `913.419861`; but real, and it
defeats the loop when it hits.)

Flooring the **local** side to the board's own resolution fixes it exactly: the
truncation is modeled where it actually happens (the board), not approximated by a
blanket subtraction. `floor2(expected)` *is* the caught-up value, so a caught-up
board passes and the largest stale value (`floor2(expected) - 0.01`) is rejected,
with **no** poll-to-exhaustion risk — a genuinely caught-up board always equals
`floor2(expected)`. The only slack left is `SCORE_EPSILON` (`1e-6`), which absorbs
pure float round-trip noise (magnitudes here are ~1e-10), **not** a hundredth. This
retires `SCORE_FRESHNESS_TOLERANCE` entirely: that one-cent constant conflated
truncation with float noise, and reusing it for cache monotonicity caused a second
bug (see [Centralized monotonic write](#centralized-monotonic-write)).

A score **higher** than expected must always be accepted, so the upper bound
stays open:

- KovaaK's stores a player's *personal best* on a leaderboard, and
  `fetch_scenario_rank` filters to the exact matched player by Steam ID /
  username ([`api_service.py`](../source/kovaaks/api_service.py)). So
  `rank_info.score` is definitively the user's own high-water mark — never
  another player's.
- A higher server score therefore means the user has a better score on
  KovaaK's than the local CSV reflects (e.g. played on another machine, or the
  local DB is missing a run). It still satisfies the guarantee we care about:
  *the leaderboard now reflects at least the new high score.* The rank and
  percentile we read are valid to display.

A symmetric `±` band would add an upper rejection, causing the loop to keep
polling past a perfectly valid (higher) result and potentially exhaust all
attempts without ever writing the cache. The asymmetry is the point: floored at the
board's 2-dp resolution below, unbounded above (a higher PB is more than caught up).

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
the loop instead of eventually succeeding, leaving the rank stale until the next
PB, the 168h TTL, or a user-clicked [Refresh](#when-the-cache-stays-stale-the-manual-refresh-button).
We accept that rather than auto-rechecking, which would hammer the API for scores
that never reach KovaaK's at all (offline play / server down) — see that section.

Each attempt makes one `fetch_scenario_rank` call. The inner
[`_get_with_retry`](../source/kovaaks/api_service.py) already handles 429s
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
            _, wrote = _save_rank_monotonic(...)   # forward-only; never regress
            if wrote:
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
[`get_scenario_rank_info`](../source/kovaaks/api_service.py) is **polling
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
[`refresh_scenario_rank`](../source/kovaaks/api_service.py) (which is just
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
  `scenario_name` backfill. It returns the **winner** `_save_rank_monotonic` reports
  (the persisted value, never a rejected lower/UNRANKED fetch), so the *display* is
  forward-only too — not just what gets *persisted*.

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
    allow_derank: bool = False,
) -> tuple[ScenarioRankInfo, bool]:
    """The single rank-cache writer, shared by the read path and the loop.

    Returns `(winner, wrote)`. `winner` is the value now authoritative for the cache
    — `candidate` if it was a forward move, else the preserved existing entry — so a
    caller can DISPLAY a value that never regresses, not just persist one. `wrote` is
    True iff the file was written. `allow_derank` (set only on a user-clicked Refresh /
    `force_refresh`) permits the one regression automatic paths forbid — RANKED→UNRANKED
    — so an explicit refresh can clear a genuine de-rank instead of it persisting
    forever (v21). The lock makes read-compare-write atomic across concurrent writers
    for the same leaderboard.
    """
    with _rank_save_lock:
        existing = _cached_rank(leaderboard_id, username)  # TTL-independent
        if existing is not None and not _is_forward(existing, candidate, allow_derank):
            return existing, False  # preserve & surface the better entry, not candidate
        save_scenario_rank(leaderboard_id, username, candidate)
        return candidate, True


def _is_forward(
    existing: ScenarioRankInfo,
    candidate: ScenarioRankInfo,
    allow_derank: bool = False,
) -> bool:
    """True unless `candidate` would regress the cache."""
    existing_ranked = existing.status == ScenarioRankStatus.RANKED
    candidate_ranked = candidate.status == ScenarioRankStatus.RANKED
    if existing_ranked and not candidate_ranked:
        # Automatic paths never drop a known rank to UNRANKED/UNKNOWN (this absorbs the
        # common transient-UNRANKED flicker). An explicit user Refresh may, so a genuine
        # de-rank can be cleared on demand instead of persisting forever (v21).
        return allow_derank
    if candidate_ranked and not existing_ranked:
        return True   # a real rank supersedes a cached UNRANKED
    if existing_ranked and candidate_ranked:
        if existing.score is None:
            return True   # nothing scored to protect; take the candidate
        if candidate.score is None:
            return False  # never drop a known score to a scoreless RANKED (a fetch never makes one)
        # Both are BOARD scores (already 2-dp-truncated by KovaaK's): equal-or-higher
        # writes, strictly-lower is rejected. SCORE_EPSILON is float-noise slack only —
        # NOT the one-cent SCORE_FRESHNESS_TOLERANCE, which would let a stale 99.99
        # overwrite a cached 100.00 (v17 fix, P1). Equal score writes regardless of
        # rank-number drift — that 1–2 position staleness is a non-goal (the v19 recency
        # tie-break was cut in v21; see Resolved Decisions).
        return candidate.score >= existing.score - SCORE_EPSILON
    return True  # both non-RANKED: nothing to protect
```

`_cached_rank` reads the stored entry directly from the rank cache file
**independent of TTL** (the comparison cares about the persisted value, not its
age) — a thin **direct** read over `_read_json(_rank_cache_file(...))` returning a
`ScenarioRankInfo`. Prefer the direct read over `get_cached_scenario_rank` with a huge
`cache_ttl_hours`: that reuses a "fresh-only" function and leans on `timedelta` not
overflowing, whereas a direct read matches the stated intent (cares about the value,
not its age).

Rule rationale:

- **RANKED never regresses to UNRANKED/UNKNOWN on automatic paths.** KovaaK's stores
  a high-water mark; a transient UNRANKED (an API hiccup, or a lagging read right after
  a PB) must not erase a known rank. The one case this masks is a *genuine* de-rank
  (KovaaK's resets/purges a leaderboard) — so an explicit Refresh clears it on demand
  (`allow_derank=True`) rather than leaving it stale forever (v21). Automatic paths stay
  flicker-free; the user's explicit "fetch current truth" is authoritative.
- **A lower RANKED score is rejected** (any decrease beyond `SCORE_EPSILON` float
  noise — *not* a one-cent tolerance, since both scores are already-truncated board
  values) — this is the loop-vs-loop *and* read-vs-loop regression guard, in one
  comparison.
- **A scoreless RANKED candidate is rejected when the existing entry has a score.**
  `ScenarioRankInfo.score` is optional, so a RANKED entry *can* carry `score=None`.
  No current writer produces that shape against a scored entry (`fetch_scenario_rank`
  always sets a score on RANKED, and the `scenario_name` backfill re-saves the same
  entry), but the model permits it, so the central monotonic-write invariant handles
  it explicitly rather than trusting every present and future caller. (Symmetric case:
  a scored candidate over a scoreless existing entry is a forward move and is written.)
- **Equal or higher is written**, refreshing `mtime`. Equal writes are how the
  cache-hit `scenario_name` backfill persists (same score, now carrying the name) and
  how a successful loop re-confirms freshness. At equal score the last writer wins on
  the rank *number*; that 1–2 position staleness in a sub-second race self-heals and is
  a non-goal (the v19 `fetched_at` tie-break was cut in v21 — see Resolved Decisions).

The one case the rule cannot catch *at write time* is a brand-new scenario with
an *empty* cache: nothing to compare against, so a lagging read-path `UNRANKED` is
written. The freshness loop corrects it on success. If the loop exhausts before
KovaaK's catches up, that `UNRANKED` (or any stale rank) persists until one of:
the next PB on that scenario (which schedules a new loop), the 168h TTL expiring
(the next non-interval view then re-fetches — interval ticks read TTL-independently),
or the user clicking [Refresh](#when-the-cache-stays-stale-the-manual-refresh-button).
We deliberately do **not** auto-recheck on every view — see that section for why.

The forced leaderboard-total refresh runs only when the save actually happened
(`_save_rank_monotonic` reported `wrote=True`). A skipped (regression-avoided) save
means a fresher writer already wrote the rank and forced its own total refresh, so
repeating it would be a wasted API call.

### When the cache stays stale: the manual refresh button

The short schedule means a genuinely slow KovaaK's update can exhaust the loop,
leaving a fresh-by-TTL but content-stale entry. Earlier drafts (v9–v11) healed
this with a **lazy staleness check** — the read path compared the cached score
against the local high and auto-re-fetched when `cached < local_high`. v12 removes
that, because the comparison cannot distinguish *temporary* lag from *permanent*
divergence:

- The user plays **offline** and never uploads — the score never reaches KovaaK's.
- KovaaK's is **down** at PB time — that specific score never lands on the board.

In both cases `cached < local_high` is true **forever**, so a lazy check would
re-fetch on *every* view of that scenario, indefinitely — hammering the API for
scenarios where re-fetching can never help (the board will never catch up). And it
gains nothing even when it does fetch: it just re-reads the same stale board value
and displays it. So the auto-recheck pays a permanent cost to heal only the rare
"temporary lag exceeded the 62s window" case.

Instead, **the user gets a Refresh button** next to the rank widget. If they
suspect the displayed rank is stale, they click it; otherwise nothing re-fetches.
This caps API calls to moments the user actually wants fresh data, and naturally
does the right thing for the divergent cases (the user clicks once, sees the rank
is unchanged, and stops).

```python
@callback(
    Output("scenario_rank", "children", allow_duplicate=True),
    Input("rank-refresh-button", "n_clicks"),
    State("scenario-dropdown-selection", "value"),
    prevent_initial_call=True,
)
def refresh_rank(_, selected_scenario):
    # One-shot "fetch current truth now"; force_refresh threads allow_derank=True into
    # _save_rank_monotonic. A lower *score* is still rejected (display stays
    # score-monotonic, the winner is returned), but a genuine de-rank (RANKED→UNRANKED)
    # IS written and shown — clearing a stale rank on demand is this button's job (v21).
    # Not a freshness loop — by the time a user clicks the board has usually settled; a
    # transient UNRANKED self-heals on the next click / loop / PB.
    if not selected_scenario:
        return "N/A"
    try:
        rank_info = get_scenario_rank_info(
            selected_scenario, config.kovaaks_username, config.steam_id,
            config.scenario_metadata_cache_ttl_hours,
            config.scenario_rank_cache_ttl_hours,
            config.leaderboard_total_cache_ttl_hours,
            force_refresh=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Manual rank refresh failed for %s", selected_scenario)
        dash_logger.error(f"Rank refresh for {selected_scenario} failed.")
        return "N/A"
    # A user-initiated refresh ALWAYS surfaces warning/error state (the user just
    # asked). This is deliberately NOT the change-gated emission the interval poll
    # uses — a persistent bad-username/Steam-ID error must still toast on click, or
    # a forced-lookup failure quietly becomes a bare "N/A".
    _emit_rank_messages(rank_info)
    return format_scenario_rank(rank_info)
```

`_emit_rank_messages` is the shared helper extracted from today's inline block in
`get_scenario_rank` ([home.py](../source/pages/home.py)):

```python
def _emit_rank_messages(rank_info: ScenarioRankInfo) -> None:
    if rank_info.warning_message:
        logger.warning("Scenario rank warning: %s", rank_info.warning_message)
        dash_logger.warning(rank_info.warning_message)
    if rank_info.error_message:
        logger.warning("Scenario rank unavailable: %s", rank_info.error_message)
        dash_logger.error(rank_info.error_message)
```

This pairs with the exhaustion notification (see [Error Handling](#error-handling)):
when the loop times out, the toast can say "…couldn't confirm the new rank — click
Refresh to retry," so the button is discoverable exactly when it's useful.

What we give up: after a *rare* loop exhaustion where the board later catches up,
the rank no longer auto-heals — the user clicks Refresh (or it heals on their next
PB, or at the 168h TTL). Given how rare >62s lag is, that is well worth not
hammering the divergent cases. (This deletes the *lazy-staleness* /
`local_high_score` fetching v10–v11 added — **not** the cache-only read itself; the
narrowed `allow_network=False` interval path remains, see [UI Behavior](#ui-behavior).)

### Leaderboard Total Refresh

On every successful freshness save, also force a fresh fetch of the
leaderboard total — bypassing its normal `leaderboard_total_cache_ttl_hours`
TTL — and overwrite
[`leaderboard/totals/{leaderboard_id}.json`](../source/kovaaks/api_service.py).

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
[`_with_leaderboard_total`](../source/kovaaks/api_service.py) inside the
freshness path. That bypasses the cache freshness check and triggers
[`fetch_leaderboard_total`](../source/kovaaks/api_service.py) +
[`save_leaderboard_total`](../source/kovaaks/api_service.py).

The freshness function does not expose the total TTL as a parameter — it always
forces a refresh on a successful save. Callers (e.g. the watchdog) don't need to
thread `config.leaderboard_total_cache_ttl_hours` through to the freshness path.

If the total fetch itself fails (transient API failure), the rank save still
succeeds. The user sees the new rank without an updated total/percentile until
the next normal lookup refreshes the total. This matches today's degradation, which
is correct: `get_scenario_rank_info` already saves the rank *before* total
enrichment ([api_service.py](../source/kovaaks/api_service.py)) and
`_with_leaderboard_total` degrades on a request failure without raising, so the rank
persists regardless of the total. The value the forced refresh adds is *percentile
accuracy* (pinning the total to KovaaK's truth on a PB), not rank persistence —
which was never at risk.

## Error Handling

The background loop must never let an error vanish. Today's executor path wraps
every refresh in [`_handle_rank_refresh_result`](../source/my_watchdog/file_watchdog.py),
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
  [`resolve_leaderboard_id`](../source/kovaaks/api_service.py) (it can
  propagate from the total-play hydration path; `get_scenario_rank_info` already
  wraps it at [`api_service.py`](../source/kovaaks/api_service.py)), and
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
SCORE_EPSILON = 1e-6  # float round-trip noise only (see Freshness Condition)


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

### Cache-only read: the `allow_network` parameter (v13)

`get_scenario_rank_info` regains `allow_network: bool = True`. When `False`, the
read does **no network** at all — it resolves and serves entirely from cache, or
returns N/A. This is the single seam the interval poll needs (see [UI
Behavior](#ui-behavior) for why a plain read is not cache-only for unresolved
scenarios). Two call sites change:

- `resolve_leaderboard_id` gains a matching `allow_network: bool = True`. When
  `False` it consults only `get_cached_leaderboard_id` and returns `None` on a
  miss — it skips both the total-play hydration fetch and `search_scenario_exact`.
- `get_scenario_rank_info`, when `allow_network=False`, threads it into
  `resolve_leaderboard_id`, then takes the existing cached-rank branch
  ([api_service.py](../source/kovaaks/api_service.py)) but **does not fall
  through to `fetch_scenario_rank` on a miss** — it returns the UNKNOWN/N/A state
  instead. It reads the rank cache **TTL-independently** (v20): a cache-only read
  can't refresh, so TTL-gating it would only degrade a still-displayed rank to N/A on
  a long-idle page; serving the last-known value keeps the interval poll a passive
  mirror, while re-fetch-on-expiry stays the job of the non-interval (TTL-gated) reads.
  The total is attached cache-only too: `allow_network=False` must **not** route
  through `_with_leaderboard_total` (it calls `get_leaderboard_total`, which fetches +
  saves on a cache miss — [api_service.py](../source/kovaaks/api_service.py)). Use
  `get_cached_leaderboard_total` + `_with_percentile` directly, so a resolved scenario
  whose total cache has expired does **not** fire a leaderboard GET every tick (P1-B).

`force_refresh=True` and `allow_network=False` are mutually exclusive in practice
(force-refresh means "fetch now"); the manual refresh uses `force_refresh=True`,
the interval poll uses `allow_network=False`. No caller sets both.

Called from
[`_refresh_rank_after_high_score`](../source/my_watchdog/file_watchdog.py),
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
        except requests.RequestException as exc:
            # Transient: resolve_leaderboard_id swallows its own hydration
            # RequestExceptions, but search_scenario_exact (the cold-cache,
            # first-PB path) can still raise. Fall through to the retry tail
            # rather than letting the broad guard kill the loop. Summarize the
            # request failure (no traceback) — it is expected and retryable — to
            # match the api_service convention (request_exception_summary).
            logger.warning(
                "Transient failure resolving leaderboard for %s; will retry: %s",
                scenario_name, request_exception_summary(exc),
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
            _, wrote = _save_rank_monotonic(leaderboard_id, username, rank_info)
            if wrote:
                # Force-refresh the total only when we actually wrote. Failure is
                # non-fatal: the rank save still stands.
                try:
                    _with_leaderboard_total(rank_info, leaderboard_total_cache_ttl_hours=0)
                except Exception:  # noqa: BLE001
                    logger.warning("Total refresh failed after fresh rank", exc_info=True)
            return  # success (or superseded by a fresher write); exit loop

        next_index = attempt_index + 1
        if next_index >= len(ATTEMPT_DELAYS_SECONDS):
            _notify_exhaustion(scenario_name, expected_score, rank_info)
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
    scenario_name: str, expected_score: float, last_rank_info: ScenarioRankInfo | None,
) -> None:
    logger.warning("Rank freshness refresh exhausted for %s", scenario_name)
    # Precision-drift diagnostic (v21): board==floor2(local) is a single-sourced
    # assumption. If the last fetch was RANKED but sat *below* floor2(expected), the
    # board may have drifted under our model (e.g. KovaaK's changed score formatting) —
    # which would make EVERY PB exhaust. Flag that distinctly so a systemic break is
    # diagnosable rather than looking like ordinary lag. Free: just the score we
    # already fetched, no extra call.
    if (
        last_rank_info is not None
        and last_rank_info.status == ScenarioRankStatus.RANKED
        and last_rank_info.score is not None
        and last_rank_info.score < _floor_2dp(expected_score) - SCORE_EPSILON
    ):
        logger.warning(
            "Possible score-precision drift for %s: board %.4f < floor2(%.6f). "
            "If this recurs on every PB, the board==floor2(local) assumption is stale.",
            scenario_name, last_rank_info.score, expected_score,
        )
    # Single generic toast. The extra username-validation call was cut in v21 — a
    # misconfigured username is already caught terminally at resolution in the common
    # case (see Resolved Decisions).
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
[`get_scenario_rank`](../source/pages/home.py), whose only inputs are the
`do_update` store and the scenario dropdown. `do_update` is **not** a periodic
tick: [`check_for_new_data`](../source/pages/home.py) runs on the 1s interval
but flips `do_update` only when `message_queue` holds an entry for the selected
scenario. So the widget re-renders on the next run or a scenario re-selection —
never on a plain timer. The freshness loop writes the cache in the background, but
nothing re-renders until the user acts. That is the gap to close.

**Approach: interval polling (cache-only) + a manual refresh** (not SSE, not
blocking).

- **Add the interval as an Input.** Add `Input("interval-component", "n_intervals")`
  to [`get_scenario_rank`](../source/pages/home.py). The widget re-reads the
  cache each tick and reflects the loop's background write within ~1s — no extra
  run needed. Surfacing what the loop wrote is the poll's *only* job.
- **The interval read must be cache-only — and that needs a flag (v13 correction).**
  v12 claimed a plain read on a tick is "a cache hit with no network." That holds
  for a *resolved* scenario (its mapping, rank, and total caches were populated by
  the selection read) but **fails for any scenario without a KovaaK's leaderboard**.
  `get_scenario_rank_info` resolves the leaderboard id *before* it can read the
  rank cache (the rank cache is keyed by id — see [api_service.py](../source/kovaaks/api_service.py)),
  and an unresolved scenario
  has no cached mapping and **no negative cache** (`save_leaderboard_id` is only
  written on an exact match — [api_service.py](../source/kovaaks/api_service.py)).
  So `resolve_leaderboard_id` falls through to `search_scenario_exact`, a network
  GET, on *every* call. With `polling_interval = 1000`, sitting on a custom
  scenario would fire one `/scenario/popular` request **per second** — wasteful and
  a 429 risk. The fix is a **cache-only read on interval-triggered invocations**:

  ```python
  from dash import ctx

  _INTERVAL_PROP = "interval-component.n_intervals"


  def _rank_allows_network(triggered: list[dict]) -> bool:
      """True unless the 1s interval is the SOLE trigger.

      A selection / do_update (real user or data event) resolves + fetches as today.
      On initial load Dash sets `triggered` to the "." sentinel (!= the interval), so a
      persisted selection still fetches; if a selection co-fires with a tick, that
      prop_id keeps this True. Deliberately NOT ctx.triggered_id, which collapses to a
      single id and would drop the co-fire and initial-load cases. Pure and ctx-free so
      tests can call it with crafted `triggered` lists (no callback context needed).
      """
      return any(t["prop_id"] != _INTERVAL_PROP for t in triggered)


  def _render_scenario_rank(selected_scenario, allow_network: bool) -> str:
      # ctx-free body: tests drive it with an explicit allow_network (no Dash context).
      if not selected_scenario:
          return "N/A"
      try:
          rank_info = get_scenario_rank_info(
              selected_scenario, config.kovaaks_username, config.steam_id,
              config.scenario_metadata_cache_ttl_hours,
              config.scenario_rank_cache_ttl_hours,
              config.leaderboard_total_cache_ttl_hours,
              allow_network=allow_network,
          )
      except Exception:  # noqa: BLE001
          logger.exception("Failed to fetch scenario rank for %s", selected_scenario)
          return "N/A"
      if allow_network:           # see emission policy below
          _emit_rank_messages(rank_info)
      return format_scenario_rank(rank_info)


  @callback(
      Output("scenario_rank", "children"),
      Input("do_update", "data"),
      Input("scenario-dropdown-selection", "value"),
      Input("interval-component", "n_intervals"),
  )
  def get_scenario_rank(_do_update, selected_scenario, _n) -> str:
      # Thin shell: read ctx only here, delegate to the ctx-free body.
      return _render_scenario_rank(selected_scenario, _rank_allows_network(ctx.triggered))
  ```

  `allow_network=False` makes the read **resolve-from-cache-only and
  fetch-nothing**: `resolve_leaderboard_id` skips hydration and
  `search_scenario_exact`; on a miss it returns `None` → N/A. The rank read is
  `get_cached_scenario_rank` read **TTL-independently** (v20) — a passive interval
  mirror can't refresh, so it serves the last-known rank rather than degrading to N/A
  once the 168h TTL lapses on a long-idle page; the total is attached via
  `get_cached_leaderboard_total` + `_with_percentile` directly — **not**
  `_with_leaderboard_total`, which fetches on a total-cache miss (P1-B). This is the
  same `allow_network` tool v10/v11
  had, kept for a *different and still-valid* reason (resolution avoidance), which
  is why v12's deletion was wrong. The freshness loop only ever runs for *resolved*
  scenarios, so the interval poll never has a background write to surface for an
  unresolved one — making a cache-only tick exactly right, never lossy.
- **Manual refresh button.** A Refresh button beside the rank lets the user force a
  one-shot `get_scenario_rank_info(force_refresh=True)` when they suspect staleness
  (see [the manual refresh button](#when-the-cache-stays-stale-the-manual-refresh-button)).
  This — not an automatic recheck — is how a post-exhaustion or divergent cache
  gets re-pulled, so the app never hammers the API on the user's behalf.
- **Notification emission policy (v13).** `get_scenario_rank` emits
  `dash_logger.warning`/`error` from `warning_message`/`error_message`
  ([home.py](../source/pages/home.py)). Firing those every second would
  spam toasts for users in a persistent warning/error state (e.g. Steam-ID
  mismatch). v13 realizes "fire on change, not every tick" as: **emit only on
  non-interval triggers** (selection, `do_update`) and on the manual refresh; stay
  silent on interval ticks. This is principled, not a hack — a cache-only tick does
  not fetch, so it produces no *new* warning/error condition; the only message it
  could re-derive is the cached Steam-ID-mismatch warning, which the user already
  saw on selection. The shared `_emit_rank_messages` helper is reused by the manual
  refresh, which (unlike the poll) emits **un**gated because it is user-initiated.
- **`dcc.Loading` + `delay_show` (v14 correction).** The rank text stays wrapped in
  `dcc.Loading` ([home.py](../source/pages/home.py)). Note that
  `dcc.Loading` keys off whether the wrapped output's callback is **in flight**, not
  off network I/O — so once the 1s interval is an input to `get_scenario_rank`, the
  child enters loading state *every tick*, even on a pure cache read, and would
  flicker the spinner once per second. The fix is **`delay_show`** (≈250–500ms) on
  this `dcc.Loading`: a localhost cache read returns in single-digit ms, well under
  the threshold, so the spinner never shows on cache-only ticks, while a genuine
  fetch (selection cache-miss / manual Refresh) outruns the delay and still shows
  it. (`delay_hide` is a secondary guard against a too-brief flash.) So the accurate
  claim is "spinner suppressed on fast cache-only ticks via `delay_show`," not
  "structurally no spinner."
  - *Optional* `no_update` short-circuit: even suppressed, the callback still
    re-runs every tick and re-writes identical `children`. Returning `no_update`
    when the formatted string is unchanged would skip the rewrite, but it needs the
    previous value threaded in (a `State`/store) — a minor tidy, not required. Flag,
    don't build, unless profiling says it matters.
- **Optional adaptive cadence.** To trim idle load the interval can be enabled/sped
  up only while a freshness loop is in flight and disabled when idle
  (`dcc.Interval.disabled`/`interval` are settable from a callback). Not required —
  with the v13 cache-only read a per-tick read does zero network and is cheap. Note
  this would *also* fix the unresolved-scenario fetch storm (no loop ⇒ no polling),
  but at the cost of tracking in-flight loops — the registry v9 deliberately
  avoided. The `allow_network=False` read solves the same problem without that
  state, so adaptive cadence stays a pure idle-load nicety, not the fix.

**Residual, stated honestly.** After a *rare* loop exhaustion (>62s lag) the rank
shows the stale value until the user plays another run, clicks Refresh, or the 168h
TTL expires. Note **re-selecting the scenario does not heal it** — the cache is
still fresh-by-TTL, so a re-selection read is a cache hit and serves the stale value
(it does not re-fetch); this matches the failure-modes table. v12 accepts this
deliberately: the alternative (auto-recheck) hammered the offline/server-down cases
where the board never catches up. The exhaustion toast points the user at Refresh,
so the heal is one click away exactly when it matters.

**Why not SSE or full-block.** SSE has no native Dash support; wiring it up would
mean `dash-extensions`' SSE/`EventSource` components plus clientside glue. (We
already depend on `dash-extensions` — it backs `DashProxy` and the notification log
handler — so the real cost is the extra client/server plumbing and a long-lived
streaming endpoint, not a new dependency.) Either way it is overkill for a local
single-user tool and unjustified until this is ever multi-user. A callback that
*blocks* until the eventually-consistent data arrives would hold a server thread
for the whole retry window and freeze the UI — a non-starter. Interval polling
gives the "updates organically as each piece lands" feel of SSE with none of the
infrastructure: each widget re-reads its own cache on the shared interval.

Failure surfaces via `dash_logger.error(...)` directly from the freshness
function — the same `dash_logger` channel the watchdog uses today. There are
three trigger points, all non-blocking: a terminal bad-username error, an
unexpected exception caught by the broad guard, and retry exhaustion (a single generic
"may still be catching up" toast, plus a free score-precision-drift log check — v21). An
unresolved leaderboard
(`resolve_leaderboard_id` → `None`) is **not** one of them: it stops the loop
with a `logger.warning` only, no toast (see [Error Handling](#error-handling)).
The old `_handle_rank_refresh_result` callback is removed because the freshness
function now emits these notifications itself.

## Failure Modes And Edge Cases

| Case | Behavior |
|---|---|
| API never reports the new score within ~62s | Loop exhausts; previous cache preserved. `_notify_exhaustion` emits a generic "still catching up — click Refresh to retry" via `dash_logger.error` (plus a free score-precision-drift log check — v21). The stale value persists until the next PB (new loop), the 168h TTL (the next **non-interval** view re-fetches on the miss — interval ticks read TTL-independently and never fetch), or the user clicking [Refresh](#when-the-cache-stays-stale-the-manual-refresh-button). We do **not** auto-recheck (see that section). |
| API reports `RANKED` with score *higher* than expected | Accept as fresh. `_save_rank_monotonic` writes it and the loop exits. |
| API reports `UNRANKED` | Not fresh — do not write. Continue retries. After exhaustion, `_notify_exhaustion` emits the generic timeout toast (a bad username is caught terminally at resolution, not here — v21). Previous cache preserved. |
| Multiple PBs for the same scenario in succession | Each schedules its own independent loop. `_save_rank_monotonic` prevents a slower lower-score loop from overwriting a higher score already cached by a faster one — no read-path suppression to manage. A short retry window also makes overlap rare (a second PB needs another ~60s run). |
| UI read callback (`get_scenario_rank`) fires during the freshness window | The interval-triggered read is cache-only (no fetch). A dropdown/`do_update` read (which *may* fetch on a cache miss) goes through `_save_rank_monotonic`, which rejects the lower/UNRANKED result *and* returns the preserved winner — so neither the cache nor the display regresses. No counter or coordination needed. |
| Interval tick, **resolved** scenario | Cache-only read (`allow_network=False`): serves the cached rank/total with no network and surfaces the Timer loop's latest write. The loop is the only fetcher during the window. |
| Interval tick, **unresolved** scenario (custom, no leaderboard) | Cache-only read returns N/A with **zero network** — `resolve_leaderboard_id` does not reach `search_scenario_exact` because `allow_network=False`. No `/scenario/popular` per-second polling; the `dcc.Loading` spinner is suppressed on these fast ticks via `delay_show`. (This is the v12 regression v13 fixes; without the flag the read would fetch every tick.) |
| Page left selected and idle on one scenario past the 168h rank TTL | The cache-only interval read is **TTL-independent** (v20), so the rank keeps showing its last-known value rather than flipping to N/A from age alone. It can't refresh anyway; the next non-interval view (selection / `do_update` / manual Refresh) is TTL-gated and re-fetches. Without this the page would interval-poll itself from a rank to N/A after a week idle. |
| `fetch_scenario_rank` raises `RequestException` | Treat as transient; continue retries. The inner `_get_with_retry` has already retried once at the HTTP layer. |
| `resolve_leaderboard_id` raises `UnknownKovaaksUserError` | Terminal. Stop the loop immediately; emit a "username may be misconfigured" `dash_logger.error`. No retries. |
| `resolve_leaderboard_id` raises `requests.RequestException` (e.g. `search_scenario_exact` network blip on the first-PB cold-cache path) | Transient. Treat like a failed fetch: continue retries, exhaust if it never resolves. Distinct from a resolved `None`. |
| `resolve_leaderboard_id` returns `None` | Terminal: the scenario has no leaderboard on KovaaK's (normal for local/custom scenarios). Stop the loop with a `logger.warning` only — **no `dash_logger` toast**, which would cry wolf on every PB of an unranked custom scenario. |
| Any unexpected exception inside an attempt | Caught by the broad guard. Logged with traceback; emits a generic `dash_logger.error`. Loop stops (no reschedule). |
| App shuts down mid-loop | Daemon Timers die with the process. Next app start relies on the long cache TTL until either the cache expires or a new PB triggers a new freshness refresh. Acceptable. |
| User configures `kovaaks_username = ""` mid-session | New PBs no-op the refresh path. Existing in-flight Timer chains finish under their original username — harmless. |
| Multiple scenarios in flight | Each is independent. Bounded by how many distinct scenarios produce PBs in the ~1-min window — realistically a handful of pending Timer threads. |
| Test environments without network | `fetch_scenario_rank` raises; loop retries then exhausts; `_notify_exhaustion`'s validation also fails transiently and falls back to the generic message; no cache changes. Safe. |
| Rank save succeeds but leaderboard total fetch fails | Rank cache is updated; total cache is left as-is. Displayed percentile may briefly use the previous total. Logged as a warning. Same graceful degradation as today (rank is saved before total enrichment); the forced refresh adds percentile accuracy, not rank persistence. |
| `schedule_rank_freshness_refresh` raises (e.g. `Timer.start` hits the OS thread limit) | Propagates to `_refresh_rank_after_high_score`, which catches it, logs, emits one `dash_logger.error`, and returns. CSV ingestion and the PB toast proceed normally; no rank refresh runs for this PB. |
| Loop exhausts, then the user re-opens the scenario after KovaaK's caught up | Re-selection alone does **not** re-fetch — the rank cache is still fresh-by-TTL, so it serves the stale value. The user clicks Refresh (one-shot `force_refresh`), which fetches the now-fresh value and persists it via `_save_rank_monotonic`. (Or it heals at the 168h TTL / next PB.) |
| Offline play or KovaaK's down at PB time (board never catches up) | `cached < local_high` permanently. v12 does **not** auto-recheck, so no repeated fetches. The user can click Refresh; it returns the same stale board value and stops. This is the case lazy staleness would have hammered forever. |

## Testing

Unit tests for the freshness function in `api_service.py`, mocking
`fetch_scenario_rank` and `threading.Timer`:

- Accepts a `RANKED` result when `api_score == expected_score`.
- Accepts a `RANKED` result when `api_score > expected_score`.
- Accepts a `RANKED` result equal to the **2-dp floor** of `expected` (the caught-up
  board value, e.g. `expected = 913.419861` → board `913.41`).
- **Rejects a stale cent-below board (v17 P1 guard):** `expected = 100.00` (exact
  2-dp boundary), board `99.99` → **not** fresh; the loop retries rather than caching
  the stale value. (Under the old `expected - 0.01` form this would have been wrongly
  accepted.)
- Retries when API returns `UNRANKED`, then accepts a later fresh result.
- Retries when API returns a lower stale score, then accepts a later fresh
  result.
- Does not call `save_scenario_rank` on any stale result.
- Calls `save_scenario_rank` exactly once on the first fresh result.
- **Monotonic write: an older/lower loop cannot overwrite a higher cached
  score.** Seed the rank cache with `score=110`; run an attempt that fetches
  `score=100` and passes freshness (`expected_score=100`); assert
  `_save_rank_monotonic` reports `wrote=False` (winner is the cached `110`), the cache
  file still reads `110`, and the forced total refresh is *not* triggered.
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
  **`caplog` regression (v20):** assert the retry log is a one-line
  `request_exception_summary` at WARNING with **no traceback** (`record.exc_info is
  None`), matching the api_service logging convention.
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
- **Exhaustion notification + drift diagnostic (v21):** on exhaustion
  `_notify_exhaustion` emits the single generic "may still be catching up"
  `dash_logger.error` (the username-validation call was cut). Separately, when the last
  fetch was RANKED with a score *below* `floor2(expected)`, it logs a distinct "possible
  score-precision drift" `logger.warning`; assert that warning fires in that case and
  not when the last score met `floor2(expected)`.
- Two concurrent loops for the same scenario at different expected scores both
  exit cleanly when the API catches up (no cache corruption, no exception, no
  regression of the higher score).
**Centralized monotonic write (`_save_rank_monotonic` / `_is_forward`)** —
table-driven over candidate-vs-existing:

- empty cache + any candidate → writes;
- existing RANKED higher, candidate RANKED lower → rejected;
- **existing RANKED `100.00`, candidate RANKED `99.99` (one cent lower) → rejected
  (v17 P1 guard):** the sub-cent regression the old `existing - 0.01` tolerance let
  through. Assert the cache still reads `100.00` and its `mtime` did not advance;
- existing RANKED, candidate UNRANKED → rejected (never regress a known rank);
- existing RANKED **with a score**, candidate RANKED **scoreless** (`score=None`) →
  rejected (never drop a known score; assert the cache keeps the scored entry and its
  `mtime` did not advance);
- existing RANKED **scoreless**, candidate RANKED **with a score** → writes (forward
  move; the candidate is strictly more informative);
- existing UNRANKED, candidate RANKED → writes;
- equal score → writes (idempotent re-confirm / `scenario_name` backfill refreshes
  `mtime`; rank-number last-writer-wins is a non-goal — the v19 `fetched_at` tie-break
  was cut in v21);
- **`allow_derank` (v21):** existing RANKED, candidate UNRANKED with `allow_derank=False`
  → rejected (winner is the cached RANKED); the *same* inputs with `allow_derank=True`
  (an explicit Refresh) → **writes** the UNRANKED, so a genuine de-rank clears on demand.

**Read path is display- and cache-monotonic (no regression during the window):**
seed the cache with `score=110`; call `get_scenario_rank_info` on a path that
fetches a lagging `score=100` (and, separately, a transient `UNRANKED`); assert it
**returns the preserved winner (`110`) for display**, the cache file still reads
`110`, and its `mtime` did **not** advance (rejected write touches nothing). This is
the "display does not regress" guard, not only "cache does not regress."

**Interval poll on a resolved scenario does not fetch — including a total-cache miss
(P1-B):** seed a fresh mapping and rank cache but an **expired (or absent) total
cache**; invoke the rank callback's interval-triggered path (`allow_network=False`);
assert it returns the cached rank and `_session_get` is **never called**. Seeding a
*fresh* total would hide the bug — the cache-only path must avoid
`_with_leaderboard_total`, which fetches on a total miss.

**Trigger classification allows network on initial render / co-fire (cold cache):**
call the pure `_rank_allows_network` helper directly — no Dash context needed — with
the initial-call sentinel `[{"prop_id": "."}]` and assert it returns `True`; likewise
for a selection + interval co-fire list, and `False` for an interval-only list. Then,
with no caches seeded, drive `get_scenario_rank` so `allow_network` is `True` and
assert resolution + `fetch_scenario_rank` run (not the cache-only path). This guards
the sentinel/co-fire behavior — a `ctx.triggered_id != "interval-component"` form
would regress both cases.

**Rank render body is testable without Dash (v19):** call `_render_scenario_rank`
directly with an explicit `allow_network` — `True` exercises resolve/fetch + gated
emit, `False` exercises the cache-only path and asserts no `_session_get` — so the
existing direct-call tests (today calling `get_scenario_rank` as a plain function) move
to the ctx-free body and stop depending on `ctx.triggered` being populated.

**Interval poll on an unresolved scenario does not fetch (v13 regression guard):**
with no cached mapping for the scenario, invoke the rank callback's
interval-triggered path (`allow_network=False`); assert it returns N/A,
`search_scenario_exact` / `_session_get` is **never called**, and nothing is
written to the mapping cache. (Without the flag this would fire `/scenario/popular`
every tick — the bug v13 fixes.)

**`allow_network=False` short-circuits resolution:** call
`get_scenario_rank_info(..., allow_network=False)` for an unresolved scenario;
assert `resolve_leaderboard_id` consults only `get_cached_leaderboard_id` (no
hydration, no `search_scenario_exact`) and the read does not fall through to
`fetch_scenario_rank` on the rank-cache miss.

**Manual refresh forces a one-shot fetch and surfaces messages:** the
`refresh_rank` callback calls `get_scenario_rank_info(..., force_refresh=True)` (which
threads `allow_derank=True`), fetching once and persisting through `_save_rank_monotonic`.
Assert a single `fetch_scenario_rank`; that a returned-lower *score* **neither**
regresses the higher cached score **nor** is displayed (the winner is rendered); that a
returned **UNRANKED** (a genuine de-rank via the explicit button) **is** written and
displayed (P1-A); and that a result carrying `error_message`/`warning_message` emits a
`dash_logger.error`/`warning` (i.e. a forced-lookup failure does **not**
become a silent "N/A"). The emission is **un**gated — it fires even when the same
error was already shown, because the click is an explicit user request.

**Interval tick does not re-toast a derived warning:** seed a cached rank whose
`matched_steam_id` differs from the configured Steam ID (so
`_with_derived_rank_warning` derives a mismatch `warning_message` at read time —
the field is `Field(..., exclude=True)` and is **never persisted directly**, so the
warning cannot be seeded into the cache file; only `matched_steam_id` can); invoke
the interval-triggered path; assert `dash_logger.warning` is **not** called
(emission is gated off on interval triggers). A selection-triggered invocation of
the same path **does** emit.

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

The freshness test assumes the leaderboard `score` is the local CSV `score`
**truncated to 2 dp** (so `board == floor2(local_high)`). This is not unit-tested (it
is a property of KovaaK's data, not our code), but it can be checked offline against
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
not a precision artifact. Conclusion: `board == floor2(local_high)` holds, which is
exactly what `_score_is_fresh` tests via `_floor_2dp(expected)` (see [Why we floor
the local score](#why-we-floor-the-local-score-instead-of-subtracting-a-tolerance)).

Manual end-to-end verification: copy a CSV file into the watched stats
directory with the `Score:` field manually adjusted. Setting the score above
the current local high score should trigger the polling path; the cache file
under `cache/leaderboard/user_rank/<username>/<leaderboard_id>.json` should
remain unchanged until KovaaK's API actually reflects a matching or higher
score (or until exhaustion).

Spinner-flicker QA (v14): with a scenario selected, leave the dashboard idle for
~30s and confirm the rank `dcc.Loading` spinner does **not** flash on the per-second
interval ticks (it should appear only on a real fetch — scenario selection or a
manual Refresh). Check both a resolved scenario and a custom/unresolved one. If it
flickers, raise `delay_show`.

## Implementation Steps

These steps ship across **three PRs**, not one — see [Rollout / PR
Staging](#rollout--pr-staging) for the grouping and rationale. The numbered steps
below are the granular checklist; the rollout section maps them onto the PRs.

1. Add to `source/kovaaks/api_service.py`: the import `from decimal import Decimal,
   ROUND_FLOOR` (for `_floor_2dp`), the module constants (`ATTEMPT_DELAYS_SECONDS`,
   `SCORE_EPSILON`), `_rank_save_lock`, and the functions `_floor_2dp`,
   `_save_rank_monotonic`, `_is_forward`, `_cached_rank`, `_score_is_fresh`,
   `schedule_rank_freshness_refresh`, `_run_attempt`, `_schedule_attempt`, and
   `_notify_exhaustion`.
2. Route the read path's writes through `_save_rank_monotonic` in
   `get_scenario_rank_info`: the cache-miss/`force_refresh` save at
   [`api_service.py`](../source/kovaaks/api_service.py) and the cache-hit
   `scenario_name` backfill at
   [`api_service.py`](../source/kovaaks/api_service.py) (in-memory
   `scenario_name` attach stays unconditional; only the write is conditional).
   Pass `allow_derank=force_refresh` so an explicit Refresh can clear a genuine de-rank
   while automatic reads cannot (P1-A). Return the `winner` it reports for display — on
   a rejected write, return the preserved cache entry, not the lower fetch — so the
   displayed value is forward-only (for scores), not just the persisted one.
3. Delete `refresh_scenario_rank` from `api_service.py`. Confirm it has no
   remaining callers (its only caller was the watchdog, updated in step 4).
4. In `file_watchdog.py`, rewrite `_refresh_rank_after_high_score` to take and
   thread `expected_score` (= `run_data.score`) into `schedule_rank_freshness_refresh`,
   wrapping that call in a try/except that logs + emits one `dash_logger.error`
   and returns (best-effort; a `Timer.start` failure must not escape the watchdog
   thread). Update the three PB call sites (new scenario; new sensitivity with new
   PB; existing scenario with new PB) to thread `expected_score` through. Call-site
   order vs. `message_queue.append` no longer matters.
5. Remove the now-unused `rank_refresh_executor` and `_handle_rank_refresh_result`
   from `file_watchdog.py`.
6. Add the cache-only read seam in `api_service.py` (v13): add
   `allow_network: bool = True` to `resolve_leaderboard_id` (when `False`, consult
   only `get_cached_leaderboard_id`; skip hydration and `search_scenario_exact`)
   and to `get_scenario_rank_info` (thread it into `resolve_leaderboard_id`; on
   `False`, do not fall through to `fetch_scenario_rank` on a rank-cache miss, read the
   rank cache TTL-independently, and attach the total via `get_cached_leaderboard_total`
   + `_with_percentile` — **not** `_with_leaderboard_total`, which fetches on a total
   miss (P1-B)).
7. Add the UI polling in `home.py`: add `Input("interval-component", "n_intervals")`
   to `get_scenario_rank`; extract a pure `_rank_allows_network(ctx.triggered)` helper
   (`any(t["prop_id"] != "interval-component.n_intervals" for t in triggered)`) and a
   ctx-free body helper `_render_scenario_rank(selected_scenario, allow_network)`, so
   the callback is a thin shell that reads `ctx` only at the edge — an interval-only
   tick is cache-only, and both the trigger classification and the render body are
   unit-testable without a Dash callback context (the existing direct-call tests drive
   `_render_scenario_rank` with an explicit `allow_network` bool). Extract `_emit_rank_messages` and call it
   only when `allow_network` is true (emit on selection/`do_update`, stay silent on
   interval ticks). Add `delay_show=300` (and optionally `delay_hide`) to the rank
   `dcc.Loading` at [home.py](../source/pages/home.py) so the per-second
   interval tick does not flicker the spinner on cache-only reads (v14).
8. Add the manual refresh button: a `dmc.Button`/`dmc.ActionIcon` (`id="rank-refresh-button"`)
   beside the rank widget and a `refresh_rank` callback that calls
   `get_scenario_rank_info(selected_scenario, ..., force_refresh=True)`, emits
   messages via `_emit_rank_messages` (ungated), and writes the result via
   `_save_rank_monotonic`.
9. Add unit tests: `_save_rank_monotonic`/`_is_forward` rule table, read-path
   no-clobber, interval poll makes no `_session_get` call for **both** resolved and
   unresolved scenarios, `allow_network=False` resolution short-circuit, interval
   tick does not re-toast a cached warning, manual-refresh one-shot fetch (no
   regression) that surfaces messages, error-classification, and exhaustion-message
   cases above.
10. Smoke-test by intentionally returning stale scores from a patched
    `fetch_scenario_rank` to confirm retries fire on schedule and the cache
    stays untouched on exhaustion.
11. Update standing docs (ships with PR 3): in `architecture.md`, replace the "Rank
    refresh pool — `ThreadPoolExecutor(max_workers=2)`" runtime-thread entry with the
    Timer-based freshness poll plus the interval / manual-Refresh UI; supersede the
    now-stale `scenario_rank_proposal.md` decisions ("Use `ThreadPoolExecutor(max_workers=2)`",
    "No manual rank refresh button is planned"); and add a `decision_log.md` entry
    recording the durable decisions (bounded score-aware Timer poll, centralized
    monotonic write, manual Refresh button) so this proposal can be distilled and
    deleted on ship per the docs-lifecycle policy.

## Rollout / PR Staging

The change ships as **two PRs — backend (PR 1 + PR 2) / UI (PR 3)** — separating the two
genuinely different risk surfaces (backend concurrency vs. Dash UI wiring) at a ceremony
level that suits a solo repo with no CI (v21, P2-B). The three-way breakdown below is the
*granular* view if you want finer staging or to land the monotonic-write foundation on
its own; it's optional, not the default. Either way, keep each diff small enough to
review thoroughly — the local gates are the merge bar.

**Why a split is cheap here: every intermediate state is shippable.** A staged
rollout is only safe if each PR leaves the app valid with no regression. All three
cut points pass:

- **After PR 1 (monotonic write):** the existing single-shot refresh still runs, but
  every cache write is now forward-only — strictly safer than today. No behavior the
  user sees changes.
- **After PR 2 (freshness loop):** the watchdog polls reliably after a PB, so the
  cached rank is no longer left stale by leaderboard lag. The rank widget still
  updates only on next-run / re-selection — i.e. *today's* UI cadence. The "update
  within ~1s without replaying" requirement is not met yet, but that is a
  *pre-existing* limitation, so it is not a regression.
- **After PR 3 (UI):** interval polling surfaces the loop's writes within ~1s and the
  manual Refresh button lands — the full feature.

Because there is no half-broken in-between state, the only cost of splitting is PR
overhead (three review/test cycles instead of one).

### The three PRs

| PR | Implementation steps | Delivers | Depends on |
|---|---|---|---|
| **PR 1 — Centralized monotonic write** | Step 1 *(partial: `_rank_save_lock`, `SCORE_EPSILON`, `_save_rank_monotonic`, `_is_forward`, `_cached_rank`)*, Step 2, plus the Step 9 tests for the `_is_forward` rule table (incl. the sub-cent regression case) and read-path no-clobber | The single forward-only cache writer every other path funnels through; cache can never regress | — |
| **PR 2 — Bounded score-aware freshness loop** | Step 1 *(rest: `ATTEMPT_DELAYS_SECONDS`, `_floor_2dp`, `_score_is_fresh`, `schedule_rank_freshness_refresh`, `_run_attempt`, `_schedule_attempt`, `_notify_exhaustion`)*, Steps 3, 4, 5, plus the Step 9 tests for freshness gating / retry / exhaustion / error classification / watchdog wiring, and Step 10 smoke test | Reliable post-PB rank refresh; deletes `refresh_scenario_rank` and the old executor | PR 1 |
| **PR 3 — UI: cache-only interval poll + manual refresh** | Steps 6, 7, 8, 11, plus the Step 9 tests for interval-no-fetch (resolved *and* unresolved), `allow_network=False` short-circuit, no-re-toast, and manual-refresh one-shot + emission | Rank updates within ~1s without replaying; manual Refresh button; standing docs updated | PR 1 (and surfaces PR 2's writes) |

Step 9 (tests) is not its own PR — each PR carries the tests for the code it adds.

### Ordering and dependency notes

- **Order: PR 1 → PR 2 → PR 3.** PR 1 is the foundation both others write through.
- **PR 3 strictly depends only on PR 1, not PR 2** (the manual Refresh and cache-only
  read need the monotonic writer, not the loop). It is sequenced *after* PR 2 because
  the interval poll's purpose is to surface the loop's background writes — shipping
  the poll before the loop exists would add a UI mechanism with little to show.
- **Why PR 1 is isolated:** the monotonic write is the trickiest correctness surface
  (process-wide lock, the `_is_forward` rule table, loop-vs-loop and read-vs-loop
  races) and is a prerequisite for both the loop and the manual refresh. Reviewing it
  free of Timer-chain logic and Dash callback wiring is the main reviewability win.

### Acceptable fallbacks

If three PRs feels like too much ceremony for a solo project, two are defensible:
**backend (PR 1 + PR 2) / UI (PR 3)** still separates the two distinct risk surfaces
at half the overhead. A single PR is also valid given the clean intermediate states
and the design's maturity — the three-PR split is a soft preference for
reviewability and de-risking, not a correctness requirement.

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
- **Display is score-forward-only, not just the cache (v18).** `_save_rank_monotonic`
  returns `(winner, wrote)`; the read path renders the `winner`, so a *fetched* worse
  **score** is never shown — the UI can't flicker to a lower number for ~1s until the
  next interval tick re-reads cache. Two scoped caveats: a fetch *exception* early-returns
  N/A (it bypasses the monotonic write — tradeoff T2), and an explicit Refresh may show a
  genuine de-rank (P1-A). Extends the cache's no-regress policy to the display, for
  scores. A pure `_rank_allows_network(ctx.triggered)` helper lands in the same round so
  the interval trigger-classification is testable without a Dash callback context.
- **Render body is ctx-free (v19); equal-score rule stays score-only (recency tie-break
  cut in v21).** v19 factored the rank callback body into a ctx-free
  `_render_scenario_rank(selected_scenario, allow_network)` so the existing direct-call
  tests need no Dash callback context — kept. v19 also added a `fetched_at` recency
  tie-break at equal score; **v21 cut it** — it protected only the rank *number* being
  1–2 positions stale for a few seconds in a sub-second race (self-healing, imperceptible)
  at the cost of a standing "`fetched_at` always tz-aware UTC" invariant. "Equal-or-higher
  ⇒ write" is the simplest correct rule; rank-number freshness at equal score is a
  non-goal (N3).
- **An explicit Refresh can clear a genuine de-rank (P1-A, v21).** Routing every write
  through `_save_rank_monotonic` (v18) plus reading `existing` TTL-independently made
  RANKED→UNRANKED *un*writable by *any* path — including the manual button, whose whole
  job is re-pulling a divergent rank. Without a fix a real de-rank (KovaaK's purges a
  leaderboard) would show stale forever with no in-app recovery. Fix: `_save_rank_monotonic`
  gains `allow_derank`, set only by `force_refresh` (the button), so automatic paths stay
  flicker-free while the explicit user action is authoritative. A lower *score* is still
  rejected even on Refresh (v18 score-display-monotonicity holds); only RANKED→UNRANKED is
  permitted, and a transient UNRANKED self-heals on the next RANKED write.
- **Two distinct score comparisons, two distinct constants (v17).** Freshness
  (local-vs-board) and monotonicity (board-vs-board) are *different* comparisons and
  must not share a constant. Freshness models KovaaK's 2-dp truncation by flooring
  the **local** score (`board >= _floor_2dp(expected) - SCORE_EPSILON`) rather than
  subtracting a one-cent tolerance, which would accept a stale cent-below board when
  `expected` sits on a 2-dp boundary. Monotonicity compares two already-truncated
  board scores and requires strict non-decrease (`candidate >= existing -
  SCORE_EPSILON`; equal-or-higher writes — the v19 equal-score recency tie-break was cut
  in v21); reusing the one-cent tolerance there punched a regression hole in
  the "never regress" invariant. `SCORE_EPSILON` (`1e-6`) is float-noise slack only;
  the retired `SCORE_FRESHNESS_TOLERANCE` (`0.01`) conflated the two. This corrected
  two P1 bugs Codex found in v16.
- **Manual refresh button instead of an automatic lazy staleness check (v12).**
  A locally-generated high score may *never* reach KovaaK's — the user played
  offline, or the server was down at PB time — so `cached < local_high` can stay
  true forever. The lazy staleness check (v9–v11) auto-re-fetched whenever that
  held, which means it would have hammered those divergent scenarios on every view
  while gaining nothing (it just re-reads the same stale board value). v12 removes
  it and adds a user-clicked Refresh button: re-fetching happens only when the user
  asks for it, which caps API calls and does the right thing for the
  offline/server-down cases. The cost — a rare post-exhaustion case no longer
  auto-heals — is worth not hammering the API. (v12 also claimed this let us delete
  the `allow_network` machinery; v13 corrects that — a narrowed cache-only read is
  still needed for resolution avoidance, see the interval-polling decision below.)
  See [the manual refresh button](#when-the-cache-stays-stale-the-manual-refresh-button).
- The freshness loop is a separate function in `api_service.py` — not a flag on
  `get_scenario_rank_info`, not a new module. The split is **polling vs. one
  fetch**: it schedules a Timer chain and re-checks over time, which a synchronous
  lookup does not do. Cache-write gating no longer differentiates them — both use
  `_save_rank_monotonic`.
- **Schedule shortened to `(2, 4, 8, 16, 32)` (~62s, v9).** KovaaK's usually
  catches up within seconds; past ~60s it is almost certainly down or a transient
  network issue. No jitter — that pattern exists to desynchronize *many* clients,
  and we are a single local client polling for eventual consistency.
- **UI updates via interval polling, not SSE or blocking (v9; cache-only read
  re-narrowed v13).** The rank widget re-reads the cache on the existing
  `dcc.Interval`, reflecting the loop's write within ~1s without waiting for another
  run. The interval-triggered read is **cache-only** via `allow_network=False` plus
  a `ctx.triggered` sole-interval check (the `any()` form — *not* `ctx.triggered_id`,
  which would drop the initial-`.`-sentinel and co-fire cases; see the UI snippet).
  v12 tried to drop both, reasoning that removing lazy
  staleness removed all reason to fetch on a tick — but resolution of *unresolved*
  scenarios is a second, independent reason: without the flag, sitting on a custom
  scenario fires `search_scenario_exact` (a `/scenario/popular` GET) every second
  (`polling_interval = 1000`), because there is no negative cache for "no
  leaderboard." So v13 keeps a narrowed `allow_network` (resolution avoidance), not
  the v10/v11 version (lazy-staleness fetch). For a resolved scenario the read is a
  cache hit (selection populated mapping/rank/total); for an unresolved one it
  returns N/A with zero network. Warning/error emission fires only on non-interval
  triggers (and the manual refresh), realizing "fire on change, not every tick"
  without per-tick re-toasting. SSE is unjustified for a local single-user tool.
  **TTL-independent (v20):** the cache-only interval read serves the rank regardless of
  its 168h TTL — a passive mirror can't refresh, so TTL-gating it would only flip a
  long-idle page's rank to N/A; TTL re-fetch stays the job of the non-interval reads.
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
  ([`file_watchdog.py`](../source/my_watchdog/file_watchdog.py)). A new
  scenario is logically a PB-from-nothing.
- No "rank is being checked" notification is emitted on attempt #0. The user
  already saw the PB toast. Only terminal/unexpected failure and
  after-exhaustion are surfaced via `dash_logger.error(...)`.
- **Exhaustion: one generic toast, no validation call; free drift diagnostic (v21).**
  Earlier drafts ran a total-play validation on exhaustion to tune the message
  ("misconfigured username" vs "still catching up") — cut in v21 as a failure-path API
  call buying a rare distinction (a bad username is already caught terminally at
  resolution in the common case). Instead `_notify_exhaustion` does a *free* check: if
  the last fetch was RANKED but below `floor2(expected)`, it logs a distinct "possible
  score-precision drift" warning — cheap insurance for the single-sourced
  `board==floor2(local)` assumption (T5), making a systemic break diagnosable instead of
  looking like ordinary lag.
- **Manual-refresh button: now built (v12); surfaces messages (v13).** Reversed
  from the earlier "deferred" stance: with lazy staleness removed, the button is the
  user's way to re-pull a stale or divergent rank on demand. It reuses
  `get_scenario_rank_info(force_refresh=True)` (no new backend function), and
  `_save_rank_monotonic` protects it — the force-refresh writes through the same
  forward-only rule, so it cannot regress a running loop's higher score. One-shot,
  not a freshness loop: by the time a user clicks, the board has usually settled,
  and they can click again if not. **v13 fix:** the callback must call the shared
  `_emit_rank_messages` so a forced-lookup failure (bad username, fetch error,
  Steam-ID mismatch) toasts instead of silently rendering "N/A". This emission is
  **un**gated (the user explicitly asked), unlike the interval poll's on-change
  emission — so "reuse the gated behavior" is too coarse; the policies differ by
  trigger.
- **Rank cache TTL: unchanged at 168h.** Kept as-is for now. Revisit only if
  real staleness complaints surface. New PBs remain the primary refresh signal,
  and that path is exactly what this proposal makes reliable.

## What's Not Changing

- `get_scenario_rank_info` keeps its read/display behavior. Two changes: (1) its
  two rank-cache writes now go through `_save_rank_monotonic` (forward-only), and
  (2) it regains an `allow_network: bool = True` parameter (v13) so the interval
  poll can request a cache-only read. The default preserves today's behavior; only
  the interval-triggered call passes `allow_network=False`. The `local_high_score`
  addition v10/v11 proposed stays dropped (that was the lazy-staleness input).
- `save_scenario_rank` itself is unchanged (it still does the unconditional file
  write); `_save_rank_monotonic` wraps it with the forward-only check that every
  writer now goes through.
- The 168h `scenario_rank_cache_ttl_hours` default is unchanged. New PBs
  remain the primary refresh signal.
- The
  [`_get_with_retry`](../source/kovaaks/api_service.py) HTTP-level retry
  is unchanged. It handles per-request 429s and transient failures; the new
  code handles cross-request eventual-consistency lag. The two are
  deliberately separate concerns.
- `ScenarioRankInfo` and other API models are unchanged. `score` is already
  populated by `fetch_scenario_rank`.
