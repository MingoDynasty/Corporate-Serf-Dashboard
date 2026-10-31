"""Tests for what the run viewer draws of a run, and for what opens and closes it.

Runs are written as stats files and loaded through the app's own parser, with
the run viewer reader's test helpers, so a run's record always agrees with
its file. What the reader works out is ``tests/test_run_viewer.py``; what
the browser does with the viewer is ``tests/test_run_viewer_browser.py``.
"""

import re
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import dash
import dash_ag_grid as dag
import dash_mantine_components as dmc
import pytest
from dash import dcc, html, no_update
from dash._callback import GLOBAL_CALLBACK_LIST

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.components import run_viewer_panel  # noqa: E402
from source.components.latest_run_card import CardBadge, score_line  # noqa: E402
from source.components.run_viewer_panel import (  # noqa: E402
    COLUMN_CLASS,
    COLUMN_OPEN_CLASS,
    ViewerContent,
    completion_time_text,
    recorded_groups,
    run_viewer_content,
    show_run,
)
from source.kovaaks.data_models import RunData  # noqa: E402
from source.kovaaks.play_sessions import in_play_order  # noqa: E402
from source.kovaaks.run_viewer import RunView, read_run_file  # noqa: E402
from source.kovaaks.time_scored_service import PaceBasis  # noqa: E402
from source.pages import run_history  # noqa: E402
from tests.rendered_text import rendered_text  # noqa: E402
from tests.test_run_viewer import (  # noqa: E402
    DAY_ONE,
    HASH,
    KILL_HEADER,
    SCENARIO,
    VIEWED_END,
    _clock,
    _scenario,
    _typical_ends,
    _view,
    _write_run,
)

TODAY = date(2026, 10, 30)


@pytest.fixture
def stats_dir(tmp_path) -> Path:
    folder = tmp_path / "stats"
    folder.mkdir()
    return folder


def _walk(component: Any):
    if isinstance(component, (list, tuple)):
        for child in component:
            yield from _walk(child)
        return
    if component is None or isinstance(component, (str, int, float)):
        return
    yield component
    yield from _walk(getattr(component, "children", None))
    for prop in ("rightSection",):
        yield from _walk(getattr(component, prop, None))


def _by_class(content: Any, class_name: str) -> list[Any]:
    return [
        component
        for component in _walk(content)
        if class_name in (getattr(component, "className", None) or "").split()
    ]


def _one(content: Any, class_name: str) -> Any:
    found = _by_class(content, class_name)
    assert len(found) == 1, f"{len(found)} components with {class_name!r}"
    return found[0]


def _drawn(
    view: RunView,
    runs: list[RunData],
    bases: Mapping[str, PaceBasis] | None = None,
    *,
    percentage: float | None = 95.0,
    today: date = TODAY,
) -> ViewerContent:
    """Draw the viewer for a run as the page does, from the runs of one store."""
    line = None
    if view.figures is not None:
        line = score_line(
            view.run,
            in_play_order(run for run in runs if run.scenario == view.run.scenario),
            view.figures.typical_score,
            view.session,
            percentage,
            lambda _scenario, version: (bases or {}).get(version or ""),
        )
    return run_viewer_content(view, line, today)


def _viewer(stats_dir, runs, viewed, bases=None, **options) -> ViewerContent:
    return _drawn(_view(stats_dir, runs, viewed, bases), runs, bases, **options)


def _tile(content: ViewerContent, label: str) -> dict[str, Any]:
    for tile in _by_class(content.body, "run-viewer-tile"):
        if rendered_text(_one(tile, "run-viewer-tile-label")) == label:
            typical = _one(tile, "run-viewer-tile-typical")
            difference = [
                child
                for child in _walk(typical.children)
                if isinstance(child, html.Span)
            ]
            return {
                "value": rendered_text(_one(tile, "run-viewer-tile-value")),
                "value_class": _one(tile, "run-viewer-tile-value").className,
                "typical": rendered_text(typical),
                "hover": getattr(typical, "title", None),
                "difference_class": difference[0].className if difference else None,
            }
    raise AssertionError(f"No {label} tile")


def _card(content: ViewerContent, label: str) -> html.Div:
    for card in _by_class(content.body, "run-viewer-card"):
        if rendered_text(_one(card, "run-viewer-card-label")) == label:
            return card
    raise AssertionError(f"No {label} card")


def _groups(content: ViewerContent) -> dict[str, Any]:
    return {
        rendered_text(_one(group, "run-viewer-group-heading")): group
        for group in _by_class(content.body, "run-viewer-group")
    }


def _table_rows(group: Any) -> list[list[str]]:
    tables = [c for c in _walk(group) if isinstance(c, dmc.Table)]
    assert len(tables) == 1
    return tables[0].data["body"]


# --- The header and the score line ---------------------------------------------


def test_the_header_names_the_scenario_the_end_and_the_runs_place_in_its_session(
    stats_dir,
) -> None:
    runs, viewed = _scenario(stats_dir)

    content = _viewer(stats_dir, runs, viewed)

    assert rendered_text(_one(content.heading, "run-viewer-kicker")) == (
        f"{SCENARIO} · ended Aug 6, 2026, 10:00:00 PM"
    )
    assert rendered_text(_one(content.heading, "run-viewer-title")) == (
        "Run 1 · Aug 6, 9:59 PM session"
    )


def test_the_title_counts_the_scenarios_runs_in_the_session_and_names_an_old_year(
    stats_dir,
) -> None:
    runs, _viewed = _scenario(stats_dir)
    second = _write_run(stats_dir, VIEWED_END + timedelta(minutes=2))
    runs.append(second)

    content = _viewer(stats_dir, runs, second, today=date(2027, 1, 2))

    assert rendered_text(_one(content.heading, "run-viewer-title")) == (
        "Run 2 · Aug 6, 2026, 9:59 PM session"
    )


def test_the_score_line_is_the_latest_run_cards_for_any_run(stats_dir) -> None:
    runs, viewed = _scenario(
        stats_dir, typical=lambda index: {"score": 1000.0 + index}, score=950.0
    )
    # A later PB does not change what the viewed run was measured against.
    runs.append(_write_run(stats_dir, VIEWED_END + timedelta(minutes=2), score=2000))

    content = _viewer(stats_dir, runs, viewed)

    line = _one(content.body, "run-viewer-score-line")
    assert rendered_text(line) == (
        "950 Below threshold 5.4% below typical at session start · 94.2% of PB"
    )
    badges = [c for c in _walk(line) if isinstance(c, dmc.Badge)]
    assert [badge.children for badge in badges] == ["Below threshold"]


def test_a_new_pb_reads_as_the_card_reads_one(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir, score=1500.0)

    line = score_line(
        viewed,
        in_play_order(runs),
        None,
        _view(stats_dir, runs, viewed).session,
        95.0,
        lambda _scenario, _version: None,
    )

    assert line.badge is CardBadge.NEW_PB
    assert line.typical is None
    assert line.pb_comparison == "Up 50.0% on your previous best of 1,000"


def test_a_file_that_cant_be_read_shows_the_header_and_says_so(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir)
    (stats_dir / viewed.stats_file_name).unlink()

    content = _viewer(stats_dir, runs, viewed)

    assert rendered_text(_one(content.heading, "run-viewer-title")).startswith("Run 1")
    assert rendered_text(content.body) == (
        "This run's file couldn't be read. See data/logs/debug.log."
    )


# --- The reference line --------------------------------------------------------


def test_the_reference_line_names_the_typical_runs_and_their_dates(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir)

    content = _viewer(stats_dir, runs, viewed)

    assert rendered_text(_one(content.body, "run-viewer-reference")) == (
        "Typical comes from your 10 runs before this session, "
        "played from Aug 4 to Aug 5."
    )
    old = _viewer(stats_dir, runs, viewed, today=date(2027, 3, 1))
    assert rendered_text(_one(old.body, "run-viewer-reference")) == (
        "Typical comes from your 10 runs before this session, "
        "played from Aug 4, 2026 to Aug 5, 2026."
    )


def test_the_reference_line_reads_one_date_when_the_runs_are_on_one(
    stats_dir,
) -> None:
    runs = [
        _write_run(stats_dir, DAY_ONE + timedelta(minutes=2 * index))
        for index in range(20)
    ]
    viewed = _write_run(stats_dir, VIEWED_END)
    runs.append(viewed)

    content = _viewer(stats_dir, runs, viewed)

    assert rendered_text(_one(content.body, "run-viewer-reference")) == (
        "Typical comes from your 20 runs before this session, played on Aug 4."
    )


def test_the_scenarios_first_session_has_no_typical_run(stats_dir) -> None:
    viewed = _write_run(stats_dir, VIEWED_END, score=1200.0)
    runs = [viewed]

    content = _viewer(stats_dir, runs, viewed)

    assert rendered_text(_one(content.body, "run-viewer-reference")) == (
        "This is the scenario's first session, so there's no typical run to "
        "compare with yet."
    )
    assert _tile(content, "Score")["typical"] == ""
    assert _tile(content, "Score")["hover"] is None
    assert not _by_class(content.body, "run-viewer-card-marked")


@pytest.mark.parametrize(("before", "words"), [(1, "1 run"), (3, "3 runs")])
def test_too_few_runs_before_the_session_say_how_many_there_were(
    stats_dir, before, words
) -> None:
    runs = [
        _write_run(stats_dir, DAY_ONE + timedelta(minutes=2 * index))
        for index in range(before)
    ]
    viewed = _write_run(stats_dir, VIEWED_END)
    runs.append(viewed)

    content = _viewer(stats_dir, runs, viewed)

    assert rendered_text(_one(content.body, "run-viewer-reference")) == (
        f"There's no typical run for this run's session yet: it had {words} before "
        "it, and a typical score needs 10 runs across 2 or more sessions, or 20 in "
        "one session."
    )
    assert _tile(content, "Accuracy")["typical"] == ""


# --- The tiles -----------------------------------------------------------------


def test_each_tile_shows_the_run_over_its_typical_and_the_difference(
    stats_dir,
) -> None:
    runs, viewed = _scenario(
        stats_dir,
        typical=lambda index: {"score": 1000.0 + index},
        score=1100.0,
        hits=40,
        fields={"Reloads": "3"},
    )

    content = _viewer(stats_dir, runs, viewed)

    # The typical score is shown to its runs' precision, half up, and the
    # difference is worked from the two values shown: 1,100 less 1,005.
    assert _tile(content, "Score") == {
        "value": "1,100",
        "value_class": "run-viewer-tile-value",
        "typical": "Typical 1,005 · +95",
        "hover": "Median of your 10 typical runs",
        "difference_class": "run-viewer-better",
    }
    assert _tile(content, "Accuracy")["value"] == "40.00%"
    assert _tile(content, "Accuracy")["typical"] == "Typical 50.00% · −10.00 pts"
    assert _tile(content, "Accuracy")["difference_class"] == "run-viewer-worse"
    # More shots is neither better nor worse.
    assert _tile(content, "Shots fired")["typical"] == "Typical 100 · 0"
    assert _tile(content, "Shots fired")["difference_class"] is None
    # Fewer reloads is better, so three more is worse.
    assert _tile(content, "Reloads")["typical"] == "Typical 0 · +3"
    assert _tile(content, "Reloads")["difference_class"] == "run-viewer-worse"
    labels = [
        rendered_text(_one(tile, "run-viewer-tile-label"))
        for tile in _by_class(content.body, "run-viewer-tile")
    ]
    assert labels == ["Score", "Accuracy", "Shots fired", "Reloads"]


def test_a_typical_some_runs_lack_counts_the_ones_it_took(stats_dir) -> None:
    runs, viewed = _scenario(
        stats_dir,
        typical=lambda index: {"fields": {"Reloads": None}} if index < 3 else {},
    )

    content = _viewer(stats_dir, runs, viewed)

    assert _tile(content, "Reloads")["hover"] == "Median of 7 of your 10 typical runs"


def test_a_figure_the_file_lacks_reads_not_recorded(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir, fields={"Reloads": None})

    content = _viewer(stats_dir, runs, viewed)

    reloads = _tile(content, "Reloads")
    assert reloads["value"] == "Not recorded"
    assert reloads["value_class"] == "run-viewer-tile-value run-viewer-unrecorded"
    assert reloads["typical"] == "Typical 0"


def test_time_shows_on_a_time_scored_version_and_faster_is_better(
    stats_dir,
) -> None:
    runs, viewed = _scenario(
        stats_dir, typical=lambda index: {"score": 10.0 + index}, score=12.55
    )

    content = _viewer(stats_dir, runs, viewed, {HASH: PaceBasis(70.0, HASH)})

    # 70 less the median of 10 to 19 is 55.5 s, and the run took 57.45 s.
    time = _tile(content, "Time")
    assert time["value"] == "0:57.5"
    assert time["typical"] == "Typical 0:55.5 · +2.0 s"
    assert time["difference_class"] == "run-viewer-worse"


def test_time_has_no_typical_when_a_typical_run_is_of_another_version(
    stats_dir,
) -> None:
    runs, viewed = _scenario(
        stats_dir,
        typical=lambda index: {"fields": {"Hash": "0" * 32}} if index == 0 else {},
        score=12.55,
    )

    content = _viewer(stats_dir, runs, viewed, {HASH: PaceBasis(70.0, HASH)})

    assert _tile(content, "Time") == {
        "value": "0:57.5",
        "value_class": "run-viewer-tile-value",
        "typical": "",
        "hover": None,
        "difference_class": None,
    }


def test_no_time_tile_on_a_version_not_known_to_be_time_scored(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir)

    content = _viewer(stats_dir, runs, viewed)

    assert "Time" not in [
        rendered_text(_one(tile, "run-viewer-tile-label"))
        for tile in _by_class(content.body, "run-viewer-tile")
    ]


@pytest.mark.parametrize(
    ("seconds", "text"),
    [("57.5", "0:57.5"), ("5.0", "0:05.0"), ("60.0", "1:00.0"), ("125.3", "2:05.3")],
)
def test_a_completion_time_reads_minutes_and_seconds_to_a_tenth(seconds, text) -> None:
    assert completion_time_text(Decimal(seconds)) == text


# --- By Bot --------------------------------------------------------------------

# Fly Bot 10 is killed first and Fly Bot 2 once, so play order, name order and
# a bot of one kill among bots of many all show. From the 21:59:00 start, Fly
# Bot takes 1.0 and 0.5 seconds, Fly Bot 2 takes 2.0, and Fly Bot 10 takes 1.0
# and 1.5.
FLY_KILLS = [
    ("21:59:01.000", "Fly Bot 10", 10, 5),
    ("21:59:02.000", "Fly Bot", 10, 8),
    ("21:59:04.000", "Fly Bot 2", 10, 6),
    ("21:59:05.500", "Fly Bot 10", 10, 5),
    ("21:59:06.000", "Fly Bot", 10, 9),
]

# Each bot is one kill, played out of name order.
ONE_KILL_EACH = [
    ("21:59:19.000", "Float 3 Bot", 1900, 684),
    ("21:59:39.500", "Bounce 1 Bot", 1975, 1013),
    ("21:59:59.750", "Bounce 2 Bot", 1972, 1158),
]

MANY_KILLS_SUBTITLE = (
    "Each kill's time runs from the kill before it, so it includes finding the bot."
)
TYPICAL_SUBTITLE = (
    "Typical is each bot's median over your typical runs. Difference is this run "
    "minus typical, in percentage points (pts) for accuracy."
)


def _fly_typical(index: int) -> dict:
    """A typical run: Fly Bot at 80% and Fly Bot 10 at 40%, a kill a second, never Fly Bot 2."""
    start = _typical_ends()[index] - timedelta(seconds=60)
    return {
        "kills": [
            (_clock(start + timedelta(seconds=second)), bot, 10, hits)
            for second, bot, hits in (
                (1, "Fly Bot 10", 4),
                (2, "Fly Bot", 8),
                (3, "Fly Bot 10", 4),
                (4, "Fly Bot", 8),
            )
        ]
    }


def _one_kill_typical(index: int) -> dict:
    """A typical run: each of the three bots at 50%, in the same order."""
    start = _typical_ends()[index] - timedelta(seconds=60)
    return {
        "kills": [
            (_clock(start + timedelta(seconds=second)), bot, 100, 50)
            for second, bot in (
                (19, "Float 3 Bot"),
                (39, "Bounce 1 Bot"),
                (59, "Bounce 2 Bot"),
            )
        ]
    }


def _by_bot(content: ViewerContent) -> dict[str, Any] | None:
    sections = _by_class(content.body, "run-viewer-by-bot")
    if not sections:
        return None
    (section,) = sections
    (grid,) = [c for c in _walk(section) if isinstance(c, dag.AgGrid)]
    notes = _by_class(section, "run-viewer-by-bot-note")
    return {
        "heading": rendered_text(_one(section, "run-viewer-heading")),
        "subtitle": rendered_text(_one(section, "run-viewer-subtitle")),
        "note": rendered_text(notes[0]) if notes else None,
        "grid": grid,
    }


def _headers(columns: list[dict]) -> list:
    """Each column's header, a group's as its name and its columns' headers."""
    return [
        (column["headerName"], [child["headerName"] for child in column["children"]])
        if "children" in column
        else column["headerName"]
        for column in columns
    ]


def _leaves(columns: list[dict]) -> dict[str, dict]:
    return {
        leaf["colId"]: leaf
        for column in columns
        for leaf in column.get("children", [column])
    }


def _cells(grid: dag.AgGrid, *keys: str) -> list[list]:
    """Each row's bot, then each named cell as it reads, in the rows' order."""
    return [
        [row["bot"], *(row.get(f"{key}_text", row.get(key)) for key in keys)]
        for row in grid.rowData
    ]


def _difference_class(column: dict, value: float | None) -> str | None:
    """Apply a Difference column's class rules to one value, as the grid does."""
    if value is None:
        return None
    for name, rule in column["cellClassRules"].items():
        if rule == "params.value === 0":
            matched = value == 0
        else:
            parts = re.fullmatch(r"params\.value \* (-?1) ([<>]) 0", rule)
            assert parts is not None, rule
            product = value * int(parts[1])
            matched = product > 0 if parts[2] == ">" else product < 0
        if matched:
            return name
    return None


def test_many_kills_show_time_per_kill_and_accuracy_in_name_order(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir, _fly_typical, kills=FLY_KILLS)

    by_bot = _by_bot(_viewer(stats_dir, runs, viewed))

    assert by_bot is not None
    assert by_bot["heading"] == "By Bot"
    assert by_bot["subtitle"] == f"{MANY_KILLS_SUBTITLE} {TYPICAL_SUBTITLE}"
    assert by_bot["note"] is None
    grid = by_bot["grid"]
    assert _headers(grid.columnDefs) == [
        "Bot",
        "Kills",
        ("Time per Kill", ["This Run", "Typical", "Difference"]),
        ("Accuracy", ["This Run", "Typical", "Difference"]),
    ]
    # Name order reads numbers as numbers. Fly Bot 2's one kill is still a
    # time per kill, and no typical run names it.
    assert _cells(
        grid,
        "kills",
        "time_per_kill",
        "time_per_kill_typical",
        "time_per_kill_difference",
    ) == [
        ["Fly Bot", 2, "0.75 s", "1.00 s", "−0.25 s"],
        ["Fly Bot 2", 1, "2.00 s", None, None],
        ["Fly Bot 10", 2, "1.25 s", "1.00 s", "+0.25 s"],
    ]
    assert _cells(grid, "accuracy", "accuracy_typical", "accuracy_difference") == [
        ["Fly Bot", "85.00%", "80.00%", "+5.00 pts"],
        ["Fly Bot 2", "60.00%", None, None],
        ["Fly Bot 10", "50.00%", "40.00%", "+10.00 pts"],
    ]


def test_each_cell_sorts_by_the_number_it_shows_and_a_typical_says_its_count(
    stats_dir,
) -> None:
    runs, viewed = _scenario(stats_dir, _fly_typical, kills=FLY_KILLS)

    grid = _by_bot(_viewer(stats_dir, runs, viewed))["grid"]

    fly, fly_2, fly_10 = grid.rowData
    assert (fly["time_per_kill"], fly["time_per_kill_typical"]) == (0.75, 1.0)
    assert fly["time_per_kill_difference"] == -0.25
    assert (fly["accuracy"], fly["accuracy_difference"]) == (85.0, 5.0)
    # An empty cell is a null, which the grid's comparator puts last.
    assert fly_2["time_per_kill_typical"] is None
    assert grid.defaultColDef["comparator"] == {"function": "nullsLastComparator"}
    assert grid.defaultColDef["sortable"] is True
    # The Bot column sorts by the server's name order.
    assert [row["bot_order"] for row in grid.rowData] == [0, 1, 2]
    assert _leaves(grid.columnDefs)["bot"]["comparator"] == {
        "function": "runViewerBotNameComparator"
    }
    assert fly["time_per_kill_typical_hover"] == "Median of your 10 typical runs"
    assert fly_2["time_per_kill_typical_hover"] is None
    assert _leaves(grid.columnDefs)["time_per_kill_typical"]["tooltipField"] == (
        "time_per_kill_typical_hover"
    )


def test_a_bots_difference_is_colored_by_which_way_is_better(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir, _fly_typical, kills=FLY_KILLS)

    grid = _by_bot(_viewer(stats_dir, runs, viewed))["grid"]

    leaves = _leaves(grid.columnDefs)
    fly, fly_2, fly_10 = grid.rowData
    time = leaves["time_per_kill_difference"]
    accuracy = leaves["accuracy_difference"]
    # A faster time is better, and so is a higher accuracy.
    assert _difference_class(time, fly["time_per_kill_difference"]) == (
        "run-viewer-better"
    )
    assert _difference_class(time, fly_10["time_per_kill_difference"]) == (
        "run-viewer-worse"
    )
    assert _difference_class(accuracy, fly["accuracy_difference"]) == (
        "run-viewer-better"
    )
    assert _difference_class(accuracy, -1.5) == "run-viewer-worse"
    assert _difference_class(time, 0.0) == "run-viewer-even"
    assert _difference_class(time, fly_2["time_per_kill_difference"]) is None


def test_a_typical_run_with_unknown_times_counts_toward_accuracy_only(
    stats_dir,
) -> None:
    def typical(index: int) -> dict:
        paused = {"Pause Duration": "1.0", "Pause Count": "1"} if index < 3 else {}
        return {**_fly_typical(index), "fields": paused}

    runs, viewed = _scenario(stats_dir, typical, kills=FLY_KILLS)

    fly = _by_bot(_viewer(stats_dir, runs, viewed))["grid"].rowData[0]

    assert fly["time_per_kill_typical_hover"] == "Median of 7 of your 10 typical runs"
    assert fly["accuracy_typical_hover"] == "Median of your 10 typical runs"


def test_time_scored_bots_show_their_splits_in_play_order(stats_dir) -> None:
    viewed = _write_run(stats_dir, VIEWED_END, score=10.0, kills=ONE_KILL_EACH)

    by_bot = _by_bot(
        _viewer(stats_dir, [viewed], viewed, {HASH: PaceBasis(70.0, HASH)})
    )

    assert by_bot is not None
    assert by_bot["subtitle"] == (
        "Each bot is one kill, in a set order, so these are the run's splits. A "
        "kill's time runs from the kill before it. Listed in the order the run "
        "plays them."
    )
    grid = by_bot["grid"]
    # The scenario's first session has no typical runs, so each figure is one
    # column, with no Typical or Difference.
    assert _headers(grid.columnDefs) == ["Bot", "Time", "Accuracy"]
    assert _cells(grid, "time", "accuracy") == [
        ["Float 3 Bot", "19.00 s", "36.00%"],
        ["Bounce 1 Bot", "20.50 s", "51.29%"],
        ["Bounce 2 Bot", "20.25 s", "58.72%"],
    ]
    assert "time_typical" not in grid.rowData[0]
    # Sorted by Bot, the rows would read in name order.
    assert [row["bot_order"] for row in grid.rowData] == [2, 0, 1]


def test_one_kill_per_bot_with_no_pace_basis_shows_accuracy_alone(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir, _one_kill_typical, kills=ONE_KILL_EACH)

    by_bot = _by_bot(_viewer(stats_dir, runs, viewed))

    assert by_bot is not None
    assert by_bot["subtitle"] == (
        "Each bot is one kill, so its time is shown only when the app knows this "
        "run was scored by completion time. Listed in the order the run plays "
        f"them. {TYPICAL_SUBTITLE}"
    )
    grid = by_bot["grid"]
    assert _headers(grid.columnDefs) == [
        "Bot",
        ("Accuracy", ["This Run", "Typical", "Difference"]),
    ]
    assert _cells(grid, "accuracy", "accuracy_typical", "accuracy_difference") == [
        ["Float 3 Bot", "36.00%", "50.00%", "−14.00 pts"],
        ["Bounce 1 Bot", "51.29%", "50.00%", "+1.29 pts"],
        ["Bounce 2 Bot", "58.72%", "50.00%", "+8.72 pts"],
    ]


@pytest.mark.parametrize(
    ("fields", "line"),
    [
        (
            {"Challenge Start": None},
            "Times aren't shown because this run's file has no start time.",
        ),
        (
            # Two seconds after the first kill.
            {"Challenge Start": "21:59:03.000"},
            "Times aren't shown because this run's file has times out of order.",
        ),
        (
            {"Pause Duration": "2.5", "Pause Count": "1"},
            "Times aren't shown because this run was paused, and its file doesn't "
            "say when.",
        ),
    ],
)
def test_a_run_whose_times_are_unknown_says_why_and_shows_no_time(
    stats_dir, fields, line
) -> None:
    runs, viewed = _scenario(stats_dir, _fly_typical, kills=FLY_KILLS, fields=fields)

    by_bot = _by_bot(_viewer(stats_dir, runs, viewed))

    assert by_bot is not None
    assert by_bot["note"] == line
    # No time cell, the typical's included, while the kills and accuracy stay.
    assert _cells(
        by_bot["grid"],
        "kills",
        "time_per_kill",
        "time_per_kill_typical",
        "time_per_kill_difference",
        "accuracy_difference",
    ) == [
        ["Fly Bot", 2, None, None, None, "+5.00 pts"],
        ["Fly Bot 2", 1, None, None, None, None],
        ["Fly Bot 10", 2, None, None, None, "+10.00 pts"],
    ]


def test_accuracy_alone_says_nothing_of_unknown_times(stats_dir) -> None:
    viewed = _write_run(
        stats_dir, VIEWED_END, kills=ONE_KILL_EACH, fields={"Challenge Start": None}
    )

    by_bot = _by_bot(_viewer(stats_dir, [viewed], viewed))

    assert by_bot is not None
    assert by_bot["note"] is None


@pytest.mark.parametrize(
    "kills",
    [
        [],
        [("21:59:20.000", "Solo Bot", 10, 5), ("21:59:40.000", "Solo Bot", 10, 5)],
    ],
    ids=["no kills", "one bot"],
)
def test_one_bot_or_none_shows_no_table_and_keeps_its_place(stats_dir, kills) -> None:
    runs, viewed = _scenario(stats_dir, kills=kills)
    other = _write_run(stats_dir, VIEWED_END + timedelta(minutes=2), kills=FLY_KILLS)
    runs.append(other)

    without = _viewer(stats_dir, runs, viewed)
    with_table = _viewer(stats_dir, runs, other)

    assert _by_bot(without) is None
    assert _by_bot(with_table) is not None
    # A hidden placeholder holds By Bot's place, so Everything Recorded keeps
    # its own between the two runs.
    place = [
        index
        for index, child in enumerate(with_table.body)
        if "run-viewer-by-bot" in (getattr(child, "className", None) or "")
    ]
    assert len(place) == 1
    assert without.body[place[0]].hidden is True
    assert len(without.body) == len(with_table.body)
    assert isinstance(without.body[-1], html.Details)
    assert isinstance(with_table.body[-1], html.Details)


def test_each_run_draws_a_grid_of_its_own(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir, kills=FLY_KILLS)
    other = _write_run(stats_dir, VIEWED_END + timedelta(minutes=2), kills=FLY_KILLS)
    runs.append(other)

    ids = {_by_bot(_viewer(stats_dir, runs, run))["grid"].id for run in (viewed, other)}

    assert len(ids) == 2
    assert all(grid_id.startswith("run-viewer-by-bot-") for grid_id in ids)


# --- Settings ------------------------------------------------------------------


def test_settings_show_eleven_cards_in_the_ruled_order(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir)

    content = _viewer(stats_dir, runs, viewed)

    cards = _by_class(content.body, "run-viewer-card")
    assert [rendered_text(_one(card, "run-viewer-card-label")) for card in cards] == [
        "Sensitivity",
        "Vertical sensitivity",
        "DPI",
        "FOV",
        "Crosshair",
        "Crosshair scale",
        "Hide gun",
        "Resolution",
        "Resolution scale",
        "Frame cap",
        "Input lag",
    ]
    assert [rendered_text(_one(card, "run-viewer-card-value")) for card in cards] == [
        "45.0 cm/360",
        "Same as horizontal",
        "1600",
        "103 Overwatch",
        "0snowi_nicedot",
        "1.6",
        "No",
        "3840x2160",
        "100%",
        "999",
        "0",
    ]
    unmarked = _card(content, "Crosshair")
    assert unmarked.className == "run-viewer-card"
    assert unmarked.title == "0snowi_nicedot"
    assert rendered_text(_one(unmarked, "run-viewer-card-typical")) == ""


def test_a_changed_setting_is_marked_with_its_typical_value(stats_dir) -> None:
    runs, viewed = _scenario(
        stats_dir,
        typical=lambda index: (
            {"fields": {"Crosshair Scale": "2.0"}} if index < 3 else {}
        ),
        fields={"Crosshair Scale": "2.0"},
    )

    content = _viewer(stats_dir, runs, viewed)

    card = _card(content, "Crosshair scale")
    assert card.className == "run-viewer-card run-viewer-card-marked"
    assert rendered_text(_one(card, "run-viewer-card-typical")) == "Typical 1.6"
    assert card.title == "2.0\nTypical 1.6 · on 7 of your 10 typical runs"


def test_a_2019_run_reads_not_recorded_and_is_never_marked(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir, typical=lambda _index: {"old": True}, old=True)

    content = _viewer(stats_dir, runs, viewed)

    for label in ("DPI", "Resolution", "Resolution scale"):
        card = _card(content, label)
        assert card.className == "run-viewer-card run-viewer-card-unrecorded"
        assert rendered_text(_one(card, "run-viewer-card-value")) == "Not recorded"
        assert card.title == (
            "The run file doesn't have this setting. Older versions of KovaaK's "
            "didn't record it."
        )
    assert not _by_class(content.body, "run-viewer-card-marked")


# --- Everything Recorded -------------------------------------------------------


def test_everything_recorded_is_closed_and_groups_every_field(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir, fields={"Future Counter": "7"})

    content = _viewer(stats_dir, runs, viewed)

    recorded = _one(content.body, "run-viewer-recorded")
    assert isinstance(recorded, html.Details)
    assert not getattr(recorded, "open", None)
    assert rendered_text(recorded.children[0]) == "Everything Recorded"
    assert rendered_text(recorded.children[1]) == (
        "The run file as KovaaK's wrote it, grouped by kind."
    )
    groups = _groups(content)
    assert list(groups) == [
        "Result",
        "Other Counters",
        "Run",
        "Settings",
        "Other",
        "Files",
        "Weapons",
        "Kills",
    ]
    assert _table_rows(groups["Result"])[0] == ["Score", "1000.0"]
    assert _table_rows(groups["Other"]) == [["Future Counter", "7"]]
    file = read_run_file(stats_dir / viewed.stats_file_name)
    assert file is not None
    grouped = [
        key for _name, fields, _folds in recorded_groups(file) for key, _value in fields
    ]
    assert sorted(grouped) == sorted(key for key, _value in file.fields)


def test_a_group_of_zeros_folds_to_one_line(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir)

    content = _viewer(stats_dir, runs, viewed)

    assert rendered_text(_groups(content)["Other Counters"]) == (
        "Other CountersAll zero: Midairs, Midaired, Directs, Directed, "
        "Distance Traveled, MBS Points"
    )


@pytest.mark.parametrize(
    "fields",
    [
        # A field the file doesn't have isn't zero.
        {"MBS Points": None},
        # Nor is one it has with no value.
        {"Midairs": ""},
        {"Directs": "2"},
    ],
)
def test_a_missing_empty_or_nonzero_field_keeps_its_group_open(
    stats_dir, fields
) -> None:
    runs, viewed = _scenario(stats_dir, fields=fields)

    content = _viewer(stats_dir, runs, viewed)

    group = _groups(content)["Other Counters"]
    assert "All zero" not in rendered_text(group)
    assert ["Midaired", "0"] in _table_rows(group)


def test_files_name_the_run_file_and_whether_a_performance_file_was_found(
    stats_dir,
) -> None:
    runs, viewed = _scenario(stats_dir)

    found = _drawn(_view(stats_dir, runs, viewed, None, lambda _run: True), runs)
    missing = _viewer(stats_dir, runs, viewed)

    assert _table_rows(_groups(found)["Files"]) == [
        ["Run file", viewed.stats_file_name],
        ["Performance file", "Found"],
    ]
    assert _table_rows(_groups(missing)["Files"])[1] == ["Performance file", "None"]


def test_the_kill_table_shows_every_column_in_file_order_as_data(stats_dir) -> None:
    runs, viewed = _scenario(
        stats_dir,
        kills=[
            ("21:59:19.000", "Bounce 1 Bot", 1900, 684),
            ("21:59:39.000", "Float 3 Bot", 1972, 1158),
        ],
    )

    content = _viewer(stats_dir, runs, viewed)

    tables = [c for c in _walk(_groups(content)["Kills"]) if isinstance(c, dmc.Table)]
    assert len(tables) == 1
    assert tables[0].data["head"] == KILL_HEADER.split(",")
    assert [row[2] for row in tables[0].data["body"]] == ["Bounce 1 Bot", "Float 3 Bot"]


def test_a_run_with_no_kill_table_says_so(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir)

    content = _viewer(stats_dir, runs, viewed)

    assert rendered_text(_groups(content)["Kills"]) == (
        "KillsThis run's file records no kills."
    )


# --- Opening and closing -------------------------------------------------------

NOW = datetime(2026, 10, 30, 12, 0)
DRAWN = ViewerContent(["heading"], ["body"])
UNCHANGED = (no_update,) * 5


@pytest.fixture
def drawn(monkeypatch) -> list[str]:
    """Draw every run as ``DRAWN``, and record which runs were drawn."""
    asked: list[str] = []

    def draw(viewed_run_id, _percentage, _now):
        asked.append(viewed_run_id)
        return DRAWN

    monkeypatch.setattr(run_viewer_panel, "run_viewer_from_store", draw)
    return asked


def _request(run: str, source: str = "list") -> dict:
    return {"run_id": run, "from": source, "at": 1}


def _held(run: str, source: str = "list", selected: str = "A") -> dict:
    return {"run_id": run, "from": source, "selected": selected}


def test_a_run_opens_in_the_charts_place_with_focus_on_close(drawn) -> None:
    result = show_run("request", _request("r1"), "A", None, 95.0, NOW)

    assert result == (
        _held("r1"),
        COLUMN_OPEN_CLASS,
        ["heading"],
        ["body"],
        {"open": "r1", "focus": "close", "run": "r1"},
    )
    assert drawn == ["r1"]


def test_another_run_pressed_in_the_list_switches_and_leaves_focus(drawn) -> None:
    result = show_run("request", _request("r2"), "A", _held("r1", "chart"), 95, NOW)

    assert result == (
        _held("r2"),
        COLUMN_OPEN_CLASS,
        ["heading"],
        ["body"],
        {"open": "r2", "focus": None, "run": "r2"},
    )


@pytest.mark.parametrize(("source", "focus"), [("list", "row"), ("chart", "chart")])
def test_close_brings_the_chart_back_and_focus_to_what_opened_the_run(
    drawn, source, focus
) -> None:
    result = show_run("close", None, "A", _held("r1", source), 95.0, NOW)

    assert result == (
        None,
        COLUMN_CLASS,
        [],
        [],
        {"open": None, "focus": focus, "run": "r1"},
    )


def test_a_change_of_scenario_closes_the_run_and_leaves_focus(drawn) -> None:
    result = show_run("selection", None, "B", _held("r1"), 95.0, NOW)

    assert result == (
        None,
        COLUMN_CLASS,
        [],
        [],
        {"open": None, "focus": None, "run": "r1"},
    )


def test_the_same_scenario_written_again_keeps_the_run_open(drawn) -> None:
    # As when a run lands with Follow on.
    assert show_run("selection", None, "A", _held("r1"), 95.0, NOW) == UNCHANGED


def test_a_run_of_another_scenario_opens_without_the_selection_moving(drawn) -> None:
    opened = show_run("request", _request("other"), "A", None, 95.0, NOW)

    assert opened[0] == _held("other", selected="A")
    assert show_run("selection", None, "A", opened[0], 95.0, NOW) == UNCHANGED


@pytest.mark.parametrize("trigger", ["close", "selection", None])
def test_with_no_run_open_nothing_changes(drawn, trigger) -> None:
    assert show_run(trigger, None, "B", None, 95.0, NOW) == UNCHANGED
    assert show_run("request", None, "B", None, 95.0, NOW) == UNCHANGED
    assert drawn == []


def test_the_open_run_pressed_again_changes_only_where_close_returns(drawn) -> None:
    same = show_run("request", _request("r1"), "A", _held("r1"), 95.0, NOW)
    from_list = show_run(
        "request", _request("r1", "list"), "A", _held("r1", "chart"), 95.0, NOW
    )

    assert same == UNCHANGED
    assert from_list == (_held("r1"), *UNCHANGED[1:])
    assert drawn == []


def test_a_run_the_store_doesnt_hold_opens_nothing(monkeypatch) -> None:
    monkeypatch.setattr(
        run_viewer_panel, "run_viewer_from_store", lambda *_arguments: None
    )

    assert show_run("request", _request("gone"), "A", None, 95.0, NOW) == UNCHANGED
    assert show_run("request", _request("gone"), "A", _held("r1"), 95.0, NOW)[0] is None


# --- On the page ---------------------------------------------------------------


def _layout_components():
    def walk(component):
        yield component
        children = getattr(component, "children", None)
        if isinstance(children, (list, tuple)):
            for child in children:
                yield from walk(child)
        elif children is not None and not isinstance(children, str):
            yield from walk(children)

    return list(walk(run_history.layout()))


def test_the_viewer_is_the_chart_columns_last_child_and_starts_hidden() -> None:
    column = next(
        component
        for component in _layout_components()
        if getattr(component, "id", None) == run_history.CHART_COLUMN_ID
    )

    assert column.className == COLUMN_CLASS
    viewer = column.children[-1]
    assert viewer.id == run_history.RUN_VIEWER_IDS.viewer
    assert viewer.className == "run-viewer"
    assert viewer.to_plotly_json()["props"]["data-request-store"] == (
        run_history.RUN_VIEWER_IDS.request
    )
    assert viewer.to_plotly_json()["props"]["data-return-focus"] == (
        run_history.CHART_MODE_ID
    )


def test_the_open_run_is_kept_in_no_store_that_outlives_the_page() -> None:
    ids = run_history.RUN_VIEWER_IDS
    stores = {
        component.id: component
        for component in _layout_components()
        if isinstance(component, dcc.Store)
    }

    for store_id in (ids.request, ids.open, ids.shown):
        # Unset is the default, "memory": a reload forgets it.
        assert getattr(stores[store_id], "storage_type", "memory") == "memory"


def test_opening_and_closing_never_write_the_chart() -> None:
    ids = run_history.RUN_VIEWER_IDS
    specs = [
        spec
        for spec in GLOBAL_CALLBACK_LIST
        if f"{ids.open}.data" in spec["output"] or f"{ids.shown_sink}" in spec["output"]
    ]

    assert len(specs) == 2
    graph = run_history.CHART_OPTIONS_IDS
    for spec in specs:
        assert graph.graph not in spec["output"]
        assert graph.cached_plot not in spec["output"]
    show = next(spec for spec in specs if f"{ids.open}.data" in spec["output"])
    assert [item["id"] for item in show["inputs"]] == [
        ids.request,
        ids.close,
        run_history.SCENARIO_SELECTION_IDS.scenario_dropdown,
    ]
    assert show["prevent_initial_call"] is True
