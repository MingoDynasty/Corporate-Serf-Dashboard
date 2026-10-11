"""Group runs into play sessions and scenario visits.

A play session is what the docs call a session: one stretch of play,
including the breaks between runs. A scenario visit is what they call a
visit: consecutive runs on one scenario within a play session. The rules,
and the decision that set them, are in ``docs/specs/sessions.md``.

Everything here is worked out from a list of runs when something asks, and
nothing is stored. The functions never read the run store and hold no clock:
a caller hands over a copy of the store's runs, and the current time.
"""

import datetime
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter

from source.kovaaks.data_models import RunData

# The longest break between two runs that keeps them in one play session, and
# the time a play session stays in progress after its last run. One number
# with both meanings, so a play session reads as in progress for exactly as
# long as a new run would still join it. It is not a setting: every install
# splits the same runs the same way.
PLAY_SESSION_BREAK_LIMIT = datetime.timedelta(minutes=30)


def _start_or_end(run: RunData) -> datetime.datetime:
    """Return when a run began, or when it ended if it has no usable start."""
    return run.run_start if run.run_start is not None else run.datetime_object


def _split_order(run: RunData) -> tuple[datetime.datetime, datetime.datetime, str, str]:
    """Return the key that puts runs in the one order they are split in.

    The end comes first. It is in whole seconds, so two runs can share one:
    after the clock goes back, or when a stats file has a stray copy. Which
    of them comes first can move a session boundary when their starts differ,
    so the run that began first does, a run with no usable start counting as
    beginning at its end. The scenario and the stats file's name settle what
    is left, and a file name is unique within a stats folder.
    """
    return (
        run.datetime_object,
        _start_or_end(run),
        run.scenario,
        run.stats_file_name or "",
    )


@dataclass(frozen=True)
class _ConsecutiveRuns:
    """One or more runs in the order they ended, and the time they span."""

    runs: tuple[RunData, ...]

    @property
    def start(self) -> datetime.datetime:
        """When the first run began, or when it ended if it has no usable start."""
        return _start_or_end(self.runs[0])

    @property
    def end(self) -> datetime.datetime:
        """When the last run ended."""
        return self.runs[-1].datetime_object


@dataclass(frozen=True)
class PlaySession(_ConsecutiveRuns):
    """The runs of one play session, in the order they ended.

    A play session has no identity of its own, because none is stored. A view
    that needs a key for one uses its first run.
    """

    @property
    def length(self) -> datetime.timedelta:
        """How long the play session lasted, with the breaks between runs."""
        return self.end - self.start


@dataclass(frozen=True)
class ScenarioVisit(_ConsecutiveRuns):
    """Consecutive runs on one scenario within a play session."""

    @property
    def scenario(self) -> str:
        """The name of the scenario every run of the visit was played on."""
        return self.runs[0].scenario


def split_into_play_sessions(runs: Iterable[RunData]) -> list[PlaySession]:
    """Split runs into play sessions, oldest first.

    A run joins the play session of the run that ended before it unless the
    break between them is longer than ``PLAY_SESSION_BREAK_LIMIT``. The break
    runs from that run's end to this run's start. For a run with no usable
    start it runs to this run's end, which overstates it by the run's length.
    A break of exactly the limit does not end a play session. Neither does a
    negative one, which a wrong start or a clock change can produce.

    The same runs split the same way whatever order they are handed over in.
    """
    # Sorted here, never trusted from the caller: each run is compared with
    # the one before it, so the same runs handed over in another order would
    # split at other places and nothing would show it. The key is total for
    # runs read from one stats folder, so no pair is left in the caller's
    # order.
    ordered = sorted(runs, key=_split_order)
    groups: list[list[RunData]] = []
    for run in ordered:
        if (
            groups
            and _start_or_end(run) - groups[-1][-1].datetime_object
            <= PLAY_SESSION_BREAK_LIMIT
        ):
            groups[-1].append(run)
        else:
            groups.append([run])
    return [PlaySession(tuple(group)) for group in groups]


def find_play_session_in_progress(
    play_sessions: Iterable[PlaySession], now: datetime.datetime
) -> PlaySession | None:
    """Return the play session in progress at ``now``, or None.

    Only the newest play session can be in progress: the one whose last run
    ended last. It is in progress while no more than
    ``PLAY_SESSION_BREAK_LIMIT`` has passed since that run ended, and a last
    run that ended after ``now`` counts.

    ``now`` is local wall-clock time on the machine that wrote the stats
    files, as every run time is. Pass the app's own clock, never a browser's:
    a browser on another device may be in another time zone.
    """
    # Asked of the whole list, never of one play session. After the clock
    # goes back, a play session that ended minutes ago and a later one whose
    # runs carry times still ahead of ``now`` both pass the time test, and
    # two play sessions must never both read as in progress.
    newest = max(play_sessions, key=attrgetter("end"), default=None)
    if newest is None or now - newest.end > PLAY_SESSION_BREAK_LIMIT:
        return None
    return newest


def split_into_scenario_visits(play_session: PlaySession) -> list[ScenarioVisit]:
    """Split one play session's runs into scenario visits, oldest first.

    A scenario is its name. Switching to another scenario ends a visit, and
    coming back to it later in the play session starts a new one. A change of
    sensitivity does not end a visit.
    """
    return [
        ScenarioVisit(tuple(visit_runs))
        for _scenario, visit_runs in groupby(
            play_session.runs, key=attrgetter("scenario")
        )
    ]
