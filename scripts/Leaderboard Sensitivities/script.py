from dataclasses import dataclass
import logging
import sys

from kovaaks.api_models import BenchmarksAPIResponse
from kovaaks.api_service import get_benchmark_json, get_leaderboard_scores
from models import EvxlData
import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

EVXL_BENCHMARKS_JSON_FILE = "../../resources/evxl/benchmarks.json"

TARGET_BENCHMARK = "Viscose Benchmarks"
TARGET_DIFFICULTY = "Hard"


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
        if evxl_benchmark.benchmarkName != TARGET_BENCHMARK:
            continue
        for evxl_difficulty in evxl_benchmark.difficulties:
            if evxl_difficulty.difficultyName != TARGET_DIFFICULTY:
                continue
            full_benchmark_name = (
                f"{evxl_benchmark.benchmarkName} - {evxl_difficulty.difficultyName}"
            )
            benchmark_name_to_id[full_benchmark_name] = (
                evxl_difficulty.kovaaksBenchmarkId
            )
    return benchmark_name_to_id


def get_sens_list(leaderboard_id: int) -> list[float]:
    sensitivities = []
    response = get_leaderboard_scores(leaderboard_id, use_cache=True)
    for ranking_player in response.data:
        if not ranking_player.attributes.cm360:
            logger.debug(
                f"Skipping empty cm360 for player: {ranking_player.steamAccountName}"
            )
            continue
        sensitivities.append(ranking_player.attributes.cm360)
    return sensitivities


def filter_with_iqr(sensitivities: list[float]) -> list[float]:
    # exclude outliers that are below (Q1 - 1.5 * IQR) and above (Q3 + 1.5 * IQR)
    data = np.array(sensitivities)
    q1 = np.percentile(data, 25)
    q3 = np.percentile(data, 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    return data[(data >= lower_bound) & (data <= upper_bound)]


def filter_with_zscore(sensitivities: list[float], threshold: int = 3) -> list[float]:
    # exclude outliers that are 3 or more standard deviations away
    data = np.array(sensitivities)
    z_scores = np.abs(stats.zscore(data))
    return data[z_scores < threshold]


def get_stats(data: list[float]) -> Stats:
    return Stats(
        minimum=min(data),
        q1=float(np.quantile(data, 0.25)),  # Calculate Q1 (25th percentile)
        median=float(np.median(data)),
        mean=float(np.mean(data)),
        q3=float(np.quantile(data, 0.75)),  # Calculate Q3 (75th percentile)
        maximum=max(data),
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
        response_json = get_benchmark_json(benchmark_id, steam_id=None, use_cache=True)
        benchmark_response = BenchmarksAPIResponse.model_validate(response_json)
        for _, category in benchmark_response.categories.items():
            for scenario_name, benchmark_scenario in category.scenarios.items():
                benchmarks_to_scenario_name_and_leaderboard_id[benchmark_name][
                    scenario_name
                ] = benchmark_scenario.leaderboard_id
        #     break  # TODO: debug only
        # break  # TODO: debug only

    # Build a dictionary to be later converted to Pandas dataframe
    keys = [
        "Scenario Name",
        "Minimum",
        "Q1",
        "Median",
        "Mean",
        "Q3",
        "Maximum",
        "Number of Sensitivities",
    ]
    data_iqr = {key: [] for key in keys}
    data_zscore = {key: [] for key in keys}
    for (
        benchmark_name,
        scenario_data,
    ) in benchmarks_to_scenario_name_and_leaderboard_id.items():
        logger.debug("benchmark_name: %s", benchmark_name)
        for scenario_name, leaderboard_id in scenario_data.items():
            logger.debug(
                "leaderboard_id: %s, scenario_name: %s", leaderboard_id, scenario_name
            )
            sensitivities = get_sens_list(leaderboard_id)
            # logger.info("Original sens: %s", sensitivities)

            sensitivities_iqr_filtered = filter_with_iqr(sensitivities)
            stats_iqr = get_stats(sensitivities_iqr_filtered)
            logger.debug(f"{scenario_name} : {stats_iqr}")
            data_iqr["Scenario Name"].append(scenario_name)
            data_iqr["Minimum"].append(stats_iqr.minimum)
            data_iqr["Q1"].append(stats_iqr.q1)
            data_iqr["Median"].append(stats_iqr.median)
            data_iqr["Mean"].append(stats_iqr.mean)
            data_iqr["Q3"].append(stats_iqr.q3)
            data_iqr["Maximum"].append(stats_iqr.maximum)
            data_iqr["Number of Sensitivities"].append(len(sensitivities))

            sensitivities_zscore_filtered = filter_with_zscore(sensitivities)
            # logger.info("Filtered sens: %s", sensitivities_zscore_filtered)
            stats_zscore = get_stats(sensitivities_zscore_filtered)
            # logger.debug(f"{scenario_name} : {stats_iqr}")
            data_zscore["Scenario Name"].append(scenario_name)
            data_zscore["Minimum"].append(stats_zscore.minimum)
            data_zscore["Q1"].append(stats_zscore.q1)
            data_zscore["Median"].append(stats_zscore.median)
            data_zscore["Mean"].append(stats_zscore.mean)
            data_zscore["Q3"].append(stats_zscore.q3)
            data_zscore["Maximum"].append(stats_zscore.maximum)
            data_zscore["Number of Sensitivities"].append(len(sensitivities))
        #     break  # TODO: debug only
        # break  # TODO: debug only

    df_iqr = pd.DataFrame(data_iqr)
    df_iqr.to_csv(f"pandas_df_iqr_{TARGET_DIFFICULTY}.csv", index=False)

    df_zscore = pd.DataFrame(data_zscore)
    df_zscore.to_csv(f"pandas_df_zscore_{TARGET_DIFFICULTY}.csv", index=False)


if __name__ == "__main__":
    main()
