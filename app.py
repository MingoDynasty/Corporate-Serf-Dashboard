"""
Entrypoint to the Corporate Serf Dashboard app.
"""
import logging.config  # Provides access to logging configuration file.
import sys
import time
import tomllib
from datetime import date, datetime, timedelta
from pathlib import Path

import dash_mantine_components as dmc
import tomli_w
from dash import Output, Input, html, no_update, clientside_callback
from dash import dcc
from dash_extensions.enrich import DashProxy
from dash_extensions.logging import NotificationsLogHandler
from dash_iconify import DashIconify
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from shared_functions import extract_data_from_file, get_unique_scenarios, is_file_of_interest, get_scenario_data, \
    generate_plot

# Logging setup
log_handler = NotificationsLogHandler()
logger = log_handler.setup_logger(__name__)
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s"
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format=LOG_FORMAT)
console_logger = logging.getLogger(__name__)

# Pull arguments from a config file.
CONFIG_FILE = "config.toml"
with open(CONFIG_FILE, "rb") as _file:
    config = tomllib.load(_file)
console_logger.debug("Loaded config: %s", config)


def update_config() -> None:
    """Write the current config file to disk."""
    with open(CONFIG_FILE, 'wb') as file:
        tomli_w.dump(config, file)


################################
# TODO: Global variables best practices ?
# There is possibly a risky race condition here, but too lazy to fix.
scenario_data = {}
new_data = False
fig = None
################################

ALL_SCENARIOS = get_unique_scenarios(config['stats_dir'])
app = DashProxy()


@app.callback(
    Input('interval-component', 'n_intervals'),
    # Output('live-update-text', 'children'),
    Output('do_update', 'data', allow_duplicate=True))
def check_for_new_data(_) -> bool:
    """
    Simple periodic trigger function to check for new data. If so then forward to update_graph() function.
    :param _: Number of times the interval has passed. Unused, but callback functions must have at least one input.
    :return: Current datetime, and the new_data flag.
    """
    # return f"Last file scan: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}", new_data
    return new_data


@app.callback(
    Input('scenario-dropdown-selection', 'value'),
    Output('do_update', 'data', allow_duplicate=True),
    prevent_initial_call=True)
def select_new_scenario(new_scenario) -> bool:
    """
    Triggers when the user selects a new scenario from the dropdown.
    :param new_scenario: The newly selected scenario.
    :return: Flag to trigger a graph update.
    """
    console_logger.debug("New scenario selected: %s", new_scenario)
    config['scenario_to_monitor'] = new_scenario
    update_config()
    return True


@app.callback(
    Input('top_n_scores', 'value'),
    Output('do_update', 'data', allow_duplicate=True),
    prevent_initial_call=True)
def update_top_n_scores(new_top_n_scores) -> bool:
    """
    Triggers when the user changes the Top N Scores value.
    :param new_top_n_scores: The new Top N Scores value.
    :return: Flag to trigger a graph update.
    """
    if not new_top_n_scores:
        return False
    console_logger.debug("New top_n_scores: %s", new_top_n_scores)
    config['top_n_scores'] = new_top_n_scores
    update_config()
    return True


@app.callback(
    Input('date-picker', 'value'),
    Output('do_update', 'data', allow_duplicate=True),
    prevent_initial_call=True)
def update_within_n_days(new_date) -> bool:
    """
    Triggers when the user selects a date from the date picker.
    :param new_date: The newly selected date.
    :return: Flag to trigger a graph update.
    """
    console_logger.debug("New date: %s", new_date)
    date_object = date.fromisoformat(new_date)
    new_within_n_days = (date.today() - date_object).days

    console_logger.debug("New within_n_days: %s", new_within_n_days)
    config['within_n_days'] = new_within_n_days
    update_config()
    return True


@app.callback(
    Input('do_update', 'data'),
    Output('graph-content', 'figure'),
    Output("notification-container", "sendNotifications"),
)
def update_graph(do_update):
    """
    Updates to the graph.
    :param do_update: whether to do an update or not.
    :return: Figure, Notification
    """
    global fig, new_data, scenario_data
    if not do_update:
        return fig, no_update

    # No scenario selected yet
    if not config['scenario_to_monitor']:
        return fig, no_update

    scenario_data = get_scenario_data(config['stats_dir'], config['scenario_to_monitor'], config['within_n_days'])
    if not scenario_data:
        console_logger.warning(
            "No scenario data for '%s'. Perhaps choose a longer date range?", config['scenario_to_monitor'])
        return fig, no_update

    console_logger.debug("Updating graph...")
    fig = generate_plot(scenario_data, config['scenario_to_monitor'], config['top_n_scores'])

    new_data = False
    notification = {
        "action": "show",
        "title": "Notification",
        "message": "Graph updated!",
        "color": "blue",
        "id": "graph-updated-notification",
        "icon": DashIconify(icon="material-symbols:refresh-rounded"),
    }
    return fig, [notification]


# noinspection PyTypeChecker
app.layout = dmc.MantineProvider(
    [
        dmc.NotificationContainer(id="notification-container"),
        dcc.Interval(
            id='interval-component',
            interval=config['polling_interval'],
            n_intervals=0
        ),
        html.H1(children='Corporate Serf Dashboard v1.0.0', style={'textAlign': 'center'}),
        dmc.Grid(
            children=[
                dmc.GridCol(
                    dmc.Flex(
                        children=[
                            dmc.Select(
                                label="Selected scenario",
                                placeholder='Select a scenario...',
                                id="scenario-dropdown-selection",
                                data=ALL_SCENARIOS,
                                searchable=True,
                                value=config['scenario_to_monitor'],
                                style={"min-width": "500px"},
                                maxDropdownHeight=1000,
                                checkIconPosition="right",
                                persistence=True,
                                scrollAreaProps={"type": "auto"},
                                ml="xl",
                            ),
                            dmc.NumberInput(
                                id='top_n_scores',
                                placeholder="Top N scores to consider...",
                                label="Top N scores",
                                variant="default",
                                size="sm",
                                radius="sm",
                                min=1,
                                value=config['top_n_scores'],
                                persistence=True,
                            ),
                            dmc.DatePickerInput(
                                id='date-picker',
                                label="Oldest date to consider",
                                rightSection=DashIconify(icon="clarity:date-line"),
                                value=(datetime.now() - timedelta(days=config['within_n_days'])),
                                maxDate=datetime.now(),
                                persistence=True,
                            ),
                        ],
                        gap="md",
                        justify="flex-start",
                        align="flex-start",
                        direction="row",
                        wrap="wrap",
                    ), span=10,
                ),
                dmc.GridCol(
                    dmc.Flex(
                        children=[
                            dmc.Anchor(DashIconify(icon="ion:logo-github", width=40),
                                       href="https://github.com/MingoDynasty/Corporate-Serf-Dashboard"),
                            dmc.Switch(
                                offLabel=DashIconify(icon="radix-icons:sun", width=15,
                                                     color=dmc.DEFAULT_THEME["colors"]["yellow"][8]),
                                onLabel=DashIconify(icon="radix-icons:moon", width=15,
                                                    color=dmc.DEFAULT_THEME["colors"]["yellow"][6]),
                                id="color-scheme-switch",
                                persistence=True,
                                color="grey",
                                mr='xl'
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
        dcc.Graph(id='graph-content', style={'height': '80vh'}),
        dmc.Group(
            children=[
                # dmc.Text(id='live-update-text', size="md", ml='xl', hidden=True),
                dmc.Anchor(DashIconify(icon="logos:discord-icon", width=40),
                           href="https://discordapp.com/users/222910150636339211",
                           ml='xl'),
                dmc.Text("Contact me via Discord: MingoDynasty", size="md"),
            ],
        ),
        dcc.Store(id='do_update', storage_type='memory')  # Stores data in browser's memory
    ]
    + log_handler.embed()
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


class NewFileHandler(FileSystemEventHandler):
    """
    This class handles monitoring a specified directory for newly created files.
    """

    def on_created(self, event):
        global new_data
        if event.is_directory:  # Check if it's a file, not a directory
            return
        console_logger.debug("Detected new file: %s", event.src_path)
        # Add your custom logic here to process the new file
        # For example, you could read its content, move it, or trigger another function.
        file = event.src_path

        # 1. Check if this file is a file that we care about.
        if not is_file_of_interest(file, config['scenario_to_monitor'], config['within_n_days']):
            console_logger.debug("Not an interesting file: %s", file)
            return

        # 2. Extract data from the file, and check if this data will actually change the plot.
        time.sleep(1)  # Wait a second to avoid permission issues with race condition
        score, _, horizontal_sens, _ = extract_data_from_file(str(Path(config['stats_dir'], file)))
        should_update = False
        score_to_beat = None  # don't really need to initialize this here, but squelches Python warning
        if horizontal_sens not in scenario_data:
            console_logger.debug("New sensitivity detected: %s", horizontal_sens)
            should_update = True
        else:
            previous_scores = sorted(scenario_data[horizontal_sens])
            score_to_beat = previous_scores[0]
            if len(previous_scores) > config['top_n_scores']:
                score_to_beat = previous_scores[-config['top_n_scores']]
            if score > score_to_beat:
                console_logger.debug("New top %s score: %s", config['top_n_scores'], score)
                should_update = True
        if not should_update:
            console_logger.debug(
                "Not a new sensitivity (%s), and score (%s) not high enough (%s).",
                horizontal_sens, score, score_to_beat)
            return
        new_data = True
        return


if __name__ == '__main__':
    # Get scenario data
    scenario_data = get_scenario_data(config['stats_dir'], config['scenario_to_monitor'], config['within_n_days'])

    # Do first time run and generate plot
    fig = generate_plot(scenario_data, config['scenario_to_monitor'], config['top_n_scores'])

    # Monitor for new files
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, config['stats_dir'],
                      recursive=False)  # Set recursive=True to monitor subdirectories
    observer.start()
    console_logger.info("Monitoring directory: %s", config['stats_dir'])

    # Run the Dash app
    app.run(debug=True, use_reloader=False, host="localhost", port=8080)

    # Probably don't need this but I kept it anyway
    observer.stop()
    observer.join()  # Wait until the observer thread terminates
