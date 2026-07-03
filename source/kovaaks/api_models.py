"""
Pydantic models for Kovaak's API responses.
"""

import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Scenario(BaseModel):
    """Represent a scenario included in a playlist response."""

    author: str
    aimType: str
    playCount: int
    scenarioName: str
    webappUsername: str
    steamAccountName: str


class Playlist(BaseModel):
    """Represent a playlist returned by KovaaK's."""

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
    """Represent a paginated playlist response."""

    page: int
    max: int
    total: int
    data: list[Playlist]

    @field_validator("data", mode="before")
    @classmethod
    def ignore_null_playlist_items(cls, value):
        """Discard null playlist entries before response validation."""
        if isinstance(value, list):
            return [item for item in value if item is not None]
        return value


class BenchmarkScenario(BaseModel):
    """Represent one scenario's progress in a benchmark."""

    score: int
    leaderboard_rank: None
    scenario_rank: int
    rank_maxes: list[float]
    leaderboard_id: int


class Category(BaseModel):
    """Represent a benchmark category and its scenario progress."""

    benchmark_progress: int
    category_rank: int
    rank_maxes: list[float]
    scenarios: dict[str, BenchmarkScenario]


class Rank(BaseModel):
    """Represent a benchmark rank and its display assets."""

    icon: str
    name: str
    color: str
    frame: str
    description: str
    playercard_large: str
    playercard_small: str


class BenchmarksAPIResponse(BaseModel):
    """Represent a player's benchmark progress response."""

    benchmark_progress: int
    overall_rank: int
    categories: dict[str, Category]
    ranks: list[Rank]


class Attributes(BaseModel):
    """Represent optional run attributes attached to a leaderboard score."""

    # fov: int
    hash: str | None = None
    cm360: float | None = None
    epoch: int | None = None
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
    accuracyDamage: int | None = None
    challengeStart: str | None = None
    # modelOverrides: ModelOverrides
    # sensRandomizer: None
    scenarioVersion: str | None = None
    # clientBuildVersion: str


class RankingPlayer(BaseModel):
    """Represent one player entry on a scenario leaderboard."""

    steamId: str
    score: float
    rank: int
    steamAccountName: str | None = None
    webappUsername: str | None = None
    kovaaksPlusActive: bool | None = None
    country: str | None = None
    attributes: Attributes | None = None


class LeaderboardAPIResponse(BaseModel):
    """Represent a paginated scenario leaderboard response."""

    page: int
    max: int
    total: int
    data: list[RankingPlayer]


class UserScenarioCounts(BaseModel):
    """Represent a user's play count for one scenario."""

    plays: int


class UserScenarioTotalPlayItem(BaseModel):
    """Represent one scenario in a user's total-play response."""

    leaderboardId: str
    scenarioName: str
    counts: UserScenarioCounts
    rank: int | None = None
    score: float | None = None


class UserScenarioTotalPlayAPIResponse(BaseModel):
    """Represent a paginated user total-play response."""

    page: int
    max: int
    total: int
    data: list[UserScenarioTotalPlayItem]


class ScenarioSearchCounts(BaseModel):
    """Represent aggregate counts for a scenario search result."""

    plays: int | None = None
    entries: int | None = None


class ScenarioSearchDetails(BaseModel):
    """Represent descriptive details for a scenario search result."""

    aimType: str | None = None
    authors: list[str] | None = None
    description: str | None = None


class ScenarioSearchTopScore(BaseModel):
    """Represent the top score attached to a scenario search result."""

    score: float | None = None


class ScenarioSearchItem(BaseModel):
    """Represent one scenario returned by exact-name search."""

    rank: int
    leaderboardId: int
    scenarioName: str
    scenario: ScenarioSearchDetails | None = None
    counts: ScenarioSearchCounts | None = None
    topScore: ScenarioSearchTopScore | None = None


class ScenarioSearchAPIResponse(BaseModel):
    """Represent a paginated scenario search response."""

    page: int
    max: int
    total: int
    data: list[ScenarioSearchItem]


class ScenarioRankStatus(StrEnum):
    """Describe whether current scenario rank data is available."""

    RANKED = "RANKED"
    UNRANKED = "UNRANKED"
    UNKNOWN = "UNKNOWN"


class ScenarioRankInfo(BaseModel):
    """Represent current rank information for a selected scenario."""

    status: ScenarioRankStatus
    rank: int | None = None
    leaderboard_id: int | None = None
    scenario_name: str | None = None
    score: float | None = None
    matched_steam_id: str | None = None
    total_players: int | None = None
    percentile: float | None = None
    fetched_at: datetime.datetime | None = None
    error_message: str | None = None
    warning_message: str | None = Field(default=None, exclude=True)
