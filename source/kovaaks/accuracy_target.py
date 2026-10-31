"""Estimate the hit accuracy each rank needs, from a scenario's own runs.

A run's score over its hit accuracy is the score it would have made at 100%
with the same shots. Where the fire button is held for the whole run, as on
tracking, that figure is about the same on every run, so a rank's threshold
over it is an estimate of the accuracy the rank needs. Where shots vary from
run to run, as on most click scenarios, the figures disagree and there is no
such estimate. Nothing here is stored: the chart works it out on every build.
"""

import math
import statistics
from collections.abc import Sequence
from enum import Enum

from source.kovaaks.data_models import RunData

# One run can't show that its shots are steady, and short streaks of
# disagreeing runs pass by chance: on the maintainer's stats, 15 of 148
# disagreeing versions passed on their first 3 runs and 5 on their first 5.
MIN_RUNS = 5
# A run agrees when its score at 100% is within this share of the median.
# The tightest held-fire switching scenario measured spread 1.5%.
AGREEMENT = 0.02
# At least this many runs in ten must agree, counted in whole runs: 5 to 9
# runs must all agree, and 10 to 19 may have one outside.
AGREEING_IN_TEN = 9


class NoFullAccuracyScore(Enum):
    """Why a scenario has no score at 100%, in the order the reasons are checked."""

    TIME_SCORED = "time_scored"
    TOO_FEW_RUNS = "too_few_runs"
    TOO_FEW_RUNS_SINCE_UPDATE = "too_few_runs_since_update"
    RUNS_DISAGREE = "runs_disagree"


def full_accuracy_score(
    runs: Sequence[RunData],
    *,
    time_scored: bool,
) -> float | NoFullAccuracyScore:
    """Return the score a scenario's runs would make at 100% hit accuracy, or why not.

    ``runs`` is the scenario's whole history in play order. Its newest run
    names the version, and only that version's runs with a hit accuracy and
    a score above zero count; files with no ``Hash:`` line are one version.
    ``time_scored`` is whether the app recognizes that version as
    time-scored, which rules it out whatever its runs: a countdown's score
    can agree across runs of a steady player without following accuracy.

    Passing, the answer is the median of the runs' scores at 100%. It is an
    estimate for a run with the median run's shots, not a guarantee.
    """
    if time_scored:
        return NoFullAccuracyScore.TIME_SCORED
    if not runs:
        return NoFullAccuracyScore.TOO_FEW_RUNS
    version = runs[-1].scenario_hash
    current = [run for run in runs if run.scenario_hash == version]
    figures = [
        run.score / run.accuracy
        for run in current
        if run.accuracy > 0 and run.score > 0
    ]
    if len(figures) < MIN_RUNS:
        if len(current) < len(runs):
            return NoFullAccuracyScore.TOO_FEW_RUNS_SINCE_UPDATE
        return NoFullAccuracyScore.TOO_FEW_RUNS
    median = statistics.median(figures)
    # A difference against a share of the median, not a ratio against 1: a
    # run exactly 2% off would land a hair over in float and fail.
    agreeing = sum(abs(figure - median) <= AGREEMENT * median for figure in figures)
    if 10 * agreeing < AGREEING_IN_TEN * len(figures):
        return NoFullAccuracyScore.RUNS_DISAGREE
    return median


def accuracy_target(threshold: float, full_score: float) -> float | None:
    """Return a rank's accuracy target in percent, or ``None`` above 100%.

    ``full_score`` is the scenario's score at 100%. The target is rounded up
    to the next tenth, so a run with the median run's shots that reaches it
    reaches the rank. A threshold at or below zero needs no accuracy, so it
    reads 0.0 rather than a figure below zero that means nothing.
    """
    # The inner round strips float noise that would push an exact tenth up
    # one: 28.8 / 60 is 48%, but 28.8 / 60 * 1000 is 480.00000000000006,
    # which would read 48.1.
    tenths = math.ceil(round(threshold / full_score * 1000, 6))
    if tenths > 1000:
        return None
    return max(tenths, 0) / 10
