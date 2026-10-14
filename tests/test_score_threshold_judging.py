"""How a run is judged against the score threshold, and the percentage it shows.

``judge_run`` and ``shown_percentage`` are the one place a run is judged. The
run list's check and the latest-run card both go through them, so the rule is
held here on the two functions themselves: the comparison at the goal's edge,
by score and by pace, the two display caps, and the runs nothing judges.
"""

import pytest

from source.components.score_threshold import (
    ThresholdVerdict,
    Unjudged,
    judge_run,
    normalize_score_threshold_percentage,
    shown_percentage,
)

PACE_CONSTANT = 1000.0


def _judged(
    score: float,
    previous_best: float,
    goal: float,
    pace_constant: float | None = None,
) -> ThresholdVerdict:
    """Judge a run that is not the first at its sensitivity."""
    verdict = judge_run(score, previous_best, False, pace_constant, goal)
    assert isinstance(verdict, ThresholdVerdict), verdict
    return verdict


@pytest.mark.parametrize(
    ("score", "previous_best", "goal", "passed", "shown"),
    [
        pytest.param(830.0, 800.0, 102.5, True, "103.8", id="above_the_goal"),
        pytest.param(820.0, 800.0, 102.5, True, "102.5", id="exactly_at_the_goal"),
        # 19.57 is exactly 95% of 20.60, but in floats 20.6 * 95 / 100 is
        # 19.570000000000004, which would fail the run and cap it to 94.9%.
        pytest.param(
            19.57, 20.60, 95, True, "95.0", id="exactly_at_a_goal_floats_overshoot"
        ),
        # 99.97% of the PB: a pass at 95%, which rounding alone prints as 100.0%.
        pytest.param(11523.0, 11526.0, 95, True, "99.9", id="a_pass_short_of_the_pb"),
        # The cap is for a run below the PB only: a tie is all of it.
        pytest.param(11526.0, 11526.0, 95, True, "100.0", id="a_tie_with_the_pb"),
        pytest.param(780.0, 800.0, 98.75, False, "97.5", id="below_the_goal"),
        # 94.98% of the PB: short of 95%, which rounding alone prints as 95.0%.
        pytest.param(
            10848.0, 11421.0, 95, False, "94.9", id="a_miss_that_rounds_to_the_goal"
        ),
        # A 98.74% goal prints as 98.7%, so a 98.73% run must print lower still.
        pytest.param(
            9873.0, 10000.0, 98.74, False, "98.6", id="a_goal_that_prints_rounded_down"
        ),
        # A goal above 100: the run beat the old PB and still missed the bar.
        pytest.param(
            820.0, 800.0, 105.0, False, "102.5", id="a_new_pb_short_of_a_stretch_goal"
        ),
        # A goal above 100 puts the miss's cap above the PB too, so the other
        # cap is what keeps a run 0.03% short of the PB from reading 100.0%.
        pytest.param(
            11523.0,
            11526.0,
            105.0,
            False,
            "99.9",
            id="a_stretch_goal_miss_short_of_the_pb",
        ),
    ],
)
def test_a_run_judged_by_score_passes_or_misses_and_shows_this_percentage(
    score, previous_best, goal, passed, shown
):
    verdict = _judged(score, previous_best, goal)

    assert verdict.passed is passed
    assert verdict.by_pace is False
    assert verdict.goal_percentage == goal
    assert f"{shown_percentage(verdict):.1f}" == shown


@pytest.mark.parametrize(
    ("score", "previous_best", "passed", "shown"),
    [
        # 905 took 95 s and 902 took 98 s: 96.9% of the pace, where the score's
        # own ratio reads 99.7%.
        pytest.param(902.0, 905.0, True, "96.9", id="above_the_goal"),
        # 883.02 against 896.17 passes at 98.5% of the score, and is 88.8% of
        # the pace.
        pytest.param(883.02, 896.17, False, "88.8", id="below_the_goal"),
        # 95 s against 100 s is exactly 95% of the pace.
        pytest.param(900.0, 905.0, True, "95.0", id="exactly_at_the_goal"),
        # 198.74 s against 209.2 s is exactly 95%, and in floats both the ratio
        # and the cross-multiplied form come out a hair under it.
        pytest.param(
            790.8, 801.26, True, "95.0", id="exactly_at_a_goal_floats_undershoot"
        ),
        # 103.83 s against 103.86 s is 99.97% of the pace.
        pytest.param(896.14, 896.17, True, "99.9", id="a_pass_short_of_the_pb"),
        # 95 s against 100.02 s is 94.98% of the pace.
        pytest.param(899.98, 905.0, False, "94.9", id="a_miss_that_rounds_to_the_goal"),
        # Pace needs positive times, not a positive previous best: 1,005 s
        # against 1,020 s is 98.5% of the pace.
        pytest.param(-20.0, -5.0, True, "98.5", id="a_previous_best_of_zero_or_less"),
    ],
)
def test_a_run_judged_by_pace_passes_or_misses_and_shows_this_percentage(
    score, previous_best, passed, shown
):
    verdict = _judged(score, previous_best, 95, PACE_CONSTANT)

    assert verdict.passed is passed
    assert verdict.by_pace is True
    assert f"{shown_percentage(verdict):.1f}" == shown


def test_a_run_with_no_constant_is_judged_by_score():
    # The same two scores as the pass by pace, which read 96.9% there.
    verdict = _judged(902.0, 905.0, 95)

    assert verdict.by_pace is False
    assert f"{shown_percentage(verdict):.1f}" == "99.7"


def test_an_undefined_pace_falls_back_to_the_score():
    # A score at the constant took no time at all, so pace is undefined and the
    # run is judged as any other scenario's would be.
    verdict = _judged(1000.0, 905.0, 95, PACE_CONSTANT)

    assert verdict.passed is True
    assert verdict.by_pace is False
    assert f"{shown_percentage(verdict):.1f}" == "110.5"


@pytest.mark.parametrize("pace_constant", [None, PACE_CONSTANT])
def test_a_run_compared_by_score_with_a_previous_best_of_zero_or_less_is_not_judged(
    pace_constant,
):
    # With the constant, the score sits at it, so pace is undefined and the
    # score rule decides.
    assert (
        judge_run(1000.0, 0.0, False, pace_constant, 95)
        is Unjudged.NO_PERCENTAGE_TO_JUDGE_BY
    )
    assert judge_run(-20.0, -5.0, False, None, 95) is Unjudged.NO_PERCENTAGE_TO_JUDGE_BY


@pytest.mark.parametrize("pace_constant", [None, PACE_CONSTANT])
def test_the_first_run_at_a_sensitivity_is_not_judged_by_score_or_by_pace(
    pace_constant,
):
    assert judge_run(902.0, 905.0, True, pace_constant, 95) is Unjudged.FIRST_RUN
    assert judge_run(902.0, None, True, pace_constant, 95) is Unjudged.FIRST_RUN


@pytest.mark.parametrize("empty_percentage", [None, "", 0])
def test_an_empty_percentage_judges_no_run(empty_percentage):
    """A cleared field sends an empty string, and one never set sends nothing."""
    goal = normalize_score_threshold_percentage(empty_percentage)

    assert goal is None
    assert judge_run(780.0, 800.0, False, None, goal) is Unjudged.NO_PERCENTAGE_SET


@pytest.mark.parametrize(
    ("typed", "goal"), [(95, 95.0), ("98.75", 98.75), (102.5, 102.5)]
)
def test_a_typed_percentage_is_the_goal(typed, goal):
    assert normalize_score_threshold_percentage(typed) == goal
