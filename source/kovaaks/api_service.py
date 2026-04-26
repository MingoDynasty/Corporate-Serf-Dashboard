"""
Provides business logic for Kovaak's API.
"""

import json
import logging
import os
from pathlib import Path
from enum import StrEnum
from datetime import datetime, timedelta

import requests

from source.kovaaks.api_models import (
    LeaderboardAPIResponse,
    PlaylistAPIResponse,
    UserScenarioTotalPlayAPIResponse,
)

TIMEOUT = 10
logger = logging.getLogger(__name__)

CACHE_DIR = "cache"


class Endpoints(StrEnum):
    def __new__(cls, path: str):
        base = "https://kovaaks.com/webapp-backend"
        obj = str.__new__(cls, base + path)  # type: ignore
        obj._value_ = base + path
        return obj

    BENCHMARKS = "/benchmarks/player-progress-rank-benchmark"
    LEADERBOARD = "/leaderboard/scores/global"
    PLAYLIST = "/playlist/playlists"
    USER_SCENARIO_TOTAL_PLAY = "/user/scenario/total-play"


def make_cache():
    for endpoint in Endpoints:
        os.makedirs(Path(CACHE_DIR, endpoint.name.lower()), exist_ok=True)
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
    leaderboard_id: int, use_cache: bool = False
) -> LeaderboardAPIResponse:
    cache_file = Path(CACHE_DIR, "leaderboard", f"{leaderboard_id}.json")
    if use_cache and os.path.exists(cache_file):
        with open(cache_file) as file:
            data = json.load(file)
            return LeaderboardAPIResponse.model_validate(data)

    params = {"page": 0, "max": 100, "leaderboardId": leaderboard_id}
    response = requests.get(Endpoints.LEADERBOARD, params=params, timeout=TIMEOUT)
    response.raise_for_status()

    # save to cache
    with open(cache_file, "w") as file:
        json.dump(response.json(), file, indent=2)

    return LeaderboardAPIResponse.model_validate(response.json())


def _is_cache_fresh(cache_file: Path, ttl_hours: int) -> bool:
    if ttl_hours <= 0 or not os.path.exists(cache_file):
        return False

    modified_at = datetime.fromtimestamp(cache_file.stat().st_mtime)
    return datetime.now() - modified_at < timedelta(hours=ttl_hours)


def get_user_scenario_total_play(
    username: str,
    cache_ttl_hours: int = 24,
) -> UserScenarioTotalPlayAPIResponse:
    cache_file = Path(CACHE_DIR, "user_scenario_total_play", f"{username}.json")
    if _is_cache_fresh(cache_file, cache_ttl_hours):
        with open(cache_file) as file:
            return UserScenarioTotalPlayAPIResponse.model_validate(json.load(file))

    page = 0
    max_results = 100
    data = []
    total = 0
    try:
        while page == 0 or len(data) < total:
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
            total = response_json["total"]
            data.extend(response_json["data"])
            page += 1
    except requests.RequestException:
        if os.path.exists(cache_file):
            logger.warning("Using stale scenario rank cache for %s", username)
            with open(cache_file) as file:
                return UserScenarioTotalPlayAPIResponse.model_validate(json.load(file))
        raise

    cached_response = {
        "page": 0,
        "max": max_results,
        "total": total,
        "data": data,
    }
    with open(cache_file, "w") as file:
        json.dump(cached_response, file, indent=2)

    return UserScenarioTotalPlayAPIResponse.model_validate(cached_response)


def get_user_scenario_rank(
    username: str | None,
    scenario_name: str,
    cache_ttl_hours: int = 24,
) -> int | None:
    if not username:
        return None

    response = get_user_scenario_total_play(username, cache_ttl_hours)
    for scenario in response.data:
        if scenario.scenarioName == scenario_name:
            return scenario.rank
    return None


make_cache()
