"""
Pydantic models for Kovaak's API responses.
"""

import datetime
from typing import List

from pydantic import BaseModel


class Scenario(BaseModel):
    author: str
    aimType: str
    playCount: int
    scenarioName: str
    webappUsername: str
    steamAccountName: str


class Playlist(BaseModel):
    playlistName: str
    subscribers: int
    scenarioList: List[Scenario]
    playlistCode: str
    playlistId: int
    published: datetime.datetime
    steamId: int
    steamAccountName: str
    webappUsername: str
    description: str
    aimType: str
    playlistDuration: int


class PlaylistAPIResponse(BaseModel):
    page: int
    max: int
    total: int
    data: List[Playlist]
