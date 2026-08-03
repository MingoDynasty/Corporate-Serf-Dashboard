"""
This module handles functions around plots.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Generic, TypeVar

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go

from source.kovaaks.data_models import Rank, RunData
from source.utilities.utilities import format_absolute_timestamp, format_decimal

logger = logging.getLogger(__name__)

_K = TypeVar("_K")


def generate_placeholder_plot() -> go.Figure:
    """Build a neutral transparent figure for graph panels awaiting data."""
    figure = go.Figure()
    figure.update_layout(
        dragmode=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return figure


def generate_empty_plot(title: str, message: str) -> go.Figure:
    """Build an intentional empty-state figure for graph panels without data."""
    figure = go.Figure()
    figure.update_layout(
        dragmode=False,
        annotations=[
            {
                "text": f"<b>{title}</b>",
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.58,
                "showarrow": False,
                "align": "center",
                "font": {"size": 22},
            },
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.46,
                "showarrow": False,
                "align": "center",
                "font": {"size": 15},
            },
        ],
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"l": 40, "r": 40, "t": 40, "b": 40},
    )
    return figure


def add_high_score_overlay(figure: go.Figure, high_score: float) -> go.Figure:
    """Add a labeled high-score line to a figure."""
    figure.add_hline(
        name="PB Score",
        annotation_text=f"PB Score ({format_decimal(high_score):.2f})",
        y=high_score,
        line_dash="dash",
    )
    return figure


def add_score_threshold_overlay(figure: go.Figure, score_threshold: float) -> go.Figure:
    """Add a labeled score-threshold line to a figure."""
    figure.add_hline(
        name="Score Threshold",
        annotation_text=f"Score Threshold ({format_decimal(score_threshold):.2f})",
        y=score_threshold,
        line_dash="dash",
    )
    return figure


def _add_rank_overlays(
    figure: go.Figure,
    rank_overlay_switch: bool,
    rank_data: list[Rank],
    scores: list[float],
) -> None:
    """Overlay rank threshold lines spanning the plotted score range."""
    if not (rank_overlay_switch and rank_data):
        return

    # Select by threshold value, not ladder index, so the overlay is robust to
    # non-monotonic rank ladders in upstream KovaaK's data. We draw every rank
    # whose threshold lands inside the plotted score range, plus the nearest
    # context rank strictly below and strictly above that range (including any
    # ties at those boundary thresholds). This is a strict generalization of
    # the old index-bracketing: for strictly ascending ladders the selection is
    # identical (with equal thresholds the new code draws all tied ranks where
    # the old drew one).
    low = float(min(scores))
    high = float(max(scores))

    thresholds_below = [r.threshold for r in rank_data if r.threshold < low]
    thresholds_above = [r.threshold for r in rank_data if r.threshold > high]
    nearest_below = max(thresholds_below) if thresholds_below else None
    nearest_above = min(thresholds_above) if thresholds_above else None

    def _is_selected(threshold: float) -> bool:
        return low <= threshold <= high or threshold in (nearest_below, nearest_above)

    # Draw in original ladder order; do not sort or mutate rank_data (shared).
    for rank in rank_data:
        if not _is_selected(rank.threshold):
            continue
        figure.add_hline(
            name=rank.name,
            annotation_text=f"{rank.name} ({format_decimal(rank.threshold)}) ",
            y=rank.threshold,
            line_dash="dash",
            line_color=rank.color,
        )


@dataclass(frozen=True)
class _AxisDescriptor(Generic[_K]):
    """Per-axis configuration for the shared scatter/line plot builder.

    ``_K`` is the type of the ``scenario_data`` grouping key, so the x-value
    extractors stay honest per plot: sensitivity groups by ``str``, time groups
    by ``datetime.date``.

    :param axis_title: label for the x column, axis, and dataframe key.
    :param empty_message: empty-state message shown when there is no data.
    :param scatter_x: per-run x value from the ``(dict key, run)`` pair.
    :param line_x: per-group x value from the dict key.
    :param hover_x_label: hovertemplate fragment for the x value.
    """

    axis_title: str
    empty_message: str
    scatter_x: Callable[[_K, RunData], float | str | date]
    line_x: Callable[[_K], float | str | date]
    hover_x_label: str


def _generate_xy_plot(
    scenario_data: dict[_K, list[RunData]],
    scenario_name: str,
    rank_overlay_switch: bool,
    rank_data: list[Rank],
    axis: _AxisDescriptor[_K],
) -> go.Figure:
    """
    Build a scatter-plus-average-line score plot against a configurable x axis.

    :param scenario_data: the scenario data to use for the plot.
    :param scenario_name: the name of the scenario to use for the plot.
    :param rank_overlay_switch: enable/disable rank overlay.
    :param rank_data: an optional list of ranks to plot.
    :param axis: descriptor for the x column, values, and hover label.
    :return: go.Figure Plot
    """
    if not scenario_data:
        return generate_empty_plot(
            "No runs to plot",
            axis.empty_message,
        )

    axis_title = axis.axis_title
    hover_x_label = axis.hover_x_label
    scores: list[float] = []
    scatter_plot_data: dict[str, list[float | str | date]] = {
        "Score": [],
        axis_title: [],
        "Datetime": [],
        "Accuracy": [],
    }
    line_plot_data: dict[str, list[float | str | date]] = {
        "Score": [],
        axis_title: [],
    }

    for key, runs_data in scenario_data.items():
        for run_data in runs_data:
            scores.append(run_data.score)
            scatter_plot_data["Score"].append(run_data.score)
            scatter_plot_data[axis_title].append(axis.scatter_x(key, run_data))
            scatter_plot_data["Datetime"].append(
                format_absolute_timestamp(
                    run_data.datetime_object, include_seconds=True
                ),
            )
            scatter_plot_data["Accuracy"].append(round(100 * run_data.accuracy, 2))
        line_plot_data[axis_title].append(axis.line_x(key))
        line_plot_data["Score"].append(float(np.mean([rd.score for rd in runs_data])))
    # If we want to generate a trendline (e.g. lowess)
    # if len(data.keys()) <= 2:
    #     # We need at least 3 sensitivities to generate a trendline
    #     logger.debug(f"WARNING: Skipping '{scenario}' due to insufficient Sensitivity data.")
    #     return

    current_datetime = format_absolute_timestamp(datetime.today())
    title = f"{scenario_name} (updated: {current_datetime!s})"
    logger.debug("Generating plot for: %s", scenario_name)

    figure_scatter = px.scatter(
        data_frame=pd.DataFrame(scatter_plot_data),
        x=axis_title,
        y="Score",
        hover_name="Datetime",
        hover_data=["Datetime"],
        custom_data=["Datetime", "Accuracy"],
    )
    figure_scatter.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br><br>"
        + "<b>Score</b>: %{y}<br>"
        + f"{hover_x_label}<br>"
        + "<b>Accuracy</b>: %{customdata[1]}%"
        + "<extra></extra>",
        hoverlabel={"font_size": 16},
    )

    # trendline="lowess"  # simply using average line for now
    figure_line = px.line(
        data_frame=pd.DataFrame(line_plot_data),
        x=axis_title,
        y="Score",
    )
    figure_line.update_traces(
        hovertemplate="<b>Average Score</b>: %{y}<br>"
        + hover_x_label
        + "<extra></extra>",
        hoverlabel={"font_size": 16},
    )

    figure_combined = go.Figure(data=figure_scatter.data + figure_line.data)
    figure_combined.update_layout(
        title=title,
        xaxis={"title": axis_title},
        yaxis={"title": "Score"},
        font={
            "size": 14,
        },
    )
    figure_combined["data"][0]["name"] = "Run Data Point"
    figure_combined["data"][0]["showlegend"] = True
    figure_combined["data"][1]["name"] = "Average Score"
    figure_combined["data"][1]["showlegend"] = True

    _add_rank_overlays(
        figure_combined,
        rank_overlay_switch,
        rank_data,
        scores,
    )
    return figure_combined


def generate_sensitivity_plot(
    scenario_data: dict[str, list[RunData]],
    scenario_name: str,
    rank_overlay_switch: bool,
    rank_data: list[Rank],
) -> go.Figure:
    """
    Generate a plot using the scenario data.
    :param scenario_data: the scenario data to use for the plot.
    :param scenario_name: the name of the scenario to use for the plot.
    :param rank_overlay_switch: enable/disable rank overlay.
    :param rank_data: an optional list of ranks to plot.
    :return: go.Figure Plot
    """
    return _generate_xy_plot(
        scenario_data,
        scenario_name,
        rank_overlay_switch,
        rank_data,
        _AxisDescriptor[str](
            axis_title="Sensitivity",
            empty_message="No sensitivity data is available for this scenario yet.",
            scatter_x=lambda _key, run: f"{run.horizontal_sens} {run.sens_scale}",
            line_x=lambda key: key,
            hover_x_label="<b>Sensitivity</b>: %{x}",
        ),
    )


def generate_time_plot(
    scenario_data: dict[date, list[RunData]],
    scenario_name: str,
    rank_overlay_switch: bool,
    rank_data: list[Rank],
) -> go.Figure:
    """
    Generate a plot using the scenario data.
    :param scenario_data: the scenario data to use for the plot.
    :param scenario_name: the name of the scenario to use for the plot.
    :param rank_overlay_switch: enable/disable rank overlay.
    :param rank_data: an optional list of ranks to plot.
    :return: go.Figure Plot
    """
    return _generate_xy_plot(
        scenario_data,
        scenario_name,
        rank_overlay_switch,
        rank_data,
        _AxisDescriptor[date](
            axis_title="Date",
            empty_message="No score history is available for this scenario yet.",
            scatter_x=lambda key, _run: key,
            line_x=lambda key: key,
            hover_x_label="<b>Date</b>: %{x}",
        ),
    )


def apply_light_dark_mode(figure: go.Figure, color_scheme: str) -> go.Figure:
    """
    Apply light or dark mode to figure.
    :param figure: figure to lighten or darken.
    :param color_scheme: active Mantine color scheme.
    :return: figure with template applied.
    """
    template = "mantine_dark" if color_scheme == "dark" else "mantine_light"
    figure.update_layout(template=template)
    return figure


def generate_aim_training_journey_plot(
    journey_data: dict[str, dict[datetime, float]],
    aim_training_checkpoints: dict[datetime, int],
) -> go.Figure:
    """Plot playlist progress over time with training-hour checkpoints."""
    figures = {}

    # loop through each playlist and data and build a line plot
    for idx, (playlist, journey) in enumerate(journey_data.items()):
        line_plot_data: dict[str, list] = {
            "Date": [],
            "Percentage": [],
        }

        for date_obj, percentage in journey.items():
            line_plot_data["Date"].append(date_obj)
            line_plot_data["Percentage"].append(round(100 * percentage, 2))

        figure_line = px.line(
            data_frame=pd.DataFrame(line_plot_data),
            x="Date",
            y="Percentage",
            markers=True,
            title=playlist,
        )
        figure_line.update_traces(
            line_color=figure_line.layout.template.layout.colorway[idx],
        )
        figures[playlist] = figure_line

    # combined the data for each line plot into a single plot
    data = None
    for figure in figures.values():
        data = figure.data if data is None else data + figure.data

    figure_combined = go.Figure(data=data)
    figure_combined.update_layout(
        title="Aim Training Journey",
        xaxis={"title": "Datetime"},
        yaxis={"title": "Percentage"},
        font={
            "size": 16,
        },
    )

    for idx, playlist in enumerate(figures.keys()):
        figure_combined["data"][idx]["name"] = playlist
        figure_combined["data"][idx]["showlegend"] = True

    # add vertical lines to display aim training hours as checkpoints
    for date_obj, checkpoint in aim_training_checkpoints.items():
        figure_combined.add_vline(
            x=date_obj.timestamp() * 1000,
            line_dash="dash",
            annotation_text=f" {checkpoint} hours",
        )

    return figure_combined
