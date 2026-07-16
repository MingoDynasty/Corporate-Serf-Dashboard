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
from source.kovaaks.data_service import (
    delete_superseded_user_playlist_files,
    delete_user_playlist,
    get_playlist_display_label,
    get_superseded_user_playlist_files,
    get_user_root_playlist_codes,
    load_playlist_from_code,
)
from source.kovaaks.playlist_overview_service import build_playlist_overview_rows
from source.kovaaks.playlist_visibility_service import (
    hide_playlist,
    is_playlist_shown,
    show_playlist,
    toggle_playlist_visibility,
)

logger = logging.getLogger(__name__)

VISIBILITY_COLUMN_ID = "hidden"
# The delete action cell's colId. Matches the ``deletable`` row flag so the
# renderer can hide itself on bundled rows; excluded from row navigation.
DELETE_COLUMN_ID = "deletable"

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

dash.register_page(
    __name__,
    path="/playlists",
    title="Playlists",
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

LOWEST_PERCENTILE_TOOLTIP = (
    "params.value == null ? null : ('Lowest: ' + params.data.lowest_scenario)"
)

# The eye toggle acts immediately with no confirm step, so the hover copy
# carries the action, its consequence, and the way back (Show hidden).
VISIBILITY_TOOLTIP = (
    "params.data.hidden"
    " ? 'Show this playlist again in the overview and playlist selectors'"
    " : 'Hide this playlist from the overview and playlist selectors;"
    " restore it later via Show hidden'"
)

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
        "headerTooltip": (
            "Scenarios you have played at least once, out of the scenarios in "
            "the playlist."
        ),
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
            "function": "params.value == null ? null : 'last-played-affordance'"
        },
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 130,
    },
    {
        "headerName": "Median Percentile",
        "field": "median_percentile_sort",
        "headerTooltip": (
            "Median leaderboard percentile across this playlist's scenarios "
            "with a cached position. N/M = scenarios with a cached position "
            "out of scenarios in the playlist - fills in as you open "
            "playlists."
        ),
        "valueFormatter": {"function": "params.data.median_percentile_display"},
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 160,
    },
    {
        "headerName": "Lowest Percentile",
        "field": "lowest_percentile_sort",
        "headerTooltip": (
            "The playlist's weakest scenario by leaderboard percentile, over "
            "the same N/M coverage as Median Percentile. Hover a value to see "
            "which scenario."
        ),
        "valueFormatter": {"function": "params.data.lowest_percentile_display"},
        "tooltipValueGetter": {"function": LOWEST_PERCENTILE_TOOLTIP},
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
    Output("playlists-overview-grid", "rowData"),
    Output("playlists-overview-status", "children"),
    Input("playlists-overview-mounted", "data"),
    Input("playlists-overview-show-hidden", "checked"),
    Input("playlists-overview-grid", "cellClicked"),
    Input("playlists-rows-refresh", "data"),
)
def load_playlist_overview_rows(_mounted, show_hidden, cell_clicked, _rows_refresh):
    """Build overview rows from local run data and rank caches (no network).

    Also handles hide/unhide: a click on the visibility action cell toggles
    that playlist's preference, then the rows rebuild from the new state.
    """
    if ctx.triggered_id == "playlists-overview-grid":
        if (
            not isinstance(cell_clicked, dict)
            or cell_clicked.get("colId") != VISIBILITY_COLUMN_ID
            or not isinstance(cell_clicked.get("rowId"), str)
            or not cell_clicked["rowId"]
        ):
            return no_update, no_update
        toggle_playlist_visibility(cell_clicked["rowId"])

    rows = build_playlist_overview_rows(include_hidden=bool(show_hidden))
    if not rows:
        if build_playlist_overview_rows(include_hidden=True):
            return [], 'All playlists are hidden. Toggle "Show hidden" to manage them.'
        return [], "No playlists are loaded."
    return rows, ""


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
    Output("playlists-rows-refresh", "data"),
    Output("playlists-import-modal", "opened", allow_duplicate=True),
    Output("playlists-import-textinput", "value"),
    Input("playlists-import-button", "n_clicks"),
    State("playlists-import-textinput", "value"),
    State("playlists-rows-refresh", "data"),
    prevent_initial_call=True,
)
def import_playlist(_, playlist_to_import, rows_refresh):
    """Import a playlist code and surface the result on this page.

    Reuses the shared import service path. On success the playlist is marked
    visible ("importing is the intent to see"), the refresh store is bumped so
    the overview rebuilds and shows the new row without a page reload, and the
    modal closes with a cleared field so the user sees that new row. A refusal
    leaves the modal open with the pasted code intact so the user can correct
    it; a duplicate-code refusal whose conflicting playlist is hidden gets the
    unhide hint appended (R14).
    """
    if not playlist_to_import:
        return no_update, no_update, no_update, no_update
    playlist_to_import = playlist_to_import.strip()
    logger.debug("Importing playlist '%s'", playlist_to_import)
    error_message, canonical_code = load_playlist_from_code(playlist_to_import)

    if error_message:
        # The refusal branch can carry the conflicting existing code; if that
        # playlist is hidden, tell the user where to find it.
        if canonical_code is not None and not is_playlist_shown(canonical_code):
            error_message += HIDDEN_DUPLICATE_HINT
        notification = {
            "action": "show",
            "title": "Playlist Import Failed",
            "message": error_message,
            "color": "red",
            "id": "imported-playlist-failed-notification",
            "icon": local_icon("material-symbols:upload"),
        }
        return [notification], no_update, no_update, no_update

    # Importing is the intent to see: new playlists arrive visible. Mark the
    # canonical stored code, which can differ from the pasted input. The
    # is-not-None guard is defensive; the service contract guarantees a code
    # here, but never persist a None into the shown-set if that ever changes.
    if canonical_code is not None:
        show_playlist(canonical_code)
    notification = {
        "action": "show",
        "title": "Notification",
        "message": "Successfully imported playlist!",
        "color": "green",
        "id": "imported-playlist-successful-notification",
        "icon": local_icon("material-symbols:upload"),
    }
    return [notification], (rows_refresh or 0) + 1, False, ""


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
    # never open a misleading "will be removed from data/playlists" dialog
    # (delete_user_playlist would refuse it anyway, but only after a scare).
    if playlist_code not in get_user_root_playlist_codes():
        return no_update, no_update, no_update
    label = get_playlist_display_label(playlist_code)
    message = (
        f'Delete "{label}" ({playlist_code})? This removes its playlist file '
        "from data/playlists. You can re-import it later by share code."
    )
    return True, playlist_code, message


@callback(
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Output("playlists-rows-refresh", "data", allow_duplicate=True),
    Output("playlists-delete-modal", "opened", allow_duplicate=True),
    Input("playlists-delete-confirm-button", "n_clicks"),
    State("playlists-delete-target", "data"),
    State("playlists-rows-refresh", "data"),
    prevent_initial_call=True,
)
def confirm_delete_playlist(n_clicks, target_code, rows_refresh):
    """Delete the confirmed user playlist, then rebuild the grid.

    On failure the red notification carries the service's message and the grid
    is left untouched. On success the visibility membership is dropped too
    (in a show-list, forgetting a code IS removing its membership — this keeps
    preferences.json from accumulating dead codes) and the refresh store bumps
    so the deleted row disappears without a page reload.

    Guard on ``n_clicks``: under DashProxy an ``allow_duplicate`` callback can
    still fire once on initial page load despite ``prevent_initial_call``, so a
    destructive handler must confirm a real button click (a fresh load has
    ``n_clicks`` None and no target) before touching the filesystem.
    """
    if not n_clicks or not target_code:
        return no_update, no_update, no_update
    error_message = delete_user_playlist(target_code)
    if error_message:
        notification = {
            "action": "show",
            "title": "Playlist Delete Failed",
            "message": error_message,
            "color": "red",
            "id": "deleted-playlist-failed-notification",
        }
        return [notification], no_update, False
    hide_playlist(target_code)
    notification = {
        "action": "show",
        "title": "Notification",
        "message": "Deleted playlist.",
        "color": "green",
        "id": "deleted-playlist-successful-notification",
    }
    return [notification], (rows_refresh or 0) + 1, False


@callback(
    Output("playlists-superseded-alert", "style"),
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
        return {"display": "none"}, ""
    count = len(superseded_files)
    noun = "file" if count == 1 else "files"
    verb = "is" if count == 1 else "are"
    message = (
        f"{count} leftover playlist {noun} in data/playlists {verb} superseded "
        "by bundled benchmarks."
    )
    return {}, message


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
    Output("playlists-rows-refresh", "data", allow_duplicate=True),
    Output("playlists-superseded-modal", "opened", allow_duplicate=True),
    Input("playlists-superseded-confirm-button", "n_clicks"),
    State("playlists-rows-refresh", "data"),
    prevent_initial_call=True,
)
def confirm_delete_superseded(n_clicks, rows_refresh):
    """Delete the superseded user files, then refresh the alert.

    ``delete_superseded_user_playlist_files`` prunes every file it removes even
    on partial failure, so the refresh store bumps in both branches to keep the
    alert's count honest.

    Guard on ``n_clicks``: like ``confirm_delete_playlist``, this
    ``allow_duplicate`` handler can fire once on initial page load under
    DashProxy, and it must never delete files without a real confirm click.
    """
    if not n_clicks:
        return no_update, no_update, no_update
    error_message = delete_superseded_user_playlist_files()
    next_refresh = (rows_refresh or 0) + 1
    if error_message:
        notification = {
            "action": "show",
            "title": "Cleanup Failed",
            "message": error_message,
            "color": "red",
            "id": "superseded-cleanup-failed-notification",
        }
        return [notification], next_refresh, False
    notification = {
        "action": "show",
        "title": "Notification",
        "message": "Deleted leftover playlist files.",
        "color": "green",
        "id": "superseded-cleanup-successful-notification",
    }
    return [notification], next_refresh, False


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
            # Bumped by a successful import or delete so the row-load callback
            # (and the superseded alert) rebuild without a page reload.
            dcc.Store(id="playlists-rows-refresh", data=0),
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
            # Cleanup affordance for user files superseded by bundled
            # benchmarks. Hidden (display:none) until superseded files exist.
            dmc.Alert(
                id="playlists-superseded-alert",
                title="Leftover playlist files",
                color="yellow",
                style={"display": "none"},
                children=dmc.Group(
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
            dcc.Loading(
                dag.AgGrid(
                    id="playlists-overview-grid",
                    className="ag-theme-quartz playlist-overview-grid",
                    columnDefs=TABLE_COLUMN_DEFS,
                    rowData=[],
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
                        "height": "100%",
                        "width": "100%",
                        "minHeight": 300,
                    },
                ),
                parent_style={
                    "flex": 1,
                    "minHeight": 0,
                    "display": "flex",
                    "flexDirection": "column",
                },
            ),
        ],
        gap="md",
        style={
            "height": (
                "calc(100dvh - var(--app-shell-header-offset, 0rem) "
                "- 2*var(--app-shell-padding, 1rem))"
            )
        },
    )
