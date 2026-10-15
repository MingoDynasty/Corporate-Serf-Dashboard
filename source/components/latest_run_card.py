"""What the Run History page's latest-run card shows: the last run played.

``latest_run`` works out, from a copy of the run store, the newest run on any
scenario and what the card says about it: when it was played, its score, its
verdict, how it measured up against the PB it was chasing, and where it sits
in its session. The rest of the module draws that in the card.

The card is worked out from the run store each time, never from the message a
new run arrives in, so it is right on a page that has just been drawn, with
no new run.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, NamedTuple

import dash_mantine_components as dmc
from dash import dcc, html

from source.components.chart_options import TOOLTIP_EVENTS
from source.components.run_history_list import (
    BELOW_THRESHOLD_TEXT,
    NEW_PB_TEXT,
    NO_RUNS_TEXT,
    THRESHOLD_PASSED_TEXT,
    run_id,
)
from source.components.run_marks import Chased, what_runs_chased
from source.components.score_threshold import (
    ThresholdVerdict,
    Unjudged,
    judge_run,
    normalize_score_threshold_percentage,
    shown_percentage,
)
from source.kovaaks.data_models import RunData
from source.kovaaks.data_service import get_all_runs, new_high_score_runs
from source.kovaaks.pace import percent_faster
from source.kovaaks.play_sessions import (
    PlaySession,
    find_play_session_in_progress,
    in_play_order,
    split_into_play_sessions,
    split_into_scenario_visits,
)
from source.kovaaks.time_scored_service import PaceBasis, get_version_pace_basis
from source.utilities.utilities import (
    format_elapsed_duration,
    format_score,
    format_whole_percent,
)

LATEST_RUN_LABEL = "Latest run"
NO_RUNS_MESSAGE = "Play a scenario in KovaaK's and your latest run will show here."

CARD_CLASS = "run-history-card"
HEADING_CLASS = "run-history-card-heading"
HEADING_TEXT_CLASS = "run-history-card-heading-text"
HEADING_LABEL_CLASS = "run-history-card-label"
# The run's age, with the hover affordance Last played's has.
TIME_CLASS = "cell-tooltip-affordance"
TIME_TARGET_CLASS = "run-history-card-time-target"
SCENARIO_CLASS = "run-history-card-scenario"
SCENARIO_BUTTON_CLASS = f"{SCENARIO_CLASS} run-history-card-scenario-button"
BODY_CLASS = "run-history-card-body"
SCORE_ROW_CLASS = "run-history-card-score-row"
SCORE_CLASS = "run-history-card-score"
RESULT_CLASS = "run-history-card-result"
SESSION_CLASS = "run-history-card-session"
EMPTY_TITLE_CLASS = "run-history-card-empty-title"
EMPTY_MESSAGE_CLASS = "run-history-card-empty-message"


class CardBadge(Enum):
    """The one badge beside the card's score. The value is its Mantine color."""

    NEW_PB = "yellow"
    THRESHOLD_PASSED = "green"
    BELOW_THRESHOLD = "gray"


BADGE_TEXT = {
    CardBadge.NEW_PB: NEW_PB_TEXT,
    CardBadge.THRESHOLD_PASSED: THRESHOLD_PASSED_TEXT,
    CardBadge.BELOW_THRESHOLD: BELOW_THRESHOLD_TEXT,
}


@dataclass(frozen=True)
class LatestRun:
    """What the card says about the last run played, as the text it shows.

    ``run_id`` is the run's id as the run list keys its row and a run event
    names it. ``played_at`` is when the run ended, as the run's file names it,
    which the browser words as an age. ``result`` is the card's second line
    and ``session`` its third.
    """

    run_id: str
    scenario: str
    played_at: datetime
    score: str
    badge: CardBadge | None
    result: str
    session: str


def _badge(verdict: ThresholdVerdict | Unjudged, is_new_pb: bool) -> CardBadge | None:
    """Choose the badge: New PB whenever the run is one, else its verdict."""
    if is_new_pb:
        return CardBadge.NEW_PB
    if isinstance(verdict, ThresholdVerdict):
        return (
            CardBadge.THRESHOLD_PASSED if verdict.passed else CardBadge.BELOW_THRESHOLD
        )
    return None


def _new_pb_gain(score: float, previous_best: float, chased: Chased) -> str:
    """Word how far a new PB beat the previous best, as its toast does."""
    previous = format_score(previous_best)
    gain_by_pace = (
        percent_faster(chased.pace_constant, previous_best, score)
        if chased.pace_constant is not None
        else None
    )
    if gain_by_pace is not None:
        return f"{gain_by_pace:.1f}% faster than your previous best of {previous}"
    if previous_best > 0:
        gain = (score / previous_best - 1) * 100
        return f"Up {gain:.1f}% on your previous best of {previous}"
    # Zero has no percentage to give, and a negative one would read backwards.
    return f"Your previous best was {previous}"


def _comparison(
    score: float,
    chased: Chased,
    verdict: ThresholdVerdict | Unjudged,
    is_new_pb: bool,
) -> str | None:
    """Word the run against the PB it was chasing, or return None with nothing to say.

    The percentage is a fact about the run, so it shows whether or not the
    run was judged. Two kinds of run have none: a scenario's first run, and
    a run that is not a new PB and is compared by score with a previous best
    of zero or less.
    """
    previous_best = chased.previous_best
    if previous_best is None:
        return None
    if is_new_pb:
        return _new_pb_gain(score, previous_best, chased)
    measured = verdict
    if not isinstance(measured, ThresholdVerdict):
        # Nothing judges the run, so it is measured here against a goal of
        # 100 only for the percentage that comes back: the judging function
        # is the one place a percentage of a PB is worked out, by pace or by
        # score. Of the two display caps, the one that holds a miss
        # under its goal has no goal to hold it under. The other still
        # applies, and against 100 the two are the same cap: a run below the
        # PB shows at most 99.9%.
        measured = judge_run(score, previous_best, False, chased.pace_constant, 100.0)
    if not isinstance(measured, ThresholdVerdict):
        return None
    measure = "PB pace" if measured.by_pace else "PB"
    return f"{shown_percentage(measured):.1f}% of {measure}"


def _session_line(session: PlaySession, scenario: str, in_progress: bool) -> str:
    """Word the run's number in its session and the time spent on its scenario.

    The run is the session's last, so its number is how many of the session's
    runs were on its scenario. The time is the sum of the scenario's visits,
    each from its first run's start to its last run's end, so it includes
    the breaks between a visit's runs.

    A visit whose first run has no usable start is counted from that run's
    end, so a visit of one long run would add nothing and the time could
    read ``<1 min``. The line says the time is unknown then, and never gives
    a number.
    """
    visits = [
        visit
        for visit in split_into_scenario_visits(session)
        if visit.scenario == scenario
    ]
    number = sum(len(visit.runs) for visit in visits)
    which_session = "this session" if in_progress else "last session"
    if any(visit.runs[0].run_start is None for visit in visits):
        return f"Run {number} {which_session} · Time on this scenario unknown"
    seconds = sum((visit.end - visit.start).total_seconds() for visit in visits)
    return (
        f"Run {number} {which_session} · "
        f"{format_elapsed_duration(seconds)} on this scenario"
    )


def latest_run(
    all_runs: Iterable[RunData],
    goal_percentage: float | None,
    now: datetime,
    version_pace_basis: Callable[[str, str | None], PaceBasis | None],
) -> LatestRun | None:
    """Work out what the card says about the newest run in ``all_runs``.

    ``all_runs`` is a copy of every run in the run store, on every scenario.
    ``goal_percentage`` is ``None`` while the percentage is empty. ``now`` is
    the app's own clock, which decides whether the run's session is in
    progress. ``version_pace_basis`` answers for one version of one
    scenario. ``None`` with no runs.

    The newest run is the last run of the newest session, the run the run
    list names as the newest. It is judged as the list judges it: against
    the PB it was chasing, under its own version of the scenario.
    """
    runs = list(all_runs)
    sessions = split_into_play_sessions(runs)
    if not sessions:
        return None
    session = sessions[-1]
    run = session.runs[-1]
    scenario = run.scenario
    scenario_runs = in_play_order(
        scenario_run for scenario_run in runs if scenario_run.scenario == scenario
    )
    chased = what_runs_chased(
        scenario_runs, lambda version: version_pace_basis(scenario, version)
    )[run]
    verdict = judge_run(
        run.score,
        chased.previous_best,
        chased.is_new_sensitivity,
        chased.pace_constant,
        goal_percentage,
    )
    is_new_pb = run in new_high_score_runs(scenario_runs)

    accuracy = f"Accuracy {format_whole_percent(run.accuracy)}"
    comparison = _comparison(run.score, chased, verdict, is_new_pb)
    return LatestRun(
        run_id=run_id(run),
        scenario=scenario,
        played_at=run.datetime_object,
        score=format_score(run.score),
        badge=_badge(verdict, is_new_pb),
        result=accuracy if comparison is None else f"{comparison} · {accuracy}",
        session=_session_line(
            session,
            scenario,
            find_play_session_in_progress(sessions, now) is not None,
        ),
    )


def latest_run_from_store(
    score_threshold_percentage: float | str | None,
    now: datetime,
) -> LatestRun | None:
    """Work out what the card says from the run store.

    ``score_threshold_percentage`` is the percentage field's value as the
    browser sends it. The runs are copied from the store once, so the run,
    its session, and the PB it was chasing all come from the same moment.
    """
    return latest_run(
        get_all_runs(),
        normalize_score_threshold_percentage(score_threshold_percentage),
        now,
        get_version_pace_basis,
    )


# --- The card on a page --------------------------------------------------------


class LatestRunCardIds(NamedTuple):
    """The component ids one page gives its latest-run card.

    ``played_at`` is a store holding when the run ended, in epoch seconds, or
    nothing with no run. A script on the page words it into ``label``, the
    first line's words before the scenario's name, hidden with no run:
    ``time`` is the run's age in it and ``time_tooltip`` the age's hover.
    ``heading`` holds the scenario's name while it is the one selected, and
    ``body`` the lines under the first. ``scenario_button`` is the
    scenario's name while another scenario is selected: a button whose
    ``value`` is the name and whose click asks the page for that scenario.
    """

    played_at: str
    label: str
    time: str
    time_tooltip: str
    heading: str
    scenario_button: str
    body: str


class CardContent(NamedTuple):
    """What a page writes to its card, one field per prop it writes."""

    played_at: float | None
    heading: html.Span | None
    scenario_button: str | None
    scenario_button_value: str | None
    scenario_button_label: str | None
    body: list[Any]


def latest_run_card(ids: LatestRunCardIds) -> dmc.Box:
    """Build the card with nothing in it yet.

    The page's callbacks write what it shows. What they write is in the
    layout from the start and is never drawn again. A page must hold every
    input of a callback whose output it holds, so a scenario button that came
    and went with the card's text would call the callback it feeds each time
    it was put back. And the run's age, which a script writes, would come
    and go under the script if the server's answer drew it.
    """
    return dmc.Box(
        className=CARD_CLASS,
        children=[
            dcc.Store(id=ids.played_at),
            html.Div(
                className=HEADING_CLASS,
                children=[
                    # One item of the heading, with the age inline in it. The
                    # heading is a flex container, which drops a space between
                    # its items, and a screen reader would be handed the words
                    # on either side of the age run together.
                    html.Span(
                        [
                            f"{LATEST_RUN_LABEL} · ",
                            dmc.Tooltip(
                                dmc.Text(
                                    className=TIME_CLASS,
                                    id=ids.time,
                                    inherit=True,
                                    span=True,
                                    tabIndex=0,
                                ),
                                # dmc wraps the tooltip's target in a block
                                # box, which would break the line round it.
                                boxWrapperProps={"className": TIME_TARGET_CLASS},
                                events=TOOLTIP_EVENTS,
                                id=ids.time_tooltip,
                                label="",
                            ),
                            " · ",
                        ],
                        className=HEADING_LABEL_CLASS,
                        hidden=True,
                        id=ids.label,
                    ),
                    html.Span(id=ids.heading, className=HEADING_TEXT_CLASS),
                    html.Button(
                        id=ids.scenario_button,
                        className=SCENARIO_BUTTON_CLASS,
                        n_clicks=0,
                        type="button",
                    ),
                ],
            ),
            html.Div(id=ids.body, className=BODY_CLASS),
        ],
    )


def latest_run_card_content(
    shown: LatestRun | None,
    selected_scenario: str | None,
) -> CardContent:
    """Build what the card shows for a run, or for a run store with none.

    While the run's scenario is the one selected its name is plain text.
    While another is selected the name is the scenario button, which selects
    it.
    """
    if shown is None:
        return CardContent(
            played_at=None,
            heading=None,
            scenario_button=None,
            scenario_button_value=None,
            scenario_button_label=None,
            body=[
                html.Div(NO_RUNS_TEXT, className=EMPTY_TITLE_CLASS),
                html.Div(NO_RUNS_MESSAGE, className=EMPTY_MESSAGE_CLASS),
            ],
        )

    is_selected = shown.scenario == selected_scenario
    score_row: list[Any] = [html.Span(shown.score, className=SCORE_CLASS)]
    if shown.badge is not None:
        score_row.append(
            dmc.Badge(
                BADGE_TEXT[shown.badge],
                color=shown.badge.value,
                # The app's sentence case, where the badge's own style would
                # print capitals.
                tt="none",
                variant="light",
            )
        )
    return CardContent(
        played_at=shown.played_at.timestamp(),
        heading=(
            # The title gives the whole name where the card cuts it short.
            html.Span(shown.scenario, className=SCENARIO_CLASS, title=shown.scenario)
            if is_selected
            else None
        ),
        scenario_button=None if is_selected else shown.scenario,
        scenario_button_value=None if is_selected else shown.scenario,
        scenario_button_label=None if is_selected else f"Show {shown.scenario}",
        body=[
            html.Div(score_row, className=SCORE_ROW_CLASS),
            html.Div(shown.result, className=RESULT_CLASS),
            html.Div(shown.session, className=SESSION_CLASS),
        ],
    )
