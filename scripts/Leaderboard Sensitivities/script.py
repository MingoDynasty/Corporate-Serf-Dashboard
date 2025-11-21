from dataclasses import dataclass
import logging
import sys

from kovaaks.api_models import BenchmarksAPIResponse
from kovaaks.api_service import get_benchmark_json, get_leaderboard_scores
from models import EvxlData
import numpy as np
import pandas as pd

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

EVXL_BENCHMARKS_JSON_FILE = "../../resources/evxl/benchmarks.json"


@dataclass()
class Stats:
    minimum: float
    q1: float
    median: float
    mean: float
    q3: float
    maximum: float


def load_evxl_data():
    """
    Load data from EVXL benchmarks JSON file.
    :return: Example: {"Viscose Benchmarks - Easier": 686}
    """
    benchmark_name_to_id = {}
    with open(EVXL_BENCHMARKS_JSON_FILE, encoding="utf-8") as file:
        json_data = file.read()
    evxl_data = EvxlData.model_validate_json(json_data)
    for evxl_benchmark in evxl_data.root:
        if evxl_benchmark.benchmarkName != "Viscose Benchmarks":
            continue
        for evxl_difficulty in evxl_benchmark.difficulties:
            if evxl_difficulty.difficultyName != "Easier":
                continue
            full_benchmark_name = (
                f"{evxl_benchmark.benchmarkName} - {evxl_difficulty.difficultyName}"
            )
            benchmark_name_to_id[full_benchmark_name] = (
                evxl_difficulty.kovaaksBenchmarkId
            )
    return benchmark_name_to_id


def calculate_stats(leaderboard_id: int) -> Stats:
    sensitivities = []
    response = get_leaderboard_scores(leaderboard_id)
    for ranking_player in response.data:
        if not ranking_player.attributes.cm360:
            logger.warning(
                f"Skipping empty cm360 for player: {ranking_player.steamAccountName}"
            )
            continue
        sensitivities.append(ranking_player.attributes.cm360)
    return Stats(
        minimum=min(sensitivities),
        q1=float(np.quantile(sensitivities, 0.25)),  # Calculate Q1 (25th percentile)
        median=float(np.median(sensitivities)),
        mean=float(np.mean(sensitivities)),
        q3=float(np.quantile(sensitivities, 0.75)),  # Calculate Q3 (75th percentile)
        maximum=max(sensitivities),
    )


def main() -> None:
    benchmark_names_to_id = load_evxl_data()

    benchmarks_to_scenario_name_and_leaderboard_id = dict.fromkeys(
        benchmark_names_to_id.keys(), {}
    )
    # logger.debug(benchmarks_to_scenario_name_and_leaderboard_id)

    # for each benchmark, call the benchmarks API to get the list of scenarios, and leaderboard ID per scenario
    for benchmark_name, benchmark_id in benchmark_names_to_id.items():
        logger.debug(f"benchmark_id={benchmark_id}, benchmark_name={benchmark_name}")
        response_json = get_benchmark_json(benchmark_id, None)
        benchmark_response = BenchmarksAPIResponse.model_validate(response_json)
        for _, category in benchmark_response.categories.items():
            for scenario_name, benchmark_scenario in category.scenarios.items():
                benchmarks_to_scenario_name_and_leaderboard_id[benchmark_name][
                    scenario_name
                ] = benchmark_scenario.leaderboard_id
        # break  # TODO: debug only

    # Build a dictionary to be later converted to Pandas dataframe
    data = {
        "Scenario Name": [],
        "Minimum": [],
        "Q1": [],
        "Median": [],
        "Mean": [],
        "Q3": [],
        "Maximum": [],
    }
    for (
        benchmark_name,
        scenario_data,
    ) in benchmarks_to_scenario_name_and_leaderboard_id.items():
        logger.debug("benchmark_name: %s", benchmark_name)
        for scenario_name, leaderboard_id in scenario_data.items():
            logger.debug(
                "leaderboard_id: %s, scenario_name: %s", leaderboard_id, scenario_name
            )
            stats = calculate_stats(leaderboard_id)
            logger.debug(f"{scenario_name} : {stats}")

            data["Scenario Name"].append(scenario_name)
            data["Minimum"].append(stats.minimum)
            data["Q1"].append(stats.q1)
            data["Median"].append(stats.median)
            data["Mean"].append(stats.mean)
            data["Q3"].append(stats.q3)
            data["Maximum"].append(stats.maximum)
        #     break
        # break

    df = pd.DataFrame(data)
    df.to_csv("my_data_pandas.csv", index=False)


if __name__ == "__main__":
    main()
