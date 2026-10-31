"""The parts of ``plot_service`` every chart shares.

The empty and placeholder figures, the overlay lines, and the Run Data Points
preferences. The three figures of the Run History chart are
``tests/test_plot_service_run_history.py``.
"""

import plotly.graph_objs as go
import pytest

from source.kovaaks.accuracy_target import NoFullAccuracyScore
from source.kovaaks.data_models import Rank
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
)

# A trace that is not the run points', the stars', or the ring's, standing in
# for whatever else a figure may come to hold.
OTHER_TRACE_NAME = "Another trace"

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


def test_score_overlays_label_their_lines_in_sentence_case() -> None:
    fig = add_score_threshold_overlay(add_high_score_overlay(go.Figure(), 123.0), 118.0)

    assert [annotation.text for annotation in fig.layout.annotations] == [
        "PB score (123.00)",
        "Score threshold (118.00)",
    ]


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


# --- Accuracy targets beside the rank lines ------------------------------------

# Bronze, Silver and Gold are drawn around scores of 100 to 120, and Platinum
# only with Show all ranks on.
TARGETS_LADDER = [
    Rank(name="Bronze", color="#aaaaaa", threshold=80.0),
    Rank(name="Silver", color="#bbbbbb", threshold=110.0),
    Rank(name="Gold", color="#ffcc00", threshold=140.0),
    Rank(name="Platinum", color="#cccccc", threshold=500.0),
]
RANK_LABELS = ["Bronze (80) ", "Silver (110) ", "Gold (140) "]


def _with_targets(
    accuracy_targets: float | NoFullAccuracyScore | None,
    *,
    rank_overlay: bool = True,
    rank_data: list[Rank] = TARGETS_LADDER,
    scores: tuple[float, ...] = (100.0, 120.0),
    show_all_ranks: bool = False,
) -> go.Figure:
    figure = go.Figure()
    _add_rank_overlays(
        figure,
        rank_overlay,
        rank_data,
        list(scores),
        show_all_ranks,
        accuracy_targets,
    )
    return figure


def _rank_labels(figure: go.Figure) -> list[str]:
    return [
        annotation.text
        for annotation in figure.layout.annotations
        if annotation.text.endswith(") ")
    ]


def _targets(figure: go.Figure) -> list[tuple[float, str]]:
    """Return each figure in the right margin: its line's threshold and its text."""
    return [
        (annotation.y, annotation.text)
        for annotation in figure.layout.annotations
        if annotation.xref == "paper" and annotation.xanchor == "left"
    ]


def _notes(figure: go.Figure) -> list[str]:
    return [
        annotation.text
        for annotation in figure.layout.annotations
        if annotation.yref == "paper"
    ]


def test_with_the_switch_off_the_rank_lines_are_as_they_were() -> None:
    figure = _with_targets(None)

    assert [annotation.text for annotation in figure.layout.annotations] == (
        RANK_LABELS
    )
    assert figure.layout.margin.to_plotly_json() == {}


def test_each_drawn_line_gets_its_target_beside_it_and_the_margins_stay() -> None:
    """Gold's 140 over 130 is above 100%, so Gold gets no figure.

    Platinum isn't drawn, so it gets none either, and the labels are as they
    were.
    """
    figure = _with_targets(130.0)

    assert _targets(figure) == [(80.0, "61.6%"), (110.0, "84.7%")]
    assert _rank_labels(figure) == RANK_LABELS
    assert _notes(figure) == []
    assert figure.layout.margin.to_plotly_json() == {}


def test_a_target_sits_6_px_outside_the_plot_level_with_its_line() -> None:
    """In the theme's text color: the pale rank colors can't be read on light."""
    (target, *_others) = [
        annotation
        for annotation in _with_targets(1000.0).layout.annotations
        if annotation.xanchor == "left"
    ]

    assert target.to_plotly_json() == {
        "text": "8.0%",
        "x": 1,
        "xref": "paper",
        "xanchor": "left",
        "xshift": 6,
        "y": 80.0,
        "yref": "y",
        "showarrow": False,
    }


def test_show_all_ranks_gives_every_rank_its_target() -> None:
    figure = _with_targets(1000.0, show_all_ranks=True)

    assert _targets(figure) == [
        (80.0, "8.0%"),
        (110.0, "11.0%"),
        (140.0, "14.0%"),
        (500.0, "50.0%"),
    ]


def test_the_targets_follow_the_lines_a_non_monotonic_ladder_draws() -> None:
    """Hare (54) and Penguin (58) bracket scores of 55 to 57, and nothing else."""
    figure = _with_targets(100.0, rank_data=VISCOSE_LADDER, scores=(55.0, 57.0))

    assert _targets(figure) == [(54.0, "54.0%"), (58.0, "58.0%")]


@pytest.mark.parametrize(
    ("reason", "note"),
    [
        (
            NoFullAccuracyScore.TIME_SCORED,
            "This scenario has no accuracy targets, because it's scored by "
            "completion time.",
        ),
        (
            NoFullAccuracyScore.TOO_FEW_RUNS,
            "Accuracy targets need at least 5 runs of this scenario.",
        ),
        (
            NoFullAccuracyScore.TOO_FEW_RUNS_SINCE_UPDATE,
            "Accuracy targets need at least 5 runs of this scenario since it was "
            "last updated.",
        ),
        (
            NoFullAccuracyScore.RUNS_DISAGREE,
            "This scenario has no accuracy targets, because your scores here "
            "don't follow your accuracy closely enough.",
        ),
    ],
)
def test_a_scenario_with_no_score_at_100_percent_gets_the_note_for_its_reason(
    reason, note
) -> None:
    figure = _with_targets(reason)

    assert _notes(figure) == [note]
    assert _targets(figure) == []
    assert _rank_labels(figure) == RANK_LABELS
    assert figure.layout.margin.to_plotly_json() == {"b": 112}


def test_every_drawn_rank_above_100_percent_gets_the_above_100_note() -> None:
    figure = _with_targets(50.0)

    assert _notes(figure) == [
        "Every rank on the chart has an estimated accuracy target above 100%."
    ]
    assert _targets(figure) == []
    assert figure.layout.margin.to_plotly_json() == {"b": 112}


def test_the_note_sits_under_the_axis_title_right_aligned_and_quiet() -> None:
    (note,) = _with_targets(NoFullAccuracyScore.TOO_FEW_RUNS).layout.annotations[3:]

    assert note.to_plotly_json() == {
        "text": "Accuracy targets need at least 5 runs of this scenario.",
        "x": 1,
        "xref": "paper",
        "xanchor": "right",
        "y": 0,
        "yref": "paper",
        "yanchor": "top",
        "yshift": -82,
        "showarrow": False,
        "font": {"size": 12},
        "opacity": 0.8,
    }


@pytest.mark.parametrize(
    "accuracy_targets", [1000.0, 50.0, NoFullAccuracyScore.RUNS_DISAGREE]
)
@pytest.mark.parametrize(
    ("rank_overlay", "rank_data"),
    [(False, TARGETS_LADDER), (True, [])],
    ids=["rank thresholds off", "no ladder"],
)
def test_with_no_rank_line_drawn_there_is_no_target_and_no_note(
    accuracy_targets, rank_overlay, rank_data
) -> None:
    figure = _with_targets(
        accuracy_targets, rank_overlay=rank_overlay, rank_data=rank_data
    )

    assert figure.layout.annotations == ()
    assert figure.layout.margin.to_plotly_json() == {}


def _point_figure() -> go.Figure:
    """A two-trace stand-in for a scored figure, run trace second."""
    return go.Figure(
        data=[
            go.Scatter(name=OTHER_TRACE_NAME, y=[1, 2]),
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
    # The other trace is not the run points' and stays generated.
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
                go.Scatter(name=OTHER_TRACE_NAME, y=[1, 2]),
                go.Scatter(name=RUN_DATA_POINT_TRACE_NAME, y=[1, 2]),
            ]
        )

    for point_size, star_size in (("Small", 9), ("Default", 12), ("Large", 16)):
        figure = apply_point_appearance(starred_figure(), point_size, "#1c7ed6")
        stars, other, run_trace = figure.data

        assert stars.marker.size == star_size
        # Point color is the run points' alone.
        assert stars.marker.color == "#fab005"
        assert stars.marker.symbol == "star"
        assert run_trace.marker.size == POINT_SIZE_PRESET_PX.get(point_size)
        assert run_trace.marker.color == "#1c7ed6"
        assert other.marker.size is None


def test_apply_point_appearance_tolerates_figures_without_a_run_trace() -> None:
    for figure in (
        generate_placeholder_plot(),
        generate_empty_plot("No runs to plot", "Nothing here yet."),
        go.Figure(data=[go.Scatter(name=OTHER_TRACE_NAME, y=[1, 2])]),
    ):
        before = figure.to_json()
        assert apply_point_appearance(figure, "Large", "#f03e3e").to_json() == before
