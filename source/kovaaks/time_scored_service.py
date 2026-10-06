"""Tell which scenarios are time-scored, from the game's performance files.

KovaaK's writes one performance file per run into the ``performances`` folder
beside the stats folder. This module lists that folder once, reads a file only
when a surface asks about its scenario, and remembers each answer by file
name, because a written file never changes. It only ever reads the folder, and
nothing here is written to disk.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from source.kovaaks.data_models import RunData
from source.kovaaks.data_service import get_runs_newest_first
from source.kovaaks.performance_file import (
    PerformanceReading,
    Scoring,
    read_performance_file,
)

PERFORMANCE_DIRECTORY_NAME = "performances"
STATS_FILE_SUFFIX = " Stats.csv"
PERFORMANCE_FILE_SUFFIX = " Performance.perf"

logger = logging.getLogger(__name__)

# Unsynchronized on the same terms as the run stores: after startup the
# watchdog thread is the only writer of the listing, and a raced read
# self-heals on the next look. See the 2026-07-09 "Unsynchronized In-Memory
# Stores" entry in docs/decision_log.md.
_performance_dir: Path | None = None
_performance_file_names: set[str] = set()
_readings: dict[str, PerformanceReading] = {}


@dataclass(frozen=True)
class PaceBasis:
    """A time-scored scenario's constant, and the version it was read from.

    A score of ``s`` took ``constant - s`` seconds. ``scenario_hash`` names the
    one version of the scenario the constant is known to hold for.
    """

    constant: float
    scenario_hash: str


def index_performance_files(stats_dir: str) -> None:
    """List the ``performances`` folder beside the stats folder, parsing nothing.

    A stats folder with no such folder beside it, as when the setting points
    at a copy of the stats files, lists nothing, and so recognizes nothing.
    The folder is still remembered, because the game creates it with the first
    run it writes a performance file for.
    """
    global _performance_dir, _performance_file_names  # noqa: PLW0603
    performance_dir = Path(stats_dir).parent / PERFORMANCE_DIRECTORY_NAME
    names: set[str] = set()
    try:
        with os.scandir(performance_dir) as entries:
            names = {
                entry.name
                for entry in entries
                if entry.name.endswith(PERFORMANCE_FILE_SUFFIX)
            }
    except OSError as exc:
        logger.debug(
            'Could not list the performance files in "%s": %s', performance_dir, exc
        )
    _performance_dir = performance_dir
    _performance_file_names = names
    _readings.clear()
    logger.debug(
        'Performance file listing complete: %d files in "%s".',
        len(names),
        performance_dir,
    )


def _performance_file_name(run: RunData) -> str | None:
    """Name the performance file the game would have written for a run."""
    stats_file_name = run.stats_file_name
    if stats_file_name is None or not stats_file_name.endswith(STATS_FILE_SUFFIX):
        return None
    return stats_file_name.removesuffix(STATS_FILE_SUFFIX) + PERFORMANCE_FILE_SUFFIX


def note_performance_file(run: RunData) -> None:
    """Add a landed run's performance file to the listing, if the game wrote one.

    Without this the listing stays as startup found it, and the table and the
    chart would keep judging a scenario by files older than the one the
    watchdog just read.
    """
    name = _performance_file_name(run)
    if name is None or _performance_dir is None or name in _performance_file_names:
        return
    # ``os.path.isfile`` answers False where a ``Path`` method could raise, and
    # this runs on the watchdog thread before the run is imported.
    if os.path.isfile(_performance_dir / name):
        _performance_file_names.add(name)


def _describe(reading: PerformanceReading) -> str:
    distance = reading.largest_distance
    return (
        f"time limit {reading.time_limit:g}, {reading.score_events} score events, "
        "largest distance from the countdown "
        + ("none" if distance is None else f"{distance:.4f}")
    )


def _reading_for(name: str) -> PerformanceReading | None:
    """Return a listed file's answer, reading the file at most once.

    ``None`` means the file could not be read. That is not remembered, so the
    next look tries again.
    """
    reading = _readings.get(name)
    if reading is not None or _performance_dir is None:
        return reading
    try:
        data = (_performance_dir / name).read_bytes()
    except OSError as exc:
        logger.warning('Failed to read performance file "%s": %s', name, exc)
        return None
    reading = read_performance_file(data)
    _readings[name] = reading
    if reading.scoring is Scoring.CANNOT_ANSWER:
        logger.debug(
            'Performance file "%s" can\'t answer whether its scenario is time-scored.',
            name,
        )
    else:
        logger.debug(
            'Performance file "%s" is %s: %s.',
            name,
            reading.scoring.value,
            _describe(reading),
        )
    return reading


def get_pace_basis(
    scenario_name: str,
    landed_run: RunData | None = None,
) -> PaceBasis | None:
    """Return a time-scored scenario's constant and version, or ``None``.

    ``None`` covers a scenario that is not time-scored and one the app can't
    tell about alike: either way every surface keeps its score math.

    The scenario's newest run names the version. That run and the older runs
    of the same hash are tried newest first, and the first performance file
    that can answer decides. ``landed_run`` is a run the watchdog has parsed
    and not yet stored, so that a new run is judged with its own file.
    """
    if not _performance_file_names:
        return None
    runs = get_runs_newest_first(scenario_name)
    if landed_run is not None:
        runs = sorted(
            [*runs, landed_run],
            key=lambda run: run.datetime_object,
            reverse=True,
        )
    if not runs or runs[0].scenario_hash is None:
        return None
    version = runs[0].scenario_hash
    for run in runs:
        if run.scenario_hash != version:
            continue
        name = _performance_file_name(run)
        if name is None or name not in _performance_file_names:
            continue
        reading = _reading_for(name)
        # Skipped, never decisive: a file that can't be read, or is on a
        # schema version this build does not know, says nothing about how the
        # scenario scores. Stopping here would turn every recognized scenario
        # back to score math on its first run after KovaaK's changes the
        # format, with nothing on screen to say why.
        if reading is None or reading.scoring is Scoring.CANNOT_ANSWER:
            continue
        # Decisive, never skipped: every ordinary scenario's newest file
        # answers this, and looking past it for a countdown that is not there
        # would read that scenario's whole history on every look.
        if reading.scoring is Scoring.NOT_TIME_SCORED:
            return None
        # Guaranteed by read_performance_file: a time-scored answer carries
        # the limit and the hash it was read from.
        assert reading.time_limit is not None
        assert reading.scenario_hash is not None
        return PaceBasis(
            constant=reading.time_limit,
            scenario_hash=reading.scenario_hash,
        )
    return None


def eligible_pace_constant(
    basis: PaceBasis | None,
    *runs: RunData | None,
) -> float | None:
    """Return the constant when every run is of the version it was read from.

    The constant was read from one version of the scenario, and nothing shows
    that another version scores the same way. A PB from an older version
    measured against it would get a completion time it never had, so a
    comparison with any such run keeps its score math.
    """
    if basis is None:
        return None
    for run in runs:
        if run is None or run.scenario_hash != basis.scenario_hash:
            return None
    return basis.constant
