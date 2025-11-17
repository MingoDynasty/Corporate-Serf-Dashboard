"""
Business logic for monitoring a specified directory for newly created files.
"""

import datetime
import logging
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler

from source.config.config_service import config
from source.kovaaks.data_service import (
    extract_data_from_file,
    get_sensitivities_vs_runs,
    is_scenario_in_database,
    load_csv_file_into_database,
)
from source.my_queue.message_queue import NewFileMessage, message_queue

logger = logging.getLogger(__name__)


class NewFileHandler(FileSystemEventHandler):
    """
    This class handles monitoring a specified directory for newly created files.
    """

    def on_created(self, event):
        if event.is_directory:  # Check if it's a file, not a directory
            return
        logger.debug("Detected new file: %s", event.src_path)
        # Add your custom logic here to process the new file
        # For example, you could read its content, move it, or trigger another function.
        file = event.src_path
        if not file.endswith(".csv"):
            return

        time.sleep(1)  # Wait a second to avoid permission issues with race condition
        run_data = extract_data_from_file(str(Path(config.stats_dir, file)))
        if not run_data:
            logger.warning("Failed to get run data for CSV file: %s", file)
            return

        sensitivity_key = f"{run_data.horizontal_sens} {run_data.sens_scale}"

        # Case 1: new scenario.
        if not is_scenario_in_database(run_data.scenario):
            logger.debug("Found new scenario: %s", run_data.scenario)
            message_queue.put(
                NewFileMessage(
                    datetime_created=datetime.datetime.now(),
                    nth_score=1,
                    scenario_name=run_data.scenario,
                    score=run_data.score,
                    sensitivity=sensitivity_key,
                )
            )
            load_csv_file_into_database(file)
            return

        # Case 2: new sensitivity.
        sensitivities_vs_runs = get_sensitivities_vs_runs(run_data.scenario)
        if sensitivity_key not in sensitivities_vs_runs:
            logger.debug("Found new sensitivity: %s", sensitivity_key)
            message_queue.put(
                NewFileMessage(
                    datetime_created=datetime.datetime.now(),
                    nth_score=1,
                    scenario_name=run_data.scenario,
                    score=run_data.score,
                    sensitivity=sensitivity_key,
                )
            )
            load_csv_file_into_database(file)
            return

        # Case 3: existing scenario and existing sensitivity, find nth score.
        nth_score = 1
        # TODO: O(n) linear search, should do O(log(n)) binary search instead
        for prev_run_data in sensitivities_vs_runs[sensitivity_key]:
            if prev_run_data.score > run_data.score:
                nth_score += 1
        logger.debug("Nth score: %s", nth_score)
        message_queue.put(
            NewFileMessage(
                datetime_created=datetime.datetime.now(),
                nth_score=nth_score,
                scenario_name=run_data.scenario,
                score=run_data.score,
                sensitivity=sensitivity_key,
            )
        )
        load_csv_file_into_database(file)
        return
