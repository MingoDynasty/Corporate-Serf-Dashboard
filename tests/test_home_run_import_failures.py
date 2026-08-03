"""A run that failed to import must still reach the user, from a plain thread."""

import dash
import pytest

from source.my_watchdog import file_watchdog

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402


@pytest.fixture(autouse=True)
def _empty_failure_queue():
    file_watchdog.run_import_failure_queue.clear()
    yield
    file_watchdog.run_import_failure_queue.clear()


def test_no_failures_leaves_the_notification_output_alone():
    assert home.flush_run_import_failures(1) is dash.no_update


def test_one_failure_drains_into_one_red_toast():
    file_watchdog.run_import_failure_queue.append(
        file_watchdog.RUN_IMPORT_FAILURE_MESSAGE
    )

    notifications = home.flush_run_import_failures(1)

    assert len(notifications) == 1
    assert notifications[0]["title"] == "Run not recorded"
    assert notifications[0]["color"] == "red"
    assert notifications[0]["id"] == "run-import-failure"
    assert notifications[0]["message"] == file_watchdog.RUN_IMPORT_FAILURE_MESSAGE


def test_a_batch_of_failures_still_makes_one_toast():
    file_watchdog.run_import_failure_queue.extend(
        [file_watchdog.RUN_IMPORT_FAILURE_MESSAGE] * 3
    )

    notifications = home.flush_run_import_failures(1)

    assert len(notifications) == 1
    assert notifications[0]["message"] == (
        "3 new run files could not be processed. See debug.log for details."
    )


def test_a_drained_failure_does_not_toast_again_on_the_next_tick():
    file_watchdog.run_import_failure_queue.append(
        file_watchdog.RUN_IMPORT_FAILURE_MESSAGE
    )

    home.flush_run_import_failures(1)

    assert home.flush_run_import_failures(2) is dash.no_update
