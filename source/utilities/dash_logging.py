from collections.abc import Callable
import logging
import uuid

from dash_extensions.logging import NotificationsLogHandler
import dash_mantine_components as dmc


def get_custom_notification_log_writers() -> dict[int, Callable]:
    """
    This mimics dash_extensions.logging.py module, to allow for customization.
    It's a bit hacky, but it works.
    """

    def _default_kwargs(color, title, message):
        return dict(
            color=color,
            title=title,
            message=message,
            id=str(uuid.uuid4()),
            action="show",
            autoClose=8000,
        )

    def log_info(message, **kwargs):
        return dmc.Notification(
            **{**_default_kwargs("blue", "Info", message), **kwargs}
        )

    def log_warning(message, **kwargs):
        return dmc.Notification(
            **{**_default_kwargs("yellow", "Warning", message), **kwargs}
        )

    def log_error(message, **kwargs):
        return dmc.Notification(
            **{**_default_kwargs("red", "Error", message), **kwargs}
        )

    return {
        logging.INFO: log_info,
        logging.WARNING: log_warning,
        logging.ERROR: log_error,
    }


def get_dash_logger(logger_name: str) -> logging.Logger:
    """Get a logger that outputs notifications to the UI."""
    return log_handler.setup_logger(logger_name + ".dash")


log_handler = NotificationsLogHandler()
log_handler.log_writers = get_custom_notification_log_writers()
