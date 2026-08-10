"""Build the user-settings page at ``/settings``.

The one runtime writer of the settings store. It shows what is on disk (never
the process-pinned accessors), saves all three keys at once, and says when the
running process no longer matches what was saved.

Component ids are ``app-settings-*``: the prefix kept them clear of the bare
``settings-*`` namespace that the Scenario Performance page's graph-settings
modal owned, and it stays now that the modal is gone.
"""

import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, ctx, dcc, no_update

from source.config.identity_detection import (
    IdentityCandidate,
    IdentityDetectionResult,
    detect_identity_candidates,
)
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
from source.pages.page_title import page_title
from source.utilities.build_info import get_build_info
from source.utilities.paths import log_dir
from source.utilities.utilities import format_absolute_timestamp

logger = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path="/settings",
    title=page_title("Settings"),
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

DETECT_STATUS_CLASS = "app-settings-detect-status"

PICKER_CLASS = "app-settings-identity-picker"
# The picker ships hidden and stays hidden unless a detection produces
# something to choose between, the same modifier trick as the notice above.
PICKER_HIDDEN_CLASS = f"{PICKER_CLASS} app-settings-identity-picker-hidden"

# The only conclusive miss: every account on this machine was checked, and none
# of them owns a KovaaK's profile. There is no reverse lookup from a Steam ID,
# so manual entry really is the only path left — which is why this message is
# reserved for the one result that has ruled everything else out.
NO_MATCH_STATUS = (
    "No Steam account on this machine has a KovaaK's profile. Type your "
    "username in yourself — KovaaK's cannot look one up from a Steam ID."
)
# The same empty-handed result from a run that did not finish. Deliberately not
# the message above: an account that went unchecked may be the answer.
NOTHING_VERIFIED_STATUS = (
    "No KovaaK's profile matched the Steam accounts that could be checked."
)
DISCOVERY_FAILED_STATUS = (
    "Steam's account list could not be read, so accounts on this machine may "
    "have been missed. See data/logs/debug.log."
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


def _format_last_seen(last_access: str) -> str:
    """Render a profile's last-access stamp for a candidate's secondary line.

    KovaaK's sends UTC ISO-8601 (``2026-08-02T14:56:42.919Z``) and the app shows
    local time in the house format. A stamp that does not parse is shown exactly
    as it arrived: the date is decoration, and an unreadable one must not cost
    the user a candidate they could otherwise pick.
    """
    try:
        parsed = datetime.fromisoformat(last_access)
    except ValueError:
        return last_access
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone()
    return format_absolute_timestamp(parsed)


def _candidate_radio(candidate: IdentityCandidate) -> dmc.Radio:
    """Build one picker row: the verified name, then where it came from.

    The label is the canonical ``webapp.username`` — the value that gets saved —
    and the persona that found it is secondary, because two accounts are told
    apart by which Steam login they belong to, not by the KovaaK's name.
    """
    return dmc.Radio(
        value=candidate.steam_id,
        label=candidate.username,
        description=(
            f"Steam account {candidate.persona_name} · last seen "
            f"{_format_last_seen(candidate.last_access)}"
        ),
    )


def _picker_rows(candidates: tuple[IdentityCandidate, ...]) -> dmc.Stack:
    """Build the picker's rows in the engine's order (newest last seen first)."""
    return dmc.Stack(
        children=[_candidate_radio(candidate) for candidate in candidates],
        gap="xs",
    )


def _can_auto_fill(result: IdentityDetectionResult) -> bool:
    """Say whether one candidate is the whole answer rather than the only one seen.

    Filling needs certainty, not a majority: a run that left an account
    unchecked, or that could not read the account list, may be hiding a second
    verified account, and a wrong identity fills caches with someone else's
    ranks. Anything short of this goes to the picker.
    """
    return (
        len(result.candidates) == 1
        and result.unchecked_count == 0
        and result.discovery_complete
    )


def _unchecked_status(count: int) -> str:
    """Say how much of the machine detection could not answer for."""
    return (
        f"{count} Steam account{'' if count == 1 else 's'} could not be checked; "
        "press Detect again to retry."
    )


def _detect_status(result: IdentityDetectionResult) -> str:
    """Say what a detection found, never dressing an unfinished run as final.

    The lead says what came back and the caveats say what did not, so an
    incomplete run always reads as incomplete — the conclusive no-match message
    is only reachable when nothing was left unresolved.
    """
    parts = []
    count = len(result.candidates)
    if count:
        parts.append(
            f"Found {count} KovaaK's account{'' if count == 1 else 's'}. "
            "Choose the one to use, then Save."
        )
    elif result.unchecked_count or not result.discovery_complete:
        parts.append(NOTHING_VERIFIED_STATUS)
    else:
        parts.append(NO_MATCH_STATUS)

    if not result.discovery_complete:
        parts.append(DISCOVERY_FAILED_STATUS)
    if result.unchecked_count:
        parts.append(_unchecked_status(result.unchecked_count))
    return " ".join(parts)


@callback(
    Output("app-settings-username", "value"),
    Output("app-settings-steam-id", "value"),
    Output("app-settings-detect-status", "children"),
    Output("app-settings-identity-picker", "children"),
    Output("app-settings-identity-picker", "className"),
    Output("app-settings-identity-picker", "value"),
    Output("app-settings-identity-candidates", "data"),
    Input("app-settings-detect-button", "n_clicks"),
    # One slow-spell account can hold the probe for ~30 seconds, so the button
    # spins for the duration; Mantine's loading state also swallows clicks,
    # which keeps an impatient user from queueing more KovaaK's calls.
    running=[(Output("app-settings-detect-button", "loading"), True, False)],
    prevent_initial_call=True,
)
def detect_identity(n_clicks):
    """Check this machine's Steam accounts against KovaaK's and offer the result.

    Suggestion only: this fills inputs and never touches the store — Save stays
    the single writer. A lone certain candidate is filled in directly; anything
    less certain is offered in the picker instead, and an empty-handed run says
    which kind of empty it was.

    Guard on ``n_clicks``: under DashProxy a callback can still fire once on
    initial page load despite ``prevent_initial_call``, and this one calls
    KovaaK's.
    """
    if not n_clicks or ctx.triggered_id != "app-settings-detect-button":
        return (no_update,) * 7

    result = detect_identity_candidates()
    # Only what the picker needs to fill the form. The personas and stamps stay
    # in the rendered rows: nothing about an account the user never picks is
    # worth shipping to the browser twice.
    stored = [
        {"username": candidate.username, "steam_id": candidate.steam_id}
        for candidate in result.candidates
    ]

    if _can_auto_fill(result):
        candidate = result.candidates[0]
        return (
            candidate.username,
            candidate.steam_id,
            f"Found {candidate.username}. Save to apply it.",
            _picker_rows(()),
            PICKER_HIDDEN_CLASS,
            None,
            stored,
        )

    return (
        no_update,
        no_update,
        _detect_status(result),
        _picker_rows(result.candidates),
        PICKER_CLASS if result.candidates else PICKER_HIDDEN_CLASS,
        # A fresh detection clears the old selection, so picking the same
        # account again is still a change the pick callback sees.
        None,
        stored,
    )


@callback(
    Output("app-settings-username", "value", allow_duplicate=True),
    Output("app-settings-steam-id", "value", allow_duplicate=True),
    Input("app-settings-identity-picker", "value"),
    State("app-settings-identity-candidates", "data"),
    prevent_initial_call=True,
)
def use_detected_identity(steam_id, candidates):
    """Fill the identity fields from the picked candidate. Save applies it.

    The candidates come from the store rather than from a second detection, so
    a pick costs no KovaaK's calls and always fills what the user was shown.
    Guarded like every other state-changing callback here, because clearing the
    picker also arrives as a value change.
    """
    if not steam_id or ctx.triggered_id != "app-settings-identity-picker":
        return no_update, no_update

    for candidate in candidates or []:
        if candidate.get("steam_id") == steam_id:
            return candidate.get("username", ""), steam_id
    return no_update, no_update


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


# Spelled here rather than reused from ``api_service.PROJECT_URL``: that one is
# the contact point stamped into the User-Agent, and a settings page has no
# business importing the KovaaK's client to render a link.
ISSUES_URL = "https://github.com/MingoDynasty/Corporate-Serf-Dashboard/issues/new"
# The filename of the merged issue form. GitHub pre-fills a form's fields from
# query params named after their field ids, so this and ``version`` below are
# both contracts with ``.github/ISSUE_TEMPLATE/bug_report.yml``.
BUG_REPORT_TEMPLATE = "bug_report.yml"


def bug_report_url(release_label: str) -> str:
    """Build the pre-filled "Report a bug" link for the running build.

    Every label the resolver can produce is pre-filled, ``dev`` and ``unknown``
    included: the form requires the version field, the value is editable, and
    "unknown" is itself the honest answer for a build nothing could identify.
    """
    query = urlencode({"template": BUG_REPORT_TEMPLATE, "version": release_label})
    return f"{ISSUES_URL}?{query}"


def _version_section() -> dmc.Stack:
    """Name the running build, then offer the two things a bug report needs.

    Static text read straight off ``BuildInfo`` — the identity is resolved once
    per process by one reader, and nothing here re-derives any part of it. It
    answers "which version am I running?" after an update, and the link beside
    it carries that same label into the report, so nobody has to transcribe it.
    The log directory is shown for the same reason: the form asks for
    ``debug.log``, and this names where to find it.
    """
    build = get_build_info()
    return dmc.Stack(
        children=[
            dmc.Text(f"Version {build.release_label}", id="app-settings-version"),
            dmc.Text(
                f"Commit {build.short_description}",
                id="app-settings-build",
                c="dimmed",
                size="sm",
            ),
            dmc.Anchor(
                "Report a bug",
                id="app-settings-bug-report",
                href=bug_report_url(build.release_label),
                target="_blank",
                size="sm",
                # A Stack child stretches, and a full-width anchor makes the
                # whole empty row a click target.
                w="fit-content",
            ),
            dmc.Text(
                f"Logs {log_dir()}",
                id="app-settings-log-dir",
                c="dimmed",
                size="sm",
            ),
        ],
        gap="xs",
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


def _identity_detection() -> dmc.Stack:
    """Build the Detect control, its status line, and the picker it may fill.

    All three ship empty: identity detection costs KovaaK's calls, so it runs
    behind the button and never on a render path. The picker stays hidden until
    a detection produces something to choose between.
    """
    return dmc.Stack(
        children=[
            dmc.Group(
                children=[
                    dmc.Button(
                        "Detect",
                        id="app-settings-detect-button",
                        # Secondary to Save, which is the only button here that
                        # changes anything.
                        variant="default",
                    ),
                    dmc.Text(
                        "",
                        id="app-settings-detect-status",
                        className=DETECT_STATUS_CLASS,
                    ),
                ],
                gap="md",
                align="center",
            ),
            dmc.RadioGroup(
                id="app-settings-identity-picker",
                children=[],
                label="Detected KovaaK's accounts",
                description="Choosing one fills the fields above; Save applies it.",
                className=PICKER_HIDDEN_CLASS,
            ),
            # What the picker's rows mean, so a pick needs no second detection.
            dcc.Store(id="app-settings-identity-candidates"),
        ],
        gap="sm",
    )


# Per Dash documentation, we should include **kwargs in case the layout receives unexpected query strings.
def layout(**kwargs):  # noqa: ARG001
    """Build the settings form from the stored values.

    Built per visit, and from the stored view rather than the pinned
    accessors, so the form always shows what is on disk — including a change
    that is waiting on a restart. Stats-directory detection runs per visit too:
    it is a registry read, a couple of file reads, and a handful of directory
    probes, so the suggestions always describe the machine as it is now.
    Identity detection does not: it calls KovaaK's, so opening the page never
    costs a request and the Detect button is the only thing that spends one.
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
            _identity_detection(),
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
            dmc.Divider(),
            _version_section(),
        ],
        gap="md",
    )
