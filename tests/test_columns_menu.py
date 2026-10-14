"""The shared Columns menu control, apart from the tables that use it."""

import dash
import dash_mantine_components as dmc
import pytest
from dash._callback import GLOBAL_CALLBACK_LIST, GLOBAL_CALLBACK_MAP

from source.components.columns_menu import (
    MenuChoice,
    MenuColumn,
    choice_checkbox_id,
    columns_menu,
    columns_menu_sink,
    register_columns_menu,
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
    # The dropdown renders in a portal at the end of the page, so focus has to
    # be moved into it on open.
    assert columns_menu(MENU_ID, COLUMNS).trapFocus is True


def test_columns_menu_leaves_focus_where_a_dismissing_click_put_it():
    # ``returnFocus`` hands focus back to the button on every close, including
    # one caused by a click on another control. Text typed next went to the
    # button, where a space reopens the menu and flips a checkbox. Escape
    # returns focus without the prop.
    props = columns_menu(MENU_ID, COLUMNS).to_plotly_json()["props"]

    assert props.get("returnFocus") is not True


def test_columns_menu_sink_carries_the_id_the_callback_outputs_to():
    assert columns_menu_sink(MENU_ID).id == "test-columns-sink"


CHOICES = [MenuChoice("median_best", "Median and best")]


def _checkboxes(menu) -> list[dmc.Checkbox]:
    _target, dropdown = menu.children
    return dropdown.children.children


def test_a_choice_that_is_not_a_column_comes_after_the_columns_unchecked():
    checkboxes = _checkboxes(columns_menu(MENU_ID, COLUMNS, CHOICES))

    assert [
        (checkbox.id, checkbox.label, checkbox.checked, checkbox.persistence)
        for checkbox in checkboxes
    ] == [
        ({"type": MENU_ID, "column": "first_sort"}, "First", True, True),
        ({"type": MENU_ID, "column": "second_id"}, "Second ID", False, True),
        (
            {"type": "test-columns-choice", "choice": "median_best"},
            "Median and best",
            False,
            True,
        ),
    ]
    assert checkboxes[-1].id == choice_checkbox_id(MENU_ID, "median_best")


def test_a_menu_given_no_choice_draws_its_columns_alone():
    """Both playlist tables build their menus this way, and are unchanged."""
    assert [
        checkbox.id for checkbox in _checkboxes(columns_menu(MENU_ID, COLUMNS))
    ] == [
        {"type": MENU_ID, "column": "first_sort"},
        {"type": MENU_ID, "column": "second_id"},
    ]


@pytest.fixture
def restored_callbacks():
    """Take a test's registrations back out of Dash's process-wide registry."""
    saved_list = list(GLOBAL_CALLBACK_LIST)
    saved_map = dict(GLOBAL_CALLBACK_MAP)
    yield
    GLOBAL_CALLBACK_LIST[:] = saved_list
    GLOBAL_CALLBACK_MAP.clear()
    GLOBAL_CALLBACK_MAP.update(saved_map)


def test_the_column_callback_never_sees_a_choice_that_is_not_a_column(
    restored_callbacks,
):
    """It matches every checkbox of the menu's ``type``, and shows each as a column."""
    register_columns_menu(MENU_ID, "test-grid")
    (registration,) = [
        entry
        for entry in GLOBAL_CALLBACK_LIST
        if entry["output"] == "test-columns-sink.data"
    ]
    (pattern,) = [dep["id"] for dep in registration["inputs"]]
    choice = choice_checkbox_id(MENU_ID, "median_best")

    assert (
        pattern
        == dash.dependencies.Input(
            {"type": MENU_ID, "column": dash.ALL}, "checked"
        ).component_id_str()
    )
    assert choice["type"] != MENU_ID
    assert set(choice) != {"type", "column"}
