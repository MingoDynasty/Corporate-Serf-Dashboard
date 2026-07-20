# KovaaK's API Notes

Living notes for the KovaaK's webapp backend endpoints this project relies on.

These endpoints are treated as external contracts that may change. When we discover a new quirk, update this file and add regression coverage when practical.

Base URL:

```text
https://kovaaks.com/webapp-backend
```

## Rate Limiting

KovaaK's may return HTTP `429 Too Many Requests` during bursty access patterns, especially cold-cache playlist table loads that fetch many scenario ranks and totals.

KovaaK's also has slow spells where `/leaderboard/scores/global` takes 9–28
seconds to respond but still returns valid data (measured 2026-07-13). The
request timeout must clear that band: it defaults to 30 seconds, configurable
via `kovaaks_api_timeout_seconds` in `config.toml`.

Project retry policy:

- Retry GET requests once on HTTP `429`.
- Retry GET requests once on connection-level failures (`requests.ConnectionError`, which includes `ConnectTimeout`): the request never reached the server, so a retry is safe.
- Never retry read timeouts (`requests.ReadTimeout`): the server received the request and is still working on it — abandoning the read does not cancel the server-side query — so an immediate duplicate doubles KovaaK's load with almost no chance of finishing sooner (2 of 63 retries succeeded during the 2026-07-13 slow spell).
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
- Expected HTTP/network request failures should be logged as concise operation failures without tracebacks. Keep tracebacks for local cache, schema, or other unexpected processing failures.

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
- Returns HTTP 400 on some invalid/gibberish `search` input (e.g. a pasted
  code with stray punctuation). The playlist import flow
  (`load_playlist_from_code`) catches this — along with timeouts, connection
  failures, and schema-invalid responses — and degrades it to a refusal
  message naming the pasted code rather than a raw callback error.

Null-hydration quirk (diagnosed 2026-07-17): for some real, public playlists
the search counts the match but returns a `null` record instead of the
payload. Observed for `KovaaKsCarryingGodlikeTile` ("VDIM Adept S5 -
Clicking I", 30 scenarios) — a code search returns `{"total": 1, "data":
[null]}` (a 43-byte body, confirmed live and in the app's debug.log); a search
on its display name returns 2 matches, both null. It is not a privacy setting:
Evxl reports `is_private: false`. The app's `ignore_null_playlist_items`
validator (`api_models.PlaylistAPIResponse`) drops the null so the response
looks like zero results. Import handles this by falling back to Evxl's exact
`playlist-by-code` lookup (below) whenever the search does not yield exactly
one usable record; only if that fallback also fails does the user see the
refusal.

## `/benchmarks/player-progress-rank-benchmark`

Existing app behavior uses this endpoint for benchmark progress.

Important limitation:

- Requires a benchmark ID.
- Works for benchmark playlists, but not every playlist is a benchmark.
- Scenario rank display should not depend on this endpoint.

Leaderboard-ID facts (verified 2026-07-19; used by leaderboard-ID seeding —
see the 2026-07-20 decision log entry):

- The endpoint accepts the placeholder Steam ID `00000000000000000` — no real
  user identity is needed. `get_benchmark_json` already sends exactly that
  placeholder, so resolving a benchmark's scenario IDs works on a username-less
  install.
- Every scenario in the response carries its own `leaderboard_id` (a stable,
  user-independent value), for the whole benchmark in one call. The benchmark
  importer embeds these into the generated playlist JSONs, and the app folds
  them into the permanent name->ID mapping cache at startup — so unplayed
  bundled-playlist scenarios resolve their leaderboard ID without the slow,
  timeout-prone exact-name search endpoint.

Benchmark rank-data quirks (surfaced by `scripts/benchmark_importer`, which
merges Evxl rank names/colors with this endpoint's per-scenario `rank_maxes`
one-to-one):

- The response's top-level `ranks[]` can omit display fields (observed:
  `color`) on some tiers. Observed on benchmark IDs 2108, 2450, 2477, 2487
  (2026-07-11), which initially blocked importing those benchmarks. The
  importer never reads these display fields (served rank colors come from
  Evxl), so `api_models.Rank.color` is now optional and a missing value no
  longer fails response validation.
- A benchmark's rank count can disagree with the Evxl rank ladder it is paired
  with, which aborts the 1:1 merge. Observed: benchmark 2412 ("Black Dawn /
  Celestial Forge") exposes 3 tiers (Emperor/Angelic/Morningstar) while Evxl
  lists 9.
- Upstream-adjacent gap: a mis-cased `sharecode` in Evxl's benchmark snapshot
  makes Evxl's own `playlist-by-code` endpoint return HTTP 400, blocking the
  import before this endpoint is reached (observed: `KovaaksBottingRockyBm`,
  which should be `KovaaKsBottingRockyBm`).

These are upstream data issues, not app bugs; the affected benchmarks import
normally once the source data is corrected.

## Evxl `playlist-by-code` (external fallback)

Not a KovaaK's endpoint — a third-party Evxl service the app uses as the
playlist-import fallback for the null-hydration quirk above.

```text
GET https://api.evxl.app/kovaaks/playlist-by-code?shareCode=KovaaKsCarryingGodlikeTile
```

Observed behavior:

- Exact-sharecode lookup. Resolves arbitrary community playlists (verified
  against "GON MACHINE for VALO v2" and "MICRO GOLD MINE"), not just Evxl
  benchmarks.
- Response is snake_case: top-level `playlist_b64` (the raw KovaaK's offline
  playlist JSON — the app ignores it), `updated` (epoch; Evxl's copy is cached
  and can be days stale — acceptable for import), and `playlist` with
  `playlist_name`, `playlist_code`, `scenario_list[].scenario_name`, plus
  extras (`is_private`, `author_name`, `description`, `playlist_id`,
  `author_steam_id`) the app does not need.
- Unknown or **mis-cased** codes return HTTP 400. `_get_with_retry`
  `raise_for_status()`es this immediately (no retry), so the import fallback
  sees one `requests.HTTPError` and refuses.
- There is no first-party KovaaK's by-code endpoint (path and query variants
  404 or ignore the parameter).

The app consumes only `playlist_name`, `playlist_code`, and
`scenario_list[].scenario_name` (see `api_service.get_evxl_playlist` and the
`Evxl*` models in `api_models.py`). The stored code is Evxl's canonical
`playlist_code`, never the pasted input.

## Derived Data

Percentile is derived from current rank and unfiltered leaderboard total:

```python
percentile = ((total_players - rank + 0.5) / total_players) * 100
```

Display with exactly two decimal places. Do not persist percentile in rank cache.
