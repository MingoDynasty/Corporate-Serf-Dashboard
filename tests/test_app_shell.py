from collections import deque

import dash_mantine_components as dmc
from dash import dcc

from source import app_shell


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


def test_app_shell_layout_exposes_theme_provider_and_location():
    shell = app_shell.layout()

    provider = _find_component_by_id(shell, "mantine-provider")
    location = _find_component_by_id(shell, "app-location")
    sync_interval = _find_component_by_id(shell, "theme-sync-interval")
    theme_switch = _find_component_by_id(shell, "color-scheme-switch")

    assert isinstance(provider, dmc.MantineProvider)
    assert isinstance(location, dcc.Location)
    assert isinstance(sync_interval, dcc.Interval)
    assert sync_interval.max_intervals == 1
    assert isinstance(theme_switch, dmc.Switch)


def test_navbar_burger_open_state_persists_across_refresh():
    shell = app_shell.layout()

    burger = _find_component_by_id(shell, "burger")

    assert burger.persistence is True
    assert burger.persistence_type == "local"
    assert burger.persisted_props == ["opened"]
