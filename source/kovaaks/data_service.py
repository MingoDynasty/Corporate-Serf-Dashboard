"""
Provides business logic for managing Kovaaks data.
"""

from datetime import datetime
import logging
import os
from pathlib import Path

from pydantic import ValidationError
from sortedcontainers import SortedDict, SortedList

from source.config.config_service import config
from source.kovaaks.api_service import get_playlist_data
from source.kovaaks.data_models import (
    PlaylistData,
    Rank,
    RunData,
    Scenario,
    ScenarioStats,
)
from source.utilities.stopwatch import Stopwatch

PLAYLIST_DIRECTORY = "resources/playlists"
SUB_CSV_HEADER = "Weapon,Shots,Hits,Damage Done,Damage Possible,,Sens Scale,Horiz Sens,Vert Sens,FOV,Hide Gun,Crosshair,Crosshair Scale,Crosshair Color,ADS Sens,ADS Zoom Scale,Avg Target Scale,Avg Time Dilation"  # pylint: disable=line-too-long
logger = logging.getLogger(__name__)

# TODO: maybe at some point convert this to in-memory SQLite
#  But a simple dictionary should suffice for now.
kovaaks_database: dict = {}

playlist_database: dict[str, list[Scenario]] = {}


def is_scenario_in_database(scenario_name: str) -> bool:
    """Check if a scenario is in the database."""
    return scenario_name in kovaaks_database


def get_scenario_stats(scenario_name: str) -> ScenarioStats:
    """Get scenario statistics for a scenario."""
    return kovaaks_database[scenario_name]["scenario_stats"]


def get_sensitivities_vs_runs(scenario_name: str) -> dict[str, list[RunData]]:
    """Get sensitivities vs runs for a scenario."""
    return kovaaks_database[scenario_name]["sensitivities_vs_runs"]


def get_sensitivities_vs_runs_filtered(
    scenario_name: str, top_n_scores: int, oldest_date: datetime
) -> dict[str, list[RunData]]:
    """
    Get sensitivities vs runs for a scenario, filtered by top N scores, and oldest date.
    :param scenario_name: the name of the scenario to filter by.
    :param top_n_scores: the number of top scores to filter by.
    :param oldest_date: oldest date to filter by (inclusive).
    """
    # TODO: dictionary comprehension is technically Pythonic, but I'm too lazy to figure out the optimal syntax.
    #  Besides, this logic might get blown away if/when we migrate to SQLite.
    filtered_data = {}
    for key, runs_data in kovaaks_database[scenario_name][
        "sensitivities_vs_runs"
    ].items():
        filtered_data[key] = []

        # RunData list is already sorted by score, so we can simply iterate backwards.
        for run_data in reversed(runs_data):
            if run_data.datetime_object < oldest_date:
                continue
            filtered_data[key].append(run_data)
            if len(filtered_data[key]) >= top_n_scores:
                break

        # avoid issues with empty arrays in the dictionary
        if not filtered_data[key]:
            del filtered_data[key]
    return filtered_data


def get_playlists() -> list[str]:
    """Get list of available playlists."""
    return sorted(list(playlist_database.keys()))


def get_scenarios_from_playlists(playlist_name: str) -> list[str]:
    """Get scenarios from a playlist."""
    return [item.name for item in playlist_database[playlist_name]]


def get_rank_data_from_playlist(playlist_name: str, scenario_name: str) -> list[Rank]:
    if playlist_name not in playlist_database:
        logger.warning(
            "Failed to get rank data for playlist (%s), scenario (%s)",
            playlist_name,
            scenario_name,
        )
        return []
    scenarios = playlist_database[playlist_name]
    for scenario in scenarios:
        if scenario.name != scenario_name:
            continue
        return scenario.ranks
    logger.warning(
        "Failed to get rank data for playlist (%s), scenario (%s)",
        playlist_name,
        scenario_name,
    )
    return []


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

    for csv_file in csv_files:
        load_csv_file_into_database(csv_file)
    stopwatch.stop()
    logger.debug(
        "Loaded %d CSV files in %.2f seconds.",
        len(csv_files),
        round(stopwatch.elapsed(), 2),
    )


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


# TODO: simply pull this from the database instead of rescanning files again.
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


def extract_data_from_file(full_file_path: str) -> RunData | None:
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

        with open(full_file_path, encoding="utf-8") as file:
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
                horizontal_sens = round(
                    float(str_horizontal_sens), config.sens_round_decimal_places
                )
            elif line.startswith("Scenario:"):
                scenario = line.split(",")[1].strip()
    except ValueError:
        logger.warning("Failed to parse file: %s", full_file_path, exc_info=True)
        return None

    if (
        datetime_object is None
        or accuracy is None
        or horizontal_sens is None
        or scenario is None
        or score is None
        or sens_scale is None
    ):
        logger.warning("Missing data from file: %s", full_file_path)
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


def load_playlists() -> None:
    playlist_files = []
    with os.scandir(PLAYLIST_DIRECTORY) as entries:
        for entry in entries:
            if entry.is_file() and entry.name.endswith(".json"):
                playlist_files.append(entry.path)
    for playlist_file in playlist_files:
        try:
            with open(playlist_file, encoding="utf-8") as file:
                json_data = file.read()
            playlist_data = PlaylistData.model_validate_json(json_data)

            if playlist_data.name in playlist_database:
                logger.warning(
                    "Playlist already exists in database: %s",
                    playlist_data.name,
                )
                continue
            playlist_database[playlist_data.name] = playlist_data.scenarios
        except ValidationError:
            logger.warning("Invalid JSON format in playlist file: %s", playlist_file)


def load_playlist_from_code(input_playlist_code: str) -> str | None:
    response = get_playlist_data(input_playlist_code)
    if not response or not response.data:
        message = (
            f"Failed to load playlist data for playlist code: {input_playlist_code}"
        )
        logger.warning(message)
        return message

    if len(response.data) > 1:
        message = f"Found more than one playlist from code: {input_playlist_code}"
        logger.warning(message)
        return message

    playlist_data = PlaylistData(
        name=response.data[0].playlistName,
        code=response.data[0].playlistCode,
        scenarios=[
            Scenario(name=item.scenarioName) for item in response.data[0].scenarioList
        ],
    )

    if playlist_data.name in playlist_database:
        message = f"Playlist already exists in database: {playlist_data.name}"
        logger.warning(message)
        return message
    write_playlist_data_to_file(playlist_data)
    playlist_database[playlist_data.name] = playlist_data.scenarios
    return None


def write_playlist_data_to_file(playlist_data: PlaylistData) -> None:
    file_path = Path(PLAYLIST_DIRECTORY, playlist_data.name + ".json")
    with open(file_path, "w", encoding="utf-8") as file:
        json_string = playlist_data.model_dump_json(indent=2, exclude_none=True)
        file.write(json_string)


load_playlists()
