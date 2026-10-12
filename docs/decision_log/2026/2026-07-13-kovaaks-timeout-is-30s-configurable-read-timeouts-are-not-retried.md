# 2026-07-13: KovaaK's Timeout Is 30s (Configurable); Read Timeouts Are Not Retried

Status: Accepted

Decision: All KovaaK's API requests share one timeout, default 30 seconds,
configurable via `kovaaks_api_timeout_seconds` in `config.toml` and applied at
app startup through `api_service.set_request_timeout()`. `_get_with_retry`
retries only `requests.ConnectionError` (which covers `ConnectTimeout`); a
`ReadTimeout` fails immediately instead of being retried.

Supersedes: the `requests.Timeout` clause of the 2026-04-28 transient-retry
decision. The `429`/`Retry-After` policy and the `ConnectionError` retry from
that entry stand, and the 2026-06-21 keep-the-hand-rolled-retry decision is
reaffirmed, not revisited.

Rationale: measured 2026-07-13 during a KovaaK's slow spell,
`/leaderboard/scores/global` latency ranged 9–28s while responses stayed
valid — a Postman probe succeeded after ~28s, and in-app fetches succeeded at
9.0–9.4s, just under the old hardcoded 10s wire. With a 10s timeout every
attempt during the spell died, and because the stale-rank fallback is
deliberately read-only (see the 2026-07-12 entry), the same expired cache
entry re-timed-out on every page open — one expired scenario added ~20s to
every playlist load until a fetch succeeded. A read timeout also does not
cancel the server-side query, so the old immediate retry doubled KovaaK's
load for almost nothing (2 of 63 retries succeeded that night); a connection
error, by contrast, means the request never reached the server and remains
safe to retry. 30s clears the observed worst case, and the config knob is the
escape hatch if slow spells drift past it.

Constraints:

- Deliberately a single timeout value — no connect/read split and no
  urllib3 `Retry` adoption (the 2026-06-21 entry holds the full migration
  analysis). Beyond that entry's reasons: the per-retry warnings in
  `_get_with_retry` are the primary forensic log, and the benchmark importer
  depends on its per-call `attempts`/`backoff_seconds` knobs, which
  `requests` cannot express per request through adapter-mounted `Retry`.
- The importer shares the helper, so its retry schedule now governs only
  connection errors and 429s; a read timeout fails the sharecode
  immediately.
