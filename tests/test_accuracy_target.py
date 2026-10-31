"""The score at 100% hit accuracy behind a scenario's accuracy targets, and each target.

``full_accuracy_score`` reads a scenario's whole history in play order and
gives the median of its newest version's scores at 100%, or the reason it
has none. ``accuracy_target`` turns a rank's threshold into a percent.
"""

from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from source.kovaaks.accuracy_target import (
    NoFullAccuracyScore,
    accuracy_target,
    full_accuracy_score,
)
from source.kovaaks.data_models import RunData

START = datetime(2026, 10, 30, 12, 0)


def _runs(
    *full_scores: float,
    accuracy: float = 0.5,
    scenario_hash: str | None = "v2",
    start: datetime = START,
) -> list[RunData]:
    """Build one run a minute, each scoring its score at 100% times ``accuracy``."""
    return [
        RunData(
            datetime_object=start + timedelta(minutes=index),
            score=full_score * accuracy,
            sens_scale="cm/360",
            horizontal_sens=40.0,
            scenario="VT Controlsphere Viscose",
            accuracy=accuracy,
            scenario_hash=scenario_hash,
        )
        for index, full_score in enumerate(full_scores)
    ]


def _older_version(count: int) -> list[RunData]:
    return _runs(*[1000.0] * count, scenario_hash="v1", start=START - timedelta(days=1))


# --- The score at 100% ---------------------------------------------------------


def test_runs_that_agree_give_the_median_of_their_scores_at_100_percent() -> None:
    assert full_accuracy_score(
        _runs(6001, 5990, 6010, 6003, 5995), time_scored=False
    ) == pytest.approx(6001)


def test_an_even_count_gives_the_mean_of_the_middle_two() -> None:
    assert full_accuracy_score(
        _runs(990, 995, 1000, 1005, 1010, 1020), time_scored=False
    ) == pytest.approx(1002.5)


def test_a_run_exactly_2_percent_from_the_median_agrees() -> None:
    assert full_accuracy_score(
        _runs(1000, 1000, 1000, 1000, 1020), time_scored=False
    ) == pytest.approx(1000)


def test_a_run_exactly_2_percent_off_agrees_through_hit_and_shot_noise() -> None:
    """One point per hit: 616 hits of 2,040 shots is 2040.0000000000002 at 100%."""
    runs = _runs(2000, 2000, 2000, 2000, 2040)
    runs[-1] = replace(runs[-1], score=616, accuracy=616 / 2040)
    assert full_accuracy_score(runs, time_scored=False) == 2000


def test_a_run_a_hair_more_than_2_percent_off_disagrees() -> None:
    assert (
        full_accuracy_score(_runs(2000, 2000, 2000, 2000, 2040.001), time_scored=False)
        is NoFullAccuracyScore.RUNS_DISAGREE
    )


def test_nine_runs_pass_only_when_all_nine_agree() -> None:
    assert full_accuracy_score(_runs(*[1000] * 9), time_scored=False) == 1000
    assert (
        full_accuracy_score(_runs(*[1000] * 8, 1100), time_scored=False)
        is NoFullAccuracyScore.RUNS_DISAGREE
    )


def test_ten_runs_pass_with_one_outside_and_not_with_two() -> None:
    assert full_accuracy_score(_runs(*[1000] * 9, 1100), time_scored=False) == 1000
    assert (
        full_accuracy_score(_runs(*[1000] * 8, 1100, 900), time_scored=False)
        is NoFullAccuracyScore.RUNS_DISAGREE
    )


def test_twenty_runs_pass_with_two_outside() -> None:
    assert (
        full_accuracy_score(_runs(*[1000] * 18, 1100, 900), time_scored=False) == 1000
    )


def test_five_runs_that_disagree_give_the_disagreement_reason() -> None:
    """Clicks at a varying pace fire more shots on some runs than on others."""
    assert (
        full_accuracy_score(_runs(900, 950, 1000, 1050, 1100), time_scored=False)
        is NoFullAccuracyScore.RUNS_DISAGREE
    )


def test_four_runs_give_the_count_reason() -> None:
    assert (
        full_accuracy_score(_runs(*[1000] * 4), time_scored=False)
        is NoFullAccuracyScore.TOO_FEW_RUNS
    )


def test_no_runs_give_the_count_reason() -> None:
    assert full_accuracy_score([], time_scored=False) is (
        NoFullAccuracyScore.TOO_FEW_RUNS
    )


def test_four_runs_since_an_update_give_the_since_update_reason() -> None:
    runs = [*_older_version(20), *_runs(*[1000] * 4)]

    assert (
        full_accuracy_score(runs, time_scored=False)
        is NoFullAccuracyScore.TOO_FEW_RUNS_SINCE_UPDATE
    )


def test_only_the_newest_versions_runs_count() -> None:
    """An update can change a scenario's length, and so its shots."""
    runs = [*_older_version(20), *_runs(*[1500] * 5)]

    assert full_accuracy_score(runs, time_scored=False) == 1500


def test_runs_of_an_older_version_that_disagree_dont_count_against_the_newest() -> None:
    older = _runs(
        800, 1200, 900, 1100, 1000, scenario_hash="v1", start=START - timedelta(days=1)
    )

    assert full_accuracy_score([*older, *_runs(*[1000] * 5)], time_scored=False) == 1000


def test_files_with_no_hash_count_as_one_version() -> None:
    runs = _runs(*[1000] * 5, scenario_hash=None)

    assert full_accuracy_score(runs, time_scored=False) == 1000


@pytest.mark.parametrize(
    "runs",
    [
        _runs(*[1000] * 5),
        _runs(*[1000] * 4),
        [*_older_version(20), *_runs(*[1000] * 4)],
        _runs(900, 950, 1000, 1050, 1100),
        [],
    ],
    ids=["passing", "four runs", "four since an update", "disagreeing", "no runs"],
)
def test_a_time_scored_version_has_none_ahead_of_every_other_reason(runs) -> None:
    """A steady player's countdown scores can agree without following accuracy."""
    assert (
        full_accuracy_score(runs, time_scored=True) is NoFullAccuracyScore.TIME_SCORED
    )


def test_zero_accuracy_and_zero_score_are_skipped() -> None:
    """Five runs with a figure, and two more that can't give one."""
    zero_accuracy, zero_score = _runs(1000, 1000)
    zero_accuracy = replace(zero_accuracy, accuracy=0.0, score=0.0)
    zero_score = replace(zero_score, score=0.0)
    runs = [
        zero_accuracy,
        zero_score,
        *_runs(*[1000] * 5, start=START + timedelta(hours=1)),
    ]

    assert full_accuracy_score(runs, time_scored=False) == 1000
    assert (
        full_accuracy_score([zero_accuracy, zero_score, *runs[2:6]], time_scored=False)
        is NoFullAccuracyScore.TOO_FEW_RUNS
    )


def test_a_negative_score_is_skipped() -> None:
    """Some scenarios take points off for a miss, so a run can end below zero."""
    (negative,) = _runs(1000)
    negative = replace(negative, score=-50.0)

    assert (
        full_accuracy_score([negative, *_runs(*[1000] * 4)], time_scored=False)
        is NoFullAccuracyScore.TOO_FEW_RUNS
    )


# --- The target ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("threshold", "full_score", "target"),
    [
        # Saffron on VT Controlsphere Viscose: 39.16% reads 39.2%.
        (2350, 6001, 39.2),
        # Jade on VT EddieTS Intermediate S5, reached by a PB at 41.09%.
        (1020, 2482.4, 41.1),
        # Rounded up, never to the nearest: 39.11% reads 39.2% too.
        (3911, 10_000, 39.2),
        (40, 100, 40.0),
        # Float noise at a tenth's edge: 28.8 / 60 * 1000 is a hair over 480.
        (28.8, 60, 48.0),
        (1000, 1000, 100.0),
        (0, 1000, 0.0),
        (-50, 1000, 0.0),
    ],
)
def test_a_target_is_rounded_up_to_the_next_tenth(
    threshold, full_score, target
) -> None:
    assert accuracy_target(threshold, full_score) == target


def test_an_exact_tenth_keeps_its_tenth() -> None:
    assert f"{accuracy_target(400, 1000):.1f}%" == "40.0%"


@pytest.mark.parametrize("threshold", [1000.01, 1005, 2000])
def test_a_target_above_100_percent_is_left_out(threshold) -> None:
    assert accuracy_target(threshold, 1000) is None
