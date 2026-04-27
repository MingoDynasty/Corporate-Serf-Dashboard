"""
Provides business logic for Kovaak's API.
"""

import json
import logging
import os
import threading
from pathlib import Path
from enum import StrEnum
from datetime import UTC, datetime, timedelta

import requests

from source.kovaaks.api_models import (
    LeaderboardAPIResponse,
    PlaylistAPIResponse,
    RankingPlayer,
    ScenarioRankInfo,
    ScenarioRankStatus,
    ScenarioSearchAPIResponse,
    UserScenarioTotalPlayAPIResponse,
)

TIMEOUT = 10
logger = logging.getLogger(__name__)
_CACHE_IO_LOCK = threading.RLock()

CACHE_DIR = "cache"


class UnknownKovaaksUserError(ValueError):
    """Raised when KovaaK's returns no user for the configured username."""


class Endpoints(StrEnum):
    def __new__(cls, path: str):
        base = "https://kovaaks.com/webapp-backend"
        obj = str.__new__(cls, base + path)  # type: ignore
        obj._value_ = base + path
        return obj

    BENCHMARKS = "/benchmarks/player-progress-rank-benchmark"
    LEADERBOARD = "/leaderboard/scores/global"
    PLAYLIST = "/playlist/playlists"
    SEARCH_SCENARIO = "/scenario/popular"
    USER_SCENARIO_TOTAL_PLAY = "/user/scenario/total-play"


def make_cache():
    """Create non-user-specific cache directories and permanent index files."""
    for endpoint in Endpoints:
        os.makedirs(Path(CACHE_DIR, endpoint.name.lower()), exist_ok=True)
    for directory in (
        "scenario_leaderboards",
        "user_scenario_total_play",
        Path("leaderboard", "user_rank"),
        Path("leaderboard", "totals"),
    ):
        os.makedirs(Path(CACHE_DIR, directory), exist_ok=True)

    leaderboard_mapping_file = Path(
        CACHE_DIR,
        "scenario_leaderboards",
        "scenario_name_to_leaderboard_id.json",
    )
    if not leaderboard_mapping_file.exists():
        _write_json(leaderboard_mapping_file, {})
    return


def get_playlist_data(playlist_code) -> PlaylistAPIResponse:
    params = {"page": 0, "max": 20, "search": playlist_code.strip()}

    response = requests.get(Endpoints.PLAYLIST, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return PlaylistAPIResponse.model_validate(response.json())


def get_benchmark_json(
    benchmark_id: int, steam_id: int | None = None, use_cache: bool = False
) -> str:
    cache_file = Path(CACHE_DIR, "benchmarks", f"{benchmark_id}.json")
    if use_cache and os.path.exists(cache_file):
        with open(cache_file) as file:
            return json.load(file)

    params = {
        "benchmarkId": benchmark_id,
        "steamId": steam_id or "00000000000000000",
    }
    response = requests.get(Endpoints.BENCHMARKS, params=params, timeout=TIMEOUT)
    response.raise_for_status()

    print(type(response))
    print(type(response.json()))

    # save to cache
    with open(cache_file, "w") as file:
        json.dump(response.json(), file, indent=2)

    return response.json()


def get_leaderboard_scores(
    leaderboard_id: int,
    username_search: str | None = None,
    page: int = 0,
    max_results: int = 100,
) -> LeaderboardAPIResponse:
    if page < 0:
        raise ValueError("page must be greater than or equal to 0")
    if max_results <= 0:
        raise ValueError("max_results must be greater than 0")

    params = {
        "page": page,
        "max": max_results,
        "leaderboardId": leaderboard_id,
    }
    if username_search:
        params["usernameSearch"] = username_search
    response = requests.get(Endpoints.LEADERBOARD, params=params, timeout=TIMEOUT)
    response.raise_for_status()

    return LeaderboardAPIResponse.model_validate(response.json())


def _is_cache_fresh(cache_file: Path, ttl_hours: int) -> bool:
    if ttl_hours <= 0 or not os.path.exists(cache_file):
        return False

    modified_at = datetime.fromtimestamp(cache_file.stat().st_mtime)
    return datetime.now() - modified_at < timedelta(hours=ttl_hours)


def _read_json(cache_file: Path) -> dict | list | None:
    with _CACHE_IO_LOCK:
        try:
            with open(cache_file, encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            logger.warning("Failed to read cache file: %s", cache_file, exc_info=True)
            return None


def _write_json(cache_file: Path, data: dict | list) -> None:
    with _CACHE_IO_LOCK:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = cache_file.with_name(
            f".{cache_file.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        )
        try:
            with open(temp_file, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_file, cache_file)
        finally:
            if temp_file.exists():
                temp_file.unlink()


def _safe_cache_key(value: str) -> str:
    """Normalize user-provided values before embedding them in cache paths."""
    return "".join(
        char if char.isalnum() or char in ("-", "_") else "_"
        for char in value
    )


def _user_scenario_total_play_cache_file(username: str) -> Path:
    return Path(CACHE_DIR, "user_scenario_total_play", f"{_safe_cache_key(username)}.json")


def _user_scenario_total_play_page_cache_file(username: str, page: int) -> Path:
    return Path(
        CACHE_DIR,
        "user_scenario_total_play",
        _safe_cache_key(username),
        f"page_{page}.json",
    )


def _has_terminal_user_scenario_total_play_page(
    username: str,
    max_results: int,
) -> bool:
    """
    Return whether cached total-play page files include a final short page.

    The merged total-play cache alone is ambiguous when it has exactly a full page
    of rows. A raw page with fewer than `max_results` rows is our signal that we
    actually reached the end of pagination.
    """
    page_dir = Path(CACHE_DIR, "user_scenario_total_play", _safe_cache_key(username))
    for page_file in page_dir.glob("page_*.json"):
        cache_data = _read_json(page_file)
        if not isinstance(cache_data, dict):
            continue

        data = cache_data.get("data")
        if isinstance(data, list) and len(data) < max_results:
            return True
    return False


def _is_unknown_username_total_play_response(cache_data: dict | list | None) -> bool:
    """Detect our cached marker for KovaaK's literal-null unknown-user response."""
    return isinstance(cache_data, dict) and cache_data.get("error") == "unknown_username"


def _is_complete_paginated_response(
    cache_data: dict | list | None,
    max_results: int,
    terminal_page_seen: bool,
) -> bool:
    """
    Validate that a merged paginated cache represents a complete fetch.

    `total-play` can report a `total` that does not force us to probe the next
    page. If the merged row count lands exactly on a page boundary, require a
    cached terminal page before trusting the merged file.
    """
    if not isinstance(cache_data, dict):
        return False

    data = cache_data.get("data")
    total = cache_data.get("total")
    if not isinstance(data, list) or not isinstance(total, int):
        return False
    if len(data) < total:
        return False
    if len(data) >= max_results and len(data) % max_results == 0:
        return terminal_page_seen
    return True


def _leaderboard_mapping_file() -> Path:
    return Path(CACHE_DIR, "scenario_leaderboards", "scenario_name_to_leaderboard_id.json")


def get_cached_leaderboard_id(scenario_name: str) -> int | None:
    cache_data = _read_json(_leaderboard_mapping_file())
    if not isinstance(cache_data, dict):
        return None

    scenario_data = cache_data.get(scenario_name)
    if not isinstance(scenario_data, dict):
        return None

    leaderboard_id = scenario_data.get("leaderboard_id")
    if leaderboard_id is None:
        return None
    return int(leaderboard_id)


def save_leaderboard_id(
    scenario_name: str,
    leaderboard_id: int,
    source: str,
) -> None:
    """Upsert a scenario-name to leaderboard-ID mapping unless it conflicts."""
    with _CACHE_IO_LOCK:
        cache_file = _leaderboard_mapping_file()
        cache_data = _read_json(cache_file)
        mappings = cache_data if isinstance(cache_data, dict) else {}

        existing = mappings.get(scenario_name)
        if isinstance(existing, dict) and existing.get("leaderboard_id") not in (
            None,
            leaderboard_id,
        ):
            logger.warning(
                "Conflicting leaderboard id for scenario %s: existing=%s new=%s source=%s",
                scenario_name,
                existing.get("leaderboard_id"),
                leaderboard_id,
                source,
            )
            return

        mappings[scenario_name] = {
            "leaderboard_id": int(leaderboard_id),
            "source": source,
            "fetched_at": datetime.now(UTC).isoformat(),
        }
        _write_json(cache_file, mappings)


def get_user_scenario_total_play(
    username: str,
    cache_ttl_hours: int = 24,
) -> UserScenarioTotalPlayAPIResponse:
    """
    Fetch and cache total-play metadata for a user.

    This endpoint is used only as metadata for discovering scenario leaderboard
    IDs. It is not authoritative for current score or rank, so callers should not
    use the returned `rank` field for UI rank display.

    High-level flow:
    1. Trust a fresh merged cache only if it looks complete.
    2. Otherwise fetch and cache each raw API page.
    3. Write a merged cache response for simple future reads.
    4. Fall back to stale merged cache only when the API itself is unavailable.
    """
    max_results = 100
    cache_file = _user_scenario_total_play_cache_file(username)

    # Fast path: use the merged cache only when it has enough evidence that all
    # pages were fetched. This avoids getting stuck forever with a page-0-only
    # cache file from an earlier buggy or interrupted run.
    if _is_cache_fresh(cache_file, cache_ttl_hours):
        cache_data = _read_json(cache_file)
        if _is_unknown_username_total_play_response(cache_data):
            raise UnknownKovaaksUserError(
                f"KovaaK's username '{username}' was not found."
            )
        if _is_complete_paginated_response(
            cache_data,
            max_results,
            _has_terminal_user_scenario_total_play_page(username, max_results),
        ):
            return UserScenarioTotalPlayAPIResponse.model_validate(cache_data)
        logger.warning("Ignoring incomplete total-play cache for %s", username)

    page = 0
    data = []
    total = 0
    try:
        # Slow path: collect raw pages first, then synthesize the merged cache.
        # Keeping the page files makes API behavior inspectable without forcing
        # every caller to understand pagination.
        while True:
            params = {
                "username": username,
                "page": page,
                "max": max_results,
                "sort_param[]": "count",
            }
            response = requests.get(
                Endpoints.USER_SCENARIO_TOTAL_PLAY,
                params=params,
                timeout=TIMEOUT,
            )
            response.raise_for_status()

            response_json = response.json()
            if response_json is None:
                # KovaaK's returns literal null when the username does not exist.
                # Cache a structured marker so later lookups fail explicitly.
                unknown_user_response = {
                    "page": page,
                    "max": max_results,
                    "total": 0,
                    "data": [],
                    "error": "unknown_username",
                    "username": username,
                }
                _write_json(
                    _user_scenario_total_play_page_cache_file(username, page),
                    unknown_user_response,
                )
                _write_json(cache_file, unknown_user_response)
                raise UnknownKovaaksUserError(
                    f"KovaaK's username '{username}' was not found."
                )
            _write_json(
                _user_scenario_total_play_page_cache_file(username, page),
                response_json,
            )

            response_data = response_json["data"]
            total = max(total, response_json["total"])
            data.extend(response_data)
            page += 1
            total = max(total, len(data))
            # Keep fetching while the API says more rows exist, and also probe
            # one extra page when the current page is full. Some observed
            # responses under-report `total`.
            if not response_data:
                break
            if len(response_data) < max_results and len(data) >= total:
                break
    except requests.RequestException:
        # A network failure is not proof that the user has no plays. Reuse stale
        # metadata if we have it; otherwise let the caller decide how to degrade.
        if os.path.exists(cache_file):
            logger.warning("Using stale total-play cache for %s", username)
            cache_data = _read_json(cache_file)
            if isinstance(cache_data, dict):
                return UserScenarioTotalPlayAPIResponse.model_validate(cache_data)
        raise

    # The merged cache is the app-facing snapshot. Individual page files are
    # retained only for debuggability and cache-completeness checks.
    cached_response = {
        "page": 0,
        "max": max_results,
        "total": total,
        "data": data,
    }
    _write_json(cache_file, cached_response)

    return UserScenarioTotalPlayAPIResponse.model_validate(cached_response)


def hydrate_leaderboard_id_cache(
    username: str | None,
    cache_ttl_hours: int = 24,
) -> None:
    """
    Use total-play metadata to enrich the permanent leaderboard mapping cache.

    This is deliberately an upsert-only metadata operation. It should never be
    treated as current rank or score truth.
    """
    if not username:
        return

    response = get_user_scenario_total_play(username, cache_ttl_hours)
    for scenario in response.data:
        save_leaderboard_id(
            scenario.scenarioName,
            int(scenario.leaderboardId),
            "total-play",
        )


def search_scenario_exact(scenario_name: str) -> int | None:
    """
    Resolve a scenario by exact name through KovaaK's scenario search endpoint.

    The API returns fuzzy/prefix matches, so `data[0]` is not safe. Only a single
    exact `scenarioName` match is accepted.
    """
    params = {"page": 0, "max": 100, "scenarioNameSearch": scenario_name}
    response = requests.get(Endpoints.SEARCH_SCENARIO, params=params, timeout=TIMEOUT)
    response.raise_for_status()

    search_response = ScenarioSearchAPIResponse.model_validate(response.json())
    matches = [
        scenario
        for scenario in search_response.data
        if scenario.scenarioName == scenario_name
    ]
    if len(matches) == 1:
        leaderboard_id = int(matches[0].leaderboardId)
        save_leaderboard_id(scenario_name, leaderboard_id, "scenario-search")
        return leaderboard_id
    if len(matches) > 1:
        logger.warning(
            "Found multiple exact scenario search matches for %s: %s",
            scenario_name,
            [match.leaderboardId for match in matches],
        )
    return None


def resolve_leaderboard_id(
    scenario_name: str,
    username: str | None = None,
    metadata_cache_ttl_hours: int = 24,
) -> int | None:
    """
    Resolve a selected scenario name to a leaderboard ID.

    The total-play cache is a best-effort metadata source. If it is unavailable,
    continue to exact scenario search rather than treating cache failure as a
    user-facing rank failure.

    Fallback order:
    1. Permanent local mapping cache.
    2. User total-play metadata hydration.
    3. Exact-name scenario search.
    """
    # The permanent cache is the cheapest and most trusted source once learned.
    leaderboard_id = get_cached_leaderboard_id(scenario_name)
    if leaderboard_id is not None:
        return leaderboard_id

    if username:
        # Hydration is opportunistic: it can fill many mappings at once, but
        # failure should not block exact search for the selected scenario.
        try:
            hydrate_leaderboard_id_cache(username, metadata_cache_ttl_hours)
        except requests.RequestException:
            logger.warning(
                "Failed to hydrate leaderboard metadata from total-play for %s",
                username,
                exc_info=True,
            )
        leaderboard_id = get_cached_leaderboard_id(scenario_name)
        if leaderboard_id is not None:
            return leaderboard_id

    # Last resort: ask KovaaK's scenario search and accept only exact matches.
    return search_scenario_exact(scenario_name)


def _rank_cache_file(
    leaderboard_id: int,
    username: str,
) -> Path:
    return Path(
        CACHE_DIR,
        "leaderboard",
        "user_rank",
        _safe_cache_key(username),
        f"{leaderboard_id}.json",
    )


def get_cached_scenario_rank(
    leaderboard_id: int,
    username: str,
    cache_ttl_hours: int = 168,
) -> ScenarioRankInfo | None:
    cache_file = _rank_cache_file(leaderboard_id, username)
    if not _is_cache_fresh(cache_file, cache_ttl_hours):
        return None

    cache_data = _read_json(cache_file)
    if not isinstance(cache_data, dict):
        return None
    return ScenarioRankInfo.model_validate(cache_data).model_copy(
        update={"total_players": None}
    )


def save_scenario_rank(
    leaderboard_id: int,
    username: str,
    rank_info: ScenarioRankInfo,
) -> None:
    rank_cache_data = rank_info.model_copy(update={"total_players": None})
    _write_json(
        _rank_cache_file(leaderboard_id, username),
        rank_cache_data.model_dump(mode="json", exclude_none=True),
    )


def _leaderboard_total_cache_file(leaderboard_id: int) -> Path:
    return Path(CACHE_DIR, "leaderboard", "totals", f"{leaderboard_id}.json")


def get_cached_leaderboard_total(
    leaderboard_id: int,
    cache_ttl_hours: int = 24,
) -> int | None:
    """Read a fresh cached total player count for a leaderboard."""
    cache_file = _leaderboard_total_cache_file(leaderboard_id)
    if not _is_cache_fresh(cache_file, cache_ttl_hours):
        return None

    cache_data = _read_json(cache_file)
    if not isinstance(cache_data, dict):
        return None

    total_players = cache_data.get("total_players")
    if not isinstance(total_players, int):
        return None
    return total_players


def save_leaderboard_total(leaderboard_id: int, total_players: int) -> None:
    """Cache the total number of ranked players for a leaderboard."""
    _write_json(
        _leaderboard_total_cache_file(leaderboard_id),
        {
            "leaderboard_id": int(leaderboard_id),
            "total_players": int(total_players),
            "fetched_at": datetime.now(UTC).isoformat(),
        },
    )


def fetch_leaderboard_total(leaderboard_id: int) -> int:
    """
    Fetch the total ranked-player count using the leaderboard endpoint.

    The API returns the total row count with every leaderboard response, so
    requesting one row keeps this cheap while still using the authoritative
    leaderboard source.
    """
    leaderboard_response = get_leaderboard_scores(leaderboard_id, max_results=1)
    return int(leaderboard_response.total)


def get_leaderboard_total(
    leaderboard_id: int,
    cache_ttl_hours: int = 24,
) -> int:
    """Return a cached leaderboard total, refreshing it when stale or missing."""
    cached_total = get_cached_leaderboard_total(leaderboard_id, cache_ttl_hours)
    if cached_total is not None:
        return cached_total

    total_players = fetch_leaderboard_total(leaderboard_id)
    save_leaderboard_total(leaderboard_id, total_players)
    return total_players


def _with_leaderboard_total(
    rank_info: ScenarioRankInfo,
    leaderboard_total_cache_ttl_hours: int = 24,
) -> ScenarioRankInfo:
    """
    Best-effort attach total ranked-player count to a ranked result.

    Total-count freshness has its own short TTL. A failure here should degrade to
    showing just the rank, because the rank result itself is still valid.
    """
    if (
        rank_info.status != ScenarioRankStatus.RANKED
        or rank_info.leaderboard_id is None
    ):
        return rank_info

    try:
        total_players = get_leaderboard_total(
            rank_info.leaderboard_id,
            leaderboard_total_cache_ttl_hours,
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "Failed to fetch leaderboard total for %s",
            rank_info.leaderboard_id,
            exc_info=True,
        )
        return rank_info
    return rank_info.model_copy(update={"total_players": total_players})


def _find_matching_player(
    players: list[RankingPlayer],
    username: str,
    steam_id: str | None = None,
) -> RankingPlayer | None:
    """Choose the exact player from a partial-match leaderboard search result."""
    if steam_id:
        for player in players:
            if player.steamId == steam_id:
                return player

    for player in players:
        if player.webappUsername == username:
            return player

    for player in players:
        if player.steamAccountName == username:
            return player

    return None


def _steam_id_mismatch_warning(
    username: str,
    configured_steam_id: str | None,
    matched_steam_id: str | None,
) -> str | None:
    if (
        not configured_steam_id
        or not matched_steam_id
        or matched_steam_id == configured_steam_id
    ):
        return None

    return (
        f"Configured Steam ID '{configured_steam_id}' does not match "
        f"KovaaK's user '{username}' (actual Steam ID: {matched_steam_id})."
    )


def _with_derived_rank_warning(
    rank_info: ScenarioRankInfo,
    username: str,
    steam_id: str | None = None,
) -> ScenarioRankInfo:
    """Attach transient UI warnings derived from current config and cached facts."""
    return rank_info.model_copy(
        update={
            "warning_message": _steam_id_mismatch_warning(
                username,
                steam_id,
                rank_info.matched_steam_id,
            )
        }
    )


def fetch_scenario_rank(
    leaderboard_id: int,
    username: str,
    steam_id: str | None = None,
) -> ScenarioRankInfo:
    """
    Fetch the user's current rank from the authoritative leaderboard endpoint.

    `usernameSearch` is partial-match, so the response is filtered again by
    Steam ID or exact username before it is trusted.
    """
    leaderboard_response = get_leaderboard_scores(
        leaderboard_id,
        username_search=username,
        max_results=50,
    )
    player = _find_matching_player(leaderboard_response.data, username, steam_id)
    if not player:
        return ScenarioRankInfo(
            status=ScenarioRankStatus.UNRANKED,
            leaderboard_id=leaderboard_id,
            fetched_at=datetime.now(UTC),
        )

    return ScenarioRankInfo(
        status=ScenarioRankStatus.RANKED,
        rank=player.rank,
        leaderboard_id=leaderboard_id,
        score=player.score,
        matched_steam_id=player.steamId,
        fetched_at=datetime.now(UTC),
    )


def get_scenario_rank_info(
    scenario_name: str,
    username: str | None,
    steam_id: str | None = None,
    metadata_cache_ttl_hours: int = 24,
    rank_cache_ttl_hours: int = 168,
    leaderboard_total_cache_ttl_hours: int = 24,
    force_refresh: bool = False,
) -> ScenarioRankInfo:
    """
    Main rank lookup entry point for UI and background refresh callers.

    Expected KovaaK's API failures are converted into UNKNOWN rank states so UI
    code can display N/A without knowing endpoint or cache details.

    Result states:
    - RANKED: leaderboard exists and the exact user has a score.
    - UNRANKED: leaderboard exists and the configured user appears valid, but no
      score was found.
    - UNKNOWN: missing config, invalid username, unresolved leaderboard, or API
      failure.
    """
    if not username:
        return ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            error_message="KovaaK's username is not configured.",
        )

    # First resolve scenario name -> leaderboard ID. Everything after this point
    # can use the stable numeric leaderboard identifier.
    try:
        leaderboard_id = resolve_leaderboard_id(
            scenario_name,
            username,
            metadata_cache_ttl_hours,
        )
    except UnknownKovaaksUserError as exc:
        return ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            scenario_name=scenario_name,
            error_message=str(exc),
        )
    except requests.RequestException:
        logger.warning(
            "Failed to resolve leaderboard for %s",
            scenario_name,
            exc_info=True,
        )
        return ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            scenario_name=scenario_name,
            error_message=f"Failed to resolve leaderboard for {scenario_name}.",
        )
    if leaderboard_id is None:
        return ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            error_message=f"Could not resolve leaderboard for {scenario_name}.",
        )

    # Rank cache is intentionally long-lived. New high-score detection refreshes
    # this cache, so normal scenario switching should avoid leaderboard calls.
    if not force_refresh:
        cached_rank = get_cached_scenario_rank(
            leaderboard_id,
            username,
            rank_cache_ttl_hours,
        )
        if cached_rank:
            if cached_rank.scenario_name is None:
                cached_rank = cached_rank.model_copy(
                    update={"scenario_name": scenario_name}
                )
                save_scenario_rank(leaderboard_id, username, cached_rank)
            cached_rank = _with_leaderboard_total(
                cached_rank,
                leaderboard_total_cache_ttl_hours,
            )
            return _with_derived_rank_warning(cached_rank, username, steam_id)

    # Fresh rank lookup is the authoritative path for current rank. total-play
    # is not used here because it can lag behind the leaderboard endpoint.
    try:
        rank_info = fetch_scenario_rank(leaderboard_id, username, steam_id)
    except requests.RequestException:
        logger.warning(
            "Failed to fetch scenario rank for %s",
            scenario_name,
            exc_info=True,
        )
        return ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            leaderboard_id=leaderboard_id,
            scenario_name=scenario_name,
            error_message=f"Failed to fetch scenario rank for {scenario_name}.",
        )
    if rank_info.status == ScenarioRankStatus.UNRANKED:
        # A missing leaderboard row normally means the user has not played the
        # scenario. Because an invalid configured username can look the same,
        # ask total-play to explicitly confirm whether the user exists.
        try:
            get_user_scenario_total_play(username, metadata_cache_ttl_hours)
        except UnknownKovaaksUserError as exc:
            return ScenarioRankInfo(
                status=ScenarioRankStatus.UNKNOWN,
                leaderboard_id=leaderboard_id,
                scenario_name=scenario_name,
                error_message=str(exc),
            )
        except requests.RequestException:
            logger.warning(
                "Failed to validate KovaaK's username through total-play for %s",
                username,
                exc_info=True,
            )
    rank_info = rank_info.model_copy(update={"scenario_name": scenario_name})
    save_scenario_rank(leaderboard_id, username, rank_info)
    rank_info = _with_leaderboard_total(
        rank_info,
        leaderboard_total_cache_ttl_hours,
    )
    return _with_derived_rank_warning(rank_info, username, steam_id)


def refresh_scenario_rank(
    scenario_name: str,
    username: str,
    steam_id: str | None = None,
    metadata_cache_ttl_hours: int = 24,
    leaderboard_total_cache_ttl_hours: int = 24,
) -> ScenarioRankInfo:
    return get_scenario_rank_info(
        scenario_name,
        username,
        steam_id,
        metadata_cache_ttl_hours,
        rank_cache_ttl_hours=0,
        leaderboard_total_cache_ttl_hours=leaderboard_total_cache_ttl_hours,
        force_refresh=True,
    )


make_cache()
