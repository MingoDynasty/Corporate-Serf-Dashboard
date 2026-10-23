"""What the Run History page's latest-run card shows: the selected scenario's latest run.

``latest_run`` works out, from a copy of the run store, the selected
scenario's latest run and what the card says about it: when it was played,
its score, its verdict, how it measured up against the PB it was chasing, and
where it sits in its session. The rest of the module draws that in the card.

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
    NO_SCENARIO_TEXT,
    THRESHOLD_PASSED_TEXT,
    run_id,
)
from source.components.run_marks import Chased, new_pb_gain, what_runs_chased
from source.components.score_threshold import (
    ThresholdVerdict,
    Unjudged,
    judge_run,
    normalize_score_threshold_percentage,
    shown_percentage,
)
from source.kovaaks.data_models import RunData
from source.kovaaks.data_service import get_all_runs, new_high_score_runs
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
    format_percent,
    format_score,
    format_short_timestamp,
)

LATEST_RUN_LABEL = "Latest run"
# With no scenario selected and no runs at all. With Follow off a first run
# leaves the selection empty, so "will show here" would promise what the card
# does not do.
NO_RUNS_MESSAGE = "Play a scenario in KovaaK's. Select it to see its latest run."
NO_SCENARIO_RUNS_MESSAGE = (
    "Play this scenario in KovaaK's and your latest run will show here."
)

CARD_CLASS = "run-history-card"
HEADING_CLASS = "run-history-card-heading"
HEADING_TEXT_CLASS = "run-history-card-heading-text"
HEADING_LABEL_CLASS = "run-history-card-label"
# The run's age, with the hover affordance the playlist tables' Last played has.
TIME_CLASS = "cell-tooltip-affordance"
TIME_TARGET_CLASS = "run-history-card-time-target"
SCENARIO_CLASS = "run-history-card-scenario"
BODY_CLASS = "run-history-card-body"
SCORE_ROW_CLASS = "run-history-card-score-row"
SCORE_CLASS = "run-history-card-score"
RESULT_CLASS = "run-history-card-result"
SESSION_CLASS = "run-history-card-session"
EMPTY_TITLE_CLASS = "run-history-card-empty-title"
EMPTY_MESSAGE_CLASS = "run-history-card-empty-message"


# A card's age is worded in the browser, when the card is written and on every
# 30-second tick, as the playlist tables' Last played is, so it stays current
# on a page left open:
# during play the latest-run card's doubles as a break timer. The hover is the
# exact time in the shared format. With nothing to date, the words that hold
# the age are hidden, and the card's name before them stays. The latest-run
# card and the PB card both register it.
AGE_SCRIPT = """
    (seconds, _nIntervals) => {
        if (seconds === null || seconds === undefined) {
            return [true, "", ""];
        }
        const dagfuncs = window.dashAgGridFunctions;
        return [
            false,
            dagfuncs.relativeTime(seconds, ""),
            dagfuncs.absoluteTime(seconds, ""),
        ];
    }
    """


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
    """What the card says about the selected scenario's latest run, as the text it shows.

    ``run_id`` is the run's id as the run list keys its row and a run event
    names it. ``played_at`` is when the run ended, as the run's file names it,
    which the browser words as an age. ``result`` is the card's second line,
    ``session`` its third and ``time_on_scenario`` its fourth.
    """

    run_id: str
    scenario: str
    played_at: datetime
    score: str
    badge: CardBadge | None
    result: str
    session: str
    time_on_scenario: str


def _badge(verdict: ThresholdVerdict | Unjudged, is_new_pb: bool) -> CardBadge | None:
    """Choose the badge: New PB whenever the run is one, else its verdict."""
    if is_new_pb:
        return CardBadge.NEW_PB
    if isinstance(verdict, ThresholdVerdict):
        return (
            CardBadge.THRESHOLD_PASSED if verdict.passed else CardBadge.BELOW_THRESHOLD
        )
    return None


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
        return new_pb_gain(score, previous_best, chased)
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


def _which_session(
    sessions: list[PlaySession], session: PlaySession, now: datetime
) -> str:
    """Word which session a run is in, after its number.

    The newest session is "this session" while it is in progress and "last
    session" once it has ended. An older one is named as the run list names
    its row, by when it began, with the year where it is not this one. The
    word "session" stays inside the parentheses, or the time would read as
    the run's own.
    """
    if session is not sessions[-1]:
        return f"({format_short_timestamp(session.start, now.date())} session)"
    if find_play_session_in_progress(sessions, now) is not None:
        return "this session"
    return "last session"


def _session_lines(
    session: PlaySession, scenario: str, which_session: str
) -> tuple[str, str]:
    """Word the run's number in its session, then the time spent on its scenario.

    The run is its scenario's last in the session, so its number is how many
    of the session's runs were on its scenario. The time is the sum of the
    scenario's visits, each from its first run's start to its last run's
    end, so it includes the breaks between a visit's runs.

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
    run_line = f"Run {number} {which_session}"
    if any(visit.runs[0].run_start is None for visit in visits):
        return run_line, "Time on this scenario unknown"
    seconds = sum((visit.end - visit.start).total_seconds() for visit in visits)
    return run_line, f"{format_elapsed_duration(seconds)} on this scenario"


def latest_run(
    all_runs: Iterable[RunData],
    scenario: str | None,
    goal_percentage: float | None,
    now: datetime,
    version_pace_basis: Callable[[str, str | None], PaceBasis | None],
) -> LatestRun | None:
    """Work out what the card says about ``scenario``'s latest run in ``all_runs``.

    ``all_runs`` is a copy of every run in the run store, on every scenario.
    ``scenario`` is the selected one, or nothing. ``goal_percentage`` is
    ``None`` while the percentage is empty. ``now`` is the app's own clock,
    which decides whether the newest session is in progress and which year
    an older session's name leaves out. ``version_pace_basis`` answers for
    one version of one scenario. ``None`` with no scenario, or none of its
    runs.

    The scenario's latest run is its last run in the newest session that
    holds one. The sessions are split from every run, as the run list splits
    them, so the two agree on which run is newest, two that ended in the same
    second included. A run that lands late, older than the store's newest,
    is the card's run once it is newer than the scenario's latest. It is
    judged as the list judges it: against the PB it was chasing, under its
    own version of the scenario.
    """
    if not scenario:
        return None
    runs = list(all_runs)
    sessions = split_into_play_sessions(runs)
    for session in reversed(sessions):
        played = [run for run in session.runs if run.scenario == scenario]
        if played:
            break
    else:
        return None
    run = played[-1]
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

    accuracy = f"Accuracy {format_percent(run.accuracy)}"
    comparison = _comparison(run.score, chased, verdict, is_new_pb)
    session_line, time_line = _session_lines(
        session, scenario, _which_session(sessions, session, now)
    )
    return LatestRun(
        run_id=run_id(run),
        scenario=scenario,
        played_at=run.datetime_object,
        score=format_score(run.score),
        badge=_badge(verdict, is_new_pb),
        result=accuracy if comparison is None else f"{comparison} · {accuracy}",
        session=session_line,
        time_on_scenario=time_line,
    )


class StoreRuns(NamedTuple):
    """What the page reads from one copy of the run store.

    ``shown`` is what the card says about the selected scenario's latest run,
    or ``None``. ``newest_run_id`` is the id of the newest run on any
    scenario, the run the chart's ring and the run list's highlight mark, or
    ``None`` with no runs in the store.
    """

    shown: LatestRun | None
    newest_run_id: str | None


def latest_run_from_store(
    selected_scenario: str | None,
    score_threshold_percentage: float | str | None,
    now: datetime,
) -> StoreRuns:
    """Work out what the card says, and the newest run on any scenario, from the run store.

    ``score_threshold_percentage`` is the percentage field's value as the
    browser sends it. The runs are copied from the store once, so the run,
    its session, the PB it was chasing, and the newest run all come from the
    same moment.
    """
    runs = get_all_runs()
    return StoreRuns(
        shown=latest_run(
            runs,
            selected_scenario,
            normalize_score_threshold_percentage(score_threshold_percentage),
            now,
            get_version_pace_basis,
        ),
        newest_run_id=run_id(in_play_order(runs)[-1]) if runs else None,
    )


# --- The card on a page --------------------------------------------------------


class LatestRunCardIds(NamedTuple):
    """The component ids one page gives its latest-run card.

    ``played_at`` is a store holding when the run ended, in epoch seconds, or
    nothing with no run. A script on the page words it into ``label``, the
    first line's words between ``Latest run`` and the scenario's name, hidden
    with no run: ``time`` is the run's age in it and ``time_tooltip`` the
    age's hover. ``heading`` holds the run's scenario's name, and ``body``
    the lines under the first, or the card's empty state.
    """

    played_at: str
    label: str
    time: str
    time_tooltip: str
    heading: str
    body: str


class CardContent(NamedTuple):
    """What a page writes to its card, one field per prop it writes."""

    played_at: float | None
    heading: html.Span | None
    body: list[Any]


def latest_run_card(ids: LatestRunCardIds) -> dmc.Paper:
    """Build the card with nothing in it yet.

    The page's callbacks write what it shows. The run's age, which a script
    writes, is in the layout from the start: it would come and go under the
    script if the server's answer drew it.
    """
    return dmc.Paper(
        withBorder=True,
        radius="sm",
        className=CARD_CLASS,
        children=[
            dcc.Store(id=ids.played_at),
            html.Div(
                className=HEADING_CLASS,
                children=[
                    # One item of the heading, with the age inline in it. The
                    # heading is a flex container, which drops a space between
                    # its items, and a screen reader would be handed the words
                    # on either side of the age run together. The card's name
                    # stays with no run, as the PB card's does, and only the
                    # words that hold the age are hidden.
                    html.Span(
                        [
                            LATEST_RUN_LABEL,
                            html.Span(
                                [
                                    " · ",
                                    dmc.Tooltip(
                                        dmc.Text(
                                            className=TIME_CLASS,
                                            id=ids.time,
                                            inherit=True,
                                            span=True,
                                            tabIndex=0,
                                        ),
                                        # dmc wraps the tooltip's target in a
                                        # block box, which would break the
                                        # line round it.
                                        boxWrapperProps={
                                            "className": TIME_TARGET_CLASS
                                        },
                                        events=TOOLTIP_EVENTS,
                                        id=ids.time_tooltip,
                                        label="",
                                    ),
                                    " · ",
                                ],
                                hidden=True,
                                id=ids.label,
                            ),
                        ],
                        className=HEADING_LABEL_CLASS,
                    ),
                    html.Span(id=ids.heading, className=HEADING_TEXT_CLASS),
                ],
            ),
            html.Div(id=ids.body, className=BODY_CLASS),
        ],
    )


def _empty_body(selected_scenario: str | None, store_has_runs: bool) -> list[html.Div]:
    """Build what the card says with no run to report.

    The selection decides first, as on the PB card: a playlist filter lists
    its scenarios before any is played, so a scenario can be selected in a
    store with no runs, and the card then speaks of it.
    """
    if selected_scenario:
        message = NO_SCENARIO_RUNS_MESSAGE
    elif store_has_runs:
        return [html.Div(NO_SCENARIO_TEXT, className=EMPTY_TITLE_CLASS)]
    else:
        message = NO_RUNS_MESSAGE
    return [
        html.Div(NO_RUNS_TEXT, className=EMPTY_TITLE_CLASS),
        html.Div(message, className=EMPTY_MESSAGE_CLASS),
    ]


def latest_run_card_content(
    shown: LatestRun | None,
    selected_scenario: str | None,
    store_has_runs: bool,
) -> CardContent:
    """Build what the card shows for the selected scenario's latest run, or its empty state.

    ``store_has_runs`` tells the two states with no scenario selected apart:
    a store with no runs reads the first run's two steps, and a store with
    runs reads that no scenario is selected.
    """
    if shown is None:
        return CardContent(
            played_at=None,
            heading=None,
            body=_empty_body(selected_scenario, store_has_runs),
        )

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
        # The title gives the whole name where the card cuts it short.
        heading=html.Span(
            shown.scenario, className=SCENARIO_CLASS, title=shown.scenario
        ),
        body=[
            html.Div(score_row, className=SCORE_ROW_CLASS),
            html.Div(shown.result, className=RESULT_CLASS),
            html.Div(shown.session, className=SESSION_CLASS),
            html.Div(shown.time_on_scenario, className=SESSION_CLASS),
        ],
    )
