"""
Provides business logic for Kovaak's API.
"""

import logging
from typing import Optional

import requests

from kovaaks.api_models import PlaylistAPIResponse

BASE_URL = "https://kovaaks.com/webapp-backend"
ENDPOINTS = {
    "playlist": BASE_URL + "/playlist/playlists",
    "benchmarks": BASE_URL + "/benchmarks/player-progress-rank-benchmark",
}
TIMEOUT = 10
logger = logging.getLogger(__name__)


def get_playlist_data(playlist_code) -> PlaylistAPIResponse:
    params = {"page": 0, "max": 20, "search": playlist_code.strip()}

    response = requests.get(ENDPOINTS["playlist"], params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return PlaylistAPIResponse.model_validate(response.json())


def get_benchmark_json(benchmark_id: int, steam_id: Optional[int] = None) -> str:
    params = {
        "benchmarkId": benchmark_id,
        "steamId": steam_id or "00000000000000000",
    }
    response = requests.get(ENDPOINTS["benchmarks"], params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()
