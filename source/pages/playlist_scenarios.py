"""Per-playlist scenario table page."""

from urllib.parse import urlencode

import dash
import dash_ag_grid as dag
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, clientside_callback, dcc, no_update

from source.kovaaks.data_service import get_playlist_by_code
from source.kovaaks.playlist_scenarios_service import build_playlist_scenario_rank_rows
from source.pages.playlist_components import playlist_selector

dash.register_page(
    __name__,
    path_template="/playlists/<playlist_code>",
    title="Playlist Scenarios",
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
        "cellRenderer": {"function": "scenarioHomeLinkRenderer(params)"},
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


def _add_scenario_home_links(
    rows: list[dict[str, str | int | float | None]],
    playlist_code: str,
) -> list[dict[str, str | int | float | None]]:
    linked_rows: list[dict[str, str | int | float | None]] = []
    for row in rows:
        scenario_name = row.get("scenario")
        linked_row = row
        if isinstance(scenario_name, str):
            linked_row = {
                **row,
                "scenario_home_href": scenario_home_href(
                    scenario_name,
                    playlist_code,
                ),
            }
        linked_rows.append(linked_row)
    return linked_rows


@callback(
    Output("playlist-scenarios-location", "pathname"),
    Input("playlist-scenarios-selector", "value"),
    State("playlist-scenarios-location", "pathname"),
    prevent_initial_call=True,
)
def route_to_selected_playlist(playlist_code, current_pathname):
    """Navigate to a newly selected playlist without redundant routing."""
    if not playlist_code:
        return no_update

    pathname = f"/playlists/{playlist_code}"
    if pathname == current_pathname:
        return no_update
    return pathname


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

    rows = build_playlist_scenario_rank_rows(playlist_code)
    return _add_scenario_home_links(rows, playlist_code), ""


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


def layout(playlist_code: str | None = None, **kwargs):  # noqa: ARG001
    """Build the per-playlist scenario table page."""
    # Keep the raw route code for error handling, but only pass the selector a
    # value that exists in its options list.
    playlist = get_playlist_by_code(playlist_code) if playlist_code else None
    playlist_selector_value = playlist_code if playlist else None

    return dmc.Stack(
        children=[
            dcc.Location(id="playlist-scenarios-location", refresh="callback-nav"),
            # The table load is intentionally driven by this layout-bound store
            # instead of the URL. When the selector changes, Dash Pages first
            # navigates and rebuilds the page, then this store triggers exactly
            # one load for the new playlist.
            dcc.Store(id="playlist-scenarios-code", data=playlist_code),
            dcc.Store(id="playlist-scenarios-relative-time-refresh"),
            dcc.Interval(
                id="playlist-scenarios-relative-time-interval",
                interval=30_000,
                n_intervals=0,
            ),
            dmc.Group(
                children=[
                    playlist_selector(
                        "playlist-scenarios-selector",
                        value=playlist_selector_value,
                    ),
                ],
                align="flex-end",
                justify="space-between",
            ),
            dmc.Text("", c="dimmed", id="playlist-scenarios-status"),
            dcc.Loading(
                dag.AgGrid(
                    id="playlist-scenarios-grid",
                    className="ag-theme-quartz playlist-scenarios-grid",
                    columnDefs=TABLE_COLUMN_DEFS,
                    rowData=[],
                    defaultColDef={
                        "resizable": True,
                        "sortable": True,
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
