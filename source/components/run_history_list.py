"""What the Run History page's run list shows: one scenario's runs, by session.

``build_run_list`` turns a copy of the run store into a flat list of row
records: a row per session, and under it that session's runs of the scenario,
with a divider where the scenario was left and returned to and a date header
where a run is on another date than its session began. The page sends the
records to the browser as data, and a script draws them in a grid.

The list is worked out from the run store each time, never from the batches
of new runs a page is sent: two open tabs race for each batch, and a list
built from batches would miss runs in one of them.

Which rows are open is the browser's alone. The records only name the newest
run and the row it opens, and the script applies that once per run.
"""

import math
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import Any, TypedDict

from source.components.run_marks import RunMark, mark_runs
from source.components.score_threshold import (
    ThresholdVerdict,
    Unjudged,
    normalize_score_threshold_percentage,
)
from source.kovaaks.data_models import RunData
from source.kovaaks.data_service import get_all_runs
from source.kovaaks.play_sessions import (
    PlaySession,
    find_play_session_in_progress,
    in_play_order,
    split_into_play_sessions,
    split_into_scenario_visits,
)
from source.kovaaks.time_scored_service import get_version_pace_basis
from source.utilities.utilities import (
    format_elapsed_duration,
    format_score,
    format_short_date,
    format_short_timestamp,
    format_time_of_day,
)

# How many sessions the list loads at first, and how many more each press of
# Show older sessions adds.
SESSIONS_PER_LOAD = 30

# The kinds of row. A session row and the rows under it share the session
# row's id as ``sid``, which is how the script hides a closed session's rows.
SESSION_ROW = "session"
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


class RunListModel(TypedDict):
    """Everything the browser is sent to draw the list.

    ``rows`` is in the order the list shows them, the first row first.
    ``newest_run`` is the id of the newest run in the whole run store, and
    ``forced_open`` the ids of the rows that run opens. The script opens them
    once per ``newest_run``, so a row the player closed is not reopened by a
    later change of scenario. ``empty`` is the text shown in place of the
    list when there is nothing to list, and ``None`` otherwise.
    """

    rows: list[dict[str, Any]]
    newest_run: str | None
    forced_open: list[str]
    heading: str
    grid_name: str
    empty: str | None


def empty_run_list(text: str) -> RunListModel:
    """Build the model of a list with nothing to list, and the text that says so."""
    return {
        "rows": [],
        "newest_run": None,
        "forced_open": [],
        "heading": "",
        "grid_name": "",
        "empty": text,
    }


def run_id(run: RunData) -> str:
    """Return the id a run's row is keyed by: its stats file's name.

    A run event's ``run_id`` is the same value, so a run that just landed can
    be found in the list. A record that was not read from a stats file has no
    name, and is keyed by its scenario and its end.
    """
    return run.stats_file_name or f"{run.scenario} {run.datetime_object.isoformat()}"


def _count(count: int, noun: str) -> str:
    """Word a count with its noun: ``1 run``, ``47 runs``, ``1,204 runs``."""
    return f"{count:,} {noun}" if count == 1 else f"{count:,} {noun}s"


def _whole_percent(fraction: float) -> str:
    """Format an accuracy to the whole percent, a half rounding up.

    Not ``round``, which sends a half to the even number: 54.5 would read
    54% and 55.5 would read 56%.
    """
    return f"{math.floor(fraction * 100 + 0.5)}%"


def _check_text(mark: RunMark) -> str:
    """Word a run's verdict, or the reason it has none."""
    if isinstance(mark.verdict, ThresholdVerdict):
        return THRESHOLD_PASSED_TEXT if mark.verdict.passed else BELOW_THRESHOLD_TEXT
    return UNJUDGED_TEXT[mark.verdict]


def _run_row(run: RunData, number: int, session_id: str, mark: RunMark) -> dict:
    return {
        "id": f"r:{run_id(run)}",
        "kind": RUN_ROW,
        "sid": session_id,
        "n": number,
        "time": format_time_of_day(run.datetime_object),
        "score": format_score(run.score),
        "passed": mark.passed,
        "check_text": _check_text(mark),
        "new_pb": mark.is_new_pb,
        "accuracy": _whole_percent(run.accuracy),
        "shots": "" if run.shots_fired is None else f"{run.shots_fired:,}",
        "sens": f"{run.horizontal_sens} {run.sens_scale}",
    }


def _session_child_rows(
    session: PlaySession,
    scenario: str,
    session_id: str,
    today: date,
    marks: Mapping[RunData, RunMark],
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
        rows.append(_run_row(run, index + 1, session_id, marks[run]))
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
    in_progress = find_play_session_in_progress(sessions, now) is not None
    today = now.date()
    listed = [
        session
        for session in reversed(sessions)
        if session is newest_session
        or any(run.scenario == scenario for run in session.runs)
    ]

    rows: list[dict] = []
    for session in listed[:session_limit]:
        session_id = f"s:{run_id(session.runs[0])}"
        is_first_row = session is newest_session
        played = sum(run.scenario == scenario for run in session.runs)
        rows.append(
            {
                "id": session_id,
                "kind": SESSION_ROW,
                "sid": session_id,
                "name": format_short_timestamp(session.start, today),
                "in_progress": is_first_row and in_progress,
                # Only the first row gives its length: the session being
                # played is the one whose length matters at a glance.
                "length": (
                    format_elapsed_duration(session.length.total_seconds())
                    if is_first_row
                    else None
                ),
                "counts": f"{played:,} of {_count(len(session.runs), 'run')}",
            }
        )
        rows.extend(_session_child_rows(session, scenario, session_id, today, marks))
    if len(listed) > session_limit:
        rows.append(
            {
                "id": MORE_ROW_ID,
                "kind": MORE_ROW,
                "sid": MORE_ROW_ID,
                "text": SHOW_OLDER_SESSIONS_LABEL,
            }
        )

    scenario_run_count = sum(
        run.scenario == scenario for session in sessions for run in session.runs
    )
    return {
        "rows": rows,
        "newest_run": run_id(newest_session.runs[-1]),
        "forced_open": [rows[0]["id"]],
        "heading": f"{scenario} · {_count(scenario_run_count, 'run')}",
        "grid_name": f"Runs of {scenario}, by session",
        "empty": None,
    }


def run_list_from_store(
    scenario: str | None,
    session_limit: int,
    score_threshold_percentage: float | str | None,
    now: datetime,
) -> RunListModel:
    """Build the list from the run store, for the scenario the page shows.

    ``score_threshold_percentage`` is the percentage field's value as the
    browser sends it. The runs are copied from the store once, and the
    sessions and the marks are both worked out from that one copy, so a run
    that lands meanwhile cannot be in one and not the other.
    """
    all_runs = get_all_runs()
    if not all_runs:
        return empty_run_list(NO_RUNS_TEXT)
    if not scenario:
        return empty_run_list(NO_SCENARIO_TEXT)
    marks = mark_runs(
        in_play_order(run for run in all_runs if run.scenario == scenario),
        normalize_score_threshold_percentage(score_threshold_percentage),
        lambda version: get_version_pace_basis(scenario, version),
    )
    return build_run_list(all_runs, scenario, session_limit, now, marks)


def is_session_in_progress(now: datetime) -> bool:
    """Tell whether the run store's newest session is in progress at ``now``.

    Asked of the app's own clock, never a browser's. A page that shows the
    state asks again on a timer, because nothing happens when a session ends.
    """
    sessions = split_into_play_sessions(get_all_runs())
    return find_play_session_in_progress(sessions, now) is not None
