"""Per-playlist scenario table page."""

import copy
import json
from collections.abc import Collection, Sequence
from typing import Any, NamedTuple
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
    html,
    no_update,
)

from source.components.columns_menu import (
    COLUMNS_MENU_GRID_OPTIONS,
    MenuColumn,
    columns_menu,
    columns_menu_sink,
    register_columns_menu,
)
from source.components.local_icon import local_icon
from source.config.settings_service import get_kovaaks_username, get_steam_id
from source.kovaaks.data_service import (
    get_playlist_by_code,
    get_playlist_display_label,
    get_scenario_groups,
    is_benchmark_playlist,
)
from source.kovaaks.evxl_links import evxl_benchmark_url
from source.kovaaks.playlist_scenarios_service import (
    PlaylistScenarioFillDrain,
    build_playlist_scenario_rank_rows,
    drain_playlist_scenario_fill,
    scenario_home_href,
    start_playlist_scenario_fill,
)
from source.pages.page_title import page_title


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
    title=page_title(_page_title),
)

LEADERBOARD_ID_COLUMN_ID = "leaderboard_id"

AUTO_SIZE_COLUMN_KEYS = [
    LEADERBOARD_ID_COLUMN_ID,
    "last_played_sort",
    "runs_sort",
    "position_sort",
    "total_sort",
    "percentile_sort",
    "pb_score_sort",
    "tier_sort",
    "next_tier_sort",
    "pb_timestamp_sort",
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
        "headerName": "Leaderboard ID",
        "field": LEADERBOARD_ID_COLUMN_ID,
        "headerTooltip": (
            "The number KovaaK's uses to identify this scenario's leaderboard "
            "in its API."
        ),
        "cellClass": "cell-selectable-text",
        # Hidden until the Columns menu shows it. ``initialHide``, never
        # ``hide``: AG Grid reapplies ``hide`` whenever column defs arrive
        # again, which would override the user's choice.
        "initialHide": True,
        # A sortable column needs a name in ``?sort=``. Without one the
        # address writer stops writing for as long as the column is sorted,
        # which silently ends sort memory.
        "sortable": False,
        "minWidth": 90,
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
        "field": "position_sort",
        "valueFormatter": {
            "function": "params.data.position_pending ? '' : params.data.position_display"
        },
        "cellClass": {
            "function": (
                "params.data.position_pending ? 'playlist-cell-pending' : null"
            )
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
            "function": ("params.data.total_pending ? 'playlist-cell-pending' : null")
        },
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 120,
    },
    {
        "headerName": "Percentile",
        "field": "percentile_sort",
        "headerTooltip": (
            "Your percentile on the scenario's global leaderboard: the share "
            "of players you place above. Higher is better."
        ),
        "valueFormatter": {
            "function": (
                "params.data.percentile_pending ? '' : params.data.percentile_display"
            )
        },
        "cellClass": {
            "function": (
                "params.data.percentile_pending ? 'playlist-cell-pending' : null"
            )
        },
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 140,
    },
    {
        "headerName": "PB Score",
        "field": "pb_score_sort",
        "valueFormatter": {"function": "params.data.pb_score_display"},
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 120,
    },
    {
        "headerName": "PB Date",
        "field": "pb_timestamp_sort",
        "valueFormatter": {"function": "relativeTime(params.value, 'N/A')"},
        "tooltipValueGetter": {
            "function": (
                "params.value == null ? null : absoluteTime(params.value, 'N/A')"
            )
        },
        "cellClass": {
            "function": "params.value == null ? null : 'cell-tooltip-affordance'"
        },
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 120,
    },
    {
        "headerName": "PB cm/360",
        "field": "pb_cm360_sort",
        "headerTooltip": (
            "Mouse sensitivity of your personal-best run, in centimeters of "
            "mouse travel per full 360-degree turn. Higher is slower."
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

# Only a benchmark's table has these, directly after PB Score, the value both
# compute from.
BENCHMARK_COLUMN_DEFS = [
    {
        "headerName": "Rank",
        "field": "tier_sort",
        "headerTooltip": "The highest rank your PB score has reached on this scenario.",
        "valueFormatter": {"function": "params.data.tier_display"},
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 100,
    },
    {
        "headerName": "Next Rank",
        "field": "next_tier_sort",
        "headerTooltip": (
            "How much your PB score has to grow to reach the next rank. "
            'A row that reads "faster" is a scenario scored by completion '
            "time, and shows how much faster you have to finish than your PB. "
            "Lower is closer."
        ),
        "valueFormatter": {"function": "params.data.next_tier_display"},
        "tooltipValueGetter": {"function": "params.data.next_tier_tooltip"},
        "cellClass": {
            "function": (
                "params.data.next_tier_tooltip == null"
                " ? null : 'cell-tooltip-affordance'"
            )
        },
        "comparator": {"function": "nullsLastComparator"},
        "sortable": True,
        "minWidth": 150,
    },
]


class GroupColumn(NamedTuple):
    """One of the two group columns a benchmark's table can show.

    ``column_id`` is chosen once. The Columns menu keeps a stored choice under
    it, so renaming one resets that choice in every browser.
    """

    column_id: str
    header: str
    name_field: str
    color_field: str
    run_field: str


CATEGORY_COLUMN = GroupColumn(
    "category", "Category", "category_name", "category_color", "category_run"
)
SUBCATEGORY_COLUMN = GroupColumn(
    "subcategory",
    "Subcategory",
    "subcategory_name",
    "subcategory_color",
    "subcategory_run",
)
GROUP_COLUMNS = (CATEGORY_COLUMN, SUBCATEGORY_COLUMN)
GROUP_COLUMN_WIDTH = 34


def _group_column_def(column: GroupColumn) -> dict:
    """Build one group column: narrow, pinned, and merged down each group."""
    name = f"params.data.{column.name_field}"
    return {
        "colId": column.column_id,
        # The header shows no text, because 34 px can't fit the word. The
        # name stays in the header for assistive technology, hidden by the
        # header class, and the tooltip shows it on hover.
        "headerName": column.header,
        "headerTooltip": column.header,
        "headerClass": "playlist-scenario-group-header",
        # The cell's value is the row's run, never the group's name. The grid
        # merges neighboring cells whose values are equal, and dash-ag-grid
        # passes no ``spanRows`` function through, so equality is the only
        # merge test. With the name as the value, two groups that share a name
        # across a category boundary would merge into one.
        "field": column.run_field,
        "spanRows": True,
        # Without this the filter box would match the run numbers, so typing
        # a digit would keep rows for no reason a user could see.
        "getQuickFilterText": {"function": name},
        "tooltipValueGetter": {"function": f"{name} || null"},
        "cellRenderer": "ScenarioGroupLabel",
        "cellRendererParams": {"nameField": column.name_field},
        "cellStyle": {
            "function": f"scenarioGroupCellStyle(params.data.{column.color_field})"
        },
        "cellClass": "playlist-scenario-group-cell",
        # Pinned so a group taller than the window keeps its label in view.
        # The label is ``position: sticky``, and an unpinned cell's nearest
        # scroll container is the one that scrolls the columns sideways, so
        # there the label would scroll away with the cell's middle.
        "pinned": "left",
        "lockPinned": True,
        "suppressMovable": True,
        "sortable": False,
        "resizable": False,
        "width": GROUP_COLUMN_WIDTH,
        "minWidth": GROUP_COLUMN_WIDTH,
        "maxWidth": GROUP_COLUMN_WIDTH,
        # The Columns menu fits a column it has just shown to its content.
        "suppressAutoSize": True,
    }


COLUMNS_MENU_ID = "playlist-scenarios-columns"

# The Columns menu's entries, in table order: every column the table can work
# without. A column the table's structure depends on is never listed, and the
# row means nothing without its Scenario cell, which is also the link into it.
# The labels are kept by hand, in sentence case as controls, where the headers
# they name keep Title Case.
MENU_COLUMNS = [
    MenuColumn(LEADERBOARD_ID_COLUMN_ID, "Leaderboard ID", shown_by_default=False),
    MenuColumn("last_played_sort", "Last played"),
    MenuColumn("runs_sort", "Runs"),
    MenuColumn("position_sort", "Position"),
    MenuColumn("total_sort", "Total players"),
    MenuColumn("percentile_sort", "Percentile"),
    MenuColumn("pb_score_sort", "PB score"),
    MenuColumn("pb_timestamp_sort", "PB date"),
    MenuColumn("pb_cm360_sort", "PB cm/360"),
    MenuColumn("pb_accuracy_sort", "PB accuracy"),
]

# Rendered only on a benchmark's table, so a playlist's table leaves their
# stored choices alone.
BENCHMARK_MENU_COLUMNS = [
    MenuColumn("tier_sort", "Rank"),
    MenuColumn("next_tier_sort", "Next rank"),
]

# The names ``?sort=`` uses in the address bar, mapped to column IDs. Other code
# keys on the column IDs, so the names exist only where the URL is read and
# written: a saved link survives a field rename, and "rank" never names the
# Position column (Rank is the benchmark tier).
SORT_URL_NAMES = {
    "scenario": "scenario",
    "last-played": "last_played_sort",
    "runs": "runs_sort",
    "position": "position_sort",
    "total-players": "total_sort",
    "percentile": "percentile_sort",
    "pb-score": "pb_score_sort",
    "rank": "tier_sort",
    "next-rank": "next_tier_sort",
    "pb-date": "pb_timestamp_sort",
    "pb-cm360": "pb_cm360_sort",
    "pb-accuracy": "pb_accuracy_sort",
}
SORT_DIRECTIONS = ("asc", "desc")


def _parse_sort(sort: object, column_ids: Collection[str]) -> list[tuple[str, str]]:
    """Read a ``?sort=`` value as ``(column ID, direction)`` pairs, by priority.

    Anything not entirely valid reads as unsorted, an empty list: a missing,
    empty, or repeated parameter, an unknown name, a name for a column not in
    ``column_ids``, a bad direction, or a duplicate name, which also caps the
    list at one entry per column. Matching is exact, and no valid part of a
    mixed value is kept.
    """
    if not isinstance(sort, str) or not sort:
        return []
    directions_by_id: dict[str, str] = {}
    for entry in sort.split(","):
        name, _, direction = entry.partition(".")
        column_id = SORT_URL_NAMES.get(name)
        # The name table serves every page, but only a benchmark's table has
        # Rank and Next Rank. Seeding a column the page lacks raises KeyError.
        if (
            column_id is None
            or column_id not in column_ids
            or direction not in SORT_DIRECTIONS
            or column_id in directions_by_id
        ):
            return []
        directions_by_id[column_id] = direction
    return list(directions_by_id.items())


def _group_columns(playlist_code: str | None) -> tuple[GroupColumn, ...]:
    """List the group columns a playlist's table shows, one per level it names.

    Empty for a table without groups. A benchmark with one level of grouping
    has categories only.
    """
    groups = get_scenario_groups(playlist_code) if playlist_code else None
    if groups is None:
        return ()
    if any(group.subcategory for group in groups):
        return GROUP_COLUMNS
    return (CATEGORY_COLUMN,)


def _column_defs(
    sort: object,
    *,
    benchmark: bool,
    group_columns: Sequence[GroupColumn] = (),
) -> list[dict]:
    """Copy the column defs, seeding the grid's opening sort from ``?sort=``.

    A benchmark's table adds Rank and Next Rank directly after PB Score, and
    ``group_columns`` ahead of Scenario. A fresh copy per call, because the
    module's column defs are shared across requests. The seed is
    ``initialSort``, never ``sort``: AG Grid reapplies ``sort`` whenever
    column defs arrive again, overriding the user's header clicks.
    """
    column_defs: list[dict] = copy.deepcopy(TABLE_COLUMN_DEFS)
    if benchmark:
        fields = [column["field"] for column in column_defs]
        after_pb_score = fields.index("pb_score_sort") + 1
        column_defs[after_pb_score:after_pb_score] = copy.deepcopy(
            BENCHMARK_COLUMN_DEFS
        )
    columns_by_id = {column["field"]: column for column in column_defs}
    for sort_index, (column_id, direction) in enumerate(
        _parse_sort(sort, columns_by_id)
    ):
        columns_by_id[column_id]["initialSort"] = direction
        columns_by_id[column_id]["initialSortIndex"] = sort_index
    if group_columns:
        # The Scenario cell names the row's group under the scenario while
        # the table is ungrouped, for the levels whose columns are shown.
        columns_by_id["scenario"]["cellRendererParams"] = {
            "groupLevels": [
                {"columnId": column.column_id, "nameField": column.name_field}
                for column in group_columns
            ]
        }
        column_defs[0:0] = [_group_column_def(column) for column in group_columns]
    return column_defs


def _opens_grouped(sort: object, *, benchmark: bool) -> bool:
    """Tell whether the table opens in playlist order, which is grouped.

    A link that carries a valid ``?sort=`` opens ungrouped. The filter box is
    always empty as the page opens.
    """
    column_ids = [column["field"] for column in _column_defs(None, benchmark=benchmark)]
    return not _parse_sort(sort, column_ids)


def _menu_columns(
    *,
    benchmark: bool,
    group_columns: Sequence[GroupColumn] = (),
) -> list[MenuColumn]:
    """List the Columns menu's entries in the order the table shows them."""
    columns = list(MENU_COLUMNS)
    if benchmark:
        column_ids = [column.column_id for column in columns]
        after_pb_score = column_ids.index("pb_score_sort") + 1
        columns[after_pb_score:after_pb_score] = BENCHMARK_MENU_COLUMNS
    # Rendered only for the levels the table has, as Rank and Next rank are
    # only on a benchmark's table, so a table without groups leaves the stored
    # choices alone. The labels are the headers' own words.
    return [
        *(MenuColumn(column.column_id, column.header) for column in group_columns),
        *columns,
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
        return [], f"No imported playlist has the code {playlist_code}.", None, True

    generation_token = uuid4().hex
    rows = build_playlist_scenario_rank_rows(playlist_code, generation_token)
    if not get_kovaaks_username():
        # Without a username every per-scenario lookup short-circuits offline
        # to UNKNOWN, so phase 2 would fetch nothing and settle every position
        # as unavailable. That is persistent configuration state, not a
        # failure: skip the fill and say so in place instead. Nothing on screen
        # can contradict the line -- the service's no-username guard fires
        # before any cache read, so every position cell renders N/A.
        _clear_pending_flags(rows)
        return rows, _username_unset_status(), None, True
    # Registration deliberately happens only after the phase-1 rows exist. A
    # spurious/fast interval tick must never drain updates into an empty grid.
    if not start_playlist_scenario_fill(playlist_code, generation_token):
        # A concurrent delete can remove the playlist between phase 1 and
        # registration. With no fill to settle the rows, clear every pending
        # flag here so the disabled interval cannot strand animation forever.
        _clear_pending_flags(rows)
        return rows, "Update interrupted", None, True
    status = _live_fill_status(0, len(rows))
    return rows, status, generation_token, False


def _clear_pending_flags(rows: list[dict]) -> None:
    """Settle every position cell for rows no fill will ever update."""
    for row in rows:
        row["position_pending"] = False
        row["total_pending"] = False
        row["percentile_pending"] = False


def _username_unset_status() -> list:
    """State the unset-username condition in the grid's own status line.

    Built fresh per call rather than shared at module scope: the value is a
    callback output, and a mutable component list must not be reused across
    requests.
    """
    return [
        "Positions unavailable. Set your KovaaK's username in ",
        dmc.Anchor("Settings", href="/settings", refresh=False),
        ".",
    ]


def _live_fill_status(done_count: int, total: int) -> str:
    return f"Updating positions from KovaaK's… {done_count}/{total}"


def _settled_fill_status(fill: PlaylistScenarioFillDrain) -> str:
    if fill.terminal == "cancelled":
        return f"Update interrupted · {fill.done_count} of {fill.total} refreshed"
    if fill.unknown_count:
        status = f"{fill.unknown_count} of {fill.total} positions unavailable"
        if fill.stale_count:
            status += f" · {fill.stale_count} from cache · KovaaK's unreachable"
        return status
    if fill.stale_count:
        return (
            f"{fill.stale_count} of {fill.total} positions from cache · "
            "KovaaK's unreachable"
        )
    return ""


@callback(
    Output("playlist-scenarios-grid", "rowTransaction"),
    Output("playlist-scenarios-status", "children", allow_duplicate=True),
    Input("playlist-scenarios-fill-interval", "n_intervals"),
    State("playlist-scenarios-generation", "data"),
    prevent_initial_call=True,
)
def drain_playlist_scenario_rows(_n_intervals, generation_token):
    """Apply streamed rows and settle the status when the fill ends."""
    # DashProxy can phantom-fire allow_duplicate callbacks on initial load.
    if not generation_token:
        return no_update, no_update
    fill = drain_playlist_scenario_fill(generation_token)
    if fill is None:
        return no_update, no_update

    transaction = {"update": fill.updates} if fill.updates else no_update
    if fill.terminal is None:
        return transaction, _live_fill_status(fill.done_count, fill.total)
    return transaction, _settled_fill_status(fill)


clientside_callback(
    """
    async (_nIntervals) => {
        if (!window.dash_ag_grid || !window.dash_ag_grid.getApiAsync) {
            return window.dash_clientside.no_update;
        }

        try {
            const gridApi = await window.dash_ag_grid.getApiAsync("playlist-scenarios-grid");
            gridApi.refreshCells({force: true, columns: ["last_played_sort", "pb_timestamp_sort"]});
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


# Keep ``?sort=`` in step with the table, so Back, a reload, or a copied link
# reopens the page with the sort the user left it in.
clientside_callback(
    """
    (columnState, playlistCode) => {
        const noUpdate = window.dash_clientside.no_update;
        const namesByColumnId = SORT_NAMES_BY_COLUMN_ID;
        // Until the grid initializes there is no column state. Reading that
        // as "unsorted" would strip ?sort= from the address on arrival.
        if (
            !Array.isArray(columnState)
            || columnState.length === 0
            || !columnState.every((column) => column && typeof column.colId === "string")
            || typeof playlistCode !== "string"
            || !playlistCode
        ) {
            return noUpdate;
        }
        // A row click moves the address to another page before this grid
        // unmounts, so a late publish must not write there. Dash Pages hands
        // the page its path segment undecoded, so compare the raw pathname.
        if (window.location.pathname !== "/playlists/" + playlistCode) {
            return noUpdate;
        }
        const sorted = columnState
            .map((column, position) => ({column, position}))
            .filter(({column}) => column.sort === "asc" || column.sort === "desc")
            .sort((a, b) =>
                (a.column.sortIndex ?? a.position) - (b.column.sortIndex ?? b.position)
            );
        if (sorted.some(({column}) => !Object.hasOwn(namesByColumnId, column.colId))) {
            return noUpdate;
        }
        const value = sorted
            .map(({column}) => namesByColumnId[column.colId] + "." + column.sort)
            .join(",");
        const current = new URLSearchParams(window.location.search).getAll("sort");
        if (value ? current.length === 1 && current[0] === value : current.length === 0) {
            return noUpdate;
        }
        // Built by hand because URLSearchParams would write the commas as %2C.
        const kept = window.location.search
            .slice(1)
            .split("&")
            .filter((pair) => pair && new URLSearchParams(pair).keys().next().value !== "sort");
        if (value) {
            kept.push("sort=" + value);
        }
        const search = kept.length ? "?" + kept.join("&") : "";
        // Never through a dcc.Location prop: that pushes a history entry and
        // makes Dash Pages re-render the page on every sort click. A raw
        // replaceState fires no event Dash listens for.
        window.history.replaceState(
            window.history.state,
            "",
            window.location.pathname + search + window.location.hash
        );
        return noUpdate;
    }
    """.replace(
        "SORT_NAMES_BY_COLUMN_ID",
        json.dumps({column_id: name for name, column_id in SORT_URL_NAMES.items()}),
    ),
    Output("playlist-scenarios-sort-sink", "data"),
    Input("playlist-scenarios-grid", "columnState"),
    State("playlist-scenarios-code", "data"),
)


# Keep the table's grouped or ungrouped state in step with its sort, the
# filter box, and the group columns' visibility, and redraw the cells that
# read it. The state lives on the grid's ``context`` object, which the group
# and Scenario renderers read as they draw. It is one flag for the whole
# table: grouped while the table is in playlist order with an empty filter
# box.
#
# The column state is only this callback's trigger. Everything it reads comes
# from the grid API after the wait, so a run that waited longer for the grid
# still sees the grid as it is. It never writes the ``columnState`` prop,
# which would also set the column order.
#
# The Columns menu redraws no cells, so a change to a group column's
# visibility is redrawn here even when the state itself did not change: the
# Scenario cell's second line names only the levels still shown.
#
# The callback also installs, once per grid, the repair for the grid's own
# stale merged cells, which its source explains.
clientside_callback(
    """
    (() => {
        let latestRun = 0;
        const repairedGrids = new WeakSet();

        // A workaround for a defect in AG Grid 35.3.1, the version
        // dash-ag-grid 35.3.0 bundles. The grid keeps a merged cell's control
        // across row-model updates without refreshing it, so two sort changes
        // and then none, the three header clicks that clear a sort, leave
        // merged cells at a stale height and rows with no group cell at all.
        // No refresh or redraw call repairs that. Hiding and showing the
        // group columns does, because the grid then builds those cells again.
        // AG Grid 36.1.0 fixed the defect (measured 2026-10-06). Remove this
        // when dash-ag-grid bundles that version or a later one: the
        // decision-log entry for the group columns has the evidence.
        const repairSpansAfterModelUpdates = (gridApi) => {
            if (repairedGrids.has(gridApi)) {
                return;
            }
            repairedGrids.add(gridApi);
            gridApi.addEventListener("modelUpdated", () => {
                // The grid rebuilds its own record of the merges in answer
                // to this same event, so the repair waits one task for it.
                window.setTimeout(() => {
                    if (gridApi.isDestroyed()) {
                        return;
                    }
                    // Only the columns showing now: one the Columns menu
                    // has hidden must stay hidden.
                    const shown = GROUP_COLUMN_IDS.filter((colId) => {
                        const column = gridApi.getColumn(colId);
                        return column && column.isVisible();
                    });
                    gridApi.setColumnsVisible(shown, false);
                    gridApi.setColumnsVisible(shown, true);
                }, 0);
            });
        };

        return async (_columnState, filterText) => {
            const noUpdate = window.dash_clientside.no_update;
            if (!window.dash_ag_grid || !window.dash_ag_grid.getApiAsync) {
                return noUpdate;
            }

            latestRun += 1;
            const run = latestRun;
            try {
                const gridApi = await window.dash_ag_grid.getApiAsync("playlist-scenarios-grid");
                if (gridApi.getGridOption("enableCellSpan")) {
                    repairSpansAfterModelUpdates(gridApi);
                }
                // The filter text is this run's own argument, so an older run
                // that lands late would put an old state back.
                if (run !== latestRun) {
                    return noUpdate;
                }
                const groupColumnIds = GROUP_COLUMN_IDS.filter(
                    (colId) => gridApi.getColumn(colId)
                );
                const context = gridApi.getGridOption("context");
                if (groupColumnIds.length === 0 || !context) {
                    return noUpdate;
                }
                const sorted = gridApi
                    .getColumnState()
                    .some((column) => column.sort === "asc" || column.sort === "desc");
                const grouped = !sorted && !(filterText || "").trim();
                const shown = groupColumnIds
                    .filter((colId) => gridApi.getColumn(colId).isVisible())
                    .join(",");
                if (context.grouped === grouped && context.shownGroupColumns === shown) {
                    return noUpdate;
                }
                context.grouped = grouped;
                context.shownGroupColumns = shown;
                gridApi.refreshCells({
                    force: true,
                    columns: [...groupColumnIds, "scenario"],
                });
            } catch (error) {
                console.warn("Failed to set the playlist scenario table's grouped state.", error);
            }
            return noUpdate;
        };
    })()
    """.replace(
        "GROUP_COLUMN_IDS",
        json.dumps([column.column_id for column in GROUP_COLUMNS]),
    ),
    Output("playlist-scenarios-group-sink", "data"),
    Input("playlist-scenarios-grid", "columnState"),
    Input("playlist-scenarios-quick-filter", "value"),
)


register_columns_menu(COLUMNS_MENU_ID, "playlist-scenarios-grid")


# The Evxl link's tooltip and its accessible name: the link shows only a
# logo, so this is the one place its name is written.
EVXL_LINK_LABEL = "View on Evxl"
# ``Any`` because ``html.A`` takes ``aria-*`` as wildcard keywords: mypy
# checks a ``dict[str, str]`` against every other parameter and fails.
_EVXL_LINK_NAME: dict[str, Any] = {"aria-label": EVXL_LINK_LABEL}


def _page_header(playlist_code: str, *, benchmark: bool) -> dmc.Group:
    """Title the page with the playlist's display label and its share code.

    A benchmark that Evxl has a page for also gets a link to that page: Evxl's
    logo, named by a tooltip.
    """
    children = [
        dmc.Title(get_playlist_display_label(playlist_code), order=2),
        dmc.Text(playlist_code, c="dimmed", size="sm"),
    ]
    evxl_url = evxl_benchmark_url(playlist_code, get_steam_id()) if benchmark else None
    if evxl_url is not None:
        children.append(
            dmc.Tooltip(
                # ``html.A``, not ``dmc.Anchor``: the Mantine wrapper
                # percent-decodes an href before rendering it, which turns an
                # encoded ``/`` or ``#`` in a benchmark name into a path
                # separator or a fragment.
                html.A(
                    local_icon("evxl:logo", height=24),
                    id="playlist-scenarios-evxl-link",
                    # ``mantine-focus-auto`` is the keyboard focus ring
                    # ``dmc.Anchor`` would have brought. Without it the ring
                    # is the browser's own, which is near-black in Chromium
                    # and can't be seen on the dark theme.
                    className="playlist-scenarios-evxl-link mantine-focus-auto",
                    href=evxl_url,
                    target="_blank",
                    # The icon is hidden from assistive technology, so the
                    # link would have no name without this.
                    **_EVXL_LINK_NAME,
                ),
                label=EVXL_LINK_LABEL,
                # On keyboard focus too: the tooltip is the only place the
                # link's name is written.
                events={"hover": True, "focus": True, "touch": False},
                boxWrapperProps={"className": "playlist-scenarios-evxl-link-box"},
            )
        )
    return dmc.Group(align="baseline", gap="sm", children=children)


def layout(
    playlist_code: str | None = None,
    sort: str | list[str] | None = None,
    **kwargs,  # noqa: ARG001
):
    """Build the per-playlist scenario table page.

    ``sort`` is the raw ``?sort=`` query value, which Dash Pages passes as a
    string, or as a list when the parameter repeats.
    """
    playlist = get_playlist_by_code(playlist_code) if playlist_code else None
    benchmark = playlist is not None and is_benchmark_playlist(playlist)
    group_columns = _group_columns(playlist_code)
    grid_options: dict[str, Any] = {**COLUMNS_MENU_GRID_OPTIONS}
    if group_columns:
        # Cell spanning rules out some grid features on the same grid: the
        # grid-wide ``enableCellTextSelection``, click row selection, cell
        # selection, and editing or row dragging on a spanning column (read
        # from the validation rules in the AG Grid 35.3.1 bundle). The table
        # uses none of them, and the Leaderboard ID cell's selectable text
        # comes from a cell class, not from the grid-wide option. It is an
        # initial option, so it is set only on a table that has groups.
        grid_options["enableCellSpan"] = True
        grid_options["context"] = {"grouped": _opens_grouped(sort, benchmark=benchmark)}
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
            # Dummy sinks for the client-side quick-filter, sort-URL,
            # grouped-state, and Columns menu callbacks' outputs.
            dcc.Store(id="playlist-scenarios-quick-filter-sink"),
            dcc.Store(id="playlist-scenarios-sort-sink"),
            dcc.Store(id="playlist-scenarios-group-sink"),
            columns_menu_sink(COLUMNS_MENU_ID),
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
            *(
                [_page_header(playlist_code, benchmark=benchmark)]
                if playlist_code is not None
                else []
            ),
            dmc.Group(
                children=[
                    dmc.Group(
                        children=[
                            dmc.TextInput(
                                id="playlist-scenarios-quick-filter",
                                placeholder="Filter scenarios",
                                size="sm",
                                w=240,
                            ),
                            dmc.Text("", c="dimmed", id="playlist-scenarios-status"),
                        ],
                        gap="md",
                        align="center",
                    ),
                    columns_menu(
                        COLUMNS_MENU_ID,
                        _menu_columns(benchmark=benchmark, group_columns=group_columns),
                    ),
                ],
                justify="space-between",
            ),
            dag.AgGrid(
                id="playlist-scenarios-grid",
                className="ag-theme-quartz playlist-scenarios-grid",
                columnDefs=_column_defs(
                    sort, benchmark=benchmark, group_columns=group_columns
                ),
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
                    **grid_options,
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
        className="page-fill-column",
    )
