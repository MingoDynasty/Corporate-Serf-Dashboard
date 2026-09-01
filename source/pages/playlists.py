"""Playlist-level overview page at the playlists landing route."""

import logging

import dash
import dash_ag_grid as dag
import dash_mantine_components as dmc
from dash import (
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    ctx,
    dcc,
    no_update,
)

from source.components.local_icon import local_icon
from source.config.settings_service import get_kovaaks_username
from source.kovaaks.data_service import (
    delete_superseded_user_playlist_files,
    delete_user_playlist,
    get_playlist_display_label,
    get_superseded_user_playlist_files,
    get_user_root_playlist_codes,
    load_playlist_from_code,
)
from source.kovaaks.percentile_warmup_service import (
    PercentileWarmupSnapshot,
    enqueue_playlist_percentile_warmup,
    get_percentile_warmup_state,
)
from source.kovaaks.playlist_overview_service import build_playlist_overview_rows
from source.kovaaks.playlist_visibility_service import (
    get_visibility_store_message,
    hide_playlist,
    is_playlist_shown,
    show_playlist,
    toggle_playlist_visibility,
)
from source.pages.page_title import page_title
from source.utilities.notifications import (
    TOAST_CHANNEL_REGISTRY_STORE_ID,
    channel_toast,
    toast,
)
from source.utilities.store_schema import UnsupportedSchemaError
from source.utilities.utilities import format_approximate_duration

logger = logging.getLogger(__name__)

VISIBILITY_COLUMN_ID = "hidden"
# The delete action cell's colId. Matches the ``deletable`` row flag so the
# renderer can hide itself on bundled rows; excluded from row navigation.
DELETE_COLUMN_ID = "deletable"
WARMUP_REFRESH_INTERVAL_MS = 1_000

# Reused from the former Settings-modal import control, with the trailing
# clause reworded for the overview: importing here lands the playlist as a new
# visible row on this management surface.
IMPORT_HELP_TEXT = (
    "Paste a KovaaK's playlist share code and press Import to add that "
    "playlist to this list."
)

# Appended to a duplicate-code refusal when the conflicting playlist exists but
# is hidden (R14): the code "already exists" but the user cannot see it, so
# point them at the toggle that surfaces it.
HIDDEN_DUPLICATE_HINT = (
    ' It is currently hidden — toggle "Show hidden" on this page to unhide it.'
)

# Appended to the import toast when the playlist file landed but the visibility
# write failed. The import itself succeeded, so the message must say so and then
# name the one thing that did not happen, plus its recovery: the new code is
# absent from the shown set, so its row renders as hidden and "Show hidden" is
# what surfaces it before the eye toggle can be clicked.
IMPORT_VISIBILITY_FAILED_HINT = (
    " It could not be marked visible, so it may be missing from playlist"
    ' selectors — toggle "Show hidden" on this page, then click its row\'s eye'
    " icon to show it."
)

# Shown when a show/hide is refused because the visibility file belongs to a
# newer build. Nothing was written and nothing changed, so the toast is the
# whole report: without it the click would fail the Dash request silently.
VISIBILITY_REFUSED_TITLE = "Show and hide are unavailable"

# This page's toast channels. The three problem lanes are single-identity: a
# retry against the same input reproduces the same message, and the policy
# replaces identical copy rather than stacking it. The outcome lanes are keyed
# by canonical playlist code, so two playlists in flight stack side by side
# while the supported delete-then-re-import cycle replaces one playlist's own
# toast. Never key by the pasted input, which can differ in case.
VISIBILITY_REFUSED_CHANNEL = "visibility-refused-notification"
IMPORT_FAILED_CHANNEL = "imported-playlist-failed-notification"
DELETE_FAILED_CHANNEL = "deleted-playlist-failed-notification"
CLEANUP_FAILED_CHANNEL = "superseded-cleanup-failed-notification"
# Constant copy ("Leftover files deleted"), so a second cleanup would stack a
# byte-identical toast. Classified by what can recur, not by how likely it is.
CLEANUP_SUCCESSFUL_CHANNEL = "superseded-cleanup-successful-notification"


def import_successful_channel(playlist_code: str) -> str:
    """Name the import-success channel for one canonical playlist code."""
    return f"imported-playlist-successful-{playlist_code}"


def import_visibility_failed_channel(playlist_code: str) -> str:
    """Name the split-outcome import channel for one canonical code."""
    return f"imported-playlist-visibility-failed-{playlist_code}"


def delete_successful_channel(playlist_code: str) -> str:
    """Name the delete-success channel for one canonical playlist code."""
    return f"deleted-playlist-successful-{playlist_code}"


VISIBILITY_ALERT_TITLE = "Playlist visibility is not being used"
# The alert ships hidden and the render callback drops this modifier, the same
# way the leftover-files notice below it works.
VISIBILITY_ALERT_HIDDEN_CLASS = "playlists-visibility-alert-hidden"

SUPERSEDED_NOTICE_TITLE = "Leftover playlist files"
# The leftover-files notice holds a button, so it wears the alert anatomy on a
# ``dmc.Paper`` instead of being a ``dmc.Alert``: the component's ``role=alert``
# is for text content, and it would assertively interrupt for an optional bit of
# housekeeping the announcement cannot act on. Blue, because the bundled copy
# already won and nothing is broken.
SUPERSEDED_NOTICE_CLASS = "alert-panel"
SUPERSEDED_NOTICE_HIDDEN_CLASS = (
    f"{SUPERSEDED_NOTICE_CLASS} playlists-superseded-alert-hidden"
)

dash.register_page(
    __name__,
    path="/playlists",
    title=page_title("Playlists"),
)

AUTO_SIZE_COLUMN_KEYS = [
    "type_display",
    "played_sort",
    "runs_sort",
    "last_played_sort",
    "median_percentile_sort",
    "lowest_percentile_sort",
]

COLUMN_SIZE_OPTIONS: dag.AgGrid.ColumnSizeOptions = {
    "keys": AUTO_SIZE_COLUMN_KEYS,
    "skipHeader": False,
}

# Two-line tooltip: the exact-timestamp convention on line one, and the
# playlist's most neglected scenario on line two (rendered by the pre-line
# tooltip rule in stylesheet.css). The stalest age is computed at hover time so
# it never goes stale on a long-lived page.
LAST_PLAYED_TOOLTIP = (
    "params.value == null ? null : (absoluteTime(params.value, 'Never')"
    " + (params.data.stalest_scenario == null ? '' : '\\nStalest: '"
    " + params.data.stalest_scenario + ', '"
    " + relativeTime(params.data.stalest_sort, 'Never')))"
)

PERCENTILE_PLACEHOLDER_TOOLTIP = (
    "('Shown once all ' + params.data.played_count"
    " + ' played scenarios have data — open the playlist to fetch now')"
)

PERCENTILE_TOOLTIP = (
    "params.data.percentile_aggregates_resolved ? null : "
    f"{PERCENTILE_PLACEHOLDER_TOOLTIP}"
)

LOWEST_PERCENTILE_TOOLTIP = (
    "params.data.percentile_aggregates_resolved"
    " ? (params.value == null ? null : ('Lowest: '"
    " + params.data.lowest_scenario))"
    f" : {PERCENTILE_PLACEHOLDER_TOOLTIP}"
)

PERCENTILE_CELL_CLASS = (
    "params.data.percentile_aggregates_resolved"
    " ? null : 'playlist-overview-percentile-placeholder'"
)

# Unlike Median, a resolved Lowest value carries hover-only detail (which
# scenario is the weakest), so it gets the shared dotted-underline affordance.
LOWEST_PERCENTILE_CELL_CLASS = (
    "params.data.percentile_aggregates_resolved"
    " ? (params.value == null ? null : 'cell-tooltip-affordance')"
    " : 'playlist-overview-percentile-placeholder'"
)

# The eye toggle acts immediately with no confirm step, so the hover copy
# carries the action and its consequence.
VISIBILITY_TOOLTIP = (
    "params.data.hidden"
    " ? 'Show this playlist again in the overview and playlist selectors'"
    " : 'Hide this playlist from the overview and playlist selectors'"
)

# The delete icon carries no text label, so the tooltip supplies the click
# consequence. Bundled rows render no icon; return null there so no tooltip
# shows on the empty cell.
DELETE_TOOLTIP = "params.data.deletable ? 'Delete this playlist' : null"

TABLE_COLUMN_DEFS = [
    {
        "headerName": "Playlist",
        "field": "name",
        # Real anchor to /playlists/<code> (built client-side from the row's
        # share code). Whole-row click nav still works; the anchor adds
        # new-tab / copy-link affordances a server-callback nav can't.
        "cellRenderer": "PlaylistNameLink",
        "sortable": True,
        "flex": 1,
        "minWidth": 280,
        "maxWidth": 420,
    },
    {
        "headerName": "Type",
        "field": "type_display",
        "headerTooltip": (
            "Benchmarks carry rank thresholds (Bronze, Silver, ...) for their "
            "scenarios; playlists are plain scenario lists."
        ),
        "cellRenderer": "TypeBadge",
        "sortable": True,
        # Wide enough for the BENCHMARK pill plus cell padding: autoSize can
        # run before rows arrive, leaving the column at this floor, and 110
        # ellipsized the badge.
        "minWidth": 140,
    },
    {
        "headerName": "Played",
        "field": "played_sort",
        "headerTooltip": "Scenarios played / total scenarios",
        "valueFormatter": {"function": "params.data.played_display"},
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 90,
    },
    {
        "headerName": "Runs",
        "field": "runs_sort",
        "valueFormatter": {"function": "params.data.runs_display"},
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 80,
    },
    {
        "headerName": "Last Played",
        "field": "last_played_sort",
        # Default sort: the staleness view is the page's purpose — active
        # playlists float up, "Never" stays last (nullsLastComparator handles
        # both sort directions).
        "sort": "desc",
        "valueFormatter": {"function": "relativeTime(params.value, 'Never')"},
        "tooltipValueGetter": {"function": LAST_PLAYED_TOOLTIP},
        "cellClass": {
            "function": "params.value == null ? null : 'cell-tooltip-affordance'"
        },
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 130,
    },
    {
        "headerName": "Median Percentile",
        "field": "median_percentile_sort",
        "headerTooltip": (
            "Median leaderboard percentile across ranked scenarios you have "
            "played. Shown once every played scenario has enough cached "
            "leaderboard data."
        ),
        "valueFormatter": {"function": "params.data.median_percentile_display"},
        "tooltipValueGetter": {"function": PERCENTILE_TOOLTIP},
        "cellClass": {"function": PERCENTILE_CELL_CLASS},
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 160,
    },
    {
        "headerName": "Lowest Percentile",
        "field": "lowest_percentile_sort",
        "headerTooltip": (
            "The weakest leaderboard percentile among ranked scenarios you "
            "have played. Shown once every played scenario has enough cached "
            "leaderboard data; hover a value to see which scenario."
        ),
        "valueFormatter": {"function": "params.data.lowest_percentile_display"},
        "tooltipValueGetter": {"function": LOWEST_PERCENTILE_TOOLTIP},
        "cellClass": {"function": LOWEST_PERCENTILE_CELL_CLASS},
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 160,
    },
    {
        # Hide/unhide action cell. Its colId is excluded from row navigation,
        # and the row-load callback treats clicks on it as visibility toggles.
        "headerName": "",
        "field": VISIBILITY_COLUMN_ID,
        "cellRenderer": "VisibilityAction",
        "tooltipValueGetter": {"function": VISIBILITY_TOOLTIP},
        "sortable": False,
        "resizable": False,
        "minWidth": 90,
        "maxWidth": 100,
    },
    {
        # Delete action cell (user playlists only; the renderer draws nothing
        # on bundled rows). Its colId is excluded from row navigation, and a
        # click opens the delete confirmation modal.
        "headerName": "",
        "field": DELETE_COLUMN_ID,
        "cellRenderer": "DeleteAction",
        "tooltipValueGetter": {"function": DELETE_TOOLTIP},
        "sortable": False,
        "resizable": False,
        "minWidth": 90,
        "maxWidth": 100,
    },
]


@callback(
    Output("playlists-location", "pathname"),
    Input("playlists-overview-grid", "cellClicked"),
    prevent_initial_call=True,
)
def route_to_clicked_playlist(cell_clicked):
    """Navigate to a playlist's scenario table from any cell in its row."""
    if not isinstance(cell_clicked, dict):
        return no_update
    if cell_clicked.get("colId") in (VISIBILITY_COLUMN_ID, DELETE_COLUMN_ID):
        return no_update
    playlist_code = cell_clicked.get("rowId")
    if not isinstance(playlist_code, str) or not playlist_code:
        return no_update
    return f"/playlists/{playlist_code}"


@callback(
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Output("notification-container", "hideNotifications", allow_duplicate=True),
    Output(TOAST_CHANNEL_REGISTRY_STORE_ID, "data", allow_duplicate=True),
    Output("playlists-rows-refresh", "data", allow_duplicate=True),
    Input("playlists-overview-grid", "cellClicked"),
    State("playlists-rows-refresh", "data"),
    State(TOAST_CHANNEL_REGISTRY_STORE_ID, "data"),
    prevent_initial_call=True,
)
def update_playlist_visibility(cell_clicked, rows_refresh, toast_channels):
    """Toggle one visibility cell and wake warmup work after an unhide.

    A refusal (the visibility file belongs to a newer build) reports through a
    toast and leaves the rows alone: nothing was written, so rebuilding them
    would only redraw the state the user just tried to change. The refusal is a
    channel, so a second click on the same cell re-pops the same answer rather
    than reading as a dead toggle. An ordinary write failure still propagates
    untouched — see the PR #183 rule pinned in the tests.
    """
    if (
        ctx.triggered_id != "playlists-overview-grid"
        or not isinstance(cell_clicked, dict)
        or cell_clicked.get("colId") != VISIBILITY_COLUMN_ID
        or not isinstance(cell_clicked.get("rowId"), str)
        or not cell_clicked["rowId"]
    ):
        return no_update, no_update, no_update, no_update

    playlist_code = cell_clicked["rowId"]
    try:
        unhidden = toggle_playlist_visibility(playlist_code)
    except UnsupportedSchemaError as exc:
        logger.warning("Refused to change playlist visibility: %s", exc)
        notification = toast(
            VISIBILITY_REFUSED_CHANNEL,
            VISIBILITY_REFUSED_TITLE,
            str(exc),
            color="red",
            icon=local_icon("material-symbols:warning-outline"),
        )
        return *channel_toast(notification, toast_channels), no_update
    if unhidden:
        enqueue_playlist_percentile_warmup(playlist_code)
    # Hides need an ordinary row rebuild. Unhides additionally need this
    # explicit bump so the disabled warmup interval's owner observes the new
    # enqueue generation and re-arms it.
    return no_update, no_update, no_update, (rows_refresh or 0) + 1


@callback(
    Output("playlists-overview-grid", "rowData"),
    Output("playlists-overview-status", "children"),
    Output("playlists-overview-warmup-interval", "disabled"),
    Output("playlists-overview-warmup-status", "children"),
    Output("playlists-overview-warmup-generation", "data"),
    Input("playlists-overview-mounted", "data"),
    Input("playlists-overview-show-hidden", "checked"),
    Input("playlists-rows-refresh", "data"),
    Input("playlists-overview-warmup-interval", "n_intervals"),
    State("playlists-overview-warmup-generation", "data"),
)
def load_playlist_overview_rows(
    _mounted,
    show_hidden,
    _rows_refresh,
    _warmup_tick,
    observed_generation,
):
    """Snapshot warmup state, then build cache-only rows before disabling."""
    warmup_outputs = _playlist_overview_warmup_state(observed_generation)
    record_activity = ctx.triggered_id != "playlists-overview-warmup-interval"
    rows = build_playlist_overview_rows(
        include_hidden=bool(show_hidden),
        record_activity=record_activity,
    )
    if not rows:
        if build_playlist_overview_rows(
            include_hidden=True,
            record_activity=record_activity,
        ):
            return (
                [],
                'All playlists are hidden. Toggle "Show hidden" to manage them.',
                *warmup_outputs,
            )
        return [], "No playlists are loaded.", *warmup_outputs
    # Rows exist, so the empty-grid messages above have nothing to say and the
    # slot is free for the one condition that silently empties both percentile
    # columns.
    if not get_kovaaks_username():
        return rows, _username_unset_status(), *warmup_outputs
    return rows, "", *warmup_outputs


def _username_unset_status() -> list:
    """State the unset-username condition in the overview's status line.

    Mirrors the playlist scenarios page one level up: with no username every
    rank lookup short-circuits offline, so both percentile columns read N/A on
    every row with nothing on screen to explain it. That is persistent
    configuration state, not a failure.

    Built fresh per call rather than shared at module scope: the value is a
    callback output, and a mutable component list must not be reused across
    requests.
    """
    return [
        "Percentiles unavailable. Set your KovaaK's username in ",
        dmc.Anchor("Settings", href="/settings", refresh=False),
        ".",
    ]


def _format_retry_time(snapshot: PercentileWarmupSnapshot) -> str:
    """Render the worker's UTC deadline in the desktop's local time."""
    if snapshot.paused_until is None:
        return ""
    return snapshot.paused_until.astimezone().strftime("%I:%M %p").lstrip("0")


def _format_warmup_status(snapshot: PercentileWarmupSnapshot) -> str:
    if snapshot.fatal_state:
        return f"Percentile update stopped: {snapshot.fatal_state}"
    if not snapshot.remaining_count:
        return ""

    status = f"Updating percentile data: {snapshot.remaining_count} remaining"
    if snapshot.paused_until is not None:
        return f"{status} · paused; retrying at {_format_retry_time(snapshot)}"
    if snapshot.recent_pace_seconds is not None:
        eta = snapshot.remaining_count * snapshot.recent_pace_seconds
        status += f" (~{format_approximate_duration(eta)})"
    return status


def _playlist_overview_warmup_state(observed_generation):
    """Compute interval outputs before the caller's sequenced row rebuild."""
    snapshot = get_percentile_warmup_state()
    observed_generation = (
        observed_generation if isinstance(observed_generation, int) else 0
    )

    # A callback response based on an older snapshot must never disable an
    # interval that has already observed and re-armed for a newer enqueue.
    if snapshot.enqueue_generation < observed_generation:
        return False, no_update, observed_generation

    busy = bool(snapshot.queued_names) or snapshot.in_flight is not None
    new_generation = snapshot.enqueue_generation > observed_generation
    disabled = not (busy or new_generation)
    if snapshot.fatal_state:
        disabled = True
    return disabled, _format_warmup_status(snapshot), snapshot.enqueue_generation


@callback(
    Output("playlists-import-modal", "opened"),
    Input("playlists-import-open-button", "n_clicks"),
    State("playlists-import-modal", "opened"),
    prevent_initial_call=True,
)
def toggle_import_modal(_, opened):
    """Open or close the share-code import modal."""
    return not opened


@callback(
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Output("notification-container", "hideNotifications", allow_duplicate=True),
    Output(TOAST_CHANNEL_REGISTRY_STORE_ID, "data", allow_duplicate=True),
    Output("playlists-rows-refresh", "data"),
    Output("playlists-import-modal", "opened", allow_duplicate=True),
    Output("playlists-import-textinput", "value"),
    Output("playlists-import-textinput", "error"),
    Input("playlists-import-button", "n_clicks"),
    State("playlists-import-textinput", "value"),
    State("playlists-rows-refresh", "data"),
    State(TOAST_CHANNEL_REGISTRY_STORE_ID, "data"),
    # The Import button spins (and, via Mantine's loading state, refuses further
    # clicks) for the duration of the fetch. The playlist search is the
    # timeout-prone endpoint, so a slow import can hang for tens of seconds; the
    # spinner is the whole loading design and the disable covers spam-clicks.
    running=[(Output("playlists-import-button", "loading"), True, False)],
    prevent_initial_call=True,
)
def import_playlist(n_clicks, playlist_to_import, rows_refresh, toast_channels):
    """Import a playlist code and surface the result on this page.

    Reuses the shared import service path. On success the playlist is marked
    visible ("importing is the intent to see"), the refresh store is bumped so
    the overview rebuilds and shows the new row without a page reload, and the
    modal closes with a cleared field so the user sees that new row. A refusal
    leaves the modal open with the pasted code intact so the user can correct
    it; a duplicate-code refusal whose conflicting playlist is hidden gets the
    unhide hint appended (R14).

    An empty or whitespace-only submit is a local validation problem, not an
    event, so it sets an inline field error rather than sending a notification;
    any non-empty submit clears that error. The phantom initial fire (guarded
    on ``ctx.triggered_id``/``n_clicks``) must leave the error untouched.

    A failed visibility write does not fail the import: the playlist file is
    already on disk, so the toast turns orange and reports the split outcome
    rather than vanishing (see the 2026-08-02 committed-side-effect entry in
    ``docs/decision_log.md``).

    Both landing outcomes clear the failure channel: it claims to report the
    latest attempt, so a corrected retry must not leave the red refusal beside
    the toast that answers it.
    """
    if ctx.triggered_id != "playlists-import-button" or not n_clicks:
        return (
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
        )
    playlist_to_import = (playlist_to_import or "").strip()
    if not playlist_to_import:
        # Inline field error, not a notification: this is a local validation
        # problem. Touch nothing else so the modal and field stay as they are.
        return (
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            "Enter a playlist code.",
        )
    logger.debug("Importing playlist '%s'", playlist_to_import)
    error_message, canonical_code = load_playlist_from_code(playlist_to_import)

    if error_message:
        # The refusal branch can carry the conflicting existing code; if that
        # playlist is hidden, tell the user where to find it.
        if canonical_code is not None and not is_playlist_shown(canonical_code):
            error_message += HIDDEN_DUPLICATE_HINT
        notification = toast(
            IMPORT_FAILED_CHANNEL,
            "Playlist import failed",
            error_message,
            color="red",
            icon=local_icon("material-symbols:upload"),
        )
        return (
            *channel_toast(notification, toast_channels),
            no_update,
            no_update,
            no_update,
            None,
        )

    # Importing is the intent to see: new playlists arrive visible. Mark the
    # canonical stored code, which can differ from the pasted input. The
    # is-not-None guard is defensive; the service contract guarantees a code
    # here, but never persist a None into the shown-set if that ever changes.
    visibility_write_failed = False
    if canonical_code is not None:
        try:
            show_playlist(canonical_code)
        except OSError, UnsupportedSchemaError:
            # The playlist file is already written — an irreversible step that
            # succeeded — so failing the request here would leave the user with
            # no report at all for something that happened. Report the split
            # outcome instead. The store is untouched (temp file plus atomic
            # replace, and a newer-stamped file is never written at all), so
            # the code is simply absent from the shown set.
            logger.exception(
                "Failed to mark imported playlist '%s' as shown", canonical_code
            )
            visibility_write_failed = True
        # Outside the try: the playlist file exists either way, so warm it.
        enqueue_playlist_percentile_warmup(canonical_code)
    # Name the imported playlist using the canonical stored code (never the
    # pasted input, which can differ in case) so the toast confirms exactly
    # what landed. The fallback mirrors the guard above: the service contract
    # guarantees a code here, but never render a "None" into the toast — or
    # pass one to the str-typed label lookup — if that ever changes.
    imported_code = canonical_code if canonical_code is not None else playlist_to_import
    label = get_playlist_display_label(imported_code)
    imported_message = f'Imported "{label}" ({imported_code}).'
    if visibility_write_failed:
        notification = toast(
            import_visibility_failed_channel(imported_code),
            "Playlist imported — not shown",
            imported_message + IMPORT_VISIBILITY_FAILED_HINT,
            color="orange",
            icon=local_icon("material-symbols:upload"),
        )
    else:
        notification = toast(
            import_successful_channel(imported_code),
            "Playlist imported",
            imported_message,
            color="green",
            icon=local_icon("material-symbols:upload"),
        )
    # Every other output matches the success path: the import happened, so the
    # grid rebuilds and the modal closes with a cleared field either way.
    return (
        *channel_toast(notification, toast_channels, clears=(IMPORT_FAILED_CHANNEL,)),
        (rows_refresh or 0) + 1,
        False,
        "",
        None,
    )


@callback(
    Output("playlists-delete-modal", "opened"),
    Output("playlists-delete-target", "data"),
    Output("playlists-delete-message", "children"),
    Input("playlists-overview-grid", "cellClicked"),
    Input("playlists-delete-cancel-button", "n_clicks"),
    prevent_initial_call=True,
)
def manage_delete_modal(cell_clicked, _cancel):
    """Open the delete confirmation modal for a clicked delete cell, or cancel.

    A click on the delete action cell opens the modal naming the target
    playlist; the Cancel button (or the modal's own close control) closes it.
    Deletion itself is confirmed by ``confirm_delete_playlist``.
    """
    if ctx.triggered_id == "playlists-delete-cancel-button":
        return False, no_update, no_update
    if (
        not isinstance(cell_clicked, dict)
        or cell_clicked.get("colId") != DELETE_COLUMN_ID
        or not isinstance(cell_clicked.get("rowId"), str)
        or not cell_clicked["rowId"]
    ):
        return no_update, no_update, no_update
    playlist_code = cell_clicked["rowId"]
    # Bundled rows render no Delete link, but their (empty) delete cell still
    # emits cellClicked with this colId. Refuse non-user codes here — same
    # source of truth as the row's ``deletable`` flag — so a bundled row can
    # never open a misleading delete-confirm dialog (delete_user_playlist
    # would refuse it anyway, but only after a scare).
    if playlist_code not in get_user_root_playlist_codes():
        return no_update, no_update, no_update
    label = get_playlist_display_label(playlist_code)
    message = (
        f'Delete "{label}" ({playlist_code})? You can re-import it later by share code.'
    )
    return True, playlist_code, message


@callback(
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Output("notification-container", "hideNotifications", allow_duplicate=True),
    Output(TOAST_CHANNEL_REGISTRY_STORE_ID, "data", allow_duplicate=True),
    Output("playlists-rows-refresh", "data", allow_duplicate=True),
    Output("playlists-delete-modal", "opened", allow_duplicate=True),
    Input("playlists-delete-confirm-button", "n_clicks"),
    State("playlists-delete-target", "data"),
    State("playlists-rows-refresh", "data"),
    State(TOAST_CHANNEL_REGISTRY_STORE_ID, "data"),
    prevent_initial_call=True,
)
def confirm_delete_playlist(n_clicks, target_code, rows_refresh, toast_channels):
    """Delete the confirmed user playlist, then rebuild the grid.

    On failure the red notification carries the service's message and the grid
    is left untouched. On success the visibility membership is dropped too
    (in a show-list, forgetting a code IS removing its membership — this keeps
    playlist_visibility.json from accumulating dead codes) and the refresh store bumps
    so the deleted row disappears without a page reload. A failed visibility
    write is logged and otherwise ignored: the delete is what the toast reports
    (see the 2026-08-02 committed-side-effect entry in ``docs/decision_log.md``).
    Success clears the failure channel, so a retry that lands does not leave the
    red toast standing beside the green one.

    Guard on ``n_clicks``: under DashProxy an ``allow_duplicate`` callback can
    still fire once on initial page load despite ``prevent_initial_call``, so a
    destructive handler must confirm a real button click (a fresh load has
    ``n_clicks`` None and no target) before touching the filesystem.
    """
    if not n_clicks or not target_code:
        return no_update, no_update, no_update, no_update, no_update
    # Look up the label before the delete: afterwards the code is gone from
    # the playlist database and the lookup falls back to the raw code.
    label = get_playlist_display_label(target_code)
    error_message = delete_user_playlist(target_code)
    if error_message:
        notification = toast(
            DELETE_FAILED_CHANNEL,
            "Playlist delete failed",
            error_message,
            color="red",
        )
        return *channel_toast(notification, toast_channels), no_update, False
    try:
        hide_playlist(target_code)
    except OSError, UnsupportedSchemaError:
        # Membership bookkeeping only, and it has no observable consequence: the
        # row is gone either way, a dead code renders nowhere, and a later
        # re-import early-returns on the still-shown code. So log it and still
        # report the delete — the outcome the user actually asked about, and
        # which has already committed. Failing the request instead would show
        # nothing, and the natural retry deletes an absent file and renders a
        # red "delete failed" toast for a delete that succeeded.
        logger.exception(
            "Failed to drop deleted playlist '%s' from the shown set", target_code
        )
    notification = toast(
        delete_successful_channel(target_code),
        "Playlist deleted",
        f'Deleted "{label}" ({target_code}).',
        color="green",
    )
    return (
        *channel_toast(notification, toast_channels, clears=(DELETE_FAILED_CHANNEL,)),
        (rows_refresh or 0) + 1,
        False,
    )


@callback(
    Output("playlists-visibility-alert", "className"),
    Output("playlists-visibility-text", "children"),
    Input("playlists-overview-mounted", "data"),
    Input("playlists-rows-refresh", "data"),
)
def render_visibility_alert(_mounted, _rows_refresh):
    """Say when the visibility file is not the one driving these rows.

    An unusable visibility store falls back to the first-run seed, which looks
    exactly like a fresh install: every bundled benchmark visible, the user's
    own choices silently gone. This is the only place that difference is
    visible, so it renders on every visit and after every row refresh rather
    than as a toast that scrolls away.
    """
    message = get_visibility_store_message()
    if not message:
        return VISIBILITY_ALERT_HIDDEN_CLASS, ""
    return "", message


@callback(
    Output("playlists-superseded-alert", "className"),
    Output("playlists-superseded-text", "children"),
    Input("playlists-overview-mounted", "data"),
    Input("playlists-rows-refresh", "data"),
)
def render_superseded_alert(_mounted, _rows_refresh):
    """Show the cleanup alert only while superseded user files remain.

    The recorded list is refreshed on each ``load_playlists()`` run and pruned
    as files are deleted, so the alert re-renders (and hides) whenever the
    refresh store bumps after a cleanup.
    """
    superseded_files = get_superseded_user_playlist_files()
    if not superseded_files:
        return SUPERSEDED_NOTICE_HIDDEN_CLASS, ""
    count = len(superseded_files)
    noun = "file" if count == 1 else "files"
    verb = "is" if count == 1 else "are"
    message = (
        f"{count} leftover playlist {noun} in data/playlists {verb} superseded "
        "by bundled benchmarks."
    )
    return SUPERSEDED_NOTICE_CLASS, message


@callback(
    Output("playlists-superseded-modal", "opened"),
    Output("playlists-superseded-message", "children"),
    Input("playlists-superseded-delete-button", "n_clicks"),
    Input("playlists-superseded-cancel-button", "n_clicks"),
    prevent_initial_call=True,
)
def manage_superseded_modal(_delete, _cancel):
    """Open the confirm modal for the superseded-file cleanup, or cancel it.

    Keyed off ``ctx.triggered_id`` (not a bare else) so an initial-load fire —
    where the triggered id is None — cannot pop the modal open unbidden.
    """
    if ctx.triggered_id == "playlists-superseded-cancel-button":
        return False, no_update
    if ctx.triggered_id != "playlists-superseded-delete-button":
        return no_update, no_update
    superseded_files = get_superseded_user_playlist_files()
    if not superseded_files:
        return no_update, no_update
    count = len(superseded_files)
    noun = "file" if count == 1 else "files"
    message = (
        f"Delete {count} leftover playlist {noun} from data/playlists? They are "
        "superseded by bundled benchmarks and hold no data."
    )
    return True, message


@callback(
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Output("notification-container", "hideNotifications", allow_duplicate=True),
    Output(TOAST_CHANNEL_REGISTRY_STORE_ID, "data", allow_duplicate=True),
    Output("playlists-rows-refresh", "data", allow_duplicate=True),
    Output("playlists-superseded-modal", "opened", allow_duplicate=True),
    Input("playlists-superseded-confirm-button", "n_clicks"),
    State("playlists-rows-refresh", "data"),
    State(TOAST_CHANNEL_REGISTRY_STORE_ID, "data"),
    prevent_initial_call=True,
)
def confirm_delete_superseded(n_clicks, rows_refresh, toast_channels):
    """Delete the superseded user files, then refresh the alert.

    ``delete_superseded_user_playlist_files`` prunes every file it removes even
    on partial failure, so the refresh store bumps in both branches to keep the
    alert's count honest. Success clears the failure channel for the same reason
    the delete path does.

    Guard on ``n_clicks``: like ``confirm_delete_playlist``, this
    ``allow_duplicate`` handler can fire once on initial page load under
    DashProxy, and it must never delete files without a real confirm click.
    """
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update
    error_message = delete_superseded_user_playlist_files()
    next_refresh = (rows_refresh or 0) + 1
    if error_message:
        notification = toast(
            CLEANUP_FAILED_CHANNEL,
            "Cleanup failed",
            error_message,
            color="red",
        )
        return *channel_toast(notification, toast_channels), next_refresh, False
    notification = toast(
        CLEANUP_SUCCESSFUL_CHANNEL,
        "Leftover files deleted",
        "Deleted leftover playlist files.",
        color="green",
    )
    return (
        *channel_toast(notification, toast_channels, clears=(CLEANUP_FAILED_CHANNEL,)),
        next_refresh,
        False,
    )


clientside_callback(
    """
    async (_nIntervals) => {
        if (!window.dash_ag_grid || !window.dash_ag_grid.getApiAsync) {
            return window.dash_clientside.no_update;
        }

        try {
            const gridApi = await window.dash_ag_grid.getApiAsync("playlists-overview-grid");
            gridApi.refreshCells({force: true, columns: ["last_played_sort"]});
        } catch (error) {
            console.warn("Failed to refresh playlist overview relative timestamps.", error);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("playlists-overview-relative-time-refresh", "data"),
    Input("playlists-overview-relative-time-interval", "n_intervals"),
)


# Client-side quick filter: pipe the text input straight into AG Grid's built-in
# quick filter so rows narrow as the user types, with no server round-trip.
clientside_callback(
    """
    async (value) => {
        if (!window.dash_ag_grid || !window.dash_ag_grid.getApiAsync) {
            return window.dash_clientside.no_update;
        }

        try {
            const gridApi = await window.dash_ag_grid.getApiAsync("playlists-overview-grid");
            gridApi.setGridOption("quickFilterText", value || "");
        } catch (error) {
            console.warn("Failed to apply playlist overview quick filter.", error);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("playlists-overview-quick-filter-sink", "data"),
    Input("playlists-overview-quick-filter", "value"),
)


def layout(**kwargs):  # noqa: ARG001
    """Build the playlist-level overview page."""
    return dmc.Stack(
        children=[
            dcc.Location(id="playlists-location", refresh="callback-nav"),
            # The row load is driven by this layout-bound store so revisiting
            # the page rebuilds rows exactly once from current local state.
            dcc.Store(id="playlists-overview-mounted", data=True),
            # Bumped by visibility, import, or delete actions so row consumers
            # rebuild without a page reload; warmup also uses it to re-arm.
            dcc.Store(id="playlists-rows-refresh", data=0),
            # Browser-observed worker generation. The warmup interval owner
            # uses this to preserve re-arms across idle/enqueue races.
            dcc.Store(id="playlists-overview-warmup-generation", data=0),
            # Holds the code the delete confirmation modal is targeting.
            dcc.Store(id="playlists-delete-target"),
            dcc.Store(id="playlists-overview-relative-time-refresh"),
            # Dummy sink for the client-side quick-filter callback's output.
            dcc.Store(id="playlists-overview-quick-filter-sink"),
            dcc.Interval(
                id="playlists-overview-relative-time-interval",
                interval=30_000,
                n_intervals=0,
            ),
            dcc.Interval(
                id="playlists-overview-warmup-interval",
                interval=WARMUP_REFRESH_INTERVAL_MS,
                n_intervals=0,
                disabled=True,
            ),
            dmc.Title("Playlists", order=2),
            dmc.Group(
                children=[
                    dmc.Group(
                        children=[
                            dmc.TextInput(
                                id="playlists-overview-quick-filter",
                                placeholder="Filter playlists...",
                                size="sm",
                                w=240,
                            ),
                            dmc.Text("", c="dimmed", id="playlists-overview-status"),
                            dmc.Text(
                                "",
                                c="dimmed",
                                id="playlists-overview-warmup-status",
                            ),
                        ],
                        gap="md",
                        align="center",
                    ),
                    dmc.Group(
                        children=[
                            dmc.Switch(
                                checked=False,
                                id="playlists-overview-show-hidden",
                                label="Show hidden",
                                # Remembered across visits (localStorage) so
                                # the management view stays how it was left.
                                persistence=True,
                                size="sm",
                            ),
                            dmc.Button(
                                "Import",
                                id="playlists-import-open-button",
                                variant="default",
                                leftSection=local_icon(
                                    "material-symbols:upload",
                                    width=18,
                                ),
                            ),
                        ],
                        gap="md",
                        align="center",
                    ),
                ],
                justify="space-between",
            ),
            dmc.Modal(
                title="Import Playlist",
                id="playlists-import-modal",
                children=dmc.Group(
                    gap="md",
                    grow=False,
                    align="flex-start",
                    children=[
                        dmc.TextInput(
                            id="playlists-import-textinput",
                            placeholder="KovaaK's playlist code...",
                            label="Playlist code",
                            description=IMPORT_HELP_TEXT,
                            size="md",
                            w="300px",
                        ),
                        dmc.Button(
                            children="Import",
                            id="playlists-import-button",
                            mt="xl",
                        ),
                    ],
                ),
            ),
            # Delete confirmation for a user playlist. Opened by a click on a
            # row's delete cell; the target code lives in the store above.
            dmc.Modal(
                title="Delete Playlist",
                id="playlists-delete-modal",
                children=dmc.Stack(
                    gap="md",
                    children=[
                        dmc.Text(id="playlists-delete-message"),
                        dmc.Group(
                            justify="flex-end",
                            gap="sm",
                            children=[
                                dmc.Button(
                                    "Cancel",
                                    id="playlists-delete-cancel-button",
                                    variant="default",
                                ),
                                dmc.Button(
                                    "Delete",
                                    id="playlists-delete-confirm-button",
                                    color="red",
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            # Why the show/hide state may not be the user's. Hidden until the
            # visibility file is one this build cannot use.
            dmc.Alert(
                id="playlists-visibility-alert",
                title=VISIBILITY_ALERT_TITLE,
                color="yellow",
                icon=local_icon("material-symbols:warning-outline"),
                className=VISIBILITY_ALERT_HIDDEN_CLASS,
                children=dmc.Text(id="playlists-visibility-text"),
            ),
            # Cleanup affordance for user files superseded by bundled
            # benchmarks. Hidden until superseded files exist.
            dmc.Paper(
                id="playlists-superseded-alert",
                className=SUPERSEDED_NOTICE_HIDDEN_CLASS,
                withBorder=True,
                children=dmc.Stack(
                    gap="xs",
                    children=[
                        dmc.Group(
                            gap="xs",
                            align="center",
                            children=[
                                local_icon(
                                    "material-symbols:info-outline",
                                    className="alert-panel-icon",
                                ),
                                dmc.Text(
                                    SUPERSEDED_NOTICE_TITLE,
                                    className="alert-panel-title",
                                ),
                            ],
                        ),
                        dmc.Group(
                            justify="space-between",
                            align="center",
                            children=[
                                dmc.Text(id="playlists-superseded-text"),
                                dmc.Button(
                                    "Delete leftover files",
                                    id="playlists-superseded-delete-button",
                                    color="red",
                                    variant="light",
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            dmc.Modal(
                title="Delete Leftover Files",
                id="playlists-superseded-modal",
                children=dmc.Stack(
                    gap="md",
                    children=[
                        dmc.Text(id="playlists-superseded-message"),
                        dmc.Group(
                            justify="flex-end",
                            gap="sm",
                            children=[
                                dmc.Button(
                                    "Cancel",
                                    id="playlists-superseded-cancel-button",
                                    variant="default",
                                ),
                                dmc.Button(
                                    "Delete",
                                    id="playlists-superseded-confirm-button",
                                    color="red",
                                ),
                            ],
                        ),
                    ],
                ),
            ),
            dag.AgGrid(
                id="playlists-overview-grid",
                className="ag-theme-quartz playlist-overview-grid",
                columnDefs=TABLE_COLUMN_DEFS,
                rowClassRules={
                    "playlist-overview-row-hidden": "params.data.hidden",
                },
                defaultColDef={
                    "resizable": True,
                    "sortable": True,
                    # Always reserve the sort-indicator slot (a faint
                    # unsorted icon) so autoSize measures the header with
                    # room for the arrow; clicking to sort then swaps the
                    # icon in place instead of truncating the label to "…".
                    "unSortIcon": True,
                },
                dashGridOptions={
                    "animateRows": False,
                    "tooltipShowDelay": 0,
                    # Row ids carry the playlist code so any cell click can
                    # navigate to /playlists/{code}.
                    "getRowId": {"function": "params.data.code"},
                },
                columnSize="autoSize",
                columnSizeOptions=COLUMN_SIZE_OPTIONS,
                dangerously_allow_code=True,
                style={
                    "flex": 1,
                    "height": "100%",
                    "width": "100%",
                    "minHeight": 300,
                },
            ),
        ],
        gap="md",
        className="page-fill-column",
    )
