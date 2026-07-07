"""Build the aim-training journey page and its progress graph."""

import logging

import dash
import dash_mantine_components as dmc
from dash import Input, Output, callback, dcc
from dash.exceptions import PreventUpdate

from source.kovaaks.data_service import (
    filter_known_playlist_codes,
    get_aim_training_checkpoints,
    get_aim_training_journey_for_playlists,
    get_playlist_display_label,
    get_playlist_selector_options,
)
from source.plot.plot_service import (
    apply_light_dark_mode,
    generate_aim_training_journey_plot,
)
from source.utilities.dash_logging import get_dash_logger

logger = logging.getLogger(__name__)
dash_logger = get_dash_logger(__name__)
dash.register_page(
    __name__,
    path="/aim-training-journey",
    title="Aim Training Journey",
)


@callback(
    Output("aim-training-journey-graph", "figure"),
    Input("playlists-multi-select", "value"),
    Input("checkpoint-hour", "value"),
    Input("color-scheme-switch", "computedColorScheme"),
)
def generate_graph(selected_playlist, checkpoint_hour, color_scheme):
    """Build a themed progress graph for the selected playlists."""
    if color_scheme not in {"dark", "light"}:
        raise PreventUpdate
    if not selected_playlist or not checkpoint_hour:
        return None
    selected_playlist_codes = filter_known_playlist_codes(selected_playlist)
    if not selected_playlist_codes:
        return None

    journey_data = get_aim_training_journey_for_playlists(selected_playlist_codes)
    labeled_journey_data = {
        get_playlist_display_label(playlist_code): data
        for playlist_code, data in journey_data.items()
    }
    for playlist_code, data in journey_data.items():
        if not data:
            message = (
                "Insufficient data for playlist: "
                f"{get_playlist_display_label(playlist_code)}"
            )
            dash_logger.warning(message)

    aim_training_checkpoints = get_aim_training_checkpoints(checkpoint_hour)
    figure = generate_aim_training_journey_plot(
        labeled_journey_data,
        aim_training_checkpoints,
    )
    return apply_light_dark_mode(figure, color_scheme)


# Per Dash documentation, we should include **kwargs in case the layout receives unexpected query strings.
def layout(**kwargs):  # noqa: ARG001
    """Build the work-in-progress aim-training journey page."""
    return dmc.Box(
        [
            dmc.Alert(
                children="This page is still a work in progress!",
                # props as configured above:
                color="#ff6b6b",
                withCloseButton=False,
                variant="light",
                radius="sm",
                # other props...
            ),
            dmc.Grid(
                children=[
                    dmc.GridCol(
                        dmc.Flex(
                            children=[
                                dmc.MultiSelect(
                                    # allowDeselect=False,
                                    # autoSelectOnBlur=True,
                                    checkIconPosition="right",
                                    # clearSearchOnFocus=True,
                                    clearable=True,
                                    data=get_playlist_selector_options(),
                                    id="playlists-multi-select",
                                    label="Playlist filter",
                                    miw=400,
                                    ml="xl",
                                    persistence=True,
                                    placeholder="Select a playlist...",
                                    searchable=True,
                                ),
                                dmc.NumberInput(
                                    id="checkpoint-hour",
                                    label="Checkpoint Hour",
                                    min=1,
                                    persistence=True,
                                    # placeholder="Checkpoint Hour...",
                                    radius="sm",
                                    size="sm",
                                    variant="default",
                                    value=10,
                                ),
                            ],
                            gap="md",
                            justify="flex-start",
                            align="flex-start",
                            direction="row",
                            wrap="wrap",
                        ),
                        span=12,
                    ),
                ],
            ),
            dcc.Graph(id="aim-training-journey-graph", style={"height": "80vh"}),
        ],
    )
