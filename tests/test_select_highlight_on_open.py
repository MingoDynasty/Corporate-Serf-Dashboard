"""The Scenario Performance dropdowns keep their name on screen when opened.

``assets/selectHighlightOnOpen.js`` does the work in the browser, where no
test here can run it. These tests pin the joints it hangs on: the class the
page marks its dropdowns with, the dmc prop that would empty the field before
the script could highlight it, and the attribute the bundled Mantine build
flags an open list with.
"""

from pathlib import Path

import dash
import dash_mantine_components as dmc
import pytest

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "assets" / "selectHighlightOnOpen.js"
DMC_BUNDLE = Path(dmc.__file__).parent / "dash_mantine_components.js"
DROPDOWN_IDS = (
    home.SCENARIO_SELECTION_IDS.playlist_filter,
    home.SCENARIO_SELECTION_IDS.scenario_dropdown,
)
OPEN_LIST_ATTRIBUTE = '"data-expanded"'


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


def _dropdown(select_id):
    return next(
        component
        for component in _walk_components(home.layout())
        if getattr(component, "id", None) == select_id
    )


@pytest.fixture(scope="module")
def script():
    return SCRIPT.read_text(encoding="utf-8")


@pytest.mark.parametrize("select_id", DROPDOWN_IDS)
def test_dropdown_input_carries_the_class_the_script_finds_it_by(select_id, script):
    select = _dropdown(select_id)

    assert select.searchable is True
    assert select.classNames == {"input": home.SELECT_HIGHLIGHT_ON_OPEN_CLASS}
    assert f'"input.{home.SELECT_HIGHLIGHT_ON_OPEN_CLASS}"' in script


@pytest.mark.parametrize("select_id", DROPDOWN_IDS)
def test_dropdown_does_not_also_empty_its_field(select_id):
    """``clearSearchOnFocus`` runs first and leaves the script nothing to
    highlight, so the name is gone again and nothing looks broken."""
    assert not getattr(_dropdown(select_id), "clearSearchOnFocus", None)


def test_bundled_mantine_still_flags_an_open_list_the_way_the_script_reads_it(
    script,
):
    """The script tells an open list from a closed one by this attribute. If
    an upgrade drops it every field reads as closed, and each keystroke of a
    search then replaces the one before. A failure here means re-reading how
    the bundle's Combobox target marks an open list before touching the
    script."""
    assert f"const OPEN = {OPEN_LIST_ATTRIBUTE};" in script
    assert f"{OPEN_LIST_ATTRIBUTE}:" in DMC_BUNDLE.read_text(encoding="utf-8")
