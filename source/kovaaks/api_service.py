"""
Provides business logic for Kovaak's API.
"""

import json
import logging
import os
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
    for endpoint in Endpoints:
        os.makedirs(Path(CACHE_DIR, endpoint.name.lower()), exist_ok=True)
    for directory in (
        "scenario_leaderboards",
        "user_scenario_total_play",
        "leaderboard_user_rank",
        "leaderboard_totals",
    ):
        os.makedirs(Path(CACHE_DIR, directory), exist_ok=True)

    leaderboard_mapping_file = Path(
        CACHE_DIR,
        "scenario_leaderboards",
        "scenario_name_to_leaderboard_id.json",
    )
    if not leaderboard_mapping_file.exists():
        with open(leaderboard_mapping_file, "w", encoding="utf-8") as file:
            json.dump({}, file, indent=2)
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
    use_cache: bool = False,
    username_search: str | None = None,
) -> LeaderboardAPIResponse:
    cache_file = Path(CACHE_DIR, "leaderboard", f"{leaderboard_id}.json")
    if use_cache and not username_search and os.path.exists(cache_file):
        with open(cache_file) as file:
            data = json.load(file)
            return LeaderboardAPIResponse.model_validate(data)

    params = {
        "page": 0,
        "max": 50 if username_search else 100,
        "leaderboardId": leaderboard_id,
    }
    if username_search:
        params["usernameSearch"] = username_search
    response = requests.get(Endpoints.LEADERBOARD, params=params, timeout=TIMEOUT)
    response.raise_for_status()

    # save to cache
    if not username_search:
        with open(cache_file, "w") as file:
            json.dump(response.json(), file, indent=2)

    return LeaderboardAPIResponse.model_validate(response.json())


def _is_cache_fresh(cache_file: Path, ttl_hours: int) -> bool:
    if ttl_hours <= 0 or not os.path.exists(cache_file):
        return False

    modified_at = datetime.fromtimestamp(cache_file.stat().st_mtime)
    return datetime.now() - modified_at < timedelta(hours=ttl_hours)


def _read_json(cache_file: Path) -> dict | list | None:
    try:
        with open(cache_file, encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        logger.warning("Failed to read cache file: %s", cache_file, exc_info=True)
        return None


def _write_json(cache_file: Path, data: dict | list) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def _safe_cache_key(value: str) -> str:
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
    return isinstance(cache_data, dict) and cache_data.get("error") == "unknown_username"


def _is_complete_paginated_response(
    cache_data: dict | list | None,
    max_results: int,
    terminal_page_seen: bool,
) -> bool:
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
    max_results = 100
    cache_file = _user_scenario_total_play_cache_file(username)
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
            if not response_data:
                break
            if len(response_data) < max_results and len(data) >= total:
                break
    except requests.RequestException:
        if os.path.exists(cache_file):
            logger.warning("Using stale total-play cache for %s", username)
            cache_data = _read_json(cache_file)
            if isinstance(cache_data, dict):
                return UserScenarioTotalPlayAPIResponse.model_validate(cache_data)
        raise

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
    leaderboard_id = get_cached_leaderboard_id(scenario_name)
    if leaderboard_id is not None:
        return leaderboard_id

    if username:
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

    return search_scenario_exact(scenario_name)


def _rank_cache_file(leaderboard_id: int, username: str) -> Path:
    return Path(
        CACHE_DIR,
        "leaderboard_user_rank",
        f"{leaderboard_id}_{_safe_cache_key(username)}.json",
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
    return ScenarioRankInfo.model_validate(cache_data)


def save_scenario_rank(
    leaderboard_id: int,
    username: str,
    rank_info: ScenarioRankInfo,
) -> None:
    _write_json(
        _rank_cache_file(leaderboard_id, username),
        rank_info.model_dump(mode="json", exclude_none=True),
    )


def _find_matching_player(
    players: list[RankingPlayer],
    username: str,
    steam_id: str | None = None,
) -> RankingPlayer | None:
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


def fetch_scenario_rank(
    leaderboard_id: int,
    username: str,
    steam_id: str | None = None,
) -> ScenarioRankInfo:
    leaderboard_response = get_leaderboard_scores(
        leaderboard_id,
        username_search=username,
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
        fetched_at=datetime.now(UTC),
    )


def get_scenario_rank_info(
    scenario_name: str,
    username: str | None,
    steam_id: str | None = None,
    metadata_cache_ttl_hours: int = 24,
    rank_cache_ttl_hours: int = 168,
    force_refresh: bool = False,
) -> ScenarioRankInfo:
    if not username:
        return ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            error_message="KovaaK's username is not configured.",
        )

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
            return cached_rank

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
    return rank_info


def refresh_scenario_rank(
    scenario_name: str,
    username: str,
    steam_id: str | None = None,
    metadata_cache_ttl_hours: int = 24,
) -> ScenarioRankInfo:
    return get_scenario_rank_info(
        scenario_name,
        username,
        steam_id,
        metadata_cache_ttl_hours,
        rank_cache_ttl_hours=0,
        force_refresh=True,
    )


def get_user_scenario_rank(
    username: str | None,
    scenario_name: str,
    cache_ttl_hours: int = 24,
) -> int | None:
    rank_info = get_scenario_rank_info(
        scenario_name,
        username,
        rank_cache_ttl_hours=cache_ttl_hours,
    )
    if rank_info.status == ScenarioRankStatus.RANKED:
        return rank_info.rank
    return None


make_cache()
