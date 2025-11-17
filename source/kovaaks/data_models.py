"""
Pydantic models for various data classes.
"""

from dataclasses import dataclass
import datetime

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
    name: str
    color: str
    threshold: float


class Scenario(BaseModel):
    name: str
    ranks: list[Rank] | None = None


class PlaylistData(BaseModel):
    name: str
    code: str
    scenarios: list[Scenario]
