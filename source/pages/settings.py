"""Build the user-settings page at ``/settings``.

The one runtime writer of the settings store. It shows what is on disk (never
the process-pinned accessors), saves all three keys at once, and says when the
running process no longer matches what was saved.

Component ids are ``app-settings-*``: Home's graph-settings modal already owns
the bare ``settings-*`` namespace.
"""

import logging
from pathlib import Path

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, ctx, no_update

from source.config.settings_service import (
    KOVAAKS_USERNAME_KEY,
    STATS_DIR_KEY,
    STEAM_ID_KEY,
    get_settings,
    is_restart_pending,
    save_settings,
)
from source.kovaaks.percentile_warmup_service import start_percentile_warmup_worker

logger = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path="/settings",
    title="Settings",
)

STATS_DIR_DESCRIPTION = (
    "The KovaaK's stats folder this app reads runs from, usually "
    "...\\FPSAimTrainer\\FPSAimTrainer\\stats. Leave it empty to run without "
    "run data."
)
USERNAME_DESCRIPTION = (
    "Your KovaaK's account name, used to look up your leaderboard rank. Leave "
    "it empty to turn rank lookups off."
)
STEAM_ID_DESCRIPTION = (
    "Your 17-digit SteamID64. Optional; it disambiguates accounts that share a "
    "KovaaK's username."
)

STATS_DIR_ERROR = "No such directory."
STEAM_ID_ERROR = "Enter digits only."

RESTART_NOTICE = (
    "Saved. Restart the dashboard to apply — this app is still running on the "
    "settings it started with."
)
SAVED_STATUS = "Settings saved."

RESTART_NOTICE_CLASS = "app-settings-restart-notice"
# The notice ships hidden and is revealed by dropping this modifier, the same
# way the playlists page reveals its cleanup alert.
RESTART_NOTICE_HIDDEN_CLASS = (
    f"{RESTART_NOTICE_CLASS} app-settings-restart-notice-hidden"
)


def _validate(stats_dir: str, steam_id: str) -> tuple[str | None, str | None]:
    """Check the offline rules, returning one error per field (None when fine).

    The username is free text and has no rule. Validation is offline only by
    design: confirming a username against KovaaK's is detection territory and
    belongs to a later proposal.
    """
    stats_dir_error = (
        STATS_DIR_ERROR if stats_dir and not Path(stats_dir).is_dir() else None
    )
    # ``isascii`` guards the digit check: ``str.isdigit`` also accepts
    # superscripts and non-Latin digit forms, which no endpoint would take.
    steam_id_error = (
        STEAM_ID_ERROR
        if steam_id and not (steam_id.isascii() and steam_id.isdigit())
        else None
    )
    return stats_dir_error, steam_id_error


def _restart_notice() -> tuple[str, str]:
    """Build the notice's children and class for the current process state."""
    if not is_restart_pending():
        return "", RESTART_NOTICE_HIDDEN_CLASS
    return RESTART_NOTICE, RESTART_NOTICE_CLASS


@callback(
    Output("app-settings-stats-dir", "error"),
    Output("app-settings-steam-id", "error"),
    Output("app-settings-save-status", "children"),
    Output("app-settings-restart-notice", "children"),
    Output("app-settings-restart-notice", "className"),
    Input("app-settings-save-button", "n_clicks"),
    State("app-settings-stats-dir", "value"),
    State("app-settings-username", "value"),
    State("app-settings-steam-id", "value"),
    prevent_initial_call=True,
)
def save_user_settings(n_clicks, stats_dir, username, steam_id):
    """Validate the form, then write all three keys or none of them.

    All-or-nothing: any field-level error writes nothing, so a save never
    leaves the store holding half a form. On success every key is written —
    empty string for a cleared field — which keeps the cleared-versus-never-set
    distinction the ``stats_dir`` bootstrap will rely on, and cold-starts the
    warmup worker that boot skipped when there was no username to serve.

    Guard on ``n_clicks``: under DashProxy a callback can still fire once on
    initial page load despite ``prevent_initial_call``, and this one writes to
    disk.
    """
    if not n_clicks or ctx.triggered_id != "app-settings-save-button":
        return no_update, no_update, no_update, no_update, no_update

    stats_dir = (stats_dir or "").strip()
    username = (username or "").strip()
    steam_id = (steam_id or "").strip()

    stats_dir_error, steam_id_error = _validate(stats_dir, steam_id)
    if stats_dir_error or steam_id_error:
        return stats_dir_error, steam_id_error, "", no_update, no_update

    save_settings(
        {
            STATS_DIR_KEY: stats_dir,
            KOVAAKS_USERNAME_KEY: username,
            STEAM_ID_KEY: steam_id,
        }
    )
    logger.info("Saved user settings from the settings page")
    if username:
        # Idempotent, and correct in every pin state: it starts the worker the
        # first time an identity exists and is a no-op once one is running.
        start_percentile_warmup_worker()

    notice, notice_class = _restart_notice()
    return None, None, SAVED_STATUS, notice, notice_class


def _settings_input(
    component_id: str,
    label: str,
    description: str,
    value: str,
) -> dmc.TextInput:
    """Build one settings field, sized so a long path stays readable."""
    return dmc.TextInput(
        id=component_id,
        label=label,
        description=description,
        value=value,
        # Never a NumberInput, not even for the Steam ID: a SteamID64 exceeds
        # JavaScript's exact-integer range, and a cleared NumberInput reports
        # an empty string rather than a missing value.
        w="min(40rem, 100%)",
    )


# Per Dash documentation, we should include **kwargs in case the layout receives unexpected query strings.
def layout(**kwargs):  # noqa: ARG001
    """Build the settings form from the stored values.

    Built per visit, and from the stored view rather than the pinned
    accessors, so the form always shows what is on disk — including a change
    that is waiting on a restart.
    """
    stored = get_settings()
    notice, notice_class = _restart_notice()
    return dmc.Stack(
        children=[
            dmc.Title("Settings", order=2),
            _settings_input(
                "app-settings-stats-dir",
                "Stats directory",
                STATS_DIR_DESCRIPTION,
                stored.get(STATS_DIR_KEY, ""),
            ),
            _settings_input(
                "app-settings-username",
                "KovaaK's username",
                USERNAME_DESCRIPTION,
                stored.get(KOVAAKS_USERNAME_KEY, ""),
            ),
            _settings_input(
                "app-settings-steam-id",
                "Steam ID",
                STEAM_ID_DESCRIPTION,
                stored.get(STEAM_ID_KEY, ""),
            ),
            dmc.Group(
                children=[
                    dmc.Button("Save", id="app-settings-save-button"),
                    dmc.Text("", c="dimmed", id="app-settings-save-status"),
                ],
                gap="md",
                align="center",
            ),
            dmc.Text(
                notice,
                id="app-settings-restart-notice",
                className=notice_class,
            ),
        ],
        gap="md",
    )
