"""A new run CSV that is not ready yet gets more parse attempts before a toast."""

import logging
from collections import deque
from pathlib import Path

import pytest
from sortedcontainers import SortedList
from watchdog.events import FileCreatedEvent

from source.kovaaks import data_service
from source.my_watchdog import file_watchdog

SCENARIO = "Synthetic parse retry"
FILENAME = f"{SCENARIO} - Challenge - 2026.10.26-12.00.00 Stats.csv"
CONTENT = (
    "Score:,100\nSens Scale:,cm/360\nHoriz Sens:,40\n"
    f"Scenario:,{SCENARIO}\n"
    + data_service.POSSIBLE_SUB_CSV_HEADERS[0]
    + "\nRifle,100,90,0,0\n"
)
# What a reader can see mid-write: the score line is there, its value is not.
PARTIAL_CONTENT = "Score:\n"


@pytest.fixture(autouse=True)
def isolated_stores(monkeypatch):
    monkeypatch.setattr(data_service, "kovaaks_database", {})
    monkeypatch.setattr(
        data_service, "run_database", SortedList(key=lambda run: run.datetime_object)
    )
    monkeypatch.setattr(file_watchdog, "message_queue", deque())
    monkeypatch.setattr(file_watchdog, "run_import_failure_queue", deque())


def _deliver(path: Path) -> None:
    file_watchdog.NewFileHandler().dispatch(FileCreatedEvent(str(path)))


def test_file_finished_during_a_retry_wait_imports_once_without_a_toast(
    tmp_path, monkeypatch
):
    path = tmp_path / FILENAME
    path.write_text(PARTIAL_CONTENT, encoding="utf-8")
    waits = []

    def wait(seconds):
        waits.append(seconds)
        if len(waits) == 2:
            # The writer finishes after the first parse saw a partial file.
            path.write_text(CONTENT, encoding="utf-8")

    monkeypatch.setattr(file_watchdog.time, "sleep", wait)
    _deliver(path)

    assert waits == list(file_watchdog.PARSE_WAITS_SECONDS[:2])
    assert len(data_service.run_database) == 1
    assert [message.run_id for message in file_watchdog.message_queue] == [FILENAME]
    assert file_watchdog.drain_run_import_failures() == []


def test_file_that_never_parses_is_tried_after_every_wait_then_reported_once(
    tmp_path, monkeypatch, caplog
):
    path = tmp_path / FILENAME
    path.write_text(PARTIAL_CONTENT, encoding="utf-8")
    waits = []
    monkeypatch.setattr(file_watchdog.time, "sleep", waits.append)

    with caplog.at_level(logging.WARNING, logger=file_watchdog.logger.name):
        _deliver(path)

    assert waits == list(file_watchdog.PARSE_WAITS_SECONDS)
    assert list(data_service.run_database) == []
    assert list(file_watchdog.message_queue) == []
    assert file_watchdog.drain_run_import_failures() == [
        file_watchdog.RUN_IMPORT_FAILURE_MESSAGE
    ]
    # Each attempt's parse failure is logged where it happens; the handler
    # reports the run as not recorded only once, after the last attempt.
    handler_warnings = [
        record for record in caplog.records if record.name == file_watchdog.logger.name
    ]
    assert [record.getMessage() for record in handler_warnings] == [
        f'Failed to get run data for CSV file: "{path}"'
    ]
