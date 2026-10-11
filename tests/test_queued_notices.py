"""Notices queued where no browser could be told must still reach the user.

A run that failed to import is queued from a plain thread, and a playlist that
did not load is queued while the app starts. Each has a flush in
``source/components/queued_notices.py`` that drains its queue into toasts.
"""

import dash
import pytest

from source.components import queued_notices
from source.kovaaks import data_service
from source.my_watchdog import file_watchdog


@pytest.fixture(autouse=True)
def _empty_failure_queue():
    file_watchdog.run_import_failure_queue.clear()
    yield
    file_watchdog.run_import_failure_queue.clear()


def test_no_failures_leaves_the_notification_output_alone():
    assert queued_notices.flush_run_import_failures(1) is dash.no_update


def test_one_failure_drains_into_one_red_toast():
    file_watchdog.run_import_failure_queue.append(
        file_watchdog.RUN_IMPORT_FAILURE_MESSAGE
    )

    notifications = queued_notices.flush_run_import_failures(1)

    assert len(notifications) == 1
    assert notifications[0]["title"] == "Run not recorded"
    assert notifications[0]["color"] == "red"
    assert notifications[0]["id"] == "run-import-failure"
    assert notifications[0]["message"] == file_watchdog.RUN_IMPORT_FAILURE_MESSAGE


def test_a_batch_of_failures_still_makes_one_toast():
    file_watchdog.run_import_failure_queue.extend(
        [file_watchdog.RUN_IMPORT_FAILURE_MESSAGE] * 3
    )

    notifications = queued_notices.flush_run_import_failures(1)

    assert len(notifications) == 1
    assert notifications[0]["message"] == (
        "3 new run files couldn't be processed. See data/logs/debug.log."
    )


def test_a_drained_failure_does_not_toast_again_on_the_next_tick():
    file_watchdog.run_import_failure_queue.append(
        file_watchdog.RUN_IMPORT_FAILURE_MESSAGE
    )

    queued_notices.flush_run_import_failures(1)

    assert queued_notices.flush_run_import_failures(2) is dash.no_update


def test_startup_playlist_warnings_flush_after_mount_and_drain_once():
    data_service.playlist_startup_warning_queue.clear()
    warnings = ["First warning", "Second warning"]
    data_service.playlist_startup_warning_queue.extend(warnings)

    notifications = queued_notices.flush_startup_playlist_warnings(1)

    assert [notification["message"] for notification in notifications] == warnings
    # They fire seconds after a server start, when nobody is guaranteed to be
    # looking, so they wait for a dismissal instead of timing out.
    assert [notification["title"] for notification in notifications] == [
        "Playlist not loaded",
        "Playlist not loaded",
    ]
    assert [notification["autoClose"] for notification in notifications] == [
        False,
        False,
    ]
    assert queued_notices.flush_startup_playlist_warnings(2) is dash.no_update
