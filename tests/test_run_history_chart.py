"""What the Run History chart plots: every run in the range its mode counts.

Each test loads runs through the real CSV loader and asks
``build_run_history_figure`` for one mode's figure, so the range, the order
the runs were played in, and which of them were new PBs are all read from the
store the app keeps.
"""

import logging
from datetime import date, datetime, timedelta

import pytest
from sortedcontainers import SortedList

from source.components import run_history_chart
from source.components.run_history_chart import (
    SCORE_VS_RUN,
    SCORE_VS_SENSITIVITY,
    SCORE_VS_TIME,
    build_run_history_figure,
    first_moment_of_day_range,
)
from source.kovaaks import data_service
from source.kovaaks.data_models import Rank, RunData
from source.plot.plot_service import (
    LATEST_RUN_TRACE_NAME,
    NEW_PB_TRACE_NAME,
    RUN_DATA_POINT_TRACE_NAME,
)

SCENARIO = "1w4ts"
TODAY = date(2026, 10, 12)
MIDNIGHT_TODAY = datetime(2026, 10, 12)
DAY_MODES = pytest.mark.parametrize("mode", [SCORE_VS_TIME, SCORE_VS_SENSITIVITY])


def _run(
    score: float,
    when: datetime,
    *,
    sens: float = 40.0,
    seconds: float | None = None,
    file_name: str | None = None,
) -> RunData:
    """Build a run that ended at ``when``. ``seconds`` gives it a usable start."""
    return RunData(
        datetime_object=when,
        score=score,
        sens_scale="cm/360",
        horizontal_sens=sens,
        scenario=SCENARIO,
        accuracy=0.5,
        stats_file_name=file_name,
        run_start=None if seconds is None else when - timedelta(seconds=seconds),
        run_length=None if seconds is None else timedelta(seconds=seconds),
    )


@pytest.fixture
def load_runs(monkeypatch):
    """Load runs through the real CSV loader, so every store has its real shape."""
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


def _figure(
    mode: str,
    *,
    run_range: str | None = "100",
    day_range: str | None = "90",
    playlist: str | None = None,
    today: date = TODAY,
):
    return build_run_history_figure(
        mode, SCENARIO, run_range, day_range, True, False, playlist, today
    )


def _points(figure):
    (trace,) = [
        trace for trace in figure.data if trace.name == RUN_DATA_POINT_TRACE_NAME
    ]
    return trace


def _stars(figure) -> list[float]:
    """Return the scores starred, or none when the figure has no New PB trace."""
    return [
        score
        for trace in figure.data
        if trace.name == NEW_PB_TRACE_NAME
        for score in trace.y
    ]


def _daily_runs(count: int) -> list[RunData]:
    """Build ``count`` runs, one a day, the newest today, scored 1 to ``count``."""
    return [
        _run(float(index + 1), MIDNIGHT_TODAY - timedelta(days=count - 1 - index))
        for index in range(count)
    ]


# --- Score vs Run: a range in runs ---------------------------------------------


@pytest.mark.parametrize(
    ("run_range", "plotted", "first_run_number"),
    [("50", 50, 71), ("100", 100, 21), ("200", 120, 1), ("all", 120, 1)],
)
def test_score_vs_run_plots_the_last_runs_of_its_range(
    load_runs, run_range, plotted, first_run_number
) -> None:
    """Every run in the range is a point, numbered by its place in the history."""
    load_runs(*_daily_runs(120))

    figure, supports_overlays = _figure(SCORE_VS_RUN, run_range=run_range)

    points = _points(figure)
    assert supports_overlays is True
    assert len(points.y) == plotted
    assert list(points.x) == list(range(first_run_number, 121))
    # The newest runs are the ones kept, oldest of them first.
    assert list(points.y) == [float(score) for score in range(121 - plotted, 121)]


@pytest.mark.parametrize("stored", [None, "", "25", "last-week"])
def test_a_run_range_the_select_does_not_offer_reads_as_the_default(
    load_runs, stored
) -> None:
    """The browser remembers the value, so one from another list can come back."""
    load_runs(*_daily_runs(120))

    figure, _supports_overlays = _figure(SCORE_VS_RUN, run_range=stored)

    assert len(_points(figure).y) == 100


def test_score_vs_run_ignores_the_range_in_days(load_runs) -> None:
    """Each mode reads the one select it shows."""
    load_runs(*_daily_runs(120))

    figure, _supports_overlays = _figure(SCORE_VS_RUN, run_range="all", day_range="7")

    assert len(_points(figure).y) == 120


def test_score_vs_run_is_never_empty_for_a_scenario_with_runs(load_runs) -> None:
    """A range in runs always holds the newest run, however old it is."""
    load_runs(_run(100.0, datetime(2019, 1, 1, 12)))

    figure, supports_overlays = _figure(SCORE_VS_RUN, run_range="50", day_range="7")

    assert supports_overlays is True
    assert list(_points(figure).y) == [100.0]


# --- Score vs Time and Score vs Sensitivity: a range in days -------------------


def test_a_range_of_days_counts_today() -> None:
    """On October 11 the last 7 days are October 5 to 11."""
    assert first_moment_of_day_range(7, date(2026, 10, 11)) == datetime(2026, 10, 5)
    assert first_moment_of_day_range(1, date(2026, 10, 11)) == datetime(2026, 10, 11)


@DAY_MODES
@pytest.mark.parametrize(
    ("day_range", "first_day"),
    [
        ("7", date(2026, 10, 6)),
        ("14", date(2026, 9, 29)),
        ("30", date(2026, 9, 13)),
        ("90", date(2026, 7, 15)),
        # The last 12 months are 365 days, counted the same way.
        ("365", date(2025, 10, 13)),
    ],
)
def test_a_range_of_days_starts_at_its_first_days_midnight(
    load_runs, mode, day_range, first_day
) -> None:
    """A run leaves the chart at midnight, never in the middle of a day."""
    first_moment = datetime.combine(first_day, datetime.min.time())
    just_inside = _run(101.0, first_moment)
    just_outside = _run(102.0, first_moment - timedelta(seconds=1))
    today = _run(103.0, MIDNIGHT_TODAY + timedelta(hours=20))
    load_runs(just_outside, just_inside, today)

    figure, supports_overlays = _figure(mode, day_range=day_range)

    assert supports_overlays is True
    assert sorted(_points(figure).y) == [101.0, 103.0]


@DAY_MODES
def test_all_time_plots_every_run(load_runs, mode) -> None:
    load_runs(*_daily_runs(120), _run(999.0, datetime(2019, 1, 1, 12)))

    figure, _supports_overlays = _figure(mode, day_range="all")

    assert len(_points(figure).y) == 121


@DAY_MODES
def test_a_day_range_the_select_does_not_offer_reads_as_the_default(
    load_runs, mode
) -> None:
    load_runs(*_daily_runs(120))

    figure, _supports_overlays = _figure(mode, day_range="45")

    assert len(_points(figure).y) == 90


@DAY_MODES
def test_the_day_modes_ignore_the_range_in_runs(load_runs, mode) -> None:
    load_runs(*_daily_runs(120))

    figure, _supports_overlays = _figure(mode, run_range="50", day_range="all")

    assert len(_points(figure).y) == 120


@DAY_MODES
def test_a_range_with_no_runs_in_it_says_so(load_runs, mode) -> None:
    load_runs(_run(100.0, MIDNIGHT_TODAY - timedelta(days=30)))

    figure, supports_overlays = _figure(mode, day_range="7")

    assert supports_overlays is False
    assert len(figure.data) == 0
    title, message = figure.layout.annotations
    assert title.text == "<b>No runs in this range</b>"
    assert message.text == "Choose a longer range or play more runs."


def test_score_vs_time_plots_runs_in_the_order_they_were_played(load_runs) -> None:
    runs = _daily_runs(5)
    load_runs(runs[3], runs[0], runs[4], runs[1], runs[2])

    figure, _supports_overlays = _figure(SCORE_VS_TIME)

    assert list(_points(figure).x) == [run.datetime_object for run in runs]


def test_score_vs_sensitivity_lists_the_sensitivities_lowest_first(load_runs) -> None:
    """Whatever order the runs were played in, the axis reads in order."""
    noon = MIDNIGHT_TODAY + timedelta(hours=12)
    load_runs(
        _run(100.0, noon, sens=40.0),
        _run(101.0, noon + timedelta(minutes=1), sens=30.5),
        _run(102.0, noon + timedelta(minutes=2), sens=100.0),
        _run(103.0, noon + timedelta(minutes=3), sens=30.5),
    )

    figure, _supports_overlays = _figure(SCORE_VS_SENSITIVITY)

    assert list(dict.fromkeys(_points(figure).x)) == [
        "30.5 cm/360",
        "40.0 cm/360",
        "100.0 cm/360",
    ]
    assert len(_points(figure).y) == 4


# --- New PB stars ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("mode", "ranges"),
    [
        (SCORE_VS_RUN, {"run_range": "50"}),
        (SCORE_VS_TIME, {"day_range": "7"}),
    ],
    ids=["score_vs_run", "score_vs_time"],
)
def test_stars_are_judged_over_the_whole_history_before_the_range_is_applied(
    load_runs, mode, ranges
) -> None:
    """A new PB the range leaves out is not drawn, and it still counts.

    Run 60 of 110 scores 500 and is outside both ranges. Inside them only the
    run that beats 500 is a new PB. Judged within the range alone, the first
    run in it and every run that rose above it would be starred too.
    """
    runs = _daily_runs(110)
    runs[59] = _run(500.0, runs[59].datetime_object)
    runs[108] = _run(600.0, runs[108].datetime_object)
    load_runs(*runs)

    figure, _supports_overlays = _figure(mode, **ranges)

    assert 500.0 not in _points(figure).y
    assert _stars(figure) == [600.0]


def test_score_vs_sensitivity_has_no_stars(load_runs) -> None:
    load_runs(*_daily_runs(10))

    figure, _supports_overlays = _figure(SCORE_VS_SENSITIVITY)

    assert _stars(figure) == []
    assert [trace.name for trace in figure.data] == [
        RUN_DATA_POINT_TRACE_NAME,
        LATEST_RUN_TRACE_NAME,
    ]


def test_a_chart_with_no_new_pb_in_range_has_no_star_trace(load_runs) -> None:
    runs = _daily_runs(60)
    runs[0] = _run(999.0, runs[0].datetime_object)
    load_runs(*runs)

    figure, _supports_overlays = _figure(SCORE_VS_RUN, run_range="50")

    assert [trace.name for trace in figure.data] == [
        RUN_DATA_POINT_TRACE_NAME,
        LATEST_RUN_TRACE_NAME,
    ]


@pytest.mark.parametrize("stored_first", ["began_first", "began_second"])
def test_two_runs_that_ended_in_one_second_are_starred_in_the_order_played(
    load_runs, stored_first
) -> None:
    """The chart orders such a pair as the sessions do, and judges them so too.

    Both beat the PB before them, the one that began first with the lower
    score. In play order each is a new PB. The store keeps a pair in the
    order it was loaded, so judged in that order with the higher score
    first, the lower one would lose its star, and the two would be plotted
    the other way round.
    """
    ended = MIDNIGHT_TODAY + timedelta(hours=12)
    baseline = _run(50.0, ended - timedelta(hours=1), seconds=60)
    began_first = _run(100.0, ended, seconds=90)
    began_second = _run(120.0, ended, seconds=30)
    pair = (
        (began_first, began_second)
        if stored_first == "began_first"
        else (began_second, began_first)
    )
    load_runs(baseline, *pair)

    figure, _supports_overlays = _figure(SCORE_VS_RUN)

    assert list(_points(figure).y) == [50.0, 100.0, 120.0]
    assert _stars(figure) == [100.0, 120.0]


# --- Rank lines and an unexpected mode -----------------------------------------


@pytest.mark.parametrize("mode", [SCORE_VS_RUN, SCORE_VS_TIME, SCORE_VS_SENSITIVITY])
def test_the_rank_lines_are_the_selected_playlists(
    load_runs, monkeypatch, mode
) -> None:
    load_runs(*_daily_runs(10))
    asked = []

    def rank_data(playlist_code, scenario_name):
        asked.append((playlist_code, scenario_name))
        return [Rank(name="Bronze", color="#aa7744", threshold=5.0)]

    monkeypatch.setattr(
        run_history_chart, "get_rank_data_from_playlist_code", rank_data
    )

    figure, _supports_overlays = _figure(mode, playlist="KovaaKsTestCode")

    assert asked == [("KovaaKsTestCode", SCENARIO)]
    assert [annotation.text for annotation in figure.layout.annotations] == [
        "Bronze (5) "
    ]


@pytest.mark.parametrize("mode", [SCORE_VS_RUN, SCORE_VS_TIME, SCORE_VS_SENSITIVITY])
def test_no_playlist_means_no_rank_lines_and_no_lookup(
    load_runs, monkeypatch, mode
) -> None:
    load_runs(*_daily_runs(10))
    monkeypatch.setattr(
        run_history_chart,
        "get_rank_data_from_playlist_code",
        lambda *_args: pytest.fail("looked up a ladder with no playlist selected"),
    )

    figure, _supports_overlays = _figure(mode, playlist=None)

    assert not figure.layout.annotations


@pytest.mark.parametrize("mode", [SCORE_VS_RUN, SCORE_VS_TIME, SCORE_VS_SENSITIVITY])
def test_both_rank_switches_reach_the_figure(load_runs, monkeypatch, mode) -> None:
    """Silver is inside the plotted scores, and Bronze and Gold are the nearest outside.

    Platinum is drawn only with Show all ranks on, and none is drawn with
    Rank thresholds off, whatever Show all ranks says.
    """
    load_runs(
        _run(90.0, MIDNIGHT_TODAY - timedelta(days=1)),
        _run(120.0, MIDNIGHT_TODAY),
    )
    ladder = [
        Rank(name="Bronze", color="#aaaaaa", threshold=80),
        Rank(name="Silver", color="#bbbbbb", threshold=110),
        Rank(name="Gold", color="#ffcc00", threshold=150),
        Rank(name="Platinum", color="#cccccc", threshold=500),
    ]
    monkeypatch.setattr(
        run_history_chart, "get_rank_data_from_playlist_code", lambda *_args: ladder
    )

    def drawn_ranks(rank_overlay: bool, show_all_ranks: bool) -> list[str]:
        figure, _supports_overlays = build_run_history_figure(
            mode,
            SCENARIO,
            "100",
            "90",
            rank_overlay,
            show_all_ranks,
            "KovaaKsTestCode",
            TODAY,
        )
        return [
            annotation.text.split(" (")[0] for annotation in figure.layout.annotations
        ]

    assert drawn_ranks(True, False) == ["Bronze", "Silver", "Gold"]
    assert drawn_ranks(True, True) == ["Bronze", "Silver", "Gold", "Platinum"]
    assert drawn_ranks(False, True) == []


def test_an_unexpected_mode_names_the_three_it_could_have_been(
    load_runs, caplog
) -> None:
    load_runs(*_daily_runs(3))

    with caplog.at_level(logging.ERROR, logger=run_history_chart.__name__):
        figure, supports_overlays = _figure("score_vs_moon")

    assert supports_overlays is False
    assert len(figure.data) == 0
    title, message = figure.layout.annotations
    assert title.text == "<b>Unsupported graph option</b>"
    assert message.text == (
        "Choose <b>Score vs Run</b>, <b>Score vs Time</b>, or "
        "<b>Score vs Sensitivity</b>."
    )
    assert "Unsupported chart mode: 'score_vs_moon'" in caplog.text


def test_the_chart_opens_on_score_vs_run_with_100_runs_or_90_days() -> None:
    """The three layout defaults. A changed one resets what browsers remember."""
    assert run_history_chart.CHART_MODE_DEFAULT == SCORE_VS_RUN
    assert run_history_chart.RUN_RANGE_DEFAULT == "100"
    assert run_history_chart.DAY_RANGE_DEFAULT == "90"


def test_the_mode_and_range_options_read_as_the_copy_block_words_them() -> None:
    def labels(options):
        return [option["label"] for option in options]

    assert labels(run_history_chart.CHART_MODE_OPTIONS) == [
        "Score vs Run",
        "Score vs Time",
        "Score vs Sensitivity",
    ]
    assert labels(run_history_chart.RUN_RANGE_OPTIONS) == [
        "Last 50 runs",
        "Last 100 runs",
        "Last 200 runs",
        "All runs",
    ]
    assert labels(run_history_chart.DAY_RANGE_OPTIONS) == [
        "Last 7 days",
        "Last 14 days",
        "Last 30 days",
        "Last 90 days",
        "Last 12 months",
        "All time",
    ]


# --- The ring round the scenario's newest run ---------------------------------


def _ring(figure):
    return next(
        (trace for trace in figure.data if trace.name == LATEST_RUN_TRACE_NAME), None
    )


def test_each_mode_rings_the_scenarios_newest_run_tagged_with_its_id(load_runs) -> None:
    """The id is how the page tells whether that run is the last one played."""
    runs = [
        _run(100.0, MIDNIGHT_TODAY - timedelta(days=2), sens=30.0, file_name="a.csv"),
        _run(120.0, MIDNIGHT_TODAY - timedelta(days=1), sens=40.0, file_name="b.csv"),
        _run(110.0, MIDNIGHT_TODAY, sens=30.0, file_name="c.csv"),
    ]
    load_runs(*runs)

    by_run, _ = _figure(SCORE_VS_RUN)
    by_time, _ = _figure(SCORE_VS_TIME)
    by_sensitivity, _ = _figure(SCORE_VS_SENSITIVITY)

    assert (list(_ring(by_run).x), list(_ring(by_run).y)) == ([3], [110.0])
    assert list(_ring(by_time).x) == [MIDNIGHT_TODAY]
    assert list(_ring(by_sensitivity).x) == ["30.0 cm/360"]
    for figure in (by_run, by_time, by_sensitivity):
        assert _ring(figure).meta == "c.csv"
        assert list(_ring(figure).y) == [110.0]


@pytest.mark.parametrize("run_range", ["50", "100", "200", "all"])
def test_a_range_in_runs_always_holds_the_run_it_rings(load_runs, run_range) -> None:
    load_runs(*_daily_runs(260))

    figure, _supports_overlays = _figure(SCORE_VS_RUN, run_range=run_range)

    assert (list(_ring(figure).x), list(_ring(figure).y)) == ([260], [260.0])


@DAY_MODES
def test_a_newest_run_the_range_leaves_out_is_not_ringed(load_runs, mode) -> None:
    """The chart then has no run of the scenario to draw at all."""
    load_runs(
        *[
            _run(100.0 + day, MIDNIGHT_TODAY - timedelta(days=20 + day))
            for day in range(3)
        ]
    )

    in_range, _ = _figure(mode, day_range="30")
    out_of_range, supports_overlays = _figure(mode, day_range="7")

    assert _ring(in_range) is not None
    assert _ring(out_of_range) is None
    assert supports_overlays is False


@pytest.mark.parametrize("stored_first", ["began_first", "began_second"])
def test_of_two_runs_that_ended_in_one_second_the_later_played_is_ringed(
    load_runs, stored_first
) -> None:
    """The order the sessions are split in settles it, as it does for the list."""
    began_first = _run(500.0, MIDNIGHT_TODAY, seconds=90, file_name="first.csv")
    began_second = _run(400.0, MIDNIGHT_TODAY, seconds=30, file_name="second.csv")
    pair = (
        [began_first, began_second]
        if stored_first == "began_first"
        else [began_second, began_first]
    )
    load_runs(
        _run(100.0, MIDNIGHT_TODAY - timedelta(days=1), file_name="old.csv"), *pair
    )

    figure, _supports_overlays = _figure(SCORE_VS_RUN)

    assert _ring(figure).meta == "second.csv"
    assert (list(_ring(figure).x), list(_ring(figure).y)) == ([3], [400.0])
