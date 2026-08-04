"""Build the toast payloads the app shell's notification container renders."""

from typing import Any

# The dmc.NotificationContainer in the app shell that displays all toasts.
NOTIFICATION_CONTAINER_ID = "notification-container"

# The per-client store feeding ``upsert_toast``'s duration alternation. It is
# hosted in the app shell beside the container so its lifecycle matches the
# toasts': a page-layout store would reset on navigation and could hand a
# still-visible toast the duration it is already displaying.
TOAST_LIFETIME_STORE_ID = "toast-lifetime-sequence"

# The one nominal toast lifetime. Conditions that fire when nobody may be
# looking pass ``auto_close=False`` instead and stay until dismissed.
DEFAULT_AUTO_CLOSE_MS = 8000

# Two durations no viewer can tell apart, alternated by ``upsert_toast``.
# Mantine keys its auto-close effect on the resolved duration alone, so a
# replacement carrying the same number inherits the old toast's remaining time;
# a changed number forces the effect to cancel and re-arm for a full lifetime.
_ALTERNATING_AUTO_CLOSE_MS = (DEFAULT_AUTO_CLOSE_MS, DEFAULT_AUTO_CLOSE_MS + 1)


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


def upsert_toast(
    notification: dict[str, Any],
    sequence: int | None,
) -> list[dict[str, Any]]:
    """Pair the payloads that let one id replace whatever it is showing.

    A bare ``show`` cannot replace: DMC 2.8.0 ignores it for an id already on
    screen, and ``update`` is a no-op for an id that is not. So each emission
    sends both actions with the same id and payload -- whichever matches the
    toast's current state applies, and the other does nothing.

    ``sequence`` is the caller's per-client counter, incremented once per
    emission. It only picks which of two indistinguishable durations this
    emission carries; alternating them is what makes the replacement start a
    full lifetime instead of inheriting the remainder of the old timer.
    """
    payload = {
        **notification,
        "autoClose": _ALTERNATING_AUTO_CLOSE_MS[(sequence or 0) % 2],
    }
    return [{**payload, "action": "update"}, payload]
