"""Per-playlist scenario table page."""

from urllib.parse import urlencode

import dash
import dash_ag_grid as dag
import dash_mantine_components as dmc
from dash import (
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    dcc,
    no_update,
)

from source.kovaaks.data_service import (
    get_playlist_by_code,
    get_playlist_display_label,
)
from source.kovaaks.playlist_scenarios_service import build_playlist_scenario_rank_rows


def _page_title(playlist_code=None, **_kwargs):
    """Carry the playlist name into the browser tab title.

    Dash Pages calls this per request with the route's path variables, after
    startup's ``load_playlists()`` has filled the playlist store, so the label
    lookup is safe here.
    """
    if not playlist_code:
        return "Playlist Scenarios"
    return f"{get_playlist_display_label(playlist_code)} - Playlist Scenarios"


dash.register_page(
    __name__,
    path_template="/playlists/<playlist_code>",
    title=_page_title,
)

AUTO_SIZE_COLUMN_KEYS = [
    "last_played_sort",
    "runs_sort",
    "rank_sort",
    "total_sort",
    "percentile_sort",
    "high_score_sort",
    "pb_cm360_sort",
    "pb_accuracy_sort",
]

COLUMN_SIZE_OPTIONS: dag.AgGrid.ColumnSizeOptions = {
    "keys": AUTO_SIZE_COLUMN_KEYS,
    "skipHeader": False,
}

TABLE_COLUMN_DEFS = [
    {
        "headerName": "Scenario",
        "field": "scenario",
        "sortable": True,
        "flex": 1,
        "minWidth": 280,
        "maxWidth": 400,
        "cellClass": "playlist-scenario-link-cell",
    },
    {
        "headerName": "Last Played",
        "field": "last_played_sort",
        "valueFormatter": {"function": "relativeTime(params.value, 'Never')"},
        "tooltipValueGetter": {
            "function": (
                "params.value == null ? null : absoluteTime(params.value, 'Never')"
            )
        },
        "cellClass": {
            "function": "params.value == null ? null : 'last-played-affordance'"
        },
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 130,
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
        "headerName": "Position",
        "field": "rank_sort",
        "valueFormatter": {"function": "params.data.rank_display"},
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 120,
    },
    {
        "headerName": "Total Players",
        "field": "total_sort",
        "valueFormatter": {"function": "params.data.total_display"},
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 120,
    },
    {
        "headerName": "Percentile",
        "field": "percentile_sort",
        "headerTooltip": (
            "Your percentile on the scenario's global leaderboard - the share "
            "of players you place above (higher is better)."
        ),
        "valueFormatter": {"function": "params.data.percentile_display"},
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 140,
    },
    {
        "headerName": "PB Score",
        "field": "high_score_sort",
        "valueFormatter": {"function": "params.data.high_score_display"},
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 120,
    },
    {
        "headerName": "PB cm/360",
        "field": "pb_cm360_sort",
        "headerTooltip": (
            "Mouse sensitivity of your personal-best run, in centimeters of "
            "mouse travel per full 360-degree turn (higher = lower "
            "sensitivity)."
        ),
        "valueFormatter": {"function": "params.data.pb_cm360_display"},
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 95,
    },
    {
        "headerName": "PB Accuracy",
        "field": "pb_accuracy_sort",
        "valueFormatter": {"function": "params.data.pb_accuracy_display"},
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 130,
    },
]


def scenario_home_href(scenario_name: str, playlist_code: str) -> str:
    """Build the Home URL that opens a scenario plot from a playlist row."""
    return "/?" + urlencode(
        {
            "playlist_code": playlist_code,
            "scenario": scenario_name,
        }
    )


@callback(
    Output("playlist-scenarios-location", "href"),
    Input("playlist-scenarios-grid", "cellClicked"),
    State("playlist-scenarios-code", "data"),
    prevent_initial_call=True,
)
def route_to_scenario_home(cell_clicked, current_playlist_code):
    """Open the Home plot for a clicked scenario cell."""
    if (
        not isinstance(cell_clicked, dict)
        or cell_clicked.get("colId") != "scenario"
        or not isinstance(cell_clicked.get("value"), str)
        or not current_playlist_code
    ):
        return no_update
    return scenario_home_href(cell_clicked["value"], current_playlist_code)


@callback(
    Output("playlist-scenarios-grid", "rowData"),
    Output("playlist-scenarios-status", "children"),
    Input("playlist-scenarios-code", "data"),
)
def load_playlist_scenario_rows(playlist_code):
    """Build sortable scenario rows for the selected imported playlist."""
    if not playlist_code:
        return [], "Select a playlist from the Playlists page."

    playlist = get_playlist_by_code(playlist_code)
    if playlist is None:
        return [], f"Playlist code is not imported: {playlist_code}"

    return build_playlist_scenario_rank_rows(playlist_code), ""


clientside_callback(
    """
    async (_nIntervals) => {
        if (!window.dash_ag_grid || !window.dash_ag_grid.getApiAsync) {
            return window.dash_clientside.no_update;
        }

        try {
            const gridApi = await window.dash_ag_grid.getApiAsync("playlist-scenarios-grid");
            gridApi.refreshCells({force: true, columns: ["last_played_sort"]});
        } catch (error) {
            console.warn("Failed to refresh playlist scenario relative timestamps.", error);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("playlist-scenarios-relative-time-refresh", "data"),
    Input("playlist-scenarios-relative-time-interval", "n_intervals"),
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
            const gridApi = await window.dash_ag_grid.getApiAsync("playlist-scenarios-grid");
            gridApi.setGridOption("quickFilterText", value || "");
        } catch (error) {
            console.warn("Failed to apply playlist scenario quick filter.", error);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("playlist-scenarios-quick-filter-sink", "data"),
    Input("playlist-scenarios-quick-filter", "value"),
)


def _page_header(playlist_code: str) -> dmc.Group:
    """Title the page with the playlist's display label and its share code."""
    return dmc.Group(
        align="baseline",
        gap="sm",
        children=[
            dmc.Title(get_playlist_display_label(playlist_code), order=2),
            dmc.Text(playlist_code, c="dimmed", size="sm"),
        ],
    )


def layout(playlist_code: str | None = None, **kwargs):  # noqa: ARG001
    """Build the per-playlist scenario table page."""
    return dmc.Stack(
        children=[
            dcc.Location(id="playlist-scenarios-location", refresh="callback-nav"),
            # The table load is intentionally driven by this layout-bound store
            # instead of the URL. When the route changes, Dash Pages first
            # navigates and rebuilds the page, then this store triggers exactly
            # one load for the new playlist.
            dcc.Store(id="playlist-scenarios-code", data=playlist_code),
            dcc.Store(id="playlist-scenarios-relative-time-refresh"),
            # Dummy sink for the client-side quick-filter callback's output.
            dcc.Store(id="playlist-scenarios-quick-filter-sink"),
            dcc.Interval(
                id="playlist-scenarios-relative-time-interval",
                interval=30_000,
                n_intervals=0,
            ),
            # No playlist selected: skip the header and let the status line
            # in the filter row below prompt the user to pick one from the
            # Playlists page.
            *([_page_header(playlist_code)] if playlist_code is not None else []),
            dmc.Group(
                children=[
                    dmc.TextInput(
                        id="playlist-scenarios-quick-filter",
                        placeholder="Filter scenarios...",
                        size="sm",
                        w=240,
                    ),
                    dmc.Text("", c="dimmed", id="playlist-scenarios-status"),
                ],
                gap="md",
                align="center",
            ),
            dcc.Loading(
                dag.AgGrid(
                    id="playlist-scenarios-grid",
                    className="ag-theme-quartz playlist-scenarios-grid",
                    columnDefs=TABLE_COLUMN_DEFS,
                    rowData=[],
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
