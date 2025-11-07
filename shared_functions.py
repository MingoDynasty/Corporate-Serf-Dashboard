"""
Shared functions for the Corporate Serf app.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


logger = logging.getLogger(__name__)
scenario_data = {}


@dataclass(frozen=True)
class RunData:
    datetime_object: datetime
    score: float
    sens_scale: str
    horizontal_sens: float
    scenario: str


def get_unique_scenarios(_dir: str) -> list:
    """
    Gets the list of unique scenarios from a directory.
    :param _dir: directory to search for scenarios.
    :return: list of unique scenarios
    """
    unique_scenarios = set()
    files = [
        file for file in os.listdir(_dir) if os.path.isfile(os.path.join(_dir, file))
    ]
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
        splits = Path(full_file_path).stem.split(" Stats")[0].split(" - ")
        datetime_object = datetime.strptime(splits[-1], "%Y.%m.%d-%H.%M.%S")

        with open(full_file_path, "r", encoding="utf-8") as file:
            lines_list = file.readlines()  # Read all lines into a list

        for line in lines_list:
            if line.startswith("Score:"):
                score = float(line.split(",")[1].strip())
            elif line.startswith("Sens Scale:"):
                sens_scale = line.split(",")[1].strip()
            elif line.startswith("Horiz Sens:"):
                str_horizontal_sens = line.split(",")[1].strip()
                # sometimes the sens looks like 20.123456789, so round it to look cleaner
                horizontal_sens = round(float(str_horizontal_sens), 4)
            elif line.startswith("Scenario:"):
                scenario = line.split(",")[1].strip()
    except ValueError:
        logger.warning("Failed to parse file: %s", full_file_path, exc_info=True)
        return None

    if (
        not datetime_object
        or not score
        or not sens_scale
        or not horizontal_sens
        or not scenario
    ):
        logger.warning("Missing data from file: %s", full_file_path, exc_info=True)
        return None

    run_data = RunData(
        datetime_object=datetime_object,
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


def get_relevant_csv_files(
    stats_dir: str, scenario_name: str, within_n_days: int
) -> list:
    """
    Get relevant CSV files for a given scenario.
    :param stats_dir: directory where scenario CSV files are located.
    :param scenario_name: the name of a scenario to get CSV files for.
    :param within_n_days: file must be within n days to be interesting.
    :return: list of relevant CSV files.
    """
    files = [
        file
        for file in os.listdir(stats_dir)
        if os.path.isfile(os.path.join(stats_dir, file))
    ]
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


@dataclass()
class ScenarioStats:
    date_last_played: Optional[datetime]
    number_of_runs: int


def get_scenario_data(
    stats_dir: str, scenario: str, within_n_days: int
) -> Tuple[dict[str, list], ScenarioStats]:
    """
    Get all scenario data for a given scenario.
    :param stats_dir: directory where scenario CSV files are located.
    :param scenario: the name of a scenario to get data for.
    :param within_n_days: data must be within n days to be interesting.
    :return: dictionary of scenario data.
    """
    scenario_files = get_relevant_csv_files(stats_dir, scenario, within_n_days)
    scenario_data: dict[str, list] = {}
    scenario_stats = ScenarioStats(None, 0)
    for scenario_file in scenario_files:
        run_data = extract_data_from_file(str(Path(stats_dir, scenario_file)))
        if not run_data:
            logger.warning("Failed to get run data for CSV file: %s", scenario_file)
            continue

        key = f"{run_data.horizontal_sens} {run_data.sens_scale}"
        if key not in scenario_data:
            scenario_data[key] = []
        scenario_data[key].append(run_data)

        scenario_stats.number_of_runs += 1
        if (
            scenario_stats.date_last_played is None
            or run_data.datetime_object > scenario_stats.date_last_played
        ):
            scenario_stats.date_last_played = run_data.datetime_object

    # Sort by Sensitivity
    # Note that for example: "5.0 cm/360" should come before "25.0 cm/360"
    scenario_data = dict(
        sorted(scenario_data.items(), key=lambda item: float(item[0].split(" ")[0]))
    )
    return scenario_data, scenario_stats
