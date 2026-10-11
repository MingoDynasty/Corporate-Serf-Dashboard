"""Deliver the notices that were queued where no browser could be told."""

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


@callback(
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Input("interval-component", "n_intervals"),
    prevent_initial_call=True,
)
def flush_run_import_failures(_n_intervals):
    """Deliver run imports the watchdog thread could not complete.

    Home-gated, like the delivery it replaces: a missing run is a Home-visible
    fact, so the next poll tick is soon enough.
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


@callback(
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Input("startup-playlist-warning-interval", "n_intervals"),
    prevent_initial_call=True,
)
def flush_startup_playlist_warnings(_):
    """Deliver import-time playlist warnings after Dash has mounted."""
    warnings = drain_startup_playlist_warnings()
    if not warnings:
        return no_update
    return _build_startup_playlist_warning_notifications(warnings)
