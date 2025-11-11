"""
Provides business logic for Kovaak's API.
"""

import logging

import requests

from kovaaks_api_models import PlaylistAPIResponse

BASE_URL = "https://kovaaks.com/webapp-backend"
ENDPOINTS = {"playlist": BASE_URL + "/playlist/playlists"}
logger = logging.getLogger(__name__)


def get_playlist_data(playlist_code) -> PlaylistAPIResponse:
    params = {"page": 0, "max": 20, "search": playlist_code.strip()}

    response = requests.get(ENDPOINTS["playlist"], params=params, timeout=5)
    response.raise_for_status()
    response = PlaylistAPIResponse.model_validate(response.json())
    return response
