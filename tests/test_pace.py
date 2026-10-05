import math

import pytest

from source.kovaaks.pace import (
    pace_goal_met,
    pace_percent,
    pace_threshold_score,
    percent_faster,
)

CONSTANT = 1000.0


def test_pace_percent_is_the_reference_time_over_the_runs_time():
    # A 905 took 95 s and a 900 took 100 s, so the 900 ran at 95% of the pace.
    assert pace_percent(CONSTANT, 905.0, 900.0) == 95.0
    assert pace_percent(CONSTANT, 900.0, 905.0) == pytest.approx(105.2632, abs=1e-4)
    # The proposal's worked run: 883.02 against a PB of 896.17.
    assert pace_percent(CONSTANT, 896.17, 883.02) == pytest.approx(88.7588, abs=1e-4)


def test_percent_faster_is_the_next_rank_gap_and_the_personal_best_gain():
    # The gap: a PB of 896.2 against Lavender at 899.
    assert percent_faster(CONSTANT, 896.2, 899.0) == pytest.approx(2.7723, abs=1e-4)
    assert percent_faster(CONSTANT, 999.0, 999.25) == pytest.approx(33.3333, abs=1e-4)
    # The gain: 884.41 to 896.17.
    assert percent_faster(CONSTANT, 884.41, 896.17) == pytest.approx(11.3262, abs=1e-4)
    # A slower run is a negative gain, which the session log prints.
    assert percent_faster(CONSTANT, 896.17, 883.02) == pytest.approx(-11.2412, abs=1e-4)


def test_a_score_percentage_understates_pace_by_the_score_over_the_time():
    """The same two scores read 0.3% apart by score and 2.8% apart by pace."""
    by_score = (899.0 - 896.2) / 896.2 * 100
    by_pace = percent_faster(CONSTANT, 896.2, 899.0)

    assert by_score == pytest.approx(0.3124, abs=1e-4)
    assert by_pace is not None
    assert by_pace / by_score == pytest.approx(896.2 / (CONSTANT - 899.0), rel=1e-9)


def test_pace_threshold_score_finishes_at_the_goal_percentage_of_pb_pace():
    line = pace_threshold_score(CONSTANT, 896.2, 95.0)

    assert line == pytest.approx(890.7368, abs=1e-4)
    # The line's own pace is the goal, which is what the verdict then judges.
    assert line is not None
    assert pace_percent(CONSTANT, 896.2, line) == pytest.approx(95.0)


def test_a_goal_above_one_hundred_puts_the_line_above_the_pb():
    line = pace_threshold_score(CONSTANT, 896.2, 105.0)

    assert line is not None
    assert 896.2 < line < CONSTANT
    assert pace_threshold_score(CONSTANT, 896.2, 100.0) == pytest.approx(896.2)


def test_the_goal_is_met_exactly_at_the_goal():
    assert pace_goal_met(CONSTANT, 905.0, 900.0, 95.0) is True
    assert pace_goal_met(CONSTANT, 905.0, 899.99, 95.0) is False
    assert pace_goal_met(CONSTANT, 905.0, 900.01, 95.0) is True


def test_the_goal_is_met_exactly_where_float_math_falls_short():
    """198.74 s is 95% of 209.2 s, and both float forms of the test say no."""
    previous_best, score, goal = 801.26, 790.8, 95.0
    assert (CONSTANT - previous_best) * 100 < goal * (CONSTANT - score)
    assert (CONSTANT - previous_best) / (CONSTANT - score) * 100 < goal

    assert pace_goal_met(CONSTANT, previous_best, score, goal) is True


@pytest.mark.parametrize(
    ("reference_score", "score"),
    [
        pytest.param(1000.0, 900.0, id="a reference time of zero"),
        pytest.param(1000.5, 900.0, id="a negative reference time"),
        pytest.param(900.0, 1000.0, id="a run time of zero"),
        pytest.param(900.0, 1200.0, id="a negative run time"),
        pytest.param(math.nan, 900.0, id="a reference that is not a number"),
    ],
)
def test_pace_is_undefined_when_a_time_is_zero_or_less(reference_score, score):
    assert pace_percent(CONSTANT, reference_score, score) is None
    assert percent_faster(CONSTANT, reference_score, score) is None
    assert pace_goal_met(CONSTANT, reference_score, score, 95.0) is None


@pytest.mark.parametrize("personal_best", [1000.0, 1000.5])
def test_the_threshold_line_is_undefined_without_a_positive_pb_time(personal_best):
    assert pace_threshold_score(CONSTANT, personal_best, 95.0) is None


@pytest.mark.parametrize("goal_percentage", [0.0, -95.0])
def test_the_threshold_line_is_undefined_without_a_positive_goal(goal_percentage):
    assert pace_threshold_score(CONSTANT, 896.2, goal_percentage) is None


def test_a_score_of_zero_or_less_still_has_a_pace():
    """Only the times have to be positive, and a low score is a long time."""
    assert pace_percent(CONSTANT, -5.0, -20.0) == pytest.approx(98.5294, abs=1e-4)
    assert percent_faster(CONSTANT, 0.0, 10.0) == pytest.approx(1.0101, abs=1e-4)
    assert pace_goal_met(CONSTANT, 0.0, -10.0, 95.0) is True
    assert pace_threshold_score(CONSTANT, 0.0, 95.0) == pytest.approx(
        -52.6316, abs=1e-4
    )


def test_the_constant_is_not_assumed_to_be_one_thousand():
    assert pace_percent(250.0, 205.0, 200.0) == 90.0
    assert pace_threshold_score(250.0, 205.0, 90.0) == 200.0
    assert pace_goal_met(250.0, 205.0, 200.0, 90.0) is True
