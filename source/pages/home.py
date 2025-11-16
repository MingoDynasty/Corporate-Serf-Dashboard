import json
import logging
from datetime import datetime
from typing import Tuple

import dash
import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import (
    callback,
    Input,
    Output,
    clientside_callback,
    dcc,
    no_update,
    State,
)
from dash_extensions.logging import NotificationsLogHandler
from dash_iconify import DashIconify

from config.config_service import config
from kovaaks.data_service import (
    get_unique_scenarios,
    get_scenario_stats,
    is_scenario_in_database,
    load_playlist_from_code,
    get_scenarios_from_playlists,
    get_playlists,
    get_sensitivities_vs_runs_filtered,
    get_rank_data_from_playlist,
)
from my_queue.message_queue import message_queue
from plot.plot_service import (
    generate_plot,
    apply_light_dark_mode,
)
from utilities.dash_utilities import get_custom_notification_log_writers
from utilities.utilities import ordinal

log_handler = NotificationsLogHandler()
log_handler.log_writers = get_custom_notification_log_writers()
dash_logger = log_handler.setup_logger(__name__)
logger = logging.getLogger(__name__)

dash.register_page(
    __name__,
    path="/",
    title="Corporate Serf Dashboard",
    redirect_from=["/home", "/index"],
)


@callback(
    Output("do_update", "data", allow_duplicate=True),
    Input("interval-component", "n_intervals"),
    prevent_initial_call=True,
)
def check_for_new_data(_):
    """
    Simple periodic trigger function to check for new data. If so then forward to interested functions.
    :param _: Number of times the interval has passed. Unused, but callback functions must have at least one input.
    :return: True if we have data, else no_update.
    """
    if message_queue.empty():
        return no_update
    return True


@callback(
    Output("scenario_num_runs", "children"),
    Output("scenario_datetime_last_played", "children"),
    Output("last-played-tooltip", "label"),
    Input("do_update", "data"),
    Input("scenario-dropdown-selection", "value"),
)
def get_scenario_num_runs(_, selected_scenario) -> Tuple[int, str, str]:
    """
    Updates the Scenario Stats on the UI.
    :param _: trigger from the interval component. Its actual value is not used.
    :param selected_scenario: user-selected scenario name.
    :return: Scenario Stats data
    """
    if not selected_scenario or not is_scenario_in_database(selected_scenario):
        return 0, "N/A", "N/A"
    scenario_stats = get_scenario_stats(selected_scenario)

    days_ago = abs((scenario_stats.date_last_played - datetime.now()).days)
    return (
        scenario_stats.number_of_runs,
        f"{days_ago} days ago",
        scenario_stats.date_last_played.strftime("%Y-%m-%d %I:%M:%S %p"),
    )


@callback(
    Output("cached-plot", "data"),
    Output("notification-container", "sendNotifications"),
    Input("do_update", "data"),
    Input("scenario-dropdown-selection", "value"),
    Input("top_n_scores", "value"),
    Input("date-picker", "value"),
    Input("rank-overlay-switch", "checked"),
    State("playlist-dropdown-selection", "value"),
)
def generate_graph(
    do_update,
    selected_scenario,
    top_n_scores,
    selected_date,
    rank_overlay_switch,
    selected_playlist,
):
    """
    Updates to the graph.
    :param do_update: whether to do an update or not.
    :param selected_scenario: user-selected scenario name.
    :param top_n_scores: user-selected top n scores.
    :param selected_date: user-selected date.
    :param rank_overlay_switch: rank overlay switch. True=show rank overlay.
    :param selected_playlist: user-selected playlist name.
    :return: Figure serialized to JSON, Notification
    """
    if not selected_scenario or not top_n_scores or not selected_date:
        return go.Figure().to_json(), no_update

    if not is_scenario_in_database(selected_scenario):
        logger.warning("No scenario data found.")
        return go.Figure().to_json(), no_update

    oldest_datetime = datetime.combine(
        datetime.fromisoformat(selected_date).date(), datetime.min.time()
    )

    sensitivities_vs_runs = get_sensitivities_vs_runs_filtered(
        selected_scenario, top_n_scores, oldest_datetime
    )
    if not sensitivities_vs_runs:
        logger.warning("No scenario data for the given date range.")
        return go.Figure().to_json(), no_update

    rank_data = None
    if selected_playlist:
        rank_data = get_rank_data_from_playlist(selected_playlist, selected_scenario)

    plot = generate_plot(
        sensitivities_vs_runs, selected_scenario, rank_overlay_switch, rank_data
    )

    # Default notification is simply notifying that the graph updated.
    notification = {
        "action": "show",
        "title": "Notification",
        "message": "Graph updated!",
        "color": "blue",
        "id": "graph-updated-notification",
        "icon": DashIconify(icon="material-symbols:refresh-rounded"),
    }

    # Display a custom notification if we detected a new Top N score.
    if do_update and not message_queue.empty():
        message_data = message_queue.get()
        if (
            selected_scenario == message_data.scenario_name
            and message_data.nth_score <= top_n_scores
        ):
            notification_message = (
                f"{message_data.sensitivity} has a new "
                f"{ordinal(message_data.nth_score)} place score: {message_data.score}"
            )
            notification = {
                "action": "show",
                "title": "Notification",
                "message": notification_message,
                "color": "green",
                "id": "new-top-n-score-notification",
                "icon": DashIconify(icon="fontisto:line-chart"),
                "autoClose": 8000,
            }
    return plot.to_json(), [notification]


@callback(
    Output("graph-content", "figure"),
    Input("color-scheme-switch", "checked"),
    Input("cached-plot", "data"),
    prevent_initial_call=True,
)
def apply_light_dark_theme_to_graph(switch_on, plot_json):
    """
    Applies the light or dark theme to the graph.
    :param switch_on: switch value.
    :param plot_json: json object with plotted data.
    :return: Figure with theme applied.
    """
    if not plot_json:
        return plot_json
    return apply_light_dark_mode(go.Figure(json.loads(plot_json)), switch_on)


@callback(
    Output("settings-modal", "opened"),
    Input("settings-modal-open-button", "n_clicks"),
    State("settings-modal", "opened"),
    prevent_initial_call=True,
)
def modal_demo(_, opened):
    """This function simply handles opening/closing the Settings modal."""
    return not opened


@callback(
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Output("playlist-dropdown-selection", "data"),
    Input("settings-modal-import-button", "n_clicks"),
    State("settings-modal-import-playlist-textinput", "value"),
    prevent_initial_call=True,
)
def import_playlist(_, playlist_to_import):
    if not playlist_to_import:
        return no_update
    playlist_to_import = playlist_to_import.strip()
    logger.debug("Importing playlist '%s'", playlist_to_import)
    error_message = load_playlist_from_code(playlist_to_import)
    if error_message:
        notification = {
            "action": "show",
            "title": "Notification",
            "message": "Failed to import playlist.",
            "color": "red",
            "id": "imported-playlist-failed-notification",
            "icon": DashIconify(icon="material-symbols:upload"),
        }
    else:
        notification = {
            "action": "show",
            "title": "Notification",
            "message": "Successfully imported playlist!",
            "color": "green",
            "id": "imported-playlist-successful-notification",
            "icon": DashIconify(icon="material-symbols:upload"),
        }
    return [notification], get_playlists()


@callback(
    Output("scenario-dropdown-selection", "data"),
    Input("playlist-dropdown-selection", "value"),
)
def select_playlist(selected_playlist):
    if not selected_playlist:
        return get_unique_scenarios(config.stats_dir)
    return get_scenarios_from_playlists(selected_playlist)


# Add Dash Mantine Component figure templates to Plotly's templates.
dmc.add_figure_templates()


def layout(**kwargs):
    return dmc.MantineProvider(
        [
            dcc.Store(id="do_update"),  # used for Interval component
            dcc.Store(id="cached-plot"),  # caches the plot for easy light/dark mode
            dcc.Interval(
                id="interval-component", interval=config.polling_interval, n_intervals=0
            ),
            dmc.Grid(
                children=[
                    dmc.GridCol(
                        dmc.Flex(
                            children=[
                                dmc.Select(
                                    label="Playlist filter",
                                    placeholder="Select a playlist...",
                                    id="playlist-dropdown-selection",
                                    data=get_playlists(),
                                    clearable=True,
                                    checkIconPosition="right",
                                    miw=400,
                                    persistence=True,
                                    ml="xl",
                                ),
                                dmc.Select(
                                    label="Selected scenario",
                                    placeholder="Select a scenario...",
                                    id="scenario-dropdown-selection",
                                    data=get_unique_scenarios(config.stats_dir),
                                    searchable=True,
                                    miw=500,
                                    maxDropdownHeight="75vh",
                                    checkIconPosition="right",
                                    persistence=True,
                                    scrollAreaProps={"type": "auto"},
                                ),
                                dmc.Space(h="xl"),
                                dmc.Space(h="xl"),
                                dmc.NumberInput(
                                    id="top_n_scores",
                                    placeholder="Top N scores to consider...",
                                    label="Top N scores",
                                    variant="default",
                                    size="sm",
                                    radius="sm",
                                    min=1,
                                    persistence=True,
                                ),
                                dmc.DatePickerInput(
                                    id="date-picker",
                                    label="Oldest date to consider",
                                    rightSection=DashIconify(icon="clarity:date-line"),
                                    maxDate=datetime.now(),
                                    persistence=True,
                                ),
                                dmc.Box(
                                    [
                                        dmc.Title("Scenario Stats", order=6),
                                        dmc.Group(
                                            [
                                                dmc.Text(
                                                    "Last played:",
                                                    fw=700,
                                                    span=True,
                                                    size="sm",
                                                ),
                                                dmc.Tooltip(
                                                    dmc.Text(
                                                        id="scenario_datetime_last_played",
                                                        span=True,
                                                        size="sm",
                                                    ),
                                                    id="last-played-tooltip",
                                                    label="My Tooltip",
                                                ),
                                            ],
                                            gap="0.25em",
                                        ),
                                        dmc.Text(
                                            [
                                                dmc.Text(
                                                    "Number of runs: ",
                                                    fw=700,
                                                    span=True,
                                                ),
                                                dmc.Text(
                                                    id="scenario_num_runs", span=True
                                                ),
                                            ],
                                            size="sm",
                                        ),
                                    ],
                                    w=300,
                                ),
                            ],
                            gap="md",
                            justify="flex-start",
                            align="flex-start",
                            direction="row",
                            wrap="wrap",
                        ),
                        span=10,
                    ),
                    dmc.GridCol(
                        dmc.Flex(
                            children=[
                                dmc.Tooltip(
                                    dmc.Button(
                                        "Settings",
                                        id="settings-modal-open-button",
                                        variant="default",
                                        leftSection=DashIconify(
                                            icon="clarity:settings-line", width=25
                                        ),
                                    ),
                                    label="Settings",
                                ),
                                dmc.Modal(
                                    title="Settings",
                                    id="settings-modal",
                                    children=[
                                        dmc.Group(
                                            gap="md",
                                            grow=False,
                                            children=[
                                                dmc.TextInput(
                                                    id="settings-modal-import-playlist-textinput",
                                                    placeholder="KovaaK's playlist code...",
                                                    label="Import Playlist",
                                                    size="md",
                                                    w="300px",
                                                ),
                                                dmc.Button(
                                                    children="Import",
                                                    id="settings-modal-import-button",
                                                    mt="lg",
                                                ),
                                            ],
                                        ),
                                        dmc.Space(h="lg"),
                                        dmc.Title("Display Settings", order=4),
                                        dmc.Space(h="xs"),
                                        dmc.Switch(
                                            id="rank-overlay-switch",
                                            labelPosition="right",
                                            label="Rank Overlay",
                                            checked=True,
                                            persistence=True,
                                        ),
                                    ],
                                ),
                            ],
                            gap="md",
                            justify="flex-end",
                            align="center",
                            direction="row",
                            wrap="wrap",
                        ),
                        span="auto",
                    ),
                ],
                gutter="xl",
                overflow="hidden",
            ),
            dcc.Graph(id="graph-content", style={"height": "80vh"}),
        ]
        + log_handler.embed(),
    )
