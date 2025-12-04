from datetime import datetime
import json
import logging

import dash
from dash import (
    Input,
    Output,
    State,
    callback,
    dcc,
    no_update,
)
from dash_iconify import DashIconify
import dash_mantine_components as dmc
import plotly.graph_objects as go

from source.config.config_service import config
from source.kovaaks.data_service import (
    get_playlists,
    get_rank_data_from_playlist,
    get_scenario_stats,
    get_scenarios_from_playlists,
    get_sensitivities_vs_runs_filtered,
    get_time_vs_runs,
    get_unique_scenarios,
    is_scenario_in_database,
    load_playlist_from_code,
)
from source.my_queue.message_queue import message_queue
from source.plot.plot_service import (
    apply_light_dark_mode,
    generate_sensitivity_plot,
    generate_time_plot,
)
from source.utilities.dash_logging import get_dash_logger
from source.utilities.utilities import ordinal

logger = logging.getLogger(__name__)
dash_logger = get_dash_logger(__name__)
dash.register_page(
    __name__,
    path="/",
    title="Corporate Serf Dashboard",
    redirect_from=["/home", "/index"],
)


@callback(
    Output("do_update", "data", allow_duplicate=True),
    Input("interval-component", "n_intervals"),
    State("scenario-dropdown-selection", "value"),
    prevent_initial_call=True,
)
def check_for_new_data(_, selected_scenario):
    """
    Simple periodic trigger function to check for new data. If so then forward to interested functions.
    :param _: Number of times the interval has passed. Unused, but callback functions must have at least one input.
    :param selected_scenario: name of the currently selected scenario.
    :return: True if we have data, else no_update.
    """
    if len(message_queue) == 0:
        return no_update

    if message_queue[0].scenario_name != selected_scenario:
        message_queue.pop()
        return no_update
    return True


@callback(
    Output("scenario_num_runs", "children"),
    Output("scenario_datetime_last_played", "children"),
    Output("last-played-tooltip", "label"),
    Input("do_update", "data"),
    Input("scenario-dropdown-selection", "value"),
)
def get_scenario_num_runs(_, selected_scenario) -> tuple[int, str, str]:
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
    Input("x-axis-radiogroup", "value"),
    Input("rank-overlay-switch", "checked"),
    State("playlist-dropdown-selection", "value"),
)
def generate_graph(
    do_update,
    selected_scenario,
    top_n_scores,
    selected_date,
    x_axis_radiogroup,
    rank_overlay_switch,
    selected_playlist,
):
    """
    Updates to the graph.
    :param do_update: whether to do an update or not.
    :param selected_scenario: user-selected scenario name.
    :param top_n_scores: user-selected top n scores.
    :param selected_date: user-selected date.
    :param x_axis_radiogroup: user-selected x-axis radio group.
    :param rank_overlay_switch: rank overlay switch. True=show rank overlay.
    :param selected_playlist: user-selected playlist name.
    :return: Figure serialized to JSON, Notification
    """
    if not selected_scenario or not top_n_scores or not selected_date:
        return go.Figure().to_json(), no_update

    if not is_scenario_in_database(selected_scenario):
        logger.warning("No scenario data found for: %s", selected_scenario)
        dash_logger.warning("No scenario data found.")
        return go.Figure().to_json(), no_update

    oldest_datetime = datetime.combine(
        datetime.fromisoformat(selected_date).date(),
        datetime.min.time(),
    )

    plot = go.Figure()
    if x_axis_radiogroup == "score_vs_sensitivity":
        sensitivities_vs_runs = get_sensitivities_vs_runs_filtered(
            selected_scenario,
            top_n_scores,
            oldest_datetime,
        )
        if not sensitivities_vs_runs:
            logger.warning(
                "No scenario data found for (%s) for date range: %s",
                selected_scenario,
                oldest_datetime,
            )
            dash_logger.warning("No scenario data for the given date range.")
            return go.Figure().to_json(), no_update

        rank_data = None
        if selected_playlist:
            rank_data = get_rank_data_from_playlist(
                selected_playlist, selected_scenario
            )

        plot = generate_sensitivity_plot(
            sensitivities_vs_runs,
            selected_scenario,
            rank_overlay_switch,
            rank_data,
        )
    elif x_axis_radiogroup == "score_vs_time":
        time_vs_runs = get_time_vs_runs(
            selected_scenario,
            top_n_scores,
            oldest_datetime,
        )
        if not time_vs_runs:
            logger.warning(
                "No scenario data found for (%s) for date range: %s",
                selected_scenario,
                oldest_datetime,
            )
            dash_logger.warning("No scenario data for the given date range.")
            return go.Figure().to_json(), no_update

        rank_data = None
        if selected_playlist:
            rank_data = get_rank_data_from_playlist(
                selected_playlist, selected_scenario
            )

        plot = generate_time_plot(
            time_vs_runs,
            selected_scenario,
            rank_overlay_switch,
            rank_data,
        )
    else:
        logger.error("Unsupported radio option: %s", x_axis_radiogroup)

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
                f"{ordinal(message_data.nth_score)} place score: {message_data.score:.2f}"
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


# Per Dash documentation, we should include **kwargs in case the layout receives unexpected query strings.
def layout(**kwargs):  # noqa: ARG001
    return dmc.Box(
        children=[
            dcc.Store(id="do_update"),  # used for Interval component
            dcc.Store(id="cached-plot"),  # caches the plot for easy light/dark mode
            dcc.Interval(
                id="interval-component",
                interval=config.polling_interval,
                n_intervals=0,
            ),
            dmc.Grid(
                children=[
                    dmc.GridCol(
                        dmc.Flex(
                            children=[
                                dmc.Select(
                                    allowDeselect=False,
                                    autoSelectOnBlur=True,
                                    checkIconPosition="right",
                                    clearSearchOnFocus=True,
                                    clearable=True,
                                    data=get_playlists(),
                                    id="playlist-dropdown-selection",
                                    label="Playlist filter",
                                    maxDropdownHeight="75vh",
                                    miw=400,
                                    ml="xl",
                                    persistence=True,
                                    placeholder="Select a playlist...",
                                    searchable=True,
                                ),
                                dmc.Select(
                                    allowDeselect=False,
                                    autoSelectOnBlur=True,
                                    checkIconPosition="right",
                                    clearSearchOnFocus=True,
                                    data=get_unique_scenarios(config.stats_dir),
                                    id="scenario-dropdown-selection",
                                    label="Selected scenario",
                                    maxDropdownHeight="75vh",
                                    miw=500,
                                    persistence=True,
                                    placeholder="Select a scenario...",
                                    scrollAreaProps={"type": "auto"},
                                    searchable=True,
                                ),
                                dmc.Space(h="xl"),
                                dmc.Space(h="xl"),
                                dmc.NumberInput(
                                    id="top_n_scores",
                                    label="Top N scores",
                                    min=1,
                                    persistence=True,
                                    placeholder="Top N scores to consider...",
                                    radius="sm",
                                    size="sm",
                                    variant="default",
                                    value=5,
                                ),
                                dmc.DatePickerInput(
                                    id="date-picker",
                                    label="Oldest date to consider",
                                    maxDate=datetime.now().isoformat(),
                                    persistence=True,
                                    rightSection=DashIconify(icon="clarity:date-line"),
                                    value=datetime(
                                        datetime.now().year,
                                        month=1,
                                        day=1,
                                    ).isoformat(),
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
                                                    id="scenario_num_runs",
                                                    span=True,
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
                                dmc.RadioGroup(
                                    children=dmc.Stack(
                                        [
                                            dmc.Radio(label, value=value)
                                            for value, label in [
                                                [
                                                    "score_vs_sensitivity",
                                                    "Score vs Sensitivity",
                                                ],
                                                ["score_vs_time", "Score vs Time"],
                                            ]
                                        ],
                                    ),
                                    id="x-axis-radiogroup",
                                    value="score_vs_sensitivity",
                                    persistence=True,
                                ),
                                dmc.Space(h="xl"),
                                dmc.Tooltip(
                                    dmc.Button(
                                        "Settings",
                                        id="settings-modal-open-button",
                                        variant="default",
                                        leftSection=DashIconify(
                                            icon="clarity:settings-line",
                                            width=25,
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
        ],
    )
