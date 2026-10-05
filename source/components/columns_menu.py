"""Build a table's Columns menu and apply its choices to the grid."""

import json
from collections.abc import Sequence
from typing import NamedTuple

import dash_mantine_components as dmc
from dash import ALL, Input, Output, State, clientside_callback, dcc

from source.components.local_icon import local_icon


class MenuColumn(NamedTuple):
    """One column a table's Columns menu can show or hide.

    ``shown_by_default`` must match the column's initial visibility in the
    grid's column definitions, and must never differ between two layouts of the
    same table: Dash drops a stored choice whose layout default changed.
    """

    column_id: str
    label: str
    shown_by_default: bool = True


# Applied through the grid API, never by writing the grid's ``columnState`` prop
# or sending column definitions again. dash-ag-grid applies a Dash-written
# ``columnState`` with ``applyOrder: true``, so the write would also set the
# column order, and resent definitions reapply every ``sort`` and ``hide`` they
# declare over the user's own.
_APPLY_COLUMNS = """
async (checked, ids) => {
    const noUpdate = window.dash_clientside.no_update;
    if (!window.dash_ag_grid || !window.dash_ag_grid.getApiAsync) {
        return noUpdate;
    }

    try {
        const gridApi = await window.dash_ag_grid.getApiAsync(GRID_ID);
        const shown = [];
        const hidden = [];
        ids.forEach((id, index) => (checked[index] ? shown : hidden).push(id.column));
        const shownBefore = new Set(
            gridApi.getAllDisplayedColumns().map((column) => column.getColId())
        );
        gridApi.setColumnsVisible(shown, true);
        gridApi.setColumnsVisible(hidden, false);
        // A hidden column keeps its sort, which would leave the rows ordered
        // by a column that is off screen, with no header to show why.
        gridApi.applyColumnState({
            state: hidden.map((colId) => ({colId, sort: null})),
        });
        // setColumnsVisible does not size the column it shows, and one shown
        // as the page opens comes up at its minimum width.
        const added = shown.filter((colId) => !shownBefore.has(colId));
        if (added.length) {
            gridApi.autoSizeColumns(added, false);
        }
    } catch (error) {
        console.warn("Failed to apply the Columns menu to the grid.", GRID_ID, error);
    }
    return noUpdate;
}
"""


def _checkbox_id(menu_id: str, column: object) -> dict:
    # The ID is the checkbox's local-storage key, so renaming a menu or a
    # column ID resets that stored choice once.
    return {"type": menu_id, "column": column}


def columns_menu_sink(menu_id: str) -> dcc.Store:
    """Build the store the menu's clientside callback outputs into."""
    return dcc.Store(id=f"{menu_id}-sink")


def columns_menu(menu_id: str, columns: Sequence[MenuColumn]) -> dmc.Popover:
    """Build the Columns button and its menu of one checkbox per column.

    A checked column is shown. The menu closes on an outside click or Escape,
    never on a change, so several columns can be set in one visit. The choices
    live in the browser's local storage, and they reach the grid through
    ``register_columns_menu``, which runs with the stored values as the page
    mounts, before the menu is ever opened.
    """
    return dmc.Popover(
        position="bottom-end",
        # A closed menu must keep its checkboxes mounted. Dash renders a
        # remounted component from the props its parent last passed down, not
        # from its current ones, so a checkbox changed and then unmounted would
        # come back showing its old state, and its next click would do nothing.
        keepMounted=True,
        # The menu renders in a portal at the end of the page, so without the
        # trap a keyboard user who opens it has to tab through the rest of the
        # page to reach the first checkbox.
        trapFocus=True,
        returnFocus=True,
        children=[
            dmc.PopoverTarget(
                dmc.Button(
                    "Columns",
                    id=f"{menu_id}-button",
                    variant="default",
                    rightSection=local_icon(
                        "material-symbols:keyboard-arrow-down",
                        width=20,
                    ),
                )
            ),
            dmc.PopoverDropdown(
                dmc.Stack(
                    gap="xs",
                    children=[
                        # One persisted checkbox per column, never one checkbox
                        # group. A group's value is the list of shown columns,
                        # and that list's default differs between two layouts
                        # of one table (a benchmark adds columns), so Dash
                        # would drop the stored choice on every move between
                        # them.
                        dmc.Checkbox(
                            id=_checkbox_id(menu_id, column.column_id),
                            label=column.label,
                            checked=column.shown_by_default,
                            persistence=True,
                            size="sm",
                        )
                        for column in columns
                    ],
                )
            ),
        ],
    )


def register_columns_menu(menu_id: str, grid_id: str) -> None:
    """Register the callback that applies a menu's checkboxes to its grid.

    It runs when the page mounts and on every change, and does three things in
    order: sets each column's visibility, clears the sort of every hidden
    column, and sizes the columns it just showed. Call once per menu, at import.
    """
    clientside_callback(
        _APPLY_COLUMNS.replace("GRID_ID", json.dumps(grid_id)),
        Output(f"{menu_id}-sink", "data"),
        Input(_checkbox_id(menu_id, ALL), "checked"),
        State(_checkbox_id(menu_id, ALL), "id"),
    )
