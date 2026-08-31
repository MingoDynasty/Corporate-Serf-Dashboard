"""Build the toast payloads the app shell's notification container renders."""

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from dash import Patch

# The dmc.NotificationContainer in the app shell that displays all toasts.
NOTIFICATION_CONTAINER_ID = "notification-container"

# The per-client store mapping each logical toast channel to the instance id it
# currently has on screen, so ``channel_toast`` knows what to hide. It is
# hosted in the app shell beside the container so its lifecycle matches the
# toasts': a page-layout store would reset on navigation and leave a
# still-visible toast with no id to replace it by.
TOAST_CHANNEL_REGISTRY_STORE_ID = "toast-channel-registry"

# The personal best celebration's own toast id, deliberately not the page's
# run-verdict id: the celebration is an app-wide family with its own lifetime,
# so it must survive the next ordinary run toast instead of being replaced by
# it.
CELEBRATION_NOTIFICATION_ID = "pb-celebration"

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
    payload whose id is already on screen. An event toast passes the id it
    wants to appear under; a channel toast passes its logical channel key and
    hands the payload to ``channel_toast``, which stamps a fresh instance id
    over it. ``auto_close=False`` keeps the toast up until the user dismisses
    it.
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


class ChannelEmission(NamedTuple):
    """One channel emission's three container outputs, in output order."""

    send: list[dict[str, Any]]
    hide: list[str]
    registry: Patch


def channel_toast(
    notification: dict[str, Any],
    registry: Mapping[str, str | None] | None,
    *,
    clears: Sequence[str] = (),
) -> ChannelEmission:
    """Re-pop one toast channel, hiding the instance it replaces.

    ``notification`` carries the channel's *logical key* in its ``id``, and
    this stamps a fresh per-emission instance id over it. Showing a new id is
    what makes a repeat visible at all: DMC 2.8.0 ignores a ``show`` for an id
    already on screen, so a stable id answers a retry with nothing. The
    container applies ``hideNotifications`` after ``sendNotifications``, so the
    replaced instance animates out while the fresh one enters, and the fresh
    one carries its own full lifetime rather than the remainder of the old
    timer.

    ``clears`` names the other channels this emission falsifies -- a success
    clearing the failure it answers. Their current instances join the hide
    list, and their registry entries are cleared with them. Hiding an id that
    is not on screen is a no-op, so a channel that never fired costs nothing.

    Registry writes are per-key ``dash.Patch`` assignments, never a whole-dict
    replacement: a response that rewrote the whole dict would carry a stale
    value for every channel it did not emit, so two responses landing out of
    order could resurrect an obsolete instance id -- leaving two toasts of one
    channel on screen, or a failure toast beside the success that cleared it.
    """
    channel_key = notification["id"]
    instance_id = f"{channel_key}-{uuid.uuid4().hex}"
    current = registry or {}
    hide = [
        instance
        for key in (channel_key, *clears)
        if (instance := current.get(key)) is not None
    ]
    patch = Patch()
    patch[channel_key] = instance_id
    for key in clears:
        # Assigned None rather than deleted: the key may never have been
        # written, and the registry only ever asks whether a channel has an
        # instance on screen.
        patch[key] = None
    return ChannelEmission([{**notification, "id": instance_id}], hide, patch)


def upsert_sticky_toast(notification: dict[str, Any]) -> list[dict[str, Any]]:
    """Pair the payloads that let one until-dismissed id replace what it shows.

    A bare ``show`` cannot replace: DMC 2.8.0 ignores it for an id already on
    screen, and ``update`` is a no-op for an id that is not. So each emission
    sends both actions with the same id and payload -- whichever matches the
    toast's current state applies, and the other does nothing.

    Why the celebration keeps this instead of moving to ``channel_toast``: a
    toast that stays until dismissed has no timer to re-arm, and re-popping it
    would replay the entry animation for news the user has already seen and
    chosen to leave up.
    """
    payload = {**notification, "autoClose": False}
    return [{**payload, "action": "update"}, payload]
