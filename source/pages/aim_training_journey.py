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
)
from source.kovaaks.playlist_visibility_service import (
    get_visible_playlist_selector_options,
)
from source.pages.page_title import page_title
from source.pages.playlist_selector import PLAYLIST_SELECTOR_PRESET
from source.plot.plot_service import (
    apply_light_dark_mode,
    generate_aim_training_journey_plot,
    generate_empty_plot,
    generate_placeholder_plot,
)

logger = logging.getLogger(__name__)
_NO_JOURNEY_DATA_PLOT_TITLE = "No playlist progress yet"
_NO_JOURNEY_DATA_PLOT_MESSAGE = (
    "Play scenarios from the selected playlists and the graph will fill in."
)
dash.register_page(
    __name__,
    path="/aim-training-journey",
    title=page_title("Aim Training Journey"),
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
    if not selected_playlist:
        return apply_light_dark_mode(
            generate_empty_plot(
                "No playlists selected",
                "Choose one or more playlists to compare progress.",
            ),
            color_scheme,
        )
    selected_playlist_codes = filter_known_playlist_codes(selected_playlist)
    if not selected_playlist_codes:
        return apply_light_dark_mode(
            generate_empty_plot(
                "No playlists selected",
                "Choose one or more playlists to compare progress.",
            ),
            color_scheme,
        )
    if not checkpoint_hour:
        return apply_light_dark_mode(
            generate_empty_plot(
                "Graph settings incomplete",
                "Choose a Checkpoint Hour value to plot progress.",
            ),
            color_scheme,
        )

    journey_data = get_aim_training_journey_for_playlists(selected_playlist_codes)
    for playlist_code, data in journey_data.items():
        if not data:
            logger.warning(
                "Insufficient data for playlist: %s",
                get_playlist_display_label(playlist_code),
            )

    # Nothing to plot is a state, not an event: say so where the chart would
    # be, the way Home's empty plots do, instead of toasting over the page.
    # Only a selection with no runs at all takes the empty state; a partial
    # selection still plots what it has.
    if not any(journey_data.values()):
        return apply_light_dark_mode(
            generate_empty_plot(
                _NO_JOURNEY_DATA_PLOT_TITLE,
                _NO_JOURNEY_DATA_PLOT_MESSAGE,
            ),
            color_scheme,
        )

    labeled_journey_data = {
        get_playlist_display_label(playlist_code): data
        for playlist_code, data in journey_data.items()
    }
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
                                    **PLAYLIST_SELECTOR_PRESET,
                                    clearable=True,
                                    data=get_visible_playlist_selector_options(),
                                    id="playlists-multi-select",
                                    label="Playlist filter",
                                    persistence=True,
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
            dcc.Graph(
                id="aim-training-journey-graph",
                figure=generate_placeholder_plot(),
                style={"height": "80vh"},
            ),
        ],
    )
