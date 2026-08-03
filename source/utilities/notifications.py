"""Build the toast payloads the app shell's notification container renders."""

from typing import Any

# The dmc.NotificationContainer in the app shell that displays all toasts.
NOTIFICATION_CONTAINER_ID = "notification-container"

# The one nominal toast lifetime. Conditions that fire when nobody may be
# looking pass ``auto_close=False`` instead and stay until dismissed.
DEFAULT_AUTO_CLOSE_MS = 8000


# One parameter per payload field; a settings object would only re-spell the
# keyword arguments callers already write.
def toast(  # noqa: PLR0913
    notification_id: str,
    title: str,
    message: str,
    *,
    color: str,
    icon: Any = None,
    auto_close: int | bool = DEFAULT_AUTO_CLOSE_MS,
) -> dict[str, Any]:
    """Build one ``sendNotifications`` payload.

    ``notification_id`` is the dedupe key: DMC's ``show`` action ignores a
    payload whose id is already on screen, so ids are stable and semantic.
    ``auto_close=False`` keeps the toast up until the user dismisses it.
    """
    notification: dict[str, Any] = {
        "action": "show",
        "id": notification_id,
        "title": title,
        "message": message,
        "color": color,
        "autoClose": auto_close,
    }
    if icon is not None:
        notification["icon"] = icon
    return notification
