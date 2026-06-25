import dash
from dash import dcc
import dash_mantine_components as dmc

dash.Dash(__name__, use_pages=True, pages_folder="")

from source import app_shell  # noqa: E402


def _walk_components(component):
    if component is None or isinstance(component, str | int | float):
        return
    if isinstance(component, list | tuple):
        for child in component:
            yield from _walk_components(child)
        return

    yield component
    yield from _walk_components(getattr(component, "children", None))


def test_app_shell_layout_exposes_theme_provider_and_location():
    components_by_id = {
        component.id: component
        for component in _walk_components(app_shell.layout())
        if getattr(component, "id", None)
    }

    assert isinstance(components_by_id["mantine-provider"], dmc.MantineProvider)
    assert isinstance(components_by_id["app-location"], dcc.Location)
    assert isinstance(components_by_id["theme-sync-interval"], dcc.Interval)
    assert components_by_id["theme-sync-interval"].max_intervals == 1
    assert isinstance(components_by_id["color-scheme-switch"], dmc.Switch)
