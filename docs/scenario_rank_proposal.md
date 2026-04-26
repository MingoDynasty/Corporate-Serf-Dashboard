# Scenario Stats Current Rank Feature Proposal

## Goal

Display the user's current leaderboard rank for the selected scenario under the Scenario Stats section of the home page.

Phase 1 display:

```text
Rank: #11263
Rank: Unranked
Rank: N/A
```

Phase 2 display:

```text
Rank: 11263/18342 (38.6% Percentile)
Rank: Unranked
Rank: N/A
```

The first milestone prioritizes correctness over completeness. A stale rank is worse than no rank.

## Key Discovery

The `/user/scenario/total-play` endpoint is useful, but it is not authoritative for current score or current rank.

For `VT Pasu Intermediate S5`, `total-play` returned:

```text
leaderboardId: 98330  |  rank: 13125  |  score: 799.31
```

But the leaderboard endpoint with `usernameSearch` returned fresher data:

```text
rank: 11263  |  score: 863.93
```

Conclusion: `total-play` must not be used as the source of truth for current rank. It can still be used as a metadata source for discovering `scenarioName <-> leaderboardId` mappings.

## Display States

| State | Meaning | Display |
|---|---|---|
| `RANKED` | Leaderboard exists; user has a score on it | `Rank: #11263` |
| `UNRANKED` | Leaderboard exists; user has no score | `Rank: Unranked` |
| `UNKNOWN` | Could not resolve leaderboard, or API failed | `Rank: N/A` |

`Unranked` and `N/A` are intentionally different. `Unranked` is a known state. `N/A` means something went wrong or the leaderboard could not be found.

## Data Sources

### Current Rank

Use the leaderboard endpoint with `usernameSearch`:

```text
GET /leaderboard/scores/global?leaderboardId={leaderboard_id}&page=0&max=50&usernameSearch={username}
```

This is the authoritative source for the displayed current rank.

The endpoint performs partial matching. For example, searching `Mingo` can return `Domingo`, `MingoDynasty`, and `mingoaims`. The app must not trust the first result. It should search with the most specific configured identity available and choose the matching player deterministically:

1. Prefer exact `steamId == steam_id`, if `steam_id` is configured.
2. Otherwise prefer exact `webappUsername == kovaaks_username`.
3. Otherwise prefer exact `steamAccountName == kovaaks_username`.
4. If there is no exact match, treat the player as `UNRANKED`.

`steam_id` is included in Milestone 1 because it guarantees we select the correct player even when `usernameSearch` returns multiple partial matches.

If a configured `steam_id` does not match any returned player, but exact username matching does find a player, the app should still use the username match so rank lookup can continue. In that case, attach a warning to the rank result and surface it through `dash_logger.warning(...)` so the user knows their configured Steam ID is probably wrong.

### Scenario To Leaderboard ID

Resolve the selected scenario name to a `leaderboardId` via this fallback chain:

```text
selected_scenario
    |
    v
1. Permanent local cache: scenario_name_to_leaderboard_id.json
    |
    |- HIT  -> leaderboardId
    `- MISS
        |
        v
2. total-play metadata cache, if user has played this scenario
    |
    |- HIT  -> leaderboardId; periodically upsert all discovered mappings into permanent cache
    `- MISS
        |
        v
3. Scenario search endpoint: /scenario/popular?scenarioNameSearch=...
    |
    |- exactly one exact scenarioName match -> leaderboardId, upsert into permanent cache
    |- no exact match                       -> UNKNOWN
    |- multiple exact matches               -> UNKNOWN, log warning
    `- API failure                          -> UNKNOWN
```

The scenario search endpoint does fuzzy or prefix matching. Searching `VT Pasu Intermediate S5` can return variants such as `VT Pasu Intermediate S5 Multi`, `VT Pasu Intermediate S5 Speed`, and `VT Pasu Intermediate S5 Hard`. The app must filter returned rows by exact `scenarioName == selected_scenario`.

Implementation detail: do not blindly use `data[0]`. Filter all returned rows for exact matches. Request `max=100` and do not paginate in the first implementation. It is very unlikely that an exact match will be absent from the first 100 results; most exact matches should appear within the first 10 results.

### Playlist API

The playlist API is not a direct leaderboard-ID source:

```text
GET /playlist/playlists?page=0&max=20&search={playlist_code}
```

The observed response includes playlist-level metadata and scenario entries with fields such as `scenarioName`, `author`, `aimType`, `playCount`, `webappUsername`, and `steamAccountName`, but it does not return `leaderboardId`.

Playlist metadata can still help the app know which scenario names belong to an imported playlist, but it cannot resolve current rank by itself.

### Leaderboard Total

This is Phase 2 only:

```text
GET /leaderboard/scores/global?leaderboardId={leaderboard_id}&page=0&max=1
```

The unfiltered response `total` field is the number of ranked players. Do not use `total` from the `usernameSearch` response, because that represents search matches.

## Configuration

New fields in `config.toml` / `example.toml`:

```toml
# KovaaK's webapp username. Leave empty to disable rank lookups.
kovaaks_username = ""

# Optional Steam ID. Preferred when username search is ambiguous, such as when
# your username is a substring of another player's username.
steam_id = ""

# How long to cache total-play metadata, in hours.
scenario_metadata_cache_ttl_hours = 24

# How long to cache per-scenario rank data, in hours.
# A long TTL is acceptable because new high scores trigger immediate refreshes.
scenario_rank_cache_ttl_hours = 168

# How long to cache leaderboard totals, in hours. Used for percentile in Phase 2.
leaderboard_total_cache_ttl_hours = 24
```

An empty `kovaaks_username` disables rank lookups. An empty `steam_id` falls back to exact username matching.

## Caching

Use JSON files on disk. SQLite is not necessary until rank history, joins, or multi-user support is needed.

### Directory Structure

```text
cache/
  scenario_leaderboards/
    scenario_name_to_leaderboard_id.json   # permanent mapping, no TTL

  user_scenario_total_play/
    MingoDynasty.json                      # merged seeding metadata, 24h TTL
    MingoDynasty/
      page_0.json                         # raw total-play API page
      page_1.json                         # raw total-play API page

  leaderboard_user_rank/
    MingoDynasty/
      98330.json                         # current rank, 168h TTL

  leaderboard_totals/
    98330.json                             # total players, 24h TTL, Phase 2
```

Rank and total are stored in separate files because they have different TTLs and are fetched via different calls. Coupling them would force a total re-fetch every time the short-lived rank cache expires.

### Permanent Mapping Cache

`scenarioName -> leaderboardId` is unlikely to change. Once learned, save it indefinitely.

```json
{
  "VT Pasu Intermediate S5": {
    "leaderboard_id": 98330,
    "source": "total-play",
    "fetched_at": "2026-04-26T03:30:00Z"
  }
}
```

Rules:

- No TTL.
- Any source that reveals a mapping upserts this file.
- Upserts should hold a process-local cache lock across the full read-modify-write.
- Writes should go to a temporary JSON file first, then atomically replace the target file so concurrent readers never see a partially written mapping.
- `source` is for debuggability only.
- Possible sources: `/user/scenario/total-play`, scenario search, benchmark data when available.
- Not a source: `/playlist/playlists`, because the observed response does not include `leaderboardId`.

### Total-Play Cache

`user_scenario_total_play/{username}.json` stores a merged app-facing snapshot from `/user/scenario/total-play`. Raw API pages are also cached under `user_scenario_total_play/{username}/page_{n}.json`.

Purpose:

- Discover leaderboard IDs for scenarios the user has played.
- Seed and continually enrich the permanent mapping cache.
- Collect play-count metadata if useful later.

Not trusted for:

- current rank
- current score
- percentile

Initialization behavior:

- If the `total-play` metadata cache is missing or stale and `kovaaks_username` is configured, fetch `/user/scenario/total-play`.
- Fetch and cache each raw page, then write a merged `{username}.json` response for simple future reads.
- Treat a full page as ambiguous and probe the next page. This avoids trusting a page-0-only cache when the API under-reports `total`.
- After each successful `total-play` fetch, upsert all discovered `scenarioName -> leaderboardId` mappings into the permanent mapping cache.
- If the permanent cache already has entries, preserve them and add newly discovered scenarios.
- This makes `total-play` a recurring metadata hydrator, not just a one-time initializer.
- `total-play` should only upsert metadata. It should not overwrite current rank or current score values.
- If KovaaK's returns literal `null` for the configured username, cache a structured unknown-user marker and return `UNKNOWN` rank state rather than `UNRANKED`.
- If total-play metadata hydration fails due to network/API failure, log it and continue to exact scenario search. A metadata cache miss should not block the fallback chain.

Conflict behavior:

- If a scenario name is new, insert it.
- If a scenario name already exists with the same `leaderboardId`, keep it and optionally update debug metadata such as `last_seen_at` or `last_seen_source`.
- If a scenario name already exists with a different `leaderboardId`, do not silently overwrite it. Keep the existing mapping and log a warning until a deliberate conflict policy exists.

### Current Rank Cache

`leaderboard_user_rank/{safe_username}/{leaderboard_id}.json` stores current rank data:

```json
{
  "status": "RANKED",
  "rank": 11263,
  "leaderboard_id": 98330,
  "scenario_name": "VT Pasu Intermediate S5",
  "score": 863.93,
  "matched_steam_id": "76561197986713986",
  "fetched_at": "2026-04-26T03:30:00Z"
}
```

Rules:

- TTL: `scenario_rank_cache_ttl_hours`, default 168 hours.
- Cache key includes the sanitized username as a directory and the leaderboard ID as the filename.
- Username sanitization should replace characters that are invalid or awkward in Windows paths before writing cache files.
- The configured Steam ID is not part of the path. Identity facts live in the JSON payload via `matched_steam_id`.
- Automatically refresh on a new high score for that scenario.
- Serialize rank status with stable `StrEnum` values such as `"RANKED"`, `"UNRANKED"`, and `"UNKNOWN"`.
- Cache files may include `scenario_name`, `score`, `matched_steam_id`, and `error_message` for debuggability.
- `warning_message` is not stored. It is derived at read time from the current configured Steam ID and cached `matched_steam_id`, then surfaced through the UI if needed.

Rationale:

- Once a rank is known for a scenario, it does not need frequent polling.
- The most important freshness event is a new local high score, and that event triggers an immediate refresh.
- Rank can still drift downward as other players improve, but Scenario Stats is primarily meant to reflect the user's local progress, not provide a constantly live leaderboard feed.
- A long TTL avoids unnecessary API calls during normal scenario switching.

If stale rank data becomes a real user-facing issue, revisit the TTL without changing the rest of the design.

### Leaderboard Total Cache

`leaderboard_totals/{leaderboard_id}.json` is Phase 2 only.

Rules:

- TTL: `leaderboard_total_cache_ttl_hours`, default 24 hours.
- Stores the unfiltered leaderboard `total`.
- Separate from rank cache because total has a different freshness requirement.

### TTL And Corruption Handling

All TTL checks can use file `mtime`:

```python
def _is_cache_fresh(cache_file: Path, ttl_seconds: int) -> bool:
    return cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < ttl_seconds
```

All cache reads should be wrapped in `try/except`. A missing or malformed file should fall back to a fresh API fetch, not crash the app.

All JSON cache writes should be atomic: write the complete JSON payload to a temporary file in the same directory, flush it, then replace the destination with `os.replace(...)`. This prevents UI/background refresh races from reading an empty or half-written JSON file.

### Leaderboard ID Type

`total-play` returns `leaderboardId` as a string, for example `"98330"`. Other endpoints treat it as an integer. Cast to `int` on ingestion so the rest of the codebase uses one type.

## Rank Cache Invalidation

### Normal Path

Rank is served from cache while within `scenario_rank_cache_ttl_hours`. On cache miss or expiry, fetch fresh from the leaderboard endpoint.

### High-Score-Triggered Refresh

When `file_watchdog.py` detects a new stats file:

1. Parse the run into `RunData`.
2. Determine whether the run is a new high score for that scenario.
3. If it is a new high score and rank lookups are configured, enqueue a background rank refresh for that scenario.
4. The background task calls `/leaderboard/scores/global` with `usernameSearch`.
5. Save the result to the rank cache.
6. The Scenario Stats UI picks up the refreshed rank on its next update cycle.

Why background? Keep the watchdog file-handling path fast. A network call in the hot path could delay UI notification for every new run.

Why only on new high score? A run that does not beat the existing high score cannot improve the player's leaderboard rank. Refreshing would usually be wasted API work.

### Background Execution Options

There are three reasonable options for the high-score-triggered refresh:

| Option | Pros | Cons |
|---|---|---|
| Synchronous call in watchdog path | Simplest implementation; easiest error handling | Blocks file handling on network I/O; a slow or unavailable KovaaK's API could delay UI updates |
| One-off background thread | Simple; avoids blocking watchdog; little infrastructure | Harder to cap concurrency; repeated PBs could create multiple simultaneous threads |
| Shared executor | Still simple; avoids blocking watchdog; caps concurrency; centralizes future background work | Slightly more setup than one-off threads; errors need to be logged from futures |

Recommendation: use a small shared `ThreadPoolExecutor(max_workers=2)`. Resource usage is still extremely low, it avoids blocking the watchdog path, and it gives enough room for more than one quick refresh if multiple high scores are discovered close together.

Realistically, refresh failure should usually mean the KovaaK's API is unavailable. The failure should be logged with the normal module logger and surfaced to the UI through `dash_logger.error(...)`. `dash_logger` comes from `source.utilities.dash_logging.get_dash_logger`, which uses the existing `NotificationsLogHandler` and `notification-container` path. The user will see their new high score in the chart, so it would be jarring if the rank data silently failed to update.

### App Not Running Edge Case

There is one important edge case: the user may hit a new high score while the app is not running. In that case, the watchdog will not see the new file event when it happens, so high-score-triggered refresh will not fire immediately.

The long rank TTL still helps here. Once the cached rank expires, the app will refresh rank on normal lookup and eventually catch up. For the first implementation, `scenario_rank_cache_ttl_hours = 168` is acceptable. It avoids hammering the KovaaK's API and puts some responsibility on the user to keep the app running if they expect rank to update immediately after a PB.

## Internal Models

```python
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ScenarioRankStatus(StrEnum):
    RANKED = "RANKED"
    UNRANKED = "UNRANKED"
    UNKNOWN = "UNKNOWN"


class ScenarioRankInfo(BaseModel):
    status: ScenarioRankStatus
    rank: int | None = None
    leaderboard_id: int | None = None
    scenario_name: str | None = None
    score: float | None = None
    matched_steam_id: str | None = None
    fetched_at: datetime | None = None
    error_message: str | None = None
    warning_message: str | None = Field(default=None, exclude=True)
    total_players: int | None = None  # populated in Phase 2
```

The UI callback consumes only `ScenarioRankInfo`. No endpoint-specific logic belongs in `home.py`.

When writing `ScenarioRankInfo` to JSON, use the stable `ScenarioRankStatus` string values directly. Cache files should contain readable values such as `"RANKED"`, `"UNRANKED"`, and `"UNKNOWN"`. When reading from JSON, reconstruct with `ScenarioRankStatus(raw_status)`.

`matched_steam_id` is the stable fact captured from the leaderboard response. `warning_message` is intentionally transient: the service layer derives it from the current config each time rank info is returned. This prevents stale warnings from surviving a config correction.

Expected KovaaK's API/domain failures should be converted to `ScenarioRankInfo(status=UNKNOWN, error_message=...)` inside `api_service.py`. Unexpected application bugs may still raise and can be handled by UI/background safety nets.

## Expected Code Changes

### Config

Add the config fields listed above to `example.toml` and `ConfigData`.

### API Models

Add:

- `UserScenarioTotalPlayEntry`
- `UserScenarioTotalPlayResponse`
- scenario search response models
- `ScenarioRankStatus`
- `ScenarioRankInfo`

Reuse existing `LeaderboardAPIResponse` and `RankingPlayer` for the `usernameSearch` response where possible.

Generate the initial response models for `/user/scenario/total-play` and `/scenario/popular` with `datamodel-code-generator` from representative JSON fixtures. Review the generated classes before committing them: keep the fields needed for this feature and make unstable or irrelevant nested fields optional or omit them so rank lookup does not become brittle.

### API Service

Add functions behind a clean abstraction. UI callbacks should only call `get_scenario_rank_info`; all cache and endpoint logic stays in this layer.

`get_leaderboard_scores(...)` should remain a thin KovaaK's API wrapper. It should not read or write raw leaderboard cache files. Cache behavior belongs in domain-specific helpers such as current-rank cache and, later, leaderboard-total cache.

```python
# leaderboardId mapping cache
get_cached_leaderboard_id(scenario_name: str) -> int | None
save_leaderboard_id(scenario_name: str, leaderboard_id: int, source: str) -> None

# total-play metadata and recurring mapping hydration
get_user_scenario_total_play(username: str) -> UserScenarioTotalPlayResponse
hydrate_leaderboard_id_cache(username: str) -> None

# scenario search
search_scenario_exact(scenario_name: str) -> int | None

# leaderboardId resolution
resolve_leaderboard_id(scenario_name: str, username: str | None) -> int | None

# rank cache
get_cached_scenario_rank(leaderboard_id: int, username: str) -> ScenarioRankInfo | None
save_scenario_rank(leaderboard_id: int, username: str, rank_info: ScenarioRankInfo) -> None

# live rank fetch
fetch_scenario_rank(leaderboard_id: int, username: str, steam_id: str | None = None) -> ScenarioRankInfo

# main entry points
get_scenario_rank_info(scenario_name: str, username: str | None, steam_id: str | None = None) -> ScenarioRankInfo
refresh_scenario_rank(scenario_name: str, username: str, steam_id: str | None = None) -> ScenarioRankInfo
```

Add new entries to `Endpoints`:

```python
SEARCH_SCENARIO = "/scenario/popular"
USER_SCENARIO_TOTAL_PLAY = "/user/scenario/total-play"
```

### Data Service / Watchdog

On new high score detection:

- Trigger `refresh_scenario_rank` through a shared `ThreadPoolExecutor(max_workers=2)`.
- Do not block the watchdog hot path.
- Let the normal update path notify the UI.
- If the background task fails, log with the normal module logger and call `dash_logger.error(...)` so the user understands when rank did not update after a new high score.

High-score detection should live near the existing data update logic, not in the UI callback.

### UI

Add a separate Dash callback for rank, independent of `get_scenario_num_runs`, so local stats render immediately while rank resolves.

Recommended behavior:

- Wrap the rank display in `dcc.Loading`.
- Callback does one thing: `get_scenario_rank_info(selected_scenario, config.kovaaks_username, config.steam_id)`.
- Render based on `ScenarioRankInfo.status`.

```python
match rank_info.status:
    case ScenarioRankStatus.RANKED:
        if rank_info.warning_message:
            dash_logger.warning(rank_info.warning_message)
        return f"Rank: #{rank_info.rank}"
    case ScenarioRankStatus.UNRANKED:
        return "Rank: Unranked"
    case ScenarioRankStatus.UNKNOWN:
        if rank_info.error_message:
            dash_logger.error(rank_info.error_message)
        return "Rank: N/A"
```

## Percentile Calculation

Phase 2 needs:

```text
current_rank
total_ranked_players
```

Formula matching the original example:

```python
percentile = ((total_ranked_players - current_rank) / total_ranked_players) * 100
```

Example:

```text
rank = 2
total = 10
percentile = 80
```

Display:

```text
Rank: 2/10 (80% Percentile)
```

If rank 1 should display `100%` instead of `90%`, use:

```python
percentile = ((total_ranked_players - current_rank + 1) / total_ranked_players) * 100
```

That would make rank `2/10` display as `90%`, so it does not match the original example. Confirm before implementing Phase 2.

## Milestones

### Milestone 1: Current Rank

- Config: `kovaaks_username`, `steam_id`, `scenario_metadata_cache_ttl_hours`, `scenario_rank_cache_ttl_hours`
- Permanent `scenarioName -> leaderboardId` cache
- Hydrate that cache from `total-play` whenever the `total-play` metadata cache is stale
- `resolve_leaderboard_id` fallback chain: permanent cache -> total-play -> exact scenario search
- Fetch and cache rank via `usernameSearch` with exact identity matching
- Display `Rank: #...`, `Rank: Unranked`, or `Rank: N/A`
- Separate UI callback with `dcc.Loading`

### Milestone 2: High-Score Rank Refresh

- Detect new high score in the watchdog/data path
- Background rank refresh on new PB through `ThreadPoolExecutor(max_workers=2)`
- Save refreshed rank to current-rank cache
- Surface refreshed rank to UI on next update cycle
- Surface refresh failures to the UI through `dash_logger.error(...)`

### Milestone 3: Percentile

- Config: `leaderboard_total_cache_ttl_hours`
- Fetch and cache leaderboard total
- Percentile calculation and display

### Milestone 4: Optional Rank History

- Store rank snapshots over time
- Reconsider SQLite at this point

## Trade-Offs

| Decision | Alternative | Reason chosen |
|---|---|---|
| JSON file cache | SQLite | Sufficient for current scope. No history or joins needed yet. Move to SQLite if rank history is desired. |
| TTL via `mtime` | Timestamp field inside JSON | No extra logic; `mtime` resets automatically on write. |
| Separate rank and total cache files | Combined file | Different TTLs; coupling forces total re-fetch whenever short-lived rank cache expires. |
| Long rank TTL plus PB refresh | Short rank TTL | Once known, rank can be reused for normal browsing; new high scores trigger immediate refresh. |
| Shared executor PB refresh | Sync in watchdog or one-off threads | Keeps the file-handling hot path fast while capping concurrency. |
| Exact username match first | Blind first result | `usernameSearch` is partial-match, so first result can be the wrong user. |
| Include `steam_id` | Username only | Steam ID guarantees the correct player when `usernameSearch` returns multiple partial matches. |
| Exact scenario search | Blind first result | Scenario search returns variants, so first result is not a safe general rule. |
| Single mapping JSON file | One file per scenario | Hundreds of entries are trivially small; one file is simpler. |

## Resolved Decisions

- Include `steam_id` in Milestone 1.
- Use `StrEnum` for `ScenarioRankStatus` so JSON cache values are stable and readable.
- Keep `scenario_rank_cache_ttl_hours = 168`; revisit only if stale rank data becomes a real user-facing issue.
- Use first-page scenario search with `max=100`; do not paginate unless real data shows this is insufficient.
- Use `ThreadPoolExecutor(max_workers=2)` for high-score-triggered refresh.
- Surface rank refresh failures to the UI through `dash_logger.error(...)`.
- No manual rank refresh button is planned.
