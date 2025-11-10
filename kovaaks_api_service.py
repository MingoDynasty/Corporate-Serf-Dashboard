"""
Provides business logic for Kovaak's API.
"""

import logging

import requests

BASE_URL = "https://kovaaks.com/webapp-backend"
ENDPOINTS = {"playlist": BASE_URL + "/playlist/playlists"}
logger = logging.getLogger(__name__)


# page=0&max=20&search=kovaaksbouncingsilverbinding
def get_playlist_data(playlist_code):
    params = {"page": 0, "max": 20, "search": playlist_code.strip()}

    response = requests.get(ENDPOINTS["playlist"], params=params)
    json = response.json()

    if response.status_code != 200 or not json["data"]:
        logger.warning(
            "Failed to get playlist data for playlist code: %s", playlist_code
        )
    return json["data"]
