# KovaaK's API Notes

Living notes for the KovaaK's webapp backend endpoints this project relies on.

These endpoints are treated as external contracts that may change. When we discover a new quirk, update this file and add regression coverage when practical.

Base URL:

```text
https://kovaaks.com/webapp-backend
```

## Rate Limiting

KovaaK's may return HTTP `429 Too Many Requests` during bursty access patterns, especially cold-cache playlist table loads that fetch many scenario ranks and totals.

Project retry policy:

- Retry GET requests once on HTTP `429`.
- Retry GET requests once on narrow transient network failures: `requests.Timeout` and `requests.ConnectionError`.
- Honor `Retry-After` when present.
- Fall back to a short default delay when `Retry-After` is absent or invalid.
- Cap the retry delay so the UI does not stall for a long server-requested wait.
- Do not retry non-429 HTTP failures or unexpected exceptions.
- Do not show a UI notification for a recovered retry. If the retry also fails, normal service-layer failure handling applies.

Connection reuse:

- KovaaK's GET requests use one `requests.Session` per worker thread.
- Thread-local sessions allow keep-alive connection pooling during cold-cache playlist table loads without sharing one mutable `Session` across concurrent workers.

## Endpoint Summary

| Endpoint | Project Use | Authoritative For Current Rank? | Notes |
| --- | --- | --- | --- |
| `/leaderboard/scores/global` | Current rank lookup and leaderboard total lookup | Yes | Use with `leaderboardId`. Add `usernameSearch` only for user rank lookup. |
| `/user/scenario/total-play` | Metadata hydration/upsert for `scenarioName -> leaderboardId` | No | Can lag behind current score/rank. Returns `null` for unknown usernames. |
| `/scenario/popular` | Exact-name fallback for leaderboard ID resolution | No | Search can return many variants; require exact `scenarioName` match. |
| `/benchmarks/player-progress-rank-benchmark` | Existing benchmark progress flow | For benchmark playlists only | Requires benchmark ID, so it does not cover all playlists. |
| `/playlist/playlists` | Playlist discovery/metadata inspection | No | Does not include leaderboard IDs in observed responses. |

## `/leaderboard/scores/global`

Example current-rank lookup:

```text
GET /leaderboard/scores/global?leaderboardId=98330&page=0&max=100&usernameSearch=MingoDynasty
```

Example total-ranked-players lookup:

```text
GET /leaderboard/scores/global?leaderboardId=98330&page=0&max=1
```

Fields we rely on:

- top-level `total`: row count for the query
- `data[].rank`
- `data[].score`
- `data[].steamId`
- `data[].webappUsername`
- `data[].steamAccountName`

Important behavior:

- With `usernameSearch`, `total` is the number of search matches, not the leaderboard population.
- Without `usernameSearch`, `total` is the total number of ranked players for that leaderboard.
- `usernameSearch` is partial/fuzzy enough that a search like `Mingo` can return multiple players.
- Prefer exact `steamId` match when configured.
- If `steamId` does not match but exact `webappUsername` does, keep the username match and surface a warning.
- Current score/rank should come from this endpoint, not `total-play`.

Failure handling:

- Rank lookup failures should produce `ScenarioRankInfo(status=UNKNOWN, error_message=...)`.
- Leaderboard total lookup is enrichment only. If total lookup fails, preserve the valid ranked/unranked result.

## `/user/scenario/total-play`

Example:

```text
GET /user/scenario/total-play?username=MingoDynasty&page=0&max=100&sort_param[]=count
```

Fields we rely on:

- `data[].scenarioName`
- `data[].leaderboardId`
- pagination fields: `page`, `max`, `total`

Important behavior:

- Useful for initializing and upserting the permanent local `scenarioName -> leaderboardId` cache.
- Not reliable for current score or current rank; observed values can lag behind the leaderboard endpoint.
- Unknown usernames can return raw JSON `null`, not an object response.
- Some rows may have `rank: null`; generated models should allow that where the field is retained.
- Cache each page separately and use all fetched pages for metadata hydration.

Failure handling:

- `null` response means the configured KovaaK's username is unknown and should become an explicit unknown/error state, not `UNRANKED`.
- Cache failures should not block active fallback lookup. If metadata is missing, resolve the selected scenario lazily through KovaaK's APIs.

## `/scenario/popular`

Example:

```text
GET /scenario/popular?page=0&max=100&scenarioNameSearch=VT%20Pasu%20Intermediate%20S5
```

Fields we rely on:

- `data[].scenarioName`
- `data[].leaderboardId`
- `data[].counts.entries`

Important behavior:

- Search can return many variants for a scenario name.
- Require exact `scenarioName` match before saving a leaderboard ID.
- First page with `max=100` is expected to be enough for now; revisit only if real data disproves this.

## `/playlist/playlists`

Example:

```text
GET /playlist/playlists?page=0&max=20&search=KovaaKsGearingMehLowground
```

Observed behavior:

- Returns playlist-level metadata and `scenarioList`.
- `scenarioList` includes scenario names/authors/aim types.
- Observed responses do not include `leaderboardId`, so this endpoint is not enough for rank lookup.

## `/benchmarks/player-progress-rank-benchmark`

Existing app behavior uses this endpoint for benchmark progress.

Important limitation:

- Requires a benchmark ID.
- Works for benchmark playlists, but not every playlist is a benchmark.
- Scenario rank display should not depend on this endpoint.

## Derived Data

Percentile is derived from current rank and unfiltered leaderboard total:

```python
percentile = ((total_players - rank + 0.5) / total_players) * 100
```

Display with exactly two decimal places. Do not persist percentile in rank cache.
