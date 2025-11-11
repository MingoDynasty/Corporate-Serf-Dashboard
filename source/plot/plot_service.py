"""
This module handles functions around plots.
"""

import logging
from datetime import datetime
from typing import Dict, List, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go

logger = logging.getLogger(__name__)


def generate_plot(
    scenario_data: dict, scenario_name: str, top_n_scores: int, oldest_date: datetime
) -> go.Figure:
    """
    Generate a plot using the scenario data.
    :param scenario_data: the scenario data to use for the plot.
    :param scenario_name: the name of the scenario to use for the plot.
    :param top_n_scores: the number of top scores to use for the plot.
    :param oldest_date: date to filter by.
    :return: go.Figure Plot
    """
    if not scenario_data:
        return go.Figure()

    scatter_plot_data: Dict[str, List[Union[float, str]]] = {
        "Score": [],
        "Sensitivity": [],
        "Datetime": [],
        "Accuracy": [],
    }
    line_plot_data: Dict[str, List[Union[float, str]]] = {
        "Score": [],
        "Sensitivity": [],
    }

    # TODO: move this to data service. Plot Service should only be concerned with receiving a dict of data and plotting it.
    for sens, runs_data in scenario_data.items():
        filtered_runs = [
            item for item in runs_data if item.datetime_object >= oldest_date
        ]
        if not filtered_runs:
            continue

        # Get top N scores for each sensitivity
        sorted_list = sorted(filtered_runs, key=lambda rd: rd.score, reverse=True)
        top_n_largest = sorted_list[:top_n_scores]
        for run_data in top_n_largest:
            scatter_plot_data["Score"].append(run_data.score)
            scatter_plot_data["Sensitivity"].append(
                f"{run_data.horizontal_sens} {run_data.sens_scale}"
            )
            scatter_plot_data["Datetime"].append(
                run_data.datetime_object.strftime("%Y-%m-%d %I:%M:%S %p")
            )
            scatter_plot_data["Accuracy"].append(round(100 * run_data.accuracy, 2))
        line_plot_data["Sensitivity"].append(sens)
        line_plot_data["Score"].append(
            float(np.mean([rd.score for rd in top_n_largest]))
        )
    # If we want to generate a trendline (e.g. lowess)
    # if len(data.keys()) <= 2:
    #     # We need at least 3 sensitivities to generate a trendline
    #     logger.debug(f"WARNING: Skipping '{scenario}' due to insufficient Sensitivity data.")
    #     return

    current_datetime = datetime.today().strftime("%Y-%m-%d %I:%M:%S %p")
    title = f"{scenario_name} (updated: {str(current_datetime)})"
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
    return figure_combined


def apply_light_dark_mode(figure: go.Figure, switch_on) -> go.Figure:
    """
    Apply light or dark mode to figure.
    :param figure: figure to lighten or darken.
    :param switch_on: True=Dark mode, False=Light mode.
    :return: figure with template applied.
    """
    template = "mantine_dark" if switch_on else "mantine_light"
    figure.update_layout(template=template)
    return figure
