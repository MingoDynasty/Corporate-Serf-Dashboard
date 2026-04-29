"""Per-playlist scenario table page."""

import dash
from dash import Input, Output, State, callback, dcc, no_update
import dash_ag_grid as dag
import dash_mantine_components as dmc

from source.config.config_service import config
from source.kovaaks.data_service import get_playlist_by_code
from source.kovaaks.playlist_scenarios_service import (
    PlaylistRankLookupConfig,
    build_playlist_scenario_rank_rows,
)
from source.pages.playlist_components import playlist_selector

dash.register_page(
    __name__,
    path_template="/playlists/<playlist_code>",
    title="Playlist Scenarios",
)

TABLE_COLUMN_DEFS = [
    {
        "headerName": "Scenario",
        "field": "scenario",
        "sortable": True,
        "flex": 2,
        "minWidth": 280,
    },
    {
        "headerName": "Current Rank",
        "field": "rank_sort",
        "valueFormatter": {"function": "params.data.rank_display"},
        "comparator": {"function": "dagfuncs.nullsLastComparator"},
        "sortable": True,
        "flex": 1,
        "minWidth": 120,
    },
    {
        "headerName": "Total Ranks",
        "field": "total_sort",
        "valueFormatter": {"function": "params.data.total_display"},
        "comparator": {"function": "dagfuncs.nullsLastComparator"},
        "sortable": True,
        "flex": 1,
        "minWidth": 120,
    },
    {
        "headerName": "Percentile",
        "field": "percentile_sort",
        "valueFormatter": {"function": "params.data.percentile_display"},
        "comparator": {"function": "dagfuncs.nullsLastComparator"},
        "sortable": True,
        "flex": 1,
        "minWidth": 140,
    },
]


def _lookup_config() -> PlaylistRankLookupConfig:
    return PlaylistRankLookupConfig(
        username=config.kovaaks_username,
        steam_id=config.steam_id,
        scenario_metadata_cache_ttl_hours=config.scenario_metadata_cache_ttl_hours,
        scenario_rank_cache_ttl_hours=config.scenario_rank_cache_ttl_hours,
        leaderboard_total_cache_ttl_hours=config.leaderboard_total_cache_ttl_hours,
    )


@callback(
    Output("playlist-scenarios-location", "pathname"),
    Input("playlist-scenarios-selector", "value"),
    State("playlist-scenarios-location", "pathname"),
    prevent_initial_call=True,
)
def route_to_selected_playlist(playlist_code, current_pathname):
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
    if not playlist_code:
        return [], "Select a playlist from the Playlists page."

    playlist = get_playlist_by_code(playlist_code)
    if playlist is None:
        return [], "The selected playlist is not imported."

    rows = build_playlist_scenario_rank_rows(playlist_code, _lookup_config())
    return rows, ""


def layout(playlist_code: str | None = None, **kwargs):  # noqa: ARG001
    playlist = get_playlist_by_code(playlist_code) if playlist_code else None
    selected_playlist_code = playlist_code if playlist else None

    return dmc.Stack(
        children=[
            dcc.Location(id="playlist-scenarios-location", refresh="callback-nav"),
            # The table load is intentionally driven by this layout-bound store
            # instead of the URL. When the selector changes, Dash Pages first
            # navigates and rebuilds the page, then this store triggers exactly
            # one load for the new playlist.
            dcc.Store(id="playlist-scenarios-code", data=playlist_code),
            dmc.Group(
                children=[
                    playlist_selector(
                        "playlist-scenarios-selector",
                        value=selected_playlist_code,
                    ),
                ],
                align="flex-end",
                justify="space-between",
            ),
            dmc.Text(
                "" if playlist else "The selected playlist is not imported.",
                c="dimmed",
                id="playlist-scenarios-status",
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
                    },
                    dashGridOptions={
                        "animateRows": False,
                        "domLayout": "autoHeight",
                    },
                    columnSize="responsiveSizeToFit",
                    dangerously_allow_code=True,
                    style={"width": "100%"},
                )
            ),
        ],
        gap="md",
    )
