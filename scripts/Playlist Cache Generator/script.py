import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

from kovaaks.api_models import BenchmarksAPIResponse
from kovaaks.api_service import get_benchmark_json, get_playlist_data
from kovaaks.data_models import PlaylistData, Scenario, Rank
from models import EvxlData, EvxlDatabaseItem

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

EVXL_BENCHMARKS_JSON_FILE = "../../resources/evxl/benchmarks.json"


def load_evxl_data() -> Dict[str, EvxlDatabaseItem]:
    evxl_database = {}
    with open(EVXL_BENCHMARKS_JSON_FILE, "r", encoding="utf-8") as file:
        json_data = file.read()
    evxl_data = EvxlData.model_validate_json(json_data)
    for evxl_benchmark in evxl_data.root:
        for evxl_difficulty in evxl_benchmark.difficulties:
            if evxl_difficulty.sharecode in evxl_database:
                logger.warning(
                    "Sharecode already exists in database: %s",
                    evxl_difficulty.sharecode,
                )
                continue
            evxl_database[evxl_difficulty.sharecode] = EvxlDatabaseItem(
                kovaaksBenchmarkId=evxl_difficulty.kovaaksBenchmarkId,
                rankColors=evxl_difficulty.rankColors,
            )
    return evxl_database


def main() -> None:
    # 1. Read Evxl `benchmarks.json` file
    evxl_database = load_evxl_data()
    logger.info(f"Found {len(evxl_database)} evxl benchmarks.")
    counter = 0

    temp_skip_sharecodes = [
        "KovaaKsCarryingSlowGauntlet",  # "data": []
        "KovaaKsChallengingSmallClass",  # "data": []
        "KovaaKsHeadshottingAquamarineCapture",  # "data": []
        "KovaaKsReloadingCaffeinatedStrike",  # "data": []
        "KovaaKsAfkingSalmonNuns",  # "data": [null]
        "KovaaKsAdventuringRoyalpurpleWindow",  # "data": [null]
        "KovaaKsAdsingRoyalpurpleChat",  # "data": [null]
        "KovaaKsTeleportingGoatedBlueberry",  # "data": [null]
        "KovaaKsTrackingEasyBattlepass",  # "data": [null]
        "KovaaKsDroppingMahoganyChallenge",  # "data": [null]
        "KovaaKsCarryingCloseMomentum",  # "data": [null]
        "KovaaKsGriefingFlawlessGoat",  # "data": [null]
        "KovaaKsPlunderingGreenGunsmith",  # "data": [null]
        "KovaaKsSensing360Button",  # "data": [null]
        "KovaaKsEntryfraggingBuggedLowground",  # "data": [null]
        "KovaaKsMainingForestgreenCallout",  # "data": [null]
    ]

    for sharecode, evxl_database_item in evxl_database.items():
        counter += 1

        if counter < 124:
            continue

        if sharecode in temp_skip_sharecodes:
            logger.debug(f"Skipping: {sharecode}")
            continue

        logger.debug(
            f"Generating cache ({counter}/{len(evxl_database)}) for sharecode: {sharecode}"
        )

        # 2. Query KovaaK's API for playlist data
        playlist_response = get_playlist_data(sharecode)
        playlist = None
        for _playlist in playlist_response.data:
            if _playlist.playlistCode.lower() != sharecode.lower():
                continue
            playlist = _playlist
        if not playlist:
            message = f"Failed to find playlist from code: {sharecode}"
            logger.warning(message)
            # raise Exception(message)
            continue
        logger.debug(
            f"Generating cache ({counter}/{len(evxl_database)}) for playlist: {playlist_response.data[0].playlistName.strip()}"
        )
        # if len(playlist_response.data) > 1:
        #     message = f"Found more than one playlist from code: {sharecode}"
        #     logger.warning(message)
        #     continue

        ################################
        # TODO: debugging only
        # playlist_filename = "playlist_" + expected_file
        # with open(playlist_filename, "w") as file_handle:
        #     file_handle.write(json.dumps(playlist_response_json, indent=4))
        # with open(playlist_filename, "r") as file_handle:
        #     response_json = json.load(file_handle)
        # playlist_response = PlaylistAPIResponse.model_validate(response_json)
        ################################

        # 3. Query KovaaK's API for benchmarks data
        response_json = get_benchmark_json(evxl_database_item.kovaaksBenchmarkId, None)
        ################################
        # TODO: debugging only
        # benchmark_filename = "benchmark_" + expected_file
        # with open(benchmark_filename, "w") as file_handle:
        #     file_handle.write(json.dumps(response_json, indent=4))
        # with open(benchmark_filename, "r") as file_handle:
        #     response_json = json.load(file_handle)
        ################################
        benchmark_response = BenchmarksAPIResponse.model_validate(response_json)

        # 4. Merge all this data and store into `resources/playlists/cache`
        evxl_rank_data = list(evxl_database_item.rankColors.items())
        scenario_list: List[Scenario] = []
        for _, category in benchmark_response.categories.items():
            for scenario_name, benchmark_scenario in category.scenarios.items():
                if len(benchmark_scenario.rank_maxes) != len(evxl_rank_data):
                    message = (
                        f"Mismatch of rank lengths! Evxl has {len(evxl_rank_data)}, "
                        f"whereas KovaaK's Benchmark API has {len(benchmark_scenario.rank_maxes)}"
                    )
                    logger.error(message)
                    raise Exception(message)

                ranks_data = []
                for idx in range(len(benchmark_scenario.rank_maxes)):
                    ranks_data.append(
                        Rank(
                            rank_name=evxl_rank_data[idx][0],
                            rank_color=evxl_rank_data[idx][1],
                            rank_threshold=benchmark_scenario.rank_maxes[idx],
                        )
                    )
                scenario_list.append(
                    Scenario(
                        scenario_name=scenario_name,
                        rank_data=ranks_data,
                    )
                )

        playlist_data = PlaylistData(
            playlist_name=playlist_response.data[0].playlistName.strip(),
            playlist_code=sharecode,
            scenario_list=scenario_list,
        )

        # Save to file
        os.makedirs("cache", exist_ok=True)  # create the cache directory if not exist
        cache_filename = Path("cache", playlist_data.playlist_name + ".json")
        with open(cache_filename, "w") as file_handle:
            file_handle.write(playlist_data.model_dump_json(indent=2))
    return


if __name__ == "__main__":
    main()
