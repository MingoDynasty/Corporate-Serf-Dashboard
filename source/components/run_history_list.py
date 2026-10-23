"""What the Run History page's run list shows, in either of its two views.

Under This scenario, ``build_run_list`` turns a copy of the run store into a
flat list of row records: a row per session, and under it that session's runs
of the scenario, with a divider where the scenario was left and returned to
and a date header where a run is on another date than its session began.
Under All scenarios, ``build_session_tree`` lists every session whole: under a
session a row per visit, in the order they were played, and under each its
runs. The page sends the records to the browser as data, and a script draws
them in a grid.

The list is worked out from the run store each time, never from the batches
of new runs a page is sent: two open tabs race for each batch, and a list
built from batches would miss runs in one of them.

Which rows are open is the browser's alone. The records only name the newest
run and the rows it opens, and the script applies that once per run in each
view.
"""

import json
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from typing import Any, NamedTuple, TypedDict

import dash_ag_grid as dag
import dash_mantine_components as dmc
from dash import (
    ALL,
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    dcc,
    html,
    no_update,
)

from source.components.columns_menu import (
    COLUMNS_MENU_GRID_OPTIONS,
    MenuChoice,
    MenuColumn,
    choice_checkbox_id,
    column_checkbox_id,
    columns_menu,
    columns_menu_sink,
    register_columns_menu,
)
from source.components.run_marks import RunMark, mark_runs
from source.components.score_threshold import (
    ThresholdVerdict,
    Unjudged,
    normalize_score_threshold_percentage,
)
from source.kovaaks.data_models import RunData, run_id
from source.kovaaks.data_service import get_all_runs
from source.kovaaks.play_sessions import (
    PlaySession,
    ScenarioVisit,
    find_play_session_in_progress,
    in_play_order,
    split_into_play_sessions,
    split_into_scenario_visits,
)
from source.kovaaks.time_scored_service import get_version_pace_basis
from source.utilities.utilities import (
    format_elapsed_duration,
    format_percent,
    format_score,
    format_short_date,
    format_short_timestamp,
    format_time_of_day,
)

# How many sessions each view loads at first, and how many more each press of
# Show older sessions adds to the view it is pressed in.
SESSIONS_PER_LOAD = 30

# The list's two views, as the switch above it names them. The browser
# remembers the switch under its id, against the default it was drawn with,
# so the values and the default are chosen once.
VIEW_SCENARIO = "scenario"
VIEW_ALL = "all"
LIST_VIEW_DEFAULT = VIEW_SCENARIO
LIST_VIEW_OPTIONS = [
    {"value": VIEW_SCENARIO, "label": "This scenario"},
    {"value": VIEW_ALL, "label": "All scenarios"},
]

# The kinds of row. A session row and the rows under it share the session
# row's id as ``sid``, which is how the script hides a closed session's rows.
# Under All scenarios the rows under a scenario row also carry its id as
# ``vid``, and show only while both rows are open.
SESSION_ROW = "session"
SCENARIO_ROW = "scenario"
RUN_ROW = "run"
DIVIDER_ROW = "divider"
DATE_ROW = "date"
NOTE_ROW = "note"
MORE_ROW = "more"
MORE_ROW_ID = "more"

NO_SCENARIO_TEXT = "No scenario selected"
NO_RUNS_TEXT = "No runs yet"
NOT_PLAYED_TEXT = "Not played in this session"
SHOW_OLDER_SESSIONS_LABEL = "Show older sessions"
IN_PROGRESS_LABEL = "In progress"
SESSION_LENGTH_HELP = (
    "The length runs from the first run to the last run. It doesn't count the "
    "time since your last run."
)
ALL_SCENARIOS_HEADING = "All scenarios"
ALL_SCENARIOS_GRID_NAME = "Runs of all scenarios, by session"
# A scenario row's name is a button that selects the scenario, and a press says
# what the dropdown now holds.
SHOW_SCENARIO_LABEL = "Show {scenario}"
SELECTED_SCENARIO_TEXT = "Selected scenario: {scenario}"
# The figures of a row that stands for one scenario's runs, while Median and
# best is on: in the row's line ahead of its count. Never worded as typical,
# usual, average, or normal: it describes the runs under the row and compares
# nothing. Under This scenario the script draws a session row's words in
# columns, so it is handed them alone.
MEDIAN_LABEL = "Median"
BEST_LABEL = "Best"
SCORE_LABEL = "Score"
MEDIAN_AND_BEST_TEXT = f"{MEDIAN_LABEL} {{median}} · {BEST_LABEL} {{best}}"
ONE_SCORE_TEXT = f"{SCORE_LABEL} {{score}}"
THRESHOLD_PASSED_TEXT = "Threshold passed"
BELOW_THRESHOLD_TEXT = "Below threshold"
NEW_PB_TEXT = "New PB"
# What a blank cell says on hover, and to a screen reader, for each reason
# nothing judges a run. Unknown is not a miss, so each says why.
UNJUDGED_TEXT = {
    Unjudged.NO_PERCENTAGE_SET: "Not judged. No score threshold percentage is set.",
    Unjudged.FIRST_RUN: (
        "Not judged. A scenario's first run, and the first run at a new "
        "sensitivity, aren't judged against the score threshold."
    ),
    Unjudged.NO_PERCENTAGE_TO_JUDGE_BY: (
        "Not judged. Your personal best before this run was zero or less, so "
        "there is no percentage to judge by."
    ),
}


class FigureColumns(TypedDict):
    """The widest text each part of This scenario's figure columns holds.

    The script makes each part as wide as its text here, so the columns line
    up across the session rows. Taken over every session the view can list,
    loaded or not, so Show older sessions never moves a column.

    ``median`` and ``best`` are each a whole number and its decimals, either
    of them ``""`` where no session has one. Best's column also holds a
    one-run session's score. ``count`` is the widest count of every session
    row, including the newest. ``one_run`` tells whether any session's
    figures are one run's score, so Best's label has room for Score.
    """

    median: list[str]
    best: list[str]
    count: str | None
    one_run: bool


class RunListModel(TypedDict):
    """Everything the browser is sent to draw the list in one view.

    ``rows`` is in the order the list shows them, the first row first, and
    ``view`` is the view they are for. ``newest_run`` is the id of the newest
    run in the whole run store, named even when there is nothing to list,
    and ``forced_open`` the ids of the rows that run opens in this view. Each
    view keeps a mark in the script, the newest run whose rows it has
    opened, so a row the player closed is not reopened by a later change of
    scenario or of view. ``session_limit`` is how many sessions this view's
    rows were loaded up to, which the script adds to when older ones are
    asked for. ``columns`` is what the figure columns under This scenario are
    sized by, and ``None`` in the other view or with nothing to list.
    ``empty`` is the text shown in place of the list when there is nothing to
    list, and ``None`` otherwise.
    """

    rows: list[dict[str, Any]]
    view: str
    newest_run: str | None
    forced_open: list[str]
    session_limit: int
    columns: FigureColumns | None
    heading: str
    grid_name: str
    empty: str | None


def empty_run_list(
    text: str,
    *,
    view: str = VIEW_SCENARIO,
    newest_run: str | None = None,
) -> RunListModel:
    """Build the model of a list with nothing to list, and the text that says so.

    ``newest_run`` is the store's newest run, when the store has one. The
    script starts each view's mark from the first model a visit draws, so a
    list with nothing to list still has to name it.
    """
    return {
        "rows": [],
        "view": view,
        "newest_run": newest_run,
        "forced_open": [],
        "session_limit": SESSIONS_PER_LOAD,
        "columns": None,
        "heading": "",
        "grid_name": "",
        "empty": text,
    }


def _count(count: int, noun: str) -> str:
    """Word a count with its noun: ``1 run``, ``47 runs``, ``1,204 runs``."""
    return f"{count:,} {noun}" if count == 1 else f"{count:,} {noun}s"


def _check_text(mark: RunMark) -> str:
    """Word a run's verdict, or the reason it has none."""
    if isinstance(mark.verdict, ThresholdVerdict):
        return THRESHOLD_PASSED_TEXT if mark.verdict.passed else BELOW_THRESHOLD_TEXT
    return UNJUDGED_TEXT[mark.verdict]


def _figures(runs: Iterable[RunData]) -> str | None:
    """Word the median and the best score of the runs under a row, or ``None``.

    The median is the middle score, or the mean of the two middle scores when
    their number is even. One run's figures are that run's score, and a row
    with no run has none.
    """
    scores = [run.score for run in runs]
    if not scores:
        return None
    if len(scores) == 1:
        return ONE_SCORE_TEXT.format(score=format_score(scores[0]))
    return MEDIAN_AND_BEST_TEXT.format(
        median=format_score(statistics.median(scores)),
        best=format_score(max(scores)),
    )


def _split_score(score: float) -> list[str]:
    """Split a score as it reads at its decimal point: ``["17,080", ".5"]``.

    A score with no decimals has none to split off: ``["17,080", ""]``.
    """
    whole, point, decimals = format_score(score).partition(".")
    return [whole, point + decimals]


def _figure_parts(runs: Sequence[RunData]) -> dict[str, list[str]] | None:
    """Split a session row's figures for its columns under This scenario, or ``None``.

    Two or more runs give a ``median`` and a ``best``, and one run gives its
    ``score``, which the list draws in Best's column under its own label. A
    row with no run has no figures. The values are the ones ``_figures``
    words, each split at its decimal point.
    """
    scores = [run.score for run in runs]
    if not scores:
        return None
    if len(scores) == 1:
        return {"score": _split_score(scores[0])}
    return {
        "median": _split_score(statistics.median(scores)),
        "best": _split_score(max(scores)),
    }


def _widest(texts: Iterable[str]) -> str:
    """Return the text that draws widest: the most characters, then the most digits.

    A column's texts differ only in their digits, their separators, and a
    count's plural s, and the list draws every digit one width, wider than
    any of those. So the text this picks is the one the browser draws widest.
    """
    return max(
        texts, key=lambda text: (len(text), sum(map(str.isdigit, text))), default=""
    )


def _figure_columns(
    figures: Sequence[dict[str, list[str]] | None], counts: Sequence[str]
) -> FigureColumns:
    """Find the widest text of each part of the figure columns.

    ``figures`` is every listed session's ``_figure_parts``, and ``counts``
    is every listed session's count.
    """
    medians = [parts["median"] for parts in figures if parts and "median" in parts]
    bests = [parts.get("best") or parts["score"] for parts in figures if parts]
    return {
        "median": [_widest(m[0] for m in medians), _widest(m[1] for m in medians)],
        "best": [_widest(b[0] for b in bests), _widest(b[1] for b in bests)],
        "count": _widest(counts) if counts else None,
        "one_run": any(parts and "score" in parts for parts in figures),
    }


# A run row's id is this and the run's id. The script finds the row of a
# view's mark by it.
RUN_ROW_ID_PREFIX = "r:"


def _fov_text(run: RunData) -> str:
    """Write a run's FOV as the player typed it, then its scale if the file names one.

    A whole number drops its ``.0``, as the game's own setting reads.
    """
    if run.fov is None:
        return ""
    number = str(int(run.fov)) if run.fov.is_integer() else str(run.fov)
    return f"{number} {run.fov_scale}" if run.fov_scale else number


def _latest_scenario_run_id(
    sessions: Sequence[PlaySession], scenario: str | None
) -> str | None:
    """Find the selected scenario's latest run in the same order as the card."""
    return next(
        (
            run_id(run)
            for session in reversed(sessions)
            for run in reversed(session.runs)
            if run.scenario == scenario
        ),
        None,
    )


def _run_row(
    run: RunData,
    number: int,
    session_id: str,
    mark: RunMark,
    highlighted_run: str | None,
) -> dict:
    return {
        "id": f"{RUN_ROW_ID_PREFIX}{run_id(run)}",
        "kind": RUN_ROW,
        "sid": session_id,
        # The selected scenario's latest run, as on the card and chart.
        "latest": run_id(run) == highlighted_run,
        "n": number,
        "time": format_time_of_day(run.datetime_object),
        "score": format_score(run.score),
        "passed": mark.passed,
        "check_text": _check_text(mark),
        "new_pb": mark.is_new_pb,
        "accuracy": format_percent(run.accuracy),
        "shots": "" if run.shots_fired is None else f"{run.shots_fired:,}",
        "reloads": "" if run.reloads is None else f"{run.reloads:,}",
        "sens": f"{run.horizontal_sens} {run.sens_scale}",
        "fov": _fov_text(run),
        "avg_fps": "" if run.avg_fps is None else f"{run.avg_fps:,.0f}",
    }


def _session_child_rows(  # noqa: PLR0913
    session: PlaySession,
    scenario: str,
    session_id: str,
    today: date,
    marks: Mapping[RunData, RunMark],
    highlighted_run: str | None,
) -> list[dict]:
    """Build the rows under one session row, in the order the list shows them.

    The scenario's runs are numbered in the order they were played and listed
    newest first. A divider sits between two runs the scenario was left
    between, and counts the runs played on other scenarios meanwhile.

    A run row shows a time of day alone, and the session's name gives only
    the date the session began. So once any listed run is on another date,
    every date among the listed runs gets a header, the session's own date
    included: a run's date is the date it ended on. Where a header and a
    divider fall between the same two runs, the divider comes first, so the
    header sits directly above the runs it names.
    """
    # Oldest first: each of the scenario's runs, and before a run the runs
    # played on other scenarios since the scenario's last one.
    played: list[tuple[RunData, list[RunData]]] = []
    elsewhere: list[RunData] = []
    for visit in split_into_scenario_visits(session):
        if visit.scenario != scenario:
            # Runs before the scenario's first visit are not a return to it.
            if played:
                elsewhere.extend(visit.runs)
            continue
        for run in visit.runs:
            played.append((run, elsewhere))
            elsewhere = []

    if not played:
        return [
            {
                "id": f"e:{session_id}",
                "kind": NOTE_ROW,
                "sid": session_id,
                "text": NOT_PLAYED_TEXT,
            }
        ]

    began_on = session.start.date()
    dated = any(run.datetime_object.date() != began_on for run, _ in played)
    rows: list[dict] = []
    for index in range(len(played) - 1, -1, -1):
        run, _ = played[index]
        ended_on = run.datetime_object.date()
        newer = played[index + 1] if index + 1 < len(played) else None
        if newer is not None and newer[1]:
            scenarios_elsewhere = {other.scenario for other in newer[1]}
            rows.append(
                {
                    "id": f"g:{run_id(newer[0])}",
                    "kind": DIVIDER_ROW,
                    "sid": session_id,
                    "text": (
                        f"{_count(len(newer[1]), 'run')} on "
                        f"{_count(len(scenarios_elsewhere), 'other scenario')}"
                    ),
                }
            )
        if dated and (newer is None or newer[0].datetime_object.date() != ended_on):
            rows.append(
                {
                    "id": f"d:{session_id}:{ended_on.isoformat()}",
                    "kind": DATE_ROW,
                    "sid": session_id,
                    "text": format_short_date(ended_on, today),
                }
            )
        rows.append(_run_row(run, index + 1, session_id, marks[run], highlighted_run))
    return rows


def build_run_list(
    all_runs: Iterable[RunData],
    scenario: str,
    session_limit: int,
    now: datetime,
    marks: Mapping[RunData, RunMark],
) -> RunListModel:
    """Build the list of one scenario's runs, grouped by session.

    ``all_runs`` is a copy of every run in the run store, on every scenario:
    a session row counts all of a session's runs, and a divider counts runs
    on other scenarios. ``session_limit`` is how many sessions to load.
    ``now`` is the app's own clock, which decides whether the newest session
    is in progress and which year a date leaves out. ``marks`` holds a mark
    for every run of the scenario.

    Sessions are listed newest first, and only those that hold a run of the
    scenario. The newest session is the exception: it is always the first
    row, in progress or not, even when the scenario was not played in it.

    A session has no stored identity, so its row is keyed by its first run.
    A late run can join a session, and a run can become a session's first,
    which gives that session's row a new id.
    """
    sessions = split_into_play_sessions(all_runs)
    if not sessions:
        return empty_run_list(NO_RUNS_TEXT)

    newest_session = sessions[-1]
    newest_run = run_id(newest_session.runs[-1])
    highlighted_run = _latest_scenario_run_id(sessions, scenario)
    in_progress = find_play_session_in_progress(sessions, now) is not None
    today = now.date()
    # Each session with its place among all sessions, counting back from the
    # newest, which its count's link loads All scenarios up to, and its runs
    # of the scenario.
    listed = [
        (place, session, played)
        for place, session in enumerate(reversed(sessions), start=1)
        if (played := [run for run in session.runs if run.scenario == scenario])
        or session is newest_session
    ]
    figures = [_figure_parts(played) for _, _, played in listed]
    counts = [
        f"{len(played):,} of {_count(len(session.runs), 'run')}"
        for _, session, played in listed
    ]

    rows: list[dict] = []
    for index, (place, session, _) in enumerate(listed[:session_limit]):
        session_id = f"s:{run_id(session.runs[0])}"
        is_first_row = session is newest_session
        rows.append(
            {
                "id": session_id,
                "kind": SESSION_ROW,
                "sid": session_id,
                "name": format_short_timestamp(session.start, today),
                "in_progress": is_first_row and in_progress,
                "counts": counts[index],
                "place": place,
                "figures": figures[index],
            }
        )
        rows.extend(
            _session_child_rows(
                session, scenario, session_id, today, marks, highlighted_run
            )
        )
    if len(listed) > session_limit:
        rows.append(_more_row())

    scenario_run_count = sum(
        run.scenario == scenario for session in sessions for run in session.runs
    )
    return {
        "rows": rows,
        "view": VIEW_SCENARIO,
        "newest_run": newest_run,
        "forced_open": [rows[0]["id"]],
        "session_limit": session_limit,
        "columns": _figure_columns(figures, counts),
        "heading": f"{scenario} · {_count(scenario_run_count, 'run')}",
        "grid_name": f"Runs of {scenario}, by session",
        "empty": None,
    }


def _more_row() -> dict:
    return {
        "id": MORE_ROW_ID,
        "kind": MORE_ROW,
        "sid": MORE_ROW_ID,
        "text": SHOW_OLDER_SESSIONS_LABEL,
    }


def _visit_rows(  # noqa: PLR0913
    visit: ScenarioVisit,
    number: int,
    run_numbers: Mapping[RunData, int],
    session_id: str,
    began_on: date,
    today: date,
    selected: str | None,
    marks: Mapping[RunData, RunMark],
    highlighted_run: str | None,
) -> list[dict]:
    """Build one visit's scenario row and the rows under it, as the tree shows them.

    The runs are listed newest first, each numbered among its scenario's runs
    in the session. A date header is the built list's rule asked of this
    visit alone: once any of its runs is on another date than the session
    began, every date among its runs gets a header, the session's own
    included. A run's date is the date it ended on.
    """
    visit_id = f"v:{run_id(visit.runs[0])}"
    selected_here = visit.scenario == selected
    rows: list[dict] = [
        {
            "id": visit_id,
            "kind": SCENARIO_ROW,
            "sid": session_id,
            "name": visit.scenario,
            "number": number,
            "counts": _count(len(visit.runs), "run"),
            "new_pb": any(marks[run].is_new_pb for run in visit.runs),
            "figures": _figures(visit.runs),
            "sel": selected_here,
            "name_label": SHOW_SCENARIO_LABEL.format(scenario=visit.scenario),
            "selected_text": SELECTED_SCENARIO_TEXT.format(scenario=visit.scenario),
        }
    ]
    dated = any(run.datetime_object.date() != began_on for run in visit.runs)
    for index in range(len(visit.runs) - 1, -1, -1):
        run = visit.runs[index]
        ended_on = run.datetime_object.date()
        newer = visit.runs[index + 1] if index + 1 < len(visit.runs) else None
        if dated and (newer is None or newer.datetime_object.date() != ended_on):
            rows.append(
                {
                    "id": f"d:{visit_id}:{ended_on.isoformat()}",
                    "kind": DATE_ROW,
                    "sid": session_id,
                    "vid": visit_id,
                    "text": format_short_date(ended_on, today),
                }
            )
        rows.append(
            {
                **_run_row(
                    run, run_numbers[run], session_id, marks[run], highlighted_run
                ),
                "vid": visit_id,
                "sel": selected_here,
            }
        )
    return rows


def build_session_tree(
    all_runs: Iterable[RunData],
    selected: str | None,
    session_limit: int,
    now: datetime,
    marks: Mapping[RunData, RunMark],
) -> RunListModel:
    """Build the list of every session whole, with the scenarios played in it.

    ``all_runs`` is a copy of every run in the run store. ``selected`` is the
    page's selected scenario, or ``None``: its rows carry ``sel``, which
    draws their band, and its latest run carries the highlight. ``marks``
    holds a mark for every run of every scenario played in the sessions listed.
    ``session_limit`` and ``now`` are as ``build_run_list`` takes them.

    Sessions are listed newest first, every one of them. Under a session, a
    scenario row per visit, numbered in the order they were played and listed
    newest first, and under each its runs. A run's number counts its
    scenario's runs in the session, and carries on into a second visit, so a
    run has one number in both views. There are no dividers: the rows between
    two visits of one scenario say it was left.

    A scenario row is keyed by its visit's first run, as a session row is by
    the session's. A late run can split a visit or join two, and the row
    then has a new id.
    """
    sessions = split_into_play_sessions(all_runs)
    if not sessions:
        return empty_run_list(NO_RUNS_TEXT, view=VIEW_ALL)

    newest_session = sessions[-1]
    newest_run = run_id(newest_session.runs[-1])
    highlighted_run = _latest_scenario_run_id(sessions, selected)
    in_progress = find_play_session_in_progress(sessions, now) is not None
    today = now.date()

    rows: list[dict] = []
    forced_open: list[str] = []
    for session in list(reversed(sessions))[:session_limit]:
        session_id = f"s:{run_id(session.runs[0])}"
        is_first_row = session is newest_session
        rows.append(
            {
                "id": session_id,
                "kind": SESSION_ROW,
                "sid": session_id,
                "name": format_short_timestamp(session.start, today),
                "in_progress": is_first_row and in_progress,
                # Every session row gives its length here: in the tree a
                # session is the subject, and its length one of its facts.
                "length": format_elapsed_duration(session.length.total_seconds()),
                "length_help": is_first_row,
                "counts": (
                    f"{_count(len(session.runs), 'run')} · "
                    f"{_count(len({run.scenario for run in session.runs}), 'scenario')}"
                ),
            }
        )
        played: Counter[str] = Counter()
        run_numbers: dict[RunData, int] = {}
        for run in session.runs:
            played[run.scenario] += 1
            run_numbers[run] = played[run.scenario]
        visits = split_into_scenario_visits(session)
        for number in range(len(visits), 0, -1):
            child_rows = _visit_rows(
                visits[number - 1],
                number,
                run_numbers,
                session_id,
                session.start.date(),
                today,
                selected,
                marks,
                highlighted_run,
            )
            if is_first_row and number == len(visits):
                # The newest run is the last of the newest visit: it opens
                # its session row and that visit's scenario row.
                forced_open = [session_id, child_rows[0]["id"]]
            rows.extend(child_rows)
    if len(sessions) > session_limit:
        rows.append(_more_row())

    return {
        "rows": rows,
        "view": VIEW_ALL,
        "newest_run": newest_run,
        "forced_open": forced_open,
        "session_limit": session_limit,
        # Its rows are different scenarios, so columns would compare nothing.
        "columns": None,
        "heading": (
            f"{ALL_SCENARIOS_HEADING} · "
            f"{_count(sum(len(session.runs) for session in sessions), 'run')}"
        ),
        "grid_name": ALL_SCENARIOS_GRID_NAME,
        "empty": None,
    }


def _mark_scenario(
    runs: Iterable[RunData],
    scenario: str,
    goal_percentage: float | None,
) -> dict[RunData, RunMark]:
    """Mark every run of one scenario, from its whole history in the store."""
    return mark_runs(
        in_play_order(run for run in runs if run.scenario == scenario),
        goal_percentage,
        lambda version: get_version_pace_basis(scenario, version),
    )


def run_list_from_store(
    view: str,
    scenario: str | None,
    session_limit: int,
    score_threshold_percentage: float | str | None,
    now: datetime,
) -> RunListModel:
    """Build the list from the run store, in one view, for the scenario the page shows.

    ``session_limit`` is how many sessions the view has loaded.
    ``score_threshold_percentage`` is the percentage field's value as the
    browser sends it. The runs are copied from the store once, and the
    sessions and the marks are both worked out from that one copy, so a run
    that lands meanwhile cannot be in one and not the other.

    Under All scenarios every scenario played in the listed sessions is
    marked, one scenario at a time over its whole history, by the function
    that marks the selected scenario under This scenario. A run's check and
    star are then the same in both views.
    """
    all_runs = get_all_runs()
    if not all_runs:
        return empty_run_list(NO_RUNS_TEXT, view=view)
    goal_percentage = normalize_score_threshold_percentage(score_threshold_percentage)
    if view == VIEW_ALL:
        sessions = split_into_play_sessions(all_runs)
        listed = sessions[max(len(sessions) - session_limit, 0) :]
        by_scenario: defaultdict[str, list[RunData]] = defaultdict(list)
        for run in all_runs:
            by_scenario[run.scenario].append(run)
        marks: dict[RunData, RunMark] = {}
        for name in {run.scenario for session in listed for run in session.runs}:
            marks.update(_mark_scenario(by_scenario[name], name, goal_percentage))
        return build_session_tree(all_runs, scenario, session_limit, now, marks)
    if not scenario:
        return empty_run_list(
            NO_SCENARIO_TEXT,
            view=view,
            newest_run=run_id(in_play_order(all_runs)[-1]),
        )
    return build_run_list(
        all_runs,
        scenario,
        session_limit,
        now,
        _mark_scenario(all_runs, scenario, goal_percentage),
    )


def is_session_in_progress(now: datetime) -> bool:
    """Tell whether the run store's newest session is in progress at ``now``.

    Asked of the app's own clock, never a browser's. A page that shows the
    state asks again on a timer, because nothing happens when a session ends.
    """
    sessions = split_into_play_sessions(get_all_runs())
    return find_play_session_in_progress(sessions, now) is not None


# --- The list on a page --------------------------------------------------------

EXPAND_ALL_LABEL = "Expand all"
COLLAPSE_ALL_LABEL = "Collapse all"
SHOW_ALL_RUNS_LABEL = "Show all runs"
HIDE_ALL_RUNS_LABEL = "Hide all runs"
MARKS_HEADER = "Marks"
LIST_VIEW_LABEL = "Run list view"
# A session row's count under This scenario is a button that jumps to the
# session under All scenarios. Its text is its name, and this its hover.
WHOLE_SESSION_HELP = "Show the whole session"
# What a screen reader is told that a sighted reader sees drawn: the name of
# a group row's button, and what a key pressed on the row just did to it.
SESSION_TOGGLE_LABEL = "Session"
SCENARIO_TOGGLE_LABEL = "Scenario"
EXPANDED_ANNOUNCEMENT = "Expanded"
COLLAPSED_ANNOUNCEMENT = "Collapsed"

RUN_LIST_CLASS = "run-history-list"
# The list with nothing to list: its text shows in place of its header and
# its grid.
RUN_LIST_NOTHING_CLASS = f"{RUN_LIST_CLASS} run-history-list-nothing"
# The list with runs and no scenario selected, under This scenario: the text
# shows in place of the grid, and the switch stays above it. The tree needs
# no selection, and without the switch a player could not reach it.
RUN_LIST_UNSELECTED_CLASS = f"{RUN_LIST_CLASS} run-history-list-unselected"
RUN_LIST_GRID_CLASS = "run-history-list-grid"
LATEST_ROW_CLASS = "run-list-row-latest"
SELECTED_ROW_CLASS = "run-list-row-selected"

# The columns the Columns menu shows or hides, in table order. Shots Fired
# and Sensitivity are shown to start, and the other three are off, so the
# list looks as it did until someone asks for more. The browser remembers
# each choice under an id built from the column's, and drops it if the
# column's default ever changes, so neither may change.
RUN_LIST_MENU_COLUMNS = (
    MenuColumn("shots", "Shots Fired"),
    MenuColumn("reloads", "Reloads", shown_by_default=False),
    MenuColumn("sens", "Sensitivity"),
    MenuColumn("fov", "FOV", shown_by_default=False),
    MenuColumn("avg_fps", "Avg FPS", shown_by_default=False),
)
# The choice that is not a column: the median and best of the runs under a
# row that stands for one scenario's runs. Off to start, so the list looks as
# it did until someone asks for more. The browser remembers it under its id.
MEDIAN_AND_BEST_CHOICE = MenuChoice("median_best", "Median and best")


class RunListIds(NamedTuple):
    """The component ids one page gives its run list.

    ``columns_menu`` is the Columns menu's id, which is part of the id of
    each of its checkboxes. The browser stores a checkbox's choice under its
    id, so changing it resets that choice for every user.

    ``view`` is the switch between the two views, which the browser
    remembers under its id. ``session_limit`` and ``all_session_limit`` are
    the stores holding how many sessions This scenario and All scenarios
    load. The list's script adds to the view's own when older sessions are
    asked for, and the page takes both as inputs of the callback that builds
    the rows. ``model`` is the store that callback writes the rows to.

    ``jump`` and ``scenario_asked`` are stores the script writes and the
    server reads. ``jump`` names how far back a session asked for from its
    count is, and ``scenario_asked`` the scenario whose name was pressed in
    the tree. Each is always in the layout, because a page has to hold every
    input of a callback whose output it holds.
    """

    panel: str
    heading: str
    view: str
    expand_all: str
    columns_menu: str
    grid: str
    empty: str
    announcer: str
    model: str
    session_limit: str
    all_session_limit: str
    jump: str
    scenario_asked: str
    apply_sink: str
    expand_all_sink: str
    figures_sink: str


def _fixed_width(width: int) -> dict[str, int]:
    """Hold a column to one width.

    The list's width is worked out from these widths, in
    ``run_list_widths``, so the columns shown fit it with a scrollbar's room
    to spare and the last one is not clipped once enough rows are open to
    scroll. The minimum and the maximum are what hold it: the shared Columns
    menu fits a column to its content when it shows one, and a column with
    one allowed width comes out of that fit unchanged.
    """
    return {"width": width, "minWidth": width, "maxWidth": width}


def run_list_column_defs() -> list[dict[str, Any]]:
    """Build the list's ten columns, each named for the row field it shows.

    Reloads, FOV and Avg FPS are hidden to start, as their menu entries are
    unchecked.
    """
    return [
        {
            "field": "n",
            "headerName": "#",
            "cellClass": "run-list-number",
            "headerClass": "run-list-number",
            # Moves with the class's padding-left in the stylesheet: the
            # number's room is what the two leave.
            **_fixed_width(50),
        },
        {"field": "time", "headerName": "Time", **_fixed_width(66)},
        {"field": "score", "headerName": "Score", **_fixed_width(72)},
        {
            # The check and the star. It has no visible header, and takes the
            # room the fixed columns leave, so it is the one that gives when
            # a scrollbar appears.
            "colId": "marks",
            "headerName": MARKS_HEADER,
            "headerClass": "run-list-header-unseen",
            "cellRenderer": "RunListMarks",
            "flex": 1,
            "minWidth": 34,
        },
        {
            "field": "accuracy",
            "headerName": "Accuracy",
            "type": "rightAligned",
            **_fixed_width(70),
        },
        {
            "field": "shots",
            "headerName": "Shots Fired",
            "type": "rightAligned",
            **_fixed_width(82),
        },
        {
            "field": "reloads",
            "headerName": "Reloads",
            "type": "rightAligned",
            "hide": True,
            **_fixed_width(64),
        },
        {
            "field": "sens",
            "headerName": "Sensitivity",
            "type": "rightAligned",
            **_fixed_width(96),
        },
        {
            "field": "fov",
            "headerName": "FOV",
            "type": "rightAligned",
            "hide": True,
            # A long scale is cut short, so the hover gives the whole text.
            "tooltipField": "fov",
            **_fixed_width(116),
        },
        {
            "field": "avg_fps",
            "headerName": "Avg FPS",
            "type": "rightAligned",
            "hide": True,
            **_fixed_width(64),
        },
    ]


# The room the list takes beyond its fixed columns: its two borders, a
# classic scrollbar, and the marks column at the width it had when the list
# was always 500px. So the default columns need exactly 500px, and no
# browser sees its marks column change.
RUN_LIST_ROOM = 64


def run_list_widths() -> tuple[int, dict[str, int]]:
    """Return what the list needs before its menu's columns, and what each adds.

    The list needs ``RUN_LIST_ROOM`` plus the fixed width of every column it
    shows. The first value counts the columns the menu can't hide, and the
    second maps each menu column's id to the width it adds when shown. Both
    are read from ``run_list_column_defs``, so a width changed there moves
    the list's.
    """
    menu_ids = {column.column_id for column in RUN_LIST_MENU_COLUMNS}
    need = RUN_LIST_ROOM
    widths: dict[str, int] = {}
    for column in run_list_column_defs():
        if "maxWidth" not in column:
            # The marks column, which flexes inside RUN_LIST_ROOM.
            continue
        column_id = column.get("colId", column["field"])
        if column_id in menu_ids:
            widths[column_id] = column["maxWidth"]
        else:
            need += column["maxWidth"]
    return need, widths


def run_list_stores(ids: RunListIds) -> list[dcc.Store]:
    """Build the stores the list's callbacks read and write."""
    return [
        dcc.Store(id=ids.model),
        # Not remembered: every visit starts each view from the first load.
        dcc.Store(id=ids.session_limit, data=SESSIONS_PER_LOAD),
        dcc.Store(id=ids.all_session_limit, data=SESSIONS_PER_LOAD),
        # Empty until the script asks: no input is ever missing.
        dcc.Store(id=ids.jump),
        dcc.Store(id=ids.scenario_asked),
        dcc.Store(id=ids.apply_sink),
        dcc.Store(id=ids.expand_all_sink),
        dcc.Store(id=ids.figures_sink),
        columns_menu_sink(ids.columns_menu),
    ]


def run_list_class(model: RunListModel) -> str:
    """Name the list's class for a model: rows, nothing to list, or no scenario."""
    if model["empty"] is None:
        return RUN_LIST_CLASS
    if model["empty"] == NO_SCENARIO_TEXT:
        return RUN_LIST_UNSELECTED_CLASS
    return RUN_LIST_NOTHING_CLASS


def run_list_panel(ids: RunListIds) -> dmc.Paper:
    """Build the list: its header, the grid, and the text for nothing to list.

    The header is the switch between the two views at the left, with Expand
    all and the Columns menu at the right. The heading line is in it too, in
    its place before the switch, for a screen reader only: the latest-run
    card above the list names its scenario on screen.

    The grid is given no rows. The page's callback writes them to
    ``ids.model``, and the script registered by ``register_run_list`` hands
    them to the grid.
    """
    live_region: dict[str, Any] = {"aria-live": "polite"}
    return dmc.Paper(
        withBorder=True,
        radius="sm",
        id=ids.panel,
        className=RUN_LIST_CLASS,
        children=[
            dmc.Box(
                className="run-history-list-header",
                children=[
                    # A line of text, and not an HTML heading, so a screen
                    # reader hears what it heard while the line was on
                    # screen.
                    dmc.Text(
                        id=ids.heading,
                        className="run-history-list-heading visually-hidden",
                    ),
                    dmc.SegmentedControl(
                        data=LIST_VIEW_OPTIONS,
                        id=ids.view,
                        className="run-history-list-view",
                        persistence=True,
                        radius="sm",
                        size="sm",
                        # The same on every visit. The browser stores the
                        # choice against the value the layout was drawn with,
                        # and discards it when a later visit draws another.
                        value=LIST_VIEW_DEFAULT,
                        **{"aria-label": LIST_VIEW_LABEL},
                    ),
                    dmc.Box(
                        className="run-history-list-actions",
                        children=[
                            dmc.Button(
                                EXPAND_ALL_LABEL, id=ids.expand_all, variant="default"
                            ),
                            columns_menu(
                                ids.columns_menu,
                                RUN_LIST_MENU_COLUMNS,
                                (MEDIAN_AND_BEST_CHOICE,),
                            ),
                        ],
                    ),
                ],
            ),
            dag.AgGrid(
                id=ids.grid,
                className=f"ag-theme-quartz {RUN_LIST_GRID_CLASS}",
                columnDefs=run_list_column_defs(),
                defaultColDef={
                    # A sort would scatter each session's rows.
                    "sortable": False,
                    "resizable": False,
                    "suppressMovable": True,
                },
                dashGridOptions={
                    **COLUMNS_MENU_GRID_OPTIONS,
                    "animateRows": False,
                    # A cell's hover is the browser's own title, as a scenario
                    # row's name is, and not a popup the grid draws.
                    "enableBrowserTooltips": True,
                    "headerHeight": 28,
                    # A run that lands must not move what the reader is
                    # looking at. The script scrolls to the top itself, when
                    # the page follows the scenario just played.
                    "suppressScrollOnNewData": True,
                    # A full-width row is drawn in a container of its own
                    # unless embedded, and the grid moves rows by transform
                    # and leaves them in the page in their old order. Without
                    # these two a screen reader reads the session rows apart
                    # from the runs under them.
                    "embedFullWidthRows": True,
                    "ensureDomOrder": True,
                    "isFullWidthRow": {"function": "runListIsFullWidth(params)"},
                    "fullWidthCellRenderer": "RunListWideRow",
                    "isExternalFilterPresent": {"function": "true"},
                    "doesExternalFilterPass": {"function": "runListFilterPass(params)"},
                    "getRowHeight": {"function": "runListRowHeight(params)"},
                    "getRowClass": {"function": "runListRowClass(params)"},
                    # A rule for the selected scenario's latest run, not
                    # part of the class ``getRowClass`` returns: when a row
                    # is refreshed the grid adds that class again and never
                    # takes off one it added before, where it both adds and
                    # removes a rule's class. The run that was the latest
                    # stays in the list, and has to lose the highlight.
                    # The band on the selected scenario's run rows in the tree
                    # is a rule for the same reason: it moves with the
                    # selection. A scenario row's band is drawn by the
                    # script: the grid works the rules out again when a row's
                    # data changes, but not for a full-width row, so a rule's
                    # band stayed on the scenario selected before.
                    "rowClassRules": {
                        "run-list-row-linked": "params.data.linked === true",
                        LATEST_ROW_CLASS: "params.data.latest",
                        SELECTED_ROW_CLASS: (
                            f"params.data.sel && params.data.kind === '{RUN_ROW}'"
                        ),
                    },
                    # The grid would say "No Matching Rows" over a list whose
                    # one session is closed, and "No Rows To Show" before the
                    # first rows arrive.
                    "suppressOverlays": ["loading", "noRows", "noMatchingRows"],
                    "context": {
                        "gridId": ids.grid,
                        "limitStoreIds": {
                            VIEW_SCENARIO: ids.session_limit,
                            VIEW_ALL: ids.all_session_limit,
                        },
                        "jumpStoreId": ids.jump,
                        "askStoreId": ids.scenario_asked,
                        "expandAllId": ids.expand_all,
                        "announcerId": ids.announcer,
                        "sessionsPerLoad": SESSIONS_PER_LOAD,
                        "treeView": VIEW_ALL,
                        "runRowIdPrefix": RUN_ROW_ID_PREFIX,
                        "labels": {
                            "expandAll": EXPAND_ALL_LABEL,
                            "collapseAll": COLLAPSE_ALL_LABEL,
                            "showAllRuns": SHOW_ALL_RUNS_LABEL,
                            "hideAllRuns": HIDE_ALL_RUNS_LABEL,
                            "session": SESSION_TOGGLE_LABEL,
                            "scenario": SCENARIO_TOGGLE_LABEL,
                            "expanded": EXPANDED_ANNOUNCEMENT,
                            "collapsed": COLLAPSED_ANNOUNCEMENT,
                            "inProgress": IN_PROGRESS_LABEL,
                            "lengthHelp": SESSION_LENGTH_HELP,
                            "wholeSession": WHOLE_SESSION_HELP,
                            "newPb": NEW_PB_TEXT,
                            "median": MEDIAN_LABEL,
                            "best": BEST_LABEL,
                            "score": SCORE_LABEL,
                        },
                    },
                },
                eventListeners={
                    "cellKeyDown": ["runListKeyDown(params)"],
                    "cellMouseOver": ["runHistoryHoverOver(params)"],
                    "cellMouseOut": ["runHistoryHoverOut(params)"],
                    "bodyScroll": ["runHistoryHoverClear(params)"],
                },
                getRowId="params.data.id",
                dangerously_allow_code=True,
                style={"flex": 1, "minHeight": 0, "width": "100%"},
            ),
            dmc.Text(id=ids.empty, className="run-history-list-empty"),
            # Where a key pressed on a group row says what it did, and a
            # press on a scenario's name what it selected. In the page before
            # anything is said: a live region added with its text already in
            # it is not read out.
            html.Div(
                id=ids.announcer,
                className="visually-hidden",
                role="status",
                **live_region,
            ),
        ],
    )


# Only the newest run applies: each waits for the grid on its own timer, so
# an older one can finish last and would put its rows back. The source is a
# function that returns the callback, so the counter it closes over lasts for
# the life of the page.
_APPLY_RUN_LIST = """
(() => {
    let latestRun = 0;

    return async (model, follow) => {
        const noUpdate = window.dash_clientside.no_update;
        if (!model || !window.runHistoryList || !window.dash_ag_grid) {
            return noUpdate;
        }
        latestRun += 1;
        const run = latestRun;
        const gridApi = await window.dash_ag_grid.getApiAsync(GRID_ID);
        if (run === latestRun) {
            window.runHistoryList.apply(gridApi, model, follow);
        }
        return noUpdate;
    };
})()
"""

_EXPAND_ALL = """
async (clicks) => {
    if (clicks && window.runHistoryList && window.dash_ag_grid) {
        const gridApi = await window.dash_ag_grid.getApiAsync(GRID_ID);
        window.runHistoryList.toggleAll(gridApi);
    }
    return window.dash_clientside.no_update;
}
"""

# The checkbox runs as the page mounts, with the remembered value, and on
# every change. Its state belongs to the list's script, not a grid.
_APPLY_FIGURES = """
(checked) => {
    if (window.runHistoryList) {
        window.runHistoryList.setFigures(Boolean(checked));
    }
    return window.dash_clientside.no_update;
}
"""


# The width the list's shown columns need, written to the page as a CSS
# variable that the stylesheet clamps between the list's minimum and the
# chart's floor. It runs as the page mounts, with the stored choices, and on
# every change. The widths come from the server's column list and not from
# the grid: the marks column's width follows the list's, which this sets.
_LIST_NEED = """
(checked, ids) => {
    let need = BASE_NEED;
    ids.forEach((id, index) => {
        if (checked[index]) {
            need += WIDTHS[id.column] || 0;
        }
    });
    return {"--run-history-list-need": `${need}px`};
}
"""


def jump_to_session(jump: dict | None, held_limit: int | None) -> tuple:
    """Switch the list to All scenarios, loaded far enough back to hold a session.

    ``jump`` is what the script wrote when a session's count was pressed:
    the session's place among all sessions, counting back from the newest.
    If All scenarios has loaded fewer sessions than that, it loads that many,
    and the session is the last one listed.

    The switch is written here, and not by the script, because a value a
    callback writes to a remembered control is remembered: the view the jump
    leaves on screen is the view a reload shows. Both outputs are plain, and
    the callback that builds the rows takes both as inputs, so Dash holds it
    until this answers and the tree is built once, already reaching the
    session. What to open and where to scroll stay in the browser.
    """
    if not jump:
        return no_update, no_update
    place = jump.get("place")
    loaded = held_limit or SESSIONS_PER_LOAD
    return (
        VIEW_ALL,
        place if isinstance(place, int) and place > loaded else no_update,
    )


def register_run_list(ids: RunListIds, *, follow_switch: str, page: str) -> None:
    """Register the scripts that draw the list, and the jump, for one page's ids.

    Call once per page, at import. ``follow_switch`` is the id of the page's
    Follow switch: while it is on, a run that lands scrolls the list back to
    the top. It is read as state, so flipping it applies nothing. ``page`` is
    the id of the page's root: its ``style`` holds the width the list's shown
    columns need, as ``--run-history-list-need``, and nothing else may write
    that ``style``.

    The rows reach the grid through its API and never as Dash components or
    through its ``rowData`` prop. Which rows are open is kept by the script
    and never sent to the server. The server hears only how far back a jump
    reaches, from ``ids.jump``.
    """
    grid_id = json.dumps(ids.grid)
    clientside_callback(
        _APPLY_RUN_LIST.replace("GRID_ID", grid_id),
        Output(ids.apply_sink, "data"),
        Input(ids.model, "data"),
        State(follow_switch, "checked"),
    )
    clientside_callback(
        _EXPAND_ALL.replace("GRID_ID", grid_id),
        Output(ids.expand_all_sink, "data"),
        Input(ids.expand_all, "n_clicks"),
        prevent_initial_call=True,
    )
    clientside_callback(
        _APPLY_FIGURES,
        Output(ids.figures_sink, "data"),
        Input(
            choice_checkbox_id(ids.columns_menu, MEDIAN_AND_BEST_CHOICE.choice_id),
            "checked",
        ),
    )
    callback(
        Output(ids.view, "value"),
        Output(ids.all_session_limit, "data"),
        Input(ids.jump, "data"),
        State(ids.all_session_limit, "data"),
        # The store is empty until a count is pressed, and a mount must not
        # move the switch.
        prevent_initial_call=True,
    )(jump_to_session)
    base_need, widths = run_list_widths()
    clientside_callback(
        _LIST_NEED.replace("BASE_NEED", str(base_need)).replace(
            "WIDTHS", json.dumps(widths)
        ),
        Output(page, "style"),
        Input(column_checkbox_id(ids.columns_menu, ALL), "checked"),
        State(column_checkbox_id(ids.columns_menu, ALL), "id"),
    )
    register_columns_menu(ids.columns_menu, ids.grid)
