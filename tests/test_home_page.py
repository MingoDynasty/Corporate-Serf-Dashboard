"""The Scenario Performance page: its name and route, and what its layout holds.

These tests render the page and hold facts that belong to none of the blocks
it hosts: the order of its headings, the absent settings modal, and how the
playlist filter, the Top N input and the follow switch are set up.
"""

import dash
import dash_mantine_components as dmc

from source.components import scenario_selection

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402


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


def _layout_components(monkeypatch) -> dict:
    """Render Home without touching disk and index the tree by component id."""
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])

    return {
        getattr(component, "id", None): component
        for component in _walk_components(home.layout())
    }


def test_home_playlist_filter_dropdown_scrollbar_is_always_visible(monkeypatch):
    monkeypatch.setattr(
        home,
        "get_visible_playlist_selector_options",
        lambda: [{"label": "Voltaic Benchmarks", "value": "KovaaKsTestCode"}],
    )
    monkeypatch.setattr(
        scenario_selection, "get_scenario_names", lambda: ["1wall6targets"]
    )

    playlist_filter = next(
        component
        for component in _walk_components(home.layout())
        if getattr(component, "id", None) == "playlist-dropdown-selection"
    )

    assert playlist_filter.scrollAreaProps == {"type": "always"}
    assert playlist_filter.persistence is True


def test_home_top_n_input_uses_compact_width(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])

    page = home.layout()
    top_n_scores = next(
        component
        for component in _walk_components(page)
        if getattr(component, "id", None) == "top_n_scores"
    )
    controls_flex = next(
        component
        for component in _walk_components(page)
        if isinstance(component, dmc.Flex)
        and any(
            getattr(child, "id", None) == "top_n_scores" for child in component.children
        )
    )

    assert top_n_scores.w == "8rem"
    assert getattr(top_n_scores, "placeholder", None) is None
    assert controls_flex.gap == "sm"
    assert controls_flex.wrap == "wrap"


def test_page_is_named_scenario_performance_and_keeps_the_root_route():
    """The rename is labels-only: the product name moved, the route did not."""
    page = dash.page_registry["source.pages.home"]

    assert page["name"] == "Scenario Performance"
    # Registered as a callable so the optional build-label prefix can be read
    # per request; unprefixed here because the flag defaults off.
    assert page["title"]() == "Scenario Performance"
    assert page["path"] == "/"


def test_home_section_titles_keep_visual_size_with_accessible_heading_order(
    monkeypatch,
):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])

    titles = {
        component.children: component
        for component in _walk_components(home.layout())
        if isinstance(component, dmc.Title)
    }

    assert titles["Scenario Stats"].order == 2
    assert titles["Scenario Stats"].size == "h6"
    # The inspector's groups sit under the page's h2 sections.
    for group in ("Overlays", "Run Data Points", "Score Threshold", "Notifications"):
        assert titles[group].order == 3
        assert titles[group].size == "h6"


def test_home_no_longer_builds_the_settings_modal(monkeypatch):
    components = _layout_components(monkeypatch)

    assert "settings-modal" not in components
    assert "settings-modal-open-button" not in components
    assert not [
        component
        for component in components.values()
        if isinstance(component, dmc.Modal)
    ]


def _label_text(component) -> str:
    """Flatten a control's label into the text a reader would see."""
    return "".join(
        part for part in _walk_components(component.label) if isinstance(part, str)
    )


def test_follow_switch_sits_under_the_scenario_selector_it_governs(monkeypatch):
    """It is stacked with the selector, not spread across the controls row."""
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])

    scenario_field = next(
        component
        for component in _walk_components(home.layout())
        if getattr(component, "className", None) == "home-scenario-field"
    )
    switch = scenario_field.children[1]

    assert [getattr(child, "id", None) for child in scenario_field.children] == [
        "scenario-dropdown-selection",
        "automatically-change-scenario-switch",
    ]
    assert _label_text(switch) == "Follow newly played scenario"
    assert switch.checked is True
    assert switch.persistence is True
