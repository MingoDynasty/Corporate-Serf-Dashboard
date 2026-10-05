"""The shared Columns menu control, apart from the tables that use it."""

import dash_mantine_components as dmc

from source.components.columns_menu import (
    MenuColumn,
    columns_menu,
    columns_menu_sink,
)

MENU_ID = "test-columns"
COLUMNS = [
    MenuColumn("first_sort", "First"),
    MenuColumn("second_id", "Second ID", shown_by_default=False),
]


def test_columns_menu_builds_one_persisted_checkbox_per_column():
    target, dropdown = columns_menu(MENU_ID, COLUMNS).children
    button = target.children
    checkboxes = dropdown.children.children

    assert isinstance(button, dmc.Button)
    assert button.children == "Columns"
    assert button.id == "test-columns-button"
    # One checkbox per column, never one group: a group's default would differ
    # between two layouts of one table, and Dash drops a stored value whose
    # layout default changed.
    assert all(isinstance(checkbox, dmc.Checkbox) for checkbox in checkboxes)
    assert [
        (checkbox.id, checkbox.label, checkbox.checked, checkbox.persistence)
        for checkbox in checkboxes
    ] == [
        ({"type": MENU_ID, "column": "first_sort"}, "First", True, True),
        ({"type": MENU_ID, "column": "second_id"}, "Second ID", False, True),
    ]


def test_columns_menu_keeps_its_closed_dropdown_mounted():
    # Dash renders a remounted component from the props its parent last passed
    # down. An unmounted checkbox would come back showing its old state after
    # the menu was closed and opened again, and its next click would do nothing.
    assert columns_menu(MENU_ID, COLUMNS).keepMounted is True


def test_columns_menu_is_reachable_from_the_keyboard():
    menu = columns_menu(MENU_ID, COLUMNS)

    # The dropdown renders in a portal at the end of the page, so focus has to
    # be moved into it on open and handed back to the button on close.
    assert menu.trapFocus is True
    assert menu.returnFocus is True


def test_columns_menu_sink_carries_the_id_the_callback_outputs_to():
    assert columns_menu_sink(MENU_ID).id == "test-columns-sink"
