import math

import pytest

from source.kovaaks.performance_file import (
    COUNTDOWN_TOLERANCE,
    Scoring,
    read_performance_file,
)
from tests.performance_files import (
    COUNTDOWN_FIXTURE,
    COUNTDOWN_FIXTURE_HASH,
    DEFAULT_HASH,
    FIXED_LENGTH_FIXTURE,
    build_performance_file,
    countdown_events,
    score_event,
)


def test_a_real_countdown_file_answers_with_its_time_limit_and_hash():
    reading = read_performance_file(COUNTDOWN_FIXTURE.read_bytes())

    assert reading.scoring is Scoring.TIME_SCORED
    assert reading.time_limit == 1000.0
    assert reading.scenario_hash == COUNTDOWN_FIXTURE_HASH
    assert reading.score_events == 60
    # The distance is a start lag of a few milliseconds, far inside the
    # tolerance. A reader that mis-summed the events would not land here.
    assert reading.largest_distance is not None
    assert reading.largest_distance < 0.02


def test_a_real_fixed_length_file_answers_not_time_scored():
    reading = read_performance_file(FIXED_LENGTH_FIXTURE.read_bytes())

    assert reading.scoring is Scoring.NOT_TIME_SCORED
    assert reading.time_limit == 60.0
    assert reading.scenario_hash == "a5fa9fbc3d55851b11534c60b85a9247"
    assert reading.score_events == 60
    assert reading.largest_distance is not None
    assert reading.largest_distance > 40


def test_a_score_that_falls_faster_than_the_clock_is_not_time_scored():
    """250 - 1.5 * t is on the line's edge after one second and off it after two."""
    events = countdown_events(250.0, 10, points_per_second=1.5)

    reading = read_performance_file(build_performance_file(events, time_limit=250.0))

    assert reading.scoring is Scoring.NOT_TIME_SCORED


def test_a_first_event_that_grants_the_limit_then_gains_is_not_time_scored():
    events = [(1.0, 999.0), (2.0, 5.0), (3.0, 3.0), (4.0, 8.0)]

    reading = read_performance_file(build_performance_file(events))

    assert reading.scoring is Scoring.NOT_TIME_SCORED


def test_a_slowed_countdown_follows_the_files_timescale():
    """A scenario at 0.9 speed loses 0.9 points per real second.

    Six events are what tells the two timescales apart: read at 1.0 the score
    drifts a tenth of a point per second, and crosses the tolerance at the
    sixth.
    """
    events = countdown_events(1000.0, 6, points_per_second=0.9)

    slowed = read_performance_file(build_performance_file(events, timescale=0.9))
    full_speed = read_performance_file(build_performance_file(events, timescale=1.0))

    assert slowed.scoring is Scoring.TIME_SCORED
    assert slowed.time_limit == 1000.0
    assert full_speed.scoring is Scoring.NOT_TIME_SCORED


@pytest.mark.parametrize(
    ("early_by", "expected"),
    [
        (0.1, Scoring.TIME_SCORED),
        (0.6, Scoring.NOT_TIME_SCORED),
    ],
)
def test_the_tolerance_absorbs_a_start_lag_and_no_more(early_by, expected):
    events = countdown_events(1000.0, 30, early_by=early_by)

    reading = read_performance_file(build_performance_file(events))

    assert reading.scoring is expected
    assert reading.largest_distance == pytest.approx(early_by, abs=1e-3)
    assert (early_by <= COUNTDOWN_TOLERANCE) is (expected is Scoring.TIME_SCORED)


def test_a_seven_event_countdown_answers_with_its_time_limit():
    reading = read_performance_file(
        build_performance_file(countdown_events(750.0, 7), time_limit=750.0)
    )

    assert reading.scoring is Scoring.TIME_SCORED
    assert reading.time_limit == 750.0
    assert reading.scenario_hash == DEFAULT_HASH


@pytest.mark.parametrize("count", [0, 1])
def test_fewer_than_two_score_events_is_not_time_scored(count):
    """One event cannot show a score falling, however well it sits on the line."""
    reading = read_performance_file(
        build_performance_file(countdown_events(1000.0, count))
    )

    assert reading.scoring is Scoring.NOT_TIME_SCORED
    assert reading.score_events == count


def test_another_schema_version_cannot_answer():
    reading = read_performance_file(
        build_performance_file(countdown_events(), schema_version=2)
    )

    assert reading.scoring is Scoring.CANNOT_ANSWER
    assert reading.time_limit is None
    assert reading.scenario_hash is None


def test_an_empty_file_cannot_answer():
    assert read_performance_file(b"").scoring is Scoring.CANNOT_ANSWER


def test_truncated_bytes_cannot_answer():
    """A cut inside the last event must not read as a shorter, complete file."""
    data = COUNTDOWN_FIXTURE.read_bytes()

    assert read_performance_file(data[:-3]).scoring is Scoring.CANNOT_ANSWER


def test_no_truncation_of_a_real_file_raises():
    data = COUNTDOWN_FIXTURE.read_bytes()

    for length in range(0, len(data), 7):
        assert read_performance_file(data[:length]).scoring in set(Scoring)


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"\xff" * 12, id="a varint that never ends"),
        pytest.param(b"\x0b\x00", id="a group, which proto3 does not write"),
        pytest.param(b"\x0a\x7f\x00", id="a length past the end of the file"),
        pytest.param(b"\x08\x01", id="a header that is not a message"),
    ],
)
def test_bytes_that_are_not_a_performance_file_cannot_answer(data):
    assert read_performance_file(data).scoring is Scoring.CANNOT_ANSWER


@pytest.mark.parametrize(
    "header_fields",
    [
        pytest.param({"with_header": False}, id="no header"),
        pytest.param({"schema_version": None}, id="no schema version"),
        pytest.param({"scenario_hash": None}, id="no scenario hash"),
        pytest.param({"time_limit": None}, id="no time limit"),
        pytest.param({"time_limit": 0.0}, id="a time limit of zero"),
        pytest.param({"time_limit": -1000.0}, id="a negative time limit"),
        pytest.param({"time_limit": math.inf}, id="an infinite time limit"),
        pytest.param({"timescale": None}, id="no timescale"),
        pytest.param({"timescale": 0.0}, id="a timescale of zero"),
        pytest.param({"timescale": -1.0}, id="a negative timescale"),
        pytest.param({"timescale": math.nan}, id="a timescale that is not a number"),
    ],
)
def test_a_header_missing_what_the_check_needs_cannot_answer(header_fields):
    """A header with no usable limit, timescale, or hash describes no countdown.

    Without this a missing timescale would read as zero, and a file whose
    score never moved would sit on a line that never falls.
    """
    reading = read_performance_file(
        build_performance_file(countdown_events(), **header_fields)
    )

    assert reading.scoring is Scoring.CANNOT_ANSWER


def test_a_score_event_that_is_not_a_number_is_not_time_scored():
    events = [*countdown_events(1000.0, 5), (6.0, math.nan)]

    reading = read_performance_file(build_performance_file(events))

    assert reading.scoring is Scoring.NOT_TIME_SCORED
    assert reading.largest_distance == math.inf


def test_an_event_with_no_timestamp_reads_as_time_zero():
    """proto3 leaves a zero off the wire, so its absence is the value zero."""
    untimed = b"\x12\x07" + b"\x3a\x05\x0d" + b"\x00\x00\x7a\x44"
    data = build_performance_file() + untimed + score_event(1.0, -1.0)

    reading = read_performance_file(data)

    assert reading.scoring is Scoring.TIME_SCORED
    assert reading.score_events == 2
    assert reading.largest_distance == 0.0
