"""Mark a scenario's past runs: which passed the score threshold, which were new PBs.

The run toast judges a run when it lands, from three facts the watchdog works
out at that moment: the PB the run was chasing, whether the run was the first
at its sensitivity, and the constant the two can be compared by pace with. A
past run has no message to carry them, so they are worked out here from the
run store, and the run is then judged by the function the toast judges with.

Nothing here is stored. A mark is worked out again each time something asks,
from the runs, the percentage, and what the performance files say now.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import NamedTuple

from source.components.score_threshold import (
    ThresholdVerdict,
    Unjudged,
    judge_run,
)
from source.kovaaks.data_models import RunData
from source.kovaaks.data_service import new_high_score_runs
from source.kovaaks.time_scored_service import PaceBasis, eligible_pace_constant


class Chased(NamedTuple):
    """What one run was up against when it was played.

    ``previous_best`` is the PB the run was chasing: the scenario's best score
    before it, at any sensitivity, and ``None`` for the scenario's first run.
    ``pace_constant`` is the constant of the run's own version of the
    scenario when that PB was set on the same version, and ``None`` wherever
    the two are compared by score.
    """

    previous_best: float | None
    is_new_sensitivity: bool
    pace_constant: float | None


@dataclass(frozen=True)
class RunMark:
    """What is drawn beside one run's score.

    ``verdict`` is how the run measured up against the score threshold, or
    the reason nothing judges it. ``is_new_pb`` never depends on the
    threshold: the first run at a new sensitivity is not judged and can still
    be a new PB.
    """

    verdict: ThresholdVerdict | Unjudged
    is_new_pb: bool

    @property
    def passed(self) -> bool:
        """Whether the run was judged and met the score threshold."""
        return isinstance(self.verdict, ThresholdVerdict) and self.verdict.passed


def what_runs_chased(
    runs: Sequence[RunData],
    version_pace_basis: Callable[[str | None], PaceBasis | None],
) -> dict[RunData, Chased]:
    """Work out what each run of one scenario was up against.

    ``runs`` is the scenario's whole history, at every sensitivity, in the
    order the runs were played. ``version_pace_basis`` answers for one
    version of the scenario, named by a stats file's ``Hash:``, and is asked
    once per version.

    A run is measured under its own version, never under the version the
    scenario's newest run names. Under the newest run's, a later run on
    another version would stop an old run counting as a pace comparison, so a
    run that missed by pace would be judged by score and pass, with no change
    to the run, to the PB it was chasing, or to the percentage.

    On a tied score the earliest run holds the PB, as it does for the run
    toast, so that run's version is the one a later run is compared under.
    """
    chased: dict[RunData, Chased] = {}
    bases: dict[str | None, PaceBasis | None] = {}
    sensitivities_played: set[tuple[float, str]] = set()
    best_run: RunData | None = None
    for run in runs:
        version = run.scenario_hash
        if version not in bases:
            bases[version] = version_pace_basis(version)
        sensitivity = (run.horizontal_sens, run.sens_scale)
        chased[run] = Chased(
            previous_best=None if best_run is None else best_run.score,
            is_new_sensitivity=sensitivity not in sensitivities_played,
            pace_constant=eligible_pace_constant(bases[version], run, best_run),
        )
        sensitivities_played.add(sensitivity)
        if best_run is None or run.score > best_run.score:
            best_run = run
    return chased


def mark_runs(
    runs: Sequence[RunData],
    goal_percentage: float | None,
    version_pace_basis: Callable[[str | None], PaceBasis | None],
) -> dict[RunData, RunMark]:
    """Mark every run of one scenario.

    ``runs`` and ``version_pace_basis`` are as ``what_runs_chased`` takes
    them, and ``goal_percentage`` is ``None`` while the percentage is empty.
    Each run is judged against the PB it was chasing, so a later PB removes
    no check. The percentage in force when a run was played was never
    recorded, so every run is judged by the one handed in.
    """
    # The chart's own function over the chart's own order, so a star in the
    # list is on the same run as the star on the chart, a same-second pair
    # included.
    new_pbs = new_high_score_runs(runs)
    return {
        run: RunMark(
            verdict=judge_run(
                run.score,
                chased.previous_best,
                chased.is_new_sensitivity,
                chased.pace_constant,
                goal_percentage,
            ),
            is_new_pb=run in new_pbs,
        )
        for run, chased in what_runs_chased(runs, version_pace_basis).items()
    }
