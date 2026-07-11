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
from source.kovaaks.data_service import load_playlist_from_code
from source.kovaaks.playlist_overview_service import build_playlist_overview_rows
from source.kovaaks.playlist_visibility_service import (
    is_playlist_shown,
    show_playlist,
    toggle_playlist_visibility,
)

logger = logging.getLogger(__name__)

VISIBILITY_COLUMN_ID = "hidden"

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

TABLE_COLUMN_DEFS = [
    {
        "headerName": "Playlist",
        "field": "name",
        "sortable": True,
        "flex": 1,
        "minWidth": 280,
        "maxWidth": 420,
    },
    {
        "headerName": "Type",
        "field": "type_display",
        "cellRenderer": "TypeBadge",
        "sortable": True,
        "minWidth": 110,
    },
    {
        "headerName": "Played",
        "field": "played_sort",
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
        "valueFormatter": {"function": "params.data.median_percentile_display"},
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 160,
    },
    {
        "headerName": "Lowest Percentile",
        "field": "lowest_percentile_sort",
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
    if cell_clicked.get("colId") == VISIBILITY_COLUMN_ID:
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
    Input("playlists-import-refresh", "data"),
)
def load_playlist_overview_rows(_mounted, show_hidden, cell_clicked, _import_refresh):
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
    Output("playlists-import-refresh", "data"),
    Input("playlists-import-button", "n_clicks"),
    State("playlists-import-textinput", "value"),
    State("playlists-import-refresh", "data"),
    prevent_initial_call=True,
)
def import_playlist(_, playlist_to_import, import_refresh):
    """Import a playlist code and surface the result on this page.

    Reuses the shared import service path. On success the playlist is marked
    visible ("importing is the intent to see") and the refresh store is bumped
    so the overview rebuilds and shows the new row without a page reload. A
    duplicate-code refusal whose conflicting playlist is hidden gets the unhide
    hint appended (R14).
    """
    if not playlist_to_import:
        return no_update, no_update
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
        return [notification], no_update

    # Importing is the intent to see: new playlists arrive visible. Mark the
    # canonical stored code, which can differ from the pasted input.
    show_playlist(canonical_code)
    notification = {
        "action": "show",
        "title": "Notification",
        "message": "Successfully imported playlist!",
        "color": "green",
        "id": "imported-playlist-successful-notification",
        "icon": local_icon("material-symbols:upload"),
    }
    return [notification], (import_refresh or 0) + 1


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


def layout(**kwargs):  # noqa: ARG001
    """Build the playlist-level overview page."""
    return dmc.Stack(
        children=[
            dcc.Location(id="playlists-location", refresh="callback-nav"),
            # The row load is driven by this layout-bound store so revisiting
            # the page rebuilds rows exactly once from current local state.
            dcc.Store(id="playlists-overview-mounted", data=True),
            # Bumped by a successful import so the row-load callback rebuilds
            # and shows the new row without a page reload.
            dcc.Store(id="playlists-import-refresh", data=0),
            dcc.Store(id="playlists-overview-relative-time-refresh"),
            dcc.Interval(
                id="playlists-overview-relative-time-interval",
                interval=30_000,
                n_intervals=0,
            ),
            dmc.Group(
                children=[
                    dmc.Text("", c="dimmed", id="playlists-overview-status"),
                    dmc.Group(
                        children=[
                            dmc.Switch(
                                checked=False,
                                id="playlists-overview-show-hidden",
                                label="Show hidden",
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
