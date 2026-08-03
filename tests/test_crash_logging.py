"""Crash hooks and the watchdog guard must leave log records, not dead threads."""

import logging
import sys
import threading
from types import SimpleNamespace

from source.my_watchdog import file_watchdog
from source.utilities import crash_logging


def _current_exc_info():
    try:
        raise ValueError("boom")
    except ValueError:
        return sys.exc_info()


def test_main_thread_hook_logs_critical(caplog):
    with caplog.at_level(logging.CRITICAL, logger=crash_logging.logger.name):
        crash_logging._log_uncaught_exception(*_current_exc_info())

    assert [record.levelno for record in caplog.records] == [logging.CRITICAL]
    assert "Uncaught exception" in caplog.text
    assert "boom" in caplog.text


def test_main_thread_hook_skips_keyboard_interrupt(caplog):
    with caplog.at_level(logging.CRITICAL, logger=crash_logging.logger.name):
        crash_logging._log_uncaught_exception(
            KeyboardInterrupt,
            KeyboardInterrupt(),
            None,
        )

    assert caplog.records == []


def test_thread_hook_logs_critical_with_thread_name(monkeypatch, caplog):
    monkeypatch.setattr(
        threading,
        "excepthook",
        crash_logging._log_uncaught_thread_exception,
    )

    def boom():
        raise ValueError("thread boom")

    thread = threading.Thread(target=boom, name="boom-thread")
    with caplog.at_level(logging.CRITICAL, logger=crash_logging.logger.name):
        thread.start()
        thread.join()

    assert [record.levelno for record in caplog.records] == [logging.CRITICAL]
    assert "boom-thread" in caplog.text
    assert "thread boom" in caplog.text


def test_thread_hook_ignores_system_exit(monkeypatch, caplog):
    monkeypatch.setattr(
        threading,
        "excepthook",
        crash_logging._log_uncaught_thread_exception,
    )

    thread = threading.Thread(target=sys.exit, args=(1,), name="exit-thread")
    with caplog.at_level(logging.CRITICAL, logger=crash_logging.logger.name):
        thread.start()
        thread.join()

    assert caplog.records == []


def test_on_created_survives_unexpected_error(monkeypatch, caplog):
    def explode(_path):
        raise OSError("file still locked")

    monkeypatch.setattr(file_watchdog.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(file_watchdog, "extract_data_from_file", explode)
    file_watchdog.run_import_failure_queue.clear()

    with caplog.at_level(logging.ERROR, logger=file_watchdog.logger.name):
        file_watchdog.NewFileHandler().on_created(
            SimpleNamespace(is_directory=False, src_path="run.csv")
        )

    assert "Failed to process new stats file: run.csv" in caplog.text
    # exc_info rides along, so the traceback reaches debug.log.
    assert "file still locked" in caplog.text
    # The watchdog thread has no callback context, so it publishes the failure
    # for Home's interval callback to drain rather than driving a UI output.
    assert file_watchdog.drain_run_import_failures() == [
        "Could not process a new run file. See debug.log for details."
    ]
    assert file_watchdog.drain_run_import_failures() == []
