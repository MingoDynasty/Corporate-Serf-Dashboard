"""
Provides business logic for Kovaak's API.
"""

import json
import logging
import os
from pathlib import Path
from enum import StrEnum

import requests

from source.kovaaks.api_models import LeaderboardAPIResponse, PlaylistAPIResponse

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


make_cache()
