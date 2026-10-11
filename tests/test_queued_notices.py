"""Notices queued where no browser could be told must still reach the user.

A run that failed to import is queued from a plain thread, and a playlist that
did not load is queued while the app starts. Each has a flush in
``source/components/queued_notices.py`` that drains its queue into toasts.
"""

import dash
import pytest
from dash._callback import GLOBAL_CALLBACK_LIST, GLOBAL_CALLBACK_MAP

from source.components import queued_notices, scenario_selection
from source.kovaaks import data_service
from source.my_watchdog import file_watchdog

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402


@pytest.fixture(autouse=True)
def _empty_failure_queue():
    file_watchdog.run_import_failure_queue.clear()
    yield
    file_watchdog.run_import_failure_queue.clear()


def _walk_components(component):
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk_components(child)
        return
    yield from _walk_components(children)


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


NOTIFICATION_OUTPUT = "notification-container.sendNotifications@"


def _flushes_on(interval_id: str) -> list[dict]:
    """Find the registrations whose only Input is one interval's tick."""
    return [
        entry
        for entry in GLOBAL_CALLBACK_LIST
        if [(dep["id"], dep["property"]) for dep in entry["inputs"]]
        == [(interval_id, "n_intervals")]
    ]


def _answering(registration: dict) -> str:
    """Name the function a registration runs."""
    return GLOBAL_CALLBACK_MAP[registration["output"]]["callback"].__name__


@pytest.fixture
def restored_callbacks():
    """Take a test's registrations back out of Dash's process-wide registry."""
    saved_list = list(GLOBAL_CALLBACK_LIST)
    saved_map = dict(GLOBAL_CALLBACK_MAP)
    yield
    GLOBAL_CALLBACK_LIST[:] = saved_list
    GLOBAL_CALLBACK_MAP.clear()
    GLOBAL_CALLBACK_MAP.update(saved_map)


@pytest.mark.parametrize(
    ("interval_id", "flush"),
    [
        ("interval-component", "flush_run_import_failures"),
        ("startup-playlist-warning-interval", "flush_startup_playlist_warnings"),
    ],
)
def test_the_page_registers_each_flush_on_an_interval_its_layout_builds(
    monkeypatch, interval_id, flush
):
    """Registration is a call the page makes; without it a queue never empties."""
    (registration,) = _flushes_on(interval_id)

    assert _answering(registration) == flush
    assert registration["output"].startswith(NOTIFICATION_OUTPUT)
    # Registered to answer the interval's tick, not the mount.
    assert registration["prevent_initial_call"] is True

    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])
    mounted = {
        getattr(component, "id", None) for component in _walk_components(home.layout())
    }
    # The layout spells each interval's id itself, so nothing but this ties
    # it to the id the flush was registered on.
    assert interval_id in mounted


def test_a_second_page_registers_each_flush_on_an_interval_of_its_own(
    restored_callbacks,
):
    registered_before = len(GLOBAL_CALLBACK_LIST)

    queued_notices.register_run_import_failure_flush("second-poll")
    queued_notices.register_startup_playlist_warning_flush("second-startup")

    added = GLOBAL_CALLBACK_LIST[registered_before:]
    assert [
        (
            [(dep["id"], dep["property"]) for dep in entry["inputs"]],
            entry["state"],
            _answering(entry),
        )
        for entry in added
    ] == [
        ([("second-poll", "n_intervals")], [], "flush_run_import_failures"),
        ([("second-startup", "n_intervals")], [], "flush_startup_playlist_warnings"),
    ]
    # Both pages write the shell's one notification container. Dash tells the
    # writers apart by their inputs, so each registration is its own output
    # and the first page's two are still there.
    writers = [
        entry["output"]
        for entry in GLOBAL_CALLBACK_LIST
        if entry["output"].startswith(NOTIFICATION_OUTPUT)
    ]
    assert len(writers) == len(set(writers))
    assert {entry["output"] for entry in added} <= set(writers)
    assert len(_flushes_on("interval-component")) == 1
    assert len(_flushes_on("startup-playlist-warning-interval")) == 1
