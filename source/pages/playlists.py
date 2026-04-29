"""Bare playlists route used as the transitional M1 playlist picker."""

import dash
from dash import Input, Output, callback, dcc, no_update
import dash_mantine_components as dmc

from source.pages.playlist_components import playlist_selector

dash.register_page(
    __name__,
    path="/playlists",
    title="Playlists",
)


@callback(
    Output("playlists-location", "pathname"),
    Input("playlists-selector", "value"),
    prevent_initial_call=True,
)
def route_to_selected_playlist(playlist_code):
    if not playlist_code:
        return no_update
    return f"/playlists/{playlist_code}"


def layout(**kwargs):  # noqa: ARG001
    return dmc.Stack(
        children=[
            dcc.Location(id="playlists-location", refresh="callback-nav"),
            dmc.Group(
                children=[playlist_selector("playlists-selector")],
                align="flex-end",
            ),
            dmc.Text("Select a playlist to view its scenarios.", c="dimmed"),
        ],
        gap="md",
    )
