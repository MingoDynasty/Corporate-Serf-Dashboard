"""
This mimics dash_extensions.logging.py module, to allow for customization.
It's a bit hacky, but it works.
"""

import logging
import uuid
from typing import Callable

import dash_mantine_components as dmc


def get_custom_notification_log_writers() -> dict[int, Callable]:
    """
    Log writers that target the Notification component from dash_mantine_components.
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
