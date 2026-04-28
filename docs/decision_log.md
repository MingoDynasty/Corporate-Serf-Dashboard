# Decision Log

Durable project decisions that future contributors and agents should preserve unless a newer entry supersedes them.

Use this log for decisions that are hard to reverse, cross-cutting, based on external API behavior, or likely to be questioned later. Do not record every small implementation choice.

When a decision changes, keep the old entry and mark it `Superseded`. Add a new entry explaining what changed, why, and any migration notes.

## Status Values

- `Proposed`: under consideration, not yet agreed.
- `Accepted`: current agreed decision.
- `Superseded`: replaced by a newer decision.
- `Rejected`: considered and intentionally not chosen.

## 2026-04-27: Use JSON Files For Runtime API Caches

Status: Accepted

Decision: Store current API cache data as JSON files under `cache/`.

Why: The current cache use cases are simple key-value lookups with short or medium TTLs. JSON keeps the implementation transparent, easy to inspect, and low-friction.

Consequences: Cache reads must tolerate missing, malformed, stale, or partially-written files. Cache writes should be atomic where practical. Reconsider SQLite when we need rank history, multi-record queries, or stronger transactional guarantees.

## 2026-04-27: Treat `total-play` As Metadata Only

Status: Accepted

Decision: Use `/user/scenario/total-play` only to hydrate or upsert scenario metadata such as `scenarioName -> leaderboardId`.

Why: The endpoint can lag behind current leaderboard scores and ranks. `/leaderboard/scores/global` is the authoritative source for current rank.

Consequences: Current-rank lookup should not trust score or rank data from `total-play`. The endpoint remains useful for cache initialization and metadata discovery.

## 2026-04-27: Keep KovaaK's API Details Behind `ScenarioRankInfo`

Status: Accepted

Decision: UI code consumes `ScenarioRankInfo` and should not know which KovaaK's endpoint produced the data.

Why: Endpoint details, fallback behavior, cache rules, and expected API failures belong in the service layer. This keeps Dash callbacks focused on rendering.

Consequences: Expected KovaaK's API/domain failures should become `ScenarioRankInfo(status=UNKNOWN, error_message=...)` in `api_service.py`. UI code can render `RANKED`, `UNRANKED`, or `UNKNOWN` without duplicating endpoint logic.

## 2026-04-27: Prefer Steam ID Matching When Configured

Status: Accepted

Decision: When `steam_id` is configured, prefer it for leaderboard identity matching. If Steam ID matching fails but exact username matching succeeds, keep the rank result and surface a warning.

Why: `usernameSearch` can return partial matches. Steam ID is the strongest identity check, but a mistyped Steam ID should not hide otherwise valid exact-username rank data.

Consequences: The warning is transient and derived from current config each time rank info is returned. It should not be persisted in rank cache.

## 2026-04-27: Make Leaderboard Total Enrichment Best-Effort

Status: Accepted

Decision: Leaderboard total lookup should never invalidate a valid rank or unranked result.

Why: Total players and percentile are enrichment data. If total lookup fails because of network errors, malformed responses, validation failures, or cache I/O issues, showing the valid rank alone is better than falling back to `N/A`.

Consequences: `_with_leaderboard_total()` catches expected total-enrichment failures, logs them, and returns the original `ScenarioRankInfo`.

## 2026-04-27: Use The Midpoint Percentile Formula

Status: Accepted

Decision: Derive percentile with:

```python
percentile = ((total_players - rank + 0.5) / total_players) * 100
```

Why: This matches the KovaaK's-style percentile behavior we agreed to use.

Consequences: Percentile is display-only metadata derived when rank info is returned. It is not stored in rank cache. No tiny-leaderboard special casing is planned, so `rank 1 of 1` displays `50.00%`.

## 2026-04-27: Keep KovaaK's API Findings In A Dedicated Notes File

Status: Accepted

Decision: Track KovaaK's endpoint behavior, relied-upon fields, and discovered quirks in `docs/kovaaks_api_notes.md`.

Why: We are probing unofficial or lightly documented API behavior across multiple milestones. Keeping API lore in one living document helps future agents avoid rediscovering endpoint semantics from chat history.

Consequences: When new endpoint behavior or failure modes are discovered, update the notes file and add regression coverage when practical.
