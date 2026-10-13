"""Deliver the notices that were queued where no browser could be told.

A failed run import is found on the watchdog thread, and a playlist that did
not load is found while the app starts. Each waits in a queue on the server
until an interval in a mounted page asks for it. A page registers each flush
on an interval of its own, once, at import. Every page that does reads the
same queue, so whichever one is open delivers what is in it.
"""

from dash import Input, Output, callback, no_update

from source.components.local_icon import local_icon
from source.kovaaks.data_service import drain_startup_playlist_warnings
from source.my_watchdog.file_watchdog import drain_run_import_failures
from source.utilities.notifications import toast

_RUN_IMPORT_FAILURE_NOTIFICATION_ID = "run-import-failure"


def _build_run_import_failure_notification(
    failures: list[str],
) -> dict[str, object]:
    """Fold a batch of failed run imports into one red toast.

    Red is earned here: the user played those runs and nothing else tells them
    the runs never landed.
    """
    message = (
        failures[0]
        if len(failures) == 1
        else (
            f"{len(failures)} new run files couldn't be processed. "
            "See data/logs/debug.log."
        )
    )
    return toast(
        _RUN_IMPORT_FAILURE_NOTIFICATION_ID,
        "Run not recorded",
        message,
        color="red",
        icon=local_icon("material-symbols:warning-outline"),
    )


def flush_run_import_failures(_n_intervals):
    """Deliver run imports the watchdog thread could not complete.

    Delivered only on the pages that register it, Home and Run History: a
    missing run is a fact those pages show, so the next poll tick is soon
    enough.
    """
    failures = drain_run_import_failures()
    if not failures:
        return no_update
    return [_build_run_import_failure_notification(failures)]


def _build_startup_playlist_warning_notifications(
    warnings: list[str],
) -> list[dict[str, object]]:
    """Report the playlists that did not survive the startup scan.

    Persistent, not timed: these fire once per boot, seconds after the server
    starts, which is exactly when nobody is guaranteed to be watching.
    """
    return [
        toast(
            f"startup-playlist-warning-{idx}",
            "Playlist not loaded",
            warning,
            color="yellow",
            icon=local_icon("material-symbols:warning-outline"),
            auto_close=False,
        )
        for idx, warning in enumerate(warnings)
    ]


def flush_startup_playlist_warnings(_):
    """Deliver import-time playlist warnings after Dash has mounted."""
    warnings = drain_startup_playlist_warnings()
    if not warnings:
        return no_update
    return _build_startup_playlist_warning_notifications(warnings)


def register_run_import_failure_flush(interval_id: str) -> None:
    """Register the run import failure flush on one page's polling interval.

    Call once per page, at import, with the id of a ``dcc.Interval`` its
    layout builds. The toast goes to the shell's notification container, which
    every page shares.
    """
    callback(
        Output("notification-container", "sendNotifications", allow_duplicate=True),
        Input(interval_id, "n_intervals"),
        prevent_initial_call=True,
    )(flush_run_import_failures)


def register_startup_playlist_warning_flush(interval_id: str) -> None:
    """Register the startup playlist warning flush on one page's interval.

    Call once per page, at import, with the id of a ``dcc.Interval`` its
    layout builds to tick once, shortly after the page mounts. The toasts go
    to the shell's notification container, which every page shares.
    """
    callback(
        Output("notification-container", "sendNotifications", allow_duplicate=True),
        Input(interval_id, "n_intervals"),
        prevent_initial_call=True,
    )(flush_startup_playlist_warnings)
