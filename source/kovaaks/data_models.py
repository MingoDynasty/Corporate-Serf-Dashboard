"""
asdf
"""

import datetime
from dataclasses import dataclass
from typing import List

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


class PlaylistData(BaseModel):
    playlist_name: str
    playlist_code: str
    scenario_list: List[str]
