"""
Pydantic models for various data classes.
"""

import datetime
from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel


@dataclass(frozen=True)
class RunData:
    """Dataclass models data extracted from a Kovaak's run file."""

    datetime_object: datetime.datetime
    score: float
    sens_scale: str
    horizontal_sens: float
    scenario: str
    accuracy: float


@dataclass()
class ScenarioStats:
    """Dataclass models statistics for a scenario."""

    date_last_played: datetime.datetime
    number_of_runs: int


class Rank(BaseModel):
    rank_name: str
    rank_color: str
    rank_threshold: float


class Scenario(BaseModel):
    scenario_name: str
    rank_data: Optional[List[Rank]] = None


class PlaylistData(BaseModel):
    playlist_name: str
    playlist_code: str
    scenario_list: List[Scenario]
