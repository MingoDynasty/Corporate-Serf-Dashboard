"""Send selected Python log records to Dash notification components."""

import logging
import uuid
from collections import deque
from collections.abc import Callable
from typing import Any

import dash_mantine_components as dmc
from dash_extensions._typing import context_value
from dash_extensions.logging import NotificationsLogHandler

# Notification color and title per log level, shared by the in-context
# writers and the background-thread queue path.
_LEVEL_STYLES: dict[int, tuple[str, str]] = {
    logging.INFO: ("blue", "Info"),
    logging.WARNING: ("yellow", "Warning"),
    logging.ERROR: ("red", "Error"),
}

# Records logged from threads without a Dash callback context (the file
# watchdog, the rank-freshness Timer chain) cannot reach the UI through
# set_props. Their notification props are queued here and delivered to the
# notification container by an interval callback on the Home page.
_background_notification_queue: deque[dict[str, Any]] = deque()


def _notification_props(levelno: int, message: str) -> dict[str, Any] | None:
    """Build ``sendNotifications``-shaped props, or None for unmapped levels."""
    style = _LEVEL_STYLES.get(levelno)
    if style is None:
        return None
    color, title = style
    return {
        "color": color,
        "title": title,
        "message": message,
        "id": str(uuid.uuid4()),
        "action": "show",
        "autoClose": 8000,
    }


def get_custom_notification_log_writers() -> dict[int, Callable]:
    """
    This mimics dash_extensions.logging.py module, to allow for customization.
    It's a bit hacky, but it works.
    """

    def _make_writer(levelno: int) -> Callable:
        def _write(message, **kwargs):
            return dmc.Notification(
                **{**(_notification_props(levelno, message) or {}), **kwargs},
            )

        return _write

    return {levelno: _make_writer(levelno) for levelno in _LEVEL_STYLES}


def drain_background_notifications() -> list[dict[str, Any]]:
    """Drain queued background-thread notifications, oldest first."""
    drained: list[dict[str, Any]] = []
    while True:
        try:
            drained.append(_background_notification_queue.popleft())
        except IndexError:
            return drained


def _in_callback_context() -> bool:
    """Return whether a Dash callback context is active on this thread."""
    if context_value is None:  # Dash internals moved; assume no context.
        return False
    try:
        return bool(context_value.get())
    except LookupError:
        # Fresh threads never inherit the ContextVar, so it can be unset.
        return False


class QueueingNotificationsLogHandler(NotificationsLogHandler):
    """
    Notification handler that is safe to use from background threads.

    The stock handler delivers through ``set_props``, which needs a Dash
    callback context; on a plain thread (watchdog events, refresh Timers)
    the context is unset and ``emit`` raises ``LookupError`` out of the
    ``logger.error(...)`` call, so the promised notification never appears
    and the thread dies. Records logged without a context are queued
    instead, and ``drain_background_notifications`` hands them to the
    notification container from an interval callback.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Deliver via set_props in a callback context, else queue the record."""
        try:
            if _in_callback_context():
                super().emit(record)
                return
            notification = _notification_props(record.levelno, record.getMessage())
            if notification is not None:
                _background_notification_queue.append(notification)
        except Exception:  # noqa: BLE001 -- logging must never raise into callers.
            self.handleError(record)


def get_dash_logger(logger_name: str) -> logging.Logger:
    """Get a logger that outputs notifications to the UI."""
    return log_handler.setup_logger(logger_name + ".dash")


log_handler = QueueingNotificationsLogHandler()
log_handler.log_writers = get_custom_notification_log_writers()
