from collections import deque
from pathlib import Path

import dash_mantine_components as dmc
from dash import dcc
from dash._callback import GLOBAL_CALLBACK_LIST

from source import app_shell

DMC_BUNDLE = Path(dmc.__file__).parent / "dash_mantine_components.js"


def _find_component_by_id(root, component_id):
    components = deque([root])
    while components:
        component = components.popleft()
        if getattr(component, "id", None) == component_id:
            return component

        children = getattr(component, "children", None)
        if children is None:
            continue
        if isinstance(children, list):
            components.extend(children)
        else:
            components.append(children)

    raise AssertionError(f"Component not found: {component_id}")


def test_app_shell_layout_exposes_native_theme_provider_and_toggle():
    shell = app_shell.layout()

    provider = _find_component_by_id(shell, "mantine-provider")
    theme_switch = _find_component_by_id(shell, "color-scheme-switch")

    assert isinstance(provider, dmc.MantineProvider)
    assert provider.defaultColorScheme == "light"
    assert isinstance(theme_switch, dmc.ColorSchemeToggle)


def _walk_components(root):
    components = deque([root])
    while components:
        component = components.popleft()
        yield component
        children = getattr(component, "children", None)
        if children is None:
            continue
        if isinstance(children, (list, tuple)):
            components.extend(children)
        else:
            components.append(children)


def test_theme_toggle_is_wrapped_in_tooltip():
    shell = app_shell.layout()

    tooltips = [
        component
        for component in _walk_components(shell)
        if isinstance(component, dmc.Tooltip)
        and any(
            getattr(child, "id", None) == "color-scheme-switch"
            for child in _walk_components(component.children)
        )
    ]

    assert len(tooltips) == 1
    assert tooltips[0].label == "Switch between light and dark mode"
    toggle = _find_component_by_id(tooltips[0], "color-scheme-switch")
    assert (
        toggle.to_plotly_json()["props"]["aria-label"]
        == "Switch between light and dark mode"
    )


def test_github_tooltip_is_a_plain_link_label():
    """The build identity lives on the settings page, not behind this hover."""
    assert app_shell.github_component.label == "View this app on GitHub"


def test_color_scheme_is_restored_before_styles_load():
    script_position = app_shell.APP_INDEX_STRING.index(
        'const colorSchemeKey = "mantine-color-scheme-value"',
    )
    styles_position = app_shell.APP_INDEX_STRING.index("{%css%}")

    assert script_position < styles_position
    assert "_dash_persistence.color-scheme-switch.checked.true" in (
        app_shell.APP_INDEX_STRING
    )
    assert "window.localStorage.removeItem(legacySwitchKey)" in (
        app_shell.APP_INDEX_STRING
    )


def test_index_string_declares_english_language():
    assert '<html lang="en">' in app_shell.APP_INDEX_STRING


def test_nav_link_uses_single_mantine_anchor_for_dash_navigation():
    link = app_shell.nav_link("navbar-home", "Home", "/", "bi:house-door-fill")

    assert isinstance(link, dmc.NavLink)
    assert link.id == "navbar-home"
    assert link.href == "/"
    assert link.refresh is False


def test_navbar_links_to_every_navigable_page():
    shell = app_shell.layout()

    links = [
        (component.label, component.href)
        for component in _walk_components(shell)
        if isinstance(component, dmc.NavLink)
    ]

    assert links == [
        ("Home", "/"),
        ("Run History", "/run-history"),
        ("Playlists", "/playlists"),
        ("Settings", "/settings"),
    ]


def test_every_navbar_icon_is_drawn_in_the_same_square():
    """Hold a file that is wider than tall to the box the square ones fill.

    Run History's icon is 32 by 24. Sized by its height alone it was drawn 48
    px wide in a 34 px box, and hung out of both sides of it.
    """
    shell = app_shell.layout()

    sizes = {
        link.label: (
            link.leftSection.children.style["width"],
            link.leftSection.children.style["height"],
        )
        for link in _walk_components(shell)
        if isinstance(link, dmc.NavLink)
    }

    assert sizes == dict.fromkeys(
        ["Home", "Run History", "Playlists", "Settings"], (36, 36)
    )


def test_a_navbar_icon_keeps_its_shape_inside_its_square():
    link = app_shell.nav_link(
        "navbar-run-history", "Run History", "/run-history", "fontisto:line-chart"
    )

    assert "center / contain" in link.leftSection.children.style["mask"]


# --- The navbar marks the open page ----------------------------------------------
#
# The matching itself runs in the browser, where no test here can run it. These
# tests pin the joints it hangs on: which links the callback writes to, where it
# reads the addresses from, and the stylesheet rule that draws the mark.


def _navbar_links():
    return [
        component
        for component in _walk_components(app_shell.layout())
        if isinstance(component, dmc.NavLink)
    ]


def _open_page_callback():
    (spec,) = [
        spec for spec in GLOBAL_CALLBACK_LIST if "aria-current" in str(spec["output"])
    ]
    return spec


def test_the_open_page_callback_writes_to_every_navbar_link():
    """A link the callback does not write to is never marked, on any page."""
    spec = _open_page_callback()

    assert spec["output"].strip(".").split("...") == [
        f"{link.id}.aria-current" for link in _navbar_links()
    ]
    assert spec["clientside_function"] is not None
    # The first load has to be marked too, not only a later navigation.
    assert spec["prevent_initial_call"] is False


def test_the_open_page_callback_reads_each_address_from_its_link():
    """The callback pairs addresses with links by position, and owns none.

    An address written into the callback would be a second copy of the one
    on the link, free to go stale when the link moves.
    """
    spec = _open_page_callback()

    assert [(dep["id"], dep["property"]) for dep in spec["state"]] == [
        (link.id, "href") for link in _navbar_links()
    ]


def test_the_open_page_callback_follows_the_address_from_the_shell():
    spec = _open_page_callback()
    location = _find_component_by_id(app_shell.layout(), app_shell.NAVBAR_LOCATION_ID)

    assert [(dep["id"], dep["property"]) for dep in spec["inputs"]] == [
        (app_shell.NAVBAR_LOCATION_ID, "pathname")
    ]
    assert isinstance(location, dcc.Location)
    assert location.refresh is False


def test_a_navbar_link_carries_no_mark_of_its_own():
    """Leave the mark to the callback alone.

    A fixed ``aria-current`` would mark the same link on every page. The
    component's ``active`` would run a second matcher beside the callback's,
    one that draws the mark and never sets the attribute.
    """
    for link in _navbar_links():
        props = link.to_plotly_json()["props"]

        assert "active" not in props
        assert "aria-current" not in props


def test_bundled_mantine_still_draws_a_link_that_carries_aria_current():
    """Pin the stylesheet rule the mark on screen comes from.

    The callback sets only the attribute. If an upgrade stops styling it, a
    screen reader is still told which page is open and nothing on screen
    shows it. A failure here means re-reading how the bundle draws an active
    ``NavLink`` before touching the callback.
    """
    assert "where([data-active], [aria-current='page'])" in DMC_BUNDLE.read_text(
        encoding="utf-8"
    )


def test_navbar_defaults_to_open_on_a_first_run():
    shell = app_shell.layout()

    burger = _find_component_by_id(shell, "burger")
    appshell = _find_component_by_id(shell, "appshell")

    assert burger.opened is True
    # The shell's initial `collapsed` has to agree with the burger: the
    # clientside callback recomputes it from `opened` on load, so a
    # disagreement shows a collapsed navbar for a frame before it opens.
    assert appshell.navbar["collapsed"] == {"mobile": False, "desktop": False}


def test_navbar_burger_open_state_persists_across_refresh():
    shell = app_shell.layout()

    burger = _find_component_by_id(shell, "burger")

    assert burger.persistence is True
    assert burger.persistence_type == "local"
    assert burger.persisted_props == ["opened"]
    assert burger.to_plotly_json()["props"]["aria-label"] == "Show or hide navigation"
