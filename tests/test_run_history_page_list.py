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
    build_run_list,
    empty_run_list,
)
from source.components.run_marks import mark_runs  # noqa: E402
from source.kovaaks.data_models import RunData  # noqa: E402
from source.pages import home, run_history  # noqa: E402
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


def test_the_list_holds_its_heading_line_the_grid_and_the_text_for_nothing_to_list():
    panel = _by_id(run_history.layout(), IDS.panel)

    header, grid, empty, announcer = panel.children
    assert panel.className == RUN_LIST_CLASS
    assert header.className == "run-history-list-header"
    assert [getattr(child, "id", None) for child in header.children][:2] == [
        IDS.heading,
        IDS.expand_all,
    ]
    assert isinstance(header.children[2], dmc.Popover)
    assert (grid.id, empty.id, announcer.id) == (IDS.grid, IDS.empty, IDS.announcer)


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
    assert "grid-template-columns: minmax(0, 1fr) 500px;" in _css_block(
        STYLESHEET.read_text(encoding="utf-8"), ".run-history-columns"
    )


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


def test_the_columns_menu_offers_shots_fired_and_sensitivity_both_shown():
    checkboxes = _menu_checkboxes()

    assert [(box.label, box.checked, box.persistence) for box in checkboxes] == [
        ("Shots Fired", True, True),
        ("Sensitivity", True, True),
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
    assert [box.checked for box in _menu_checkboxes(run_history.layout(**query))] == [
        True,
        True,
    ]


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
        "limitStoreId": IDS.session_limit,
        "expandAllId": IDS.expand_all,
        "announcerId": IDS.announcer,
        "sessionsPerLoad": 30,
        "labels": {
            "expandAll": "Expand all",
            "collapseAll": "Collapse all",
            "session": "Session",
            "expanded": "Expanded",
            "collapsed": "Collapsed",
            "inProgress": "In progress",
            "lengthHelp": (
                "The length runs from the first run to the last run. It doesn't "
                "count the time since your last run."
            ),
            "newPb": "New PB",
        },
    }


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
    ]

    assert not [text for text in copy if f'"{text}' in script]


def _sample_rows() -> dict[str, dict]:
    """Build lists that between them hold a row of every kind, and return one of each."""
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
    marks = mark_runs(
        [r for r in runs if r.scenario == SCENARIO], 95.0, lambda _version: None
    )
    listed = build_run_list(runs, SCENARIO, 2, now, marks)
    never_played = build_run_list(runs, "Scenario C", 2, now, {})
    rows = {row["kind"]: row for row in [*listed["rows"], *never_played["rows"]]}
    assert set(rows) == {"session", "run", "divider", "date", "note", "more"}
    return rows


def test_the_last_run_played_is_highlighted_by_a_rule_on_a_field_the_rows_carry():
    """A rule, because the grid works a row's class out only when it draws it.

    The run that was the latest stays in the list when the next one lands,
    and a class given by ``getRowClass`` would stay on it.
    """
    rules = _options()["rowClassRules"]

    assert rules == {"run-list-row-latest": "params.data.latest"}
    assert "latest" in _sample_rows()["run"]
    assert "latest" not in LIST_SCRIPT.read_text(encoding="utf-8")


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


def test_a_closed_sessions_rows_are_filtered_out_by_the_set_of_open_ids():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert (
        "return data.kind === SESSION || data.kind === MORE || "
        "state.open.has(data.sid);"
    ) in script
    # What is open never leaves the browser.
    assert "set_props(context.limitStoreId" in script
    assert script.count("set_props(") == 2


def test_a_full_width_row_is_given_its_gridcell_role_by_hand():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert 'role: "gridcell"' in script
    assert '"aria-colspan": props.api.getAllDisplayedColumns().length' in script


def test_enter_space_left_and_right_open_and_close_a_session_row():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    for key in ('"Enter"', '" "', '"ArrowRight"', '"ArrowLeft"'):
        assert f"key === {key}" in script
    # A key pressed on a button inside the row is the button's own.
    assert 'event.target.closest("button")' in script


def test_tab_is_heard_before_the_grid_hears_it():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert 'gridElement.addEventListener("keydown", onTab, true);' in script


def test_focus_goes_back_to_the_same_row_id_after_new_rows_are_applied():
    script = LIST_SCRIPT.read_text(encoding="utf-8")
    applying = script[script.index("state.apply = function") :]

    assert "id: node.data.id," in script
    assert (
        "api.setFocusedCell(node.rowIndex, focus.column, node.rowPinned || undefined);"
    ) in script
    # Read before the rows change, and put back after them.
    assert (
        applying.index("var focus = focusedRow(api, gridElement);")
        < applying.index("api.updateGridOptions(")
        < applying.index("restoreFocus(api, gridElement, focus);")
    )


def test_the_current_session_opens_once_per_newest_run():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert (
        "if (model.newest_run != null && model.newest_run !== state.appliedRun) {"
        in script
    )
    assert "state.appliedRun = model.newest_run;" in script


def test_with_follow_on_a_run_that_lands_scrolls_the_list_to_the_top():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert "if (landed && follow && api.getDisplayedRowCount() > 0) {" in script
    assert 'api.ensureIndexVisible(0, "top");' in script


def test_which_rows_are_open_is_forgotten_when_the_page_is_drawn_again():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert "if (state.api !== api) {" in script
    assert "state.open = new Set();" in script


def test_the_grid_is_named_and_a_session_rows_button_is_not_named_for_the_row():
    script = LIST_SCRIPT.read_text(encoding="utf-8")

    assert 'grid.setAttribute("aria-label", model.grid_name);' in script
    assert '"aria-label": labels.session,' in script
    assert '"aria-expanded": open,' in script


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
    """No server callback takes the grid, or either script's sink, as an input."""
    held_in_the_browser = {IDS.grid, IDS.apply_sink, IDS.expand_all_sink}
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


def test_the_list_starts_from_thirty_sessions_on_every_visit():
    store = _by_id(run_history.layout(), IDS.session_limit)

    assert store.data == 30
    assert getattr(store, "storage_type", "memory") == "memory"


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


def test_the_list_is_rebuilt_by_these_six_inputs_and_no_other():
    registration = _list_registration()
    options = run_history.CHART_OPTIONS_IDS

    assert registration["output"] == (
        f"..{IDS.model}.data...{IDS.heading}.children"
        f"...{IDS.empty}.children...{IDS.panel}.className.."
    )
    assert _keys(registration["inputs"]) == [
        f"{run_history.SCENARIO_SELECTION_IDS.scenario_dropdown}.value",
        f"{run_history.RUN_LANDED_STORE_ID}.data",
        f"{IDS.session_limit}.data",
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


def test_the_rows_are_built_from_the_run_store_for_the_selection(monkeypatch):
    asked = []
    model = {**empty_run_list(None), "heading": "Scenario A · 3 runs"}

    def from_store(*arguments):
        asked.append(arguments)
        return model

    monkeypatch.setattr(run_history, "run_list_from_store", from_store)
    monkeypatch.setattr(run_history, "datetime", _clock_at(2026, 10, 12, 22, 50))

    answer = run_history.build_run_list_rows(
        SCENARIO, "landed.csv", 60, 95, "2026-10-12", True
    )

    assert asked == [(SCENARIO, 60, 95, datetime(2026, 10, 12, 22, 50))]
    assert answer == (model, "Scenario A · 3 runs", None, RUN_LIST_CLASS)


@pytest.mark.parametrize("text", ["No scenario selected", "No runs yet"])
def test_with_nothing_to_list_the_text_takes_the_grids_place(monkeypatch, text):
    monkeypatch.setattr(
        run_history, "run_list_from_store", lambda *_arguments: empty_run_list(text)
    )

    model, heading, empty, class_name = run_history.build_run_list_rows(
        None, None, 30, 95, "2026-10-12", False
    )

    assert (heading, empty, class_name) == ("", text, RUN_LIST_NOTHING_CLASS)
    assert model["rows"] == []


def test_the_text_for_nothing_to_list_hides_the_heading_line_and_the_grid():
    css = STYLESHEET.read_text(encoding="utf-8")

    assert "display: none;" in _css_block(css, ".run-history-list-empty")
    assert "display: none;" in _css_block(
        css,
        ".run-history-list-nothing > .run-history-list-header,\n"
        ".run-history-list-nothing > .run-history-list-grid",
    )
    assert "display: block;" in _css_block(
        css, ".run-history-list-nothing > .run-history-list-empty"
    )
    assert RUN_LIST_NOTHING_CLASS == "run-history-list run-history-list-nothing"


def test_a_store_holding_no_limit_loads_the_first_thirty(monkeypatch):
    asked = []
    monkeypatch.setattr(
        run_history,
        "run_list_from_store",
        lambda *arguments: asked.append(arguments) or empty_run_list("No runs yet"),
    )

    run_history.build_run_list_rows(SCENARIO, None, None, 95, "2026-10-12", False)

    assert asked[0][1] == 30


def test_the_real_row_builder_answers_for_an_empty_store(monkeypatch):
    monkeypatch.setattr(run_history_list, "get_all_runs", list)

    model, heading, empty, class_name = run_history.build_run_list_rows(
        SCENARIO, None, 30, 95, "2026-10-12", False
    )

    assert (heading, empty, class_name) == ("", "No runs yet", RUN_LIST_NOTHING_CLASS)
    assert model == empty_run_list("No runs yet")


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


def _percentage_field(page, field_id: str) -> dmc.NumberInput:
    field = _by_id(page, field_id)
    assert isinstance(field, dmc.NumberInput)
    return field


def test_the_percentage_is_sent_on_enter_or_on_leaving_the_field():
    """Typing 90 over 95 passes through 9, and every check would flicker."""
    field = _percentage_field(
        run_history.layout(),
        run_history.CHART_OPTIONS_IDS.score_threshold_percentage,
    )

    assert field.debounce is True
    # A remembered control: the change must not move its default.
    assert (field.value, field.persistence) == (95, True)


def test_the_other_pages_percentage_field_still_sends_every_keystroke():
    field = _percentage_field(
        home.layout(), home.CHART_OPTIONS_IDS.score_threshold_percentage
    )

    assert "debounce" not in field.to_plotly_json()["props"]


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
