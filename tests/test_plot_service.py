import json
from datetime import date, datetime

import plotly.graph_objs as go

from source.kovaaks.data_models import Rank, RecordedSensitivity, RunData
from source.plot.plot_service import (
    NEW_PB_TRACE_NAME,
    POINT_SIZE_PRESET_PX,
    RUN_DATA_POINT_TRACE_NAME,
    _add_rank_overlays,
    add_high_score_overlay,
    add_score_threshold_overlay,
    apply_point_appearance,
    generate_empty_plot,
    generate_placeholder_plot,
    generate_sensitivity_plot,
    generate_time_plot,
)

# Real non-monotonic ladder from the bundled `Viscose benchmarks easier
# scenarios` playlist (scenario `1w3ts reload Larger`): Hare(54) > Ermine(50)
# breaks the assumption that thresholds ascend with rank.
VISCOSE_LADDER = [
    Rank(name="Lemming", color="#C5C3F2", threshold=36.0),
    Rank(name="Hare", color="#B2CBEA", threshold=54.0),
    Rank(name="Ermine", color="#BAF6FC", threshold=50.0),
    Rank(name="Penguin", color="#6B94DF", threshold=58.0),
    Rank(name="Fox", color="#5558AA", threshold=70.0),
    Rank(name="Mammoth", color="#6E3F98", threshold=82.0),
    Rank(name="Orca", color="#C080E4", threshold=92.0),
    Rank(name="Seal", color="#F5BDE8", threshold=102.0),
]


def _drawn_ranks(
    rank_data: list[Rank],
    scores: list[float],
    show_all_ranks: bool = False,
) -> list[str]:
    """Return the rank names overlaid for ``scores``, in draw order."""
    fig = go.Figure()
    _add_rank_overlays(fig, True, rank_data, scores, show_all_ranks)
    # add_hline annotation text is "<name> (<threshold>) "; name has no " (".
    return [ann.text.split(" (")[0] for ann in fig.layout.annotations]


def _build_run(score: float, sens: float, when: datetime) -> RunData:
    return RunData(
        datetime_object=when,
        score=score,
        sens_scale="Overwatch",
        horizontal_sens=sens,
        scenario="1w4ts",
        accuracy=0.5,
    )


def test_generate_empty_plot_has_intentional_empty_state() -> None:
    fig = generate_empty_plot("No scenario selected", "Select a scenario.")

    assert "No scenario selected" in fig.layout.annotations[0].text
    assert fig.layout.annotations[1].text == "Select a scenario."
    assert fig.layout.dragmode is False
    assert fig.layout.xaxis.visible is False
    assert fig.layout.yaxis.visible is False
    assert len(fig.data) == 0


def test_generate_placeholder_plot_is_neutral_and_transparent() -> None:
    fig = generate_placeholder_plot()

    assert not fig.layout.annotations
    assert fig.layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert fig.layout.plot_bgcolor == "rgba(0,0,0,0)"
    assert fig.layout.dragmode is False
    assert fig.layout.xaxis.visible is False
    assert fig.layout.yaxis.visible is False
    assert len(fig.data) == 0


def test_generate_sensitivity_plot_returns_empty_state_for_no_data() -> None:
    fig = generate_sensitivity_plot({}, "1w4ts", True, [])

    assert "No runs to plot" in fig.layout.annotations[0].text
    assert "No sensitivity data" in fig.layout.annotations[1].text
    assert len(fig.data) == 0


def test_generate_time_plot_returns_empty_state_for_no_data() -> None:
    fig = generate_time_plot({}, "1w4ts", True, [])

    assert "No runs to plot" in fig.layout.annotations[0].text
    assert "No score history" in fig.layout.annotations[1].text
    assert len(fig.data) == 0


def test_generate_sensitivity_plot_has_expected_traces() -> None:
    data = {
        "2.0 Overwatch": [
            _build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0)),
            _build_run(120.0, 2.0, datetime(2025, 1, 1, 11, 0, 0)),
        ],
        "3.0 Overwatch": [
            _build_run(90.0, 3.0, datetime(2025, 1, 2, 10, 0, 0)),
        ],
    }
    ranks = [
        Rank(name="Bronze", color="#aaaaaa", threshold=80),
        Rank(name="Silver", color="#bbbbbb", threshold=110),
        Rank(name="Gold", color="#ffcc00", threshold=140),
    ]

    fig = generate_sensitivity_plot(data, "1w4ts", True, ranks)

    assert len(fig.data) == 2
    assert fig.data[0].name == "Run data point"
    assert fig.data[1].name == "Average score"
    assert fig.data[1].hovertemplate.startswith("<b>Average score</b>: %{y}<br>")
    assert any(shape["type"] == "line" for shape in fig.layout.shapes)


def test_score_overlays_label_their_lines_in_sentence_case() -> None:
    fig = add_score_threshold_overlay(add_high_score_overlay(go.Figure(), 123.0), 118.0)

    assert [annotation.text for annotation in fig.layout.annotations] == [
        "PB score (123.00)",
        "Score threshold (118.00)",
    ]


def test_generate_time_plot_has_expected_traces() -> None:
    data = {
        datetime(2025, 1, 1).date(): [
            _build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0)),
            _build_run(110.0, 2.0, datetime(2025, 1, 1, 11, 0, 0)),
        ],
        datetime(2025, 1, 2).date(): [
            _build_run(120.0, 2.0, datetime(2025, 1, 2, 10, 0, 0)),
        ],
    }

    fig = generate_time_plot(data, "1w4ts", False, [])

    assert len(fig.data) == 2
    assert fig.data[0].name == "Run data point"
    assert fig.data[1].name == "Average score"


def test_time_plot_stars_each_plotted_new_pb_in_a_third_trace() -> None:
    first = _build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0))
    second = _build_run(110.0, 2.0, datetime(2025, 1, 1, 11, 0, 0))
    third = _build_run(120.0, 2.0, datetime(2025, 1, 2, 10, 0, 0))
    data = {date(2025, 1, 1): [first, second], date(2025, 1, 2): [third]}

    fig = generate_time_plot(data, "1w4ts", False, [], False, {second, third})

    # After Average score, so the stars are drawn over the other two traces.
    assert [trace.name for trace in fig.data] == [
        "Run data point",
        "Average score",
        "New PB",
    ]
    stars = fig.data[2]
    assert stars.mode == "markers"
    assert stars.hoverinfo == "skip"
    assert stars.marker.symbol == "star"
    assert stars.marker.size == 12
    assert stars.marker.color == "#fab005"
    assert stars.marker.line.color == "#5f3d00"
    assert stars.marker.line.width == 1
    assert list(zip(stars.x, stars.y, strict=True)) == [
        (date(2025, 1, 1), 110.0),
        (date(2025, 1, 2), 120.0),
    ]
    # The run trace still holds every run, so hiding the stars from the
    # legend leaves an ordinary point where each one was.
    assert list(fig.data[0].y) == [100.0, 110.0, 120.0]


def test_new_pb_stars_reach_the_browser_on_their_run_points_date_values() -> None:
    first = _build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0))
    second = _build_run(110.0, 2.0, datetime(2025, 1, 1, 11, 0, 0))
    third = _build_run(120.0, 2.0, datetime(2025, 1, 2, 10, 0, 0))
    data = {date(2025, 1, 1): [first, second], date(2025, 1, 2): [third]}

    fig = generate_time_plot(data, "1w4ts", False, [], False, {second, third})
    runs, _average, stars = json.loads(fig.to_json())["data"]

    # The two traces are built from different sources. A star whose x value
    # serialized differently from its run's would sit beside the point.
    assert runs["x"] == ["2025-01-01", "2025-01-01", "2025-01-02"]
    assert stars["x"] == ["2025-01-01", "2025-01-02"]


def test_time_plot_has_no_new_pb_trace_when_no_plotted_run_is_one() -> None:
    plotted = _build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0))
    filtered_out = _build_run(90.0, 2.0, datetime(2024, 12, 31, 10, 0, 0))
    data = {date(2025, 1, 1): [plotted]}

    for new_high_score_runs in ((), {filtered_out}):
        fig = generate_time_plot(data, "1w4ts", False, [], False, new_high_score_runs)

        assert [trace.name for trace in fig.data] == ["Run data point", "Average score"]


def test_new_pb_star_belongs_to_the_run_and_not_to_its_position() -> None:
    # The day's filter kept the later of two equal scores and dropped the
    # earlier one, which is the run that set the PB.
    new_pb = _build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0))
    kept_tie = _build_run(100.0, 2.0, datetime(2025, 1, 1, 11, 0, 0))
    data = {date(2025, 1, 1): [kept_tie]}

    fig = generate_time_plot(data, "1w4ts", False, [], False, {new_pb})

    assert [trace.name for trace in fig.data] == ["Run data point", "Average score"]


def test_time_plot_draws_a_new_pb_after_the_runs_that_share_its_point() -> None:
    # One day as ``get_time_vs_runs`` returns it: ascending by score, ties in
    # time order. Each run has its own sensitivity so the points can be told
    # apart.
    lower = _build_run(80.0, 1.0, datetime(2025, 1, 1, 9, 0, 0))
    new_pb = _build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 1, 0))
    tie = _build_run(100.0, 3.0, datetime(2025, 1, 1, 10, 5, 0))
    later_tie = _build_run(100.0, 4.0, datetime(2025, 1, 1, 10, 9, 0))
    higher = _build_run(110.0, 5.0, datetime(2025, 1, 1, 10, 30, 0))
    day_runs = [lower, new_pb, tie, later_tie, higher]
    data = {date(2025, 1, 1): day_runs}

    def sensitivities(fig: go.Figure) -> list[str]:
        return [row[2] for row in fig.data[0].customdata]

    plain = generate_time_plot(data, "1w4ts", False, [])
    starred = generate_time_plot(data, "1w4ts", False, [], False, {new_pb, higher})

    assert sensitivities(plain) == [
        "1.0 Overwatch",
        "2.0 Overwatch",
        "3.0 Overwatch",
        "4.0 Overwatch",
        "5.0 Overwatch",
    ]
    # plotly answers a hover at a shared point with the last point there, so
    # the run that set the PB has to be the last of the three at 100.
    assert sensitivities(starred) == [
        "1.0 Overwatch",
        "3.0 Overwatch",
        "4.0 Overwatch",
        "2.0 Overwatch",
        "5.0 Overwatch",
    ]
    # Only the order within the trace changed: the same scores at the same
    # positions, one star for the three runs at 100, and the same average.
    assert list(starred.data[0].y) == list(plain.data[0].y)
    assert list(starred.data[0].x) == list(plain.data[0].x)
    assert list(starred.data[2].y) == [100.0, 110.0]
    assert list(starred.data[1].y) == list(plain.data[1].y) == [98.0]
    assert day_runs == [lower, new_pb, tie, later_tie, higher]


def test_score_plots_lay_the_legend_above_the_plot() -> None:
    # Horizontal and anchored above the plot area, so the legend stops
    # reserving a right-hand column of chart width for its two entries.
    day = datetime(2025, 1, 1).date()
    runs = [_build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0))]

    for fig in (
        generate_sensitivity_plot({"2.0 Overwatch": runs}, "1w4ts", False, []),
        generate_time_plot({day: runs}, "1w4ts", False, []),
    ):
        assert fig.layout.legend.orientation == "h"
        assert fig.layout.legend.y is not None
        assert fig.layout.legend.y > 1
        assert fig.layout.legend.yanchor == "bottom"
        assert fig.layout.legend.x == 1
        assert fig.layout.legend.xanchor == "right"


def test_scatter_x_locks_sensitivity_vs_time_asymmetry() -> None:
    # The sensitivity scatter's per-point x is derived from the run
    # ("<horizontal_sens> <sens_scale>"), not the grouping dict key -- so a key
    # that differs from that string still yields the run-derived x value.
    sens_data = {
        "group-key-not-the-scatter-x": [
            _build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0)),
        ],
    }
    sens_fig = generate_sensitivity_plot(sens_data, "1w4ts", False, [])
    assert tuple(sens_fig.data[0].x) == ("2.0 Overwatch",)

    # The time scatter's per-point x is the grouping dict key (the date) itself.
    day = datetime(2025, 1, 1).date()
    time_data = {day: [_build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0))]}
    time_fig = generate_time_plot(time_data, "1w4ts", False, [])
    assert tuple(time_fig.data[0].x) == (day,)


def test_time_plot_point_hover_names_each_runs_own_sensitivity() -> None:
    # One day holds runs at two sensitivities, which its Date x value can't
    # tell apart, so each point carries its own run's sensitivity.
    time_data = {
        datetime(2025, 1, 1).date(): [
            _build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0)),
            _build_run(110.0, 3.0, datetime(2025, 1, 1, 11, 0, 0)),
        ],
        datetime(2025, 1, 2).date(): [
            _build_run(120.0, 2.5, datetime(2025, 1, 2, 10, 0, 0)),
        ],
    }
    time_fig = generate_time_plot(time_data, "1w4ts", False, [])
    points = time_fig.data[0]

    assert [
        (score, row[2]) for score, row in zip(points.y, points.customdata, strict=True)
    ] == [
        (100.0, "2.0 Overwatch"),
        (110.0, "3.0 Overwatch"),
        (120.0, "2.5 Overwatch"),
    ]
    sensitivity_line = "<b>Sensitivity</b>: %{customdata[2]}"
    hover = points.hovertemplate
    assert (
        hover.index("<b>Date</b>")
        < hover.index(sensitivity_line)
        < hover.index("<b>Accuracy</b>")
    )

    # Score vs Sensitivity already names the sensitivity as its x value.
    sens_data = {
        "2.0 Overwatch": [_build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0))],
    }
    sens_fig = generate_sensitivity_plot(sens_data, "1w4ts", False, [])
    assert sens_fig.data[0].hovertemplate.count("<b>Sensitivity</b>") == 1

    # A day's average can span sensitivities, and the line has no customdata.
    for fig in (time_fig, sens_fig):
        assert "customdata" not in fig.data[1].hovertemplate


def test_a_converted_runs_point_hover_names_the_setting_it_was_recorded_at() -> None:
    when = datetime(2025, 1, 1, 10, 0, 0)
    converted = RunData(
        datetime_object=when,
        score=100.0,
        sens_scale="cm/360",
        horizontal_sens=51.1,
        scenario="1w4ts",
        accuracy=0.5,
        # A parsed DPI is a float, and the hover must still read 1600.
        recorded_sensitivity=RecordedSensitivity(
            value=0.16,
            scale="Valorant",
            dpi=1600.0,
        ),
    )
    native = RunData(
        datetime_object=when,
        score=110.0,
        sens_scale="cm/360",
        horizontal_sens=40.8,
        scenario="1w4ts",
        accuracy=0.5,
    )
    sens_fig = generate_sensitivity_plot(
        {"51.1 cm/360": [converted], "40.8 cm/360": [native]}, "1w4ts", False, []
    )
    time_fig = generate_time_plot(
        {when.date(): [converted, native]}, "1w4ts", False, []
    )

    for fig in (sens_fig, time_fig):
        points = fig.data[0]
        assert [(row[2], row[3]) for row in points.customdata] == [
            ("51.1 cm/360", " (0.16 Valorant at 1600 DPI)"),
            # Nothing where the suffix would go.
            ("40.8 cm/360", ""),
        ]
        assert (
            "<b>Sensitivity</b>: %{customdata[2]}%{customdata[3]}<br>"
            in points.hovertemplate
        )

    # The points' sensitivity line stands in for the x line; it doesn't repeat it.
    assert sens_fig.data[0].hovertemplate.count("<b>Sensitivity</b>") == 1

    # An average can span recorded settings, so its hover is exactly what it was.
    assert sens_fig.data[1].hovertemplate == (
        "<b>Average score</b>: %{y}<br><b>Sensitivity</b>: %{x}<extra></extra>"
    )
    assert time_fig.data[1].hovertemplate == (
        "<b>Average score</b>: %{y}<br><b>Date</b>: %{x}<extra></extra>"
    )


def test_rank_overlays_omitted_when_switch_off() -> None:
    fig = go.Figure()
    _add_rank_overlays(fig, False, VISCOSE_LADDER, [55.0, 57.0])
    assert fig.layout.annotations == ()


def test_rank_overlays_non_monotonic_band_picks_nearest_context_each_side() -> None:
    # Scores land in the inverted band ~[55, 57]: no rank threshold is in range,
    # so the overlay draws the nearest context on each side -- Hare(54) below and
    # Penguin(58) above. The old index-walk silently omitted Hare here.
    assert _drawn_ranks(VISCOSE_LADDER, [55.0, 57.0]) == ["Hare", "Penguin"]


def test_rank_overlays_non_monotonic_wide_range_draws_in_range_plus_context() -> None:
    # Scores [40, 60]: in-range thresholds are Ermine(50), Hare(54), Penguin(58);
    # context is Lemming(36) below and Fox(70) above. Drawn in ladder order.
    assert _drawn_ranks(VISCOSE_LADDER, [40.0, 60.0]) == [
        "Lemming",
        "Hare",
        "Ermine",
        "Penguin",
        "Fox",
    ]


def test_rank_overlays_monotonic_equivalence() -> None:
    # For strictly ascending ladders the value-based selection matches the old
    # index-bracketing exactly: one context rank below, in-range ranks, one
    # context rank above.
    ladder = [
        Rank(name="Bronze", color="#aaaaaa", threshold=80.0),
        Rank(name="Silver", color="#bbbbbb", threshold=110.0),
        Rank(name="Gold", color="#ffcc00", threshold=140.0),
    ]
    assert _drawn_ranks(ladder, [100.0, 120.0]) == ["Bronze", "Silver", "Gold"]
    # Range strictly between two thresholds: only the bracketing context ranks.
    assert _drawn_ranks(ladder, [111.0, 139.0]) == ["Silver", "Gold"]


def test_rank_overlays_show_all_ranks_draws_the_whole_ladder() -> None:
    # Scores land in the inverted band ~[55, 57], where the bracketing selection
    # draws only Hare(54) and Penguin(58). Opting in draws every rank, in ladder
    # order, including thresholds far outside the plotted range.
    assert _drawn_ranks(VISCOSE_LADDER, [55.0, 57.0], show_all_ranks=True) == [
        rank.name for rank in VISCOSE_LADDER
    ]


def test_rank_overlays_show_all_ranks_stays_subordinate_to_the_switch() -> None:
    fig = go.Figure()
    _add_rank_overlays(fig, False, VISCOSE_LADDER, [55.0, 57.0], True)
    assert fig.layout.annotations == ()


def test_rank_overlays_include_boundary_ties() -> None:
    # Equal thresholds exist upstream; all ranks tied at a context boundary are
    # drawn (here two ranks tied at 50, the nearest threshold below the range).
    ladder = [
        Rank(name="A", color="#111111", threshold=30.0),
        Rank(name="B", color="#222222", threshold=50.0),
        Rank(name="C", color="#333333", threshold=50.0),
        Rank(name="D", color="#444444", threshold=90.0),
    ]
    assert _drawn_ranks(ladder, [70.0, 80.0]) == ["B", "C", "D"]


def test_rank_overlays_include_thresholds_at_the_plotted_range_edges() -> None:
    # Thresholds equal to the lowest and highest plotted score are in range, not
    # context. Context selection is strict, so an exclusive range check would
    # drop B and C from the overlay entirely.
    ladder = [
        Rank(name="A", color="#111111", threshold=30.0),
        Rank(name="B", color="#222222", threshold=70.0),
        Rank(name="C", color="#333333", threshold=80.0),
        Rank(name="D", color="#444444", threshold=90.0),
    ]
    assert _drawn_ranks(ladder, [70.0, 80.0]) == ["A", "B", "C", "D"]


def _point_figure() -> go.Figure:
    """A two-trace stand-in for a scored figure, run trace second."""
    return go.Figure(
        data=[
            go.Scatter(name="Average score", y=[1, 2]),
            go.Scatter(name=RUN_DATA_POINT_TRACE_NAME, y=[1, 2]),
        ]
    )


def test_apply_point_appearance_leaves_the_figure_alone_for_the_defaults() -> None:
    figure = _point_figure()
    before = figure.to_json()

    assert apply_point_appearance(figure, "Default", "").to_json() == before


def test_apply_point_appearance_sets_only_the_run_trace_marker() -> None:
    figure = apply_point_appearance(_point_figure(), "Small", "#1c7ed6")

    run_trace = figure.data[1]
    assert run_trace.marker.size == POINT_SIZE_PRESET_PX["Small"]
    assert run_trace.marker.color == "#1c7ed6"
    # The average line is a different trace and stays generated.
    assert figure.data[0].marker.size is None
    assert figure.data[0].marker.color is None


def test_apply_point_appearance_matches_by_name_not_by_index() -> None:
    # The run trace is index 0 in the shipped figures, but a figure that ever
    # reorders its traces must still style the run points and only those.
    figure = apply_point_appearance(_point_figure(), "Large", None)

    assert figure.data[1].marker.size == POINT_SIZE_PRESET_PX["Large"]
    assert figure.data[0].marker.size is None


def test_apply_point_appearance_ignores_values_it_does_not_recognize() -> None:
    figure = apply_point_appearance(_point_figure(), "Enormous", "not-a-color")
    assert figure.data[1].marker.size is None
    assert figure.data[1].marker.color is None

    # A cleared dmc input sends "", never None -- both mean Default.
    figure = apply_point_appearance(_point_figure(), None, "")
    assert figure.data[1].marker.color is None

    # One unusable half never blocks the other.
    figure = apply_point_appearance(_point_figure(), "Small", "#12345")
    assert figure.data[1].marker.size == POINT_SIZE_PRESET_PX["Small"]
    assert figure.data[1].marker.color is None


def test_apply_point_appearance_sizes_the_new_pb_trace_by_name() -> None:
    def starred_figure() -> go.Figure:
        # Stars first, so a selection by index would size the wrong trace.
        return go.Figure(
            data=[
                go.Scatter(
                    name=NEW_PB_TRACE_NAME,
                    y=[2],
                    marker={"symbol": "star", "size": 12, "color": "#fab005"},
                ),
                go.Scatter(name="Average score", y=[1, 2]),
                go.Scatter(name=RUN_DATA_POINT_TRACE_NAME, y=[1, 2]),
            ]
        )

    for point_size, star_size in (("Small", 9), ("Default", 12), ("Large", 16)):
        figure = apply_point_appearance(starred_figure(), point_size, "#1c7ed6")
        stars, average, run_trace = figure.data

        assert stars.marker.size == star_size
        # Point color is the run points' alone.
        assert stars.marker.color == "#fab005"
        assert stars.marker.symbol == "star"
        assert run_trace.marker.size == POINT_SIZE_PRESET_PX.get(point_size)
        assert run_trace.marker.color == "#1c7ed6"
        assert average.marker.size is None


def test_apply_point_appearance_tolerates_figures_without_a_run_trace() -> None:
    for figure in (
        generate_placeholder_plot(),
        generate_empty_plot("No runs to plot", "Nothing here yet."),
        go.Figure(data=[go.Scatter(name="Average score", y=[1, 2])]),
    ):
        before = figure.to_json()
        assert apply_point_appearance(figure, "Large", "#f03e3e").to_json() == before
