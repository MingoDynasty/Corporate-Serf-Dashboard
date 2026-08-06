"""Home's controls row sizes itself against the content area, not the window.

The AppShell navbar is fixed-position and 250px wide, so a viewport media
query splits Home's grid on space the page does not have. These tests pin the
two halves of the fix: the grid measures its own width, and the wide dropdowns
break onto a line at less than their target width so the row narrows before it
wraps.
"""

import re

import dash
import dash_mantine_components as dmc
import pytest

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402
from source.pages.playlist_selector import PLAYLIST_SELECTOR_PRESET  # noqa: E402

SHRINKABLE_SELECT_IDS = ("playlist-dropdown-selection", "scenario-dropdown-selection")
_FLEX_SHORTHAND = re.compile(r"^(?P<grow>\d+) (?P<shrink>\d+) (?P<basis>\d+)px$")
_PX_CLAMP = re.compile(r"^min\((?P<px>\d+)px, 100%\)$")


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


def _px(clamp, label):
    match = _PX_CLAMP.match(clamp)
    assert match, f"unrecognized {label}: {clamp!r}"
    return int(match["px"])


def _sizing(flex, floor, cap):
    """Reduce one control's sizing props to (grow, hypothetical size, target).

    A flex item is collected onto a line at its *hypothetical main size* --
    flex-basis clamped by min/max width -- so that, not flex-shrink, is what
    decides whether the row wraps.
    """
    shorthand = _FLEX_SHORTHAND.match(flex)
    assert shorthand, f"unrecognized flex shorthand: {flex!r}"
    target = _px(cap, "max width")
    hypothetical = min(max(int(shorthand["basis"]), _px(floor, "min width")), target)
    return int(shorthand["grow"]), hypothetical, target


def _sizing_of(component):
    return _sizing(component.flex, component.miw, component.maw)


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
def test_wide_dropdowns_join_a_line_below_their_target_width(select_id):
    """The whole fix: a control booking its full target width wraps instead.

    Line-breaking reads the hypothetical main size, so a basis or floor at the
    400px target reserves 400px of the row before flex-shrink ever runs -- the
    row then wraps at exactly the width it did before.
    """
    select = next(
        component
        for component in _walk_components(home.layout())
        if getattr(component, "id", None) == select_id
    )

    _grow, hypothetical, target = _sizing_of(select)

    assert hypothetical < target


@pytest.mark.parametrize("select_id", SHRINKABLE_SELECT_IDS)
def test_wide_dropdowns_grow_back_toward_their_target(select_id):
    """Breaking small is only half of it; a row with room must still fill it."""
    select = next(
        component
        for component in _walk_components(home.layout())
        if getattr(component, "id", None) == select_id
    )

    grow, _hypothetical, _target = _sizing_of(select)

    assert grow >= 1


def test_both_wide_dropdowns_size_identically():
    """They sit side by side; a mismatch reads as a rendering bug."""
    sizings = {
        component.id: _sizing_of(component)
        for component in _walk_components(home.layout())
        if getattr(component, "id", None) in SHRINKABLE_SELECT_IDS
    }

    assert len(sizings) == len(SHRINKABLE_SELECT_IDS)
    assert len(set(sizings.values())) == 1


def test_playlist_preset_carries_the_shrink_rule():
    """Both playlist dropdowns sit in wrapping rows, so the preset owns this."""
    grow, hypothetical, target = _sizing(
        PLAYLIST_SELECTOR_PRESET["flex"],
        PLAYLIST_SELECTOR_PRESET["miw"],
        PLAYLIST_SELECTOR_PRESET["maw"],
    )

    assert hypothetical < target
    assert grow >= 1
