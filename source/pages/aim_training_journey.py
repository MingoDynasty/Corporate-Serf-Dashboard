import logging

import dash
from dash import Input, Output, callback, dcc
import dash_mantine_components as dmc
from plot.plot_service import generate_aim_training_journey_plot
from utilities.dash_logging import get_dash_logger

from source.kovaaks.data_service import (
    get_aim_training_journey_for_playlists,
    get_playlists,
)

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
)
def generate_graph(selected_playlist):
    logger.debug("Selected playlists: %s", selected_playlist)
    if not selected_playlist:
        return None
    journey_data = get_aim_training_journey_for_playlists(selected_playlist)
    for playlist, data in journey_data.items():
        if not data:
            message = f"Insufficient data for playlist: {playlist}"
            dash_logger.warning(message)

    return generate_aim_training_journey_plot(journey_data)


# Per Dash documentation, we should include **kwargs in case the layout receives unexpected query strings.
def layout(**kwargs):  # noqa: ARG001
    return dmc.MantineProvider(
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
                                    data=get_playlists(),
                                    id="playlists-multi-select",
                                    label="Playlist filter",
                                    miw=400,
                                    ml="xl",
                                    persistence=True,
                                    placeholder="Select a playlist...",
                                    searchable=True,
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
