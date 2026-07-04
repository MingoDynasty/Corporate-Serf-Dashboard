"""
Business logic for monitoring a specified directory for newly created files.
"""

import datetime
import logging
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler

from source.config.config_service import config
from source.kovaaks.api_service import schedule_rank_freshness_refresh
from source.kovaaks.data_service import (
    extract_data_from_file,
    get_high_score,
    get_sensitivities_vs_runs,
    is_scenario_in_database,
    load_csv_file_into_database,
)
from source.my_queue.message_queue import NewFileMessage, message_queue
from source.utilities.dash_logging import get_dash_logger
from source.utilities.utilities import ordinal

logger = logging.getLogger(__name__)
dash_logger = get_dash_logger(__name__)

# Percentage of the high score a run must beat to "pass" in the debug logs
# below. This is an interim, developer-facing stand-in for reviewing runs
# within a session: unlike the ephemeral toast, the log keeps a scrollable
# per-run record. Retained until the Run History feature supersedes it
# (see docs/run_history_proposal.md).
#
# Known limitation: the real threshold is a live UI control this watchdog
# thread can't read, so this constant only matches the UI verdict when the UI
# is left at 95% (the usual case). The score and percent-from-high-score
# figures logged next to it are always correct regardless.
SESSION_LOG_SCORE_THRESHOLD_PCT = 0.95


def _refresh_rank_after_high_score(
    scenario_name: str,
    expected_score: float,
) -> None:
    if not config.kovaaks_username:
        return

    try:
        schedule_rank_freshness_refresh(
            scenario_name,
            config.kovaaks_username,
            config.steam_id,
            expected_score,
            config.scenario_metadata_cache_ttl_hours,
        )
    except Exception:
        logger.exception("Failed to schedule rank refresh for %s", scenario_name)
        dash_logger.error("Could not start rank update for %s.", scenario_name)


class NewFileHandler(FileSystemEventHandler):
    """
    This class handles monitoring a specified directory for newly created files.
    """

    def on_created(self, event):
        """Import a newly created run CSV and notify interested UI callbacks."""
        if event.is_directory:  # Check if it's a file, not a directory
            return
        # Add your custom logic here to process the new file
        # For example, you could read its content, move it, or trigger another function.
        file = event.src_path
        print()
        logger.debug("Detected new file: %s", Path(file).name)
        if not file.endswith(".csv"):
            return

        time.sleep(1)  # Wait a second to avoid permission issues with race condition
        run_data = extract_data_from_file(file)
        if not run_data:
            logger.warning("Failed to get run data for CSV file: %s", file)
            return

        sensitivity_key = f"{run_data.horizontal_sens} {run_data.sens_scale}"

        # Case 1: new scenario.
        if not is_scenario_in_database(run_data.scenario):
            logger.debug("Found new scenario: %s", run_data.scenario)
            new_score_threshold = SESSION_LOG_SCORE_THRESHOLD_PCT * run_data.score
            logger.debug(
                "Current score (%.2f) sets the score threshold at (%.2f)",
                run_data.score,
                new_score_threshold,
            )
            message_queue.append(
                NewFileMessage(
                    datetime_created=datetime.datetime.now(),
                    nth_score=1,
                    previous_high_score=None,
                    scenario_name=run_data.scenario,
                    score=run_data.score,
                    sensitivity=sensitivity_key,
                ),
            )
            load_csv_file_into_database(file)
            _refresh_rank_after_high_score(run_data.scenario, run_data.score)
            return

        high_score = get_high_score(run_data.scenario)
        is_new_high_score = run_data.score > high_score

        pct_threshold = SESSION_LOG_SCORE_THRESHOLD_PCT
        score_threshold = pct_threshold * high_score
        pct_diff = (run_data.score / high_score - 1) * 100
        logger.debug(
            "Current score (%g) is %+.2f%% from high score (%g) "
            "with score threshold (%.2f)",
            run_data.score,
            pct_diff,
            high_score,
            score_threshold,
        )
        if is_new_high_score:
            new_score_threshold = pct_threshold * run_data.score
            logger.debug(
                "Score threshold increased from (%.2f) to (%.2f)",
                score_threshold,
                new_score_threshold,
            )
        if run_data.score > score_threshold:
            logger.debug(
                "Successfully passed the score threshold! Ready to move onto the next scenario."
            )
        else:
            logger.debug("Failed to meet the score threshold. Keep grinding...")

        # Case 2: new sensitivity.
        sensitivities_vs_runs = get_sensitivities_vs_runs(run_data.scenario)
        if sensitivity_key not in sensitivities_vs_runs:
            logger.debug("Found new sensitivity: %s", sensitivity_key)
            message_queue.append(
                NewFileMessage(
                    datetime_created=datetime.datetime.now(),
                    nth_score=1,
                    previous_high_score=None,
                    scenario_name=run_data.scenario,
                    score=run_data.score,
                    sensitivity=sensitivity_key,
                ),
            )
            load_csv_file_into_database(file)
            if is_new_high_score:
                _refresh_rank_after_high_score(run_data.scenario, run_data.score)
            return

        # Case 3: existing scenario and existing sensitivity, find nth score.
        nth_score = 1
        # TODO: O(n) linear search, should do O(log(n)) binary search instead
        for prev_run_data in sensitivities_vs_runs[sensitivity_key]:
            if prev_run_data.score > run_data.score:
                nth_score += 1
        logger.debug(
            "%s has a new %s place score: %s",
            sensitivity_key,
            ordinal(nth_score),
            run_data.score,
        )

        message_queue.append(
            NewFileMessage(
                datetime_created=datetime.datetime.now(),
                nth_score=nth_score,
                previous_high_score=high_score,
                scenario_name=run_data.scenario,
                score=run_data.score,
                sensitivity=sensitivity_key,
            ),
        )
        load_csv_file_into_database(file)
        if is_new_high_score:
            _refresh_rank_after_high_score(run_data.scenario, run_data.score)
        return
