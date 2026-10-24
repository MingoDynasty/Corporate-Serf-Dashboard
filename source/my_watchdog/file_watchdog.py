"""
Business logic for monitoring a specified directory for newly created files.
"""

import datetime
import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from watchdog.events import (
    FileSystemEvent,
    FileSystemEventHandler,
    FileSystemMovedEvent,
)

from source.config.config_service import get_config
from source.config.settings_service import get_identity
from source.kovaaks.api_service import schedule_rank_freshness_refresh
from source.kovaaks.data_models import RunData
from source.kovaaks.data_service import (
    extract_data_from_file,
    get_all_runs,
    get_high_score,
    get_personal_best_run,
    get_sensitivities_vs_runs,
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

# Run files this worker failed to import. It runs outside any Dash
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


def _get_created_csv_path(event: FileSystemEvent) -> str | None:
    """Return a created CSV path after preserving the detection debug log."""
    if event.is_directory:
        return None

    file = os.fsdecode(event.src_path)
    logger.debug('Detected new file: "%s"', Path(file).name)
    if not file.endswith(".csv"):
        return None
    return file


def _enqueue_after_loading(file: str, message: NewFileMessage) -> bool:
    """Make a run visible to the UI only after it is queryable in the stores."""
    if not load_csv_file_into_database(file):
        # A file replaced after the first parse must remain retryable.
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
    except Exception:  # noqa: BLE001 -- a pace failure must not retry an otherwise usable run.
        # The lookup handles a missing or unreadable performance file itself.
        # Anything else must cost the pace math only: the run still imports,
        # and its message carries no constant, so every consumer keeps score.
        logger.warning(
            'Failed to tell whether "%s" is time-scored',
            run_data.scenario,
            exc_info=True,
        )
        return None


def import_run_file(file: str) -> bool:
    """Import and announce one run, returning False when the attempt fails.

    Call only from the ingestion worker after startup. Store writes precede
    notification publication, and failures never announce a landed run.
    """
    logger.debug('Importing new run file: "%s"', Path(file).name)
    try:
        return _load_and_announce_run(file)
    except Exception:  # noqa: BLE001 -- keep later runs importing after a failure.
        logger.exception('Failed to process new stats file: "%s"', file)
        return False


def _load_and_announce_run(file: str) -> bool:
    """Load one parsed run and publish its pre-import facts."""
    run_data = extract_data_from_file(file)
    if not run_data:
        logger.warning('Failed to get run data for CSV file: "%s"', file)
        return False

    sensitivity_key = f"{run_data.horizontal_sens} {run_data.sens_scale}"

    # The per-file grace period also lets the game's companion performance
    # file arrive before the run's pace constant is judged.
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
        loaded = _enqueue_after_loading(file, message)
        if loaded:
            _refresh_rank_after_high_score(run_data.scenario, run_data.score)
        return loaded

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
        loaded = _enqueue_after_loading(file, message)
        if loaded and is_new_high_score:
            _refresh_rank_after_high_score(run_data.scenario, run_data.score)
        return loaded

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
    loaded = _enqueue_after_loading(file, message)
    if loaded and is_new_high_score:
        _refresh_rank_after_high_score(run_data.scenario, run_data.score)
    return loaded


# Deadlines let a burst share its grace period. Keep the grace for companion
# performance files as well as Windows locks and incomplete CSV writes.
FILE_GRACE_SECONDS = 1.0
IMPORT_RETRY_DELAYS = (0.25, 0.5, 1.0, 2.0, 4.0)
FAILED_FILE_RECHECK_SECONDS = 30.0


@dataclass
class _PendingImport:
    """One path's retry state, retained until it imports or the app stops."""

    file: str
    ready_at: float
    attempts: int = 0
    reported: bool = False


class NewFileHandler(FileSystemEventHandler):
    """Queue run paths for one writer without delaying observer dispatch.

    One instance watches one stats folder. Successful startup and live imports
    are identified by their file names, matching the run notification identity.
    Failed paths remain eligible; a quiet recheck follows the bounded retries.
    """

    def __init__(self) -> None:
        """Seed successful identities before live store writes begin."""
        self._condition = threading.Condition()
        self._pending: dict[str, _PendingImport] = {}
        self._imported = {
            os.path.normcase(run.stats_file_name)
            for run in get_all_runs()
            if run.stats_file_name is not None
        }
        self._stopping = False
        self._thread = threading.Thread(
            target=self._run, name="run-import", daemon=True
        )

    def start(self) -> None:
        """Start the sole live-run writer after the startup scan finishes."""
        self._thread.start()

    def stop(self) -> None:
        """Finish an active import and leave pending files for the next startup."""
        with self._condition:
            self._stopping = True
            self._condition.notify_all()

    def join(self, timeout: float | None = None) -> None:
        """Wait for the writer to stop, optionally up to ``timeout`` seconds."""
        if self._thread.ident is not None:
            self._thread.join(timeout)

    def on_created(self, event: FileSystemEvent) -> None:
        """Queue a new CSV without reading it on the observer thread."""
        self._queue_event(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Give an unfinished file a quiet period before its first read."""
        self._queue_event(event, modified=True)

    def on_moved(self, event: FileSystemMovedEvent) -> None:
        """Queue the final CSV path when a writer renames its temporary file."""
        if not event.is_directory:
            self._queue_path(os.fsdecode(event.dest_path))

    def _queue_event(self, event: FileSystemEvent, *, modified: bool = False) -> None:
        file = _get_created_csv_path(event)
        if file is not None:
            self._queue_path(os.fsdecode(file), modified=modified)

    def _queue_path(self, file: str, *, modified: bool = False) -> None:
        if not file.endswith(".csv"):
            return
        file = os.path.abspath(file)
        key = os.path.normcase(file)
        with self._condition:
            if (
                self._stopping
                or os.path.normcase(os.path.basename(file)) in self._imported
            ):
                return
            pending = self._pending.get(key)
            if pending is None:
                self._pending[key] = _PendingImport(
                    file, time.monotonic() + FILE_GRACE_SECONDS
                )
            elif modified and pending.attempts == 0:
                pending.ready_at = time.monotonic() + FILE_GRACE_SECONDS
            self._condition.notify()

    def _next_file(self) -> tuple[str, _PendingImport] | None:
        with self._condition:
            while not self._stopping:
                if not self._pending:
                    self._condition.wait()
                    continue
                pending = min(self._pending.values(), key=lambda item: item.ready_at)
                delay = pending.ready_at - time.monotonic()
                if delay > 0:
                    self._condition.wait(delay)
                    continue
                return pending.file, pending
        return None

    def _run(self) -> None:
        while (work := self._next_file()) is not None:
            file, pending = work
            imported = import_run_file(file)
            with self._condition:
                if imported:
                    self._imported.add(os.path.normcase(os.path.basename(file)))
                    del self._pending[os.path.normcase(file)]
                elif pending.attempts < len(IMPORT_RETRY_DELAYS):
                    pending.ready_at = (
                        time.monotonic() + IMPORT_RETRY_DELAYS[pending.attempts]
                    )
                    pending.attempts += 1
                else:
                    if not pending.reported:
                        run_import_failure_queue.append(RUN_IMPORT_FAILURE_MESSAGE)
                        pending.reported = True
                    pending.ready_at = time.monotonic() + FAILED_FILE_RECHECK_SECONDS
