"""
Entrypoint to the Corporate Serf Dashboard app.
"""
import logging.config  # Provides access to logging configuration file.
import os
import sys
import time
import tomllib
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import dash_mantine_components as dmc
import numpy as np
import plotly.express as px
import plotly.graph_objs as go
import tomli_w
from dash import Output, Input, html, no_update, clientside_callback
from dash import dcc
from dash_extensions.enrich import DashProxy
from dash_extensions.logging import NotificationsLogHandler
from dash_iconify import DashIconify
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

log_handler = NotificationsLogHandler()
logger = log_handler.setup_logger(__name__)
app = DashProxy()

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s"
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=LOG_FORMAT)
console_logger = logging.getLogger(__name__)

# Pull arguments from a config file.
CONFIG_FILE = "config.toml"
with open(CONFIG_FILE, "rb") as _file:
    config = tomllib.load(_file)
console_logger.debug("Loaded config: %s", config)

# TODO: Global variables best practices ?
scenario_data = {}
new_data = False
fig = None


def get_unique_scenarios(_dir: str) -> list:
    """
    Gets the list of unique scenarios from a directory.
    :param _dir: directory to search for scenarios.
    :return: list of unique scenarios
    """
    unique_scenarios = set()
    files = [file for file in os.listdir(config['stats_dir']) if
             os.path.isfile(os.path.join(config['stats_dir'], file))]
    csv_files = [file for file in files if file.endswith(".csv")]
    for file in csv_files:
        scenario_name = file.split("-")[0].strip()
        unique_scenarios.add(scenario_name)
    return sorted(list(unique_scenarios))


all_scenarios = get_unique_scenarios(config['stats_dir'])


def update_config() -> None:
    """Write the current config file to disk."""
    with open(CONFIG_FILE, 'wb') as file:
        tomli_w.dump(config, file)


@app.callback(
    Input('interval-component', 'n_intervals'),
    Output('live-update-text', 'children'),
    Output('do_update', 'data', allow_duplicate=True))
def update_layout(_) -> tuple[str, bool]:
    """
    This function simply serves as a periodic trigger to update the graph if there is new data.
    :param _: Number of times the interval has passed. Unused, but callback functions must have at least one input.
    :return: Current datetime, and the new_data flag.
    """
    return f"Last file scan: {datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")}", new_data


@app.callback(
    Input('dropdown-selection', 'value'),
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

    scenario_data = get_scenario_data(config['scenario_to_monitor'])
    if not scenario_data:
        console_logger.warning(
            "No scenario data for '%s'. Perhaps choose a longer date range?", config['scenario_to_monitor'])
        return fig, no_update

    console_logger.debug("Performing update...")
    fig = initialize_plot(scenario_data)

    new_data = False
    notification = {
        "action": "show",
        "title": "Notification",
        "message": "Graph updated!",
        "color": "blue",
        "id": "notify"
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
                                id="dropdown-selection",
                                data=all_scenarios,
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
        dcc.Graph(id='graph-content', style={'height': '85vh'}),
        dmc.Group(
            children=[
                dmc.Text(id='live-update-text', size="md", ml='xl'),
                dmc.Anchor(DashIconify(icon="logos:discord-icon", width=40),
                           href="https://discordapp.com/users/222910150636339211"),
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


def extract_data_from_file(filename: str) -> tuple[Optional[float], Optional[str], Optional[str], Optional[str]]:
    """
    Extracts data from a scenario CSV file.
    :param filename: name of file to extract data from.
    :return: Score, Sensitivity Scale, Horizontal Sensitivity, Scenario name
    :example: 12345, 'cm/360', '40.0', 'VT Snake Track'
    """
    file_path = Path(config['stats_dir'], filename)
    with open(file_path, 'r', encoding="utf-8") as file:
        lines_list = file.readlines()  # Read all lines into a list
    score = None
    sens_scale = None
    horizontal_sens = None
    scenario = None
    for line in lines_list:
        if line.startswith("Score:"):
            score = float(line.split(",")[1].strip())
        elif line.startswith("Sens Scale:"):
            sens_scale = line.split(",")[1].strip()
        elif line.startswith("Horiz Sens:"):
            horizontal_sens = line.split(",")[1].strip()
        elif line.startswith("Scenario:"):
            scenario = line.split(",")[1].strip()
    return score, sens_scale, horizontal_sens, scenario


def is_file_of_interest(file: str) -> bool:
    """
    Check if a file is of interest. More specifically:
    1. The file is related to a scenario that we are monitoring (i.e. user has selected).
    2. The file is not too old, based on the date the user selected.
    :param file: full file path of the file to check.
    :return: True if the file is interesting, else False.
    """
    if not file.endswith(".csv"):
        return False

    filename = Path(file).stem
    scenario_name = filename.split("-")[0].strip()
    if scenario_name != config['scenario_to_monitor']:
        return False

    # splits = filename.split(" ")
    splits = file.split(" - Challenge - ")
    datetime_string = splits[1].split(" ")[0]
    format_string = "%Y.%m.%d-%H.%M.%S"
    datetime_object = datetime.strptime(datetime_string, format_string)
    delta = datetime.today() - datetime_object
    if delta.days > config['within_n_days']:
        return False

    return True


def get_scenario_data(scenario: str) -> dict:
    """
    Get scenario data for a given scenario.
    :param scenario: the name of a scenario to get data for.
    :return: dictionary of scenario data.
    """
    files = [file for file in os.listdir(config['stats_dir']) if
             os.path.isfile(os.path.join(config['stats_dir'], file))]
    csv_files = [file for file in files if file.endswith(".csv")]
    scenario_files = []
    for file in csv_files:
        scenario_name = file.split("-")[0].strip()
        if scenario_name == scenario:
            scenario_files.append(file)

    # Get the subset of files that pertain to the scenario
    _scenario_data: dict[str, list] = {}
    for scenario_file in scenario_files:
        splits = scenario_file.split(" - Challenge - ")
        datetime_string = splits[1].split(" ")[0]
        format_string = "%Y.%m.%d-%H.%M.%S"
        datetime_object = datetime.strptime(datetime_string, format_string)
        delta = datetime.today() - datetime_object
        if delta.days > config['within_n_days']:
            continue

        # scenario_name = scenario_file.split("-")[0].strip()
        score, _, horizontal_sens, _ = extract_data_from_file(scenario_file)
        if not horizontal_sens:
            # Missing sens data.
            continue

        # key = horizontal_sens + " " + sens_scale
        key = horizontal_sens
        # console_logger.debug(key)
        if key not in _scenario_data:
            _scenario_data[key] = []
        _scenario_data[key].append(score)
        # subset_files.append(file)

    # Sort by Sensitivity
    _scenario_data = dict(sorted(_scenario_data.items()))
    return _scenario_data


def initialize_plot(_scenario_data: dict) -> go.Figure:
    """TODO: rename to generate
    Initialize a plot using the scenario data.
    :param _scenario_data: the scenario data to use for the plot.
    :return: go.Figure Plot
    """
    if not _scenario_data:
        return go.Figure()
    x_data = []
    y_data = []
    average_x_data = []
    average_y_data = []
    for sens, scores in _scenario_data.items():
        # Get top N scores for each sensitivity
        sorted_list = sorted(scores, reverse=True)
        top_n_largest = sorted_list[:config['top_n_scores']]
        for score in top_n_largest:
            x_data.append(sens)
            y_data.append(score)
        average_x_data.append(sens)
        average_y_data.append(np.mean(top_n_largest))
    # If we want to generate a trendline (e.g. lowess)
    # if len(data.keys()) <= 2:
    #     # We need at least 3 sensitivities to generate a trendline
    #     console_logger.debug(f"WARNING: Skipping '{scenario}' due to insufficient Sensitivity data.")
    #     return

    # current_date = datetime.now().ctime()
    current_datetime = datetime.today().strftime("%Y-%m-%d %I:%M:%S %p")
    title = f"{config['scenario_to_monitor']} (last updated: {str(current_datetime)})"
    console_logger.debug("Generating plot for: %s", config['scenario_to_monitor'])
    fig1 = px.scatter(
        title=title,
        x=x_data,
        y=y_data,
        labels={
            "x": "Sensitivity (cm/360)",
            "y": f"Score (top {config['top_n_scores']})",
        })
    # trendline="lowess"  # simply using average line for now
    fig2 = px.line(
        x=average_x_data,
        y=average_y_data,
        # title="My Title",
        labels={
            "x": "Sensitivity (cm/360)",
            "y": "Average Score",
        },
    )

    combined_figure = go.Figure(data=fig1.data + fig2.data, layout=fig1.layout)
    combined_figure['data'][0]['name'] = 'Score Data'
    combined_figure['data'][0]['showlegend'] = True
    combined_figure['data'][1]['name'] = 'Average Score'
    combined_figure['data'][1]['showlegend'] = True
    return combined_figure


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
        if not is_file_of_interest(file):
            console_logger.debug("Not an interesting file: %s", file)
            return

        # 2. Extract data from the file, and check if this data will actually change the plot.
        time.sleep(1)  # Wait a second to avoid permission issues with race condition
        score, _, horizontal_sens, _ = extract_data_from_file(file)
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
    scenario_data = get_scenario_data(config['scenario_to_monitor'])

    # Do first time run and initialize plot
    fig = initialize_plot(scenario_data)

    # Monitor for new files
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, config['stats_dir'],
                      recursive=False)  # Set recursive=True to monitor subdirectories
    observer.start()
    console_logger.info("Monitoring directory: %s", config['stats_dir'])

    # Run the Dash app
    app.run(debug=True, use_reloader=False)

    # Probably don't need this but I kept it anyway
    observer.stop()
    observer.join()  # Wait until the observer thread terminates
