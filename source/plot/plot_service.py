"""
This module handles functions around plots.
"""

from datetime import datetime
import logging

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go

from source.kovaaks.data_models import Rank, RunData
from source.utilities.utilities import format_decimal

logger = logging.getLogger(__name__)


def generate_plot(
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
    if not scenario_data:
        return go.Figure()

    scatter_plot_data: dict[str, list[float | str]] = {
        "Score": [],
        "Sensitivity": [],
        "Datetime": [],
        "Accuracy": [],
    }
    line_plot_data: dict[str, list[float | str]] = {
        "Score": [],
        "Sensitivity": [],
    }

    for sens, runs_data in scenario_data.items():
        for run_data in runs_data:
            scatter_plot_data["Score"].append(run_data.score)
            scatter_plot_data["Sensitivity"].append(
                f"{run_data.horizontal_sens} {run_data.sens_scale}",
            )
            scatter_plot_data["Datetime"].append(
                run_data.datetime_object.strftime("%Y-%m-%d %I:%M:%S %p"),
            )
            scatter_plot_data["Accuracy"].append(round(100 * run_data.accuracy, 2))
        line_plot_data["Sensitivity"].append(sens)
        line_plot_data["Score"].append(float(np.mean([rd.score for rd in runs_data])))
    # If we want to generate a trendline (e.g. lowess)
    # if len(data.keys()) <= 2:
    #     # We need at least 3 sensitivities to generate a trendline
    #     logger.debug(f"WARNING: Skipping '{scenario}' due to insufficient Sensitivity data.")
    #     return

    current_datetime = datetime.today().strftime("%Y-%m-%d %I:%M:%S %p")
    title = f"{scenario_name} (updated: {current_datetime!s})"
    logger.debug("Generating plot for: %s", scenario_name)

    figure_scatter = px.scatter(
        data_frame=pd.DataFrame(scatter_plot_data),
        x="Sensitivity",
        y="Score",
        hover_name="Datetime",
        hover_data=["Datetime"],
        custom_data=["Datetime", "Accuracy"],
    )
    figure_scatter.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br><br>"
        + "<b>Score</b>: %{y}<br>"
        + "<b>Sensitivity</b>: %{x}<br>"
        + "<b>Accuracy</b>: %{customdata[1]}%"
        + "<extra></extra>",
        hoverlabel={"font_size": 16},
    )

    # trendline="lowess"  # simply using average line for now
    figure_line = px.line(
        data_frame=pd.DataFrame(line_plot_data),
        x="Sensitivity",
        y="Score",
    )
    figure_line.update_traces(
        hovertemplate="<b>Average Score</b>: %{y}<br>"
        + "<b>Sensitivity</b>: %{x}"
        + "<extra></extra>",
        hoverlabel={"font_size": 16},
    )

    figure_combined = go.Figure(data=figure_scatter.data + figure_line.data)
    figure_combined.update_layout(
        title=title,
        xaxis={"title": "Sensitivity"},
        yaxis={"title": "Score"},
        font={
            "size": 14,
        },
    )
    figure_combined["data"][0]["name"] = "Run Data Point"
    figure_combined["data"][0]["showlegend"] = True
    figure_combined["data"][1]["name"] = "Average Score"
    figure_combined["data"][1]["showlegend"] = True

    if rank_overlay_switch and rank_data:
        # Get the highest rank that is still below our lowest score
        idx_lowest_rank = 0
        for idx in range(1, len(rank_data)):
            if rank_data[idx].threshold >= float(min(scatter_plot_data["Score"])):
                break
            idx_lowest_rank = idx

        # Get the lowest rank that is still above our highest score
        idx_highest_rank = len(rank_data) - 1
        for idx in range(len(rank_data) - 2, -1, -1):
            if rank_data[idx].threshold <= float(max(scatter_plot_data["Score"])):
                break
            idx_highest_rank = idx

        # Show the ranks between "highest rank below min_score" and "lowest rank above max_score"
        for rank in rank_data[idx_lowest_rank : idx_highest_rank + 1]:
            figure_combined.add_hline(
                name=rank.name,
                label={
                    "text": f"{rank.name} ({format_decimal(rank.threshold)}) ",
                    "textposition": "end",
                },
                y=rank.threshold,
                line_dash="dash",
                line_color=rank.color,
            )

        # ensure slight padding in the highest rank displayed, so that the label text doesn't get cut off
        figure_combined.update_yaxes(
            autorangeoptions={"include": rank_data[idx_highest_rank].threshold * 1.02},
        )
    return figure_combined


def apply_light_dark_mode(figure: go.Figure, dark_mode_switch) -> go.Figure:
    """
    Apply light or dark mode to figure.
    :param figure: figure to lighten or darken.
    :param dark_mode_switch: True=Dark mode, False=Light mode.
    :return: figure with template applied.
    """
    template = "mantine_dark" if dark_mode_switch else "mantine_light"
    figure.update_layout(template=template)
    return figure


def generate_aim_training_journey_plot(
    journey_data: dict[str, dict[datetime, float]],
    aim_training_checkpoints: dict[datetime, int],
) -> go.Figure:
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
