from datetime import datetime

from source.kovaaks.data_models import Rank, RunData
from source.plot.plot_service import (
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
