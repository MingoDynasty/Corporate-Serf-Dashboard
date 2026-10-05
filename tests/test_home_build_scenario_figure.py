from datetime import date, datetime
from unittest.mock import Mock

import dash
import pytest
from sortedcontainers import SortedList

from source.kovaaks import data_service
from source.kovaaks.data_models import Rank, RunData

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


@pytest.fixture
def load_runs(monkeypatch):
    """Load runs through the real CSV loader, so the page's own queries filter them."""
    monkeypatch.setattr(data_service, "kovaaks_database", {})
    monkeypatch.setattr(
        data_service,
        "run_database",
        SortedList(key=lambda run: run.datetime_object),
    )

    def load(*runs: RunData) -> None:
        pending = iter(runs)
        monkeypatch.setattr(
            data_service, "extract_data_from_file", lambda _file: next(pending)
        )
        for index in range(len(runs)):
            assert data_service.load_csv_file_into_database(f"run-{index}.csv")

    return load


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

    figure, supports_overlays = home._build_scenario_figure(
        "score_vs_sensitivity", "1w4ts", 5, _OLDEST, True, False, None
    )

    assert supports_overlays is True
    assert len(figure.data) == 2
    assert figure.data[0].name == "Run data point"
    assert figure.data[1].name == "Average score"


def test_build_scenario_figure_fetches_and_applies_playlist_ranks(monkeypatch):
    data = {
        "2.0 Overwatch": [
            _build_run(90.0, 2.0, datetime(2025, 1, 1, 10, 0, 0)),
            _build_run(120.0, 2.0, datetime(2025, 1, 1, 11, 0, 0)),
        ],
    }
    ranks = [
        Rank(name="Bronze", color="#aaaaaa", threshold=80),
        Rank(name="Silver", color="#bbbbbb", threshold=110),
        Rank(name="Gold", color="#ffcc00", threshold=150),
    ]
    monkeypatch.setattr(home, "get_sensitivities_vs_runs_filtered", lambda *_: data)
    rank_fetch = Mock(return_value=ranks)
    monkeypatch.setattr(home, "get_rank_data_from_playlist_code", rank_fetch)

    figure, supports_overlays = home._build_scenario_figure(
        "score_vs_sensitivity", "1w4ts", 5, _OLDEST, True, False, "playlist-code"
    )

    assert supports_overlays is True
    rank_fetch.assert_called_once_with("playlist-code", "1w4ts")
    # The fetched ranks reach the plot builder as rank-overlay lines.
    assert any(shape["type"] == "line" for shape in figure.layout.shapes)


def test_build_scenario_figure_threads_show_all_ranks_to_the_plot(monkeypatch):
    data = {
        "2.0 Overwatch": [
            _build_run(90.0, 2.0, datetime(2025, 1, 1, 10, 0, 0)),
            _build_run(120.0, 2.0, datetime(2025, 1, 1, 11, 0, 0)),
        ],
    }
    # Silver(110) lands inside the plotted range; Bronze(80) and Gold(150) are
    # the nearest context below/above; Platinum(500) is only drawn when the
    # toggle is on.
    ranks = [
        Rank(name="Bronze", color="#aaaaaa", threshold=80),
        Rank(name="Silver", color="#bbbbbb", threshold=110),
        Rank(name="Gold", color="#ffcc00", threshold=150),
        Rank(name="Platinum", color="#cccccc", threshold=500),
    ]
    monkeypatch.setattr(home, "get_sensitivities_vs_runs_filtered", lambda *_: data)
    monkeypatch.setattr(home, "get_rank_data_from_playlist_code", lambda *_: ranks)

    def drawn_ranks(show_all_ranks: bool) -> list[str]:
        figure, _ = home._build_scenario_figure(
            "score_vs_sensitivity",
            "1w4ts",
            5,
            _OLDEST,
            True,
            show_all_ranks,
            "playlist-code",
        )
        return [
            annotation.text.split(" (")[0] for annotation in figure.layout.annotations
        ]

    assert drawn_ranks(False) == ["Bronze", "Silver", "Gold"]
    assert drawn_ranks(True) == ["Bronze", "Silver", "Gold", "Platinum"]


def _time_figure(top_n_scores: int = 5):
    figure, supports_overlays = home._build_scenario_figure(
        "score_vs_time", "1w4ts", top_n_scores, _OLDEST, False, False, None
    )
    assert supports_overlays is True
    return figure


def _points(trace) -> list[tuple]:
    return list(zip(trace.x, trace.y, strict=True))


def _run_sensitivities(figure) -> list[str]:
    return [row[2] for row in figure.data[0].customdata]


def test_build_scenario_figure_time_mode_stars_the_plotted_new_pbs(load_runs):
    load_runs(
        _build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0)),
        _build_run(110.0, 2.0, datetime(2025, 1, 1, 11, 0, 0)),
        _build_run(105.0, 2.0, datetime(2025, 1, 2, 9, 0, 0)),
        _build_run(120.0, 2.0, datetime(2025, 1, 2, 10, 0, 0)),
    )

    figure = _time_figure()

    assert [trace.name for trace in figure.data] == [
        "Run data point",
        "Average score",
        "New PB",
    ]
    assert len(figure.data[0].x) == 4
    # Not the scenario's first run, and not 105, which only beat its own day.
    assert _points(figure.data[2]) == [
        (date(2025, 1, 1), 110.0),
        (date(2025, 1, 2), 120.0),
    ]


def test_time_mode_judges_against_runs_older_than_the_oldest_date(load_runs):
    load_runs(
        _build_run(150.0, 2.0, datetime(2024, 12, 31, 10, 0, 0)),
        _build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0)),
        _build_run(120.0, 2.0, datetime(2025, 1, 1, 11, 0, 0)),
        _build_run(160.0, 2.0, datetime(2025, 1, 2, 10, 0, 0)),
    )

    figure = _time_figure()

    # The 2024 run is not drawn, and 120 still never beat it.
    assert sorted(figure.data[0].y) == [100.0, 120.0, 160.0]
    assert _points(figure.data[2]) == [(date(2025, 1, 2), 160.0)]


def test_time_mode_gives_no_star_to_a_new_pb_the_top_n_filter_dropped(load_runs):
    load_runs(
        _build_run(50.0, 2.0, datetime(2025, 1, 1, 10, 0, 0)),
        _build_run(60.0, 2.0, datetime(2025, 1, 2, 10, 0, 0)),
        _build_run(70.0, 2.0, datetime(2025, 1, 2, 11, 0, 0)),
        _build_run(80.0, 2.0, datetime(2025, 1, 2, 12, 0, 0)),
    )

    figure = _time_figure(top_n_scores=2)

    assert sorted(figure.data[0].y) == [50.0, 70.0, 80.0]
    assert _points(figure.data[2]) == [
        (date(2025, 1, 2), 70.0),
        (date(2025, 1, 2), 80.0),
    ]


def test_time_mode_gives_a_kept_tie_no_star_when_its_new_pb_was_dropped(load_runs):
    load_runs(
        _build_run(50.0, 1.0, datetime(2025, 1, 1, 10, 0, 0)),
        _build_run(60.0, 2.0, datetime(2025, 1, 2, 10, 0, 0)),
        _build_run(60.0, 3.0, datetime(2025, 1, 2, 11, 0, 0)),
    )

    figure = _time_figure(top_n_scores=1)

    # The day keeps the later of its two 60s, which only tied the new PB. It
    # sits where the new PB would have, and it never beat anything.
    assert _run_sensitivities(figure) == ["1.0 Overwatch", "3.0 Overwatch"]
    assert [trace.name for trace in figure.data] == ["Run data point", "Average score"]


def test_time_mode_orders_a_new_pb_after_the_plotted_tie_at_its_point(load_runs):
    load_runs(
        _build_run(50.0, 1.0, datetime(2025, 1, 1, 10, 0, 0)),
        _build_run(60.0, 2.0, datetime(2025, 1, 2, 10, 0, 0)),
        _build_run(60.0, 3.0, datetime(2025, 1, 2, 11, 0, 0)),
        _build_run(55.0, 4.0, datetime(2025, 1, 2, 12, 0, 0)),
    )

    figure = _time_figure()

    # One star for the pair, and the run that set the PB is the last point
    # at it, which is the one a hover there names.
    assert _points(figure.data[2]) == [(date(2025, 1, 2), 60.0)]
    assert _run_sensitivities(figure) == [
        "1.0 Overwatch",
        "4.0 Overwatch",
        "3.0 Overwatch",
        "2.0 Overwatch",
    ]
    assert list(figure.data[0].y) == [50.0, 55.0, 60.0, 60.0]
    assert _points(figure.data[1]) == [
        (date(2025, 1, 1), 50.0),
        (date(2025, 1, 2), (55.0 + 60.0 + 60.0) / 3),
    ]


def test_time_mode_has_two_traces_when_no_plotted_run_is_a_new_pb(load_runs):
    load_runs(
        _build_run(120.0, 2.0, datetime(2025, 1, 1, 10, 0, 0)),
        _build_run(110.0, 2.0, datetime(2025, 1, 1, 11, 0, 0)),
        _build_run(120.0, 2.0, datetime(2025, 1, 2, 10, 0, 0)),
    )

    figure = _time_figure()

    assert [trace.name for trace in figure.data] == ["Run data point", "Average score"]


def test_sensitivity_mode_never_stars_a_new_pb(load_runs):
    load_runs(
        _build_run(100.0, 2.0, datetime(2025, 1, 1, 10, 0, 0)),
        _build_run(110.0, 2.0, datetime(2025, 1, 1, 11, 0, 0)),
        _build_run(120.0, 3.0, datetime(2025, 1, 2, 10, 0, 0)),
    )

    figure, _ = home._build_scenario_figure(
        "score_vs_sensitivity", "1w4ts", 5, _OLDEST, False, False, None
    )

    assert [trace.name for trace in figure.data] == ["Run data point", "Average score"]


def test_build_scenario_figure_sensitivity_mode_empty_range_suppresses_overlays(
    monkeypatch,
):
    monkeypatch.setattr(home, "get_sensitivities_vs_runs_filtered", lambda *_: {})

    figure, supports_overlays = home._build_scenario_figure(
        "score_vs_sensitivity", "1w4ts", 5, _OLDEST, True, False, None
    )

    # The on-canvas empty state is the whole notice: the helper returns no
    # notification channel at all, so there is nothing to suppress.
    assert supports_overlays is False
    assert len(figure.data) == 0
    assert home._NO_DATE_RANGE_DATA_PLOT_TITLE in figure.layout.annotations[0].text
    assert figure.layout.annotations[1].text == (
        "Choose an older date or play more runs."
    )


def test_build_scenario_figure_time_mode_empty_range_suppresses_overlays(monkeypatch):
    monkeypatch.setattr(home, "get_time_vs_runs", lambda *_: {})

    figure, supports_overlays = home._build_scenario_figure(
        "score_vs_time", "1w4ts", 5, _OLDEST, True, False, None
    )

    # Same as the sensitivity-mode case above: the second empty-range call
    # site draws the empty state and says nothing else.
    assert supports_overlays is False
    assert len(figure.data) == 0
    assert home._NO_DATE_RANGE_DATA_PLOT_TITLE in figure.layout.annotations[0].text


def test_build_scenario_figure_unsupported_mode_suppresses_overlays():
    figure, supports_overlays = home._build_scenario_figure(
        "score_vs_nonsense", "1w4ts", 5, _OLDEST, True, False, None
    )

    assert supports_overlays is False
    assert len(figure.data) == 0
    assert (
        home._UNSUPPORTED_GRAPH_OPTION_PLOT_TITLE in figure.layout.annotations[0].text
    )
