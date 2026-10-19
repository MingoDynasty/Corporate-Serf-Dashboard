"""The run list on the Run History page: its layout, its callbacks, its script.

The rows themselves are ``tests/test_run_history_list.py``. These tests hold
what puts them on the page: a grid given no rows, the options that make a
flat grid read as sessions with runs under them, the three callbacks that
decide when the list is rebuilt, and the text of the script that draws it.
No test runs the script, as none runs any script in the repository. Its
behavior is checked in a browser.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path

import dash
import dash_ag_grid as dag
import dash_mantine_components as dmc
import pytest
from dash import no_update
from dash._callback import (
    GLOBAL_CALLBACK_LIST,
    GLOBAL_CALLBACK_MAP,
    GLOBAL_INLINE_SCRIPTS,
)

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.components import (  # noqa: E402
    columns_menu,
    run_history_list,
    scenario_selection,
)
from source.components.run_history_list import (  # noqa: E402
    RUN_LIST_CLASS,
    RUN_LIST_NOTHING_CLASS,
    RUN_LIST_UNSELECTED_CLASS,
    SESSIONS_PER_LOAD,
    VIEW_ALL,
    VIEW_SCENARIO,
    build_run_list,
    build_session_tree,
    empty_run_list,
    jump_to_session,
)
from source.components.run_marks import mark_runs  # noqa: E402
from source.kovaaks.data_models import RunData  # noqa: E402
from source.pages import run_history  # noqa: E402
from source.plot import plot_service  # noqa: E402
from tests.rendered_text import rendered_text  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
STYLESHEET = REPO_ROOT / "assets" / "stylesheet.css"
LIST_SCRIPT = REPO_ROOT / "assets" / "runHistoryList.js"
IDS = run_history.RUN_LIST_IDS
SCENARIO = "Scenario A"
# The list's column is 500px. Its border takes 2px, and a classic scrollbar
# is 17px in the widest browser the app is used in.
LIST_COLUMN_PX = 500
BORDER_PX = 2
SCROLLBAR_PX = 17
# A scrollbar drawn over the rows, as Firefox draws it on Windows 11 by
# default, is 12px wide with the pointer on it in Firefox 158.
OVERLAY_SCROLLBAR_PX = 12


def _walk_components(component):
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk_components(child)
        return
    yield from _walk_components(children)


def _by_id(page, component_id):
    return next(
        component
        for component in _walk_components(page)
        if getattr(component, "id", None) == component_id
    )


def _grid(page=None) -> dag.AgGrid:
    return _by_id(page or run_history.layout(), IDS.grid)


def _options() -> dict:
    return _grid().dashGridOptions


def _registration(output_fragment: str) -> dict:
    (registration,) = [
        entry for entry in GLOBAL_CALLBACK_LIST if output_fragment in entry["output"]
    ]
    return registration


def _keys(dependencies) -> list[str]:
    return [f"{dep['id']}.{dep['property']}" for dep in dependencies]


@pytest.fixture(autouse=True)
def quiet_lists(monkeypatch):
    """Keep the playlist and scenario stores out of the way of the layout."""
    monkeypatch.setattr(
        scenario_selection, "get_visible_playlist_selector_options", lambda: []
    )
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: ["All"])


# --- The layout ----------------------------------------------------------------


def test_the_list_holds_its_header_the_grid_and_the_text_for_nothing_to_list():
    panel = _by_id(run_history.layout(), IDS.panel)

    header, grid, empty, announcer = panel.children
    assert panel.className == RUN_LIST_CLASS
    assert header.className == "run-history-list-header"
    heading, switch, actions = header.children
    assert (heading.id, switch.id) == (IDS.heading, IDS.view)
    # The switch at the left of the header's line, the two buttons at its right.
    assert actions.className == "run-history-list-actions"
    expand_all, menu = actions.children
    assert expand_all.id == IDS.expand_all
    assert isinstance(menu, dmc.Popover)
    assert (grid.id, empty.id, announcer.id) == (IDS.grid, IDS.empty, IDS.announcer)


def test_the_switch_chooses_between_the_two_views_and_starts_on_this_scenario():
    switch = _by_id(run_history.layout(), IDS.view)

    assert isinstance(switch, dmc.SegmentedControl)
    assert switch.data == [
        {"value": "scenario", "label": "This scenario"},
        {"value": "all", "label": "All scenarios"},
    ]
    # Chosen once: a renamed id or a changed default resets the stored view
    # in every browser.
    assert (IDS.view, switch.value, switch.persistence) == (
        "run-history-list-view",
        "scenario",
        True,
    )
    assert switch.to_plotly_json()["props"]["aria-label"] == "Run list view"


def test_the_buttons_read_expand_all_and_columns():
    panel = _by_id(run_history.layout(), IDS.panel)

    assert _by_id(panel, IDS.expand_all).children == "Expand all"
    assert rendered_text(_by_id(panel, f"{IDS.columns_menu}-button")) == "Columns"


def test_the_grid_is_given_no_rows():
    """Rows go in through the grid's API, so the pinned row and the body rows
    change together. A ``rowData`` prop would be a second way in.
    """
    grid = _grid()

    assert getattr(grid, "rowData", None) is None
    assert getattr(grid, "rowTransaction", None) is None
    assert "pinnedTopRowData" not in grid.dashGridOptions
    assert grid.getRowId == "params.data.id"


def test_the_grid_keeps_row_virtualization():
    """It is why the grid was chosen: about 39 row elements whatever is open."""
    options = _options()

    assert "suppressRowVirtualisation" not in options
    assert "suppressMaxRenderedRowRestriction" not in options


def test_a_session_row_is_a_full_width_row_drawn_by_the_lists_own_renderer():
    options = _options()

    assert options["isFullWidthRow"] == {"function": "runListIsFullWidth(params)"}
    assert options["fullWidthCellRenderer"] == "RunListWideRow"


def test_opening_and_closing_is_an_external_filter():
    options = _options()

    assert options["isExternalFilterPresent"] == {"function": "true"}
    assert options["doesExternalFilterPass"] == {
        "function": "runListFilterPass(params)"
    }


def test_the_two_kinds_of_row_are_kept_in_reading_order():
    options = _options()

    assert options["embedFullWidthRows"] is True
    assert options["ensureDomOrder"] is True


def test_keys_on_a_row_reach_the_lists_own_handler():
    assert _grid().eventListeners == {"cellKeyDown": ["runListKeyDown(params)"]}


def test_no_column_sorts_moves_or_resizes():
    """A sort would scatter each session's rows."""
    grid = _grid()

    assert grid.defaultColDef == {
        "sortable": False,
        "resizable": False,
        "suppressMovable": True,
    }
    assert not [column for column in grid.columnDefs if column.get("sortable")]


def test_a_run_that_lands_does_not_scroll_the_list_by_itself():
    assert _options()["suppressScrollOnNewData"] is True


def test_the_grid_shows_none_of_its_own_overlays():
    """It would say "No Matching Rows" over a list whose one session is closed."""
    assert _options()["suppressOverlays"] == ["loading", "noRows", "noMatchingRows"]


def test_every_function_the_grid_names_is_named_bare_and_defined_by_the_script():
    """A ``{"function": ...}`` string is run with the functions as bare names."""
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    grid = _grid()
    strings = [
        value["function"]
        for value in grid.dashGridOptions.values()
        if isinstance(value, dict) and "function" in value
    ] + grid.eventListeners["cellKeyDown"]

    named = {match for text in strings for match in re.findall(r"(\w+)\(", text)}
    assert named == {
        "runListIsFullWidth",
        "runListFilterPass",
        "runListRowHeight",
        "runListRowClass",
        "runListKeyDown",
    }
    assert not [text for text in strings if "dagfuncs." in text]
    for name in named:
        assert f"dagfuncs.{name} = function" in script
    renderers = {
        grid.dashGridOptions["fullWidthCellRenderer"],
        *[
            column["cellRenderer"]
            for column in grid.columnDefs
            if "cellRenderer" in column
        ],
    }
    assert renderers == {"RunListWideRow", "RunListMarks"}
    for name in renderers:
        assert f"dagcomponentfuncs.{name} = function" in script


# --- The columns ---------------------------------------------------------------


def test_the_seven_columns_are_headed_as_the_copy_has_them():
    assert [column["headerName"] for column in _grid().columnDefs] == [
        "#",
        "Time",
        "Score",
        "Marks",
        "Accuracy",
        "Shots Fired",
        "Sensitivity",
    ]


def test_the_marks_column_has_a_name_and_shows_no_header():
    (marks,) = [c for c in _grid().columnDefs if c.get("colId") == "marks"]
    css = STYLESHEET.read_text(encoding="utf-8")

    assert marks["headerName"] == "Marks"
    assert marks["headerClass"] == "run-list-header-unseen"
    assert "clip-path: inset(50%);" in _css_block(
        css, ".run-history-list-grid .run-list-header-unseen .ag-header-cell-text"
    )


def test_every_column_but_the_marks_has_one_allowed_width():
    """The Columns menu fits a column it shows to its content.

    A column whose minimum and maximum are its width comes out of that fit
    unchanged, so the widths that leave room for the scrollbar stay put.
    """
    fixed = [c for c in _grid().columnDefs if c.get("colId") != "marks"]

    assert len(fixed) == 6
    for column in fixed:
        assert column["width"] == column["minWidth"] == column["maxWidth"]
    (marks,) = [c for c in _grid().columnDefs if c.get("colId") == "marks"]
    assert marks["flex"] == 1
    assert "width" not in marks


def test_the_columns_leave_room_for_the_scrollbar():
    columns = _grid().columnDefs
    narrowest = sum(column.get("width", column.get("minWidth")) for column in columns)

    assert narrowest <= LIST_COLUMN_PX - BORDER_PX - SCROLLBAR_PX
    css = STYLESHEET.read_text(encoding="utf-8")
    assert f"--run-history-list-width: {LIST_COLUMN_PX}px;" in _css_block(
        css, ".run-history-page"
    )
    assert (
        "grid-template-columns: minmax(0, 1fr) var(--run-history-list-width);"
        in _css_block(css, ".run-history-columns")
    )


def test_a_scrollbar_drawn_over_the_rows_gets_room_beside_them():
    """A scrollbar that takes no room of its own covered the last column.

    The grid marks such a scrollbar invisible. Keyed on that mark, the body
    and the pinned row both keep its width free, so the two stay in line, and
    the marks column gives the room up without going under its minimum.
    """
    css = STYLESHEET.read_text(encoding="utf-8")
    room = _css_block(
        css,
        ".run-history-list-grid:has(.ag-body-vertical-scroll.ag-scrollbar-invisible)\n"
        "    :is(.ag-center-cols-viewport, .ag-floating-top-viewport)",
    )

    assert f"padding-right: {OVERLAY_SCROLLBAR_PX}px;" in room
    columns = _grid().columnDefs
    fixed = sum(column["width"] for column in columns if "width" in column)
    (marks,) = [c for c in columns if c.get("colId") == "marks"]
    marks_room = LIST_COLUMN_PX - BORDER_PX - OVERLAY_SCROLLBAR_PX - fixed
    assert marks_room >= marks["minWidth"]


def test_the_run_numbers_room_moves_with_its_indent():
    """The # column's width and its padding move together.

    The number's room is what the two leave, less a cell's 4px on the right:
    22px, as it was at 56px and 30px.
    """
    (number,) = [c for c in _grid().columnDefs if c.get("field") == "n"]
    css = STYLESHEET.read_text(encoding="utf-8")
    indent = re.search(
        r"padding-left: (\d+)px;",
        _css_block(css, ".run-history-list-grid .run-list-number"),
    )

    assert indent
    assert number["width"] - int(indent.group(1)) - 4 == 22


def test_each_column_shows_a_field_the_rows_carry():
    fields = {column["field"] for column in _grid().columnDefs if "field" in column}

    assert fields <= set(_sample_rows()["run"])


# --- The Columns menu ----------------------------------------------------------


def _menu_checkboxes(page=None) -> list[dmc.Checkbox]:
    return [
        component
        for component in _walk_components(page or run_history.layout())
        if isinstance(component, dmc.Checkbox)
        and isinstance(component.id, dict)
        and component.id.get("type") == IDS.columns_menu
    ]


def _choice_checkboxes(page=None) -> list[dmc.Checkbox]:
    return [
        component
        for component in _walk_components(page or run_history.layout())
        if isinstance(component, dmc.Checkbox)
        and isinstance(component.id, dict)
        and component.id.get("type") == f"{IDS.columns_menu}-choice"
    ]


def test_the_columns_menu_offers_two_columns_both_shown_and_median_and_best_off():
    checkboxes = _menu_checkboxes()

    assert [(box.label, box.checked, box.persistence) for box in checkboxes] == [
        ("Shots Fired", True, True),
        ("Sensitivity", True, True),
    ]
    # Not a column, so not a checkbox the column callback hears.
    assert [
        (box.id, box.label, box.checked, box.persistence)
        for box in _choice_checkboxes()
    ] == [
        (
            {"type": "run-history-list-columns-choice", "choice": "median_best"},
            "Median and best",
            False,
            True,
        )
    ]
    # Each checkbox is named for the header of the column it shows.
    headers = {
        column["field"]: column["headerName"]
        for column in _grid().columnDefs
        if "field" in column
    }
    assert [headers[box.id["column"]] for box in checkboxes] == [
        "Shots Fired",
        "Sensitivity",
    ]


def test_the_menus_ids_are_the_ones_browsers_store_its_choices_under():
    assert [box.id for box in _menu_checkboxes()] == [
        {"type": "run-history-list-columns", "column": "shots"},
        {"type": "run-history-list-columns", "column": "sens"},
    ]


def test_no_column_starts_hidden_so_the_menus_defaults_match_the_grid():
    assert not [column for column in _grid().columnDefs if column.get("hide")]


@pytest.mark.parametrize(
    "query",
    [{}, {"scenario": SCENARIO, "playlist_code": "KovaaKsTestCode"}],
    ids=["plain", "deep_linked"],
)
def test_the_menus_layout_default_never_varies(query):
    page = run_history.layout(**query)

    assert [box.checked for box in _menu_checkboxes(page)] == [True, True]
    assert [box.checked for box in _choice_checkboxes(page)] == [False]


def test_the_grid_is_built_with_the_options_the_columns_menu_needs():
    options = _options()

    for key, value in columns_menu.COLUMNS_MENU_GRID_OPTIONS.items():
        assert options[key] == value


def test_the_columns_menu_is_registered_for_the_lists_grid():
    registration = _registration(f"{IDS.columns_menu}-sink.data")
    source = _inline_script(registration)

    assert f'getApiAsync("{IDS.grid}")' in source


# --- What the script is handed with the grid -----------------------------------


def test_the_scripts_copy_and_ids_come_with_the_grid():
    """So the script holds no string a reader sees."""
    context = _options()["context"]

    assert context == {
        "gridId": IDS.grid,
        # Show older sessions adds to the count of the view it is pressed in.
        "limitStoreIds": {
            "scenario": IDS.session_limit,
            "all": IDS.all_session_limit,
        },
        "jumpStoreId": IDS.jump,
        "askStoreId": IDS.scenario_asked,
        "expandAllId": IDS.expand_all,
        "announcerId": IDS.announcer,
        "sessionsPerLoad": 30,
        "treeView": "all",
        "runRowIdPrefix": "r:",
        "labels": {
            "expandAll": "Expand all",
            "collapseAll": "Collapse all",
            "showAllRuns": "Show all runs",
            "hideAllRuns": "Hide all runs",
            "session": "Session",
            "scenario": "Scenario",
            "expanded": "Expanded",
            "collapsed": "Collapsed",
            "inProgress": "In progress",
            "lengthHelp": (
                "The length runs from the first run to the last run. It doesn't "
                "count the time since your last run."
            ),
            "wholeSession": "Show the whole session",
            "newPb": "New PB",
            # The figures' words, which This scenario draws in columns.
            "median": "Median",
            "best": "Best",
            "score": "Score",
        },
    }


def test_a_run_rows_id_starts_with_the_prefix_the_script_finds_a_mark_by():
    """The script finds the row of a view's mark by this prefix and the run's id."""
    prefix = _options()["context"]["runRowIdPrefix"]

    for kind in ("run", "tree_run"):
        assert _sample_rows()[kind]["id"].startswith(prefix)


def test_the_script_asks_the_grid_for_nothing_it_was_not_handed():
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    context = _options()["context"]

    assert set(re.findall(r"\bcontext\.(\w+)", script)) <= set(context)
    assert set(re.findall(r"\blabels\.(\w+)", script)) <= set(context["labels"])


def test_the_script_holds_none_of_the_lists_copy():
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    context = _options()["context"]
    copy = [
        *context["labels"].values(),
        "Show older sessions",
        "Not played in this session",
        "Threshold passed",
        "Below threshold",
        "Not judged",
        "No runs yet",
        "No scenario selected",
        "This scenario",
        "All scenarios",
        "Run list view",
        "Runs of",
        "Show ",
        "Selected scenario",
        "Median",
        "Best",
        "Score ",
    ]

    assert not [text for text in copy if f'"{text}' in script]


def _sample_rows() -> dict[str, dict]:
    """Build lists that between them hold a row of every kind, and return one of each.

    The tree's run row and session row carry fields This scenario's do not,
    so they are kept as ``tree_run`` and ``tree_session``.
    """
    late = datetime(2026, 10, 11, 23, 30)

    def run(scenario: str, ended: datetime) -> RunData:
        return RunData(
            datetime_object=ended,
            score=100.0,
            sens_scale="cm/360",
            horizontal_sens=40.8,
            scenario=scenario,
            accuracy=0.5,
            stats_file_name=(
                f"{scenario} - Challenge - {ended:%Y.%m.%d-%H.%M.%S} Stats.csv"
            ),
            shots_fired=200,
        )

    runs = [
        run(SCENARIO, late - timedelta(days=2)),
        run(SCENARIO, late - timedelta(days=1)),
        # One session that crosses midnight, left and returned to.
        run(SCENARIO, late + timedelta(minutes=10)),
        run("Scenario B", late + timedelta(minutes=20)),
        run(SCENARIO, late + timedelta(minutes=40)),
    ]
    now = late + timedelta(minutes=41)
    marks = {}
    for scenario in (SCENARIO, "Scenario B"):
        marks.update(
            mark_runs(
                [r for r in runs if r.scenario == scenario], 95.0, lambda _version: None
            )
        )
    listed = build_run_list(runs, SCENARIO, 2, now, marks)
    never_played = build_run_list(runs, "Scenario C", 2, now, {})
    tree = build_session_tree(runs, SCENARIO, 2, now, marks)
    rows = {row["kind"]: row for row in [*listed["rows"], *never_played["rows"]]}
    assert set(rows) == {"session", "run", "divider", "date", "note", "more"}
    tree_rows = {row["kind"]: row for row in tree["rows"]}
    assert set(tree_rows) == {"session", "scenario", "run", "date", "more"}
    rows["scenario"] = tree_rows["scenario"]
    rows["tree_run"] = tree_rows["run"]
    rows["tree_session"] = tree_rows["session"]
    rows["tree_date"] = tree_rows["date"]
    return rows


def test_the_last_run_played_is_highlighted_by_a_rule_on_a_field_the_rows_carry():
    """A rule, because the grid works a row's class out only when it draws it.

    The run that was the latest stays in the list when the next one lands,
    and a class given by ``getRowClass`` would stay on it. The band on the
    selected scenario's run rows in the tree moves with the selection, so it
    is a rule too. A scenario row is a full-width row, which the grid does
    not work the rules out for again when its data changes, so the rule
    leaves it to the script.
    """
    rules = _options()["rowClassRules"]

    assert rules == {
        "run-list-row-latest": "params.data.latest",
        "run-list-row-selected": "params.data.sel && params.data.kind === 'run'",
    }
    assert "latest" in _sample_rows()["run"]
    assert "sel" in _sample_rows()["tree_run"]
    assert "sel" in _sample_rows()["scenario"]
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    assert "latest" not in script
    assert "run-list-row-selected" not in script


def test_the_band_is_a_look_and_the_names_button_says_it_is_current():
    css = STYLESHEET.read_text(encoding="utf-8")
    band = "box-shadow: inset 3px 0 0 var(--mantine-color-blue-filled);"
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert band in _css_block(
        css, ".run-history-list-grid .ag-row.run-list-row-selected"
    )
    assert band in _css_block(css, ".run-history-list-grid .run-list-scenario-selected")
    assert '"aria-current": data.sel ? "true" : undefined,' in script


def test_a_scenario_rows_band_follows_its_row_and_not_the_rows_it_was_drawn_with():
    """The script draws a scenario row's band from the row's data, every time.

    The grid works its row class rules out again when a row's data changes,
    but not for a full-width row, so a rule's band stayed on the scenario that
    was selected before. React redraws the renderer's class in place, and
    keyboard focus is left where it is.
    """
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    naming = script[script.index("function scenarioRow(") :]
    naming = naming[: naming.index("function sessionRow(")]

    assert (
        'data.sel ? "run-list-scenario run-list-scenario-selected" : "run-list-scenario",'
        in naming
    )
    assert "redrawRows" not in script


def test_the_highlight_is_a_look_and_tells_a_screen_reader_nothing():
    """So it does not repeat the NVDA walk the list's record describes."""
    css = STYLESHEET.read_text(encoding="utf-8")
    rule = _css_block(css, ".run-history-list-grid .ag-row.run-list-row-latest")

    assert "background-color: var(--mantine-color-blue-light);" in rule
    assert "font-weight: 600;" in rule
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    assert "run-list-row-latest" not in script


def test_the_script_reads_no_row_field_the_rows_do_not_carry():
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    carried = {field for row in _sample_rows().values() for field in row}

    assert set(re.findall(r"\bdata\.(\w+)", script)) <= carried


def test_the_script_reads_no_model_field_the_model_does_not_carry():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert set(re.findall(r"\bmodel\.(\w+)", script)) <= set(
        empty_run_list("No runs yet")
    )


# --- The script, pinned by text ------------------------------------------------


def test_the_pinned_row_and_the_body_rows_go_in_together_through_the_api():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert (
        "api.updateGridOptions({ pinnedTopRowData: rows.slice(0, 1), "
        "rowData: rows.slice(1) });"
    ) in script


def test_a_closed_rows_rows_are_filtered_out_by_the_views_set_of_open_ids():
    """A row under a scenario row shows while both its rows are open."""
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    filtering = script[script.index("dagfuncs.runListFilterPass = function") :]
    filtering = filtering[: filtering.index("};")]

    assert "if (data.kind === SESSION || data.kind === MORE) {" in filtering
    assert "var open = openRows();" in filtering
    assert (
        "return open.has(data.sid) && (data.vid == null || open.has(data.vid));"
        in filtering
    )
    assert "return viewState(state.view).open;" in script


def test_what_is_open_never_leaves_the_browser():
    """The script writes four things: a view's count, Expand all's label, and two asks."""
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    targets = re.findall(r"set_props\(\s*([^,]+),", script)
    assert sorted(targets) == sorted(
        [
            "(context.limitStoreIds || {})[state.view]",
            "context.expandAllId",
            "context.jumpStoreId",
            "context.askStoreId",
        ]
    )
    # The jump names how far back the session is, and the name what was
    # pressed: neither says which rows are open.
    assert "{ data: { place: data.place } }" in script
    assert "{ data: data.name }" in script


def test_a_full_width_row_is_given_its_gridcell_role_by_hand():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert 'role: "gridcell"' in script
    assert '"aria-colspan": props.api.getAllDisplayedColumns().length' in script


def test_enter_space_left_and_right_open_and_close_a_session_row():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    for key in ('"Enter"', '" "', '"ArrowRight"', '"ArrowLeft"'):
        assert f"key === {key}" in script
    # A scenario row takes the session row's four keys.
    assert "if (data.kind !== SESSION && data.kind !== SCENARIO) {" in script
    # A key pressed on a button inside the row is the button's own.
    assert 'event.target.closest("button")' in script


def test_tab_is_heard_before_the_grid_hears_it():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert 'gridElement.addEventListener("keydown", onTab, true);' in script


def test_focus_goes_back_to_the_same_row_id_and_button_after_new_rows_are_applied():
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    applying = script[script.index("state.apply = function") :]

    assert "id: node.data.id," in script
    assert ('part: button ? button.getAttribute("data-part") || "" : null,') in script
    assert (
        "api.setFocusedCell(node.rowIndex, focus.column, node.rowPinned || undefined);"
    ) in script
    assert ("""row.querySelector('button[data-part="' + focus.part + '"]')""") in script
    # Each of a row's buttons names its part, which is how the same one is
    # found again: a scenario row's first button is its toggle, not its name.
    for part in ('"toggle"', '"name"', '"count"', '"all"'):
        assert part in script
    # Read before the rows change, and put back after them.
    assert (
        applying.index("var focus = changedView ? null : focusedRow(api, gridElement);")
        < applying.index("api.updateGridOptions(")
        < applying.index("restoreFocus(api, gridElement, focus);")
    )


def test_each_view_opens_the_rows_of_every_run_newer_than_its_own_mark():
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    applying = script[script.index("state.apply = function") :]

    # Every view's mark starts at the run the visit's first model names.
    assert "state.firstRun = model.newest_run;" in applying
    assert "mark: state.firstRun" in script
    # A model with nothing to list is not the view's rows arriving.
    assert "if (rows.length && model.newest_run != null) {" in applying
    assert "if (!view.arrived || model.newest_run !== view.mark) {" in applying
    assert "rowsToOpen(context, model, rows, view.mark, arriving)" in applying
    assert "view.mark = model.newest_run;" in applying


def test_rows_that_first_arrive_for_a_jump_open_what_the_jump_opens():
    """Not the mark's own rows, which may be another scenario's visit.

    A session followed from `0 of 47 runs` opens nothing under it, and when
    the jump is the tree's first arrival the mark's run can be in that very
    session. Runs newer than the mark still open their rows.
    """
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    applying = script[script.index("state.apply = function") :]

    assert (
        "var arriving = !view.arrived && "
        "!(state.jump && model.view === context.treeView);"
    ) in applying
    # Decided before the jump is taken from the state.
    assert applying.index("var arriving =") < applying.index("jump = state.jump;")


def test_the_tree_walks_its_run_rows_down_to_the_views_mark():
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    walking = script[script.index("function rowsToOpen(") :]
    walking = walking[: walking.index("\n  }\n")]

    # This scenario opens its first row, as built.
    assert "if (model.view !== context.treeView) {" in walking
    assert (
        "var markRow = mark == null ? null : context.runRowIdPrefix + mark;" in walking
    )
    assert "ids.push(row.sid, row.vid);" in walking
    # The first time the view's rows arrive, the mark's own rows too.
    assert "if (arriving) {" in walking
    # Where the mark is not found, the newest run's rows alone.
    assert walking.rstrip().endswith("return model.forced_open || [];")


def test_with_follow_on_a_run_that_lands_scrolls_the_list_to_the_top():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert "if (landed && follow && api.getDisplayedRowCount() > 0) {" in script
    assert 'api.ensureIndexVisible(0, "top");' in script


def test_which_rows_are_open_is_forgotten_when_the_page_is_drawn_again():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert "if (state.api !== api) {" in script
    assert "state.views = {};" in script
    # Each view keeps its own open rows, its mark, and whether its rows have
    # arrived yet.
    assert (
        "state.views[name] = { open: new Set(), mark: state.firstRun, arrived: false };"
    ) in script


def test_the_grid_is_named_and_a_group_rows_toggle_is_named_for_its_kind():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert 'grid.setAttribute("aria-label", model.grid_name);' in script
    assert '"aria-label": label,' in script
    assert '"aria-expanded": open,' in script
    assert "toggleButton(labels.session, open, toggle)" in script
    assert "toggleButton(labels.scenario, open, toggle)" in script


def test_a_scenarios_name_is_a_button_that_asks_for_it_and_says_so():
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    naming = script[script.index("function scenarioRow(") :]
    naming = naming[: naming.index("function sessionRow(")]

    assert (
        "window.dash_clientside.set_props(context.askStoreId, { data: data.name });"
        in naming
    )
    assert "announce(context, data.selected_text);" in naming
    assert '"aria-label": data.name_label,' in naming
    # The hover with the whole name is on the part around the button.
    assert '{ className: "run-list-scenario-title", title: data.name },' in naming
    # A click on the name, a count, or Show all runs is not a click on the row.
    linking = script[script.index("function linkButton(") :]
    assert "event.stopPropagation();" in linking[: linking.index("return h(")]


def test_a_sessions_count_jumps_and_the_tree_places_the_session():
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    applying = script[script.index("state.apply = function") :]
    placing = script[script.index("function placeJump(") :]
    placing = placing[: placing.index("\n  }\n")]

    assert "state.jump = { session: data.id };" in script
    assert (
        'linkButton("run-list-count", "count", { title: labels.wholeSession }, jump, data.counts)'
        in script
    )
    assert (
        "if (state.jump && model.view === context.treeView && rows.length) {"
        in applying
    )
    assert (
        "row.id === jump.session || (row.kind === SCENARIO && row.sid === jump.session && row.sel)"
        in applying
    )
    assert 'api.ensureNodeVisible(node, "top");' in placing
    assert (
        "api.setFocusedCell(target.rowIndex, columns[0], target.rowPinned || undefined);"
        in placing
    )


def test_show_all_runs_opens_one_sessions_scenario_rows_and_says_so():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert "if (isTree(context) && open && kids.length) {" in script
    assert "setOpen(api, kids, !allKidsOpen);" in script
    assert (
        "announce(context, allKidsOpen ? labels.collapsed : labels.expanded);" in script
    )
    assert "allKidsOpen ? labels.hideAllRuns : labels.showAllRuns" in script


def test_a_view_not_on_screen_shows_from_its_top_and_older_sessions_load_into_it():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert "var changedView = model.view !== state.view;" in script
    assert (
        "window.dash_clientside.set_props((context.limitStoreIds || {})[state.view], {"
        in script
    )


def test_a_rows_height_follows_median_and_best_and_the_pinned_row_is_measured_too():
    """Row heights that change with a checkbox, with a pinned top row."""
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    setting = script[script.index("state.setFigures = function") :]

    assert (
        "return state.figures && data.figures && data.figures_below\n"
        "      ? height + SECOND_LINE_HEIGHT\n"
        "      : height;"
    ) in script
    assert "api.resetRowHeights();" in setting
    assert "api.updateGridOptions({ pinnedTopRowData: [pinned.data] });" in setting


def _function(script: str, name: str) -> str:
    """Return one function of the list's script, from its name to its end."""
    body = script[script.index(f"function {name}(") :]
    return body[: body.index("\n  }\n")]


def test_a_scenario_rows_figures_go_ahead_of_its_count():
    """``Median … · Best … · 7 runs``: the count stays at the right edge."""
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert 'return state.figures && data.figures ? [data.figures, " · "] : [];' in (
        _function(script, "figuresInLine")
    )
    assert ".concat(figuresInLine(data), [\n            data.counts," in (
        _function(script, "scenarioRow")
    )


def test_a_session_rows_figures_and_count_go_in_columns_in_its_line_or_below():
    """Under This scenario, Median, Best, and the count line up across the rows.

    The count takes a column only on a row whose figures are in its line. The
    first row's figures go below, and that line ends short by the count's
    column, so its Median and Best sit over the rows below.
    """
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    session = _function(script, "sessionRow")
    grouping = _function(script, "groupRow")

    assert "var figures = state.figures && data.figures;" in session
    assert "var below = figures && data.figures_below;" in session
    assert (
        "figureColumns(data.figures, labels).concat([columnGap(), "
        'slot("end", [state.columns.count], counts)])\n        : [counts];'
    ) in session
    assert (
        'state.columns.count ? [blank([columnGap(), slot("end", '
        '[state.columns.count], "")])] : []'
    ) in session
    assert "function groupRow(props, className, toggle, line, below) {" in grouping
    assert (
        '? h.apply(null, ["div", { className: "run-list-figures" }, partEnd()]'
        ".concat(below))"
    ) in grouping


def test_the_part_end_opens_the_figures_below_so_the_line_ends_with_the_columns():
    """The part end that tells the figures line from the first starts it.

    After the line's last part, it was one of the line's flex items, and the
    line's gap before it left the facts short of the columns' edge.
    """
    grouping = _function(LIST_SCRIPT.read_text(encoding="utf-8"), "groupRow")

    assert '["div", { className: "run-list-line" }].concat(line)),' in grouping
    assert '["div", { className: "run-list-figures" }, partEnd()]' in grouping


def test_a_columns_part_is_as_wide_as_the_widest_text_it_holds_drawn_unseen():
    """The browser sizes each part by the text the server names as the widest.

    The unseen text and the value share one grid cell, and the unseen text
    comes first, as the first child gives the part its baseline. Unseen is
    out of the accessibility tree and a page search. Tabular digits keep the
    server's pick of the widest text the browser's.
    """
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    css = STYLESHEET.read_text(encoding="utf-8")
    slot = _function(script, "slot")

    assert 'return h("span", { className: "run-list-slot-widest" }, text);' in slot
    assert slot.index("run-list-slot-widest") < slot.index('[h("span", null, content)]')
    assert "display: inline-grid;" in _css_block(css, ".run-list-slot")
    assert "font-variant-numeric: tabular-nums;" in _css_block(css, ".run-list-slot")
    assert "grid-area: 1 / 1;" in _css_block(css, ".run-list-slot > *")
    assert "justify-items: end;" in _css_block(css, ".run-list-slot-end")
    assert "justify-items: start;" in _css_block(css, ".run-list-slot-start")
    assert ".run-list-slot-widest,\n.run-list-column-blank {" in css
    assert "visibility: hidden;" in _css_block(css, ".run-list-column-blank")


def test_a_value_lines_up_on_its_decimal_point_under_its_label():
    """The label and the whole number end at their parts' right edges.

    The decimals start at theirs.
    """
    column = _function(LIST_SCRIPT.read_text(encoding="utf-8"), "figureColumn")

    assert (
        'slot("end", words, word),\n      space(),\n'
        '      slot("end", [widest[0]], value[0]),\n'
        '      slot("start", [widest[1]], value[1]),'
    ) in column


def test_every_space_between_parts_is_a_character_in_a_box_of_its_own():
    """Chrome and Edge hand a screen reader no space for a bare one between parts.

    Nor for an empty box, which read ``17,080Best``. The space between two
    columns is 16px wide.
    """
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    css = STYLESHEET.read_text(encoding="utf-8")
    space = _css_block(css, ".run-list-space")

    assert (
        'var classes = className ? "run-list-space " + className : "run-list-space";\n'
        '    return h("span", { className: classes }, " ");'
    ) in _function(script, "space")
    assert 'return space("run-list-column-gap");' in _function(script, "columnGap")
    assert "display: inline-block;" in space
    assert "white-space: pre;" in space
    assert "width: 16px;" in _css_block(css, ".run-list-column-gap")
    # No bare space between two parts of a column.
    assert '" ",' not in _function(script, "figureColumn")


def test_a_one_run_sessions_score_sits_under_best_and_its_median_is_blank():
    """The blank is Median's column drawn empty and hidden, so it keeps its room.

    Best's label has room for Score wherever a session has one run.
    """
    columns = _function(LIST_SCRIPT.read_text(encoding="utf-8"), "figureColumns")

    assert (
        "var bestWords = widest.one_run ? [labels.best, labels.score] : [labels.best];"
    ) in columns
    assert (
        'blank(figureColumn([labels.median], "", widest.median, ["", ""])'
        ".concat([columnGap()]))"
    ) in columns
    assert "figureColumn(bestWords, labels.score, widest.best, figures.score)" in (
        columns
    )
    assert "figureColumn(bestWords, labels.best, widest.best, figures.best)" in columns


def test_the_columns_widths_reach_the_script_with_the_rows_they_size():
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    applying = script[script.index("state.apply = function") :]

    assert applying.index("state.columns = model.columns;") < applying.index(
        "api.updateGridOptions({ pinnedTopRowData: rows.slice(0, 1)"
    )
    read = {
        *re.findall(r"\bstate\.columns\.(\w+)", script),
        *re.findall(r"\bwidest\.(\w+)", _function(script, "figureColumns")),
    }
    assert read <= set(run_history_list.FigureColumns.__annotations__)


def test_a_group_rows_toggle_draws_the_apps_chevron_turned_by_its_state():
    """Right when the row is closed and down when open, in the toggle's gray.

    At 16px in the toggle's 14 by 16px box, so no row grows. The drawing
    says nothing to a screen reader: the button's name and state do.
    """
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    css = STYLESHEET.read_text(encoding="utf-8")
    toggle = _function(script, "toggleButton")
    chevron = _css_block(css, ".run-list-chevron")
    icon = "icons/material-symbols-keyboard-arrow-down.svg"

    assert 'h("span", { className: "run-list-chevron", "aria-hidden": "true" })' in (
        toggle
    )
    assert "▸" not in script
    assert "▾" not in script
    assert (REPO_ROOT / "assets" / icon).is_file()
    assert f'mask: url("{icon}") no-repeat center / contain;' in chevron
    assert f'-webkit-mask: url("{icon}") no-repeat center / contain;' in chevron
    assert "background-color: currentColor;" in chevron
    assert "width: 16px;" in chevron
    assert "height: 16px;" in chevron
    assert "transform: rotate(-90deg);" in chevron
    assert "transform: none;" in _css_block(
        css, '.run-list-toggle[aria-expanded="true"] .run-list-chevron'
    )
    button = _css_block(css, ".run-list-toggle")
    assert "width: 14px;" in button
    assert "height: 16px;" in button
    assert "color: var(--mantine-color-dimmed);" in button


def test_a_key_that_opens_or_closes_a_row_is_said_through_the_live_region():
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    panel = _by_id(run_history.layout(), IDS.panel)
    region = _by_id(panel, IDS.announcer)

    assert "announce(context, open ? labels.collapsed : labels.expanded);" in script
    assert "document.getElementById(context.announcerId)" in script
    assert region.to_plotly_json()["props"]["aria-live"] == "polite"
    assert (region.role, region.className) == ("status", "visually-hidden")
    assert getattr(region, "children", None) is None


def test_expand_all_is_said_through_the_live_region_too():
    """Its press changes the button's name, which Chrome and Edge do not report."""
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    toggling = script[script.index("state.toggleAll = function (api) {") :]

    assert "var opening = !allOpen();" in toggling
    assert "setOpen(api, state.sessionIds, opening);" in toggling
    assert (
        "announce(context, opening ? labels.expanded : labels.collapsed);" in toggling
    )


def test_a_session_rows_parts_end_with_a_space_a_screen_reader_is_given():
    """Chrome and Edge join the text of flex items, and drop a space between them.

    So the space is inside the part, kept by ``white-space: pre``, and sized to
    nothing so the row's layout does not move.
    """
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    part_end = _css_block(STYLESHEET.read_text(encoding="utf-8"), ".run-list-part-end")

    assert 'return h("span", { className: "run-list-part-end" }, " ");' in script
    assert (
        'h("span", { className: "run-list-session-name" }, data.name, partEnd()),'
        in script
    )
    assert (
        'h("span", { className: "run-list-in-progress" }, labels.inProgress, partEnd())'
        in script
    )
    assert "font-size: 0;" in part_end
    assert "white-space: pre;" in part_end


def test_the_marks_cell_says_why_a_run_has_no_check():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert "title: data.passed ? undefined : data.check_text" in script
    assert 'h("span", { className: "visually-hidden" }, data.check_text)' in script
    assert '"aria-label": labels.newPb,' in script


def _inline_script(registration: dict) -> str:
    name = registration["clientside_function"]["function_name"]
    (source,) = [script for script in GLOBAL_INLINE_SCRIPTS if name in script]
    return source


def test_the_rows_reach_the_grid_from_a_store_through_a_script():
    registration = _registration(f"{IDS.apply_sink}.data")
    source = _inline_script(registration)

    assert _keys(registration["inputs"]) == [f"{IDS.model}.data"]
    # State: flipping Follow applies nothing.
    assert _keys(registration["state"]) == [f"{run_history.FOLLOW_SWITCH_ID}.checked"]
    assert "window.runHistoryList.apply(gridApi, model, follow);" in source
    assert f'getApiAsync("{IDS.grid}")' in source
    # Only the newest run applies: each waits for the grid on its own timer.
    assert "if (run === latestRun) {" in source


def test_expand_all_is_a_script_and_makes_no_request():
    registration = _registration(f"{IDS.expand_all_sink}.data")
    source = _inline_script(registration)

    assert _keys(registration["inputs"]) == [f"{IDS.expand_all}.n_clicks"]
    assert registration["prevent_initial_call"] is True
    assert "window.runHistoryList.toggleAll(gridApi);" in source


def test_nothing_on_the_server_hears_which_rows_are_open():
    """No server callback takes the grid, or any script's sink, as an input."""
    held_in_the_browser = {
        IDS.grid,
        IDS.apply_sink,
        IDS.expand_all_sink,
        IDS.figures_sink,
    }
    listening = [
        entry["output"]
        for entry in GLOBAL_CALLBACK_LIST
        if "clientside_function" not in entry
        and {
            dep["id"]
            for dep in [*entry["inputs"], *entry["state"]]
            if isinstance(dep["id"], str)
        }
        & held_in_the_browser
    ]

    assert listening == []


# --- The stores ----------------------------------------------------------------


@pytest.mark.parametrize("store_id", [IDS.session_limit, IDS.all_session_limit])
def test_each_view_starts_from_thirty_sessions_on_every_visit(store_id):
    store = _by_id(run_history.layout(), store_id)

    assert store.data == 30
    assert getattr(store, "storage_type", "memory") == "memory"


@pytest.mark.parametrize("store_id", [IDS.jump, IDS.scenario_asked])
def test_the_stores_the_script_asks_through_are_in_the_layout_and_empty(store_id):
    """A page has to hold every input of a callback whose output it holds."""
    store = _by_id(run_history.layout(), store_id)

    assert getattr(store, "data", None) is None


def test_the_layout_holds_whether_a_session_is_in_progress(monkeypatch):
    """So the first tick finds the answer already held and writes nothing."""
    asked = []
    monkeypatch.setattr(
        run_history, "is_session_in_progress", lambda now: asked.append(now) or True
    )

    store = _by_id(run_history.layout(), run_history.SESSION_IN_PROGRESS_STORE_ID)

    assert store.data is True
    assert len(asked) == 1


def test_the_run_landed_store_starts_empty():
    store = _by_id(run_history.layout(), run_history.RUN_LANDED_STORE_ID)

    assert getattr(store, "data", None) is None


# --- The callback that builds the rows -----------------------------------------


def _list_registration() -> dict:
    return _registration(f"{IDS.model}.data")


def test_the_list_is_rebuilt_by_these_eight_inputs_and_no_other():
    registration = _list_registration()
    options = run_history.CHART_OPTIONS_IDS

    assert registration["output"] == (
        f"..{IDS.model}.data...{IDS.heading}.children"
        f"...{IDS.empty}.children...{IDS.panel}.className.."
    )
    assert _keys(registration["inputs"]) == [
        f"{IDS.view}.value",
        f"{run_history.SCENARIO_SELECTION_IDS.scenario_dropdown}.value",
        f"{run_history.RUN_LANDED_STORE_ID}.data",
        f"{IDS.session_limit}.data",
        f"{IDS.all_session_limit}.data",
        f"{options.score_threshold_percentage}.value",
        f"{run_history.TODAY_STORE_ID}.data",
        f"{run_history.SESSION_IN_PROGRESS_STORE_ID}.data",
    ]
    assert registration["state"] == []
    # It draws the first list, so the page load runs it.
    assert registration["prevent_initial_call"] is False


def test_the_list_is_not_rebuilt_by_the_charts_summary_store():
    """One store for both would rebuild the list twice when Follow moves it."""
    inputs = _keys(_list_registration()["inputs"])

    assert f"{run_history.RUN_EVENTS_STORE_ID}.data" not in inputs
    assert "run-events-batch.data" not in inputs


def test_the_list_waits_for_the_selection_and_for_the_session_to_be_judged():
    """Dash holds a callback back for a queued writer of one of its inputs.

    A batch writes the summary and the run's id in one answer. The selection
    callback is queued for the first and writes the scenario, and the session
    callback is queued for the second and writes its store. The list takes
    both of those as inputs, so it is built once, after both have answered.
    """
    list_inputs = set(_keys(_list_registration()["inputs"]))
    delivery = _registration(f"{run_history.RUN_EVENTS_STORE_ID}.data")
    selection = _registration(
        f"{run_history.SCENARIO_SELECTION_IDS.playlist_filter}.value"
    )
    session = _registration(f"{run_history.SESSION_IN_PROGRESS_STORE_ID}.data")

    assert f"{run_history.RUN_LANDED_STORE_ID}.data" in delivery["output"]
    assert f"{run_history.RUN_EVENTS_STORE_ID}.data" in _keys(selection["inputs"])
    assert f"{run_history.RUN_LANDED_STORE_ID}.data" in _keys(session["inputs"])
    for writer in (selection, session):
        assert "@" not in writer["output"]
    assert {
        f"{run_history.SCENARIO_SELECTION_IDS.scenario_dropdown}.value",
        f"{run_history.SESSION_IN_PROGRESS_STORE_ID}.data",
    } <= list_inputs


def _clock_at(*moment):
    fixed = datetime(*moment)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed

    return FixedDatetime


@pytest.mark.parametrize(
    ("view", "loaded"), [(VIEW_SCENARIO, 60), (VIEW_ALL, 90)], ids=["scenario", "all"]
)
def test_the_rows_are_built_from_the_run_store_in_the_view_on_screen(
    monkeypatch, view, loaded
):
    """Each view is built with its own count of loaded sessions."""
    asked = []
    model = {**empty_run_list(None), "heading": "Scenario A · 3 runs"}

    def from_store(*arguments):
        asked.append(arguments)
        return model

    monkeypatch.setattr(run_history, "run_list_from_store", from_store)
    monkeypatch.setattr(run_history, "datetime", _clock_at(2026, 10, 12, 22, 50))

    answer = run_history.build_run_list_rows(
        view, SCENARIO, "landed.csv", 60, 90, 95, "2026-10-12", True
    )

    assert asked == [(view, SCENARIO, loaded, 95, datetime(2026, 10, 12, 22, 50))]
    assert answer == (model, "Scenario A · 3 runs", None, RUN_LIST_CLASS)


@pytest.mark.parametrize(
    ("text", "class_name"),
    [
        # The switch stays above the text: the tree needs no selection.
        ("No scenario selected", RUN_LIST_UNSELECTED_CLASS),
        ("No runs yet", RUN_LIST_NOTHING_CLASS),
    ],
)
def test_with_nothing_to_list_the_text_takes_the_grids_place(
    monkeypatch, text, class_name
):
    monkeypatch.setattr(
        run_history, "run_list_from_store", lambda *_arguments: empty_run_list(text)
    )

    model, heading, empty, panel_class = run_history.build_run_list_rows(
        VIEW_SCENARIO, None, None, 30, 30, 95, "2026-10-12", False
    )

    assert (heading, empty, panel_class) == ("", text, class_name)
    assert model["rows"] == []
    assert RUN_LIST_UNSELECTED_CLASS == "run-history-list run-history-list-unselected"


def test_the_text_for_nothing_to_list_hides_the_header_and_the_grid():
    """With no runs, the whole header goes. With no scenario selected, the switch stays."""
    css = STYLESHEET.read_text(encoding="utf-8")

    assert "display: none;" in _css_block(css, ".run-history-list-empty")
    assert "display: none;" in _css_block(
        css,
        ".run-history-list-nothing > .run-history-list-header,\n"
        ".run-history-list-nothing > .run-history-list-grid,\n"
        ".run-history-list-unselected > .run-history-list-grid,\n"
        ".run-history-list-unselected .run-history-list-heading,\n"
        ".run-history-list-unselected .run-history-list-actions",
    )
    assert "display: block;" in _css_block(
        css,
        ".run-history-list-nothing > .run-history-list-empty,\n"
        ".run-history-list-unselected > .run-history-list-empty",
    )
    assert RUN_LIST_NOTHING_CLASS == "run-history-list run-history-list-nothing"


def test_the_switch_sits_at_the_left_and_the_buttons_at_the_right():
    css = STYLESHEET.read_text(encoding="utf-8")

    assert "justify-content: space-between;" in _css_block(
        css, ".run-history-list-header"
    )
    assert "margin-left: auto;" in _css_block(css, ".run-history-list-actions")


def test_the_heading_line_is_for_a_screen_reader_only_in_both_views():
    """The latest-run card above the list names its scenario on screen.

    The line keeps its words, in its place before the switch, and stays a
    line of text: an HTML heading would change what a screen reader hears.
    """
    heading = _by_id(run_history.layout(), IDS.heading)

    assert isinstance(heading, dmc.Text)
    assert heading.className.split() == ["run-history-list-heading", "visually-hidden"]
    assert getattr(heading, "fw", None) is None
    assert getattr(heading, "truncate", None) is None


def test_the_hidden_heading_line_leaves_the_controls_on_the_headers_first_line():
    """Its absolute position takes it out of the header's line.

    Nothing gives it a line of its own any more, which is what put the
    switch and the buttons on a second line while it was on screen.
    """
    css = STYLESHEET.read_text(encoding="utf-8")
    hidden = _css_block(css, ".visually-hidden")

    assert "position: absolute;" in hidden
    assert "clip-path: inset(50%);" in hidden
    assert not re.search(r"(?m)^\.run-history-list-heading \{", css)
    assert "flex: 1 0 100%;" not in css


def test_no_text_in_the_list_is_under_12px():
    """The list's smallest text was 11px, which read too small (2026-10-18).

    A size of 0 is the part end's space, which is meant to take no room.
    """
    css = STYLESHEET.read_text(encoding="utf-8")
    sizes = {
        selector.strip(): int(size)
        for selector, body in re.findall(r"(?ms)^([^{}@/]+?) \{(.*?)^\}", css)
        if "run-list" in selector or "run-history-list" in selector
        for size in re.findall(r"font-size: (\d+)px;", body)
    }

    assert sizes
    assert {s: px for s, px in sizes.items() if 0 < px < 12} == {}


def test_a_scenarios_name_gives_before_its_count():
    css = STYLESHEET.read_text(encoding="utf-8")
    name = _css_block(css, ".run-list-scenario-name")

    assert "text-overflow: ellipsis;" in name
    assert "min-width: 0;" in name
    assert "flex: none;" in _css_block(css, ".run-list-group-facts")


@pytest.mark.parametrize("view", [VIEW_SCENARIO, VIEW_ALL])
def test_a_store_holding_no_limit_loads_the_first_thirty(monkeypatch, view):
    asked = []
    monkeypatch.setattr(
        run_history,
        "run_list_from_store",
        lambda *arguments: asked.append(arguments) or empty_run_list("No runs yet"),
    )

    run_history.build_run_list_rows(
        view, SCENARIO, None, None, None, 95, "2026-10-12", False
    )

    assert asked[0][2] == 30


def test_the_real_row_builder_answers_for_an_empty_store(monkeypatch):
    monkeypatch.setattr(run_history_list, "get_all_runs", list)

    model, heading, empty, class_name = run_history.build_run_list_rows(
        VIEW_SCENARIO, SCENARIO, None, 30, 30, 95, "2026-10-12", False
    )

    assert (heading, empty, class_name) == ("", "No runs yet", RUN_LIST_NOTHING_CLASS)
    assert model == empty_run_list("No runs yet")


# --- The jump from a session's count -------------------------------------------


def _jump_registration() -> dict:
    return _registration(f"{IDS.view}.value")


def test_one_server_callback_answers_a_jump_with_the_view_and_the_trees_count():
    registration = _jump_registration()

    assert GLOBAL_CALLBACK_MAP[registration["output"]]["callback"].__name__ == (
        "jump_to_session"
    )
    # Plain outputs, both: Dash holds a callback back for a plain output of
    # one already queued, and not for a duplicate one.
    assert registration["output"] == (
        f"..{IDS.view}.value...{IDS.all_session_limit}.data.."
    )
    assert _keys(registration["inputs"]) == [f"{IDS.jump}.data"]
    assert _keys(registration["state"]) == [f"{IDS.all_session_limit}.data"]
    # The store is empty until a count is pressed, and a mount must not move
    # the switch.
    assert registration["prevent_initial_call"] is True


def test_the_list_waits_for_the_jump_and_builds_the_tree_once():
    """It takes both of the jump's outputs as inputs, and not the jump's store."""
    list_inputs = _keys(_list_registration()["inputs"])

    assert {f"{IDS.view}.value", f"{IDS.all_session_limit}.data"} <= set(list_inputs)
    assert f"{IDS.jump}.data" not in list_inputs
    assert f"{IDS.scenario_asked}.data" not in list_inputs


def test_the_switch_and_the_trees_count_have_no_other_writer():
    jump = _jump_registration()["output"]
    writers = [
        entry["output"]
        for entry in GLOBAL_CALLBACK_LIST
        if f"{IDS.view}.value" in entry["output"]
        or f"{IDS.all_session_limit}.data" in entry["output"]
    ]

    assert writers == [jump]


@pytest.mark.parametrize(
    ("jump", "loaded", "written"),
    [
        # Nothing asked: a mount, or a call nothing triggered.
        (None, 30, (no_update, no_update)),
        ({}, 30, (no_update, no_update)),
        # A session the tree already loads: the view alone.
        ({"place": 5}, 30, (VIEW_ALL, no_update)),
        ({"place": 30}, 30, (VIEW_ALL, no_update)),
        ({"place": 31}, 60, (VIEW_ALL, no_update)),
        # Further back: the tree loads up to it, and lists it last.
        ({"place": 31}, 30, (VIEW_ALL, 31)),
        ({"place": 234}, 30, (VIEW_ALL, 234)),
        ({"place": 31}, None, (VIEW_ALL, 31)),
        # A place that is not a number loads nothing more.
        ({"place": "31"}, 30, (VIEW_ALL, no_update)),
    ],
)
def test_a_jump_switches_to_all_scenarios_and_loads_as_far_back_as_the_session(
    jump, loaded, written
):
    assert jump_to_session(jump, loaded) == written
    assert SESSIONS_PER_LOAD == 30


def test_no_callback_waits_only_on_what_the_jump_writes_now_and_then():
    """The structural test of the 2026-09-19 entry, for the jump's callback.

    It writes the switch and the tree's count only when a count is pressed.
    A callback whose Inputs were all among those two would never make its
    first call on a visit with no jump.
    """
    jump = _jump_registration()
    written = {
        output.split("@")[0] for output in jump["output"].strip(".").split("...")
    }

    starved = [
        entry["output"]
        for entry in GLOBAL_CALLBACK_LIST
        if entry is not jump
        and entry["inputs"]
        and set(_keys(entry["inputs"])) <= written
    ]

    assert starved == []


# --- Median and best -----------------------------------------------------------


def test_median_and_best_reaches_the_script_by_a_callback_of_the_lists_own():
    registration = _registration(f"{IDS.figures_sink}.data")
    source = _inline_script(registration)

    assert _keys(registration["inputs"]) == [
        '{"choice":"median_best","type":"run-history-list-columns-choice"}.checked'
    ]
    # It runs as the page mounts, with the remembered value.
    assert registration["prevent_initial_call"] is False
    assert "window.runHistoryList.setFigures(gridApi, Boolean(checked));" in source
    assert f'getApiAsync("{IDS.grid}")' in source
    assert "if (run === latestRun) {" in source


def test_the_column_callback_never_hears_median_and_best():
    registration = _registration(f"{IDS.columns_menu}-sink.data")

    assert _keys(registration["inputs"]) == [
        '{"column":["ALL"],"type":"run-history-list-columns"}.checked'
    ]


# --- "In progress", on the tick ------------------------------------------------


def test_whether_a_session_is_in_progress_is_asked_on_the_slow_tick_and_per_run():
    registration = _registration(f"{run_history.SESSION_IN_PROGRESS_STORE_ID}.data")

    assert GLOBAL_CALLBACK_MAP[registration["output"]]["callback"].__name__ == (
        "track_session_in_progress"
    )
    assert _keys(registration["inputs"]) == [
        f"{run_history.RELATIVE_TIME_INTERVAL_ID}.n_intervals",
        f"{run_history.RUN_LANDED_STORE_ID}.data",
    ]
    assert _keys(registration["state"]) == [
        f"{run_history.SESSION_IN_PROGRESS_STORE_ID}.data"
    ]
    assert registration["prevent_initial_call"] is True
    # The tick the Last played text already uses. No polling is added.
    interval = _by_id(run_history.layout(), run_history.RELATIVE_TIME_INTERVAL_ID)
    assert interval.interval == 30_000


@pytest.mark.parametrize(
    ("held", "now_in_progress", "written"),
    [
        (True, True, no_update),
        (False, False, no_update),
        # Thirty minutes after the last run, with no run landing.
        (True, False, False),
        # A run landed in a session that had read as ended.
        (False, True, True),
        (None, False, False),
    ],
)
def test_the_answer_is_written_only_when_it_is_no_longer_the_one_held(
    monkeypatch, held, now_in_progress, written
):
    monkeypatch.setattr(
        run_history, "is_session_in_progress", lambda _now: now_in_progress
    )

    assert run_history.track_session_in_progress(7, "landed.csv", held) is written


def test_the_answer_is_the_apps_own_clocks(monkeypatch):
    asked = []
    monkeypatch.setattr(
        run_history, "is_session_in_progress", lambda now: asked.append(now) or False
    )
    monkeypatch.setattr(run_history, "datetime", _clock_at(2026, 10, 12, 23, 20))

    run_history.track_session_in_progress(1, None, False)

    assert asked == [datetime(2026, 10, 12, 23, 20)]


# --- The percentage field ------------------------------------------------------


def test_the_percentage_is_sent_on_enter_or_on_leaving_the_field():
    """Typing 90 over 95 passes through 9, and every check would flicker.

    The Chart options panel has one percentage field, and it always waits
    for a commit.
    """
    field = _by_id(
        run_history.layout(),
        run_history.CHART_OPTIONS_IDS.score_threshold_percentage,
    )

    assert isinstance(field, dmc.NumberInput)
    assert field.debounce is True
    # A remembered control: the change must not move its default.
    assert (field.value, field.persistence) == (95, True)


# --- The stylesheet ------------------------------------------------------------


def _css_block(css, selector):
    match = re.search(rf"(?m)^{re.escape(selector)} \{{(.*?)^\}}", css, re.DOTALL)
    assert match, f"no {selector} rule in the stylesheet"
    return match.group(1)


def test_the_list_fills_its_column_and_scrolls_inside_its_own_box():
    css = STYLESHEET.read_text(encoding="utf-8")
    panel = _css_block(css, ".run-history-list")

    assert "height: 100%;" in panel
    assert "min-height: 0;" in panel
    assert "overflow: hidden;" in panel
    assert _grid().style == {"flex": 1, "minHeight": 0, "width": "100%"}


def test_stacked_the_list_goes_above_the_chart_at_up_to_600px():
    css = STYLESHEET.read_text(encoding="utf-8")
    stacked = css[css.index("@container run-history-page (max-width: 900px)") :]
    stacked = stacked[: stacked.index("\n}\n")]
    list_rule = re.search(
        r"\.run-history-list-column \{(.*?)\}", stacked, re.DOTALL
    ).group(1)

    assert "order: -1;" in list_rule
    assert "height: min(600px, 70dvh);" in list_rule
    assert "flex: 0 0 auto;" in list_rule


def test_the_grid_takes_the_playlist_tables_colors_in_both_themes():
    css = STYLESHEET.read_text(encoding="utf-8")

    assert (
        ".playlist-scenarios-grid.ag-theme-quartz,\n"
        ".playlist-overview-grid.ag-theme-quartz,\n"
        ".run-history-list-grid.ag-theme-quartz {\n"
        "    --ag-background-color: var(--mantine-color-body);"
    ) in css
    assert (
        ':root[data-mantine-color-scheme="dark"] '
        ".run-history-list-grid.ag-theme-quartz {\n"
        "    --ag-background-color: var(--mantine-color-dark-7);"
    ) in css
    assert _grid().className == "ag-theme-quartz run-history-list-grid"


def test_the_star_is_the_charts_own_gold():
    star = _css_block(STYLESHEET.read_text(encoding="utf-8"), ".run-list-star")

    assert f"color: {plot_service._NEW_PB_FILL_COLOR};" in star


def test_a_session_row_is_drawn_again_when_the_columns_menu_hides_a_column():
    """It spans the columns shown, and the grid does not redraw it for one hidden."""
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert 'api.addEventListener("displayedColumnsChanged", notify);' in script


def test_the_live_region_is_emptied_before_it_speaks_and_after():
    """The same word twice is no change, and a word left behind is read later."""
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    announcing = script[script.index("function announce(context, text) {") :]
    announcing = announcing[: announcing.index("function showOlderSessions")]

    assert announcing.count('region.textContent = "";') == 2
    assert announcing.count("region.textContent = text;") == 1
    assert announcing.index('region.textContent = "";') < announcing.index(
        "region.textContent = text;"
    )
