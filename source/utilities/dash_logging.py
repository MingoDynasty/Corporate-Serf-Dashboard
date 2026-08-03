"""Send selected Python log records to Dash notification components."""

import logging
import uuid
from collections import deque
from typing import Any

from dash_extensions._typing import context_value

# The dmc.NotificationContainer in the app shell that displays all toasts.
NOTIFICATION_CONTAINER_ID = "notification-container"

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


def drain_background_notifications() -> list[dict[str, Any]]:
    """Drain queued background-thread notifications, oldest first."""
    drained: list[dict[str, Any]] = []
    while True:
        try:
            drained.append(_background_notification_queue.popleft())
        except IndexError:
            return drained


def _get_callback_context() -> Any | None:
    """Return the active Dash callback context, or None on plain threads."""
    if context_value is None:  # Dash internals moved; assume no context.
        return None
    try:
        ctx = context_value.get()
    except LookupError:
        # Fresh threads never inherit the ContextVar, so it can be unset.
        return None
    return ctx or None


def _send_notification_in_context(ctx: Any, notification: dict[str, Any]) -> None:
    """Append ``notification`` to the container's pending ``sendNotifications``.

    Dash's ``set_props`` replaces a prop wholesale on each call, so a second
    log record inside the same callback would overwrite the first toast;
    merge into the already-pending batch instead.
    """
    pending = dict(ctx.updated_props.get(NOTIFICATION_CONTAINER_ID, {}))
    pending["sendNotifications"] = [
        *pending.get("sendNotifications", []),
        notification,
    ]
    ctx.updated_props[NOTIFICATION_CONTAINER_ID] = pending


class QueueingNotificationsLogHandler(logging.Handler):
    """
    Deliver log records as toasts through the app shell's NotificationContainer.

    Records logged inside a Dash callback context ride along with the
    callback response through ``updated_props`` (the ``set_props`` side
    channel), shaped for the container's ``sendNotifications`` prop. On a
    plain thread (watchdog events, refresh Timers) no context exists, so
    records are queued instead and ``drain_background_notifications`` hands
    them to the container from an interval callback on the Home page.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Send via updated_props in a callback context, else queue the record."""
        try:
            notification = _notification_props(record.levelno, record.getMessage())
            if notification is None:
                return
            ctx = _get_callback_context()
            if ctx is not None:
                _send_notification_in_context(ctx, notification)
            else:
                _background_notification_queue.append(notification)
        except Exception:  # noqa: BLE001 -- logging must never raise into callers.
            self.handleError(record)


def get_dash_logger(logger_name: str) -> logging.Logger:
    """Get a logger that outputs notifications to the UI."""
    logger = logging.getLogger(logger_name + ".dash")
    logger.addHandler(log_handler)
    logger.setLevel(logging.DEBUG)
    return logger


log_handler = QueueingNotificationsLogHandler()
