# 2026-04-29: Cache Leaderboard Totals For One Week

Status: Accepted (amended by
[2026-09-19](2026-09-19-a-clicked-refresh-re-reads-the-leaderboard-total.md): the
TTL governs automatic paths only, and both board-authoritative callers — a
user-clicked Refresh and the PB-triggered freshness chain — bypass it)

Decision: `leaderboard_total_cache_ttl_hours` defaults to `168`, matching `scenario_rank_cache_ttl_hours`.

Why: Leaderboard total player counts are expected to increase slowly. For large leaderboards, a mildly stale total count changes displayed percentile by less than the UI's two-decimal precision in most cases, while avoiding daily cold-cache total fetches across every playlist scenario.

Consequences: Total-count freshness remains configurable. If users notice stale total counts causing misleading displays, revisit the TTL or add a targeted refresh flow.
