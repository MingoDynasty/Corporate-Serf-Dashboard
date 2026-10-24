"""
Pydantic models for various data classes.
"""

import datetime
from dataclasses import dataclass

from pydantic import BaseModel, field_validator


@dataclass(frozen=True)
class RecordedSensitivity:
    """The sensitivity setting a converted run's stats file recorded."""

    value: float
    scale: str
    dpi: float


@dataclass(frozen=True)
class RunData:
    """Dataclass models data extracted from a Kovaak's run file.

    ``horizontal_sens`` and ``sens_scale`` are normalized: a run recorded on a
    game's own scale is converted to cm/360 when its file is parsed, and
    everything that groups, sorts, or compares sensitivities reads those two.
    ``recorded_sensitivity`` keeps what a converted run's file recorded, for
    display only, and is ``None`` for every run that was not converted.

    ``scenario_hash`` is the stats file's ``Hash:``, which names the version
    of the scenario the run was played on, and is ``None`` when the file has
    none. ``stats_file_name`` is the stats file's own name, which is how the
    run's performance file is found.

    ``datetime_object`` is when the run ended, in whole seconds. ``run_start``
    is when it began and ``run_length`` is how long it took to play, with
    paused time left out. Both are ``None`` together when the stats file
    gives no usable start, and a run with neither is still a run: unknown is
    never read as zero. Every time is local wall-clock time, as the game
    wrote it.

    ``shots_fired`` is the shot count ``accuracy`` was worked out from, so
    the two always describe the same weapon row of the stats file. Every run
    the parser returns has one, because a file with no shots is not a run.
    It is ``None`` only on a record built some other way, and unknown is
    never read as zero.

    ``reloads``, ``fov``, ``fov_scale`` and ``avg_fps`` are shown as they
    were recorded and never join a comparison. Each is ``None`` when its line
    is missing, has no value, or holds a value that can't be read:
    ``reloads`` that isn't a whole number of zero or more, ``fov`` that
    isn't a finite number above zero, ``fov_scale`` that is empty, and
    ``avg_fps`` that isn't a finite number of zero or more. A file with no
    ``FOVScale:`` line, as older files have, keeps its ``fov``. Unknown is
    never read as zero.
    """

    datetime_object: datetime.datetime
    score: float
    sens_scale: str
    horizontal_sens: float
    scenario: str
    accuracy: float
    recorded_sensitivity: RecordedSensitivity | None = None
    scenario_hash: str | None = None
    stats_file_name: str | None = None
    run_start: datetime.datetime | None = None
    run_length: datetime.timedelta | None = None
    shots_fired: int | None = None
    reloads: int | None = None
    fov: float | None = None
    fov_scale: str | None = None
    avg_fps: float | None = None


def run_id(run: RunData) -> str:
    """Return the id a run's row is keyed by: its stats file's name.

    A run event's ``run_id`` is the same value, so a run that just landed can
    be found in the list. A record that was not read from a stats file has no
    name, and is keyed by its scenario and its end.
    """
    return run.stats_file_name or f"{run.scenario} {run.datetime_object.isoformat()}"


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
    # startup (see docs/decision_log/, the leaderboard-ID seeding entry).
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
