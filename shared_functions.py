"""
Shared functions for the Corporate Serf app.
"""
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go

console_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunData:
    datetime_object: datetime
    score: float
    sens_scale: str
    horizontal_sens: str
    scenario: str


def get_unique_scenarios(_dir: str) -> list:
    """
    Gets the list of unique scenarios from a directory.
    :param _dir: directory to search for scenarios.
    :return: list of unique scenarios
    """
    unique_scenarios = set()
    files = [file for file in os.listdir(_dir) if
             os.path.isfile(os.path.join(_dir, file))]
    csv_files = [file for file in files if file.endswith(".csv")]
    for file in csv_files:
        scenario_name = file.split("-")[0].strip()
        unique_scenarios.add(scenario_name)
    return sorted(list(unique_scenarios))


def extract_data_from_file(full_file_path: str) -> Optional[RunData]:
    """
    Extracts data from a scenario CSV file.
    :param full_file_path: full file path of the file to extract data from.
    :return: RunData object
    """
    score = None
    sens_scale = None
    horizontal_sens = None
    scenario = None

    try:
        splits = Path(full_file_path).stem.split(' Stats')[0].split(' - ')
        datetime_object = datetime.strptime(splits[-1], "%Y.%m.%d-%H.%M.%S")

        with open(full_file_path, 'r', encoding="utf-8") as file:
            lines_list = file.readlines()  # Read all lines into a list

        for line in lines_list:
            if line.startswith("Score:"):
                score = float(line.split(",")[1].strip())
            elif line.startswith("Sens Scale:"):
                sens_scale = line.split(",")[1].strip()
            elif line.startswith("Horiz Sens:"):
                horizontal_sens = line.split(",")[1].strip()
            elif line.startswith("Scenario:"):
                scenario = line.split(",")[1].strip()
    except ValueError:
        console_logger.warning("Failed to parse file: %s", full_file_path, exc_info=True)
        return None

    if not datetime_object or not score or not sens_scale or not horizontal_sens or not scenario:
        console_logger.warning("Missing data from file: %s", full_file_path, exc_info=True)
        return None

    run_data = RunData(datetime_object=datetime_object,
                       score=score,
                       sens_scale=sens_scale,
                       horizontal_sens=horizontal_sens,
                       scenario=scenario,
                       )
    return run_data


def is_file_of_interest(file: str, scenario_name: str, within_n_days: int) -> bool:
    """
    Check if a file is of interest. More specifically:
    1. The file is related to a scenario that we are monitoring (i.e. user has selected).
    2. The file is not too old, based on the date the user selected.
    :param file: full file path of the file to check.
    :param scenario_name: the name of the scenario to check.
    :param within_n_days: file must be within n days to be interesting.
    :return: True if the file is interesting, else False.
    """
    if not file.endswith(".csv"):
        return False

    filename = Path(file).stem
    if scenario_name != filename.split("-")[0].strip():
        return False

    # splits = filename.split(" ")
    splits = file.split(" - Challenge - ")
    datetime_string = splits[1].split(" ")[0]
    format_string = "%Y.%m.%d-%H.%M.%S"
    datetime_object = datetime.strptime(datetime_string, format_string)
    delta = datetime.today() - datetime_object
    if delta.days > within_n_days:
        return False

    return True


def get_relevant_csv_files(stats_dir: str, scenario_name: str, within_n_days: int) -> list:
    """
    Get relevant CSV files for a given scenario.
    :param stats_dir: directory where scenario CSV files are located.
    :param scenario_name: the name of a scenario to get CSV files for.
    :param within_n_days: file must be within n days to be interesting.
    :return: list of relevant CSV files.
    """
    files = [file for file in os.listdir(stats_dir) if
             os.path.isfile(os.path.join(stats_dir, file))]
    csv_files = [file for file in files if file.endswith(".csv")]
    scenario_files = []
    for file in csv_files:
        if scenario_name == file.split("-")[0].strip():
            scenario_files.append(file)

    # Get the subset of files that pertain to the scenario
    relevant_csv_files = []
    for scenario_file in scenario_files:
        splits = scenario_file.split(" - Challenge - ")
        datetime_string = splits[1].split(" ")[0]
        format_string = "%Y.%m.%d-%H.%M.%S"
        datetime_object = datetime.strptime(datetime_string, format_string)
        delta = datetime.today() - datetime_object
        if delta.days > within_n_days:
            continue
        relevant_csv_files.append(scenario_file)
    return relevant_csv_files


def get_scenario_data(stats_dir: str, scenario: str, within_n_days: int) -> dict:
    """
    Get all scenario data for a given scenario.
    :param stats_dir: directory where scenario CSV files are located.
    :param scenario: the name of a scenario to get data for.
    :param within_n_days: data must be within n days to be interesting.
    :return: dictionary of scenario data.
    """
    scenario_files = get_relevant_csv_files(stats_dir, scenario, within_n_days)
    scenario_data: dict[str, list] = {}
    for scenario_file in scenario_files:
        run_data = extract_data_from_file(
            str(Path(stats_dir, scenario_file)))
        if not run_data:
            console_logger.warning("Failed to get run data for CSV file: %s", scenario_file)
            continue
        # if sens_scale != 'cm/360':
        #     # TODO: sensitivities other than cm/360 are currently not supported,
        #     #  as I don't know how to convert them to cm/360.
        #     console_logger.warning("Unsupported sensitivity scale: %s", sens_scale)
        #     continue

        # key = run_data.horizontal_sens + " " + run_data.sens_scale
        # key = run_data.horizontal_sens
        key = f"{run_data.horizontal_sens} {run_data.sens_scale}"
        if key not in scenario_data:
            scenario_data[key] = []
        scenario_data[key].append(run_data)

    # Sort by Sensitivity
    scenario_data = dict(sorted(scenario_data.items()))
    return scenario_data


def generate_plot(scenario_data: dict, scenario_name: str, top_n_scores: int) -> go.Figure:
    """
    Generate a plot using the scenario data.
    :param scenario_data: the scenario data to use for the plot.
    :param scenario_name: the name of the scenario to use for the plot.
    :param top_n_scores: the number of top scores to use for the plot.
    :return: go.Figure Plot
    """
    if not scenario_data:
        return go.Figure()

    scatter_plot_data = {
        'Score': [],
        'Sensitivity': [],
        'Datetime': []
    }
    line_plot_data = {
        'Score': [],
        'Sensitivity': [],
    }

    for sens, runs_data in scenario_data.items():
        # Get top N scores for each sensitivity
        sorted_list = sorted(runs_data, key=lambda rd: rd.score, reverse=True)
        top_n_largest = sorted_list[:top_n_scores]
        for run_data in top_n_largest:
            scatter_plot_data['Score'].append(run_data.score)
            scatter_plot_data['Sensitivity'].append(f"{run_data.horizontal_sens} {run_data.sens_scale}")
            scatter_plot_data['Datetime'].append(run_data.datetime_object.strftime('%Y-%m-%d %I:%M:%S %p'))
        line_plot_data['Sensitivity'].append(sens)
        line_plot_data['Score'].append(np.mean([rd.score for rd in top_n_largest]))
    # If we want to generate a trendline (e.g. lowess)
    # if len(data.keys()) <= 2:
    #     # We need at least 3 sensitivities to generate a trendline
    #     console_logger.debug(f"WARNING: Skipping '{scenario}' due to insufficient Sensitivity data.")
    #     return

    current_datetime = datetime.today().strftime("%Y-%m-%d %I:%M:%S %p")
    title = f"{scenario_name} (updated: {str(current_datetime)})"
    console_logger.debug("Generating plot for: %s", scenario_name)

    figure_scatter = px.scatter(
        data_frame=pd.DataFrame(scatter_plot_data),
        x="Sensitivity",
        y="Score",
        hover_name="Datetime",
        hover_data=["Datetime"],
        custom_data=["Datetime"],
    )
    figure_scatter.update_traces(
        hovertemplate='<b>%{customdata[0]}</b><br><br>' +
                      '<b>Score</b>: %{y}<br>' +
                      '<b>Sensitivity</b>: %{x}' +
                      '<extra></extra>',
        hoverlabel={"font_size": 16},
    )

    # trendline="lowess"  # simply using average line for now
    figure_line = px.line(
        data_frame=pd.DataFrame(line_plot_data),
        x="Sensitivity",
        y="Score",
    )
    figure_line.update_traces(
        hovertemplate='<b>Average Score</b>: %{y}<br>' +
                      '<b>Sensitivity</b>: %{x}' +
                      '<extra></extra>',
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
    figure_combined['data'][0]['name'] = 'Run Data Point'
    figure_combined['data'][0]['showlegend'] = True
    figure_combined['data'][1]['name'] = 'Average Score'
    figure_combined['data'][1]['showlegend'] = True
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
