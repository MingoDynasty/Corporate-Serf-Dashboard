"""Per-playlist scenario table page."""

from uuid import uuid4

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

from source.components.local_icon import local_icon
from source.kovaaks.data_service import (
    get_playlist_by_code,
    get_playlist_display_label,
)
from source.kovaaks.playlist_scenarios_service import (
    PlaylistScenarioFillDrain,
    build_playlist_scenario_rank_rows,
    drain_playlist_scenario_fill,
    scenario_home_href,
    start_playlist_scenario_fill,
)


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
        # Real anchor to the scenario's Home plot. The renderer reads the
        # prebuilt row "href" and carries the link styling on the anchor
        # itself, so new-tab / copy-link work; the cellClicked callback still
        # handles the fast in-app left-click nav.
        "cellRenderer": "ScenarioLink",
        "sortable": True,
        "flex": 1,
        "minWidth": 280,
        "maxWidth": 400,
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
            "function": "params.value == null ? null : 'cell-tooltip-affordance'"
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
        "valueFormatter": {
            "function": "params.data.rank_pending ? '' : params.data.rank_display"
        },
        "cellClass": {
            "function": ("params.data.rank_pending ? 'playlist-rank-pending' : null")
        },
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 120,
    },
    {
        "headerName": "Total Players",
        "field": "total_sort",
        "valueFormatter": {
            "function": "params.data.total_pending ? '' : params.data.total_display"
        },
        "cellClass": {
            "function": ("params.data.total_pending ? 'playlist-rank-pending' : null")
        },
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
        "valueFormatter": {
            "function": (
                "params.data.percentile_pending ? '' : params.data.percentile_display"
            )
        },
        "cellClass": {
            "function": (
                "params.data.percentile_pending ? 'playlist-rank-pending' : null"
            )
        },
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
    Output("playlist-scenarios-generation", "data"),
    Output("playlist-scenarios-fill-interval", "disabled"),
    Input("playlist-scenarios-code", "data"),
)
def load_playlist_scenario_rows(playlist_code):
    """Paint cache-only rows, then register phase 2 just before returning."""
    if not playlist_code:
        return [], "Select a playlist from the Playlists page.", None, True

    playlist = get_playlist_by_code(playlist_code)
    if playlist is None:
        return [], f"Playlist code is not imported: {playlist_code}", None, True

    generation_token = uuid4().hex
    rows = build_playlist_scenario_rank_rows(playlist_code, generation_token)
    # Registration deliberately happens only after the phase-1 rows exist. A
    # spurious/fast interval tick must never drain updates into an empty grid.
    if not start_playlist_scenario_fill(playlist_code, generation_token):
        # A concurrent delete can remove the playlist between phase 1 and
        # registration. With no fill to settle the rows, clear every pending
        # flag here so the disabled interval cannot strand animation forever.
        for row in rows:
            row["rank_pending"] = False
            row["total_pending"] = False
            row["percentile_pending"] = False
        return rows, "Update interrupted", None, True
    status = _live_fill_status(0, len(rows))
    return rows, status, generation_token, False


def _live_fill_status(done_count: int, total: int) -> str:
    return f"Updating positions from KovaaK's… {done_count}/{total}"


def _settled_fill_status(fill: PlaylistScenarioFillDrain) -> str:
    if fill.terminal == "cancelled":
        return f"Update interrupted · {fill.done_count} of {fill.total} refreshed"
    if fill.unknown_count:
        status = f"{fill.unknown_count} of {fill.total} positions unavailable"
        if fill.stale_count:
            status += f" · {fill.stale_count} from cache — KovaaK's unreachable"
        return status
    if fill.stale_count:
        return (
            f"{fill.stale_count} of {fill.total} positions from cache — "
            "KovaaK's unreachable"
        )
    return ""


def _fill_summary_notification(fill: PlaylistScenarioFillDrain):
    if fill.terminal != "complete" or not fill.consuming_terminal:
        return no_update
    if fill.unknown_count:
        message = f"Couldn't update {fill.unknown_count} of {fill.total} positions"
        if fill.stale_count:
            message += f"; {fill.stale_count} more served from cache"
        color = "red"
    elif fill.stale_count:
        message = (
            f"{fill.stale_count} of {fill.total} positions served from cache — "
            "KovaaK's was unreachable"
        )
        color = "yellow"
    else:
        return no_update
    return [
        {
            "action": "show",
            "title": "Playlist Position Update",
            "message": message,
            "color": color,
            "id": f"playlist-progressive-fill-{fill.generation_token}",
            "icon": local_icon("material-symbols:warning-outline"),
            "autoClose": 8000,
        }
    ]


@callback(
    Output("playlist-scenarios-grid", "rowTransaction"),
    Output("playlist-scenarios-status", "children", allow_duplicate=True),
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Input("playlist-scenarios-fill-interval", "n_intervals"),
    State("playlist-scenarios-generation", "data"),
    prevent_initial_call=True,
)
def drain_playlist_scenario_rows(_n_intervals, generation_token):
    """Apply streamed rows and run terminal one-shots exactly once."""
    # DashProxy can phantom-fire allow_duplicate callbacks on initial load.
    if not generation_token:
        return no_update, no_update, no_update
    fill = drain_playlist_scenario_fill(generation_token)
    if fill is None:
        return no_update, no_update, no_update

    transaction = {"update": fill.updates} if fill.updates else no_update
    if fill.terminal is None:
        status = _live_fill_status(fill.done_count, fill.total)
        return transaction, status, no_update
    return transaction, _settled_fill_status(fill), _fill_summary_notification(fill)


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
            dcc.Store(id="playlist-scenarios-generation"),
            dcc.Store(id="playlist-scenarios-relative-time-refresh"),
            # Dummy sink for the client-side quick-filter callback's output.
            dcc.Store(id="playlist-scenarios-quick-filter-sink"),
            dcc.Interval(
                id="playlist-scenarios-relative-time-interval",
                interval=30_000,
                n_intervals=0,
            ),
            dcc.Interval(
                id="playlist-scenarios-fill-interval",
                interval=1_000,
                n_intervals=0,
                disabled=True,
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
            dag.AgGrid(
                id="playlist-scenarios-grid",
                className="ag-theme-quartz playlist-scenarios-grid",
                columnDefs=TABLE_COLUMN_DEFS,
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
                    "getRowId": {
                        "function": (
                            "params.data.generation_token + ':' + "
                            "params.data.playlist_order"
                        )
                    },
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
        style={
            "height": (
                "calc(100dvh - var(--app-shell-header-offset, 0rem) "
                "- 2*var(--app-shell-padding, 1rem))"
            )
        },
    )
