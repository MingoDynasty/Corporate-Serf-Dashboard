from collections import deque

import dash_mantine_components as dmc

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


def test_app_shell_layout_exposes_native_theme_provider_and_toggle():
    shell = app_shell.layout()

    provider = _find_component_by_id(shell, "mantine-provider")
    theme_switch = _find_component_by_id(shell, "color-scheme-switch")

    assert isinstance(provider, dmc.MantineProvider)
    assert provider.defaultColorScheme == "light"
    assert isinstance(theme_switch, dmc.ColorSchemeToggle)


def test_color_scheme_is_restored_before_styles_load():
    script_position = app_shell.APP_INDEX_STRING.index(
        'const colorSchemeKey = "mantine-color-scheme-value"',
    )
    styles_position = app_shell.APP_INDEX_STRING.index("{%css%}")

    assert script_position < styles_position
    assert "_dash_persistence.color-scheme-switch.checked.true" in (
        app_shell.APP_INDEX_STRING
    )


def test_navbar_burger_open_state_persists_across_refresh():
    shell = app_shell.layout()

    burger = _find_component_by_id(shell, "burger")

    assert burger.persistence is True
    assert burger.persistence_type == "local"
    assert burger.persisted_props == ["opened"]
