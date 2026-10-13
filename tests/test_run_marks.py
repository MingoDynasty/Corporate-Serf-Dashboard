"""The check and the star a past run carries.

The first half judges plain run records, the maintainer's worked example
among them. The second half replays real files: stats files loaded through
the real loader, performance files beside them, and runs landed through the
real watchdog handler, so it would notice the list and the run toast giving
one run two answers.
"""

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import dash
import pytest
from sortedcontainers import SortedList

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.app_shell import _run_event_data  # noqa: E402
from source.components.run_marks import (  # noqa: E402
    Chased,
    RunMark,
    mark_runs,
    mark_scenario_runs,
    what_runs_chased,
)
from source.components.score_threshold import (  # noqa: E402
    ThresholdVerdict,
    Unjudged,
    judge_run,
    threshold_verdict,
)
from source.kovaaks import data_service  # noqa: E402
from source.kovaaks.data_models import RunData  # noqa: E402
from source.kovaaks.data_service import (  # noqa: E402
    get_runs_in_play_order,
    new_high_score_runs,
)
from source.kovaaks.time_scored_service import (  # noqa: E402
    PaceBasis,
    index_performance_files,
)
from source.my_watchdog import file_watchdog  # noqa: E402
from tests.performance_files import (  # noqa: E402
    DEFAULT_HASH,
    build_performance_file,
    countdown_events,
)

SCENARIO = "Ground Plaza Sparky V3"
OTHER_VERSION = "ffffffffffffffffffffffffffffffff"
FIRST_PLAYED = datetime(2026, 10, 1, 12, 0, 0)


def _run(
    score: float,
    order: int,
    *,
    sensitivity: float = 40.0,
    scenario_hash: str | None = None,
) -> RunData:
    """Build one run of the scenario, ``order`` minutes after the first."""
    ended = FIRST_PLAYED + timedelta(minutes=order)
    return RunData(
        datetime_object=ended,
        score=score,
        sens_scale="cm/360",
        horizontal_sens=sensitivity,
        scenario=SCENARIO,
        accuracy=0.5,
        scenario_hash=scenario_hash,
        stats_file_name=(
            f"{SCENARIO} - Challenge - {ended:%Y.%m.%d-%H.%M.%S} Stats.csv"
        ),
    )


def _no_pace(_version: str | None) -> PaceBasis | None:
    return None


def _checked(marks: dict[RunData, RunMark]) -> set[float]:
    return {run.score for run, mark in marks.items() if mark.passed}


def _starred(marks: dict[RunData, RunMark]) -> set[float]:
    return {run.score for run, mark in marks.items() if mark.is_new_pb}


# --- The maintainer's example --------------------------------------------------

# The PB is 100. Runs A to E are then played in order at one sensitivity.
EXAMPLE_SCORES = {"PB": 100.0, "A": 85.0, "B": 95.0, "C": 120.0, "D": 100.0, "E": 110.0}


def _example_runs() -> dict[str, RunData]:
    return {
        name: _run(score, order)
        for order, (name, score) in enumerate(EXAMPLE_SCORES.items())
    }


@pytest.mark.parametrize(
    ("percentage", "checked"),
    [
        (90.0, {"B", "C", "E"}),
        (99.0, {"C"}),
        # Above 100 a run has to beat the PB it was chasing by that margin.
        (110.0, {"C"}),
    ],
)
def test_the_example_runs_are_checked_by_the_percentage(percentage, checked):
    runs = _example_runs()

    marks = mark_runs(list(runs.values()), percentage, _no_pace)

    assert {name for name, run in runs.items() if marks[run].passed} == checked
    assert {name for name, run in runs.items() if marks[run].is_new_pb} == {"C"}


def test_each_example_run_is_judged_against_the_pb_it_was_chasing():
    runs = _example_runs()

    chased = what_runs_chased(list(runs.values()), _no_pace)

    assert {name: chased[run].previous_best for name, run in runs.items()} == {
        "PB": None,
        "A": 100.0,
        "B": 100.0,
        "C": 100.0,
        # C raised the PB, so the two runs after it chase 120.
        "D": 120.0,
        "E": 120.0,
    }


def test_a_later_pb_removes_no_check():
    """B passed against 100. C's 120 does not make B a miss."""
    runs = _example_runs()
    before_c = [runs[name] for name in ("PB", "A", "B")]

    marks_before = mark_runs(before_c, 90.0, _no_pace)
    marks_after = mark_runs(list(runs.values()), 90.0, _no_pace)

    assert marks_before[runs["B"]] == marks_after[runs["B"]]
    assert marks_after[runs["B"]].passed


def test_clearing_the_percentage_and_setting_it_back_returns_every_check():
    runs = list(_example_runs().values())

    at_ninety = mark_runs(runs, 90.0, _no_pace)
    cleared = mark_runs(runs, None, _no_pace)
    restored = mark_runs(runs, 90.0, _no_pace)

    assert _checked(cleared) == set()
    assert restored == at_ninety


def test_an_empty_percentage_judges_no_run_and_keeps_every_star():
    runs = list(_example_runs().values())

    marks = mark_runs(runs, None, _no_pace)

    assert {mark.verdict for mark in marks.values()} == {Unjudged.NO_PERCENTAGE_SET}
    assert _starred(marks) == {120.0}


# --- The runs nothing judges ---------------------------------------------------


def test_a_scenarios_first_run_is_not_judged_and_is_never_a_new_pb():
    first = _run(100.0, 0)

    marks = mark_runs([first], 95.0, _no_pace)

    assert marks[first] == RunMark(verdict=Unjudged.FIRST_RUN, is_new_pb=False)


def test_the_first_run_at_a_new_sensitivity_is_not_judged():
    first, at_new_sensitivity = _run(100.0, 0), _run(99.0, 1, sensitivity=30.0)

    marks = mark_runs([first, at_new_sensitivity], 95.0, _no_pace)

    assert marks[at_new_sensitivity] == RunMark(
        verdict=Unjudged.FIRST_RUN, is_new_pb=False
    )


def test_a_new_pb_at_a_new_sensitivity_has_its_star_and_no_check():
    """A star never depends on the threshold."""
    first, new_pb = _run(100.0, 0), _run(130.0, 1, sensitivity=30.0)

    marks = mark_runs([first, new_pb], 95.0, _no_pace)

    assert marks[new_pb] == RunMark(verdict=Unjudged.FIRST_RUN, is_new_pb=True)
    assert not marks[new_pb].passed


def test_the_second_run_at_a_sensitivity_is_judged():
    runs = [_run(100.0, 0), _run(99.0, 1, sensitivity=30.0)]
    second_at_it = _run(98.0, 2, sensitivity=30.0)

    marks = mark_runs([*runs, second_at_it], 95.0, _no_pace)

    assert marks[second_at_it].passed


@pytest.mark.parametrize("previous_best", [0.0, -5.0])
def test_a_run_compared_by_score_with_a_pb_of_zero_or_less_is_not_judged(
    previous_best,
):
    first, not_a_pb = _run(previous_best, 0), _run(previous_best - 1, 1)

    marks = mark_runs([first, not_a_pb], 95.0, _no_pace)

    assert marks[not_a_pb] == RunMark(
        verdict=Unjudged.NO_PERCENTAGE_TO_JUDGE_BY, is_new_pb=False
    )


def test_a_new_pb_over_a_pb_of_zero_has_its_star_and_no_check():
    first, new_pb = _run(0.0, 0), _run(10.0, 1)

    marks = mark_runs([first, new_pb], 95.0, _no_pace)

    assert marks[new_pb] == RunMark(
        verdict=Unjudged.NO_PERCENTAGE_TO_JUDGE_BY, is_new_pb=True
    )


@pytest.mark.parametrize(
    ("runs", "reason"),
    [
        # Each of these also fits a later reason, and takes the first.
        ([_run(0.0, 0)], Unjudged.NO_PERCENTAGE_SET),
        ([_run(0.0, 0), _run(-1.0, 1, sensitivity=30.0)], Unjudged.NO_PERCENTAGE_SET),
        ([_run(0.0, 0), _run(-1.0, 1)], Unjudged.NO_PERCENTAGE_SET),
    ],
    ids=["first run", "new sensitivity", "pb of zero"],
)
def test_an_empty_percentage_is_the_reason_given_when_more_than_one_applies(
    runs, reason
):
    marks = mark_runs(runs, None, _no_pace)

    assert marks[runs[-1]].verdict is reason


def test_a_first_run_is_the_reason_given_before_a_pb_of_zero():
    first, at_new_sensitivity = _run(0.0, 0), _run(-1.0, 1, sensitivity=30.0)

    marks = mark_runs([first, at_new_sensitivity], 95.0, _no_pace)

    assert marks[at_new_sensitivity].verdict is Unjudged.FIRST_RUN


@pytest.mark.parametrize(
    ("previous_best", "is_new_sensitivity", "goal", "reason"),
    [
        (100.0, False, None, Unjudged.NO_PERCENTAGE_SET),
        (None, True, 95.0, Unjudged.FIRST_RUN),
        (100.0, True, 95.0, Unjudged.FIRST_RUN),
        (0.0, False, 95.0, Unjudged.NO_PERCENTAGE_TO_JUDGE_BY),
    ],
)
def test_judge_run_names_why_a_run_is_not_judged(
    previous_best, is_new_sensitivity, goal, reason
):
    assert judge_run(90.0, previous_best, is_new_sensitivity, None, goal) is reason


def test_a_run_exactly_at_the_goal_passes():
    """In floats, 20.6 * 95 / 100 is a hair over 19.57."""
    verdict = judge_run(19.57, 20.6, False, None, 95.0)

    assert isinstance(verdict, ThresholdVerdict)
    assert verdict.passed
    assert not verdict.by_pace


# --- Pace, and a run's own version ---------------------------------------------


def _basis_of(**constants: float):
    """Answer for the versions named, and for no other."""
    versions = {"current": DEFAULT_HASH, "older": OTHER_VERSION}
    by_hash = {
        versions[name]: PaceBasis(constant, versions[name])
        for name, constant in constants.items()
    }
    return by_hash.get


def test_a_time_scored_run_is_judged_by_pace():
    """896.2 took 103.8 seconds and 883.02 took 116.98: 88.7% of its pace."""
    pb = _run(896.2, 0, scenario_hash=DEFAULT_HASH)
    slower = _run(883.02, 1, scenario_hash=DEFAULT_HASH)

    marks = mark_runs([pb, slower], 95.0, _basis_of(current=1000.0))

    verdict = marks[slower].verdict
    assert isinstance(verdict, ThresholdVerdict)
    assert verdict.by_pace
    assert not verdict.passed
    assert round(verdict.percentage, 1) == 88.7
    # By score the same run is 98.5% of the PB, and would pass.
    assert mark_runs([pb, slower], 95.0, _no_pace)[slower].passed


def test_a_time_scored_pb_of_zero_or_less_is_still_judged_by_pace():
    """Pace needs positive times, not a positive previous best."""
    pb = _run(-10.0, 0, scenario_hash=DEFAULT_HASH)
    slower = _run(-20.0, 1, scenario_hash=DEFAULT_HASH)

    marks = mark_runs([pb, slower], 95.0, _basis_of(current=1000.0))

    verdict = marks[slower].verdict
    assert isinstance(verdict, ThresholdVerdict)
    assert verdict.by_pace
    assert verdict.passed


def test_a_run_is_judged_under_its_own_version_not_the_newest_runs():
    """A later run on another version changes no earlier check."""
    pb = _run(896.2, 0, scenario_hash=OTHER_VERSION)
    slower = _run(883.02, 1, scenario_hash=OTHER_VERSION)
    on_a_newer_version = _run(700.0, 2, scenario_hash=DEFAULT_HASH)
    basis = _basis_of(older=1000.0)

    before = mark_runs([pb, slower], 95.0, basis)
    after = mark_runs([pb, slower, on_a_newer_version], 95.0, basis)

    assert before[slower] == after[slower]
    verdict = after[slower].verdict
    assert isinstance(verdict, ThresholdVerdict)
    assert verdict.by_pace
    assert not verdict.passed


def test_a_run_chasing_a_pb_from_another_version_is_judged_by_score():
    pb = _run(896.2, 0, scenario_hash=OTHER_VERSION)
    slower = _run(883.02, 1, scenario_hash=DEFAULT_HASH)

    chased = what_runs_chased([pb, slower], _basis_of(current=1000.0, older=1000.0))

    assert chased[slower] == Chased(
        previous_best=896.2, is_new_sensitivity=False, pace_constant=None
    )


def test_a_run_whose_file_names_no_version_is_judged_by_score():
    pb = _run(896.2, 0, scenario_hash=DEFAULT_HASH)
    slower = _run(883.02, 1, scenario_hash=None)
    asked: list[str | None] = []

    def basis(version):
        asked.append(version)
        return PaceBasis(1000.0, DEFAULT_HASH) if version else None

    chased = what_runs_chased([pb, slower], basis)

    assert chased[slower].pace_constant is None
    assert asked == [DEFAULT_HASH, None]


def test_on_a_tied_score_the_earliest_run_holds_the_pb():
    """The run that first reached the score names the version compared under."""
    pb = _run(896.2, 0, scenario_hash=OTHER_VERSION)
    tie = _run(896.2, 1, scenario_hash=DEFAULT_HASH)
    slower = _run(883.02, 2, scenario_hash=DEFAULT_HASH)

    chased = what_runs_chased([pb, tie, slower], _basis_of(current=1000.0))

    assert chased[slower].previous_best == 896.2
    assert chased[slower].pace_constant is None


def test_each_version_is_asked_about_once():
    runs = [
        _run(896.2, 0, scenario_hash=DEFAULT_HASH),
        _run(883.02, 1, scenario_hash=DEFAULT_HASH),
        _run(880.0, 2, scenario_hash=OTHER_VERSION),
        _run(881.0, 3, scenario_hash=DEFAULT_HASH),
    ]
    asked: list[str | None] = []

    def basis(version):
        asked.append(version)

    what_runs_chased(runs, basis)

    assert asked == [DEFAULT_HASH, OTHER_VERSION]


# --- A replay on real stats and performance files ------------------------------

COUNTDOWN = build_performance_file(countdown_events(1000.0, 60))
OTHER_VERSION_COUNTDOWN = build_performance_file(
    countdown_events(1000.0, 60), scenario_hash=OTHER_VERSION
)
FIXED_LENGTH = build_performance_file([(1.0, 73.0), (2.0, 27.0), (3.0, 53.0)])
FIRST, SECOND, THIRD = (
    "2026.08.01-10.00.00",
    "2026.08.02-10.00.00",
    "2026.08.03-10.00.00",
)


class _Folders:
    """A stats folder and the ``performances`` folder beside it."""

    def __init__(self, root: Path):
        self.stats = root / "stats"
        self.performances = root / "performances"
        self.stats.mkdir()
        self.performances.mkdir()

    def stats_file(
        self,
        stamp: str,
        score: float,
        *,
        scenario_hash: str | None = DEFAULT_HASH,
        sensitivity: str = "40.8",
    ) -> Path:
        """Write one stats file the real parser reads, and return its path."""
        lines = [
            f"Score:,{score}",
            "Sens Scale:,cm/360",
            f"Horiz Sens:,{sensitivity}",
            f"Vert Sens:,{sensitivity}",
            f"Scenario:,{SCENARIO}",
        ]
        if scenario_hash is not None:
            lines.append(f"Hash:,{scenario_hash}")
        lines += [
            data_service.POSSIBLE_SUB_CSV_HEADERS[0],
            "Rifle,100,50,75,100,,cm/360,40.8,40.8,103,0,0,0,0,0,0,0,0",
            "",
        ]
        path = self.stats / f"{SCENARIO} - Challenge - {stamp} Stats.csv"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def performance_file(self, stamp: str, data: bytes = COUNTDOWN) -> Path:
        path = self.performances / f"{SCENARIO} - Challenge - {stamp} Performance.perf"
        path.write_bytes(data)
        return path

    def start(self) -> None:
        """Load every stats file and list the performance files, as startup does."""
        data_service.initialize_kovaaks_data(str(self.stats))
        index_performance_files(str(self.stats))


@pytest.fixture
def folders(tmp_path, monkeypatch) -> _Folders:
    monkeypatch.setattr(data_service, "kovaaks_database", {})
    monkeypatch.setattr(
        data_service,
        "run_database",
        SortedList(key=lambda run: run.datetime_object),
    )
    return _Folders(tmp_path)


def _land(monkeypatch, stats_file: Path):
    """Land one stats file through the watchdog and return its queued message."""
    messages = []
    monkeypatch.setattr(file_watchdog.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        file_watchdog, "message_queue", SimpleNamespace(append=messages.append)
    )
    monkeypatch.setattr(
        file_watchdog, "schedule_rank_freshness_refresh", lambda *_args: None
    )
    file_watchdog.run_import_failure_queue.clear()

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(is_directory=False, src_path=str(stats_file))
    )

    assert file_watchdog.drain_run_import_failures() == []
    (message,) = messages
    return message


def _mark_of(stamp: str, percentage: float | str | None = 95.0) -> RunMark:
    """Mark the scenario's runs from the run store, and return one run's."""
    marks = mark_scenario_runs(SCENARIO, percentage)
    (run,) = [
        run
        for run in marks
        if run.stats_file_name == f"{SCENARIO} - Challenge - {stamp} Stats.csv"
    ]
    return marks[run]


def _missed_by_pace(mark: RunMark) -> bool:
    verdict = mark.verdict
    return (
        isinstance(verdict, ThresholdVerdict) and verdict.by_pace and not verdict.passed
    )


def _passed_by_score(mark: RunMark) -> bool:
    verdict = mark.verdict
    return (
        isinstance(verdict, ThresholdVerdict) and not verdict.by_pace and verdict.passed
    )


def test_a_run_that_missed_by_pace_keeps_that_after_a_run_on_a_newer_version(
    folders, monkeypatch
):
    """Under the newest run's version it would be judged by score, and pass."""
    folders.stats_file(FIRST, 896.2)
    folders.stats_file(SECOND, 883.02)
    folders.performance_file(SECOND)
    folders.start()
    assert _missed_by_pace(_mark_of(SECOND))

    folders.performance_file(THIRD, OTHER_VERSION_COUNTDOWN)
    _land(monkeypatch, folders.stats_file(THIRD, 880.0, scenario_hash=OTHER_VERSION))

    assert _missed_by_pace(_mark_of(SECOND))


def test_a_run_turns_to_pace_when_a_file_of_its_version_first_answers(
    folders, monkeypatch
):
    """It was played before the app could tell its version is time-scored."""
    folders.stats_file(FIRST, 896.2)
    folders.stats_file(SECOND, 883.02)
    folders.start()
    assert _passed_by_score(_mark_of(SECOND))

    folders.performance_file(THIRD)
    _land(monkeypatch, folders.stats_file(THIRD, 880.0))

    assert _missed_by_pace(_mark_of(SECOND))


def test_a_run_that_missed_by_pace_passes_by_score_after_a_file_shows_no_countdown(
    folders, monkeypatch
):
    """A later file of the same version answers for every run of it."""
    folders.stats_file(FIRST, 896.2)
    folders.stats_file(SECOND, 883.02)
    folders.performance_file(SECOND)
    folders.start()
    assert _missed_by_pace(_mark_of(SECOND))

    folders.performance_file(THIRD, FIXED_LENGTH)
    _land(monkeypatch, folders.stats_file(THIRD, 880.0))

    assert _passed_by_score(_mark_of(SECOND))


def test_a_cleared_percentage_field_turns_every_check_off(folders):
    """A cleared number field sends an empty string, not nothing."""
    folders.stats_file(FIRST, 896.2)
    folders.stats_file(SECOND, 890.0)
    folders.start()
    assert _mark_of(SECOND, 95).passed

    assert _mark_of(SECOND, "").verdict is Unjudged.NO_PERCENTAGE_SET
    assert _mark_of(SECOND, None).verdict is Unjudged.NO_PERCENTAGE_SET


def test_a_scenario_with_no_runs_has_no_marks(folders):
    folders.start()

    assert mark_scenario_runs(SCENARIO, 95.0) == {}


# --- The newest run's mark and the toast it got --------------------------------


def _toast_verdict(message, percentage: float) -> ThresholdVerdict | None:
    """Judge a landed run the way its toast was, from its queued message."""
    return threshold_verdict(
        # Projected the way the app shell's drain does.
        _run_event_data(message, message.datetime_created, 120.0),
        percentage,
        True,
    )


def _newest_mark(percentage: float) -> RunMark:
    marks = mark_scenario_runs(SCENARIO, percentage)
    return marks[get_runs_in_play_order(SCENARIO)[-1]]


LANDINGS = {
    "by pace, a miss": dict(score=883.02, own_file=COUNTDOWN),
    "by pace, a pass": dict(score=895.0, own_file=COUNTDOWN),
    "by pace, a new pb": dict(score=899.0, own_file=COUNTDOWN),
    "its file shows no countdown": dict(score=883.02, own_file=FIXED_LENGTH),
    "no file of its own": dict(score=883.02, own_file=None),
    "on another version": dict(
        score=883.02, own_file=OTHER_VERSION_COUNTDOWN, scenario_hash=OTHER_VERSION
    ),
    "no version named": dict(score=883.02, own_file=None, scenario_hash=None),
    "at a new sensitivity": dict(score=883.02, own_file=COUNTDOWN, sensitivity="30.0"),
}


@pytest.mark.parametrize("landing", LANDINGS.values(), ids=LANDINGS.keys())
@pytest.mark.parametrize("percentage", [90.0, 99.0])
def test_the_newest_runs_mark_agrees_with_the_toast_it_got(
    folders, monkeypatch, landing, percentage
):
    folders.stats_file(FIRST, 884.41)
    folders.stats_file(SECOND, 896.2)
    folders.performance_file(SECOND)
    folders.start()
    if landing["own_file"] is not None:
        folders.performance_file(THIRD, landing["own_file"])

    message = _land(
        monkeypatch,
        folders.stats_file(
            THIRD,
            landing["score"],
            scenario_hash=landing.get("scenario_hash", DEFAULT_HASH),
            sensitivity=landing.get("sensitivity", "40.8"),
        ),
    )

    toast = _toast_verdict(message, percentage)
    mark = _newest_mark(percentage)
    if toast is None:
        assert isinstance(mark.verdict, Unjudged)
    else:
        assert mark.verdict == toast


def test_a_scenarios_first_landed_run_is_unjudged_by_both(folders, monkeypatch):
    folders.start()
    folders.performance_file(FIRST)

    message = _land(monkeypatch, folders.stats_file(FIRST, 896.2))

    assert _toast_verdict(message, 95.0) is None
    assert _newest_mark(95.0) == RunMark(verdict=Unjudged.FIRST_RUN, is_new_pb=False)


def test_a_run_chasing_an_older_versions_pb_agrees_with_its_toast(folders, monkeypatch):
    """Both compare by score: the constant is not known to hold for that PB."""
    folders.stats_file(FIRST, 896.2, scenario_hash=OTHER_VERSION)
    folders.stats_file(SECOND, 884.41)
    folders.performance_file(SECOND)
    folders.start()
    folders.performance_file(THIRD)

    message = _land(monkeypatch, folders.stats_file(THIRD, 883.02))

    toast = _toast_verdict(message, 95.0)
    assert toast is not None
    assert not toast.by_pace
    assert _newest_mark(95.0).verdict == toast


# --- The star and the chart's --------------------------------------------------


def test_every_star_is_on_a_run_the_chart_stars(folders):
    folders.stats_file(FIRST, 884.41)
    folders.stats_file(SECOND, 896.2)
    folders.stats_file(THIRD, 896.2)
    folders.start()

    marks = mark_scenario_runs(SCENARIO, 95.0)

    assert {run for run, mark in marks.items() if mark.is_new_pb} == (
        new_high_score_runs(get_runs_in_play_order(SCENARIO))
    )
    # A tie is not a new PB: the earliest run to reach a score holds it.
    assert _starred(marks) == {896.2}
    assert sum(mark.is_new_pb for mark in marks.values()) == 1
