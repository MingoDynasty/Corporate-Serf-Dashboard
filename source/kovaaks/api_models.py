"""
Pydantic models for Kovaak's API responses.
"""

import datetime

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
    scenarioList: list[Scenario]
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
    data: list[Playlist]


class BenchmarkScenario(BaseModel):
    score: int
    leaderboard_rank: None
    scenario_rank: int
    rank_maxes: list[float]
    leaderboard_id: int


class Category(BaseModel):
    benchmark_progress: int
    category_rank: int
    rank_maxes: list[float]
    scenarios: dict[str, BenchmarkScenario]


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
    categories: dict[str, Category]
    ranks: list[Rank]


class Attributes(BaseModel):
    # fov: int
    hash: str | None = None
    cm360: float | None = None
    epoch: int
    # kills: int
    score: float | None = None
    avgFps: float | None = None
    avgTtk: float | None = None
    fovScale: str | None = None
    vertSens: float | None = None
    horizSens: float | None = None
    resolution: str | None = None
    sensScale: str | None = None
    pauseCount: int | None = None
    pauseDuration: int | None = None
    accuracyDamage: int
    challengeStart: str | None = None
    # modelOverrides: ModelOverrides
    # sensRandomizer: None
    scenarioVersion: str
    # clientBuildVersion: str


class RankingPlayer(BaseModel):
    steamId: str
    score: float
    rank: int
    steamAccountName: str | None = None
    webappUsername: str | None = None
    kovaaksPlusActive: bool | None = None
    country: str | None = None
    attributes: Attributes


class LeaderboardAPIResponse(BaseModel):
    page: int
    max: int
    total: int
    data: list[RankingPlayer]
