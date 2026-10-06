"""Build a table's Columns menu and apply its choices to the grid."""

import json
from collections.abc import Sequence
from typing import NamedTuple

import dash_mantine_components as dmc
from dash import ALL, Input, Output, State, clientside_callback, dcc

from source.components.local_icon import local_icon

# Grid options every table with a Columns menu must set. With column
# virtualization on, AG Grid renders only the columns inside the window. A
# stored choice changes which columns those are as the page opens, and the
# grid's own autosize then left each column that had just come into the window
# at its minimum width, narrower than its header, on every load. Fitting those
# columns again after a wait only moved the failure to other window widths and
# to Firefox. With every column rendered it does not happen, and the tables
# have few enough columns to afford it.
COLUMNS_MENU_GRID_OPTIONS = {"suppressColumnVirtualisation": True}


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
#
# The source is a function that returns the callback, so the counter it closes
# over lasts for the life of the page. Dash evaluates the source once, and each
# grid registers its own copy.
_APPLY_COLUMNS = """
(() => {
    let latestRun = 0;

    return async (checked, ids) => {
        const noUpdate = window.dash_clientside.no_update;
        if (!window.dash_ag_grid || !window.dash_ag_grid.getApiAsync) {
            return noUpdate;
        }

        latestRun += 1;
        const run = latestRun;
        try {
            const gridApi = await window.dash_ag_grid.getApiAsync(GRID_ID);
            // Each run waits for the grid on its own timer, so an older run
            // can land after a newer one and would put its values back.
            if (run !== latestRun) {
                return noUpdate;
            }
            const shown = [];
            const hidden = [];
            ids.forEach((id, index) => (checked[index] ? shown : hidden).push(id.column));
            const shownBefore = new Set(
                gridApi.getAllDisplayedColumns().map((column) => column.getColId())
            );
            gridApi.setColumnsVisible(shown, true);
            gridApi.setColumnsVisible(hidden, false);
            // A hidden column keeps its sort, which would leave the rows
            // ordered by a column that is off screen, with no header to show
            // why.
            gridApi.applyColumnState({
                state: hidden.map((colId) => ({colId, sort: null})),
            });
            // The quick filter matches visible columns only, but a visibility
            // change makes AG Grid drop the filter's cached text and nothing
            // more. Without this, the rows keep the answer for the columns as
            // they were until the filter text is next edited.
            gridApi.onFilterChanged();
            // setColumnsVisible does not size the column it shows, and one
            // shown as the page opens comes up at its minimum width. Only
            // the columns this run showed are fitted, so a toggle never
            // undoes a width the user set by hand. The other columns are
            // the grid's own autosize to fit, which it can because the grid
            // renders every column: see COLUMNS_MENU_GRID_OPTIONS.
            const added = shown.filter((colId) => !shownBefore.has(colId));
            if (added.length) {
                gridApi.autoSizeColumns(added, false);
            }
        } catch (error) {
            console.warn("Failed to apply the Columns menu to the grid.", GRID_ID, error);
        }
        return noUpdate;
    };
})()
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
        # page to reach the first checkbox. ``returnFocus`` stays off: it hands
        # focus back to the button on every close, including one caused by a
        # click on another control. Text then typed for that control went to
        # the button instead, where a space reopens the menu and flips a
        # checkbox. Escape returns focus to the button without it.
        trapFocus=True,
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

    It runs when the page mounts and on every change, and does four things in
    order: sets each column's visibility, clears the sort of every hidden
    column, re-runs the quick filter, and sizes the columns it just showed.
    Only the newest run applies anything, so a run that waited longer for the
    grid cannot undo a later one. The grid itself must be built with
    ``COLUMNS_MENU_GRID_OPTIONS``, or a stored choice can open the table with
    clipped headers. Call once per menu, at import.
    """
    clientside_callback(
        _APPLY_COLUMNS.replace("GRID_ID", json.dumps(grid_id)),
        Output(f"{menu_id}-sink", "data"),
        Input(_checkbox_id(menu_id, ALL), "checked"),
        State(_checkbox_id(menu_id, ALL), "id"),
    )
