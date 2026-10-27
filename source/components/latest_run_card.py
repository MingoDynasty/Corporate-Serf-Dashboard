"""What the Run History page's latest-run card shows: the selected scenario's latest run.

``latest_run`` works out, from a copy of the run store, the selected
scenario's latest run and what the card says about it: when it was played,
its score, its verdict, how it measured up against the typical score at its
session's start and the PB it was chasing, where it sits in its session, and
its sensitivity and accuracy. The rest of the module draws that in the card.

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
from source.kovaaks.pace import percent_faster
from source.kovaaks.play_sessions import (
    PlaySession,
    find_play_session_in_progress,
    in_play_order,
    split_into_play_sessions,
    split_into_scenario_visits,
)
from source.kovaaks.playlist_scenarios_service import personal_best_cm360
from source.kovaaks.time_scored_service import (
    PaceBasis,
    eligible_pace_constant,
    get_version_pace_basis,
)
from source.kovaaks.typical_score import (
    NOT_RECENT_TEXT,
    TypicalScore,
    format_typical_score,
    typical_score_at_session_start,
    typical_score_recency,
)
from source.utilities.utilities import (
    format_elapsed_duration,
    format_percent,
    format_score,
    format_short_timestamp,
)

LATEST_RUN_LABEL = "Latest run"
TYPICAL_BASIS = "typical at session start"
TYPICAL_HOVER_LEAD = "Typical score when this run's session began: "
TYPICAL_HOVER_OLD = (
    "Fewer than 10 of its runs were from the 30 days before the session "
    "began, so it may have been out of date."
)
# With no scenario selected and no runs at all. With Follow off a first run
# leaves the selection empty, so "will show here" would promise what the card
# does not do.
NO_RUNS_MESSAGE = "Play a scenario in KovaaK's. Select it to see its latest run."
NO_SCENARIO_RUNS_MESSAGE = (
    "Play this scenario in KovaaK's and your latest run will show here."
)

CARD_CLASS = "run-history-card"
HEADING_CLASS = "run-history-card-heading"
# The run's age, with the hover affordance the playlist tables' Last played has.
TIME_CLASS = "cell-tooltip-affordance"
TIME_TARGET_CLASS = "run-history-card-time-target"
BODY_CLASS = "run-history-card-body"
SCORE_ROW_CLASS = "run-history-card-score-row"
SCORE_CLASS = "run-history-card-score"
WORD_END_CLASS = "run-history-card-word-end"
BADGE_CLASS = "run-history-card-badge"
RESULT_CLASS = "run-history-card-result"
# The clock after a typical value that isn't recent, as the scenario table
# draws it, and the words a screen reader hears in its place.
OLD_MARK_CLASS = "typical-old-mark"
HIDDEN_CLASS = "visually-hidden"
TYPICAL_HOVER_CLASS = "run-history-card-typical-hover"
TYPICAL_HOVER_WIDTH = 360
_ARIA_HIDDEN: dict[str, Any] = {"aria-hidden": "true"}
# The lines under the comparison, which support the score.
QUIET_CLASS = "run-history-card-quiet"
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
class TypicalPhrase:
    """The run against its scenario's typical score at session start, as the card words it.

    ``text`` is the phrase. ``typical`` is the value it was measured against,
    formatted as the scenario table formats a typical score, for its hover.
    ``not_recent`` is whether the value wasn't recent when the session began.
    """

    text: str
    typical: str
    not_recent: bool


@dataclass(frozen=True)
class LatestRun:
    """What the card says about the selected scenario's latest run, as the text it shows.

    ``run_id`` is the run's id as the run list keys its row and a run event
    names it. ``played_at`` is when the run ended, as the run's file names it,
    which the browser words as an age. Under the score, the comparison line
    joins ``typical``, the run against the typical score at its session's
    start, and ``pb_comparison``, the run against the PB it was chasing; each
    is ``None`` with nothing to say, and with neither the line is left out.
    ``session`` is its number in its session and the time on its scenario;
    ``sensitivity_and_accuracy`` is the last line.
    """

    run_id: str
    played_at: datetime
    score: str
    badge: CardBadge | None
    typical: TypicalPhrase | None
    pb_comparison: str | None
    session: str
    sensitivity_and_accuracy: str


def _badge(verdict: ThresholdVerdict | Unjudged, is_new_pb: bool) -> CardBadge | None:
    """Choose the badge: New PB whenever the run is one, else its verdict."""
    if is_new_pb:
        return CardBadge.NEW_PB
    if isinstance(verdict, ThresholdVerdict):
        return (
            CardBadge.THRESHOLD_PASSED if verdict.passed else CardBadge.BELOW_THRESHOLD
        )
    return None


def _pb_comparison(
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


def _measured_from(percent: float, ahead: str, behind: str) -> str:
    """Word a percentage from the typical score at session start, to one decimal."""
    shown = f"{abs(percent):.1f}"
    if shown == "0.0":
        return f"Matches {TYPICAL_BASIS}"
    return f"{shown}% {ahead if percent > 0 else behind} {TYPICAL_BASIS}"


def _typical_phrase(
    run: RunData,
    value: TypicalScore | None,
    session: PlaySession,
    basis: PaceBasis | None,
) -> TypicalPhrase | None:
    """Word the run against the typical score its session began with, or return None.

    ``value`` is that typical score, ``None`` with no run before the session.
    ``basis`` is what the run's own version says of its pace. The run is
    measured by pace when every run behind the value is of that version and
    both times are positive, as the scenario table's Typical Rank decides it,
    whatever measured the run against its PB; otherwise by score, which has
    nothing to say of a typical score of zero or less. Whether the value was
    recent is judged when the session began, not when the card is read.
    """
    if value is None or value.median is None:
        return None
    typical = value.median
    constant = eligible_pace_constant(basis, *value.runs, run)
    faster = (
        percent_faster(constant, typical, run.score) if constant is not None else None
    )
    if faster is not None:
        text = _measured_from(faster, "faster than", "slower than")
    elif typical > 0:
        text = _measured_from((run.score - typical) / typical * 100, "above", "below")
    else:
        return None
    return TypicalPhrase(
        text=text,
        typical=format_typical_score(typical, value.runs),
        not_recent=not typical_score_recency(value, session.start).recent,
    )


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


def _session_line(session: PlaySession, scenario: str, which_session: str) -> str:
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
        return f"{run_line} · Time on this scenario unknown"
    seconds = sum((visit.end - visit.start).total_seconds() for visit in visits)
    return f"{run_line} · {format_elapsed_duration(seconds)} on this scenario"


def sensitivity_and_accuracy(run: RunData) -> str:
    """Word a run's sensitivity and its hit accuracy: the last line of the PB card and this one.

    The sensitivity is the scenario table's PB cm/360, formatted as that
    column formats it, and left out where the run's is unknown. The accuracy
    is the hit accuracy, as the table's PB Accuracy and the run list show a
    run's.
    """
    accuracy = f"Accuracy {format_percent(run.accuracy)}"
    cm360 = personal_best_cm360(run)
    if cm360 is None:
        return accuracy
    return f"{format_score(cm360)} cm/360 · {accuracy}"


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
    own version of the scenario. A run that isn't a new PB is also measured
    against its scenario's typical score as it stood when the run's session
    began; a new PB beats every earlier run, so that could only read above.
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
    typical = (
        None
        if is_new_pb
        else _typical_phrase(
            run,
            typical_score_at_session_start(scenario_runs, sessions, session),
            session,
            version_pace_basis(scenario, run.scenario_hash),
        )
    )

    return LatestRun(
        run_id=run_id(run),
        played_at=run.datetime_object,
        score=format_score(run.score),
        badge=_badge(verdict, is_new_pb),
        typical=typical,
        pb_comparison=_pb_comparison(run.score, chased, verdict, is_new_pb),
        session=_session_line(
            session, scenario, _which_session(sessions, session, now)
        ),
        sensitivity_and_accuracy=sensitivity_and_accuracy(run),
    )


class StoreRuns(NamedTuple):
    """What the page reads from one copy of the run store.

    ``shown`` is what the card says about the selected scenario's latest run,
    or ``None``. ``newest_run_id`` is the id of the newest run on any
    scenario, or ``None`` with no runs in the store. It distinguishes a
    missing selection from a store with no runs for the card's empty state.
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
    first line's words after ``Latest run``, hidden with no run: ``time`` is
    the run's age in it and ``time_tooltip`` the age's hover. ``body`` holds
    the lines under the first, or the card's empty state.
    """

    played_at: str
    label: str
    time: str
    time_tooltip: str
    body: str


class CardContent(NamedTuple):
    """What a page writes to its card, one field per prop it writes."""

    played_at: float | None
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
            # Not a flex container, as the PB card's first line is not: that
            # would drop the space before the age and hand a screen reader the
            # words run together. The card's name stays with no run, as the PB
            # card's does, and only the words that hold the age are hidden.
            html.Div(
                className=HEADING_CLASS,
                children=[
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
                                # dmc wraps the tooltip's target in a block
                                # box, which would break the line round it.
                                boxWrapperProps={"className": TIME_TARGET_CLASS},
                                events=TOOLTIP_EVENTS,
                                id=ids.time_tooltip,
                                label="",
                            ),
                        ],
                        hidden=True,
                        id=ids.label,
                    ),
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


def _typical_target(phrase: TypicalPhrase) -> dmc.Tooltip:
    """Draw the typical phrase with its hover, and the clock on an old value.

    The clock is the scenario table's, hidden from a screen reader, which
    hears the table's ``Not recent`` instead. Both sit inside the hover's
    target, so pointing at or focusing the clock opens the phrase's hover.
    """
    target: list[Any] = [phrase.text]
    label: list[Any] = [html.P(f"{TYPICAL_HOVER_LEAD}{phrase.typical}")]
    if phrase.not_recent:
        target += [
            html.Span(className=OLD_MARK_CLASS, **_ARIA_HIDDEN),
            html.Span(f", {NOT_RECENT_TEXT}", className=HIDDEN_CLASS),
        ]
        label.append(html.P(TYPICAL_HOVER_OLD))
    return dmc.Tooltip(
        html.Span(target, className=TIME_CLASS, tabIndex=0),
        # dmc wraps the target in a block box, which would break the line
        # round it.
        boxWrapperProps={"className": TIME_TARGET_CLASS},
        classNames={"tooltip": TYPICAL_HOVER_CLASS},
        events=TOOLTIP_EVENTS,
        label=label,
        maw=TYPICAL_HOVER_WIDTH,
        multiline=True,
    )


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
            played_at=None, body=_empty_body(selected_scenario, store_has_runs)
        )

    # The score ends on a space a screen reader reads and the eye does not
    # see: the score row is a flex container, which drops the space between
    # the score and the badge, and the two would be handed over as one word.
    score_row: list[Any] = [
        html.Span(
            [shown.score, html.Span(" ", className=WORD_END_CLASS)],
            className=SCORE_CLASS,
        )
    ]
    if shown.badge is not None:
        score_row.append(
            dmc.Badge(
                BADGE_TEXT[shown.badge],
                className=BADGE_CLASS,
                style={
                    "--run-history-card-badge-color": (
                        f"var(--mantine-color-{shown.badge.value}-6)"
                    )
                },
                # The app's sentence case, where the badge's own style would
                # print capitals.
                tt="none",
            )
        )
    body: list[Any] = [html.Div(score_row, className=SCORE_ROW_CLASS)]
    comparison: list[Any] = []
    if shown.typical is not None:
        comparison.append(_typical_target(shown.typical))
    if shown.pb_comparison is not None:
        comparison.append(
            f" · {shown.pb_comparison}" if comparison else shown.pb_comparison
        )
    if comparison:
        body.append(html.Div(comparison, className=RESULT_CLASS))
    body.append(html.Div(shown.session, className=QUIET_CLASS))
    body.append(html.Div(shown.sensitivity_and_accuracy, className=QUIET_CLASS))
    return CardContent(played_at=shown.played_at.timestamp(), body=body)
