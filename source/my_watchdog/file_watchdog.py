"""
Business logic for monitoring a specified directory for newly created files.
"""

import datetime
import logging
import time
from collections import deque
from pathlib import Path

from watchdog.events import FileSystemEventHandler

from source.config.config_service import get_config
from source.config.settings_service import get_identity
from source.kovaaks.api_service import schedule_rank_freshness_refresh
from source.kovaaks.data_models import RunData
from source.kovaaks.data_service import (
    extract_data_from_file,
    get_high_score,
    get_personal_best_run,
    get_sensitivities_vs_runs,
    is_run_file_loaded,
    is_scenario_in_database,
    load_csv_file_into_database,
)
from source.kovaaks.time_scored_service import (
    eligible_pace_constant,
    get_pace_basis,
    note_performance_file,
)
from source.my_queue.message_queue import NewFileMessage, message_queue

logger = logging.getLogger(__name__)

RUN_IMPORT_FAILURE_MESSAGE = "Couldn't process a new run file. See data/logs/debug.log."

# The wait before each parse of a new run CSV. The first lets the game finish
# the file and its performance file. The later ones give a CSV still locked or
# mid-write, by the game or by an antivirus or sync agent, more time before the
# run is reported as not recorded. Every wait holds the observer thread, so a
# file that never parses delays the next event by their sum; runs land far
# enough apart that nobody sees it. Moving the waits to a worker thread was
# weighed and declined:
# docs/decision_log/2026/2026-10-26-run-imports-retry-a-failed-parse-on-the-observer-thread.md
PARSE_WAITS_SECONDS = (1, 2, 4)

# Run files this thread failed to import. The watchdog runs outside any Dash
# callback context, so it publishes here instead of driving a UI output, and
# an interval callback on Home and on Run History drains it into one toast --
# the same shape as the startup playlist-warning queue. Typed and
# single-purpose on purpose: see the background-thread rule in
# docs/architecture.md.
run_import_failure_queue: deque[str] = deque()


def drain_run_import_failures() -> list[str]:
    """Drain run-import failures for UI delivery on a page's next poll tick."""
    failures: list[str] = []
    while True:
        try:
            failures.append(run_import_failure_queue.popleft())
        except IndexError:
            return failures


def _get_created_csv_path(event) -> str | None:
    """Return a created CSV path after preserving the detection debug log."""
    if event.is_directory:
        return None

    file = event.src_path
    logger.debug('Detected new file: "%s"', Path(file).name)
    if not file.endswith(".csv"):
        return None
    return file


def _enqueue_after_loading(file: str, message: NewFileMessage) -> bool:
    """Make a run visible to the UI only after it is queryable in the stores."""
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
        logger.exception('Failed to schedule rank refresh for "%s"', scenario_name)


def _pace_constant_for_landed_run(
    run_data: RunData,
    previous_best_run: RunData | None,
) -> float | None:
    """Work out the constant a landed run's message carries, or None.

    The run is not in the stores yet, so the lookup is handed it: a scenario's
    newest run names its version, and this run is judged by its own
    performance file.
    """
    try:
        return eligible_pace_constant(
            get_pace_basis(run_data.scenario, landed_run=run_data),
            run_data,
            previous_best_run,
        )
    except Exception:  # noqa: BLE001 -- on_created's guard would drop the run.
        # The lookup handles a missing or unreadable performance file itself.
        # Anything else must cost the pace math only: the run still imports,
        # and its message carries no constant, so every consumer keeps score.
        logger.warning(
            'Failed to tell whether "%s" is time-scored',
            run_data.scenario,
            exc_info=True,
        )
        return None


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
                'Failed to process new stats file: "%s"',
                getattr(event, "src_path", "(unknown)"),
            )
            run_import_failure_queue.append(RUN_IMPORT_FAILURE_MESSAGE)

    def _import_created_file(self, event):
        """Parse, store, and announce one created file; may raise on surprises."""
        file = _get_created_csv_path(event)
        if file is None or is_run_file_loaded(file):
            return

        run_data: RunData | None = None
        for wait in PARSE_WAITS_SECONDS:
            time.sleep(wait)
            run_data = extract_data_from_file(file)
            if run_data:
                break
        if not run_data:
            # extract_data_from_file contains its own read and parse failures --
            # a CSV still locked by KovaaK's, a mid-write line -- and returns
            # None, so on_created's guard never sees them. With the retries
            # spent and no later event promised, the run stays missing until a
            # restart: notify here or the user is never told.
            logger.warning('Failed to get run data for CSV file: "%s"', file)
            run_import_failure_queue.append(RUN_IMPORT_FAILURE_MESSAGE)
            return

        sensitivity_key = f"{run_data.horizontal_sens} {run_data.sens_scale}"

        # The game writes a run's performance file within milliseconds of its
        # stats file, so the wait before the stats file is read covers it.
        # Listing it for every run, a scenario's first included, is what lets
        # the table and the chart see the file this thread judges the run by.
        note_performance_file(run_data)

        # Case 1: new scenario.
        if not is_scenario_in_database(run_data.scenario):
            logger.debug('Found new scenario: "%s"', run_data.scenario)
            message = NewFileMessage(
                datetime_created=datetime.datetime.now(),
                is_new_sensitivity=True,
                run_id=Path(file).name,
                scenario_name=run_data.scenario,
                scenario_previous_best=None,
                score=run_data.score,
                sensitivity=sensitivity_key,
                # Nothing judges or celebrates a scenario's first run.
                pace_constant=None,
            )
            if _enqueue_after_loading(file, message):
                _refresh_rank_after_high_score(run_data.scenario, run_data.score)
            return

        high_score = get_high_score(run_data.scenario)
        is_new_high_score = run_data.score > high_score
        # Worked out here, before the run is stored and its message queued, so
        # the celebration toast agrees with the page that is redrawn once the
        # run lands.
        pace_constant = _pace_constant_for_landed_run(
            run_data,
            get_personal_best_run(run_data.scenario),
        )

        # Case 2: new sensitivity.
        sensitivities_vs_runs = get_sensitivities_vs_runs(run_data.scenario)
        if sensitivity_key not in sensitivities_vs_runs:
            logger.debug('Found new sensitivity: "%s"', sensitivity_key)
            message = NewFileMessage(
                datetime_created=datetime.datetime.now(),
                is_new_sensitivity=True,
                run_id=Path(file).name,
                scenario_name=run_data.scenario,
                scenario_previous_best=high_score,
                score=run_data.score,
                sensitivity=sensitivity_key,
                pace_constant=pace_constant,
            )
            if _enqueue_after_loading(file, message) and is_new_high_score:
                _refresh_rank_after_high_score(run_data.scenario, run_data.score)
            return

        # Case 3: existing scenario and existing sensitivity.
        message = NewFileMessage(
            datetime_created=datetime.datetime.now(),
            is_new_sensitivity=False,
            run_id=Path(file).name,
            scenario_name=run_data.scenario,
            scenario_previous_best=high_score,
            score=run_data.score,
            sensitivity=sensitivity_key,
            pace_constant=pace_constant,
        )
        if _enqueue_after_loading(file, message) and is_new_high_score:
            _refresh_rank_after_high_score(run_data.scenario, run_data.score)
