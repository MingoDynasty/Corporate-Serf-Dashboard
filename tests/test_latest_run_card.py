"""What the Run History page's latest-run card shows.

``latest_run`` is one pure function over run records, so these tests build
records and read the text the card shows. How the page calls it, and when,
is ``tests/test_run_history_page.py``.
"""

import re
from datetime import datetime, timedelta

import dash
import pytest
from dash import dcc

dash.Dash(__name__, use_pages=True, pages_folder="")

from source import app_shell  # noqa: E402
from source.components import latest_run_card  # noqa: E402
from source.components.latest_run_card import (  # noqa: E402
    CardBadge,
    LatestRun,
    LatestRunCardIds,
    latest_run,
    latest_run_card_content,
    latest_run_from_store,
)
from source.components.run_history_list import build_run_list, run_id  # noqa: E402
from source.components.run_marks import mark_runs, what_runs_chased  # noqa: E402
from source.components.score_threshold import (  # noqa: E402
    ThresholdVerdict,
    judge_run,
    shown_percentage,
)
from source.kovaaks.data_models import RunData  # noqa: E402
from source.kovaaks.play_sessions import in_play_order  # noqa: E402
from source.kovaaks.time_scored_service import PaceBasis  # noqa: E402
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
    percentage: float | None = 95.0,
    now: datetime | None = None,
    pace=_no_pace,
) -> LatestRun:
    """Work the card out as the page does, for a store that holds ``runs``."""
    if now is None:
        now = max(run.datetime_object for run in runs)
    shown = latest_run(runs, percentage, now, pace)
    assert shown is not None
    return shown


# --- Which run it is, and its first line ---------------------------------------


def test_a_store_with_no_runs_has_no_latest_run():
    assert latest_run([], 95.0, EVENING, _no_pace) is None


def test_the_card_reports_the_last_run_played_on_whatever_scenario():
    runs = [
        _run(A, EVENING, score=80.0),
        _run(B, EVENING + timedelta(minutes=5), score=612.5),
        _run(A, EVENING - timedelta(days=2), score=90.0),
    ]

    shown = _shown(runs)

    assert (shown.scenario, shown.score) == (B, "612.5")
    assert shown.run_id == run_id(runs[1])


def test_the_cards_run_is_the_one_the_run_list_names_as_the_newest():
    """So the row the list highlights is the run the card reports."""
    runs = [
        _run(A, EVENING),
        # Two runs that ended in the same second: the order the sessions are
        # split in settles which of them is the newest.
        _run(B, EVENING + timedelta(minutes=3), length=timedelta(seconds=90)),
        _run(A, EVENING + timedelta(minutes=3), length=timedelta(seconds=30)),
    ]
    now = EVENING + timedelta(minutes=4)

    for scenario in (A, B):
        marks = mark_runs(
            in_play_order(run for run in runs if run.scenario == scenario),
            95.0,
            lambda _version: None,
        )
        model = build_run_list(runs, scenario, 30, now, marks)
        assert _shown(runs, now=now).run_id == model["newest_run"]


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
    assert latest_run_card_content(shown, A).played_at == ended.timestamp()


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


# --- The second line -----------------------------------------------------------


def test_a_run_shows_its_percentage_of_the_pb_it_was_chasing_and_its_accuracy():
    runs = _scored(100.0, 120.0, 96.0, accuracy=0.57)

    # Against 120, the PB before it, and not against the first run's 100.
    assert _shown(runs).result == "80.0% of PB · Accuracy 57%"


def test_the_percentage_shows_whether_or_not_the_run_was_judged():
    """It is a fact about the run, and an empty threshold does not hide it."""
    runs = _scored(100.0, 96.0)
    first_at_its_sensitivity = [
        *_scored(100.0),
        _run(A, EVENING + timedelta(minutes=1), score=96.0, sensitivity=30.0),
    ]

    assert _shown(runs).result == "96.0% of PB · Accuracy 50%"
    assert _shown(runs, percentage=None).result == "96.0% of PB · Accuracy 50%"
    assert _shown(first_at_its_sensitivity).result == "96.0% of PB · Accuracy 50%"


def test_a_time_scored_run_shows_its_percentage_of_the_pbs_pace():
    # A clock that counts down from 100: 50 took 50 seconds and 40 took 60.
    runs = _scored(50.0, 40.0, scenario_hash=VERSION)

    assert _shown(runs, pace=_pace_of(100.0)).result == (
        "83.3% of PB pace · Accuracy 50%"
    )
    assert _shown(runs, percentage=None, pace=_pace_of(100.0)).result == (
        "83.3% of PB pace · Accuracy 50%"
    )


def test_a_time_scored_pb_of_zero_or_less_still_has_a_percentage_of_pace():
    """Pace needs positive times, and not a positive previous best."""
    runs = _scored(-10.0, -20.0, scenario_hash=VERSION)

    assert _shown(runs, pace=_pace_of(100.0)).result == (
        "91.7% of PB pace · Accuracy 50%"
    )


def test_a_new_pb_says_how_far_it_beat_the_previous_best():
    runs = _scored(3000.0, 3324.0)

    assert _shown(runs).result == (
        "Up 10.8% on your previous best of 3,000 · Accuracy 50%"
    )
    # Judged or not, it reads the same.
    assert _shown(runs, percentage=None).result == _shown(runs).result


def test_a_new_pb_by_pace_says_how_much_faster_it_finished():
    # 40 took 60 seconds and 50 took 50: a fifth faster.
    runs = _scored(40.0, 50.0, scenario_hash=VERSION)

    assert _shown(runs, pace=_pace_of(100.0)).result == (
        "20.0% faster than your previous best of 40 · Accuracy 50%"
    )


@pytest.mark.parametrize(("previous", "worded"), [(0.0, "0"), (-5.5, "-5.5")])
def test_a_new_pb_over_a_previous_best_of_zero_or_less_names_it(previous, worded):
    runs = _scored(previous, 12.0)

    assert _shown(runs).result == f"Your previous best was {worded} · Accuracy 50%"


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
def test_a_run_with_no_percentage_shows_its_accuracy_alone(runs):
    assert _shown(runs).result == "Accuracy 50%"
    assert _shown(runs, percentage=None).result == "Accuracy 50%"


@pytest.mark.parametrize(
    ("accuracy", "worded"),
    [(0.544, "54%"), (0.545, "55%"), (0.555, "56%"), (1.0, "100%"), (0.0, "0%")],
)
def test_accuracy_is_shown_to_the_whole_percent_a_half_rounding_up(accuracy, worded):
    assert _shown(_scored(100.0, accuracy=accuracy)).result == f"Accuracy {worded}"


def test_a_miss_is_held_one_tenth_under_its_goal():
    """Rounding alone would print a 94.98% miss of a 95% goal as 95.0%."""
    runs = _scored(10000.0, 9498.0)

    assert _shown(runs).badge is CardBadge.BELOW_THRESHOLD
    assert _shown(runs).result == "94.9% of PB · Accuracy 50%"


def test_a_run_below_the_pb_never_reads_as_all_of_it():
    """Rounding alone would print a run 0.03% short of the PB as 100.0%."""
    runs = _scored(10000.0, 9997.0)

    assert _shown(runs).result == "99.9% of PB · Accuracy 50%"
    # With nothing judging the run, this is the one cap left: there is no
    # goal to hold a miss under.
    assert _shown(runs, percentage=None).result == "99.9% of PB · Accuracy 50%"
    assert _shown(_scored(10000.0, 9498.0), percentage=None).result == (
        "95.0% of PB · Accuracy 50%"
    )


def test_a_run_that_ties_the_pb_reads_as_all_of_it():
    assert _shown(_scored(100.0, 100.0)).result == "100.0% of PB · Accuracy 50%"


# --- The second line agrees with the judging rule, and with the celebration ----


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
    assert _shown(runs, percentage=percentage, pace=pace).result == (
        f"{shown_percentage(verdict):.1f}% of {measure} · Accuracy 50%"
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
    assert _shown(runs, pace=pace).result.startswith(printed.group())


# --- The third line ------------------------------------------------------------


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


def test_the_third_line_numbers_the_run_and_sums_the_scenarios_visits():
    """The breaks inside a visit count, and the time on another scenario does not."""
    assert _shown(_visits()).session == "Run 4 this session · 12 min on this scenario"


def test_the_number_counts_this_scenarios_runs_in_the_runs_own_session_only():
    earlier_session = [
        _run(A, EVENING - timedelta(hours=3)),
        _run(A, EVENING - timedelta(hours=3) + timedelta(minutes=2)),
    ]

    assert _shown([*earlier_session, *_visits()]).session == (
        "Run 4 this session · 12 min on this scenario"
    )


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

    assert _shown(runs).session == f"Run 1 this session · {time} on this scenario"


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

    assert _shown(runs, now=now).session == f"Run 4 {which} · 12 min on this scenario"


def test_a_visit_whose_first_run_has_no_usable_start_reads_as_time_unknown():
    """Counted from the run's end, one long run would read as under a minute."""
    one_long_run = [_run(A, EVENING, length=None)]

    assert _shown(one_long_run).session == (
        "Run 1 this session · Time on this scenario unknown"
    )
    assert _shown(one_long_run, now=EVENING + timedelta(hours=2)).session == (
        "Run 1 last session · Time on this scenario unknown"
    )


@pytest.mark.parametrize("without_a_start", [0, 3])
def test_the_time_is_unknown_when_any_visits_first_run_has_no_usable_start(
    without_a_start,
):
    """The run's number stays, and no number is given for the time."""
    runs = _visits()
    broken = runs[without_a_start]
    runs[without_a_start] = _run(A, broken.datetime_object, length=None)

    shown = _shown(runs).session

    assert shown == "Run 4 this session · Time on this scenario unknown"
    assert not re.search(r"\d+ (min|hr)", shown)


def test_a_later_run_of_a_visit_with_no_usable_start_leaves_the_time_known():
    """A visit is timed from its first run's start to its last run's end."""
    runs = _visits()
    runs[1] = _run(A, runs[1].datetime_object, length=None)
    runs[4] = _run(A, runs[4].datetime_object, length=None)

    assert _shown(runs).session == "Run 4 this session · 12 min on this scenario"


def test_a_visit_to_another_scenario_with_no_usable_start_leaves_the_time_known():
    runs = _visits()
    runs[2] = _run(B, runs[2].datetime_object, length=None)

    assert _shown(runs).session == "Run 4 this session · 12 min on this scenario"


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

    judged = latest_run_from_store("95", EVENING + timedelta(minutes=1))
    unjudged = latest_run_from_store("", EVENING + timedelta(minutes=1))

    assert len(copies) == 2
    assert judged is not None
    assert unjudged is not None
    assert judged.badge is CardBadge.THRESHOLD_PASSED
    # A cleared field arrives as an empty string.
    assert unjudged.badge is None


def test_an_empty_run_store_has_no_latest_run(monkeypatch):
    monkeypatch.setattr(latest_run_card, "get_all_runs", list)

    assert latest_run_from_store(95.0, EVENING) is None


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
    scenario=A,
    played_at=datetime(2026, 10, 4, 22, 50),
    score="3,324",
    badge=CardBadge.THRESHOLD_PASSED,
    result="96.4% of PB · Accuracy 55%",
    session="Run 7 this session · 1 hr 6 min on this scenario",
)


def test_the_card_starts_with_nothing_in_it_and_always_holds_its_button():
    """The selection callback takes the button, so it is never drawn again."""
    card = latest_run_card.latest_run_card(IDS)

    held = {
        component.id: component
        for component in _walk(card)
        if getattr(component, "id", None)
    }
    assert set(held) == set(IDS)
    assert card.className == "run-history-card"
    assert held[IDS.heading].children is None
    assert held[IDS.body].children is None
    assert isinstance(held[IDS.played_at], dcc.Store)
    assert getattr(held[IDS.played_at], "data", None) is None
    button = held[IDS.scenario_button]
    assert (button.children, button.n_clicks, button.type) == (None, 0, "button")


def test_the_first_lines_words_and_the_age_are_drawn_once_and_hidden_until_a_run():
    """A script writes the age, so it is never part of the server's answer.

    The words, the age and the dots between are one item of the heading, so
    the spaces either side of the age reach a screen reader: the heading is a
    flex container, which drops a space between its items.
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

    label = held[IDS.label]
    assert heading.children[0] is label
    assert label.className == latest_run_card.HEADING_LABEL_CLASS
    assert label.hidden is True
    lead, tooltip, trail = label.children
    assert (lead, trail) == ("Latest run · ", " · ")
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


def test_while_its_scenario_is_selected_the_name_is_plain_text():
    content = latest_run_card_content(LATEST, A)

    assert rendered_text(content.heading) == A
    # The title gives the whole name where the card cuts it short.
    assert content.heading.title == A
    assert content.played_at == LATEST.played_at.timestamp()
    assert (
        content.scenario_button,
        content.scenario_button_value,
        content.scenario_button_label,
    ) == (None, None, None)


@pytest.mark.parametrize("selected", [B, None, ""])
def test_while_another_scenario_is_selected_the_name_is_the_button(selected):
    content = latest_run_card_content(LATEST, selected)

    assert content.heading is None
    assert content.played_at == LATEST.played_at.timestamp()
    assert content.scenario_button == A
    assert content.scenario_button_value == A
    assert content.scenario_button_label == f"Show {A}"


def test_the_body_is_the_score_with_its_badge_then_the_two_lines():
    score_row, result, session = latest_run_card_content(LATEST, A).body

    assert [rendered_text(child) for child in score_row.children] == [
        "3,324",
        "Threshold passed",
    ]
    assert rendered_text(result) == "96.4% of PB · Accuracy 55%"
    assert rendered_text(session) == (
        "Run 7 this session · 1 hr 6 min on this scenario"
    )


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

    _score, drawn = latest_run_card_content(shown, A).body[0].children

    assert (drawn.children, drawn.color) == (text, color)
    # The badge's own style would print capitals.
    assert drawn.tt == "none"


def test_a_run_with_no_badge_shows_its_score_alone():
    shown = LatestRun(**{**LATEST.__dict__, "badge": None})

    score_row = latest_run_card_content(shown, A).body[0]

    assert [rendered_text(child) for child in score_row.children] == ["3,324"]


@pytest.mark.parametrize("selected", [A, None])
def test_with_no_run_in_the_store_the_card_says_so(selected):
    content = latest_run_card_content(None, selected)

    # Nothing to word, so the script hides the first line's words.
    assert content.played_at is None
    assert content.heading is None
    assert content.scenario_button is None
    assert [rendered_text(line) for line in content.body] == [
        "No runs yet",
        "Play a scenario in KovaaK's and your latest run will show here.",
    ]
