"""Measure a time-scored scenario's runs by pace instead of by score.

A time-scored scenario scores the time left on a clock that counts down from a
constant, so a score of ``s`` took ``constant - s`` seconds. A percentage of
such a score understates a real improvement many times over, because the score
starts at the constant and not at zero. Pace is how fast one run finishes set
against another: the other run's time divided by this one's.

Every function here returns ``None`` when pace is undefined, which is when a
time in the comparison is zero or less. The caller then keeps its score math,
with that math's own rules for a score it cannot take a percentage of.
"""

from decimal import Decimal


def _has_positive_times(constant: float, *scores: float) -> bool:
    """Tell whether every score is below the constant, so its time is positive."""
    return all(score < constant for score in scores)


def pace_percent(
    constant: float,
    reference_score: float,
    score: float,
) -> float | None:
    """Return a score's pace as a percentage of the reference score's pace."""
    if not _has_positive_times(constant, reference_score, score):
        return None
    return (constant - reference_score) / (constant - score) * 100


def percent_faster(
    constant: float,
    reference_score: float,
    score: float,
) -> float | None:
    """Return how much faster, in percent, a score finishes than the reference.

    It is the Next Rank gap when the score is the next rank's threshold and
    the reference is the PB, and the gain a new personal best reports when the
    reference is the previous best.
    """
    if not _has_positive_times(constant, reference_score, score):
        return None
    return ((constant - reference_score) / (constant - score) - 1) * 100


def pace_threshold_score(
    constant: float,
    personal_best: float,
    goal_percentage: float,
) -> float | None:
    """Return the score that finishes at the goal percentage of the PB's pace."""
    if not _has_positive_times(constant, personal_best) or goal_percentage <= 0:
        return None
    return constant - (constant - personal_best) * 100 / goal_percentage


def pace_goal_met(
    constant: float,
    previous_best: float,
    score: float,
    goal_percentage: float,
) -> bool | None:
    """Tell whether a score reaches the goal percentage of the previous best's pace.

    Compared as decimals, in the cross-multiplied form, so a run exactly at
    the goal passes: in floats, a division on either side can land a hair
    under a goal the run met. A float's ``str()`` is the decimal the stats
    file wrote.
    """
    if not _has_positive_times(constant, previous_best, score):
        return None
    decimal_constant = Decimal(str(constant))
    previous_time = decimal_constant - Decimal(str(previous_best))
    run_time = decimal_constant - Decimal(str(score))
    return previous_time * 100 >= Decimal(str(goal_percentage)) * run_time
