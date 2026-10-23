"""Choose what the Run History chart plots: its modes, its ranges, and its figure.

The chart plots every run of one scenario inside a range. Score vs Run counts
its range in runs. Score vs Time and Score vs Sensitivity count theirs in
calendar days. The first two draw the typical score over the runs. The page
holds the controls and the callback, and asks ``build_run_history_figure``
for the figure. Nothing here has a component id or registers a callback.
"""

import logging
from datetime import date, datetime, time, timedelta

import plotly.graph_objects as go

from source.kovaaks.data_models import run_id
from source.kovaaks.data_service import (
    get_all_runs,
    get_rank_data_from_playlist_code,
    get_sensitivities_vs_runs,
    new_high_score_runs,
)
from source.kovaaks.play_sessions import in_play_order, split_into_play_sessions
from source.kovaaks.typical_score import build_typical_scores
from source.plot.plot_service import (
    generate_empty_plot,
    generate_score_vs_run_plot,
    generate_score_vs_sensitivity_plot,
    generate_score_vs_time_plot,
    typical_score_hold_traces,
    typical_score_traces,
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
    *,
    typical_score_switch: bool,
    middle_50_switch: bool,
    middle_80_switch: bool,
) -> tuple[go.Figure, bool]:
    """Build the chart for one scenario that has runs, in the mode asked for.

    Returns the figure plus whether score overlays apply to it. The empty
    range and the unsupported mode return ``False``, so the caller skips
    the overlays. ``run_range`` and ``day_range`` are the two
    range selects' values, and the mode decides which one is read. ``today``
    is the app's own date: a range of days counts back from it.

    The scenario's newest run is ringed when the range holds it, in a trace
    tagged with the run's id. The graph matches it to the card's run id so
    the card and chart identify the same run after a change of scenario.

    Score vs Run and Score vs Time also draw the typical score's line and
    bands, each while its switch is on: at each run on Score vs Run, and on
    Score vs Time each value held flat to the next run. Score vs Sensitivity
    draws neither.
    """
    # One copy of the store for the scenario's runs and, when the typical
    # score is drawn, the play sessions: a run that lands mid-build is then in
    # both or neither, and ``build_typical_scores`` refuses a run its sessions
    # don't hold.
    all_runs = get_all_runs()
    runs = in_play_order(run for run in all_runs if run.scenario == selected_scenario)
    newest = runs[-1]
    newest_id = run_id(newest)
    # Judged over the whole history, and only then is the range applied: a
    # new PB the range leaves out is not drawn, and it still decides which
    # later runs beat it. Judged in play order, so the star sits on the same
    # run of a same-second pair as the order the runs are plotted in.
    new_pbs = new_high_score_runs(runs)

    if mode == SCORE_VS_RUN:
        run_count = _range_count(run_range, RUN_RANGE_OPTIONS, RUN_RANGE_DEFAULT)
        plotted = runs if run_count is None else runs[-run_count:]
        first_run_number = len(runs) - len(plotted) + 1
        figure = generate_score_vs_run_plot(
            plotted,
            first_run_number,
            selected_scenario,
            rank_overlay_switch,
            _rank_data(selected_playlist, selected_scenario),
            show_all_ranks_switch,
            new_pbs,
            today,
            newest,
            newest_id,
        )
        if typical_score_switch or middle_50_switch or middle_80_switch:
            # Worked out over the whole history before the range is applied,
            # as the stars are, so the value at the range's first run counts
            # the runs before it that the range leaves out.
            values = build_typical_scores(runs, split_into_play_sessions(all_runs))
            figure.add_traces(
                typical_score_traces(
                    range(first_run_number, len(runs) + 1),
                    values[-len(plotted) :],
                    today,
                    line=typical_score_switch,
                    middle_50=middle_50_switch,
                    middle_80=middle_80_switch,
                )
            )
        return figure, True

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
    plotted = runs
    if day_count is not None:
        first_moment = first_moment_of_day_range(day_count, today)
        plotted = [run for run in runs if run.datetime_object >= first_moment]
    if not plotted:
        return (
            generate_empty_plot(
                NO_RUNS_IN_RANGE_PLOT_TITLE,
                NO_RUNS_IN_RANGE_PLOT_MESSAGE,
            ),
            False,
        )

    rank_data = _rank_data(selected_playlist, selected_scenario)
    if mode == SCORE_VS_TIME:
        figure = generate_score_vs_time_plot(
            plotted,
            selected_scenario,
            rank_overlay_switch,
            rank_data,
            show_all_ranks_switch,
            new_pbs,
            newest,
            newest_id,
        )
        if typical_score_switch or middle_50_switch or middle_80_switch:
            # Over the whole history, as on Score vs Run. The range keeps the
            # newest runs, so the last values are the plotted runs'.
            values = build_typical_scores(runs, split_into_play_sessions(all_runs))
            figure.add_traces(
                typical_score_hold_traces(
                    values[-len(plotted) :],
                    today,
                    line=typical_score_switch,
                    middle_50=middle_50_switch,
                    middle_80=middle_80_switch,
                )
            )
        return figure, True

    in_range = set(plotted)
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
            newest,
            newest_id,
        ),
        True,
    )


def _rank_data(selected_playlist: str | None, selected_scenario: str) -> list:
    """Return the selected playlist's rank ladder for the scenario, if it has one."""
    if not selected_playlist:
        return []
    return get_rank_data_from_playlist_code(selected_playlist, selected_scenario)
