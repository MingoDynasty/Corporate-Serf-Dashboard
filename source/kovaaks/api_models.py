"""
Pydantic models for Kovaak's API responses.
"""

import datetime
from typing import Dict, List

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


class BenchmarkScenario(BaseModel):
    score: int
    leaderboard_rank: None
    scenario_rank: int
    rank_maxes: List[float]
    leaderboard_id: int


class Category(BaseModel):
    benchmark_progress: int
    category_rank: int
    rank_maxes: List[float]
    scenarios: Dict[str, BenchmarkScenario]


class Rank(BaseModel):
    icon: str
    name: str
    color: str
    frame: str
    description: str
    playercard_large: str
    playercard_small: str


class BenchmarksAPIResponse(BaseModel):
    benchmark_progress: int
    overall_rank: int
    categories: Dict[str, Category]
    ranks: List[Rank]
