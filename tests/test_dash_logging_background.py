"""Regression tests for logging UI notifications from background threads.

The rank-freshness Timer chain and the file watchdog call ``dash_logger``
from plain threads, where no Dash callback context exists. The stock
``NotificationsLogHandler.emit`` raised ``LookupError`` there, killing the
thread and never showing the promised notification. The handler must queue
such records instead, for delivery by ``flush_background_notifications``.
"""

import threading
from collections.abc import Iterator

import dash
import pytest
from dash import no_update
from dash._callback_context import context_value
from dash._utils import AttributeDict

from source.utilities.dash_logging import (
    drain_background_notifications,
    get_dash_logger,
)

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402

dash_logger = get_dash_logger(__name__)


@pytest.fixture(autouse=True)
def _isolated_queue() -> Iterator[None]:
    """Keep notifications queued by other tests out of assertions."""
    drain_background_notifications()
    yield
    drain_background_notifications()


def test_background_thread_error_is_queued_not_raised() -> None:
    escaped: list[BaseException] = []

    def _log() -> None:
        try:
            dash_logger.error("Position update timed out for %s.", "VT Angleshot")
        except BaseException as exc:  # noqa: BLE001
            escaped.append(exc)

    thread = threading.Thread(target=_log)
    thread.start()
    thread.join()

    assert escaped == []
    notifications = drain_background_notifications()
    assert len(notifications) == 1
    assert notifications[0]["message"] == "Position update timed out for VT Angleshot."
    assert notifications[0]["color"] == "red"
    assert notifications[0]["action"] == "show"


def test_warning_level_queues_yellow_notification() -> None:
    def _log() -> None:
        dash_logger.warning("KovaaK's may still be catching up.")

    thread = threading.Thread(target=_log)
    thread.start()
    thread.join()

    notifications = drain_background_notifications()
    assert [n["color"] for n in notifications] == ["yellow"]
    assert [n["title"] for n in notifications] == ["Warning"]


def test_callback_context_records_bypass_the_queue() -> None:
    """Inside a callback the handler must keep the direct set_props path."""
    ctx = AttributeDict(updated_props={})
    token = context_value.set(ctx)
    try:
        dash_logger.error("in-context failure")
    finally:
        context_value.reset(token)

    assert drain_background_notifications() == []
    assert ctx.updated_props  # the notification went out through set_props


def test_flush_delivers_queued_notifications_once() -> None:
    def _log() -> None:
        dash_logger.error("Position update failed unexpectedly.")

    thread = threading.Thread(target=_log)
    thread.start()
    thread.join()

    delivered = home.flush_background_notifications(1)
    assert isinstance(delivered, list)
    assert [n["message"] for n in delivered] == ["Position update failed unexpectedly."]
    assert home.flush_background_notifications(2) is no_update
