"""
Pydantic models for various data classes.
"""

import datetime
from dataclasses import dataclass

from pydantic import BaseModel, field_validator


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
    # KovaaK's leaderboard ID for this scenario, embedded by the benchmark
    # importer from the benchmark payload it already holds. Optional so
    # user-imported playlists and pre-change corpus files keep validating; the
    # bundled corpus merges these into the permanent name->ID mapping cache at
    # startup (see docs/decision_log.md, the leaderboard-ID seeding entry).
    leaderboard_id: int | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        """Normalize scenario names so they match local stats keys.

        CSV run import strips the ``Scenario:`` value, so ``kovaaks_database``
        keys are always stripped while every scenario lookup is exact-match. A
        padded name from the KovaaK's playlist API (import) or a hand-edited
        playlist file would otherwise never resolve runs / PB / rank overlays.
        Kept lenient on empty (unlike ``code``): a whitespace-only name is an
        odd upstream quirk, not a store key, so it must not reject the whole
        playlist.
        """
        return value.strip()


class PlaylistData(BaseModel):
    """Represent imported playlist metadata and scenarios."""

    name: str
    code: str
    scenarios: list[Scenario]

    @field_validator("code")
    @classmethod
    def strip_and_require_code(cls, value: str) -> str:
        """Normalize playlist codes before they become store keys."""
        code = value.strip()
        if not code:
            msg = "Playlist code is required; add a `code` field."
            raise ValueError(msg)
        return code
