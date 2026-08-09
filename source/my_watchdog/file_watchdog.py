"""
Business logic for monitoring a specified directory for newly created files.
"""

import datetime
import logging
import time
from collections import deque
from pathlib import Path
from typing import cast

from sortedcontainers import SortedKeyList
from watchdog.events import FileSystemEventHandler

from source.config.config_service import get_config
from source.config.settings_service import get_identity
from source.kovaaks.api_service import schedule_rank_freshness_refresh
from source.kovaaks.data_service import (
    extract_data_from_file,
    get_high_score,
    get_sensitivities_vs_runs,
    is_scenario_in_database,
    load_csv_file_into_database,
)
from source.my_queue.message_queue import NewFileMessage, message_queue
from source.utilities.utilities import ordinal

logger = logging.getLogger(__name__)

RUN_IMPORT_FAILURE_MESSAGE = (
    "Could not process a new run file. See debug.log for details."
)

# Run files this thread failed to import. The watchdog runs outside any Dash
# callback context, so it publishes here instead of driving a UI output, and a
# Home interval callback drains it into one toast -- the same shape as the
# startup playlist-warning queue. Typed and single-purpose on purpose: see the
# background-thread rule in docs/architecture.md.
run_import_failure_queue: deque[str] = deque()


def drain_run_import_failures() -> list[str]:
    """Drain run-import failures for UI delivery on the next Home tick."""
    failures: list[str] = []
    while True:
        try:
            failures.append(run_import_failure_queue.popleft())
        except IndexError:
            return failures


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


def _get_created_csv_path(event) -> str | None:
    """Return a created CSV path after preserving the detection debug log."""
    if event.is_directory:
        return None

    file = event.src_path
    logger.debug("Detected new file: %s", Path(file).name)
    if not file.endswith(".csv"):
        return None
    return file


def _enqueue_after_loading(file: str, message: NewFileMessage) -> bool:
    """Make a run visible to Home only after it is queryable in the stores."""
    if not load_csv_file_into_database(file):
        # The store re-reads the CSV, so a file that parsed a moment ago in
        # _import_created_file can still fail here -- deleted or replaced in
        # between. Rare, but the run did not land either way, and this was the
        # last path that dropped one with nothing but a log line.
        run_import_failure_queue.append(RUN_IMPORT_FAILURE_MESSAGE)
        return False
    message_queue.append(message)
    return True


def _refresh_rank_after_high_score(
    scenario_name: str,
    expected_score: float,
) -> None:
    username, steam_id = get_identity()
    if not username:
        return

    try:
        schedule_rank_freshness_refresh(
            scenario_name,
            username,
            steam_id,
            expected_score,
            get_config().scenario_metadata_cache_ttl_hours,
        )
    except Exception:
        logger.exception("Failed to schedule rank refresh for %s", scenario_name)


class NewFileHandler(FileSystemEventHandler):
    """
    This class handles monitoring a specified directory for newly created files.
    """

    def on_created(self, event):
        """Import a newly created run CSV and notify interested UI callbacks."""
        try:
            self._import_created_file(event)
        except Exception:  # noqa: BLE001 -- watchdog does not guard handlers.
            # An escaped exception would kill the observer thread and silently
            # end run tracking for the rest of the session (e.g. an OSError
            # from a CSV still locked by KovaaK's); the next run must still
            # find a live handler. Log it and tell the UI instead.
            logger.exception(
                "Failed to process new stats file: %s",
                getattr(event, "src_path", "(unknown)"),
            )
            run_import_failure_queue.append(RUN_IMPORT_FAILURE_MESSAGE)

    def _import_created_file(self, event):
        """Parse, store, and announce one created file; may raise on surprises."""
        file = _get_created_csv_path(event)
        if file is None:
            return

        time.sleep(1)  # Wait a second to avoid permission issues with race condition
        run_data = extract_data_from_file(file)
        if not run_data:
            # extract_data_from_file contains its own read and parse failures --
            # a CSV still locked by KovaaK's, a mid-write line -- and returns
            # None, so on_created's guard above never sees them. This handler
            # only sees the creation event and never retries, so the run stays
            # missing until a restart: notify here or the user is never told.
            logger.warning("Failed to get run data for CSV file: %s", file)
            run_import_failure_queue.append(RUN_IMPORT_FAILURE_MESSAGE)
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
            message = NewFileMessage(
                datetime_created=datetime.datetime.now(),
                nth_score=1,
                previous_high_score=None,
                scenario_name=run_data.scenario,
                score=run_data.score,
                sensitivity=sensitivity_key,
            )
            if _enqueue_after_loading(file, message):
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
            message = NewFileMessage(
                datetime_created=datetime.datetime.now(),
                nth_score=1,
                previous_high_score=None,
                scenario_name=run_data.scenario,
                score=run_data.score,
                sensitivity=sensitivity_key,
            )
            if _enqueue_after_loading(file, message) and is_new_high_score:
                _refresh_rank_after_high_score(run_data.scenario, run_data.score)
            return

        # Case 3: existing scenario and existing sensitivity, find nth score.
        # The value is a SortedKeyList keyed by score ascending (see
        # data_service.load_csv_file_into_database); the annotation widens it to
        # list, so cast to reach bisect_key_right. The count of runs scoring
        # strictly higher than this run is len - bisect_key_right(score); the +1
        # makes it a 1-based rank (ties are not counted as higher). The new run
        # is not yet in the store, so this bisect ranks against the pre-insert
        # list.
        runs_by_score = cast(SortedKeyList, sensitivities_vs_runs[sensitivity_key])
        higher_count = len(runs_by_score) - runs_by_score.bisect_key_right(
            run_data.score
        )
        nth_score = higher_count + 1
        logger.debug(
            "%s has a new %s place score: %s",
            sensitivity_key,
            ordinal(nth_score),
            run_data.score,
        )

        message = NewFileMessage(
            datetime_created=datetime.datetime.now(),
            nth_score=nth_score,
            previous_high_score=high_score,
            scenario_name=run_data.scenario,
            score=run_data.score,
            sensitivity=sensitivity_key,
        )
        if _enqueue_after_loading(file, message) and is_new_high_score:
            _refresh_rank_after_high_score(run_data.scenario, run_data.score)
