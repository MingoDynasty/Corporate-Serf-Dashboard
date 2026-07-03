"""
Pydantic models for various data classes.
"""

import datetime
from dataclasses import dataclass

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
    damage_accuracy: float | None = None


@dataclass()
class ScenarioStats:
    """Dataclass models statistics for a scenario."""

    date_last_played: datetime.datetime
    number_of_runs: int
    high_score: float


class Rank(BaseModel):
    """Represent a playlist rank threshold and its display color."""

    name: str
    color: str
    threshold: float


class Scenario(BaseModel):
    """Represent a playlist scenario with optional rank thresholds."""

    name: str
    ranks: list[Rank] | None = None


class PlaylistData(BaseModel):
    """Represent imported playlist metadata and scenarios."""

    name: str
    code: str
    scenarios: list[Scenario]
