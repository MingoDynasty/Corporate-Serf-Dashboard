"""Choose what the Run History chart plots: its modes, its ranges, and its figure.

The chart plots every run of one scenario inside a range. Score vs Run counts
its range in runs. Score vs Time and Score vs Sensitivity count theirs in
calendar days. The page holds the controls and the callback, and asks
``build_run_history_figure`` for the figure. Nothing here has a component id
or registers a callback.
"""

import logging
from datetime import date, datetime, time, timedelta

import plotly.graph_objects as go

from source.kovaaks.data_service import (
    get_rank_data_from_playlist_code,
    get_runs_in_play_order,
    get_sensitivities_vs_runs,
    new_high_score_runs,
)
from source.plot.plot_service import (
    generate_empty_plot,
    generate_score_vs_run_plot,
    generate_score_vs_sensitivity_plot,
    generate_score_vs_time_plot,
)

logger = logging.getLogger(__name__)

SCORE_VS_RUN = "score_vs_run"
SCORE_VS_TIME = "score_vs_time"
SCORE_VS_SENSITIVITY = "score_vs_sensitivity"
CHART_MODE_OPTIONS = [
    {"value": SCORE_VS_RUN, "label": "Score vs Run"},
    {"value": SCORE_VS_TIME, "label": "Score vs Time"},
    {"value": SCORE_VS_SENSITIVITY, "label": "Score vs Sensitivity"},
]
# The mode that shows every run of a session apart, which is why the chart
# opens on it. The browser remembers the mode, so this is also the layout
# default that must never change: a changed default discards what every
# browser stored.
CHART_MODE_DEFAULT = SCORE_VS_RUN

# A range select holds a count as text, or this for the whole history.
WHOLE_HISTORY = "all"
RUN_RANGE_OPTIONS = [
    {"value": "50", "label": "Last 50 runs"},
    {"value": "100", "label": "Last 100 runs"},
    {"value": "200", "label": "Last 200 runs"},
    {"value": WHOLE_HISTORY, "label": "All runs"},
]
RUN_RANGE_DEFAULT = "100"
DAY_RANGE_OPTIONS = [
    {"value": "7", "label": "Last 7 days"},
    {"value": "14", "label": "Last 14 days"},
    {"value": "30", "label": "Last 30 days"},
    {"value": "90", "label": "Last 90 days"},
    # 365 days, counted like the others, so a point leaves at midnight too.
    {"value": "365", "label": "Last 12 months"},
    {"value": WHOLE_HISTORY, "label": "All time"},
]
DAY_RANGE_DEFAULT = "90"

NO_SCENARIO_PLOT_TITLE = "No scenario selected"
NO_SCENARIO_PLOT_MESSAGE = "Select a scenario to see your score history."
NO_LOCAL_RUNS_PLOT_TITLE = "No local runs found"
NO_LOCAL_RUNS_PLOT_MESSAGE = "Play this scenario once and the graph will fill in."
NO_RUNS_IN_RANGE_PLOT_TITLE = "No runs in this range"
NO_RUNS_IN_RANGE_PLOT_MESSAGE = "Choose a longer range or play more runs."
UNSUPPORTED_MODE_PLOT_TITLE = "Unsupported graph option"
# The empty-state messages are plotly annotation text, which cannot hold a
# component, so a control name is bolded with ``<b>`` inside the string.
UNSUPPORTED_MODE_PLOT_MESSAGE = (
    "Choose <b>Score vs Run</b>, <b>Score vs Time</b>, or <b>Score vs Sensitivity</b>."
)


def _range_count(
    value: str | None,
    options: list[dict[str, str]],
    default: str,
) -> int | None:
    """Read a range select's value as a count, or None for the whole history.

    A value the select does not offer reads as the default. The browser
    stores the value, so one from an older list of options can come back.
    """
    if value not in {option["value"] for option in options}:
        value = default
    return None if value == WHOLE_HISTORY else int(value)


def first_moment_of_day_range(days: int, today: date) -> datetime:
    """Return the midnight a range of ``days`` calendar dates starts at.

    The range counts today: on October 11 the last 7 days are October 5 to
    11. So the option's label and the chart agree, and a run leaves the chart
    at midnight and not in the middle of a day.
    """
    return datetime.combine(today - timedelta(days=days - 1), time.min)


def build_run_history_figure(  # noqa: PLR0913
    mode: str,
    selected_scenario: str,
    run_range: str | None,
    day_range: str | None,
    rank_overlay_switch: bool,
    show_all_ranks_switch: bool,
    selected_playlist: str | None,
    today: date,
) -> tuple[go.Figure, bool]:
    """Build the chart for one scenario that has runs, in the mode asked for.

    Returns the figure plus whether score overlays apply to it. The empty
    range and the unsupported mode return ``False``, so the caller skips
    overlays and notifications. ``run_range`` and ``day_range`` are the two
    range selects' values, and the mode decides which one is read. ``today``
    is the app's own date: a range of days counts back from it.
    """
    runs = get_runs_in_play_order(selected_scenario)
    # Judged over the whole history, and only then is the range applied: a
    # new PB the range leaves out is not drawn, and it still decides which
    # later runs beat it. Judged in play order, so the star sits on the same
    # run of a same-second pair as the order the runs are plotted in.
    new_pbs = new_high_score_runs(runs)

    if mode == SCORE_VS_RUN:
        run_count = _range_count(run_range, RUN_RANGE_OPTIONS, RUN_RANGE_DEFAULT)
        plotted = runs if run_count is None else runs[-run_count:]
        return (
            generate_score_vs_run_plot(
                plotted,
                len(runs) - len(plotted) + 1,
                selected_scenario,
                rank_overlay_switch,
                _rank_data(selected_playlist, selected_scenario),
                show_all_ranks_switch,
                new_pbs,
                today,
            ),
            True,
        )

    if mode not in (SCORE_VS_TIME, SCORE_VS_SENSITIVITY):
        logger.error("Unsupported chart mode: %r", mode)
        return (
            generate_empty_plot(
                UNSUPPORTED_MODE_PLOT_TITLE,
                UNSUPPORTED_MODE_PLOT_MESSAGE,
            ),
            False,
        )

    day_count = _range_count(day_range, DAY_RANGE_OPTIONS, DAY_RANGE_DEFAULT)
    if day_count is not None:
        first_moment = first_moment_of_day_range(day_count, today)
        runs = [run for run in runs if run.datetime_object >= first_moment]
    if not runs:
        return (
            generate_empty_plot(
                NO_RUNS_IN_RANGE_PLOT_TITLE,
                NO_RUNS_IN_RANGE_PLOT_MESSAGE,
            ),
            False,
        )

    rank_data = _rank_data(selected_playlist, selected_scenario)
    if mode == SCORE_VS_TIME:
        return (
            generate_score_vs_time_plot(
                runs,
                selected_scenario,
                rank_overlay_switch,
                rank_data,
                show_all_ranks_switch,
                new_pbs,
            ),
            True,
        )

    in_range = set(runs)
    return (
        generate_score_vs_sensitivity_plot(
            # The store keeps the sensitivities sorted, which is the order
            # the axis lists them in.
            [
                run
                for runs_at_sensitivity in get_sensitivities_vs_runs(
                    selected_scenario
                ).values()
                for run in runs_at_sensitivity
                if run in in_range
            ],
            selected_scenario,
            rank_overlay_switch,
            rank_data,
            show_all_ranks_switch,
        ),
        True,
    )


def _rank_data(selected_playlist: str | None, selected_scenario: str) -> list:
    """Return the selected playlist's rank ladder for the scenario, if it has one."""
    if not selected_playlist:
        return []
    return get_rank_data_from_playlist_code(selected_playlist, selected_scenario)
