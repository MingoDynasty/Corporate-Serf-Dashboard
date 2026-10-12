# 2026-06-21: Keep The Hand-Rolled GET Retry; Defer urllib3 `Retry` Migration

Status: Accepted

Decision: Keep the hand-rolled retry helpers in `source/kovaaks/api_service.py`
(`_get_with_retry`, `_retry_after_seconds`) instead of mounting a urllib3
`HTTPAdapter(max_retries=Retry(...))` on the thread-local sessions. Reconsider
only when requirements grow past one retry (exponential backoff with jitter, a
broader `status_forcelist` such as 503, separate connect/read budgets).

Why: The happy path maps cleanly onto urllib3 `Retry`, but a faithful migration
is not a clean delete. It would lose the 0.5s default delay on a 429 without
`Retry-After` (urllib3 sleeps 0s on the first retry), change the exhaustion
exception types the tests assert on (`HTTPError`/bare timeout become
`RetryError`/wrapped `ConnectionError`), downgrade recovered-retry logging from
WARNING to a DEBUG line on urllib3's logger, and still require a wrapper for the
per-request timeout default. Preserving the 5s `Retry-After` cap needs
`retry_after_max`, which requires pinning `urllib3>=2.6` — currently only a
transitive dependency. Net-neutral complexity plus a full test rewrite does not
clear the bar for replacing working, ratified code.

Consequences: The retry layer stays per-request and hand-rolled; the score-aware
rank refresh loop sits on top of it and relies on its contract (one inner retry,
bounded sleeps). If migrating later, the minimal-drift recipe is: one
module-level `Retry(total=1, status=1, connect=1, read=1, status_forcelist=[429],
allowed_methods={"GET"}, retry_after_max=5, raise_on_status=False)` mounted on
both schemes of each thread-local session, a thin wrapper retained for the
timeout default and WARNING log, and an explicit `urllib3>=2.6` floor. The full
analysis lives in git history as `docs/api_retry_urllib3_migration_proposal.md`.
