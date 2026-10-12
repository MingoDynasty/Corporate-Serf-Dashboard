# 2026-04-28: Retry KovaaK's GET Transient Failures Once

Status: Superseded in part by the 2026-07-13 timeout/read-timeout decision — `requests.Timeout` is no longer in the retry set (read timeouts fail immediately); the `429`/`Retry-After` policy and the `requests.ConnectionError` retry stand

Decision: KovaaK's GET requests should retry exactly once on HTTP `429 Too Many Requests`, `requests.Timeout`, and `requests.ConnectionError`. `429` retries should honor `Retry-After` when present and cap the wait.

Why: Playlist scenario overview can create bursty cold-cache rank and total lookups. KovaaK's can also occasionally exceed the current read timeout for one row while adjacent requests succeed. A single bounded retry handles transient failures without turning the retry helper into a full scheduler or hiding unrelated failures.

Consequences: Retry remains GET-only. Non-429 HTTP failures and unexpected exceptions continue through the existing service-layer error handling. Recovered retries are logged but are not user-facing notifications.
