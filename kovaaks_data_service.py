"""
Provides business logic for managing Kovaaks data.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

from sortedcontainers import SortedDict, SortedList

from stopwatch import Stopwatch

SUB_CSV_HEADER = "Weapon,Shots,Hits,Damage Done,Damage Possible,,Sens Scale,Horiz Sens,Vert Sens,FOV,Hide Gun,Crosshair,Crosshair Scale,Crosshair Color,ADS Sens,ADS Zoom Scale,Avg Target Scale,Avg Time Dilation"  # pylint: disable=line-too-long
logger = logging.getLogger(__name__)

# TODO: maybe at some point convert this to in-memory SQLite
#  But a simple dictionary should suffice for now.
kovaaks_database: Dict = {}


@dataclass(frozen=True)
class RunData:
    """Dataclass models data extracted from a Kovaak's run file."""

    datetime_object: datetime
    score: float
    sens_scale: str
    horizontal_sens: float
    scenario: str
    accuracy: float


@dataclass()
class ScenarioStats:
    """Dataclass models statistics for a scenario."""

    date_last_played: datetime
    number_of_runs: int


def is_scenario_in_database(scenario_name: str) -> bool:
    """Check if a scenario is in the database."""
    return scenario_name in kovaaks_database


def get_scenario_stats(scenario_name: str) -> ScenarioStats:
    """Get scenario statistics for a scenario."""
    return kovaaks_database[scenario_name]["scenario_stats"]


def get_sensitivities_vs_runs(scenario_name: str) -> Dict[str, List[RunData]]:
    """Get sensitivities vs runs for a scenario."""
    return kovaaks_database[scenario_name]["sensitivities_vs_runs"]


def initialize_kovaaks_data(stats_dir: str) -> None:
    """
    Initialize the Kovaaks database.
    :param stats_dir: stats directory to read data from.
    :return: None.
    """
    stopwatch = Stopwatch()
    stopwatch.start()
    csv_files = []
    with os.scandir(stats_dir) as entries:
        for entry in entries:
            if entry.is_file() and entry.name.endswith(".csv"):
                csv_files.append(entry.path)

    logger.debug("Found %d csv files.", len(csv_files))
    for csv_file in csv_files:
        load_csv_file_into_database(csv_file)
    stopwatch.stop()
    return


def load_csv_file_into_database(csv_file: str) -> None:
    """
    Loads a CSV file into the database.
    :param csv_file: CSV to load.
    :return: None.
    """
    run_data = extract_data_from_file(csv_file)
    if not run_data:
        logger.warning("Failed to get run data for CSV file: %s", csv_file)
        return
    # print(run_data)

    sensitivity_key = f"{run_data.horizontal_sens} {run_data.sens_scale}"
    if run_data.scenario not in kovaaks_database:
        kovaaks_database[run_data.scenario] = {
            "scenario_stats": ScenarioStats(
                date_last_played=run_data.datetime_object, number_of_runs=1
            ),
            # "raw_run_data": [run_data],
            "sensitivities_vs_runs": SortedDict(
                lambda item: float(item.split(" ")[0]),
                {
                    sensitivity_key: SortedList(
                        [run_data],
                        key=lambda item: item.score,
                    ),
                },
            ),
        }
    else:
        # Update scenario stats
        scenario_stats = kovaaks_database[run_data.scenario]["scenario_stats"]
        scenario_stats.number_of_runs += 1
        scenario_stats.date_last_played = max(
            scenario_stats.date_last_played, run_data.datetime_object
        )

        # Add to sensitivities_vs_runs
        sens_vs_runs = kovaaks_database[run_data.scenario]["sensitivities_vs_runs"]
        if sensitivity_key not in sens_vs_runs:
            sens_vs_runs[sensitivity_key] = SortedList(
                key=lambda item: item.score,
            )
        sens_vs_runs[sensitivity_key].add(run_data)
    return


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
    accuracy = None
    horizontal_sens = None
    scenario = None
    score = None
    sens_scale = None

    try:
        splits = Path(full_file_path).stem.split(" Stats")[0].split(" - ")
        datetime_object = datetime.strptime(splits[-1], "%Y.%m.%d-%H.%M.%S")

        with open(full_file_path, "r", encoding="utf-8") as file:
            lines_list = file.readlines()  # Read all lines into a list

        sub_csv_line = False
        for line in lines_list:
            line = line.strip()
            # If we encounter this specific line, then the next line is a specific CSV line
            if line == SUB_CSV_HEADER:
                sub_csv_line = True
                continue
            if sub_csv_line:
                shots = int(line.split(",")[1].strip())
                hits = int(line.split(",")[2].strip())
                accuracy = hits / shots
                sub_csv_line = False
                continue

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
        or not accuracy
        or not horizontal_sens
        or not scenario
        or not score
        or not sens_scale
    ):
        logger.warning("Missing data from file: %s", full_file_path, exc_info=True)
        return None

    run_data = RunData(
        datetime_object=datetime_object,
        score=score,
        sens_scale=sens_scale,
        horizontal_sens=horizontal_sens,
        scenario=scenario,
        accuracy=accuracy,
    )
    return run_data
