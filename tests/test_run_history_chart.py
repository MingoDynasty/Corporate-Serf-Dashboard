"""What the Run History chart plots: every run in the range its mode counts.

Each test loads runs through the real CSV loader and asks
``build_run_history_figure`` for one mode's figure, so the range, the order
the runs were played in, and which of them were new PBs are all read from the
store the app keeps.
"""

import logging
import re
import statistics
from dataclasses import replace
from datetime import date, datetime, timedelta
from itertools import pairwise

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
from source.kovaaks.play_sessions import split_into_play_sessions
from source.kovaaks.typical_score import (
    TypicalScore,
    build_typical_scores,
    typical_score_fade_time,
    typical_score_recency,
)
from source.plot.plot_service import (
    LATEST_RUN_TRACE_NAME,
    MIDDLE_50_TRACE_NAME,
    MIDDLE_80_TRACE_NAME,
    NEW_PB_TRACE_NAME,
    RUN_DATA_POINT_TRACE_NAME,
    TYPICAL_SCORE_TRACE_NAME,
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


def _figure(  # noqa: PLR0913
    mode: str,
    *,
    run_range: str | None = "100",
    day_range: str | None = "90",
    playlist: str | None = None,
    today: date = TODAY,
    typical_score: bool = True,
    middle_50: bool = True,
    middle_80: bool = True,
):
    """Build a figure with the switches as a first visit draws them, unless told."""
    return build_run_history_figure(
        mode,
        SCENARIO,
        run_range,
        day_range,
        True,
        False,
        playlist,
        today,
        typical_score_switch=typical_score,
        middle_50_switch=middle_50,
        middle_80_switch=middle_80,
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

    figure, _supports_overlays = _figure(
        SCORE_VS_RUN,
        run_range="50",
        typical_score=False,
        middle_50=False,
        middle_80=False,
    )

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
            typical_score_switch=True,
            middle_50_switch=True,
            middle_80_switch=True,
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


# --- The typical score on Score vs Run ------------------------------------------

TYPICAL_SCORE_NAMES = {
    TYPICAL_SCORE_TRACE_NAME,
    MIDDLE_50_TRACE_NAME,
    MIDDLE_80_TRACE_NAME,
}


def _sitting(first: datetime, scores: list[float]) -> list[RunData]:
    """Build one play session: a run a minute, starting at ``first``."""
    return [
        _run(score, first + timedelta(minutes=index))
        for index, score in enumerate(scores)
    ]


def _return_after_a_break() -> list[RunData]:
    """Build 35 runs: two sittings in August, then one after 60 days away.

    Runs 1 to 12 are one sitting, so the value is unknown until run 13 opens
    the second. Runs 13 to 20 are recent at their runs. Runs 21 to 29 come
    back with fewer than 10 of their 20 runs from the last 30 days, and from
    run 30 on, 10 or more are.
    """
    return [
        *_sitting(datetime(2026, 8, 1, 10), [100.0 + n for n in range(1, 13)]),
        *_sitting(datetime(2026, 8, 2, 10), [100.0 + n for n in range(13, 21)]),
        *_sitting(datetime(2026, 10, 1, 10), [200.0 + n for n in range(1, 16)]),
    ]


def _typical_traces(figure) -> list:
    return [trace for trace in figure.data if trace.name in TYPICAL_SCORE_NAMES]


def _line_traces(figure) -> tuple:
    """Return the faded line and the full-strength line, either None if absent."""
    lines = [t for t in figure.data if t.name == TYPICAL_SCORE_TRACE_NAME]
    faded = [t for t in lines if t.opacity < 1]
    full = [t for t in lines if t.opacity == 1]
    return (faded[0] if faded else None), (full[0] if full else None)


def _hover_lines(trace, x_value: float) -> list[str]:
    """Render a line trace's hover at one point, as plotly would fill it in."""
    index = list(trace.x).index(x_value)
    text = re.sub(
        r"%\{customdata\[(\d+)\]\}",
        lambda match: str(trace.customdata[index][int(match.group(1))]),
        trace.hovertemplate.removesuffix("<extra></extra>"),
    )
    return text.split("<br>")


def test_the_line_starts_at_the_first_known_value_and_fades_where_not_recent(
    load_runs,
) -> None:
    """Runs 21 to 29 are faded, and the stretch meets the full line at 20 and 30."""
    load_runs(*_return_after_a_break())

    figure, _supports_overlays = _figure(SCORE_VS_RUN)
    faded, full = _line_traces(figure)

    assert list(full.x) == [*range(13, 21), None, *range(30, 36)]
    assert list(faded.x) == list(range(20, 31))
    # Where the two kinds meet, both hold the same value: no step and no gap.
    full_at = dict(zip(full.x, full.y, strict=True))
    assert faded.y[0] == full_at[20]
    assert faded.y[-1] == full_at[30] == 160.5
    # The bands' shapes cover the same stretches, top then bottom.
    for trace in _typical_traces(figure):
        if trace.fill == "toself":
            drawn = {x for x in trace.x if x is not None}
            assert drawn == set(faded.x if trace.opacity < 1 else full.x) - {None}


def test_a_value_at_the_ranges_left_edge_counts_the_runs_the_range_hides(
    load_runs,
) -> None:
    """Judged over the whole history first, as the stars are."""
    load_runs(*_daily_runs(120))

    figure, _supports_overlays = _figure(SCORE_VS_RUN, run_range="100")
    _faded, full = _line_traces(figure)

    # Run 21's last 20 runs are runs 2 to 21, scored 2 to 21.
    assert (full.x[0], full.y[0]) == (21, 11.5)


def test_the_traces_draw_under_the_runs_in_their_own_order(load_runs) -> None:
    """The run trace stays first, so the run points keep the colorway's first color.

    Inside their layer the line draws over the bands and full strength over
    faded, each metric in one legend group, ranked after the stars.
    """
    load_runs(*_return_after_a_break())

    figure, _supports_overlays = _figure(SCORE_VS_RUN)
    typical = _typical_traces(figure)

    assert figure.data[0].name == RUN_DATA_POINT_TRACE_NAME
    assert all(trace.zorder is None for trace in figure.data[:3])
    assert [(trace.name, trace.opacity) for trace in typical] == [
        (MIDDLE_80_TRACE_NAME, 0.35),
        (MIDDLE_50_TRACE_NAME, 0.35),
        (MIDDLE_80_TRACE_NAME, 1),
        (MIDDLE_50_TRACE_NAME, 1),
        (TYPICAL_SCORE_TRACE_NAME, 0.35),
        (TYPICAL_SCORE_TRACE_NAME, 1),
    ]
    assert {trace.zorder for trace in typical} == {-1}
    assert all(trace.legendgroup == trace.name for trace in typical)
    assert {(trace.name, trace.legendrank) for trace in typical} == {
        (TYPICAL_SCORE_TRACE_NAME, 1001),
        (MIDDLE_50_TRACE_NAME, 1002),
        (MIDDLE_80_TRACE_NAME, 1003),
    }
    # One entry a metric, on its full-strength trace.
    assert [trace.showlegend for trace in typical] == [
        False,
        False,
        True,
        True,
        False,
        True,
    ]
    # The bands take no hover; the line has its own.
    assert {trace.hoverinfo for trace in typical if trace.fill == "toself"} == {"skip"}


def test_a_metric_with_only_a_faded_stretch_gives_it_the_legend_entry(
    load_runs,
) -> None:
    """A run every four days never has 10 in the last 30 days."""
    load_runs(
        *[
            _run(100.0 + index, MIDNIGHT_TODAY - timedelta(days=4 * (19 - index)))
            for index in range(20)
        ]
    )

    figure, _supports_overlays = _figure(SCORE_VS_RUN)
    typical = _typical_traces(figure)

    assert [(trace.name, trace.opacity, trace.showlegend) for trace in typical] == [
        (MIDDLE_80_TRACE_NAME, 0.35, True),
        (MIDDLE_50_TRACE_NAME, 0.35, True),
        (TYPICAL_SCORE_TRACE_NAME, 0.35, True),
    ]
    # Known from the 10th run, which has 10 runs from 10 sessions.
    assert typical[-1].x[0] == 10


def test_a_scenario_with_no_known_value_has_no_typical_score_traces(
    load_runs,
) -> None:
    """Twelve runs in one sitting: no value yet, and no line to draw."""
    load_runs(*_sitting(datetime(2026, 10, 12, 10), [100.0] * 12))

    figure, _supports_overlays = _figure(SCORE_VS_RUN)

    assert _typical_traces(figure) == []


@pytest.mark.parametrize("bridged", [False, True])
def test_the_sessions_are_split_over_every_scenarios_runs(load_runs, bridged) -> None:
    """Another scenario's runs can join two sittings of this one into one session.

    Ten runs in two halves an hour apart are known. With runs on another
    scenario between the halves, they are one session and not yet known.
    """
    halves = [
        *_sitting(datetime(2026, 10, 12, 10), [100.0] * 5),
        *_sitting(datetime(2026, 10, 12, 11), [100.0] * 5),
    ]
    bridge = [
        replace(
            _run(50.0, datetime(2026, 10, 12, 10, 4) + timedelta(minutes=minutes)),
            scenario="Another scenario",
        )
        for minutes in (20, 40)
    ]
    load_runs(*halves, *(bridge if bridged else []))

    figure, _supports_overlays = _figure(SCORE_VS_RUN)

    assert (_typical_traces(figure) == []) is bridged


def test_score_vs_sensitivity_draws_no_typical_score(load_runs) -> None:
    load_runs(*_daily_runs(40))

    figure, _supports_overlays = _figure(SCORE_VS_SENSITIVITY, day_range="all")

    assert _typical_traces(figure) == []


@pytest.mark.parametrize(
    ("switches", "drawn"),
    [
        ((True, False, False), {TYPICAL_SCORE_TRACE_NAME}),
        ((False, True, False), {MIDDLE_50_TRACE_NAME}),
        ((False, False, True), {MIDDLE_80_TRACE_NAME}),
        ((False, True, True), {MIDDLE_50_TRACE_NAME, MIDDLE_80_TRACE_NAME}),
        ((False, False, False), set()),
    ],
)
def test_each_metric_is_drawn_only_while_its_switch_is_on(
    load_runs, switches, drawn
) -> None:
    """A band can show without the line, and its faded stretch goes with it."""
    load_runs(*_return_after_a_break())
    typical_score, middle_50, middle_80 = switches

    figure, _supports_overlays = _figure(
        SCORE_VS_RUN,
        typical_score=typical_score,
        middle_50=middle_50,
        middle_80=middle_80,
    )

    names = [trace.name for trace in _typical_traces(figure)]
    assert set(names) == drawn
    # Each metric drawn has its faded stretch and its full strength.
    assert all(names.count(name) == 2 for name in drawn)


def test_the_lines_hover_says_the_value_its_runs_how_recent_and_each_band(
    load_runs,
) -> None:
    """Run 30's last 20 runs: 10 from August, 10 from October 1."""
    load_runs(*_return_after_a_break())

    _faded, full = _line_traces(_figure(SCORE_VS_RUN)[0])

    assert _hover_lines(full, 30) == [
        "<b>Typical score</b>: 161",
        "<b>Runs</b>: 20 in 3 sessions · Aug 1 to Oct 1",
        "<b>Recent</b>: 10 of 20 in the 30 days up to this run",
        "<b>Middle 50%</b>: 116 to 205",
        "<b>Middle 80%</b>: 113 to 208",
    ]
    assert full.hoverlabel.font.size == 16


def test_the_hover_counts_one_session_and_a_span_on_one_date(load_runs) -> None:
    """Run 21's last twenty runs are known, from one session on one date."""
    load_runs(*_sitting(datetime(2026, 10, 12, 10), [100.0] * 21))

    _faded, full = _line_traces(_figure(SCORE_VS_RUN)[0])

    assert _hover_lines(full, 21)[1] == "<b>Runs</b>: 20 in 1 session · on Oct 12"


@pytest.mark.parametrize(
    ("runs", "known_at"),
    [
        # Ten runs from two sessions: the tenth is the first known value.
        (
            [
                *_sitting(
                    datetime(2026, 10, 11, 10), [100.0, 104.0, 108.0, 112.0, 116.0]
                ),
                *_sitting(
                    datetime(2026, 10, 12, 10), [120.0, 124.0, 128.0, 132.0, 136.0]
                ),
            ],
            10,
        ),
        # Twenty runs in one sitting: the twentieth is.
        (_sitting(datetime(2026, 10, 12, 10), [100.0 + n for n in range(20)]), 20),
    ],
)
def test_a_scenarios_only_known_value_is_drawn_flat_for_half_a_run_each_side(
    load_runs, runs, known_at
) -> None:
    """A one-point line draws nothing in plotly, and a one-point band has no width."""
    load_runs(*runs)

    figure, _supports_overlays = _figure(SCORE_VS_RUN)
    typical = _typical_traces(figure)
    _faded, full = _line_traces(figure)

    stretch = [known_at - 0.5, known_at, known_at + 0.5]
    assert [trace.name for trace in typical] == [
        MIDDLE_80_TRACE_NAME,
        MIDDLE_50_TRACE_NAME,
        TYPICAL_SCORE_TRACE_NAME,
    ]
    assert list(full.x) == stretch
    assert len(set(full.y)) == 1
    assert full.customdata[0] == full.customdata[1] == full.customdata[2]
    for band in typical[:2]:
        assert list(band.x) == [*stretch, *reversed(stretch)]
        top, bottom = band.y[0], band.y[3]
        assert top > full.y[0] > bottom
    assert all(trace.showlegend for trace in typical)


def test_a_zoom_on_the_only_known_values_run_still_holds_its_line_and_bands(
    load_runs,
) -> None:
    """The zoom fit counts only the points inside the window, so the run keeps one.

    The window holds run 10 alone, narrower than the half runs drawn on
    either side of it. The fit's rule is ``assets/homeGraphZoomFit.js``'s.
    """
    load_runs(
        *_sitting(datetime(2026, 10, 11, 10), [100.0, 104.0, 108.0, 112.0, 116.0]),
        *_sitting(datetime(2026, 10, 12, 10), [120.0, 124.0, 128.0, 132.0, 136.0]),
    )

    figure, _supports_overlays = _figure(SCORE_VS_RUN)
    start, end = 9.75, 10.25
    in_window = {
        trace.name: sorted(
            y
            for x, y in zip(trace.x, trace.y, strict=True)
            if x is not None and start <= x <= end
        )
        for trace in _typical_traces(figure)
    }

    median = statistics.median([100.0 + 4 * n for n in range(10)])
    assert in_window[TYPICAL_SCORE_TRACE_NAME] == [median]
    # Each band's bottom and top at run 10.
    for name in (MIDDLE_50_TRACE_NAME, MIDDLE_80_TRACE_NAME):
        bottom, top = in_window[name]
        assert bottom < median < top


def test_with_more_than_one_known_value_every_point_sits_at_its_run(
    load_runs,
) -> None:
    """Only a figure's one known value is drawn flat around its run."""
    load_runs(*_return_after_a_break())

    figure, _supports_overlays = _figure(SCORE_VS_RUN)

    assert all(
        float(x).is_integer() for trace in _typical_traces(figure) for x in trace.x if x
    )


@pytest.mark.parametrize(
    ("middle_50", "middle_80", "band_lines"),
    [
        (True, False, ["<b>Middle 50%</b>: 116 to 205"]),
        (False, True, ["<b>Middle 80%</b>: 113 to 208"]),
        (False, False, []),
    ],
)
def test_a_bands_hover_line_shows_only_with_its_band(
    load_runs, middle_50, middle_80, band_lines
) -> None:
    load_runs(*_return_after_a_break())

    _faded, full = _line_traces(
        _figure(SCORE_VS_RUN, middle_50=middle_50, middle_80=middle_80)[0]
    )

    assert _hover_lines(full, 30)[3:] == band_lines


def test_the_hover_dates_carry_the_year_only_in_another_year(load_runs) -> None:
    load_runs(*_return_after_a_break())

    _faded, full = _line_traces(_figure(SCORE_VS_RUN, today=date(2027, 1, 5))[0])

    assert _hover_lines(full, 30)[1] == (
        "<b>Runs</b>: 20 in 3 sessions · Aug 1, 2026 to Oct 1, 2026"
    )


# --- The typical score on Score vs Time ------------------------------------------


def _known_at_ten(first: datetime) -> list[RunData]:
    """Build ten runs in two sittings a day apart, so the tenth is the first known.

    Scored 100 to 118 by twos, so the value after the tenth is 109.
    """
    scores = [100.0 + 2 * n for n in range(10)]
    return [
        *_sitting(first, scores[:5]),
        *_sitting(first + timedelta(days=1), scores[5:]),
    ]


def _values(runs: list[RunData]) -> list[TypicalScore]:
    """Work out the value after each of one scenario's runs, as the chart does."""
    return build_typical_scores(runs, split_into_play_sessions(runs))


def _held(trace) -> list[tuple]:
    """Return a trace's points as (time, value) pairs, a gap as (None, None)."""
    return list(zip(trace.x, trace.y, strict=True))


def _hover_at(trace, index: int) -> list[str]:
    """Render a line trace's hover at its point ``index``, as plotly would."""
    text = re.sub(
        r"%\{customdata\[(\d+)\]\}",
        lambda match: str(trace.customdata[index][int(match.group(1))]),
        trace.hovertemplate.removesuffix("<extra></extra>"),
    )
    return text.split("<br>")


def test_score_vs_time_holds_each_value_flat_to_the_next_run(load_runs) -> None:
    """A step at each run, and the line ends at the newest run, on its value."""
    runs = [
        *_known_at_ten(datetime(2026, 10, 1, 10)),
        _run(150.0, datetime(2026, 10, 5, 10)),
        _run(160.0, datetime(2026, 10, 8, 10)),
    ]
    load_runs(*runs)

    figure, _supports_overlays = _figure(SCORE_VS_TIME, day_range="all")
    faded, full = _line_traces(figure)

    t10, t11, t12 = (run.datetime_object for run in runs[-3:])
    v10, v11, v12 = _values(runs)[-3:]
    assert faded is None
    assert _held(full) == [
        (t10, v10.median),
        (t11, v10.median),
        (t11, v11.median),
        (t12, v11.median),
        (t12, v12.median),
    ]
    # The middle 50% steps with it, along its top and back along its bottom.
    (band,) = [trace for trace in figure.data if trace.name == MIDDLE_50_TRACE_NAME]
    assert list(band.x) == [t10, t11, t11, t12, t12, t12, t12, t11, t11, t10]
    assert list(band.y) == [
        v10.p75,
        v10.p75,
        v11.p75,
        v11.p75,
        v12.p75,
        v12.p25,
        v11.p25,
        v11.p25,
        v10.p25,
        v10.p25,
    ]
    # Nothing is drawn past the newest run.
    assert max(x for trace in _typical_traces(figure) for x in trace.x if x) == t12


def test_a_hold_fades_when_its_tenth_newest_run_turns_30_days_old(load_runs) -> None:
    """Full strength up to that moment, faded after it, then the next value.

    The tenth run's value is recent while its oldest run, its tenth newest,
    ended in the last 30 days. The next run comes a month after that.
    """
    runs = [
        *_known_at_ten(datetime(2026, 8, 1, 10)),
        _run(150.0, datetime(2026, 10, 1, 10)),
    ]
    load_runs(*runs)

    faded, full = _line_traces(_figure(SCORE_VS_TIME, day_range="all")[0])

    values = _values(runs)
    fade = typical_score_fade_time(values[9])
    assert fade == datetime(2026, 8, 31, 10)
    assert typical_score_recency(values[9], fade).recent
    assert not typical_score_recency(values[9], fade + timedelta(seconds=1)).recent
    tenth, eleventh = (run.datetime_object for run in runs[-2:])
    assert _held(full) == [(tenth, 109.0), (fade, 109.0)]
    # The faded part starts where the full strength ends and meets the next
    # value where it begins.
    assert _held(faded) == [
        (fade, 109.0),
        (eleventh, 109.0),
        (eleventh, values[10].median),
    ]


def test_a_holds_hover_is_its_values_at_both_ends_and_its_faded_part_has_no_count(
    load_runs,
) -> None:
    """The count changes along a hold whose runs age out, so it isn't given."""
    load_runs(
        *_known_at_ten(datetime(2026, 8, 1, 10)),
        _run(150.0, datetime(2026, 10, 1, 10)),
    )

    faded, full = _line_traces(_figure(SCORE_VS_TIME, day_range="all")[0])

    value = [
        "<b>Typical score</b>: 109",
        "<b>Runs</b>: 10 in 2 sessions · Aug 1 to Aug 2",
    ]
    bands = ["<b>Middle 50%</b>: 105 to 114", "<b>Middle 80%</b>: 102 to 116"]
    for end in (0, 1):
        assert _hover_at(full, end) == [
            *value,
            "<b>Recent</b>: 10 of 10 in the 30 days up to this run",
            *bands,
        ]
        assert _hover_at(faded, end) == [
            *value,
            "<b>Recent</b>: too few · last run Aug 2",
            *bands,
        ]
    # Where the faded part meets the next value, the point is that value's.
    assert _hover_at(faded, 2)[:3] == [
        "<b>Typical score</b>: 110",
        "<b>Runs</b>: 11 in 3 sessions · Aug 1 to Oct 1",
        "<b>Recent</b>: 1 of 11 in the 30 days up to this run",
    ]
    assert full.hoverlabel.font.size == faded.hoverlabel.font.size == 16


@pytest.mark.parametrize(
    ("after_the_fade", "fades"), [(timedelta(0), False), (timedelta(seconds=1), True)]
)
def test_a_hold_is_recent_at_its_fade_time_and_faded_a_second_later(
    load_runs, after_the_fade, fades
) -> None:
    """The next run lands on the tenth run's fade time, or one second after it."""
    fade = datetime(2026, 8, 31, 10)
    runs = [
        *_known_at_ten(datetime(2026, 8, 1, 10)),
        _run(150.0, fade + after_the_fade),
    ]
    load_runs(*runs)

    faded, full = _line_traces(_figure(SCORE_VS_TIME, day_range="all")[0])

    eleventh = runs[-1].datetime_object
    after = _values(runs)[-1].median
    if not fades:
        assert faded is None
        assert _held(full) == [
            (runs[9].datetime_object, 109.0),
            (fade, 109.0),
            (eleventh, after),
        ]
    else:
        # A second of faded hold, and the eleventh value is recent again.
        assert _held(faded) == [(fade, 109.0), (eleventh, 109.0), (eleventh, after)]
        assert _held(full)[-1] == (eleventh, after)


def test_a_value_not_recent_at_its_run_holds_faded_throughout(load_runs) -> None:
    """A run every four days never has 10 in the last 30 days.

    Each hold is faded from its run, so both its ends keep the count at its
    run: none of them is a hold whose runs aged out after it.
    """
    runs = [
        _run(100.0 + index, MIDNIGHT_TODAY - timedelta(days=4 * (19 - index)))
        for index in range(20)
    ]
    load_runs(*runs)

    figure, _supports_overlays = _figure(SCORE_VS_TIME, day_range="all")
    faded, full = _line_traces(figure)

    times = [run.datetime_object for run in runs]
    assert full is None
    # Known from the tenth run, each value held to the next run's time.
    assert list(faded.x) == [times[9], *[time for time in times[10:] for _ in "lr"]]
    assert _hover_at(faded, 0) == _hover_at(faded, 1)
    assert _hover_at(faded, 0)[2] == (
        "<b>Recent</b>: 8 of 10 in the 30 days up to this run"
    )
    assert all(
        _hover_at(faded, index)[2].endswith("in the 30 days up to this run")
        for index in range(len(faded.x))
    )
    assert all(trace.showlegend for trace in _typical_traces(figure))


def test_after_a_break_the_faded_part_meets_the_next_full_strength_value(
    load_runs,
) -> None:
    """Run 20's hold fades over the break, 21 to 29 come back faded, 30 is full."""
    runs = _return_after_a_break()
    load_runs(*runs)

    faded, full = _line_traces(_figure(SCORE_VS_TIME, day_range="all")[0])

    gap = list(full.x).index(None)
    fade = typical_score_fade_time(_values(runs)[19])
    assert fade == datetime(2026, 8, 31, 10, 10)
    assert _held(full)[gap - 1] == _held(faded)[0] == (fade, full.y[gap - 1])
    assert _held(faded)[-1] == _held(full)[gap + 1]
    assert _held(faded)[-1] == (runs[29].datetime_object, 160.5)
    assert full.x[-1] == runs[-1].datetime_object


def test_score_vs_time_values_at_the_ranges_left_edge_count_the_runs_it_hides(
    load_runs,
) -> None:
    """Judged over the whole history first, as on Score vs Run."""
    load_runs(*_daily_runs(120))

    _faded, full = _line_traces(_figure(SCORE_VS_TIME, day_range="90")[0])

    # The range starts at run 31's midnight; its last 20 runs score 12 to 31.
    assert (full.x[0], full.y[0]) == (first_moment_of_day_range(90, TODAY), 21.5)


def test_of_two_runs_in_one_second_the_later_played_ones_value_holds(
    load_runs,
) -> None:
    """The first one's value holds for no time, so the step skips it.

    The pair is drawn with its new PB last, the other way round from play
    order, so pairing a value with a place on the chart would hold the
    wrong one.
    """
    ended = datetime(2026, 10, 12, 12)
    new_pb = replace(_run(200.0, ended, seconds=90), accuracy=0.25)
    tie = replace(_run(200.0, ended, seconds=30), accuracy=0.75)
    runs = [
        *_known_at_ten(datetime(2026, 10, 10, 10)),
        new_pb,
        tie,
        _run(150.0, ended + timedelta(hours=2)),
    ]
    load_runs(*runs)

    figure, _supports_overlays = _figure(SCORE_VS_TIME, day_range="all")
    _faded, full = _line_traces(figure)

    assert [data[1] for data in _points(figure).customdata[10:12]] == [75.0, 25.0]
    v10, v11, v12, v13 = (value.median for value in _values(runs)[-4:])
    assert v11 not in {v10, v12}
    assert _held(full) == [
        (runs[9].datetime_object, v10),
        (ended, v10),
        (ended, v12),
        (runs[-1].datetime_object, v12),
        (runs[-1].datetime_object, v13),
    ]


@pytest.mark.parametrize(
    ("runs", "day_range", "opacity"),
    [
        # Ten runs from two sessions: only the tenth, the newest, is known.
        (_known_at_ten(datetime(2026, 10, 11, 10)), "all", 1),
        # A range that holds one run, whose value counts runs before it.
        (
            [
                *_known_at_ten(datetime(2026, 8, 1, 10)),
                _run(150.0, datetime(2026, 10, 12, 10)),
            ],
            "7",
            0.35,
        ),
    ],
)
def test_score_vs_times_only_value_is_marked_at_its_run(
    load_runs, runs, day_range, opacity
) -> None:
    """It holds for no time, so the line is a level stroke and each band a bar."""
    load_runs(*runs)

    figure, _supports_overlays = _figure(SCORE_VS_TIME, day_range=day_range)
    typical = _typical_traces(figure)

    value = _values(runs)[-1]
    when = runs[-1].datetime_object
    assert [trace.name for trace in typical] == [
        MIDDLE_80_TRACE_NAME,
        MIDDLE_50_TRACE_NAME,
        TYPICAL_SCORE_TRACE_NAME,
    ]
    stroke = typical[-1]
    assert (stroke.mode, stroke.marker.symbol, stroke.marker.size) == (
        "markers",
        "line-ew",
        14,
    )
    assert (list(stroke.x), list(stroke.y)) == ([when], [value.median])
    assert len(stroke.customdata) == 1
    for bar, (bottom, top) in zip(
        typical[:2], [(value.p10, value.p90), (value.p25, value.p75)], strict=True
    ):
        assert (bar.fill, bar.line.width, bar.line.color) == ("none", 14, bar.fillcolor)
        assert (list(bar.x), list(bar.y)) == ([when, when], [top, bottom])
    assert {(trace.opacity, trace.showlegend) for trace in typical} == {(opacity, True)}


def test_score_vs_time_draws_the_traces_as_score_vs_run_does(load_runs) -> None:
    """Under the runs, in the same order, legend groups and entries."""
    load_runs(*_return_after_a_break())

    figure, _supports_overlays = _figure(SCORE_VS_TIME, day_range="all")
    typical = _typical_traces(figure)

    assert figure.data[0].name == RUN_DATA_POINT_TRACE_NAME
    assert [(trace.name, trace.opacity, trace.showlegend) for trace in typical] == [
        (MIDDLE_80_TRACE_NAME, 0.35, False),
        (MIDDLE_50_TRACE_NAME, 0.35, False),
        (MIDDLE_80_TRACE_NAME, 1, True),
        (MIDDLE_50_TRACE_NAME, 1, True),
        (TYPICAL_SCORE_TRACE_NAME, 0.35, False),
        (TYPICAL_SCORE_TRACE_NAME, 1, True),
    ]
    assert {trace.zorder for trace in typical} == {-1}
    assert all(trace.legendgroup == trace.name for trace in typical)
    assert {trace.hoverinfo for trace in typical if trace.fill == "toself"} == {"skip"}


@pytest.mark.parametrize(
    ("switches", "drawn", "band_lines"),
    [
        ((True, False, False), {TYPICAL_SCORE_TRACE_NAME}, 0),
        ((True, True, False), {TYPICAL_SCORE_TRACE_NAME, MIDDLE_50_TRACE_NAME}, 1),
        ((False, False, True), {MIDDLE_80_TRACE_NAME}, None),
        ((False, False, False), set(), None),
    ],
)
def test_score_vs_time_draws_each_metric_only_while_its_switch_is_on(
    load_runs, switches, drawn, band_lines
) -> None:
    """A band's line in the hover shows only with its band."""
    load_runs(*_return_after_a_break())
    typical_score, middle_50, middle_80 = switches

    figure, _supports_overlays = _figure(
        SCORE_VS_TIME,
        day_range="all",
        typical_score=typical_score,
        middle_50=middle_50,
        middle_80=middle_80,
    )

    names = [trace.name for trace in _typical_traces(figure)]
    assert set(names) == drawn
    assert all(names.count(name) == 2 for name in drawn)
    if band_lines is not None:
        _faded, full = _line_traces(figure)
        assert len(_hover_at(full, 0)) == 3 + band_lines


def _fitted_scores(
    figure, start: datetime, end: datetime, *, crossings: bool = True
) -> tuple[float, float] | None:
    """Return the scores the zoom fit counts in an x window, before its padding.

    Mirrors ``assets/homeGraphZoomFit.js``: every trace's points inside the
    window and, unless ``crossings`` is off, the part inside it of each
    segment of a trace drawn as lines. The live check runs the asset itself.
    """
    low, high = start.timestamp(), end.timestamp()
    scores: list[float] = []
    for trace in figure.data:
        xs = [x.timestamp() if x else None for x in trace.x]
        ys = list(trace.y)
        scores += [
            y for x, y in zip(xs, ys, strict=True) if x is not None and low <= x <= high
        ]
        if not crossings or "lines" not in (trace.mode or ""):
            continue
        for (x0, y0), (x1, y1) in pairwise(zip(xs, ys, strict=True)):
            if x0 is None or x1 is None or x0 == x1:
                continue
            left, right = max(min(x0, x1), low), min(max(x0, x1), high)
            if left <= right:
                scores += [y0 + (y1 - y0) * (x - x0) / (x1 - x0) for x in (left, right)]
    return (min(scores), max(scores)) if scores else None


def test_a_zoom_inside_a_hold_keeps_its_line_and_bands_in_view(load_runs) -> None:
    """A window in the break holds no run and no point, only run 20's held value."""
    runs = _return_after_a_break()
    load_runs(*runs)

    figure, _supports_overlays = _figure(SCORE_VS_TIME, day_range="all")
    window = (datetime(2026, 9, 10), datetime(2026, 9, 20))

    value = _values(runs)[19]
    assert _fitted_scores(figure, *window, crossings=False) is None
    assert _fitted_scores(figure, *window) == (value.p10, value.p90)
