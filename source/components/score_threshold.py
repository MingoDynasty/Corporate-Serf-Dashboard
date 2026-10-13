"""Judge a run against the score threshold and place the threshold line."""

from decimal import Decimal
from enum import Enum
from typing import NamedTuple

from source.app_shell import RunEventData
from source.kovaaks.data_service import get_personal_best_run
from source.kovaaks.pace import pace_goal_met, pace_percent, pace_threshold_score
from source.kovaaks.time_scored_service import eligible_pace_constant, get_pace_basis


def normalize_score_threshold_percentage(
    score_threshold_percentage: float | str | None,
) -> float | None:
    """Return a usable threshold percentage, or None while the input is empty."""
    if not score_threshold_percentage:
        return None

    try:
        return float(score_threshold_percentage)
    except TypeError:
        return None
    except ValueError:
        return None


class ThresholdVerdict(NamedTuple):
    """How a run measured up against the score threshold it was judged on.

    ``by_pace`` says which measure ``percentage`` is in: the run's pace as a
    percentage of the previous best's, or its score as a percentage of it.
    """

    passed: bool
    percentage: float
    goal_percentage: float
    by_pace: bool = False


class Unjudged(Enum):
    """Why nothing judges a run against the score threshold.

    A run can fit more than one, and takes the first in this order.
    """

    NO_PERCENTAGE_SET = "no_percentage_set"
    FIRST_RUN = "first_run"
    NO_PERCENTAGE_TO_JUDGE_BY = "no_percentage_to_judge_by"


def judge_run(
    score: float,
    previous_best: float | None,
    is_new_sensitivity: bool,
    pace_constant: float | None,
    goal_percentage: float | None,
) -> ThresholdVerdict | Unjudged:
    """Judge one run against the score threshold, or say why nothing judges it.

    ``previous_best`` is the PB the run was chasing: the scenario's best score
    before it, at any sensitivity, and ``None`` for the scenario's first run.
    ``is_new_sensitivity`` says the run is the first at its sensitivity, and
    ``pace_constant`` is the scenario's constant when the run and that PB can
    be compared by pace. ``goal_percentage`` is ``None`` while the percentage
    is empty.

    A run goes unjudged when the goal percentage is empty, when it is the
    first at its sensitivity, or when it is compared by score with a previous
    best of zero or less: there is no denominator, not a failing one. A run
    with a pace constant is judged by pace wherever pace is defined, which
    needs positive times and not a positive previous best. Where it is
    undefined, the run is judged by score as any other.

    The run toast and the run list's check both judge through this, so a run
    that just landed and the same run read back from the run store cannot get
    two answers from the same facts.
    """
    if not goal_percentage:
        return Unjudged.NO_PERCENTAGE_SET
    if is_new_sensitivity or previous_best is None:
        return Unjudged.FIRST_RUN
    if pace_constant is not None:
        passed_by_pace = pace_goal_met(
            pace_constant,
            previous_best,
            score,
            goal_percentage,
        )
        percentage_of_pace = pace_percent(pace_constant, previous_best, score)
        if passed_by_pace is not None and percentage_of_pace is not None:
            return ThresholdVerdict(
                passed=passed_by_pace,
                percentage=percentage_of_pace,
                goal_percentage=goal_percentage,
                by_pace=True,
            )
    if previous_best <= 0:
        return Unjudged.NO_PERCENTAGE_TO_JUDGE_BY
    # Compared as decimals: in floats, 20.6 * 95 / 100 is 19.570000000000004,
    # which fails a 19.57 run sitting exactly at 95% of a 20.60 PB. A float's
    # str() is the decimal the stats CSV wrote.
    passed = Decimal(str(score)) * 100 >= Decimal(str(previous_best)) * Decimal(
        str(goal_percentage)
    )
    return ThresholdVerdict(
        passed=passed,
        percentage=score / previous_best * 100,
        goal_percentage=goal_percentage,
    )


def threshold_verdict(
    latest: RunEventData,
    score_threshold_percentage: float | str | None,
    score_threshold_notification_switch: bool,
) -> ThresholdVerdict | None:
    """Judge a run that just landed, or return None when nothing judges it.

    A run goes unjudged when the switch is off, and for each reason
    ``judge_run`` gives. The message carries the facts and this derives the
    gate; the two used to be bundled into one nullable field that meant both.
    """
    if not score_threshold_notification_switch:
        return None
    judged = judge_run(
        latest["score"],
        latest["scenario_previous_best"],
        latest["is_new_sensitivity"],
        latest["pace_constant"],
        normalize_score_threshold_percentage(score_threshold_percentage),
    )
    return judged if isinstance(judged, ThresholdVerdict) else None


def shown_percentage(verdict: ThresholdVerdict) -> float:
    """Return the percentage of PB to print, held below each line the run missed.

    Rounding alone prints a 94.98% miss of a 95% goal as "95.0% of PB (need
    95.0%)" and a run 0.03% short of the PB as "100.0% of PB". So a miss shows
    at most one tenth below the goal as printed, and a run below the PB shows
    at most 99.9% whether it passed or not. Flooring would not do: float error
    prints 407 / 500 as 81.3%.
    """
    shown = verdict.percentage
    if not verdict.passed:
        shown = min(shown, round(verdict.goal_percentage, 1) - 0.1)
    # Float division and multiplication both round monotonically, so the
    # percentage is below 100 exactly when the score is below the PB. That
    # holds for a percentage of pace too: a run's time is longer than the
    # PB's exactly when its score is lower.
    if verdict.percentage < 100:
        shown = min(shown, 99.9)
    return shown


def score_threshold_line(
    selected_scenario: str,
    high_score: float,
    goal_percentage: float,
) -> float:
    """Return the score the threshold line is drawn at, from the current PB.

    On a time-scored scenario whose PB can be measured by pace, the line sits
    at the score that finishes at the goal percentage of the PB's pace. Every
    other scenario keeps the goal as a percentage of the PB's score.
    """
    pace_constant = eligible_pace_constant(
        get_pace_basis(selected_scenario),
        get_personal_best_run(selected_scenario),
    )
    if pace_constant is not None:
        pace_line = pace_threshold_score(pace_constant, high_score, goal_percentage)
        if pace_line is not None:
            return pace_line
    return high_score * goal_percentage / 100
