"""
Entrypoint to the Corporate Serf Dashboard app.
"""

import logging.config  # Provides access to logging configuration file.
import sys
from datetime import date, datetime, timedelta
from typing import Tuple

import dash_mantine_components as dmc
from dash import Input, Output, clientside_callback, dcc, html, no_update
from dash_extensions.enrich import DashProxy
from dash_extensions.logging import NotificationsLogHandler
from dash_iconify import DashIconify
from watchdog.observers import Observer

from config_service import config
from file_watchdog import NewFileHandler
from kovaaks_data_service import (
    initialize_kovaaks_data,
    get_unique_scenarios,
    kovaaks_database,
)
from message_queue import message_queue
from plot_service import (
    generate_plot,
    apply_light_dark_mode,
)
from utilities import ordinal

# Logging setup
log_handler = NotificationsLogHandler()
dash_logger = log_handler.setup_logger(__name__)
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

################################
# TODO: Global variables best practices ?
cached_plot = None
################################

ALL_SCENARIOS = get_unique_scenarios(config.stats_dir)
app = DashProxy()


@app.callback(
    Input("interval-component", "n_intervals"),
    Output("do_update", "data", allow_duplicate=True),
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


@app.callback(
    Input("do_update", "data"),
    Input("scenario-dropdown-selection", "value"),
    Output("scenario_num_runs", "children"),
    Output("scenario_datetime_last_played", "children"),
)
def get_scenario_num_runs(_, selected_scenario) -> Tuple[int, str]:
    """
    Updates the Scenario Stats on the UI.
    :param _: trigger from the interval component. Its actual value is not used.
    :param selected_scenario: user-selected scenario name.
    :return: Scenario Stats data
    """
    scenario_stats = kovaaks_database[selected_scenario]["scenario_stats"]
    return scenario_stats.number_of_runs, scenario_stats.date_last_played.strftime(
        "%Y-%m-%d %I:%M:%S %p"
    )


@app.callback(
    Input("do_update", "data"),
    Input("scenario-dropdown-selection", "value"),
    Input("top_n_scores", "value"),
    Input("date-picker", "value"),
    Input("color-scheme-switch", "checked"),
    Output("graph-content", "figure"),
    Output("notification-container", "sendNotifications"),
)
def update_graph(do_update, newly_selected_scenario, top_n_scores, new_date, switch_on):
    """
    Updates to the graph.
    :param do_update: whether to do an update or not.
    :param newly_selected_scenario: user-selected scenario name.
    :param top_n_scores: user-selected top n scores.
    :param new_date: user-selected date.
    :param switch_on: light/dark mode switch.
    :return: Figure, Notification
    """
    global cached_plot
    if newly_selected_scenario not in kovaaks_database:
        logger.warning(
            "No scenario data for '%s'. Perhaps choose a longer date range?",
            newly_selected_scenario,
        )
        return cached_plot, no_update

    date_object = datetime.fromisoformat(new_date).date()
    _ = (date.today() - date_object).days

    sensitivities_vs_runs = kovaaks_database[newly_selected_scenario][
        "sensitivities_vs_runs"
    ]
    cached_plot = generate_plot(
        sensitivities_vs_runs, newly_selected_scenario, top_n_scores
    )

    # Default notification is simply notifying that the graph updated,
    #  usually due to user input.
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
            newly_selected_scenario == message_data.scenario_name
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
    return apply_light_dark_mode(cached_plot, switch_on), [notification]


@app.callback(
    Input("color-scheme-switch", "checked"),
    Output("graph-content", "figure", allow_duplicate=True),
)
def apply_light_dark_theme_to_graph(switch_on):
    """
    Applies the light or dark theme to the graph.
    :param switch_on: switch value.
    :return: Figure with theme applied.
    """
    if not cached_plot:
        return cached_plot
    return apply_light_dark_mode(cached_plot, switch_on)


# Add Dash Mantine Component figure templates to Plotly's templates.
dmc.add_figure_templates()

# noinspection PyTypeChecker
app.layout = dmc.MantineProvider(
    [
        dmc.NotificationContainer(id="notification-container"),
        dcc.Interval(
            id="interval-component", interval=config.polling_interval, n_intervals=0
        ),
        html.H1(
            children="Corporate Serf Dashboard v1.0.0", style={"textAlign": "center"}
        ),
        dmc.Grid(
            children=[
                dmc.GridCol(
                    dmc.Flex(
                        children=[
                            dmc.Select(
                                label="Selected scenario",
                                placeholder="Select a scenario...",
                                id="scenario-dropdown-selection",
                                data=ALL_SCENARIOS,
                                searchable=True,
                                value=config.scenario_to_monitor,
                                style={"min-width": "500px"},
                                maxDropdownHeight="75vh",
                                checkIconPosition="right",
                                persistence=True,
                                scrollAreaProps={"type": "auto"},
                                ml="xl",
                            ),
                            dmc.NumberInput(
                                id="top_n_scores",
                                placeholder="Top N scores to consider...",
                                label="Top N scores",
                                variant="default",
                                size="sm",
                                radius="sm",
                                min=1,
                                value=config.top_n_scores,
                                persistence=True,
                            ),
                            dmc.DatePickerInput(
                                id="date-picker",
                                label="Oldest date to consider",
                                rightSection=DashIconify(icon="clarity:date-line"),
                                value=(
                                    datetime.now()
                                    - timedelta(days=config.within_n_days)
                                ),
                                maxDate=datetime.now(),
                                persistence=True,
                            ),
                            dmc.Box(
                                [
                                    dmc.Title("Scenario Stats", order=6),
                                    dmc.Text(
                                        [
                                            dmc.Text(
                                                "Last played: ", fw=700, span=True
                                            ),
                                            dmc.Text(
                                                id="scenario_datetime_last_played",
                                                span=True,
                                            ),
                                        ],
                                        size="sm",
                                    ),
                                    dmc.Text(
                                        [
                                            dmc.Text(
                                                "Number of runs: ", fw=700, span=True
                                            ),
                                            dmc.Text(id="scenario_num_runs", span=True),
                                        ],
                                        size="sm",
                                    ),
                                    # dmc.Text("<b>Default</b> text 2", size="sm"),
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
                            dmc.Anchor(
                                DashIconify(icon="ion:logo-github", width=40),
                                href="https://github.com/MingoDynasty/Corporate-Serf-Dashboard",
                            ),
                            dmc.Switch(
                                offLabel=DashIconify(
                                    icon="radix-icons:sun",
                                    width=15,
                                    color=dmc.DEFAULT_THEME["colors"]["yellow"][8],
                                ),
                                onLabel=DashIconify(
                                    icon="radix-icons:moon",
                                    width=15,
                                    color=dmc.DEFAULT_THEME["colors"]["yellow"][6],
                                ),
                                id="color-scheme-switch",
                                persistence=True,
                                color="grey",
                                mr="xl",
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
        dmc.Group(
            children=[
                dmc.Anchor(
                    DashIconify(icon="logos:discord-icon", width=40),
                    href="https://discordapp.com/users/222910150636339211",
                    ml="xl",
                ),
                dmc.Text("Contact me via Discord: MingoDynasty", size="md"),
            ],
        ),
        dcc.Store(
            id="do_update",
            storage_type="memory",
        ),  # Stores data in browser's memory
    ]
    + log_handler.embed(),
)

clientside_callback(
    """
    (switchOn) => {
       document.documentElement.setAttribute('data-mantine-color-scheme', switchOn ? 'dark' : 'light');
       return window.dash_clientside.no_update
    }
    """,
    Output("color-scheme-switch", "id"),
    Input("color-scheme-switch", "checked"),
)


def main() -> None:
    """
    Main entry point.
    :return: None.
    """
    logger.debug("Loaded config: %s", config)

    # Initialize scenario data
    initialize_kovaaks_data(config.stats_dir)

    # Monitor for new files
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(
        event_handler, config.stats_dir, recursive=False
    )  # Set recursive=True to monitor subdirectories
    observer.start()
    logger.info("Monitoring directory: %s", config.stats_dir)

    # Run the Dash app
    app.run(debug=True, use_reloader=False, host="localhost", port=config.port)

    # Probably don't need this, but I kept it anyway
    observer.stop()
    observer.join()  # Wait until the observer thread terminates
    return


if __name__ == "__main__":
    main()
