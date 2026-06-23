# Proposal: Replace Hand-Rolled GET Retry With a urllib3 `Retry` Adapter?

Status: Proposed
Date: 2026-06-21

## Question

Should we delete the hand-rolled retry helpers in
[`source/kovaaks/api_service.py`](../source/kovaaks/api_service.py) —
[`_get_with_retry`](../source/kovaaks/api_service.py:113) (line 113) and
[`_retry_after_seconds`](../source/kovaaks/api_service.py:78) (line 78) — and
instead mount an `HTTPAdapter(max_retries=Retry(...))` on each thread-local
`requests.Session`?

Short answer: **Defer.** The overlap is real, but a swap does not actually
remove the wrapper, it loses two deliberate behaviors, and it forces a test
rewrite — for net-neutral complexity today. Revisit when we want *richer* retry
behavior (more attempts, real exponential backoff, broader status codes), where
`Retry` clearly earns the migration cost. The "how" is documented below so this
is not rediscovered from scratch.

## The overlap is confirmed

`urllib3.util.retry.Retry` (we ship `urllib3 2.6.3`, transitively via
`requests 2.33.1`) covers most of what the helpers do:

| Hand-rolled today | urllib3 `Retry` equivalent |
|---|---|
| One retry on HTTP 429 | `total=1`, `status=1`, `status_forcelist=[429]` |
| One retry on `Timeout` / `ConnectionError` | `connect=1`, `read=1` (urllib3's own connect/read errors) |
| GET-only | `allowed_methods=frozenset({"GET"})` |
| Honor `Retry-After` (numeric + HTTP-date) | `respect_retry_after_header=True` (default) + `parse_retry_after` |
| Cap `Retry-After` at 5s | `retry_after_max=5` (see caveat below) |

So the *happy path* maps cleanly. The trouble is in the deltas.

## Behavioral differences that are NOT 1:1

### 1. The `Retry-After` cap (the headline concern)

The task framing — "urllib3 sleeps the full `Retry-After`; only `backoff_max`
exists and it caps computed backoff, not the header" — was true for older
urllib3 but is **outdated for 2.6.3**. This version added a separate
`retry_after_max` parameter (default `21600` = 6h), and `parse_retry_after`
clamps the header to it. Verified empirically:

```text
Retry(..., retry_after_max=5).get_retry_after({"Retry-After": "60"}) -> 5
```

So the 5s cap **can** be preserved natively with `retry_after_max=5`. The catch
is robustness: `urllib3` is a *transitive* dependency. It is pinned to `2.6.3`
in `uv.lock`, but `pyproject.toml` declares no floor. If a resolve ever lands on
a urllib3 without `retry_after_max`, the constructor still accepts the kwarg on
2.6.3 but older versions would raise `TypeError` — or, worse for a looser pin,
the parameter could be absent and a hostile/buggy `Retry-After: 999999` would be
slept in full, freezing a worker thread. The current code's `MAX_RETRY_AFTER_SECONDS`
clamp is unconditional and version-independent.

**Decision: the cap must be preserved.** If we migrate, either (a) add an
explicit `urllib3>=2.6` floor to `pyproject.toml` and pass `retry_after_max=5`,
or (b) keep a one-line clamp guard in our own code. Option (b) means we never
fully delete the custom logic, which weakens the simplification argument.

### 2. The default delay when `Retry-After` is absent is lost

Current code sleeps `DEFAULT_RETRY_AFTER_SECONDS = 0.5` on a 429 with no
`Retry-After`. urllib3 falls back to exponential backoff, but with a **single**
retry that sleeps **0 seconds** — backoff only applies from the *second*
consecutive error (`get_backoff_time` returns `0` while `len(history) <= 1`,
verified empirically). No `backoff_factor` value recovers the 0.5s first-retry
delay. We would lose the polite spacing and immediately re-hammer the endpoint.

### 3. The exhaustion exception surface changes

- **429 exhausted:** today `_get_with_retry` calls `raise_for_status()` on the
  final 429 → `requests.HTTPError`. With `raise_on_status=True` (default) urllib3
  raises `MaxRetryError`, surfaced by requests as `requests.exceptions.RetryError`.
  Mitigation: set `raise_on_status=False` and keep our own `raise_for_status()`
  to preserve `HTTPError`.
- **Transient exhausted:** today a bare `requests.ReadTimeout` propagates. Via
  the adapter, the final failure is a `requests.ConnectionError`/`RetryError`
  wrapping urllib3's `MaxRetryError`, not the original exception type.

Both are caught by the broad `requests.RequestException` handlers in the service
layer, so production behavior degrades the same way — but the *types* differ,
which the existing tests assert on directly (see coverage below).

### 4. Recovery logging downgrades

The helper logs a WARNING on every recovered retry (decision log:
"Retry KovaaK's GET Transient Failures Once"). urllib3 logs a DEBUG line on its
own `urllib3` logger. We would lose the WARNING-level visibility unless we keep
custom logging — again, not a clean delete.

### 5. The wrapper does not actually go away

`_get_with_retry` also applies `kwargs.setdefault("timeout", TIMEOUT)`. `Retry`
does not set a per-request timeout, so a thin wrapper (or per-call `timeout=`)
is still required. Combined with #1, #2, and #4, a faithful migration keeps a
small custom shim rather than deleting it.

## Orthogonal to the eventual-consistency work — keep layered

This is deliberately separate from the scenario-rank eventual-consistency
proposal (latest: `scenario_rank_eventual_consistency_proposal_v9.md`). That
design is a **cross-request** freshness *waiter* — poll the leaderboard at
growing intervals until the new PB propagates — and it explicitly sits *on top
of* `_get_with_retry`, relying on it for **per-request** 429/transient handling
(v9 lines 158-159, 303-305, 773, 1029). The two layers should stay distinct:

- HTTP-level (`_get_with_retry`): one retry, politeness, bounded wait.
- Eventual-consistency loop: many scheduled attempts across requests.

A migration here must preserve the observable contract the loop depends on
(one inner retry, transient failures handled, bounded sleeps). It changes *how*
the inner layer is implemented, not the layering.

## Current behavior verified against the gates

- `uv run pytest tests/test_api_service.py` — **green** (58 tests).
- `uv run pylint source/kovaaks/api_service.py` — 9.63/10; messages are
  pre-existing docstring/arg-count noise, **none in the retry functions**
  (matches the repo's interim "don't regress the baseline" merge bar).
- `uv run mypy source` — 26 errors, all pre-existing in other files
  (`data_service`, `pages`, `app`, `plot`); **none in `api_service.py`**.

Existing coverage in `tests/test_api_service.py` is thorough and tied tightly to
the current implementation — these would need rewriting against an adapter:

- `test_get_with_retry_reuses_session_within_thread`, `..._is_thread_local`
- `test_get_with_retry_retries_once_on_429`
- `test_get_with_retry_uses_bounded_retry_after` (asserts the 5s cap + 0.5s default)
- `test_get_with_retry_caps_http_date_retry_after`
- `test_get_with_retry_does_not_retry_non_429_http_errors` (asserts `HTTPError`)
- `test_get_with_retry_gives_up_after_second_429` (asserts `HTTPError` — would become `RetryError`)
- `test_get_with_retry_retries_once_on_transient_exceptions`
- `test_get_with_retry_gives_up_after_second_transient_exception` (asserts bare `ReadTimeout`)
- `test_get_with_retry_propagates_unexpected_exceptions`

They monkeypatch `api_service._session_get` and `api_service.time.sleep`. An
adapter retries *inside* urllib3's connection pool, so these seams disappear;
adapter-level tests need a mock transport (`requests-mock`/`responses`) or a
fake `HTTPAdapter`. That is the bulk of the migration cost.

## Recommendation

**Do not migrate now.** The current helpers are ~70 lines, correct, well-tested,
and already ratified (decision log, 2026-04-28). urllib3 `Retry` would replace
them with ~10 lines of config *plus* a retained shim for timeout/cap/logging
*plus* a full test rewrite *plus* a urllib3 version floor — net-neutral on
complexity and a small regression in observability and default politeness. That
does not clear the "simpler or safer" bar for replacing working, decided code.

Reconsider when requirements grow past one retry (e.g. exponential backoff with
jitter, broader `status_forcelist` like 503, separate connect/read budgets). At
that point hand-rolling becomes the worse option and this migration pays off.

### If/when we do migrate — minimal-drift recipe

- One module-level `Retry`: `total=1, status=1, connect=1, read=1,
  status_forcelist=[429], allowed_methods=frozenset({"GET"}),
  respect_retry_after_header=True, retry_after_max=5, raise_on_status=False`.
- Mount it on both `http://` and `https://` of each thread-local session.
- Keep a thin wrapper for `timeout` default and the recovered-retry WARNING log.
- Add `urllib3>=2.6` to `pyproject.toml` (for `retry_after_max`).
- Accept losing the 0.5s no-header default, or keep a tiny guard for it.

## Drive-by note (not in scope)

`docs/api_retry_proposal.md` is the *shipped* proposal for the original helper.
Per `CLAUDE.md` ("when a proposal ships, distill it into a `decision_log.md`
entry and delete the file"), and since the decision log already carries
"2026-04-28: Retry KovaaK's GET Transient Failures Once", that file is stale and
a candidate for deletion. Flagged only — not touched here.
