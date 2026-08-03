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
from source.config.stats_dir_detection import detect_stats_dir_candidates
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

# Mantine filters an Autocomplete's options against whatever the input holds,
# which would leave a prefilled field offering only the path it already has.
# ``assets/dashMantineFunctions.js`` explains why that is the wrong default
# here; this names the replacement.
SHOW_EVERY_CANDIDATE = {"function": "allOptions"}

STATS_DIR_ERROR = "No such directory."
STEAM_ID_ERROR = "Enter a 17-digit SteamID64 — it starts with 7656119."

# The first SteamID64 of Steam's public universe: every real account ID is at
# or above it. Anything smaller with 17 digits is a typo, not an account.
STEAM_ID64_BASE = 76561197960265728
STEAM_ID64_DIGITS = 17

RESTART_NOTICE = (
    "Saved. Restart the dashboard to apply — this app is still running on the "
    "settings it started with."
)
SAVED_STATUS = "Settings saved."
SAVE_FAILED_STATUS = (
    "Could not save settings — nothing was written. See data/logs/debug.log."
)

SAVE_STATUS_CLASS = "app-settings-save-status"
SAVE_STATUS_FAILED_CLASS = f"{SAVE_STATUS_CLASS} app-settings-save-status-failed"

RESTART_NOTICE_CLASS = "app-settings-restart-notice"
# The notice ships hidden and is revealed by dropping this modifier, the same
# way the playlists page reveals its cleanup alert.
RESTART_NOTICE_HIDDEN_CLASS = (
    f"{RESTART_NOTICE_CLASS} app-settings-restart-notice-hidden"
)


def _is_steam_id64(steam_id: str) -> bool:
    """Say whether the text is shaped like a SteamID64.

    Shape only -- whether the account exists is an online question, and this
    page never asks one. The check is the range rather than digits alone
    because the realistic paste mistakes are all well-formed numbers: an
    account ID (``26448258``) or a SteamID3 fragment reads as digits and
    resolves to nobody.
    """
    # ``isascii`` guards the digit check: ``str.isdigit`` also accepts
    # superscripts and non-Latin digit forms, which no endpoint would take.
    if not (steam_id.isascii() and steam_id.isdigit()):
        return False
    return len(steam_id) == STEAM_ID64_DIGITS and int(steam_id) >= STEAM_ID64_BASE


def _validate(stats_dir: str, steam_id: str) -> tuple[str | None, str | None]:
    """Check the offline rules, returning one error per field (None when fine).

    The username is free text and has no rule. Validation is offline only by
    design: confirming a username against KovaaK's is detection territory and
    belongs to a later proposal.
    """
    stats_dir_error = (
        STATS_DIR_ERROR if stats_dir and not Path(stats_dir).is_dir() else None
    )
    steam_id_error = (
        STEAM_ID_ERROR if steam_id and not _is_steam_id64(steam_id) else None
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
    Output("app-settings-save-status", "className"),
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
        return no_update, no_update, no_update, no_update, no_update, no_update

    stats_dir = (stats_dir or "").strip()
    username = (username or "").strip()
    steam_id = (steam_id or "").strip()

    stats_dir_error, steam_id_error = _validate(stats_dir, steam_id)
    if stats_dir_error or steam_id_error:
        return (
            stats_dir_error,
            steam_id_error,
            "",
            SAVE_STATUS_CLASS,
            no_update,
            no_update,
        )

    try:
        save_settings(
            {
                STATS_DIR_KEY: stats_dir,
                KOVAAKS_USERNAME_KEY: username,
                STEAM_ID_KEY: steam_id,
            }
        )
    except OSError:
        # A locked or unwritable file leaves the store exactly as it was (the
        # write is a temp file plus an atomic replace), so the only thing left
        # to do is say so. Letting it escape would fail the request silently:
        # the form would keep whatever status it was already showing, up to and
        # including a stale "Settings saved." from an earlier save.
        logger.exception("Failed to save user settings from the settings page")
        return (
            None,
            None,
            SAVE_FAILED_STATUS,
            SAVE_STATUS_FAILED_CLASS,
            # The store is untouched, so what the notice says is still true.
            no_update,
            no_update,
        )
    logger.info("Saved user settings from the settings page")
    if username:
        # Idempotent, and correct in every pin state: it starts the worker the
        # first time an identity exists and is a no-op once one is running.
        start_percentile_warmup_worker()

    notice, notice_class = _restart_notice()
    return None, None, SAVED_STATUS, SAVE_STATUS_CLASS, notice, notice_class


# Wide enough that a deep Steam path stays readable.
_FIELD_WIDTH = "min(40rem, 100%)"


def _settings_input(
    component_id: str,
    label: str,
    description: str,
    value: str,
) -> dmc.TextInput:
    """Build one free-text settings field."""
    return dmc.TextInput(
        id=component_id,
        label=label,
        description=description,
        value=value,
        # Never a NumberInput, not even for the Steam ID: a SteamID64 exceeds
        # JavaScript's exact-integer range, and a cleared NumberInput reports
        # an empty string rather than a missing value.
        w=_FIELD_WIDTH,
    )


def _stats_dir_input(value: str, candidates: list[str]) -> dmc.Autocomplete:
    """Build the stats-directory field: free text plus detected suggestions.

    An Autocomplete rather than a Select because the candidates are hints, not
    the allowed set: a path this machine's Steam does not know about is still a
    valid answer, and with no candidates the field is exactly the text input it
    replaced. Filtering is off, so a prefilled field still offers the other
    libraries it found.
    """
    return dmc.Autocomplete(
        id="app-settings-stats-dir",
        label="Stats directory",
        description=STATS_DIR_DESCRIPTION,
        value=value,
        data=candidates,
        filter=SHOW_EVERY_CANDIDATE,
        w=_FIELD_WIDTH,
    )


# Per Dash documentation, we should include **kwargs in case the layout receives unexpected query strings.
def layout(**kwargs):  # noqa: ARG001
    """Build the settings form from the stored values.

    Built per visit, and from the stored view rather than the pinned
    accessors, so the form always shows what is on disk — including a change
    that is waiting on a restart. Stats-directory detection runs per visit too:
    it is a registry read, a couple of file reads, and a handful of directory
    probes, so the suggestions always describe the machine as it is now.
    """
    stored = get_settings()
    notice, notice_class = _restart_notice()
    return dmc.Stack(
        children=[
            dmc.Title("Settings", order=2),
            _stats_dir_input(
                stored.get(STATS_DIR_KEY, ""),
                detect_stats_dir_candidates(),
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
                    dmc.Text(
                        "",
                        id="app-settings-save-status",
                        className=SAVE_STATUS_CLASS,
                    ),
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
