"""What the Run History page's latest-run card shows.

``latest_run`` is one pure function over run records, so these tests build
records and read the text the card shows. How the page calls it, and when,
is ``tests/test_run_history_page.py``.
"""

import re
from dataclasses import replace
from datetime import datetime, timedelta

import dash
import pytest
from dash import dcc, html

dash.Dash(__name__, use_pages=True, pages_folder="")

from source import app_shell  # noqa: E402
from source.components import latest_run_card, pb_card  # noqa: E402
from source.components.latest_run_card import (  # noqa: E402
    CardBadge,
    LatestRun,
    LatestRunCardIds,
    TypicalPhrase,
    latest_run,
    latest_run_card_content,
    latest_run_from_store,
)
from source.components.run_history_list import (  # noqa: E402
    SESSION_ROW,
    build_run_list,
    run_id,
)
from source.components.run_marks import mark_runs, what_runs_chased  # noqa: E402
from source.components.score_threshold import (  # noqa: E402
    ThresholdVerdict,
    judge_run,
    shown_percentage,
)
from source.kovaaks.data_models import RunData  # noqa: E402
from source.kovaaks.play_sessions import in_play_order  # noqa: E402
from source.kovaaks.time_scored_service import PaceBasis  # noqa: E402
from source.pages import playlist_scenarios  # noqa: E402
from tests.rendered_text import rendered_text  # noqa: E402

A, B = "Scenario A", "Scenario B"
EVENING = datetime(2026, 10, 4, 21, 45, 0)
VERSION = "0123456789abcdef0123456789abcdef"
IDS = LatestRunCardIds(*LatestRunCardIds._fields)


def _run(  # noqa: PLR0913
    scenario: str,
    ended: datetime,
    *,
    score: float = 100.0,
    length: timedelta | None = timedelta(seconds=60),
    accuracy: float = 0.5,
    sensitivity: float = 40.8,
    scenario_hash: str | None = None,
) -> RunData:
    """Build one run that ended at ``ended`` and took ``length`` to play."""
    return RunData(
        datetime_object=ended,
        score=score,
        sens_scale="cm/360",
        horizontal_sens=sensitivity,
        scenario=scenario,
        accuracy=accuracy,
        scenario_hash=scenario_hash,
        stats_file_name=(
            f"{scenario} - Challenge - {ended:%Y.%m.%d-%H.%M.%S} Stats.csv"
        ),
        run_start=None if length is None else ended - length,
        run_length=length,
    )


def _scored(*scores: float, scenario: str = A, **fields) -> list[RunData]:
    """Build one run per score, a minute apart, the last one ending last."""
    return [
        _run(scenario, EVENING + timedelta(minutes=order), score=score, **fields)
        for order, score in enumerate(scores)
    ]


def _no_pace(_scenario: str, _version: str | None) -> PaceBasis | None:
    return None


def _pace_of(constant: float):
    """Answer that every scenario's ``VERSION`` counts down from ``constant``."""

    def basis(_scenario: str, version: str | None) -> PaceBasis | None:
        if version != VERSION:
            return None
        return PaceBasis(constant=constant, scenario_hash=VERSION)

    return basis


def _shown(
    runs: list[RunData],
    *,
    scenario: str = A,
    percentage: float | None = 95.0,
    now: datetime | None = None,
    pace=_no_pace,
) -> LatestRun:
    """Work the card out as the page does, for a store that holds ``runs``."""
    if now is None:
        now = max(run.datetime_object for run in runs)
    shown = latest_run(runs, scenario, percentage, now, pace)
    assert shown is not None
    return shown


def _marks(runs: list[RunData], scenario: str):
    return mark_runs(
        in_play_order(run for run in runs if run.scenario == scenario),
        95.0,
        lambda _version: None,
    )


# --- Which run it is, and its first line ---------------------------------------


@pytest.mark.parametrize("selected", [A, None, ""])
def test_a_store_with_no_runs_has_no_latest_run(selected):
    assert latest_run([], selected, 95.0, EVENING, _no_pace) is None


def test_the_card_reports_the_selected_scenarios_latest_run():
    """Not the last run played on any scenario: the two big scores are one scenario's."""
    runs = [
        _run(A, EVENING, score=80.0),
        _run(B, EVENING + timedelta(minutes=5), score=612.5),
        _run(A, EVENING - timedelta(days=2), score=90.0),
    ]

    shown_a = _shown(runs, scenario=A)
    shown_b = _shown(runs, scenario=B)

    assert shown_a.score == "80"
    assert shown_a.run_id == run_id(runs[0])
    assert shown_b.score == "612.5"
    assert shown_b.run_id == run_id(runs[1])


@pytest.mark.parametrize("selected", [None, ""])
def test_with_no_scenario_selected_there_is_no_run_to_report(selected):
    """Not the last run on any scenario: the card says nothing is selected."""
    assert latest_run(_scored(100.0, 96.0), selected, 95.0, EVENING, _no_pace) is None


def test_a_scenario_never_played_has_no_run_to_report():
    assert latest_run(_scored(100.0, 96.0), B, 95.0, EVENING, _no_pace) is None


def test_the_cards_run_is_the_one_the_run_list_names_as_the_newest():
    """So during play the row the list highlights is the run the card reports."""
    runs = [
        _run(A, EVENING),
        # Two runs that ended in the same second: the order the sessions are
        # split in settles which of them is the newest.
        _run(B, EVENING + timedelta(minutes=3), length=timedelta(seconds=90)),
        _run(A, EVENING + timedelta(minutes=3), length=timedelta(seconds=30)),
    ]
    now = EVENING + timedelta(minutes=4)

    model = build_run_list(runs, A, 30, now, _marks(runs, A))
    assert _shown(runs, scenario=A, now=now).run_id == model["newest_run"]
    # B's run is its own latest, and both views highlight it when B is selected.
    assert _shown(runs, scenario=B, now=now).run_id == run_id(runs[1])
    assert run_id(runs[1]) != model["newest_run"]


@pytest.mark.parametrize(
    ("landed", "becomes_the_cards_run"),
    [
        # Newer than the scenario's latest and older than the store's newest,
        # as a run copied into the stats folder late is.
        (EVENING + timedelta(minutes=20), True),
        # Older than the scenario's latest.
        (EVENING - timedelta(minutes=20), False),
    ],
)
def test_a_late_run_reaches_the_card_by_the_selected_scenarios_latest(
    landed, becomes_the_cards_run
):
    """Not by the store's newest, which is another scenario's run."""
    held = [
        _run(A, EVENING, score=100.0),
        _run(B, EVENING + timedelta(minutes=40)),
    ]
    late = _run(A, landed, score=77.0)
    now = EVENING + timedelta(minutes=41)

    shown = _shown([*held, late], scenario=A, now=now)

    assert shown.run_id == run_id(late if becomes_the_cards_run else held[0])


@pytest.mark.parametrize(
    ("ended", "now"),
    [
        (datetime(2026, 10, 4, 22, 50), datetime(2026, 10, 4, 22, 50, 30)),
        (datetime(2026, 10, 4, 22, 50), datetime(2026, 10, 5, 0, 1)),
        (datetime(2025, 12, 30, 22, 50), datetime(2026, 1, 2, 9, 0)),
    ],
)
def test_the_card_holds_when_the_run_ended_whatever_the_clock_reads(ended, now):
    """The browser words the age, so the clock decides nothing about the time.

    The card hands the browser the moment itself, in epoch seconds, as Last
    played's store does.
    """
    shown = _shown([_run(A, ended)], now=now)

    assert shown.played_at == ended
    assert latest_run_card_content(shown, A, True).played_at == ended.timestamp()


def test_the_score_is_formatted_as_the_playlist_scenario_table_formats_pb_score():
    assert _shown(_scored(3324.0)).score == "3,324"
    assert _shown(_scored(896.2)).score == "896.2"
    assert _shown(_scored(1234.567)).score == "1,234.57"


# --- The badge -----------------------------------------------------------------


def test_a_judged_run_that_passed_reads_threshold_passed():
    assert _shown(_scored(100.0, 96.0)).badge is CardBadge.THRESHOLD_PASSED


def test_a_judged_run_that_missed_reads_below_threshold():
    assert _shown(_scored(100.0, 90.0)).badge is CardBadge.BELOW_THRESHOLD


def test_a_new_pb_reads_new_pb_whether_or_not_it_was_judged():
    judged = _scored(100.0, 120.0)
    first_at_its_sensitivity = [
        *_scored(100.0),
        _run(A, EVENING + timedelta(minutes=1), score=120.0, sensitivity=30.0),
    ]

    assert _shown(judged).badge is CardBadge.NEW_PB
    assert _shown(judged, percentage=None).badge is CardBadge.NEW_PB
    assert _shown(first_at_its_sensitivity).badge is CardBadge.NEW_PB
    # Above 100 percent a new PB can miss its goal, and is still a new PB.
    assert _shown(judged, percentage=130.0).badge is CardBadge.NEW_PB


@pytest.mark.parametrize(
    ("runs", "percentage"),
    [
        # No percentage is set.
        (_scored(100.0, 96.0), None),
        # A scenario's first run.
        (_scored(100.0), 95.0),
        # The first run at a new sensitivity.
        (
            [
                *_scored(100.0),
                _run(A, EVENING + timedelta(minutes=1), score=96.0, sensitivity=30.0),
            ],
            95.0,
        ),
        # Compared by score with a previous best of zero or less.
        (_scored(0.0, 0.0), 95.0),
        (_scored(-5.0, -8.0), 95.0),
    ],
)
def test_a_run_nothing_judges_that_is_not_a_new_pb_has_no_badge(runs, percentage):
    assert _shown(runs, percentage=percentage).badge is None


@pytest.mark.parametrize("percentage", [90.0, 95.0, 99.0, 110.0, None])
def test_the_badge_agrees_with_the_run_lists_mark_for_the_same_run(percentage):
    """The maintainer's example, each run in turn as the last one played."""
    scores = [100.0, 85.0, 95.0, 120.0, 100.0, 110.0]
    for played in range(1, len(scores) + 1):
        runs = _scored(*scores[:played])
        mark = mark_runs(runs, percentage, lambda _version: None)[runs[-1]]

        badge = _shown(runs, percentage=percentage).badge

        assert (badge is CardBadge.NEW_PB) == mark.is_new_pb
        if not mark.is_new_pb:
            assert (badge is CardBadge.THRESHOLD_PASSED) == mark.passed


# --- The comparison line -------------------------------------------------------


def test_a_run_shows_its_percentage_of_the_pb_it_was_chasing_and_no_accuracy():
    """The run's accuracy is on the card's last line, as the PB's is on the PB card."""
    runs = _scored(100.0, 120.0, 96.0, accuracy=0.57)

    # Against 120, the PB before it, and not against the first run's 100.
    assert _shown(runs).pb_comparison == "80.0% of PB"
    assert _shown(runs).sensitivity_and_accuracy == "40.8 cm/360 · Accuracy 57.00%"


def test_the_percentage_shows_whether_or_not_the_run_was_judged():
    """It is a fact about the run, and an empty threshold does not hide it."""
    runs = _scored(100.0, 96.0)
    first_at_its_sensitivity = [
        *_scored(100.0),
        _run(A, EVENING + timedelta(minutes=1), score=96.0, sensitivity=30.0),
    ]

    assert _shown(runs).pb_comparison == "96.0% of PB"
    assert _shown(runs, percentage=None).pb_comparison == "96.0% of PB"
    assert _shown(first_at_its_sensitivity).pb_comparison == "96.0% of PB"


def test_a_time_scored_run_shows_its_percentage_of_the_pbs_pace():
    # A clock that counts down from 100: 50 took 50 seconds and 40 took 60.
    runs = _scored(50.0, 40.0, scenario_hash=VERSION)

    assert _shown(runs, pace=_pace_of(100.0)).pb_comparison == "83.3% of PB pace"
    assert (
        _shown(runs, percentage=None, pace=_pace_of(100.0)).pb_comparison
        == "83.3% of PB pace"
    )


def test_a_time_scored_pb_of_zero_or_less_still_has_a_percentage_of_pace():
    """Pace needs positive times, and not a positive previous best."""
    runs = _scored(-10.0, -20.0, scenario_hash=VERSION)

    assert _shown(runs, pace=_pace_of(100.0)).pb_comparison == "91.7% of PB pace"


def test_a_new_pb_says_how_far_it_beat_the_previous_best():
    runs = _scored(3000.0, 3324.0)

    assert _shown(runs).pb_comparison == "Up 10.8% on your previous best of 3,000"
    # Judged or not, it reads the same.
    assert _shown(runs, percentage=None).pb_comparison == _shown(runs).pb_comparison


def test_a_new_pb_by_pace_says_how_much_faster_it_finished():
    # 40 took 60 seconds and 50 took 50: a fifth faster.
    runs = _scored(40.0, 50.0, scenario_hash=VERSION)

    assert (
        _shown(runs, pace=_pace_of(100.0)).pb_comparison
        == "20.0% faster than your previous best of 40"
    )


@pytest.mark.parametrize(("previous", "worded"), [(0.0, "0"), (-5.5, "-5.5")])
def test_a_new_pb_over_a_previous_best_of_zero_or_less_names_it(previous, worded):
    runs = _scored(previous, 12.0)

    assert _shown(runs).pb_comparison == f"Your previous best was {worded}"


@pytest.mark.parametrize(
    "runs",
    [
        # A scenario's first run has nothing to compare with.
        _scored(100.0),
        # Not a new PB, and compared by score with a previous best of zero
        # or less.
        _scored(0.0, 0.0),
        _scored(-5.0, -8.0),
    ],
)
def test_a_run_with_no_percentage_has_no_comparison_line(runs):
    assert _shown(runs).pb_comparison is None
    assert _shown(runs, percentage=None).pb_comparison is None


# --- The last line -------------------------------------------------------------


@pytest.mark.parametrize(
    ("accuracy", "worded"),
    [(107 / 130, "82.31%"), (1 / 32, "3.13%"), (1.0, "100.00%"), (0.0, "0.00%")],
)
def test_accuracy_is_shown_to_two_decimals_a_half_rounding_up(accuracy, worded):
    shown = _shown(_scored(100.0, accuracy=accuracy))

    assert shown.sensitivity_and_accuracy == f"40.8 cm/360 · Accuracy {worded}"


@pytest.mark.parametrize(
    ("sensitivity", "worded"), [(50.0, "50"), (34.64, "34.64"), (1234.5, "1,234.5")]
)
def test_the_runs_cm360_is_formatted_as_the_pb_cards(sensitivity, worded):
    """One function words both cards' last lines, so they read alike."""
    run = _run(A, EVENING, sensitivity=sensitivity)

    assert _shown([run]).sensitivity_and_accuracy == (
        f"{worded} cm/360 · Accuracy 50.00%"
    )
    assert pb_card.personal_best([run], None, None, lambda _version: None).faded == (
        _shown([run]).sensitivity_and_accuracy
    )


def test_a_run_whose_cm360_is_unknown_shows_its_accuracy_alone():
    run = replace(_run(A, EVENING), sens_scale="Valorant", horizontal_sens=0.35)

    assert _shown([run]).sensitivity_and_accuracy == "Accuracy 50.00%"


def test_a_miss_is_held_one_tenth_under_its_goal():
    """Rounding alone would print a 94.98% miss of a 95% goal as 95.0%."""
    runs = _scored(10000.0, 9498.0)

    assert _shown(runs).badge is CardBadge.BELOW_THRESHOLD
    assert _shown(runs).pb_comparison == "94.9% of PB"


def test_a_run_below_the_pb_never_reads_as_all_of_it():
    """Rounding alone would print a run 0.03% short of the PB as 100.0%."""
    runs = _scored(10000.0, 9997.0)

    assert _shown(runs).pb_comparison == "99.9% of PB"
    # With nothing judging the run, this is the one cap left: there is no
    # goal to hold a miss under.
    assert _shown(runs, percentage=None).pb_comparison == "99.9% of PB"
    assert (
        _shown(_scored(10000.0, 9498.0), percentage=None).pb_comparison == "95.0% of PB"
    )


def test_a_run_that_ties_the_pb_reads_as_all_of_it():
    assert _shown(_scored(100.0, 100.0)).pb_comparison == "100.0% of PB"


# --- The comparison agrees with the judging rule, and with the celebration ----


def _chased(runs: list[RunData], pace):
    """Work out what the newest of one scenario's runs was chasing."""
    newest = runs[-1]

    def basis(version: str | None) -> PaceBasis | None:
        return pace(newest.scenario, version)

    return what_runs_chased(runs, basis)[newest]


def _event(runs: list[RunData], pace) -> dict:
    """Build the run event the newest of one scenario's runs would arrive in."""
    newest = runs[-1]
    chased = _chased(runs, pace)
    return {
        "run_id": run_id(newest),
        "scenario_name": newest.scenario,
        "sensitivity": "40.8 cm/360",
        "score": newest.score,
        "scenario_previous_best": chased.previous_best,
        "pace_constant": chased.pace_constant,
        "is_new_sensitivity": chased.is_new_sensitivity,
        "is_live": True,
    }


@pytest.mark.parametrize(
    ("scores", "pace", "hashed"),
    [
        ((100.0, 96.0), _no_pace, None),
        ((100.0, 90.0), _no_pace, None),
        ((10000.0, 9498.0), _no_pace, None),
        ((10000.0, 9997.0), _no_pace, None),
        ((407.0, 500.0, 407.0), _no_pace, None),
        ((50.0, 40.0), _pace_of(100.0), VERSION),
        ((50.0, 49.99), _pace_of(100.0), VERSION),
        ((-10.0, -20.0), _pace_of(100.0), VERSION),
    ],
)
@pytest.mark.parametrize("percentage", [90.0, 95.0, 99.0])
def test_the_percentage_is_the_judging_rules_own_at_every_goal(
    scores, pace, hashed, percentage
):
    """The card adds no rounding of its own to the rule's, by score or by pace.

    The run is judged here from what it was chasing, apart from the marks the
    card reads, and the two display caps are the rule's: a card that printed
    its own percentage would differ on the runs that sit at a cap.
    """
    runs = _scored(*scores, scenario_hash=hashed)
    chased = _chased(runs, pace)
    verdict = judge_run(
        runs[-1].score,
        chased.previous_best,
        chased.is_new_sensitivity,
        chased.pace_constant,
        percentage,
    )
    assert isinstance(verdict, ThresholdVerdict)

    measure = "PB pace" if verdict.by_pace else "PB"
    assert (
        _shown(runs, percentage=percentage, pace=pace).pb_comparison
        == f"{shown_percentage(verdict):.1f}% of {measure}"
    )


@pytest.mark.parametrize(
    ("scores", "pace", "hashed", "said"),
    [
        ((3000.0, 3324.0), _no_pace, None, r"Up [\d.]+% on your previous best of"),
        (
            (40.0, 50.0),
            _pace_of(100.0),
            VERSION,
            r"[\d.]+% faster than your previous best of",
        ),
        ((0.0, 12.0), _no_pace, None, r"Your previous best was"),
    ],
)
def test_a_new_pbs_gain_is_the_one_its_celebration_toast_printed(
    scores, pace, hashed, said
):
    runs = _scored(*scores, scenario_hash=hashed)
    toast = app_shell._celebration_toast(_event(runs, pace))

    printed = re.search(said, toast["message"])
    assert printed is not None
    comparison = _shown(runs, pace=pace).pb_comparison
    assert comparison is not None
    assert comparison.startswith(printed.group())


# --- The typical score at session start ----------------------------------------

# Two sittings before the card's session: a typical score of 100 from ten
# runs in two sessions, recent, and a PB of 200 the card's runs never beat.
EARLIER = ([100.0, 100.0, 200.0, 100.0, 100.0], [100.0] * 5)
# A time-scored scenario counting down from 100: a typical score of 40, 60 s
# a run, and a PB of 70, 30 s.
PACED = ([40.0, 40.0, 70.0, 40.0, 40.0], [40.0] * 5)


def _sittings(
    *sittings: list[float], gap: timedelta = timedelta(days=1), **fields
) -> list[RunData]:
    """Build one session per list of scores, ``gap`` apart, the last ending last."""
    runs: list[RunData] = []
    for index, scores in enumerate(sittings):
        start = EVENING - gap * (len(sittings) - 1 - index)
        runs += [
            _run(A, start + timedelta(minutes=order), score=score, **fields)
            for order, score in enumerate(scores)
        ]
    return runs


@pytest.mark.parametrize(
    ("score", "phrase"),
    [
        (103.6, "3.6% above typical at session start"),
        (94.2, "5.8% below typical at session start"),
        (100.06, "0.1% above typical at session start"),
        (99.94, "0.1% below typical at session start"),
        (100.04, "Matches typical at session start"),
        (99.96, "Matches typical at session start"),
    ],
)
def test_a_run_is_measured_from_the_typical_score_its_session_began_with(score, phrase):
    shown = _shown(_sittings(*EARLIER, [score]))

    assert shown.typical == TypicalPhrase(text=phrase, typical="100", not_recent=False)


def test_the_phrase_comes_before_the_pbs_percentage_on_one_line():
    shown = _shown(_sittings(*EARLIER, [103.6]))

    _score_row, line, *_rest = latest_run_card_content(shown, A, True).body

    assert rendered_text(line) == "3.6% above typical at session start · 51.8% of PB"
    assert line.className == latest_run_card.RESULT_CLASS


def test_every_run_of_a_session_meets_the_value_it_began_with():
    """Its own session's runs would move the typical score to 150; the phrase never moves."""
    runs = _sittings(*EARLIER, [150.0] * 12)

    for end in range(11, len(runs) + 1):
        shown = _shown(runs[:end])

        assert shown.typical == TypicalPhrase(
            text="50.0% above typical at session start",
            typical="100",
            not_recent=False,
        )


@pytest.mark.parametrize(
    "runs",
    [
        # A first session, however many runs it holds.
        _sittings([100.0] * 25),
        # Nine runs before the session make no typical score.
        _sittings([100.0] * 5, [100.0] * 4, [90.0]),
    ],
)
def test_with_no_known_value_at_session_start_there_is_no_phrase(runs):
    shown = _shown(runs)

    assert shown.typical is None
    assert rendered_text(latest_run_card_content(shown, A, True).body[1]) == (
        shown.pb_comparison
    )


def test_a_new_pb_keeps_its_gain_alone():
    """A new PB beats every earlier run, so the phrase could only read above."""
    shown = _shown(_sittings(*EARLIER, [250.0]))

    assert shown.typical is None
    assert shown.pb_comparison == "Up 25.0% on your previous best of 200"


@pytest.mark.parametrize("typical", [0.0, -10.0])
def test_by_score_a_typical_score_of_zero_or_less_has_no_phrase(typical):
    shown = _shown(_sittings([typical] * 4 + [5.0], [typical] * 5, [typical - 1]))

    assert shown.typical is None


@pytest.mark.parametrize(
    ("score", "phrase"),
    [
        (46.0, "11.1% faster than typical at session start"),
        (34.0, "9.1% slower than typical at session start"),
        (40.0, "Matches typical at session start"),
    ],
)
def test_a_time_scored_run_is_measured_from_the_typical_score_by_pace(score, phrase):
    shown = _shown(
        _sittings(*PACED, [score], scenario_hash=VERSION), pace=_pace_of(100.0)
    )

    assert shown.typical is not None
    assert shown.typical.text == phrase


def test_a_line_by_pace_names_both_of_its_measures():
    shown = _shown(
        _sittings(*PACED, [46.0], scenario_hash=VERSION), pace=_pace_of(100.0)
    )

    assert rendered_text(latest_run_card_content(shown, A, True).body[1]) == (
        "11.1% faster than typical at session start · 55.6% of PB pace"
    )


def test_a_run_of_another_version_behind_the_value_keeps_its_score_math():
    """The PB is of the run's version, so the PB's percentage is still by pace."""
    runs = _sittings(*PACED, [46.0], scenario_hash=VERSION)
    runs[0] = replace(runs[0], scenario_hash="an older version")

    shown = _shown(runs, pace=_pace_of(100.0))

    assert shown.typical is not None
    assert shown.typical.text == "15.0% above typical at session start"
    assert shown.pb_comparison == "55.6% of PB pace"


def test_the_typical_score_is_measured_by_pace_whatever_measured_the_pb():
    """A PB of an older version, out of the value's 20 runs, is measured by score."""
    runs = _sittings([70.0], [40.0] * 10, [40.0] * 10, [46.0], scenario_hash=VERSION)
    runs[0] = replace(runs[0], scenario_hash="an older version")

    shown = _shown(runs, pace=_pace_of(100.0))

    assert shown.typical is not None
    assert shown.typical.text == "11.1% faster than typical at session start"
    assert shown.pb_comparison == "65.7% of PB"


@pytest.mark.parametrize(
    "pace",
    [
        # No performance file answers for the version.
        _no_pace,
        # The typical score's time is not positive under this constant.
        _pace_of(40.0),
    ],
)
def test_without_a_pace_to_measure_by_a_time_scored_run_keeps_its_score_math(pace):
    shown = _shown(_sittings(*PACED, [46.0], scenario_hash=VERSION), pace=pace)

    assert shown.typical is not None
    assert shown.typical.text == "15.0% above typical at session start"


def test_a_value_that_wasnt_recent_when_the_session_began_is_marked():
    """Both earlier sittings were more than 30 days before the session."""
    shown = _shown(_sittings(*EARLIER, [103.6], gap=timedelta(days=31)))

    assert shown.typical == TypicalPhrase(
        text="3.6% above typical at session start", typical="100", not_recent=True
    )


def test_a_value_recent_when_the_session_began_is_never_marked_later():
    """Read two months on, the value is judged when the session began."""
    runs = _sittings(*EARLIER, [103.6])

    shown = _shown(runs, now=EVENING + timedelta(days=60))

    assert shown.typical is not None
    assert shown.typical.not_recent is False


def test_the_value_is_formatted_as_the_scenario_table_formats_a_typical_score():
    """The median of 100 and 101.5, to its runs' one decimal place."""
    shown = _shown(_sittings([100.0] * 5, [101.5] * 4 + [300.0], [103.0]))

    assert shown.typical is not None
    assert shown.typical.typical == "100.8"


# --- The session line ----------------------------------------------------------


def _line(shown: LatestRun) -> str:
    """Read the card's session line: the run in its session, then its time."""
    return shown.session


def _visits() -> list[RunData]:
    """Two visits to A with a visit to B between them, in one session.

    The first visit runs from 9:45 to 9:50 PM and the second from 9:59 to
    10:06 PM, each from its first run's start to its last run's end.
    """
    return [
        _run(A, EVENING + timedelta(minutes=1)),
        _run(A, EVENING + timedelta(minutes=5)),
        _run(B, EVENING + timedelta(minutes=10)),
        _run(A, EVENING + timedelta(minutes=15)),
        _run(A, EVENING + timedelta(minutes=21)),
    ]


def test_the_run_is_numbered_and_the_scenarios_visits_are_summed_on_one_line():
    """The breaks inside a visit count, and the time on another scenario does not."""
    assert _line(_shown(_visits())) == "Run 4 this session · 12 min on this scenario"


def test_the_number_counts_this_scenarios_runs_in_the_runs_own_session_only():
    earlier_session = [
        _run(A, EVENING - timedelta(hours=3)),
        _run(A, EVENING - timedelta(hours=3) + timedelta(minutes=2)),
    ]

    assert (
        _line(_shown([*earlier_session, *_visits()]))
        == "Run 4 this session · 12 min on this scenario"
    )


def test_the_run_is_its_scenarios_last_in_the_session_and_not_the_sessions_last():
    """Another scenario played after it changes neither line."""
    runs = [*_visits(), _run(B, EVENING + timedelta(minutes=25))]

    shown = _shown(runs, scenario=A)

    assert shown.run_id == run_id(runs[4])
    assert _line(shown) == "Run 4 this session · 12 min on this scenario"


@pytest.mark.parametrize(
    ("seconds", "time"),
    [
        (15, "<1 min"),
        (45, "1 min"),
        # A run of 60 seconds measures a little under 60: its start is
        # written to the millisecond and its end is a whole second.
        (59.9, "1 min"),
    ],
)
def test_the_time_on_a_scenario_rounds_to_the_nearest_minute(seconds, time):
    runs = [_run(A, EVENING, length=timedelta(seconds=seconds))]

    assert _line(_shown(runs)) == f"Run 1 this session · {time} on this scenario"


@pytest.mark.parametrize(
    ("since_the_run", "which"),
    [
        (timedelta(0), "this session"),
        (timedelta(minutes=30), "this session"),
        (timedelta(minutes=30, seconds=1), "last session"),
        (timedelta(days=3), "last session"),
    ],
)
def test_once_the_session_has_ended_the_line_says_last_session(since_the_run, which):
    runs = _visits()
    now = runs[-1].datetime_object + since_the_run

    assert _line(_shown(runs, now=now)) == f"Run 4 {which} · 12 min on this scenario"


def test_a_visit_whose_first_run_has_no_usable_start_reads_as_time_unknown():
    """Counted from the run's end, one long run would read as under a minute."""
    one_long_run = [_run(A, EVENING, length=None)]

    assert (
        _line(_shown(one_long_run))
        == "Run 1 this session · Time on this scenario unknown"
    )
    assert (
        _line(_shown(one_long_run, now=EVENING + timedelta(hours=2)))
        == "Run 1 last session · Time on this scenario unknown"
    )


@pytest.mark.parametrize("without_a_start", [0, 3])
def test_the_time_is_unknown_when_any_visits_first_run_has_no_usable_start(
    without_a_start,
):
    """The run's number stays, and no number is given for the time."""
    runs = _visits()
    broken = runs[without_a_start]
    runs[without_a_start] = _run(A, broken.datetime_object, length=None)

    line = _line(_shown(runs))

    assert line == "Run 4 this session · Time on this scenario unknown"
    assert not re.search(r"\d+ (min|hr)", line)


def test_a_later_run_of_a_visit_with_no_usable_start_leaves_the_time_known():
    """A visit is timed from its first run's start to its last run's end."""
    runs = _visits()
    runs[1] = _run(A, runs[1].datetime_object, length=None)
    runs[4] = _run(A, runs[4].datetime_object, length=None)

    assert _line(_shown(runs)) == "Run 4 this session · 12 min on this scenario"


def test_a_visit_to_another_scenario_with_no_usable_start_leaves_the_time_known():
    runs = _visits()
    runs[2] = _run(B, runs[2].datetime_object, length=None)

    assert _line(_shown(runs)) == "Run 4 this session · 12 min on this scenario"


# --- An older session's name ---------------------------------------------------


def _listed_name(
    runs: list[RunData], scenario: str, first_run: RunData, now: datetime
) -> str:
    """Read the name the run list gives the session that ``first_run`` begins."""
    model = build_run_list(runs, scenario, 30, now, _marks(runs, scenario))
    session_id = f"s:{run_id(first_run)}"
    (row,) = (row for row in model["rows"] if row["id"] == session_id)
    assert row["kind"] == SESSION_ROW
    return row["name"]


@pytest.mark.parametrize(
    "since_the_newest",
    [
        # The newest session is still in progress.
        timedelta(0),
        # It has ended: it is "last session", and an older one is still named.
        timedelta(days=3),
    ],
)
def test_a_run_in_an_older_session_names_it_as_the_run_list_names_its_row(
    since_the_newest,
):
    """An older session the same day as the newest is named, never "last session"."""
    older = [
        _run(A, datetime(2026, 10, 4, 14, 1)),
        _run(A, datetime(2026, 10, 4, 14, 6), score=120.0),
    ]
    newest = [_run(B, EVENING), _run(B, EVENING + timedelta(minutes=4))]
    runs = [*older, *newest]
    now = newest[-1].datetime_object + since_the_newest

    shown = _shown(runs, scenario=A, now=now)

    assert shown.run_id == run_id(older[1])
    assert _line(shown) == "Run 2 (Oct 4, 2:00 PM session) · 6 min on this scenario"
    assert _listed_name(runs, A, older[0], now) == "Oct 4, 2:00 PM"


def test_a_session_from_an_earlier_year_is_named_with_its_year():
    older = [_run(A, datetime(2025, 12, 30, 21, 46))]
    newest = [_run(B, datetime(2026, 1, 2, 9, 0))]
    runs = [*older, *newest]
    now = datetime(2026, 1, 2, 9, 1)

    assert _line(_shown(runs, scenario=A, now=now)) == (
        "Run 1 (Dec 30, 2025, 9:45 PM session) · 1 min on this scenario"
    )
    assert _listed_name(runs, A, older[0], now) == "Dec 30, 2025, 9:45 PM"


def test_the_year_joins_the_name_once_the_date_moves_into_a_new_year():
    """The app's clock decides, as it does for the run list's rows."""
    runs = [
        _run(A, datetime(2025, 12, 30, 21, 46)),
        _run(B, datetime(2025, 12, 31, 9, 0)),
    ]

    before = _shown(runs, scenario=A, now=datetime(2025, 12, 31, 23, 59))
    after = _shown(runs, scenario=A, now=datetime(2026, 1, 1, 0, 0))

    assert before.session == "Run 1 (Dec 30, 9:45 PM session) · 1 min on this scenario"
    assert after.session == (
        "Run 1 (Dec 30, 2025, 9:45 PM session) · 1 min on this scenario"
    )


def test_an_older_session_whose_first_run_has_no_usable_start_is_named_by_its_end():
    """As the run list names it: the session begins when that run ended."""
    older = [_run(A, datetime(2026, 10, 4, 14, 1), length=None)]
    newest = [_run(B, EVENING)]
    runs = [*older, *newest]

    assert _line(_shown(runs, scenario=A, now=EVENING)) == (
        "Run 1 (Oct 4, 2:01 PM session) · Time on this scenario unknown"
    )
    assert _listed_name(runs, A, older[0], EVENING) == "Oct 4, 2:01 PM"


# --- From the run store --------------------------------------------------------


def test_the_run_store_is_copied_once_and_the_fields_value_is_made_usable(
    monkeypatch,
):
    copies = []

    def get_all_runs():
        copies.append(1)
        return _scored(100.0, 96.0)

    monkeypatch.setattr(latest_run_card, "get_all_runs", get_all_runs)
    monkeypatch.setattr(
        latest_run_card, "get_version_pace_basis", lambda _scenario, _version: None
    )

    judged, _newest = latest_run_from_store(A, "95", EVENING + timedelta(minutes=1))
    unjudged, _newest = latest_run_from_store(A, "", EVENING + timedelta(minutes=1))

    assert len(copies) == 2
    assert judged is not None
    assert unjudged is not None
    assert judged.badge is CardBadge.THRESHOLD_PASSED
    # A cleared field arrives as an empty string.
    assert unjudged.badge is None


@pytest.mark.parametrize("selected", [A, B, None])
def test_the_newest_run_on_any_scenario_comes_from_the_same_copy_as_the_cards(
    monkeypatch, selected
):
    """So the card and the ring's store never come from two moments."""
    copies = []
    runs = [
        _run(A, EVENING, score=80.0),
        _run(B, EVENING + timedelta(minutes=5), score=612.5),
    ]

    def get_all_runs():
        copies.append(1)
        return list(runs)

    monkeypatch.setattr(latest_run_card, "get_all_runs", get_all_runs)
    monkeypatch.setattr(
        latest_run_card, "get_version_pace_basis", lambda _scenario, _version: None
    )

    shown, newest_run_id = latest_run_from_store(
        selected, 95.0, EVENING + timedelta(minutes=6)
    )

    assert copies == [1]
    # The newest run overall, whatever the card reports.
    assert newest_run_id == run_id(runs[1])
    assert (shown is None) == (selected is None)
    if shown is not None:
        (selected_run,) = (run for run in runs if run.scenario == selected)
        assert shown.run_id == run_id(selected_run)


@pytest.mark.parametrize("selected", [A, None])
def test_an_empty_run_store_has_no_latest_run_and_no_newest_run(monkeypatch, selected):
    monkeypatch.setattr(latest_run_card, "get_all_runs", list)

    assert latest_run_from_store(selected, 95.0, EVENING) == (None, None)


# --- What the card draws -------------------------------------------------------


def _walk(component):
    yield component
    children = getattr(component, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk(child)
    elif children is not None and not isinstance(children, str):
        yield from _walk(children)


LATEST = LatestRun(
    run_id="a.csv",
    played_at=datetime(2026, 10, 4, 22, 50),
    score="3,324",
    badge=CardBadge.THRESHOLD_PASSED,
    typical=None,
    pb_comparison="96.4% of PB",
    session="Run 7 (Oct 4, 2:00 PM session) · 1 hr 6 min on this scenario",
    sensitivity_and_accuracy="50 cm/360 · Accuracy 55.00%",
)


def test_the_card_starts_with_nothing_in_it_and_holds_no_button():
    """The card follows the selection, so it has no scenario of its own to offer."""
    card = latest_run_card.latest_run_card(IDS)

    held = {
        component.id: component
        for component in _walk(card)
        if getattr(component, "id", None)
    }
    assert set(held) == set(IDS)
    assert card.className == "run-history-card"
    assert held[IDS.body].children is None
    assert isinstance(held[IDS.played_at], dcc.Store)
    assert getattr(held[IDS.played_at], "data", None) is None
    assert not [
        component for component in _walk(card) if isinstance(component, html.Button)
    ]


def test_the_first_lines_words_and_the_age_are_drawn_once_and_hidden_until_a_run():
    """A script writes the age, so it is never part of the server's answer.

    The first line is ``Latest run · {age}``, and no scenario's name: the
    card follows the selection, which the Selected scenario field and the
    chart's title name. With no run the card's name stays, as the PB card's
    ``PB`` does, and only the words that hold the age are hidden.
    """
    card = latest_run_card.latest_run_card(IDS)
    held = {
        component.id: component
        for component in _walk(card)
        if getattr(component, "id", None)
    }
    heading = next(
        component
        for component in _walk(card)
        if getattr(component, "className", None) == latest_run_card.HEADING_CLASS
    )

    name, label = heading.children
    assert name == "Latest run"
    assert label is held[IDS.label]
    assert label.hidden is True
    lead, tooltip = label.children
    assert lead == " · "
    assert tooltip.id == IDS.time_tooltip
    assert tooltip.events == {"hover": True, "focus": True, "touch": True}
    # dmc wraps the target in a block box; the stylesheet makes it inline.
    assert tooltip.boxWrapperProps == {"className": "run-history-card-time-target"}
    age = tooltip.children
    assert age.id == IDS.time
    # Focusable, with the hover affordance Last played's has, and in the
    # heading's own size and color.
    assert (age.className, age.tabIndex, age.inherit, age.span) == (
        "cell-tooltip-affordance",
        0,
        True,
        True,
    )
    assert getattr(age, "children", None) is None


def test_the_card_names_no_scenario_and_holds_when_the_run_ended():
    content = latest_run_card_content(LATEST, A, True)

    assert content._fields == ("played_at", "body")
    assert content.played_at == LATEST.played_at.timestamp()
    assert A not in "".join(rendered_text(child) for child in content.body)


def test_the_body_is_the_score_with_its_badge_then_three_lines():
    """The comparison at its own weight, then the session and the run's settings, quiet."""
    body = latest_run_card_content(LATEST, A, True).body
    score_row, comparison, session, last = body

    # The score ends on a space a screen reader reads: the row is a flex
    # container, which would hand over "3,324Threshold passed" as one word.
    assert [rendered_text(child) for child in score_row.children] == [
        "3,324 ",
        "Threshold passed",
    ]
    score = score_row.children[0]
    assert score.className == latest_run_card.SCORE_CLASS
    value, word_end = score.children
    assert value == "3,324"
    assert (word_end.children, word_end.className) == (
        " ",
        "run-history-card-word-end",
    )
    assert rendered_text(comparison) == "96.4% of PB"
    assert comparison.className == latest_run_card.RESULT_CLASS
    assert rendered_text(session) == (
        "Run 7 (Oct 4, 2:00 PM session) · 1 hr 6 min on this scenario"
    )
    assert rendered_text(last) == "50 cm/360 · Accuracy 55.00%"
    assert session.className == last.className == latest_run_card.QUIET_CLASS


def test_with_no_comparison_the_line_is_left_out():
    """A scenario's first run has no PB to measure against."""
    shown = LatestRun(**{**LATEST.__dict__, "pb_comparison": None})
    score_row, session, last = latest_run_card_content(shown, A, True).body

    assert score_row.className == latest_run_card.SCORE_ROW_CLASS
    assert session.className == last.className == latest_run_card.QUIET_CLASS


RECENT_PHRASE = TypicalPhrase(
    text="3.6% above typical at session start", typical="3,025", not_recent=False
)


def _comparison_line(phrase: TypicalPhrase, pb_comparison: str | None = "85.8% of PB"):
    shown = replace(LATEST, typical=phrase, pb_comparison=pb_comparison)
    return latest_run_card_content(shown, A, True).body[1]


def test_the_phrase_opens_its_hover_by_mouse_and_keyboard():
    """Focusable, with the age's hover affordance, inline in the line."""
    line = _comparison_line(RECENT_PHRASE)
    tooltip, rest = line.children

    assert rest == " · 85.8% of PB"
    assert tooltip.events == {"hover": True, "focus": True, "touch": True}
    # dmc wraps the target in a block box; the stylesheet makes it inline.
    assert tooltip.boxWrapperProps == {"className": "run-history-card-time-target"}
    target = tooltip.children
    assert (target.className, target.tabIndex) == ("cell-tooltip-affordance", 0)
    assert target.children == ["3.6% above typical at session start"]
    assert [rendered_text(part) for part in tooltip.label] == [
        "Typical score when this run's session began: 3,025"
    ]


def test_an_old_value_has_the_tables_clock_and_words_and_a_second_hover_line():
    """The clock is hidden from a screen reader, which hears the table's words."""
    tooltip, _rest = _comparison_line(replace(RECENT_PHRASE, not_recent=True)).children

    text, clock, words = tooltip.children.children
    assert text == "3.6% above typical at session start"
    assert clock.className == "typical-old-mark"
    assert clock.to_plotly_json()["props"]["aria-hidden"] == "true"
    assert getattr(clock, "children", None) is None
    assert (words.className, words.children) == ("visually-hidden", ", Not recent")
    assert [rendered_text(part) for part in tooltip.label] == [
        "Typical score when this run's session began: 3,025",
        "Fewer than 10 of its runs were from the 30 days before the session "
        "began, so it may have been out of date.",
    ]


def test_the_cards_not_recent_words_are_the_scenario_tables():
    assert latest_run_card.NOT_RECENT_TEXT is playlist_scenarios.NOT_RECENT_TEXT


def test_a_phrase_with_no_pb_part_stands_alone():
    (tooltip,) = _comparison_line(RECENT_PHRASE, None).children

    assert rendered_text(tooltip) == "3.6% above typical at session start"


@pytest.mark.parametrize(
    ("badge", "text", "color"),
    [
        (CardBadge.NEW_PB, "New PB", "yellow"),
        (CardBadge.THRESHOLD_PASSED, "Threshold passed", "green"),
        (CardBadge.BELOW_THRESHOLD, "Below threshold", "gray"),
    ],
)
def test_each_badge_reads_as_the_copy_has_it(badge, text, color):
    shown = LatestRun(**{**LATEST.__dict__, "badge": badge})

    _score, drawn = latest_run_card_content(shown, A, True).body[0].children

    assert drawn.children == text
    assert drawn.className == "run-history-card-badge"
    assert drawn.style == {
        "--run-history-card-badge-color": f"var(--mantine-color-{color}-6)"
    }
    # The badge's own style would print capitals.
    assert drawn.tt == "none"


def test_a_run_with_no_badge_shows_its_score_alone():
    shown = LatestRun(**{**LATEST.__dict__, "badge": None})

    score_row = latest_run_card_content(shown, A, True).body[0]

    # The word-end space stays: the next line is a block, so it reads the same.
    assert [rendered_text(child) for child in score_row.children] == ["3,324 "]


@pytest.mark.parametrize(
    ("selected", "store_has_runs", "said"),
    [
        # Nothing selected and no runs: the first run's two steps. With
        # Follow off a first run leaves the selection empty.
        (
            None,
            False,
            [
                "No runs yet",
                "Play a scenario in KovaaK's. Select it to see its latest run.",
            ],
        ),
        (
            "",
            False,
            [
                "No runs yet",
                "Play a scenario in KovaaK's. Select it to see its latest run.",
            ],
        ),
        # Nothing selected in a store with runs.
        (None, True, ["No scenario selected"]),
        ("", True, ["No scenario selected"]),
        # A scenario with no runs, whether or not the store has any: the
        # selection decides first, as on the PB card.
        (
            A,
            True,
            [
                "No runs yet",
                "Play this scenario in KovaaK's and your latest run will show here.",
            ],
        ),
        (
            A,
            False,
            [
                "No runs yet",
                "Play this scenario in KovaaK's and your latest run will show here.",
            ],
        ),
    ],
)
def test_with_no_run_to_report_the_card_says_why(selected, store_has_runs, said):
    content = latest_run_card_content(None, selected, store_has_runs)

    # Nothing to word, so the script hides the age, and "Latest run" stays.
    assert content.played_at is None
    assert [rendered_text(line) for line in content.body] == said
    # A title, then the sentence in the quieter style, as the PB card's.
    assert content.body[0].className == latest_run_card.EMPTY_TITLE_CLASS
    assert all(
        line.className == latest_run_card.EMPTY_MESSAGE_CLASS
        for line in content.body[1:]
    )
