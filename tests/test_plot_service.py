from datetime import datetime

from source.kovaaks.data_models import Rank, RunData
from source.plot.plot_service import (
    generate_empty_plot,
    generate_sensitivity_plot,
    generate_time_plot,
)


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
