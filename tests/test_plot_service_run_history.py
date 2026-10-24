"""The three figures of the Run History chart, as ``plot_service`` builds them.

Score vs Run, Score vs Time, and Score vs Sensitivity each plot every run
they are given: one point a run, a star on each new PB where the mode has
stars, the scenario's name as the title, and no line that sums the runs up.
Which runs they are given is ``tests/test_run_history_chart.py``.
"""

import json
from dataclasses import replace
from datetime import date, datetime, timedelta

import plotly.graph_objs as go
import pytest

from source.kovaaks.data_models import Rank, RecordedSensitivity, RunData
from source.plot import plot_service
from source.plot.plot_service import (
    LATEST_RUN_RING_SIZE_DEFAULT_PX,
    LATEST_RUN_RING_SIZE_PRESET_PX,
    LATEST_RUN_TRACE_NAME,
    NEW_PB_SIZE_DEFAULT_PX,
    NEW_PB_SIZE_PRESET_PX,
    NEW_PB_TRACE_NAME,
    POINT_SIZE_PRESET_PX,
    RUN_DATA_POINT_TRACE_NAME,
    apply_point_appearance,
    generate_score_vs_run_plot,
    generate_score_vs_sensitivity_plot,
    generate_score_vs_time_plot,
    latest_run_ring_opacity,
    show_latest_run_ring,
)

SCENARIO = "1w4ts"
TODAY = date(2026, 10, 12)
NOON = datetime(2026, 10, 10, 12, 0, 0)
LADDER = [
    Rank(name="Bronze", color="#aa7744", threshold=90.0),
    Rank(name="Silver", color="#cccccc", threshold=110.0),
]
RUN_POINT_HOVER = (
    "%{customdata[0]}<br><br>"
    "<b>Score</b>: %{y}<br>"
    "<b>Overall run</b>: %{customdata[2]}<br>"
    "<b>Session run</b>: %{customdata[1]} of %{customdata[3]}"
)


def _run(
    score: float,
    when: datetime,
    *,
    sens: float = 40.8,
    accuracy: float = 0.5,
    recorded: RecordedSensitivity | None = None,
) -> RunData:
    return RunData(
        datetime_object=when,
        score=score,
        sens_scale="cm/360",
        horizontal_sens=sens,
        scenario=SCENARIO,
        accuracy=accuracy,
        recorded_sensitivity=recorded,
    )


def _score_vs_run(runs, *, first_run_number=1, new_pbs=(), ranks=(), today=TODAY):
    return generate_score_vs_run_plot(
        runs,
        first_run_number,
        SCENARIO,
        True,
        list(ranks),
        False,
        new_pbs,
        today,
        run_numbers={
            run: (index, index, len(runs)) for index, run in enumerate(runs, 1)
        },
    )


def _score_vs_time(runs, *, new_pbs=(), ranks=()):
    return generate_score_vs_time_plot(
        runs,
        SCENARIO,
        True,
        list(ranks),
        False,
        new_pbs,
        run_numbers={
            run: (index, index, len(runs)) for index, run in enumerate(runs, 1)
        },
    )


def _score_vs_sensitivity(runs, *, ranks=()):
    return generate_score_vs_sensitivity_plot(
        runs,
        SCENARIO,
        True,
        list(ranks),
        False,
        run_numbers={
            run: (index, index, len(runs)) for index, run in enumerate(runs, 1)
        },
    )


def _three_runs() -> list[RunData]:
    return [
        _run(100.0, NOON),
        _run(120.0, NOON + timedelta(minutes=5)),
        _run(110.0, NOON + timedelta(days=1)),
    ]


# One builder per mode, called with the same runs, for what all three share.
EVERY_MODE = pytest.mark.parametrize(
    "build",
    [_score_vs_run, _score_vs_time, _score_vs_sensitivity],
    ids=["score_vs_run", "score_vs_time", "score_vs_sensitivity"],
)


def _trace(figure: go.Figure, name: str):
    (trace,) = [trace for trace in figure.data if trace.name == name]
    return trace


# --- What the three modes share ----------------------------------------------


@EVERY_MODE
def test_the_title_is_the_scenarios_name_alone(build) -> None:
    """No "updated" stamp: the title is kept for an exported chart."""
    assert build(_three_runs()).layout.title.text == SCENARIO


@EVERY_MODE
def test_every_run_given_is_one_point(build) -> None:
    runs = _three_runs()

    points = _trace(build(runs), RUN_DATA_POINT_TRACE_NAME)

    assert sorted(points.y) == [100.0, 110.0, 120.0]
    assert points.mode == "markers"


@EVERY_MODE
def test_no_trace_sums_the_runs_up(build) -> None:
    """The Average score line is gone, and nothing replaces it."""
    figure = build(_three_runs())

    assert [trace.name for trace in figure.data] == [RUN_DATA_POINT_TRACE_NAME]


@EVERY_MODE
def test_the_run_points_keep_their_legend_entry(build) -> None:
    """A lone trace has no legend entry unless it asks for one."""
    assert _trace(build(_three_runs()), RUN_DATA_POINT_TRACE_NAME).showlegend is True


@EVERY_MODE
def test_the_legend_sits_above_the_plot(build) -> None:
    legend = build(_three_runs()).layout.legend

    assert (legend.orientation, legend.x, legend.xanchor) == ("h", 1, "right")
    assert (legend.y, legend.yanchor) == (1.02, "bottom")


@EVERY_MODE
def test_the_point_hover_is_compact_and_keeps_the_exact_timestamp(
    build,
) -> None:
    run = _run(101.5, datetime(2026, 10, 10, 21, 4, 22), accuracy=0.51234)

    points = _trace(build([run]), RUN_DATA_POINT_TRACE_NAME)

    sensitivity_line = (
        "<br><b>Sensitivity</b>: %{x}" if build == _score_vs_sensitivity else ""
    )
    assert (
        points.hovertemplate == RUN_POINT_HOVER + sensitivity_line + "<extra></extra>"
    )
    assert "Date" not in points.hovertemplate
    assert list(points.customdata[0]) == [
        "Oct 10, 2026, 9:04:22 PM",
        "1",
        "1",
        "1",
    ]
    assert points.hoverlabel.font.size == 16


@EVERY_MODE
def test_a_converted_runs_chart_hover_omits_the_recorded_setting(build) -> None:
    run = _run(
        100.0,
        NOON,
        recorded=RecordedSensitivity(value=0.2, scale="Valorant", dpi=1600.0),
    )

    points = _trace(build([run]), RUN_DATA_POINT_TRACE_NAME)

    assert list(points.customdata[0]) == ["Oct 10, 2026, 12:00:00 PM", "1", "1", "1"]
    assert "Accuracy" not in points.hovertemplate


def test_run_numbers_use_thousands_separators() -> None:
    run = _run(100.0, NOON)
    figure = generate_score_vs_time_plot(
        [run],
        SCENARIO,
        False,
        [],
        False,
        (),
        run_numbers={run: (1234, 5678, 2345)},
    )
    assert list(_trace(figure, RUN_DATA_POINT_TRACE_NAME).customdata[0][1:]) == [
        "1,234",
        "5,678",
        "2,345",
    ]


@EVERY_MODE
def test_the_playlists_rank_lines_are_drawn_over_the_plotted_scores(build) -> None:
    figure = build(_three_runs(), ranks=LADDER)

    assert [annotation.text for annotation in figure.layout.annotations] == [
        "Bronze (90) ",
        "Silver (110) ",
    ]


@EVERY_MODE
def test_the_point_preferences_restyle_the_run_points_by_name(build) -> None:
    figure = apply_point_appearance(build(_three_runs()), "Large", "#f03e3e")

    marker = _trace(figure, RUN_DATA_POINT_TRACE_NAME).marker
    assert (marker.size, marker.color) == (POINT_SIZE_PRESET_PX["Large"], "#f03e3e")


# --- Score vs Run -------------------------------------------------------------


def test_score_vs_run_spaces_the_runs_evenly_in_the_order_given() -> None:
    """A busy day and a quiet month each take the room their runs need."""
    runs = [
        _run(100.0, NOON),
        _run(120.0, NOON + timedelta(seconds=30)),
        _run(110.0, NOON + timedelta(days=40)),
    ]

    figure = _score_vs_run(runs)

    points = _trace(figure, RUN_DATA_POINT_TRACE_NAME)
    assert list(points.x) == [1, 2, 3]
    assert list(points.y) == [100.0, 120.0, 110.0]
    assert figure.layout.xaxis.title.text == "Run"


def test_score_vs_run_numbers_a_run_by_its_place_in_the_whole_history() -> None:
    """So a run keeps its position when the range around it changes."""
    points = _trace(
        _score_vs_run(_three_runs(), first_run_number=364), RUN_DATA_POINT_TRACE_NAME
    )

    assert list(points.x) == [364, 365, 366]


def test_score_vs_run_labels_the_first_plotted_run_of_each_day_with_its_date() -> None:
    runs = [
        _run(100.0, NOON),
        _run(101.0, NOON + timedelta(minutes=2)),
        _run(102.0, NOON + timedelta(days=1)),
        _run(103.0, NOON + timedelta(days=2)),
        _run(104.0, NOON + timedelta(days=2, minutes=2)),
    ]

    xaxis = _score_vs_run(runs, first_run_number=10).layout.xaxis

    assert xaxis.tickmode == "array"
    assert list(xaxis.tickvals) == [10, 12, 13]
    assert list(xaxis.ticktext) == ["Oct 10", "Oct 11", "Oct 12"]


def test_a_date_label_in_another_year_carries_its_year() -> None:
    runs = [
        _run(100.0, datetime(2025, 12, 30, 22, 50)),
        _run(101.0, datetime(2026, 1, 2, 9, 0)),
    ]

    xaxis = _score_vs_run(runs).layout.xaxis

    assert list(xaxis.ticktext) == ["Dec 30, 2025", "Jan 2"]


def test_one_plotted_run_gets_one_label() -> None:
    xaxis = _score_vs_run([_run(100.0, NOON)], first_run_number=7).layout.xaxis

    assert (list(xaxis.tickvals), list(xaxis.ticktext)) == ([7], ["Oct 10"])


def _label_width(label: str) -> float:
    return (
        len(label) * plot_service._RUN_AXIS_LABEL_CHARACTER_PX
        + plot_service._RUN_AXIS_LABEL_MARGIN_PX
    )


@pytest.mark.parametrize("first_day", [date(2026, 8, 1), date(2025, 11, 20)])
def test_score_vs_run_thins_its_date_labels_so_they_do_not_collide(first_day) -> None:
    """Sixty days of one run each: far more dates than the axis has room for.

    The second case crosses a year, so some labels are twice as wide.
    """
    start = datetime.combine(first_day, datetime.min.time())
    runs = [_run(100.0, start + timedelta(days=day, hours=20)) for day in range(60)]

    xaxis = _score_vs_run(runs).layout.xaxis

    positions, labels = list(xaxis.tickvals), list(xaxis.ticktext)
    assert 1 < len(positions) < 60
    pixels_per_run = plot_service._RUN_AXIS_ASSUMED_PLOT_WIDTH_PX / 59
    for (left, left_label), (right, right_label) in zip(
        zip(positions, labels, strict=True),
        zip(positions[1:], labels[1:], strict=True),
        strict=False,
    ):
        room = (right - left) * pixels_per_run
        assert room >= (_label_width(left_label) + _label_width(right_label)) / 2


def test_the_newest_day_always_keeps_its_label() -> None:
    """Thinned from the newest back: the day being played is never the one dropped."""
    start = datetime(2026, 8, 14, 20, 0)
    runs = [_run(100.0, start + timedelta(days=day)) for day in range(60)]

    xaxis = _score_vs_run(runs).layout.xaxis

    assert xaxis.tickvals[-1] == 60
    assert xaxis.ticktext[-1] == "Oct 12"


def test_score_vs_run_stars_each_plotted_run_that_was_a_new_pb() -> None:
    runs = _three_runs()

    figure = _score_vs_run(runs, first_run_number=5, new_pbs={runs[1]})

    stars = _trace(figure, NEW_PB_TRACE_NAME)
    assert (list(stars.x), list(stars.y)) == ([6], [120.0])
    assert stars.marker.symbol == "star"
    # A star answers for its own run even with ordinary run points hidden.
    assert stars.hovertemplate == RUN_POINT_HOVER + "<extra></extra>"
    assert stars.ids == (_trace(figure, RUN_DATA_POINT_TRACE_NAME).ids[1],)
    assert [trace.name for trace in figure.data] == [
        RUN_DATA_POINT_TRACE_NAME,
        NEW_PB_TRACE_NAME,
    ]


def test_a_star_is_gold_with_a_dark_outline_and_leaves_its_run_point_in_place() -> None:
    """One gold for both themes: the outline is what carries it on a light plot."""
    runs = _three_runs()

    figure = _score_vs_run(runs, new_pbs={runs[1]})

    stars = _trace(figure, NEW_PB_TRACE_NAME)
    assert stars.mode == "markers"
    assert stars.marker.size == NEW_PB_SIZE_DEFAULT_PX == 12
    assert stars.marker.color == "#fab005"
    assert stars.marker.line.color == "#5f3d00"
    assert stars.marker.line.width == 1
    # The run trace still holds every run, so hiding the stars from the
    # legend leaves an ordinary point where each one was.
    assert list(_trace(figure, RUN_DATA_POINT_TRACE_NAME).y) == [100.0, 120.0, 110.0]


def test_a_new_pb_the_figure_is_not_given_draws_no_star() -> None:
    """The stars are matched on the run, so one out of range adds nothing."""
    runs = _three_runs()
    out_of_range = _run(500.0, NOON - timedelta(days=30))

    figure = _score_vs_run(runs, new_pbs={out_of_range})

    assert [trace.name for trace in figure.data] == [RUN_DATA_POINT_TRACE_NAME]


def test_point_size_sizes_the_stars_of_a_run_history_figure() -> None:
    runs = _three_runs()

    figure = apply_point_appearance(_score_vs_run(runs, new_pbs={runs[1]}), "Small", "")

    assert (
        _trace(figure, NEW_PB_TRACE_NAME).marker.size == NEW_PB_SIZE_PRESET_PX["Small"]
    )


# --- Score vs Time ------------------------------------------------------------


def test_score_vs_time_plots_each_run_at_its_own_timestamp() -> None:
    """A day no longer shares one position."""
    runs = _three_runs()

    figure = _score_vs_time(runs)

    points = _trace(figure, RUN_DATA_POINT_TRACE_NAME)
    assert list(points.x) == [run.datetime_object for run in runs]
    assert figure.layout.xaxis.title.text == "Date"


def test_score_vs_time_stars_each_plotted_run_that_was_a_new_pb() -> None:
    runs = _three_runs()

    stars = _trace(_score_vs_time(runs, new_pbs={runs[1]}), NEW_PB_TRACE_NAME)

    assert (list(stars.x), list(stars.y)) == ([runs[1].datetime_object], [120.0])


@pytest.mark.parametrize("new_pb_first", [True, False], ids=["pb_first", "pb_second"])
def test_a_new_pb_is_drawn_last_among_runs_that_share_its_second_and_score(
    new_pb_first,
) -> None:
    """Two runs that ended in one second with one score sit on one point.

    plotly answers a hover there with the point drawn last, so the new PB is
    last whichever order the two are handed over in, and the hover under the
    star is the hover of the run that set the PB.
    """
    earlier = _run(90.0, NOON - timedelta(minutes=5), accuracy=0.11)
    new_pb = _run(120.0, NOON, accuracy=0.99)
    tie = _run(120.0, NOON, accuracy=0.22)
    later = _run(95.0, NOON + timedelta(minutes=5), accuracy=0.33)
    pair = [new_pb, tie] if new_pb_first else [tie, new_pb]

    figure = _score_vs_time([earlier, *pair, later], new_pbs={new_pb})

    points = _trace(figure, RUN_DATA_POINT_TRACE_NAME)
    expected = ["1", "3", "2", "4"] if new_pb_first else ["1", "2", "3", "4"]
    assert [row[1] for row in points.customdata] == expected
    assert list(points.x) == [
        earlier.datetime_object,
        NOON,
        NOON,
        later.datetime_object,
    ]
    stars = _trace(figure, NEW_PB_TRACE_NAME)
    assert (list(stars.x), list(stars.y)) == ([NOON], [120.0])


def test_runs_that_share_a_second_keep_their_order_without_a_new_pb() -> None:
    first = _run(120.0, NOON, accuracy=0.11)
    second = _run(120.0, NOON, accuracy=0.22)

    points = _trace(_score_vs_time([first, second]), RUN_DATA_POINT_TRACE_NAME)

    assert [row[1] for row in points.customdata] == ["1", "2"]


def test_a_new_pb_follows_every_run_that_ties_it_and_nothing_else_moves() -> None:
    """Five runs that ended in one second, two of them new PBs.

    The one at 100 goes after both runs that tie it. The one at 110 has no
    tie and stays where it was, as does the run below them all.
    """
    lower = _run(80.0, NOON, accuracy=0.11)
    new_pb = _run(100.0, NOON, accuracy=0.22)
    tie = _run(100.0, NOON, accuracy=0.33)
    later_tie = _run(100.0, NOON, accuracy=0.44)
    higher = _run(110.0, NOON, accuracy=0.55)
    ended_together = [lower, new_pb, tie, later_tie, higher]

    plain = _score_vs_time(ended_together)
    starred = _score_vs_time(ended_together, new_pbs={new_pb, higher})

    def ordinals(figure: go.Figure) -> list[str]:
        points = _trace(figure, RUN_DATA_POINT_TRACE_NAME)
        return [row[1] for row in points.customdata]

    assert ordinals(plain) == ["1", "2", "3", "4", "5"]
    assert ordinals(starred) == ["1", "3", "4", "2", "5"]
    # Only the order within the trace changed: the same scores at the same
    # positions, and one star for the three runs at 100.
    assert sorted(_trace(starred, RUN_DATA_POINT_TRACE_NAME).y) == sorted(
        _trace(plain, RUN_DATA_POINT_TRACE_NAME).y
    )
    assert list(_trace(starred, NEW_PB_TRACE_NAME).y) == [100.0, 110.0]
    assert ended_together == [lower, new_pb, tie, later_tie, higher]


def test_a_star_reaches_the_browser_at_its_run_points_own_time() -> None:
    """A star whose time serialized differently from its run's would sit beside it."""
    runs = _three_runs()

    figure = _score_vs_time(runs, new_pbs={runs[1]})
    points, stars = json.loads(figure.to_json())["data"]

    assert points["x"] == [
        "2026-10-10T12:00:00",
        "2026-10-10T12:05:00",
        "2026-10-11T12:00:00",
    ]
    assert stars["x"] == ["2026-10-10T12:05:00"]


# --- Score vs Sensitivity -----------------------------------------------------


def test_score_vs_sensitivity_plots_every_run_at_its_sensitivity() -> None:
    runs = [
        _run(100.0, NOON, sens=30.0),
        _run(105.0, NOON + timedelta(minutes=1), sens=30.0),
        _run(120.0, NOON + timedelta(minutes=2), sens=40.8),
    ]

    figure = _score_vs_sensitivity(runs)

    points = _trace(figure, RUN_DATA_POINT_TRACE_NAME)
    assert list(points.x) == ["30.0 cm/360", "30.0 cm/360", "40.8 cm/360"]
    assert list(points.y) == [100.0, 105.0, 120.0]
    assert figure.layout.xaxis.title.text == "Sensitivity"


# --- The ring round the latest run -------------------------------------------


def _ring(figure):
    """Return the figure's ring trace, or None when it has none."""
    return next(
        (trace for trace in figure.data if trace.name == LATEST_RUN_TRACE_NAME), None
    )


def test_each_mode_rings_the_run_it_is_told_to_at_that_runs_own_point() -> None:
    runs = [
        _run(100.0, NOON, sens=30.0),
        _run(120.0, NOON + timedelta(minutes=1), sens=40.8),
        _run(110.0, NOON + timedelta(minutes=2), sens=30.0),
    ]
    ringed = runs[1]

    by_run = generate_score_vs_run_plot(
        runs,
        5,
        SCENARIO,
        True,
        [],
        False,
        (),
        TODAY,
        ringed,
        "ringed.csv",
        run_numbers={
            run: (index, index, len(runs)) for index, run in enumerate(runs, 1)
        },
    )
    by_time = generate_score_vs_time_plot(
        runs,
        SCENARIO,
        True,
        [],
        False,
        (),
        ringed,
        "ringed.csv",
        run_numbers={
            run: (index, index, len(runs)) for index, run in enumerate(runs, 1)
        },
    )
    by_sensitivity = generate_score_vs_sensitivity_plot(
        runs,
        SCENARIO,
        True,
        [],
        False,
        ringed,
        "ringed.csv",
        run_numbers={
            run: (index, index, len(runs)) for index, run in enumerate(runs, 1)
        },
    )

    assert (list(_ring(by_run).x), list(_ring(by_run).y)) == ([6], [120.0])
    assert list(_ring(by_time).x) == [ringed.datetime_object]
    assert list(_ring(by_time).y) == [120.0]
    assert list(_ring(by_sensitivity).x) == ["40.8 cm/360"]
    assert list(_ring(by_sensitivity).y) == [120.0]
    for figure in (by_run, by_time, by_sensitivity):
        assert _ring(figure).meta == "ringed.csv"


def test_the_ring_has_no_legend_entry_and_no_hover_of_its_own() -> None:
    runs = _three_runs()

    ring = _ring(
        generate_score_vs_run_plot(
            runs,
            1,
            SCENARIO,
            True,
            [],
            False,
            (),
            TODAY,
            runs[-1],
            "newest.csv",
            run_numbers={
                run: (index, index, len(runs)) for index, run in enumerate(runs, 1)
            },
        )
    )

    assert ring.showlegend is False
    assert ring.hoverinfo == "skip"
    assert ring.mode == "markers"
    assert ring.marker.symbol == "circle-open"
    # Wider than the star, so a ringed new PB shows both.
    assert ring.marker.size == LATEST_RUN_RING_SIZE_DEFAULT_PX
    assert LATEST_RUN_RING_SIZE_DEFAULT_PX > NEW_PB_SIZE_DEFAULT_PX


def test_the_ring_is_drawn_last_so_it_sits_over_a_star() -> None:
    runs = _three_runs()

    figure = generate_score_vs_run_plot(
        runs,
        1,
        SCENARIO,
        True,
        [],
        False,
        {runs[-1]},
        TODAY,
        runs[-1],
        "newest.csv",
        run_numbers={
            run: (index, index, len(runs)) for index, run in enumerate(runs, 1)
        },
    )

    assert [trace.name for trace in figure.data] == [
        RUN_DATA_POINT_TRACE_NAME,
        NEW_PB_TRACE_NAME,
        LATEST_RUN_TRACE_NAME,
    ]


def test_a_run_that_is_not_plotted_gets_no_ring() -> None:
    """As when the range leaves the scenario's newest run out."""
    runs = _three_runs()
    outside = _run(999.0, NOON + timedelta(days=30))

    figure = generate_score_vs_run_plot(
        runs,
        1,
        SCENARIO,
        True,
        [],
        False,
        (),
        TODAY,
        outside,
        "outside.csv",
        run_numbers={
            run: (index, index, len(runs)) for index, run in enumerate(runs, 1)
        },
    )

    assert _ring(figure) is None
    assert _ring(_score_vs_run(runs)) is None
    assert _ring(_score_vs_time(runs)) is None
    assert _ring(_score_vs_sensitivity(runs)) is None


def test_two_runs_that_share_a_point_ring_the_one_named() -> None:
    """Matched on the run, as a star is: the ring takes that run's own score."""
    first = _run(100.0, NOON)
    second = _run(100.0, NOON, accuracy=0.9)

    figure = generate_score_vs_run_plot(
        [first, second],
        1,
        SCENARIO,
        True,
        [],
        False,
        (),
        TODAY,
        second,
        "second.csv",
        run_numbers={
            run: (index, index, 2) for index, run in enumerate([first, second], 1)
        },
    )

    assert list(_ring(figure).x) == [2]


@pytest.mark.parametrize(
    ("ringed", "latest", "opacity"),
    [
        ("a.csv", "a.csv", 1),
        # The card has moved to another scenario or run.
        ("a.csv", "b.csv", 0),
        # An empty run store names no run.
        ("a.csv", None, 0),
        (None, None, 0),
    ],
)
def test_the_ring_shows_only_round_the_run_reported_by_the_card(
    ringed, latest, opacity
) -> None:
    assert latest_run_ring_opacity(ringed, latest) == opacity


@pytest.mark.parametrize(
    ("color_scheme", "color"),
    [("light", "#1c7ed6"), ("dark", "#74c0fc"), ("unknown", "#1c7ed6")],
)
def test_the_ring_is_shown_in_the_schemes_blue_and_hidden_by_its_opacity(
    color_scheme, color
) -> None:
    """Never by ``visible``, which would take the ring out of the axis ranges."""
    runs = _three_runs()
    figure = generate_score_vs_run_plot(
        runs,
        1,
        SCENARIO,
        True,
        [],
        False,
        (),
        TODAY,
        runs[-1],
        "newest.csv",
        run_numbers={
            run: (index, index, len(runs)) for index, run in enumerate(runs, 1)
        },
    )

    shown = show_latest_run_ring(figure, "newest.csv", color_scheme)

    assert shown is figure
    assert (_ring(figure).opacity, _ring(figure).marker.color) == (1, color)
    assert _ring(figure).visible is None

    show_latest_run_ring(figure, "another.csv", color_scheme)

    assert _ring(figure).opacity == 0
    assert _ring(figure).visible is None


def test_showing_the_ring_leaves_a_figure_with_no_ring_as_it_is() -> None:
    figure = _score_vs_run(_three_runs())
    before = figure.to_json()

    show_latest_run_ring(figure, "newest.csv", "light")

    assert figure.to_json() == before


@pytest.mark.parametrize("point_size", ["Small", "Large"])
def test_point_size_sizes_the_ring_with_the_stars(point_size) -> None:
    runs = _three_runs()
    figure = generate_score_vs_run_plot(
        runs,
        1,
        SCENARIO,
        True,
        [],
        False,
        {runs[-1]},
        TODAY,
        runs[-1],
        "newest.csv",
        run_numbers={
            run: (index, index, len(runs)) for index, run in enumerate(runs, 1)
        },
    )

    apply_point_appearance(figure, point_size, "#ff0000")

    assert _ring(figure).marker.size == LATEST_RUN_RING_SIZE_PRESET_PX[point_size]
    assert (
        LATEST_RUN_RING_SIZE_PRESET_PX[point_size] > NEW_PB_SIZE_PRESET_PX[point_size]
    )
    # The point color is the run points' alone.
    assert _ring(figure).marker.color == "#1c7ed6"


def test_the_default_point_size_leaves_the_rings_own() -> None:
    runs = _three_runs()
    figure = generate_score_vs_run_plot(
        runs,
        1,
        SCENARIO,
        True,
        [],
        False,
        (),
        TODAY,
        runs[-1],
        "newest.csv",
        run_numbers={
            run: (index, index, len(runs)) for index, run in enumerate(runs, 1)
        },
    )

    apply_point_appearance(figure, "Default", "")

    assert _ring(figure).marker.size == LATEST_RUN_RING_SIZE_DEFAULT_PX


@EVERY_MODE
def test_linked_hover_uses_file_identity_even_when_runs_share_a_position(build):
    runs = [
        replace(_run(100.0, NOON), stats_file_name="first.csv"),
        replace(_run(100.0, NOON), stats_file_name="second.csv"),
    ]
    points = _trace(build(runs), RUN_DATA_POINT_TRACE_NAME)
    assert points.ids == ("first.csv", "second.csv")
    assert points.meta == "run-history-run"


def test_a_pb_stars_identity_and_tooltip_follow_its_run_after_time_reordering():
    first = replace(_run(90.0, NOON), stats_file_name="first.csv")
    pb = replace(_run(100.0, NOON), stats_file_name="pb.csv")
    tie = replace(_run(100.0, NOON), stats_file_name="tie.csv", accuracy=0.9)
    figure = _score_vs_time([first, pb, tie], new_pbs=[pb])
    points = _trace(figure, RUN_DATA_POINT_TRACE_NAME)
    star = _trace(figure, NEW_PB_TRACE_NAME)
    assert points.ids == ("first.csv", "tie.csv", "pb.csv")
    assert star.ids == ("pb.csv",)
    assert star.customdata == (points.customdata[-1],)
    assert star.hovertemplate == points.hovertemplate
    assert star.meta == "run-history-run"
