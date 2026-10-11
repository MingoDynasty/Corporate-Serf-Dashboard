from datetime import datetime, timedelta

import pytest

from source.kovaaks.data_models import RunData
from source.kovaaks.play_sessions import (
    PlaySession,
    find_play_session_in_progress,
    split_into_play_sessions,
    split_into_scenario_visits,
)

TEN = datetime(2026, 5, 1, 10, 0, 0)


def _run(
    end: datetime,
    *,
    seconds: float | None = 60,
    paused: float = 0,
    scenario: str = "1w4ts",
    horizontal_sens: float = 40.0,
) -> RunData:
    """Build a run that ended at ``end``, as the parser would hold it.

    ``seconds`` is how long it took to play, and ``paused`` is the time it
    spent paused on top of that. ``seconds=None`` is a run whose stats file
    gave no usable start.
    """
    run_start = run_length = None
    if seconds is not None:
        run_length = timedelta(seconds=seconds)
        run_start = end - run_length - timedelta(seconds=paused)
    return RunData(
        datetime_object=end,
        score=100,
        sens_scale="cm/360",
        horizontal_sens=horizontal_sens,
        scenario=scenario,
        accuracy=0.5,
        run_start=run_start,
        run_length=run_length,
    )


def _after(previous: RunData, break_seconds: float, **fields) -> RunData:
    """Build a 60-second run that starts ``break_seconds`` after another ends."""
    return _run(
        previous.datetime_object + timedelta(seconds=break_seconds + 60), **fields
    )


# --- Play sessions ------------------------------------------------------------


@pytest.mark.parametrize(
    ("break_seconds", "expected_sessions"),
    [
        pytest.param(1799, 1, id="one second under 30 minutes"),
        pytest.param(1800, 1, id="exactly 30 minutes"),
        pytest.param(1801, 2, id="one second over 30 minutes"),
    ],
)
def test_only_a_break_of_more_than_30_minutes_ends_a_session(
    break_seconds, expected_sessions
) -> None:
    first = _run(TEN)
    second = _after(first, break_seconds)

    play_sessions = split_into_play_sessions([first, second])

    assert len(play_sessions) == expected_sessions
    assert [run for session in play_sessions for run in session.runs] == [
        first,
        second,
    ]


def test_a_session_crosses_midnight() -> None:
    late = _run(datetime(2026, 5, 1, 23, 58, 0))
    early = _run(datetime(2026, 5, 2, 0, 5, 0))

    (play_session,) = split_into_play_sessions([late, early])

    assert play_session.runs == (late, early)
    assert play_session.start.date() != play_session.end.date()


def test_one_day_holds_two_sessions() -> None:
    morning = [_run(TEN), _run(TEN + timedelta(minutes=5))]
    evening = [_run(TEN + timedelta(hours=9)), _run(TEN + timedelta(hours=9.1))]

    play_sessions = split_into_play_sessions(morning + evening)

    assert [session.runs for session in play_sessions] == [
        tuple(morning),
        tuple(evening),
    ]


def test_a_session_spans_its_first_runs_start_to_its_last_runs_end() -> None:
    first = _run(TEN)
    second = _after(first, 600)
    third = _after(second, 20)

    (play_session,) = split_into_play_sessions([first, second, third])

    assert play_session.start == TEN - timedelta(seconds=60)
    assert play_session.end == third.datetime_object
    # Three minutes of runs, and the breaks between them.
    assert play_session.length == timedelta(seconds=180 + 600 + 20)


@pytest.mark.parametrize(
    ("seconds", "expected_sessions"),
    [
        # It began 29.5 minutes after the last run ended.
        pytest.param(60, 1, id="a usable start"),
        # The same run, measured to its end: 30.5 minutes.
        pytest.param(None, 2, id="no usable start"),
    ],
)
def test_a_run_with_no_start_has_its_break_measured_to_its_end(
    seconds, expected_sessions
) -> None:
    first = _run(TEN)
    second = _run(TEN + timedelta(minutes=30, seconds=30), seconds=seconds)

    assert len(split_into_play_sessions([first, second])) == expected_sessions


def test_a_run_with_no_start_joins_a_session_by_its_end() -> None:
    first = _run(TEN)
    second = _run(TEN + timedelta(minutes=20), seconds=None)
    third = _after(second, 30)

    (play_session,) = split_into_play_sessions([first, second, third])

    assert play_session.runs == (first, second, third)


def test_a_session_whose_first_run_has_no_start_begins_at_that_runs_end() -> None:
    first = _run(TEN, seconds=None)
    second = _after(first, 30)

    (play_session,) = split_into_play_sessions([first, second])

    assert play_session.start == TEN
    assert play_session.length == timedelta(seconds=90)


def test_a_paused_run_begun_inside_the_limit_rejoins_its_session() -> None:
    """A pause is part of the run, not a break.

    The run began 20 minutes after the last one ended and finished 81 minutes
    after it, having been paused for an hour.
    """
    first = _run(TEN)
    paused = _run(TEN + timedelta(minutes=81), paused=3600)
    assert paused.run_start == TEN + timedelta(minutes=20)

    (play_session,) = split_into_play_sessions([first, paused])

    assert play_session.runs == (first, paused)


def test_a_run_longer_than_the_limit_starts_a_new_session() -> None:
    # The parser gives a run over 30 minutes long no start, so its break is
    # measured to its end, however soon after the last run it began.
    first = _run(TEN)
    long_run = _run(TEN + timedelta(minutes=41), seconds=None)

    play_sessions = split_into_play_sessions([first, long_run])

    assert [session.runs for session in play_sessions] == [(first,), (long_run,)]


def test_a_negative_break_counts_as_no_break() -> None:
    # A start that repeats the previous run's lands before that run's end.
    first = _run(TEN)
    second = _run(TEN + timedelta(seconds=68), seconds=127.7)
    assert second.run_start is not None
    assert second.run_start < first.datetime_object

    (play_session,) = split_into_play_sessions([first, second])

    assert play_session.runs == (first, second)


def test_runs_handed_over_out_of_order_split_the_same_way() -> None:
    first = _run(TEN)
    second = _after(first, 30)
    third = _after(second, 3600)
    fourth = _after(third, 30)
    in_order = [first, second, third, fourth]

    play_sessions = split_into_play_sessions(in_order)

    assert [session.runs for session in play_sessions] == [
        (first, second),
        (third, fourth),
    ]
    assert split_into_play_sessions([third, first, fourth, second]) == play_sessions
    assert split_into_play_sessions(reversed(in_order)) == play_sessions


def test_runs_that_ended_in_the_same_second_keep_the_order_they_came_in() -> None:
    one = _run(TEN, scenario="one")
    other = _run(TEN, scenario="other")

    assert split_into_play_sessions([one, other])[0].runs == (one, other)
    assert split_into_play_sessions([other, one])[0].runs == (other, one)


def test_no_runs_make_no_sessions() -> None:
    assert split_into_play_sessions([]) == []


def test_one_run_makes_a_session_of_its_own() -> None:
    run = _run(TEN)

    (play_session,) = split_into_play_sessions([run])

    assert play_session.runs == (run,)
    assert play_session.start == run.run_start
    assert play_session.end == TEN
    assert play_session.length == timedelta(seconds=60)


# --- In progress --------------------------------------------------------------


@pytest.mark.parametrize(
    ("since_last_run", "in_progress"),
    [
        pytest.param(timedelta(minutes=5), True, id="5 minutes after"),
        pytest.param(timedelta(minutes=30), True, id="exactly 30 minutes after"),
        pytest.param(timedelta(minutes=30, seconds=1), False, id="one second later"),
        pytest.param(timedelta(minutes=-5), True, id="a last run in the future"),
        pytest.param(timedelta(days=-2), True, id="a last run days in the future"),
    ],
)
def test_a_session_is_in_progress_until_30_minutes_after_its_last_run(
    since_last_run, in_progress
) -> None:
    earlier = _run(TEN - timedelta(hours=3))
    first = _run(TEN - timedelta(minutes=2))
    last = _run(TEN)
    play_sessions = split_into_play_sessions([earlier, first, last])
    newest = play_sessions[-1]
    assert newest.runs == (first, last)

    found = find_play_session_in_progress(play_sessions, TEN + since_last_run)

    assert found == (newest if in_progress else None)


def test_no_sessions_means_none_in_progress() -> None:
    assert find_play_session_in_progress([], TEN) is None


def test_only_the_newest_session_that_passes_the_time_test_is_in_progress() -> None:
    """After the clock goes back, an older session can still pass the time test.

    One session ended ten minutes ago. A later-sorted one carries times still
    ahead of the clock. Asked one at a time, both would read as in progress.
    """
    ended_minutes_ago = _run(TEN)
    still_ahead = _run(TEN + timedelta(minutes=45))
    now = TEN + timedelta(minutes=10)
    older, newest = split_into_play_sessions([ended_minutes_ago, still_ahead])
    for session in (older, newest):
        assert find_play_session_in_progress([session], now) == session

    assert find_play_session_in_progress([older, newest], now) == newest
    assert find_play_session_in_progress([newest, older], now) == newest


def test_a_run_that_lands_late_reopens_a_session_that_read_as_ended() -> None:
    first = _run(TEN)
    paused = _run(TEN + timedelta(minutes=81), paused=3600)

    # While the paused run is still going, the app has only the first run.
    before = split_into_play_sessions([first])
    assert find_play_session_in_progress(before, TEN + timedelta(minutes=45)) is None

    after = split_into_play_sessions([first, paused])
    found = find_play_session_in_progress(after, paused.datetime_object)

    assert found is not None
    assert found.runs == (first, paused)


# --- Scenario visits ----------------------------------------------------------


def _session(*runs: RunData) -> PlaySession:
    (play_session,) = split_into_play_sessions(runs)
    return play_session


def test_a_return_to_a_scenario_later_in_the_session_is_a_new_visit() -> None:
    first = _run(TEN, scenario="1w4ts")
    second = _after(first, 20, scenario="1w4ts")
    third = _after(second, 20, scenario="Air Voltaic")
    fourth = _after(third, 20, scenario="1w4ts")

    visits = split_into_scenario_visits(_session(first, second, third, fourth))

    assert [(visit.scenario, visit.runs) for visit in visits] == [
        ("1w4ts", (first, second)),
        ("Air Voltaic", (third,)),
        ("1w4ts", (fourth,)),
    ]


def test_a_visit_of_one_run_spans_that_run() -> None:
    run = _run(TEN)

    (visit,) = split_into_scenario_visits(_session(run))

    assert visit.runs == (run,)
    assert visit.start == run.run_start
    assert visit.end == TEN


def test_a_visit_spans_its_first_runs_start_to_its_last_runs_end() -> None:
    other = _run(TEN, scenario="Air Voltaic")
    first = _after(other, 20)
    last = _after(first, 300)

    _other_visit, visit = split_into_scenario_visits(_session(other, first, last))

    assert visit.start == first.run_start
    assert visit.end == last.datetime_object


def test_a_visit_whose_first_run_has_no_start_begins_at_that_runs_end() -> None:
    first = _run(TEN, seconds=None)
    second = _after(first, 20)

    (visit,) = split_into_scenario_visits(_session(first, second))

    assert visit.start == TEN
    assert visit.end == second.datetime_object


def test_a_change_of_sensitivity_does_not_end_a_visit() -> None:
    first = _run(TEN, horizontal_sens=40.0)
    second = _after(first, 20, horizontal_sens=30.0)

    (visit,) = split_into_scenario_visits(_session(first, second))

    assert visit.runs == (first, second)


def test_a_visit_never_crosses_from_one_session_into_the_next() -> None:
    first = _run(TEN)
    second = _after(first, 3600)

    play_sessions = split_into_play_sessions([first, second])

    assert [
        [visit.runs for visit in split_into_scenario_visits(session)]
        for session in play_sessions
    ] == [[(first,)], [(second,)]]
