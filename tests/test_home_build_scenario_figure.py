from datetime import datetime
from unittest.mock import Mock

import dash

from source.kovaaks.data_models import RunData

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402

_OLDEST = datetime(2025, 1, 1)


def _build_run(score: float, sens: float, when: datetime) -> RunData:
    return RunData(
        datetime_object=when,
        score=score,
        sens_scale="Overwatch",
        horizontal_sens=sens,
        scenario="1w4ts",
        accuracy=0.5,
    )


def test_build_scenario_figure_sensitivity_mode_builds_traces(monkeypatch):
    data = {
        "2.0 Overwatch": [
            _build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0)),
            _build_run(120.0, 2.0, datetime(2025, 1, 1, 11, 0, 0)),
        ],
        "3.0 Overwatch": [
            _build_run(90.0, 3.0, datetime(2025, 1, 2, 10, 0, 0)),
        ],
    }
    monkeypatch.setattr(home, "get_sensitivities_vs_runs_filtered", lambda *_: data)
    monkeypatch.setattr(home, "get_rank_data_from_playlist_code", lambda *_: [])

    figure, supports_overlays = home._build_scenario_figure(
        "score_vs_sensitivity", "1w4ts", 5, _OLDEST, True, None
    )

    assert supports_overlays is True
    assert len(figure.data) == 2
    assert figure.data[0].name == "Run Data Point"
    assert figure.data[1].name == "Average Score"


def test_build_scenario_figure_time_mode_builds_traces(monkeypatch):
    data = {
        datetime(2025, 1, 1).date(): [
            _build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0)),
            _build_run(110.0, 2.0, datetime(2025, 1, 1, 11, 0, 0)),
        ],
        datetime(2025, 1, 2).date(): [
            _build_run(120.0, 2.0, datetime(2025, 1, 2, 10, 0, 0)),
        ],
    }
    monkeypatch.setattr(home, "get_time_vs_runs", lambda *_: data)
    monkeypatch.setattr(home, "get_rank_data_from_playlist_code", lambda *_: [])

    figure, supports_overlays = home._build_scenario_figure(
        "score_vs_time", "1w4ts", 5, _OLDEST, False, None
    )

    assert supports_overlays is True
    assert len(figure.data) == 2
    assert figure.data[0].name == "Run Data Point"
    assert figure.data[1].name == "Average Score"


def test_build_scenario_figure_sensitivity_mode_empty_range_suppresses_overlays(
    monkeypatch,
):
    monkeypatch.setattr(home, "get_sensitivities_vs_runs_filtered", lambda *_: {})
    # The empty-range branch warns through dash_logger, which needs a live Dash
    # callback context; stub it since this test exercises the helper in isolation.
    monkeypatch.setattr(home, "dash_logger", Mock())

    figure, supports_overlays = home._build_scenario_figure(
        "score_vs_sensitivity", "1w4ts", 5, _OLDEST, True, None
    )

    assert supports_overlays is False
    assert len(figure.data) == 0
    assert home._NO_DATE_RANGE_DATA_PLOT_TITLE in figure.layout.annotations[0].text


def test_build_scenario_figure_time_mode_empty_range_suppresses_overlays(monkeypatch):
    monkeypatch.setattr(home, "get_time_vs_runs", lambda *_: {})
    # The empty-range branch warns through dash_logger, which needs a live Dash
    # callback context; stub it since this test exercises the helper in isolation.
    monkeypatch.setattr(home, "dash_logger", Mock())

    figure, supports_overlays = home._build_scenario_figure(
        "score_vs_time", "1w4ts", 5, _OLDEST, True, None
    )

    assert supports_overlays is False
    assert len(figure.data) == 0
    assert home._NO_DATE_RANGE_DATA_PLOT_TITLE in figure.layout.annotations[0].text


def test_build_scenario_figure_unsupported_mode_suppresses_overlays():
    figure, supports_overlays = home._build_scenario_figure(
        "score_vs_nonsense", "1w4ts", 5, _OLDEST, True, None
    )

    assert supports_overlays is False
    assert len(figure.data) == 0
    assert (
        home._UNSUPPORTED_GRAPH_OPTION_PLOT_TITLE in figure.layout.annotations[0].text
    )
