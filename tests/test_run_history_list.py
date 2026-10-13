"""The rows the Run History page's run list shows.

The row model is one pure function over run records, so these tests build
records and read rows. What marks a run is ``tests/test_run_marks.py``.
"""

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
    build_run_list,
    is_session_in_progress,
    run_id,
    run_list_from_store,
)
from source.components.run_marks import mark_runs  # noqa: E402
from source.kovaaks.data_models import RunData  # noqa: E402
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
    # It is still the first row, and still gives its length.
    assert ended["rows"][0]["length"] == "11 min"
    assert [row["id"] for row in ended["rows"]] == [
        row["id"] for row in playing["rows"]
    ]


def test_only_the_first_row_gives_its_length_and_can_be_in_progress():
    day = timedelta(days=1)
    runs = [*_minutes(0, 20, start=EVENING - day), *_minutes(0, 25, 50, 65)]

    model = _build(runs)

    first, older = _of_kind(model, "session")
    # From the first run's start, a minute before it ended, to the last run's end.
    assert (first["length"], first["in_progress"]) == ("1 hr 6 min", True)
    assert (older["length"], older["in_progress"]) == (None, False)


@pytest.mark.parametrize(
    ("offsets", "length"),
    [
        ((0,), "1 min"),
        ((0, 8), "9 min"),
        ((0, 20, 40, 59), "1 hr"),
        ((0, 25, 50, 75, 100, 125), "2 hr 6 min"),
    ],
)
def test_the_session_length_counts_whole_minutes(offsets, length):
    assert _build(_minutes(*offsets))["rows"][0]["length"] == length


def test_a_session_of_one_short_run_is_under_a_minute():
    run = _run(A, EVENING, length=timedelta(seconds=40))

    assert _build([run])["rows"][0]["length"] == "<1 min"


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
        "n": 2,
        "time": "9:47 PM",
        "score": "3,324.5",
        "passed": True,
        "check_text": "Threshold passed",
        "new_pb": True,
        "accuracy": "55%",
        "shots": "1,234",
        "sens": "40.8 cm/360",
    }


@pytest.mark.parametrize(
    ("accuracy", "shown"),
    [(0.544, "54%"), (0.545, "55%"), (0.555, "56%"), (1.0, "100%"), (0.004, "0%")],
)
def test_accuracy_is_shown_to_the_whole_percent_a_half_rounding_up(accuracy, shown):
    run = _run(A, EVENING, accuracy=accuracy)

    assert _of_kind(_build([run]), "run")[0]["accuracy"] == shown


def test_a_run_with_no_shot_count_shows_none_and_not_zero():
    run = _run(A, EVENING, shots=None)

    assert _of_kind(_build([run]), "run")[0]["shots"] == ""


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
    assert run_list_from_store(A, 30, 95, EVENING)["empty"] == NO_RUNS_TEXT
    assert run_list_from_store(None, 30, 95, EVENING)["empty"] == NO_RUNS_TEXT


@pytest.mark.parametrize("scenario", [None, ""])
def test_no_selection_says_no_scenario_selected(store, scenario):
    store.extend(_minutes(0))

    model = run_list_from_store(scenario, 30, 95, EVENING)

    assert model["empty"] == NO_SCENARIO_TEXT
    assert model["rows"] == []


def test_a_scenario_with_no_local_runs_lists_the_newest_session_alone(store):
    store.extend(_minutes(0, 2, scenario=B))

    model = run_list_from_store(A, 30, 95, EVENING + timedelta(minutes=3))

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

    at_95 = run_list_from_store(A, 30, 95, now)
    at_99 = run_list_from_store(A, 30, 99, now)
    cleared = run_list_from_store(A, 30, "", now)

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
