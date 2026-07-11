from datetime import datetime

import plotly.graph_objs as go

from source.kovaaks.data_models import Rank, RunData
from source.plot.plot_service import (
    _add_rank_overlays,
    generate_empty_plot,
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


def _drawn_ranks(rank_data: list[Rank], scores: list[float]) -> list[str]:
    """Return the rank names overlaid for ``scores``, in draw order."""
    fig = go.Figure()
    _add_rank_overlays(fig, True, rank_data, scores)
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
    assert fig.data[0].name == "Run Data Point"
    assert fig.data[1].name == "Average Score"
    assert any(shape["type"] == "line" for shape in fig.layout.shapes)


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
    assert fig.data[0].name == "Run Data Point"
    assert fig.data[1].name == "Average Score"


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
    # For ascending ladders the value-based selection matches the old
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
