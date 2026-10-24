"""The rows the Run History page's run list shows.

The row model is one pure function over run records, so these tests build
records and read rows. What marks a run is ``tests/test_run_marks.py``.
"""

from dataclasses import replace
from datetime import datetime, timedelta

import dash
import pytest

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.components import run_history_list  # noqa: E402
from source.components.run_history_list import (  # noqa: E402
    NO_RUNS_TEXT,
    NO_SCENARIO_TEXT,
    SESSION_LENGTH_HELP,
    SESSIONS_PER_LOAD,
    VIEW_ALL,
    VIEW_SCENARIO,
    build_run_list,
    build_session_tree,
    is_session_in_progress,
    run_id,
    run_list_from_store,
)
from source.components.run_marks import mark_runs  # noqa: E402
from source.kovaaks.data_models import RecordedSensitivity, RunData  # noqa: E402
from source.kovaaks.play_sessions import in_play_order  # noqa: E402

A, B, C = "Scenario A", "Scenario B", "Scenario C"
EVENING = datetime(2026, 10, 4, 21, 45, 0)


def _run(  # noqa: PLR0913
    scenario: str,
    ended: datetime,
    *,
    score: float = 100.0,
    length: timedelta | None = timedelta(seconds=60),
    accuracy: float = 0.5,
    shots: int | None = 200,
    sensitivity: float = 40.8,
) -> RunData:
    """Build one run that ended at ``ended`` and took ``length`` to play."""
    return RunData(
        datetime_object=ended,
        score=score,
        sens_scale="cm/360",
        horizontal_sens=sensitivity,
        scenario=scenario,
        accuracy=accuracy,
        stats_file_name=(
            f"{scenario} - Challenge - {ended:%Y.%m.%d-%H.%M.%S} Stats.csv"
        ),
        run_start=None if length is None else ended - length,
        run_length=length,
        shots_fired=shots,
    )


def _minutes(*offsets: int, scenario: str = A, start: datetime = EVENING) -> list:
    """Build one run of ``scenario`` ending each ``offset`` minutes after ``start``."""
    return [_run(scenario, start + timedelta(minutes=offset)) for offset in offsets]


def _build(
    runs: list[RunData],
    scenario: str = A,
    *,
    limit: int = SESSIONS_PER_LOAD,
    now: datetime | None = None,
    percentage: float | None = 95.0,
):
    """Build the list as the page does, with every run marked by score."""
    marks = mark_runs(
        in_play_order(run for run in runs if run.scenario == scenario),
        percentage,
        lambda _version: None,
    )
    if now is None:
        now = max(run.datetime_object for run in runs)
    return build_run_list(runs, scenario, limit, now, marks)


def _kinds(model) -> list[str]:
    return [row["kind"] for row in model["rows"]]


def _of_kind(model, kind: str) -> list[dict]:
    return [row for row in model["rows"] if row["kind"] == kind]


def _texts(model) -> list:
    """Read the list top to bottom, one short value per row."""
    read = {
        "session": lambda row: row["name"],
        "run": lambda row: row["n"],
        "divider": lambda row: row["text"],
        "date": lambda row: row["text"],
        "note": lambda row: row["text"],
        "more": lambda row: row["text"],
    }
    return [read[row["kind"]](row) for row in model["rows"]]


# --- Which sessions are listed -------------------------------------------------


def test_a_store_with_no_runs_lists_nothing_and_says_so():
    model = build_run_list([], A, SESSIONS_PER_LOAD, EVENING, {})

    assert model["rows"] == []
    assert model["empty"] == NO_RUNS_TEXT
    assert model["newest_run"] is None
    assert model["forced_open"] == []
    assert model["view"] == VIEW_SCENARIO


def test_only_sessions_that_hold_a_run_of_the_scenario_are_listed_newest_first():
    day = timedelta(days=1)
    runs = [
        *_minutes(0, 2, start=EVENING - 3 * day),
        *_minutes(0, scenario=B, start=EVENING - 2 * day),
        *_minutes(0, start=EVENING - day),
        *_minutes(0, 2, 4),
    ]

    model = _build(runs)

    assert [row["name"] for row in _of_kind(model, "session")] == [
        "Oct 4, 9:44 PM",
        "Oct 3, 9:44 PM",
        "Oct 1, 9:44 PM",
    ]
    assert model["empty"] is None


def test_the_newest_session_is_the_first_row_even_with_no_run_of_the_scenario():
    day = timedelta(days=1)
    runs = [
        *_minutes(0, 2, start=EVENING - day),
        *_minutes(0, 2, 4, scenario=B),
    ]

    model = _build(runs)

    assert _texts(model) == [
        "Oct 4, 9:44 PM",
        "Not played in this session",
        "Oct 3, 9:44 PM",
        2,
        1,
    ]
    first_row = model["rows"][0]
    assert first_row["counts"] == "0 of 3 runs"
    assert model["rows"][1]["sid"] == first_row["id"]


def test_the_first_row_is_in_progress_until_thirty_minutes_after_its_last_run():
    runs = _minutes(0, 10)
    last = runs[-1].datetime_object

    playing = _build(runs, now=last + timedelta(minutes=30))
    ended = _build(runs, now=last + timedelta(minutes=30, seconds=1))

    assert playing["rows"][0]["in_progress"] is True
    assert ended["rows"][0]["in_progress"] is False
    assert ended["rows"][0].get("length") is None
    assert [row["id"] for row in ended["rows"]] == [
        row["id"] for row in playing["rows"]
    ]


def test_no_scenario_session_row_gives_its_length_and_only_the_first_is_in_progress():
    day = timedelta(days=1)
    runs = [*_minutes(0, 20, start=EVENING - day), *_minutes(0, 25, 50, 65)]

    model = _build(runs)

    first, older = _of_kind(model, "session")
    assert (first.get("length"), first["in_progress"]) == (None, True)
    assert (older.get("length"), older["in_progress"]) == (None, False)


@pytest.mark.parametrize(
    ("offsets", "length"),
    [
        ((0,), "1 min"),
        ((0, 8), "9 min"),
        ((0, 20, 40, 59), "1 hr"),
        ((0, 25, 50, 75, 100, 125), "2 hr 6 min"),
    ],
)
def test_the_session_length_is_given_in_minutes_and_hours(offsets, length):
    assert _tree(_minutes(*offsets))["rows"][0]["length"] == length


@pytest.mark.parametrize(
    ("seconds", "length"),
    [
        (15, "<1 min"),
        (29, "<1 min"),
        (40, "1 min"),
        # A run of 60 seconds measures a little under 60: its start is
        # written to the millisecond and its end is a whole second.
        (59.9, "1 min"),
    ],
)
def test_a_session_of_one_short_run_rounds_to_the_nearest_minute(seconds, length):
    run = _run(A, EVENING, length=timedelta(seconds=seconds))

    assert _tree([run])["rows"][0]["length"] == length


# --- A session row's counts, and its runs --------------------------------------


@pytest.mark.parametrize(
    ("mine", "others", "counts"),
    [(1, 0, "1 of 1 run"), (1, 3, "1 of 4 runs"), (7, 40, "7 of 47 runs")],
)
def test_a_session_row_counts_the_scenarios_runs_out_of_the_sessions(
    mine, others, counts
):
    runs = [
        *_minutes(*range(mine)),
        *_minutes(*range(mine, mine + others), scenario=B),
    ]

    assert _build(runs)["rows"][0]["counts"] == counts


def test_runs_are_numbered_per_session_counting_the_scenario_alone():
    day = timedelta(days=1)
    runs = [
        *_minutes(0, 2, start=EVENING - day),
        *_minutes(0, scenario=B),
        *_minutes(2, 4, 6),
    ]

    model = _build(runs)

    # Newest first under each session, and the count starts again in each.
    assert _texts(model) == [
        "Oct 4, 9:44 PM",
        3,
        2,
        1,
        "Oct 3, 9:44 PM",
        2,
        1,
    ]
    assert [row["time"] for row in _of_kind(model, "run")[:3]] == [
        "9:51 PM",
        "9:49 PM",
        "9:47 PM",
    ]


def test_every_row_under_a_session_carries_that_sessions_id():
    day = timedelta(days=1)
    runs = [*_minutes(0, start=EVENING - day), *_minutes(0, 2)]

    model = _build(runs)

    newest, older = _of_kind(model, "session")
    assert [row["sid"] for row in model["rows"]] == [
        newest["id"],
        newest["id"],
        newest["id"],
        older["id"],
        older["id"],
    ]
    assert newest["id"] != older["id"]


def test_a_session_row_is_keyed_by_the_sessions_first_run_on_any_scenario():
    first = _run(B, EVENING)
    runs = [first, *_minutes(2, 4)]

    model = _build(runs)

    assert model["rows"][0]["id"] == f"s:{run_id(first)}"
    assert [row["id"] for row in _of_kind(model, "run")] == [
        f"r:{run_id(runs[2])}",
        f"r:{run_id(runs[1])}",
    ]


# --- Dividers ------------------------------------------------------------------


def test_a_divider_counts_the_runs_and_scenarios_between_two_visits():
    runs = [
        *_minutes(0, 2),
        *_minutes(4, 6, scenario=B),
        *_minutes(8, scenario=C),
        *_minutes(10),
    ]

    model = _build(runs)

    assert _texts(model) == [
        "Oct 4, 9:44 PM",
        3,
        "3 runs on 2 other scenarios",
        2,
        1,
    ]


def test_a_divider_words_one_run_on_one_scenario_in_the_singular():
    runs = [*_minutes(0), *_minutes(2, scenario=B), *_minutes(4)]

    assert _of_kind(_build(runs), "divider")[0]["text"] == ("1 run on 1 other scenario")


def test_a_divider_counts_one_scenario_played_twice_in_the_gap_once():
    runs = [
        *_minutes(0),
        *_minutes(2, scenario=B),
        *_minutes(4, scenario=C),
        *_minutes(6, scenario=B),
        *_minutes(8),
    ]

    assert _of_kind(_build(runs), "divider")[0]["text"] == (
        "3 runs on 2 other scenarios"
    )


def test_runs_before_the_first_visit_and_after_the_last_make_no_divider():
    runs = [
        *_minutes(0, scenario=B),
        *_minutes(2, 4),
        *_minutes(6, scenario=C),
    ]

    model = _build(runs)

    assert _of_kind(model, "divider") == []
    assert _texts(model) == ["Oct 4, 9:44 PM", 2, 1]


def test_each_return_to_the_scenario_gets_its_own_divider():
    runs = [
        *_minutes(0),
        *_minutes(2, scenario=B),
        *_minutes(4),
        *_minutes(6, 8, scenario=C),
        *_minutes(10),
    ]

    model = _build(runs)

    assert _texts(model) == [
        "Oct 4, 9:44 PM",
        3,
        "2 runs on 1 other scenario",
        2,
        "1 run on 1 other scenario",
        1,
    ]
    dividers = _of_kind(model, "divider")
    assert len({row["id"] for row in dividers}) == 2


# --- Thirty sessions at a time -------------------------------------------------


def _one_run_a_day(days: int) -> list[RunData]:
    return [
        run
        for back in range(days)
        for run in _minutes(0, start=EVENING - timedelta(days=back))
    ]


def test_the_list_loads_thirty_sessions_and_offers_the_older_ones():
    model = _build(_one_run_a_day(35))

    assert SESSIONS_PER_LOAD == 30
    assert len(_of_kind(model, "session")) == 30
    assert model["rows"][-1] == {
        "id": "more",
        "kind": "more",
        "sid": "more",
        "text": "Show older sessions",
    }


def test_the_next_thirty_join_the_first_and_the_offer_goes_when_none_are_left():
    runs = _one_run_a_day(35)

    first_load = _build(runs)
    second_load = _build(runs, limit=2 * SESSIONS_PER_LOAD)

    assert len(_of_kind(second_load, "session")) == 35
    assert _of_kind(second_load, "more") == []
    loaded_first = [row["id"] for row in first_load["rows"][:-1]]
    assert [row["id"] for row in second_load["rows"]][: len(loaded_first)] == (
        loaded_first
    )


def test_exactly_thirty_sessions_offer_no_older_ones():
    assert _of_kind(_build(_one_run_a_day(30)), "more") == []


def test_a_first_row_with_no_run_of_the_scenario_counts_toward_the_thirty():
    runs = [
        *_one_run_a_day(31)[1:],
        *_minutes(0, scenario=B),
    ]

    model = _build(runs)

    sessions = _of_kind(model, "session")
    assert len(sessions) == 30
    assert sessions[0]["counts"] == "0 of 1 run"
    assert _kinds(model)[-1] == "more"


# --- The newest run, and the row it opens --------------------------------------


def test_the_model_names_the_newest_run_and_the_row_it_forces_open():
    day = timedelta(days=1)
    runs = [*_minutes(0, start=EVENING - day), *_minutes(0, 2)]

    model = _build(runs)

    assert model["newest_run"] == run_id(runs[-1])
    assert model["forced_open"] == [model["rows"][0]["id"]]


def test_a_run_on_another_scenario_is_still_the_newest_run():
    """The first row's counts change for it, so the list has to hear of it."""
    runs = _minutes(0, 2)
    landed = _run(B, EVENING + timedelta(minutes=4))

    before = _build(runs)
    after = _build([*runs, landed])

    assert after["newest_run"] == run_id(landed)
    assert after["newest_run"] != before["newest_run"]
    assert after["forced_open"] == before["forced_open"]
    assert (before["rows"][0]["counts"], after["rows"][0]["counts"]) == (
        "2 of 2 runs",
        "2 of 3 runs",
    )


def test_a_run_that_starts_a_new_session_forces_the_new_first_row_open():
    runs = _minutes(0, 2)
    landed = _run(A, EVENING + timedelta(hours=2))

    before = _build(runs)
    after = _build([*runs, landed])

    assert after["forced_open"] == [f"s:{run_id(landed)}"]
    assert after["forced_open"] != before["forced_open"]
    # The session that was first is the second row now, under the same id.
    assert _of_kind(after, "session")[1]["id"] == before["rows"][0]["id"]


def test_a_late_run_reopens_a_session_that_read_as_ended():
    """It began inside the thirty minutes and finished after them."""
    runs = _minutes(0, 2)
    last = runs[-1].datetime_object
    ended = _build(runs, now=last + timedelta(minutes=40))
    late = _run(
        A,
        last + timedelta(minutes=45),
        length=timedelta(minutes=20),
    )

    reopened = _build([*runs, late], now=last + timedelta(minutes=46))

    assert ended["rows"][0]["in_progress"] is False
    assert reopened["rows"][0]["in_progress"] is True
    assert reopened["rows"][0]["id"] == ended["rows"][0]["id"]
    assert reopened["rows"][0]["counts"] == "3 of 3 runs"


def test_a_run_with_no_usable_start_past_the_break_starts_a_new_session():
    runs = _minutes(0, 2)
    last = runs[-1].datetime_object
    late = _run(A, last + timedelta(minutes=45), length=None)

    model = _build([*runs, late])

    assert len(_of_kind(model, "session")) == 2


# --- Date headers --------------------------------------------------------------

LATE = datetime(2026, 10, 11, 23, 30, 0)


def test_a_session_on_one_date_has_no_date_header():
    assert _of_kind(_build(_minutes(0, 5, 10)), "date") == []


def test_a_session_that_crosses_midnight_has_a_header_for_each_date():
    runs = _minutes(10, 25, 40, 50, start=LATE)

    model = _build(runs)

    assert _texts(model) == [
        "Oct 11, 11:39 PM",
        "Oct 12",
        4,
        3,
        "Oct 11",
        2,
        1,
    ]
    assert [row["time"] for row in _of_kind(model, "run")] == [
        "12:20 AM",
        "12:10 AM",
        "11:55 PM",
        "11:40 PM",
    ]
    assert {row["sid"] for row in _of_kind(model, "date")} == {model["rows"][0]["id"]}


def test_a_session_that_crosses_a_year_names_the_year_that_is_not_this_one():
    new_years_eve = datetime(2026, 12, 31, 23, 30, 0)
    runs = _minutes(10, 40, start=new_years_eve)

    model = _build(runs, now=datetime(2027, 1, 1, 0, 15, 0))

    assert _texts(model) == [
        "Dec 31, 2026, 11:39 PM",
        "Jan 1",
        2,
        "Dec 31, 2026",
        1,
    ]


def test_a_later_year_reads_the_same_session_with_both_years():
    new_years_eve = datetime(2026, 12, 31, 23, 30, 0)
    runs = _minutes(10, 40, start=new_years_eve)

    model = _build(runs, now=datetime(2028, 3, 1, 12, 0, 0))

    assert [row["text"] for row in _of_kind(model, "date")] == [
        "Jan 1, 2027",
        "Dec 31, 2026",
    ]


def test_where_a_header_and_a_divider_meet_the_divider_comes_first():
    """So the header sits directly above the runs it names."""
    runs = [
        *_minutes(20, start=LATE),
        *_minutes(28, scenario=B, start=LATE),
        *_minutes(35, start=LATE),
    ]

    model = _build(runs)

    assert _texts(model) == [
        "Oct 11, 11:49 PM",
        "Oct 12",
        2,
        "1 run on 1 other scenario",
        "Oct 11",
        1,
    ]


def test_a_scenario_played_only_after_midnight_still_gets_its_one_header():
    """The session's name gives the date it began, and no listed run is on it."""
    runs = [
        *_minutes(10, 20, scenario=B, start=LATE),
        *_minutes(40, 50, start=LATE),
    ]

    model = _build(runs)

    assert _texts(model) == ["Oct 11, 11:39 PM", "Oct 12", 2, 1]


def test_one_run_that_crossed_midnight_gets_the_header_of_the_date_it_ended_on():
    run = _run(A, datetime(2026, 10, 12, 0, 1, 0), length=timedelta(minutes=2))

    model = _build([run])

    assert _texts(model) == ["Oct 11, 11:59 PM", "Oct 12", 1]


def test_a_session_that_crossed_midnight_on_other_scenarios_has_no_header():
    runs = [
        *_minutes(10, 20, start=LATE),
        *_minutes(40, 50, scenario=B, start=LATE),
    ]

    model = _build(runs)

    assert _of_kind(model, "date") == []


def test_three_dates_get_three_headers():
    """A session can run past two midnights only on paper, and is still read right."""
    start = datetime(2026, 10, 10, 23, 50, 0)
    runs = [
        _run(A, start + timedelta(minutes=5)),
        _run(A, start + timedelta(minutes=20)),
        # A run that long has no usable start, so each is within the break
        # limit of the one before only by its end.
        *[
            _run(A, start + timedelta(minutes=20 + 29 * step), length=None)
            for step in range(1, 51)
        ],
    ]

    model = _build(runs)

    assert len(_of_kind(model, "session")) == 1
    assert [row["text"] for row in _of_kind(model, "date")] == [
        "Oct 12",
        "Oct 11",
        "Oct 10",
    ]


# --- A run row -----------------------------------------------------------------


def test_a_run_row_formats_each_value_for_its_column():
    first = _run(A, EVENING, score=3000.0)
    run = _run(
        A,
        EVENING + timedelta(minutes=2),
        score=3324.5,
        accuracy=0.545,
        shots=1234,
        sensitivity=40.8,
    )

    model = _build([first, run])

    assert _of_kind(model, "run")[0] == {
        "id": f"r:{run_id(run)}",
        "kind": "run",
        "sid": model["rows"][0]["id"],
        "latest": True,
        "n": 2,
        "time": "9:47 PM",
        "score": "3,324.5",
        "passed": True,
        "check_text": "Threshold passed",
        "new_pb": True,
        "accuracy": "54.50%",
        "shots": "1,234",
        "reloads": "",
        "sens": "40.8 cm/360",
        "sens_detail": "",
        "fov": "",
        "avg_fps": "",
    }


@pytest.mark.parametrize(
    ("accuracy", "shown"),
    [(107 / 130, "82.31%"), (1 / 32, "3.13%"), (1.0, "100.00%"), (0.0, "0.00%")],
)
def test_accuracy_is_shown_to_two_decimals_a_half_rounding_up(accuracy, shown):
    run = _run(A, EVENING, accuracy=accuracy)

    assert _of_kind(_build([run]), "run")[0]["accuracy"] == shown


def test_a_run_with_no_shot_count_shows_none_and_not_zero():
    run = _run(A, EVENING, shots=None)

    assert _of_kind(_build([run]), "run")[0]["shots"] == ""


def _run_row_with(**fields) -> dict:
    run = replace(_run(A, EVENING), **fields)
    return _of_kind(_build([run]), "run")[0]


@pytest.mark.parametrize("view", [VIEW_SCENARIO, VIEW_ALL])
def test_sensitivity_tooltip_preserves_the_original_setting_in_both_views(view):
    run = replace(
        _run(A, EVENING),
        recorded_sensitivity=RecordedSensitivity(
            value=0.16, scale="Valorant", dpi=1600.0
        ),
    )
    marks = mark_runs([run], 95.0, lambda _version: None)
    build = build_run_list if view == VIEW_SCENARIO else build_session_tree
    model = build([run], A, SESSIONS_PER_LOAD, EVENING, marks)
    row = _of_kind(model, "run")[0]
    assert row["sens"] == "40.8 cm/360"
    assert row["sens_detail"] == "40.8 cm/360 (0.16 Valorant at 1600 DPI)"
    column = next(
        column
        for column in run_history_list.run_list_column_defs()
        if column.get("field") == "sens"
    )
    assert column["tooltipField"] == "sens_detail"


@pytest.mark.parametrize(
    ("fov", "scale", "shown"),
    [
        pytest.param(103.0, "Overwatch", "103 Overwatch", id="a whole number"),
        pytest.param(106.5, "Quake/Source", "106.5 Quake/Source", id="a decimal"),
        pytest.param(103.0, None, "103", id="no scale"),
        pytest.param(None, "Overwatch", "", id="no fov"),
    ],
)
def test_the_fov_cell_reads_the_number_then_its_scale(fov, scale, shown):
    assert _run_row_with(fov=fov, fov_scale=scale)["fov"] == shown


@pytest.mark.parametrize(
    ("reloads", "shown"), [(0, "0"), (12, "12"), (1234, "1,234"), (None, "")]
)
def test_reloads_is_a_count_and_unknown_is_never_zero(reloads, shown):
    assert _run_row_with(reloads=reloads)["reloads"] == shown


@pytest.mark.parametrize(
    ("avg_fps", "shown"),
    [(676.4, "676"), (689.6, "690"), (1024.2, "1,024"), (0.0, "0"), (None, "")],
)
def test_avg_fps_is_rounded_to_a_whole_number_with_a_separator(avg_fps, shown):
    assert _run_row_with(avg_fps=avg_fps)["avg_fps"] == shown


def test_a_score_drops_trailing_zeros_and_keeps_two_decimals():
    runs = [
        _run(A, EVENING, score=896.2),
        _run(A, EVENING + timedelta(minutes=2), score=12345.678),
        _run(A, EVENING + timedelta(minutes=4), score=100.0),
    ]

    assert [row["score"] for row in _of_kind(_build(runs), "run")] == [
        "100",
        "12,345.68",
        "896.2",
    ]


def _check_cell(model, number: int) -> tuple[bool, str, bool]:
    (row,) = [row for row in _of_kind(model, "run") if row["n"] == number]
    return row["passed"], row["check_text"], row["new_pb"]


def test_each_blank_cell_gives_the_one_reason_it_has_no_check():
    runs = [
        _run(A, EVENING, score=100.0),
        _run(A, EVENING + timedelta(minutes=2), score=80.0),
        _run(A, EVENING + timedelta(minutes=4), score=99.0),
        _run(A, EVENING + timedelta(minutes=6), score=130.0, sensitivity=30.0),
    ]

    model = _build(runs)

    assert _check_cell(model, 1) == (
        False,
        "Not judged. A scenario's first run, and the first run at a new "
        "sensitivity, aren't judged against the score threshold.",
        False,
    )
    assert _check_cell(model, 2) == (False, "Below threshold", False)
    assert _check_cell(model, 3) == (True, "Threshold passed", False)
    # A new PB at a new sensitivity: its star, and no check.
    assert _check_cell(model, 4)[0::2] == (False, True)
    assert _check_cell(model, 4)[1].startswith("Not judged. A scenario's first run")


def test_an_empty_percentage_is_the_reason_every_cell_gives():
    runs = [
        _run(A, EVENING, score=100.0),
        _run(A, EVENING + timedelta(minutes=2), score=120.0),
    ]

    model = _build(runs, percentage=None)

    assert {row["check_text"] for row in _of_kind(model, "run")} == {
        "Not judged. No score threshold percentage is set."
    }
    assert _check_cell(model, 2)[2] is True


def test_a_pb_of_zero_is_the_reason_a_run_compared_by_score_has_no_check():
    runs = [
        _run(A, EVENING, score=0.0),
        _run(A, EVENING + timedelta(minutes=2), score=-3.0),
    ]

    assert _check_cell(_build(runs), 2) == (
        False,
        "Not judged. Your personal best before this run was zero or less, so "
        "there is no percentage to judge by.",
        False,
    )


# --- The heading, the grid's name, and the length's hover ----------------------


@pytest.mark.parametrize(
    ("mine", "heading"),
    [(1, "Scenario A · 1 run"), (3, "Scenario A · 3 runs")],
)
def test_the_heading_names_the_scenario_and_counts_its_runs(mine, heading):
    assert _build(_minutes(*range(mine)))["heading"] == heading


def test_the_heading_counts_every_run_of_the_scenario_not_the_loaded_ones():
    model = _build(_one_run_a_day(35))

    assert len(_of_kind(model, "run")) == 30
    assert model["heading"] == "Scenario A · 35 runs"


def test_the_grid_is_named_for_the_scenario():
    assert _build(_minutes(0))["grid_name"] == "Runs of Scenario A, by session"


def test_the_lengths_hover_says_why_the_figure_stands_still_between_runs():
    assert SESSION_LENGTH_HELP == (
        "The length runs from the first run to the last run. It doesn't count "
        "the time since your last run."
    )


# --- From the run store --------------------------------------------------------


@pytest.fixture
def store(monkeypatch):
    """Stand a list of runs in for the run store."""
    runs: list[RunData] = []
    monkeypatch.setattr(run_history_list, "get_all_runs", lambda: list(runs))
    monkeypatch.setattr(
        run_history_list, "get_version_pace_basis", lambda _scenario, _version: None
    )
    return runs


def test_an_empty_store_says_no_runs_yet_whatever_is_selected(store):
    assert (
        run_list_from_store(VIEW_SCENARIO, A, 30, 95, EVENING)["empty"] == NO_RUNS_TEXT
    )
    assert (
        run_list_from_store(VIEW_SCENARIO, None, 30, 95, EVENING)["empty"]
        == NO_RUNS_TEXT
    )


@pytest.mark.parametrize("scenario", [None, ""])
def test_no_selection_says_no_scenario_selected(store, scenario):
    store.extend(_minutes(0))

    model = run_list_from_store(VIEW_SCENARIO, scenario, 30, 95, EVENING)

    assert model["empty"] == NO_SCENARIO_TEXT
    assert model["rows"] == []


def test_a_scenario_with_no_local_runs_lists_the_newest_session_alone(store):
    store.extend(_minutes(0, 2, scenario=B))

    model = run_list_from_store(
        VIEW_SCENARIO, A, 30, 95, EVENING + timedelta(minutes=3)
    )

    assert model["empty"] is None
    assert model["heading"] == "Scenario A · 0 runs"
    assert _texts(model) == ["Oct 4, 9:44 PM", "Not played in this session"]


def test_the_stores_runs_are_marked_by_the_percentage_field(store):
    store.extend(
        [
            _run(A, EVENING, score=100.0),
            _run(A, EVENING + timedelta(minutes=2), score=96.0),
        ]
    )
    now = EVENING + timedelta(minutes=3)

    at_95 = run_list_from_store(VIEW_SCENARIO, A, 30, 95, now)
    at_99 = run_list_from_store(VIEW_SCENARIO, A, 30, 99, now)
    cleared = run_list_from_store(VIEW_SCENARIO, A, 30, "", now)

    assert _check_cell(at_95, 2)[:2] == (True, "Threshold passed")
    assert _check_cell(at_99, 2)[:2] == (False, "Below threshold")
    assert _check_cell(cleared, 2)[1] == (
        "Not judged. No score threshold percentage is set."
    )


def test_the_store_answers_whether_its_newest_session_is_in_progress(store):
    store.extend(_minutes(0, 2))
    last = store[-1].datetime_object

    assert is_session_in_progress(last + timedelta(minutes=30)) is True
    assert is_session_in_progress(last + timedelta(minutes=31)) is False


def test_an_empty_store_has_no_session_in_progress(store):
    assert is_session_in_progress(EVENING) is False


# --- How many sessions were loaded ---------------------------------------------


def test_the_model_carries_the_limit_it_was_loaded_up_to():
    """The script adds to it when older sessions are asked for."""
    runs = _one_run_a_day(35)

    assert _build(runs)["session_limit"] == SESSIONS_PER_LOAD
    assert _build(runs, limit=60)["session_limit"] == 60
    assert build_run_list([], A, 90, EVENING, {})["session_limit"] == SESSIONS_PER_LOAD


# --- The selected scenario's latest run ---------------------------------------


def _latest_rows(model) -> list[str]:
    return [row["id"] for row in _of_kind(model, "run") if row["latest"]]


def test_the_row_of_the_last_run_played_is_the_one_marked_latest():
    runs = [
        *_minutes(0, 5, start=EVENING - timedelta(days=1)),
        *_minutes(0, 5, 10),
    ]

    model = _build(runs)

    assert _latest_rows(model) == [f"r:{run_id(runs[-1])}"]
    assert _latest_rows(model) == [f"r:{model['newest_run']}"]
    assert len(_of_kind(model, "run")) == 5


def test_the_selected_scenarios_latest_run_is_marked_when_another_was_last_played():
    """The global newest run remains the expansion token, separate from the highlight."""
    runs = [*_minutes(0, 5), *_minutes(10, scenario=B)]

    model = _build(runs)

    assert model["newest_run"] == run_id(runs[-1])
    assert _latest_rows(model) == [f"r:{run_id(runs[1])}"]
    assert _latest_rows(_build(runs, B)) == [f"r:{run_id(runs[-1])}"]


def test_a_run_that_lands_takes_the_mark_from_the_run_before_it():
    runs = _minutes(0, 5)
    landed = _run(A, EVENING + timedelta(minutes=9))

    before = _build(runs)
    after = _build([*runs, landed])

    assert _latest_rows(before) == [f"r:{run_id(runs[-1])}"]
    assert _latest_rows(after) == [f"r:{run_id(landed)}"]


# --- This scenario: a session row's link and inline figures --------------------


def test_a_session_row_gives_its_place_among_all_sessions_for_its_link():
    """Counting back from the newest, sessions with no run of the scenario too.

    It is how far back All scenarios loads to reach the session.
    """
    day = timedelta(days=1)
    runs = [
        *_minutes(0, start=EVENING - 3 * day),
        *_minutes(0, scenario=B, start=EVENING - 2 * day),
        *_minutes(0, scenario=B, start=EVENING - day),
        *_minutes(0, scenario=B),
    ]

    model = _build(runs)

    assert [(row["name"], row["place"]) for row in _of_kind(model, "session")] == [
        ("Oct 4, 9:44 PM", 1),
        ("Oct 1, 9:44 PM", 4),
    ]


def test_scenario_session_rows_have_no_length_hover():
    day = timedelta(days=1)
    runs = [*_minutes(0, start=EVENING - day), *_minutes(0, 2)]

    first, older = _of_kind(_build(runs), "session")

    assert not first.get("length_help")
    assert not older.get("length_help")


@pytest.mark.parametrize("in_progress", [True, False])
def test_every_scenario_session_row_keeps_its_figures_in_its_line(in_progress):
    day = timedelta(days=1)
    runs = [*_minutes(0, start=EVENING - day), *_minutes(0, 2)]

    now = runs[-1].datetime_object + timedelta(minutes=0 if in_progress else 31)
    first, older = _of_kind(_build(runs, now=now), "session")

    assert first["in_progress"] is in_progress
    assert not first.get("figures_below")
    assert not older.get("figures_below")


FIGURES_CASES = [
    ((3324.0,), "Score 3,324"),
    ((3324.0, 3422.0), "Median 3,373 · Best 3,422"),
    ((100.0, 120.5, 90.0), "Median 100 · Best 120.5"),
    ((100.0, 101.0, 90.0, 130.0), "Median 100.5 · Best 130"),
]
FIGURES_IDS = ["one", "two", "odd", "even"]
# The same figures as a session row under This scenario carries them, split
# at the decimal point for its columns.
FIGURE_PARTS = [
    {"score": ["3,324", ""]},
    {"median": ["3,373", ""], "best": ["3,422", ""]},
    {"median": ["100", ""], "best": ["120", ".5"]},
    {"median": ["100", ".5"], "best": ["130", ""]},
]


def _session(start: datetime, *scores: float, scenario: str = A) -> list[RunData]:
    """Build one session's runs of ``scenario``, two minutes apart, with these scores."""
    return [
        _run(scenario, start + timedelta(minutes=2 * index), score=score)
        for index, score in enumerate(scores)
    ]


@pytest.mark.parametrize(
    ("scores", "parts"),
    [(scores, parts) for (scores, _), parts in zip(FIGURES_CASES, FIGURE_PARTS)],
    ids=FIGURES_IDS,
)
def test_a_session_row_splits_its_median_and_best_at_the_decimal_point(scores, parts):
    runs = [*_session(EVENING, *scores), *_minutes(30, scenario=B)]

    assert _build(runs)["rows"][0]["figures"] == parts


def test_a_session_row_with_no_run_of_the_scenario_has_no_figures():
    runs = [*_minutes(0, start=EVENING - timedelta(days=1)), *_minutes(0, scenario=B)]

    first, older = _of_kind(_build(runs), "session")

    assert first["counts"] == "0 of 1 run"
    assert first["figures"] is None
    assert older["figures"] == {"score": ["100", ""]}


# --- This scenario: the figure columns -----------------------------------------


def test_the_columns_hold_the_widest_whole_number_and_decimals_of_each_column():
    """Whole numbers and decimals are sized apart, so the decimal points line up."""
    day = timedelta(days=1)
    runs = [
        *_session(EVENING - 2 * day, 10.0, 20.26),
        *_session(EVENING - day, 17080.0, 17080.0, 18980.5),
        *_session(EVENING, 300.0, 400.0),
    ]

    columns = _build(runs)["columns"]

    assert columns["median"] == ["17,080", ".13"]
    assert columns["best"] == ["18,980", ".26"]


def test_a_column_with_no_decimals_in_any_session_has_none_to_hold():
    runs = [*_session(EVENING - timedelta(days=1), 100.0, 2000.0), *_minutes(30)]

    columns = _build(runs)["columns"]

    assert columns["median"] == ["1,050", ""]
    assert columns["best"] == ["2,000", ""]


def test_the_columns_come_from_every_session_and_not_only_the_loaded_ones():
    """So Show older sessions never moves a column."""
    day = timedelta(days=1)
    oldest = EVENING - 3 * day
    runs = [
        *_session(oldest, 99990.0, 99999.5),
        *_minutes(*range(5, 15), scenario=B, start=oldest),
        *_session(oldest + timedelta(hours=2), 5.0),
        *_session(EVENING - 2 * day, 10.0, 20.0),
        *_session(EVENING - day, 10.0, 20.0),
        *_session(EVENING, 10.0, 20.0),
    ]

    model = _build(runs, limit=2)

    assert len(_of_kind(model, "session")) == 2
    assert model["columns"] == {
        "median": ["99,994", ".75"],
        "best": ["99,999", ".5"],
        "count": "2 of 12 runs",
        "one_run": True,
    }


def test_a_one_run_sessions_score_is_held_by_bests_column():
    runs = [
        *_session(EVENING - timedelta(days=1), 123456.0),
        *_session(EVENING, 10.0, 20.0),
    ]

    columns = _build(runs)["columns"]

    assert columns["best"] == ["123,456", ""]
    assert columns["median"] == ["15", ""]
    assert columns["one_run"] is True


def test_with_no_one_run_session_bests_label_holds_best_alone():
    runs = [*_session(EVENING - timedelta(days=1), 10.0, 20.0), *_minutes(30, 32)]

    assert _build(runs)["columns"]["one_run"] is False


def test_with_every_session_one_run_the_median_column_holds_nothing():
    runs = [*_session(EVENING - timedelta(days=1), 10.0), *_minutes(30)]

    columns = _build(runs)["columns"]

    assert columns["median"] == ["", ""]
    assert columns["best"] == ["100", ""]


def test_the_count_column_includes_the_first_rows_count():
    runs = [
        *_session(EVENING - timedelta(days=1), 10.0),
        *_session(EVENING, *[10.0] * 12),
    ]

    model = _build(runs)

    assert model["rows"][0]["counts"] == "12 of 12 runs"
    assert model["columns"]["count"] == "12 of 12 runs"


def test_with_the_first_row_alone_the_count_column_holds_its_count():
    assert _build(_minutes(0, 2))["columns"]["count"] == "2 of 2 runs"


def test_of_two_counts_as_long_the_one_with_more_digits_is_the_widest():
    """A comma is narrower than a digit, so ``100 of 100`` outdraws ``1 of 1,000``."""
    day = timedelta(days=1)
    crowded = EVENING - 2 * day
    runs = [
        *_session(crowded, 1.0),
        *[_run(B, crowded + timedelta(seconds=index + 1)) for index in range(999)],
        *_session(EVENING - day, *[1.0] * 100),
        *_minutes(30),
    ]

    model = _build(runs)

    counts = [row["counts"] for row in _of_kind(model, "session")[1:]]
    assert counts == ["100 of 100 runs", "1 of 1,000 runs"]
    assert model["columns"]["count"] == "100 of 100 runs"


def test_the_trees_model_and_an_empty_model_have_no_columns():
    assert _tree(_minutes(0, 2))["columns"] is None
    assert build_run_list([], A, SESSIONS_PER_LOAD, EVENING, {})["columns"] is None


# --- All scenarios: the tree ---------------------------------------------------


def _marks_for_every_scenario(runs: list[RunData]) -> dict:
    marks: dict = {}
    for scenario in {run.scenario for run in runs}:
        marks.update(
            mark_runs(
                in_play_order(run for run in runs if run.scenario == scenario),
                95.0,
                lambda _version: None,
            )
        )
    return marks


def _tree(
    runs: list[RunData],
    selected: str | None = A,
    *,
    limit: int = SESSIONS_PER_LOAD,
    now: datetime | None = None,
):
    """Build the tree as the page does, with every run of every scenario marked."""
    if now is None:
        now = max(run.datetime_object for run in runs)
    return build_session_tree(
        runs, selected, limit, now, _marks_for_every_scenario(runs)
    )


def _outline(model) -> list:
    """Read the tree top to bottom, one short value per row."""
    read = {
        "session": lambda row: row["name"],
        "scenario": lambda row: f"{row['number']}. {row['name']}",
        "run": lambda row: row["n"],
        "date": lambda row: row["text"],
        "more": lambda row: row["text"],
    }
    return [read[row["kind"]](row) for row in model["rows"]]


def test_a_return_gets_a_second_row_and_run_numbers_carry_on_across_visits():
    runs = [
        *_minutes(0, 2),
        *_minutes(4, scenario=B),
        *_minutes(6, 8, 10),
    ]

    model = _tree(runs)

    assert _outline(model) == [
        "Oct 4, 9:44 PM",
        "3. Scenario A",
        5,
        4,
        3,
        "2. Scenario B",
        1,
        "1. Scenario A",
        2,
        1,
    ]
    assert model["view"] == VIEW_ALL
    assert [row["counts"] for row in _of_kind(model, "scenario")] == [
        "3 runs",
        "1 run",
        "2 runs",
    ]


def test_a_run_has_the_same_number_in_both_views():
    runs = [*_minutes(0, 2), *_minutes(4, scenario=B), *_minutes(6, 8)]

    in_the_tree = {
        row["id"]: row["n"] for row in _of_kind(_tree(runs), "run") if row["sel"]
    }
    under_this_scenario = {row["id"]: row["n"] for row in _of_kind(_build(runs), "run")}

    assert in_the_tree == under_this_scenario


def test_the_tree_lists_every_session_newest_first_whatever_is_selected():
    day = timedelta(days=1)
    runs = [
        *_minutes(0, start=EVENING - 2 * day),
        *_minutes(0, scenario=B, start=EVENING - day),
        *_minutes(0, scenario=C),
    ]

    for selected in (A, None):
        assert [row["name"] for row in _of_kind(_tree(runs, selected), "session")] == [
            "Oct 4, 9:44 PM",
            "Oct 3, 9:44 PM",
            "Oct 2, 9:44 PM",
        ]


@pytest.mark.parametrize(
    ("runs", "counts"),
    [
        (_minutes(0), "1 run · 1 scenario"),
        (_minutes(0, 2, 4), "3 runs · 1 scenario"),
        ([*_minutes(0, 2), *_minutes(4, scenario=B)], "3 runs · 2 scenarios"),
        # Scenarios, not rows: a return is one scenario.
        (
            [*_minutes(0), *_minutes(2, scenario=B), *_minutes(4)],
            "3 runs · 2 scenarios",
        ),
    ],
    ids=["one run", "one scenario", "two scenarios", "a return"],
)
def test_a_session_row_gives_its_length_its_runs_and_its_scenarios(runs, counts):
    first = _tree(runs)["rows"][0]

    assert first["counts"] == counts
    assert first["length"]
    assert "place" not in first


def test_every_session_row_gives_its_length_and_only_the_first_its_hover():
    day = timedelta(days=1)
    runs = [*_minutes(0, 20, start=EVENING - day), *_minutes(0, 25, 50, 65)]

    first, older = _of_kind(_tree(runs), "session")

    assert (first["length"], first["length_help"], first["in_progress"]) == (
        "1 hr 6 min",
        True,
        True,
    )
    assert (older["length"], older["length_help"], older["in_progress"]) == (
        "21 min",
        False,
        False,
    )


def test_a_scenario_row_carries_its_star_where_a_new_pb_was_set():
    runs = [
        _run(A, EVENING, score=100.0),
        _run(B, EVENING + timedelta(minutes=2), score=50.0),
        _run(A, EVENING + timedelta(minutes=4), score=90.0),
        _run(A, EVENING + timedelta(minutes=6), score=120.0),
    ]

    stars = {row["number"]: row["new_pb"] for row in _of_kind(_tree(runs), "scenario")}

    # The second visit to A beat the first. A scenario's first run sets no
    # star.
    assert stars == {3: True, 2: False, 1: False}
    later = [
        *runs,
        _run(B, EVENING + timedelta(minutes=8), score=40.0),
        _run(A, EVENING + timedelta(minutes=10), score=110.0),
    ]
    stars = {row["number"]: row["new_pb"] for row in _of_kind(_tree(later), "scenario")}
    assert (stars[5], stars[4]) == (False, False)


def test_every_listed_scenario_is_marked_as_it_is_under_this_scenario():
    day = timedelta(days=1)
    runs = [
        _run(B, EVENING - day, score=100.0),
        _run(B, EVENING - day + timedelta(minutes=2), score=96.0),
        _run(A, EVENING, score=100.0),
        _run(B, EVENING + timedelta(minutes=2), score=97.0),
        _run(A, EVENING + timedelta(minutes=4), score=99.0),
        _run(B, EVENING + timedelta(minutes=6), score=120.0),
    ]

    def marks(model):
        return {
            row["id"]: (row["passed"], row["check_text"], row["new_pb"])
            for row in _of_kind(model, "run")
        }

    tree = marks(_tree(runs))
    for scenario in (A, B):
        assert marks(_build(runs, scenario)).items() <= tree.items()
    assert len(tree) == len(runs)


@pytest.mark.parametrize(("scores", "figures"), FIGURES_CASES, ids=FIGURES_IDS)
def test_a_scenario_row_gives_the_median_and_best_of_its_visits_runs(scores, figures):
    runs = [
        *_minutes(0, scenario=B, start=EVENING - timedelta(minutes=10)),
        *[
            _run(A, EVENING + timedelta(minutes=2 * index), score=score)
            for index, score in enumerate(scores)
        ],
    ]

    newest, older = _of_kind(_tree(runs), "scenario")

    assert newest["figures"] == figures
    assert older["figures"] == "Score 100"


def test_a_scenario_rows_figures_count_its_own_visit_alone():
    runs = [
        _run(A, EVENING, score=10.0),
        _run(A, EVENING + timedelta(minutes=2), score=20.0),
        _run(B, EVENING + timedelta(minutes=4)),
        _run(A, EVENING + timedelta(minutes=6), score=300.0),
    ]

    figures = [row["figures"] for row in _of_kind(_tree(runs), "scenario")]

    assert figures == ["Score 300", "Score 100", "Median 15 · Best 20"]


def test_a_scenario_row_keeps_its_figures_in_its_line():
    """The newest visit's row too: the newest session's length is on its session row."""
    runs = [*_minutes(0, start=EVENING - timedelta(days=1)), *_minutes(0), *_minutes(2)]

    scenario_rows = _of_kind(_tree(runs), "scenario")

    assert scenario_rows
    assert not any(row.get("figures_below") for row in scenario_rows)


def test_the_selected_scenarios_rows_carry_the_band_and_no_other_rows_do():
    runs = [*_minutes(0), *_minutes(2, scenario=B), *_minutes(4)]

    model = _tree(runs, A)

    assert [
        (row["kind"], row["sel"])
        for row in model["rows"]
        if row["kind"] in ("scenario", "run")
    ] == [
        ("scenario", True),
        ("run", True),
        ("scenario", False),
        ("run", False),
        ("scenario", True),
        ("run", True),
    ]
    assert not [row for row in _tree(runs, None)["rows"] if row.get("sel")]
    assert not [row for row in _tree(runs, C)["rows"] if row.get("sel")]


def test_a_scenario_rows_name_button_and_its_press_are_worded_as_the_copy_has_them():
    (row,) = _of_kind(_tree(_minutes(0)), "scenario")

    assert (row["name"], row["name_label"], row["selected_text"]) == (
        "Scenario A",
        "Show Scenario A",
        "Selected scenario: Scenario A",
    )


def test_the_tree_has_no_dividers_and_no_note_for_a_scenario_not_played():
    runs = [*_minutes(0), *_minutes(2, scenario=B), *_minutes(4)]

    assert set(_kinds(_tree(runs, C))) == {"session", "scenario", "run"}


def test_every_row_under_a_scenario_row_carries_its_id_and_its_sessions():
    runs = [
        *_minutes(0, start=LATE - timedelta(minutes=5)),
        *_minutes(0, 10, scenario=B, start=LATE + timedelta(minutes=20)),
    ]

    model = _tree(runs)

    session = model["rows"][0]
    scenario_ids = {row["id"] for row in _of_kind(model, "scenario")}
    for row in model["rows"][1:]:
        assert row["sid"] == session["id"]
        if row["kind"] != "scenario":
            assert row["vid"] in scenario_ids
    assert "vid" not in session
    assert not [row for row in _of_kind(model, "scenario") if "vid" in row]
    assert "date" in _kinds(model)


def test_a_scenario_row_is_keyed_by_its_visits_first_run():
    runs = [*_minutes(0, 2), *_minutes(4, scenario=B)]

    newest, older = _of_kind(_tree(runs), "scenario")

    assert (newest["id"], older["id"]) == (
        f"v:{run_id(runs[2])}",
        f"v:{run_id(runs[0])}",
    )


# --- All scenarios: date headers, asked of one scenario row at a time ------------


def _tree_texts_under(model, number: int) -> list:
    """Read one scenario row's runs and headers, top to bottom."""
    (scenario,) = [
        row for row in _of_kind(model, "scenario") if row["number"] == number
    ]
    return [
        row["text"] if row["kind"] == "date" else row["n"]
        for row in model["rows"]
        if row.get("vid") == scenario["id"]
    ]


def test_a_scenario_row_on_the_sessions_start_date_has_no_header():
    """The session's name already gives that date, though a later row crosses it."""
    runs = [
        *_minutes(0, 10, start=LATE),
        *_minutes(0, scenario=B, start=LATE + timedelta(minutes=40)),
    ]

    model = _tree(runs)

    assert _tree_texts_under(model, 1) == [2, 1]
    assert _tree_texts_under(model, 2) == ["Oct 12", 1]


def test_a_scenario_row_played_wholly_after_midnight_has_one_header():
    runs = [
        *_minutes(0, 20, start=LATE),
        *_minutes(35, 40, scenario=B, start=LATE),
    ]

    assert _tree_texts_under(_tree(runs), 2) == ["Oct 12", 2, 1]


def test_a_scenario_row_that_spans_midnight_has_a_header_for_each_date():
    runs = _minutes(0, 10, 35, 40, start=LATE)

    assert _tree_texts_under(_tree(runs), 1) == ["Oct 12", 4, 3, "Oct 11", 2, 1]


def test_a_single_run_that_crosses_midnight_gets_the_header_of_its_end():
    runs = [
        _run(A, LATE + timedelta(minutes=35), length=timedelta(minutes=10)),
        _run(B, LATE + timedelta(minutes=37)),
    ]

    model = _tree(runs, now=LATE + timedelta(minutes=38))

    assert model["rows"][0]["name"] == "Oct 11, 11:55 PM"
    assert _tree_texts_under(model, 1) == ["Oct 12", 1]
    assert _tree_texts_under(model, 2) == ["Oct 12", 1]


def test_a_scenario_row_in_a_session_that_crosses_a_year_names_the_other_year():
    new_years_eve = datetime(2026, 12, 31, 23, 50)

    model = _tree(_minutes(0, 20, start=new_years_eve), now=datetime(2027, 1, 1, 0, 11))

    assert _tree_texts_under(model, 1) == ["Jan 1", 2, "Dec 31, 2026", 1]


def test_a_date_header_under_a_scenario_row_is_keyed_by_that_row():
    model = _tree(_minutes(0, 20, 35, start=LATE))

    (scenario,) = _of_kind(model, "scenario")
    assert [row["id"] for row in _of_kind(model, "date")] == [
        f"d:{scenario['id']}:2026-10-12",
        f"d:{scenario['id']}:2026-10-11",
    ]


# --- All scenarios: the newest run, and the rows it opens ------------------------


def test_the_newest_run_opens_its_session_row_and_its_scenario_row():
    runs = [*_minutes(0, start=EVENING - timedelta(days=1)), *_minutes(0, 2)]

    model = _tree(runs)

    assert model["newest_run"] == run_id(runs[-1])
    session, scenario = model["rows"][:2]
    assert model["forced_open"] == [session["id"], scenario["id"]]
    assert scenario["kind"] == "scenario"


def test_a_run_that_carries_on_a_visit_opens_the_same_scenario_row():
    runs = _minutes(0, 2)
    landed = _run(A, EVENING + timedelta(minutes=4))

    before = _tree(runs)
    after = _tree([*runs, landed])

    assert after["newest_run"] == run_id(landed)
    assert after["forced_open"] == before["forced_open"]


def test_a_run_that_starts_a_new_visit_opens_a_new_scenario_row_numbered_next():
    runs = [*_minutes(0, 2), *_minutes(4, scenario=B)]
    landed = _run(A, EVENING + timedelta(minutes=6))

    before = _tree(runs)
    after = _tree([*runs, landed])

    assert after["forced_open"] == [after["rows"][0]["id"], f"v:{run_id(landed)}"]
    assert _of_kind(after, "scenario")[0]["number"] == 3
    # The row before it stays as it was.
    assert _of_kind(after, "scenario")[1] == _of_kind(before, "scenario")[0]


def test_a_run_that_lands_older_than_the_newest_and_splits_a_visit():
    """Its visit's runs either side of it become two rows, the newer under a new id."""
    runs = _minutes(0, 2, 6)
    late = _run(B, EVENING + timedelta(minutes=4))

    before = _tree(runs)
    after = _tree([*runs, late])

    (whole,) = _of_kind(before, "scenario")
    assert [row["id"] for row in _of_kind(after, "scenario")] == [
        f"v:{run_id(runs[2])}",
        f"v:{run_id(late)}",
        whole["id"],
    ]
    assert after["newest_run"] == before["newest_run"] == run_id(runs[2])
    assert after["forced_open"][1] == f"v:{run_id(runs[2])}"


@pytest.mark.parametrize(
    ("selected", "index"), [(A, 1), (B, 2), (None, None), (C, None)]
)
def test_the_tree_highlights_only_the_selected_scenarios_latest_run(selected, index):
    runs = [*_minutes(0, 2), *_minutes(4, scenario=B)]
    model = _tree(runs, selected)

    assert _latest_rows(model) == (
        [] if index is None else [f"r:{run_id(runs[index])}"]
    )
    assert model["newest_run"] == run_id(runs[-1])
    assert model["forced_open"] == _tree(runs, B)["forced_open"]


# --- All scenarios: thirty sessions at a time ------------------------------------


def test_the_tree_loads_thirty_sessions_of_its_own_and_offers_the_older_ones():
    runs = [
        *_one_run_a_day(35),
        # Five more sessions of another scenario: This scenario does not list
        # them, and the tree counts them among its thirty.
        *[
            run
            for back in range(5)
            for run in _minutes(
                30, scenario=B, start=EVENING - timedelta(days=back, hours=3)
            )
        ],
    ]

    tree = _tree(runs)
    second_load = _tree(runs, limit=2 * SESSIONS_PER_LOAD)

    assert len(_of_kind(tree, "session")) == 30
    assert tree["session_limit"] == 30
    assert _kinds(tree)[-1] == "more"
    assert len(_of_kind(second_load, "session")) == 40
    assert _of_kind(second_load, "more") == []
    scenario_sessions = _of_kind(_build(runs), "session")
    assert len(scenario_sessions) == 30
    # Ten of the sessions newer than the thirtieth are the other scenario's.
    assert scenario_sessions[-1]["place"] == 35


def test_a_tree_loaded_up_to_a_sessions_place_lists_it_last():
    runs = _one_run_a_day(40)
    asked = _of_kind(_build(runs, limit=40), "session")[34]

    tree = _tree(runs, limit=asked["place"])

    assert asked["place"] == 35
    assert _of_kind(tree, "session")[-1]["id"] == asked["id"]
    assert _kinds(tree)[-1] == "more"


# --- All scenarios: the heading and the grid's name ------------------------------


@pytest.mark.parametrize(
    ("offsets", "heading"),
    [((0,), "All scenarios · 1 run"), ((0, 2), "All scenarios · 2 runs")],
)
def test_the_trees_heading_counts_every_run_in_the_store(offsets, heading):
    assert _tree(_minutes(*offsets))["heading"] == heading


def test_the_trees_heading_counts_runs_beyond_the_loaded_sessions():
    assert _tree(_one_run_a_day(35))["heading"] == "All scenarios · 35 runs"


def test_the_trees_grid_is_named_for_all_scenarios():
    assert _tree(_minutes(0))["grid_name"] == "Runs of all scenarios, by session"


def test_an_empty_store_builds_an_empty_tree():
    model = build_session_tree([], A, SESSIONS_PER_LOAD, EVENING, {})

    assert (model["rows"], model["empty"], model["view"]) == (
        [],
        NO_RUNS_TEXT,
        VIEW_ALL,
    )
    assert model["newest_run"] is None


# --- Both views, from the run store ---------------------------------------------


def test_the_tree_from_the_store_needs_no_selected_scenario(store):
    store.extend([*_minutes(0), *_minutes(2, scenario=B)])

    model = run_list_from_store(VIEW_ALL, None, 30, 95, EVENING)

    assert model["empty"] is None
    assert model["view"] == VIEW_ALL
    assert [row["name"] for row in _of_kind(model, "scenario")] == [B, A]


def test_the_tree_from_the_store_marks_every_scenario_it_lists(store):
    store.extend(
        [
            _run(A, EVENING, score=100.0),
            _run(B, EVENING + timedelta(minutes=2), score=100.0),
            _run(A, EVENING + timedelta(minutes=4), score=96.0),
            _run(B, EVENING + timedelta(minutes=6), score=90.0),
        ]
    )

    model = run_list_from_store(VIEW_ALL, A, 30, 95, EVENING + timedelta(minutes=7))

    assert [(row["n"], row["passed"]) for row in _of_kind(model, "run")] == [
        (2, False),
        (2, True),
        (1, False),
        (1, False),
    ]


def test_the_tree_from_the_store_marks_only_the_scenarios_it_lists(store, monkeypatch):
    day = timedelta(days=1)
    store.extend([*_minutes(0, scenario=C, start=EVENING - day), *_minutes(0)])
    marked = []
    real = run_history_list._mark_scenario

    def mark(runs, scenario, goal):
        marked.append(scenario)
        return real(runs, scenario, goal)

    monkeypatch.setattr(run_history_list, "_mark_scenario", mark)

    run_list_from_store(VIEW_ALL, A, 1, 95, EVENING)

    assert marked == [A]


@pytest.mark.parametrize("view", [VIEW_SCENARIO, VIEW_ALL])
def test_an_empty_store_says_no_runs_yet_in_either_view(store, view):
    model = run_list_from_store(view, A, 30, 95, EVENING)

    assert (model["empty"], model["view"], model["newest_run"]) == (
        NO_RUNS_TEXT,
        view,
        None,
    )


def test_with_no_scenario_selected_the_model_still_names_the_newest_run(store):
    """Each view's mark starts from the first model a visit draws."""
    store.extend([*_minutes(0, 2), *_minutes(4, scenario=B)])

    model = run_list_from_store(VIEW_SCENARIO, None, 30, 95, EVENING)

    assert model["empty"] == NO_SCENARIO_TEXT
    assert model["newest_run"] == run_id(store[-1])
    assert (model["rows"], model["forced_open"]) == ([], [])


def test_each_view_is_built_with_the_count_of_sessions_it_was_given(store):
    store.extend(_one_run_a_day(35))

    assert run_list_from_store(VIEW_ALL, A, 60, 95, EVENING)["session_limit"] == 60
    assert run_list_from_store(VIEW_SCENARIO, A, 30, 95, EVENING)["session_limit"] == 30


@pytest.mark.parametrize("reversed_input", [False, True])
def test_late_runs_and_same_second_ties_keep_both_views_on_the_selected_latest(
    reversed_input,
):
    first = _run(A, EVENING, score=100.0)
    tied = _run(A, EVENING + timedelta(minutes=2), score=90.0)
    later_start = replace(
        tied,
        stats_file_name="later-start.csv",
        run_start=tied.datetime_object - timedelta(seconds=30),
        run_length=timedelta(seconds=30),
    )
    global_newest = _run(B, EVENING + timedelta(minutes=5))
    runs = [first, tied, global_newest]
    late = _run(A, EVENING + timedelta(minutes=3), score=80.0)
    older = _run(A, EVENING + timedelta(minutes=1), score=95.0)
    for added, expected in [(later_start, later_start), (late, late), (older, tied)]:
        stored = [*runs, added]
        if reversed_input:
            stored.reverse()
        for model in (_build(stored), _tree(stored)):
            assert _latest_rows(model) == [f"r:{run_id(expected)}"]
            assert model["newest_run"] == run_id(global_newest)
