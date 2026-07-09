"""Playlist-level overview page at the playlists landing route."""

import dash
import dash_ag_grid as dag
import dash_mantine_components as dmc
from dash import Input, Output, callback, clientside_callback, dcc, no_update

from source.kovaaks.playlist_overview_service import build_playlist_overview_rows

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
    playlist_code = cell_clicked.get("rowId")
    if not isinstance(playlist_code, str) or not playlist_code:
        return no_update
    return f"/playlists/{playlist_code}"


@callback(
    Output("playlists-overview-grid", "rowData"),
    Output("playlists-overview-status", "children"),
    Input("playlists-overview-mounted", "data"),
)
def load_playlist_overview_rows(_mounted):
    """Build overview rows from local run data and rank caches (no network)."""
    rows = build_playlist_overview_rows()
    if not rows:
        return [], "No playlists are loaded."
    return rows, ""


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
            dcc.Store(id="playlists-overview-relative-time-refresh"),
            dcc.Interval(
                id="playlists-overview-relative-time-interval",
                interval=30_000,
                n_intervals=0,
            ),
            dmc.Text("", c="dimmed", id="playlists-overview-status"),
            dcc.Loading(
                dag.AgGrid(
                    id="playlists-overview-grid",
                    className="ag-theme-quartz playlist-overview-grid",
                    columnDefs=TABLE_COLUMN_DEFS,
                    rowData=[],
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
