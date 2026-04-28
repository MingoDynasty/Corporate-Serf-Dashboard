# API Retry Helper Proposal v2 (M0)

## Goal

Add a single retry layer for KovaaK's GET requests so transient `429 Too Many Requests` responses degrade gracefully instead of immediately failing user-facing operations.

This is a small infrastructure milestone that should ship before the Playlist Scenarios Overview page.

## Why Now

The Playlist Scenarios Overview proposal will load rank data across every scenario in a selected playlist. On a cold cache, a large playlist may trigger many leaderboard calls in a short window:

```text
40 scenarios * 2 leaderboard calls per scenario = ~80 calls
```

The M1 plan already limits this with:

- cache-first row building
- a dedicated `ThreadPoolExecutor(max_workers=4)`
- render-when-ready table loading
- per-row failure handling

Even so, a short burst can still hit KovaaK's rate limiting. A low-level 429 retry means the existing single-scenario rank lookup and the upcoming playlist table both inherit the same protection.

This is not a full rate-limit strategy. It is a narrow seatbelt for transient 429s.

## Scope

### In

- Add a `_get_with_retry(url, **kwargs)` helper in `source/kovaaks/api_service.py`.
- Retry only GET requests, because every current KovaaK's API caller is GET-only.
- Retry exactly once when the response status is `429`.
- Honor `Retry-After` when KovaaK's provides it.
- Fall back to a short default delay when `Retry-After` is absent or invalid.
- Cap retry delay to avoid freezing the app for a long server-requested wait.
- Log via the module `logger` when a retry fires.
- Refactor every existing `requests.get(...)` call in `api_service.py` through the helper.
- Add regression tests for retry behavior.
- Update `docs/kovaaks_api_notes.md` and `docs/decision_log.md` if implemented.

### Out

- Retrying non-GET methods.
- Retrying non-429 HTTP failures.
- Retrying timeouts, DNS failures, connection failures, or other non-HTTP exceptions.
- Exponential backoff, circuit breakers, token buckets, or a centralized rate limiter.
- M1's parallel playlist-table fetch executor.
- Changing user-facing failure states. If the retry also fails, callers should continue through the existing `UNKNOWN` / `N/A` behavior.

## Design

### Helper

Use a GET-specific helper instead of a method-agnostic wrapper. This keeps retry semantics safe and honest: GET is idempotent for our use case, while future POST/PUT/DELETE behavior should be a separate decision.

```python
MAX_RETRY_AFTER_SECONDS = 5.0
DEFAULT_RETRY_AFTER_SECONDS = 0.5


def _get_with_retry(url: str, **kwargs) -> requests.Response:
    """
    Make a KovaaK's GET request with one automatic retry on HTTP 429.

    All kwargs pass through to `requests.get(...)`.
    """
    kwargs.setdefault("timeout", TIMEOUT)

    response = requests.get(url, **kwargs)
    if response.status_code != 429:
        response.raise_for_status()
        return response

    delay_seconds = _retry_after_seconds(response)
    logger.warning(
        "Rate limited by KovaaK's at %s; retrying once after %.2fs",
        url,
        delay_seconds,
    )
    time.sleep(delay_seconds)

    response = requests.get(url, **kwargs)
    response.raise_for_status()
    return response
```

### `Retry-After` Parsing

`Retry-After` can be either a number of seconds or an HTTP date. Support both forms, but keep the behavior bounded.

```python
def _retry_after_seconds(response: requests.Response) -> float:
    raw_retry_after = response.headers.get("Retry-After")
    delay_seconds = DEFAULT_RETRY_AFTER_SECONDS

    if raw_retry_after:
        delay_seconds = _parse_retry_after(raw_retry_after)

    delay_seconds = max(0.0, delay_seconds)
    return min(delay_seconds, MAX_RETRY_AFTER_SECONDS)
```

Implementation detail: `_parse_retry_after(...)` can use simple float parsing for numeric values and `email.utils.parsedate_to_datetime(...)` for HTTP-date values. Invalid values should fall back to `DEFAULT_RETRY_AFTER_SECONDS`.

### Refactor Targets

Replace existing `requests.get(...)` calls in `source/kovaaks/api_service.py`:

- `get_playlist_data`
- `get_benchmark_json`
- `get_leaderboard_scores`
- `get_user_scenario_total_play` pagination loop
- `search_scenario_exact`

Because `_get_with_retry(...)` still calls `requests.get(...)`, many existing tests that monkeypatch `api_service.requests.get` should continue to work with minimal changes. Tests that inspect response shape may need `FakeResponse.status_code = 200` and `FakeResponse.headers = {}` defaults.

### Opportunistic Cleanup

`docs/tech_debt.md` currently tracks debug `print(...)` statements in `get_benchmark_json`. Since this proposal touches that function's request path, it is reasonable to remove those prints in the same implementation PR.

Keep broader tech-debt cleanup out of scope.

## M1 Interaction

This helper reduces cold-cache playlist table fragility, but it does not replace careful M1 fetch design.

M1 should still:

- read local/cache data first where possible
- avoid duplicate fetches for the same leaderboard ID
- keep the table executor at a modest worker count
- render per-row `UNKNOWN` / `N/A` if a request still fails after retry
- avoid user-facing warnings for a recovered 429

If a row fails after retry, the existing service-layer behavior should decide whether it becomes `UNKNOWN`, `UNRANKED`, or a valid partial result.

## Test Plan

Add tests in `tests/test_api_service.py`.

1. **Retries once on 429**
   - First response has `status_code = 429`.
   - Second response has `status_code = 200`.
   - Helper returns the second response.
   - `requests.get` is called twice.
   - `time.sleep` is called with the expected delay.

2. **Honors numeric `Retry-After`**
   - First response has `Retry-After: 1.25`.
   - Sleep receives `1.25`.

3. **Caps large `Retry-After`**
   - First response has `Retry-After: 60`.
   - Sleep receives `MAX_RETRY_AFTER_SECONDS`.

4. **Falls back on invalid `Retry-After`**
   - First response has `Retry-After: nonsense`.
   - Sleep receives `DEFAULT_RETRY_AFTER_SECONDS`.

5. **Does not retry non-429 4xx**
   - Response has `status_code = 404`.
   - Helper raises `HTTPError`.
   - `requests.get` is called once.

6. **Gives up after second 429**
   - Both responses have `status_code = 429`.
   - Helper raises `HTTPError`.
   - `requests.get` is called twice.

7. **Non-HTTP exceptions still propagate**
   - `requests.get` raises `requests.ConnectionError`.
   - Helper propagates the exception.
   - No retry attempt occurs.

8. **Existing wrapper calls use retry helper**
   - At least one endpoint wrapper test verifies `get_leaderboard_scores(...)` goes through `_get_with_retry(...)` and preserves params/timeout.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest tests
uv run ruff check source tests
uv run python -m compileall source tests
```

## Trade-Offs

| Decision | Alternative | Reason |
|---|---|---|
| GET-only helper | Method-agnostic `_request_with_retry` | Current callers are GET-only; retrying non-idempotent methods should be a future decision. |
| Single retry | Multiple retries / exponential backoff | Smallest useful guardrail for transient bursts. Avoids long UI stalls. |
| Honor `Retry-After` with cap | Fixed sleep only | More respectful of API guidance while keeping app latency bounded. |
| Retry 429 only | Retry 5xx/network errors too | 429 has clear "try later" semantics. Broader retries can mask unrelated failures. |
| Module logger only on recovered retry | UI notification | A recovered retry is not user-actionable. If retry fails, existing service-layer error handling reaches the UI where appropriate. |
| Keep M1 executor separate | Put worker throttling in retry helper | Retry handles one request. M1 controls burst size and duplicate work. |

## Documentation Updates If Implemented

- Add a KovaaK's API notes section for 429 behavior and retry policy.
- Add a decision-log entry: "Retry KovaaK's GET 429s Once".
- Remove the `get_benchmark_json` debug-print tech-debt entry if cleaned up in the implementation PR.

## Open Questions

None blocking. Defaults proposed:

- `DEFAULT_RETRY_AFTER_SECONDS = 0.5`
- `MAX_RETRY_AFTER_SECONDS = 5.0`
- retry count: one retry after the original attempt
