"""Home's controls row sizes itself against the content area, not the window.

The AppShell navbar is fixed-position and 250px wide, so a viewport media
query splits Home's grid on space the page does not have. These tests pin the
two halves of the fix: the grid measures its own width, and the wide dropdowns
narrow before the row wraps.
"""

import dash
import dash_mantine_components as dmc
import pytest

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402
from source.pages.playlist_selector import PLAYLIST_SELECTOR_PRESET  # noqa: E402

SHRINKABLE_SELECT_IDS = ("playlist-dropdown-selection", "scenario-dropdown-selection")


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


@pytest.fixture(autouse=True)
def quiet_playlists(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])


@pytest.fixture
def controls_grid():
    grids = [
        component
        for component in _walk_components(home.layout())
        if isinstance(component, dmc.Grid)
    ]
    assert len(grids) == 1, "Home is expected to have exactly one controls grid"
    return grids[0]


def test_controls_grid_measures_its_own_width(controls_grid):
    """Without this the columns split on window width the navbar has taken."""
    assert controls_grid.type == "container"


def test_controls_grid_declares_the_breakpoints_its_container_needs(controls_grid):
    """Mantine renders the container element only when both props are set.

    ``type="container"`` alone still emits ``@container`` queries, but with no
    container to resolve against they never match and every column silently
    falls back to its ``base`` span.
    """
    assert controls_grid.breakpoints == home.HOME_GRID_BREAKPOINTS
    assert set(controls_grid.breakpoints) == {"xs", "sm", "md", "lg", "xl"}


def test_breakpoint_thresholds_still_track_the_mantine_defaults():
    """Only the box being measured changed; the thresholds themselves did not."""
    assert home.HOME_GRID_BREAKPOINTS == dmc.DEFAULT_THEME["breakpoints"]


def test_breakpoints_are_a_copy_of_the_shared_theme_dict():
    """The theme dict is process-wide; a Dash prop must not alias it."""
    assert home.HOME_GRID_BREAKPOINTS is not dmc.DEFAULT_THEME["breakpoints"]


@pytest.mark.parametrize("select_id", SHRINKABLE_SELECT_IDS)
def test_wide_dropdowns_narrow_before_the_row_wraps(select_id):
    """A 400px floor makes the row wrap rather than shrink; a basis does not."""
    select = next(
        component
        for component in _walk_components(home.layout())
        if getattr(component, "id", None) == select_id
    )

    assert select.flex == "0 1 400px"
    assert select.miw == "min(200px, 100%)"


def test_playlist_preset_carries_the_shrink_rule():
    """Both playlist dropdowns sit in wrapping rows, so the preset owns this."""
    assert PLAYLIST_SELECTOR_PRESET["flex"] == "0 1 400px"
    assert PLAYLIST_SELECTOR_PRESET["miw"] == "min(200px, 100%)"
