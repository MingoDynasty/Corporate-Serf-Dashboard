# 2026-04-27: Make Leaderboard Total Enrichment Best-Effort

Status: Accepted (amended by
[2026-09-19](2026-09-19-a-clicked-refresh-re-reads-the-leaderboard-total.md): a
failed total lookup now falls back to the last cached count for every caller
rather than returning the result untouched)

Decision: Leaderboard total lookup should never invalidate a valid rank or unranked result.

Why: Total players and percentile are enrichment data. If total lookup fails because of network errors, malformed responses, validation failures, or cache I/O issues, showing the valid rank alone is better than falling back to `N/A`.

Consequences: `_with_leaderboard_total()` catches expected total-enrichment failures, logs them, and returns the original `ScenarioRankInfo`.
