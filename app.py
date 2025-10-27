import logging.config  # Provides access to logging configuration file.
import os
import sys
import time
import tomllib
from datetime import date, datetime, timedelta
from pathlib import Path

import dash_mantine_components as dmc
import numpy as np
import plotly.express as px
import plotly.graph_objs as go
import tomli_w
from dash import Output, Input, html, no_update
from dash import dcc
from dash_extensions.enrich import DashProxy
from dash_extensions.logging import NotificationsLogHandler
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

log_handler = NotificationsLogHandler()
logger = log_handler.setup_logger(__name__)
app = DashProxy()

log_format = "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s"
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=log_format)
console_logger = logging.getLogger(__name__)

# Pull arguments from a config file.
config_file = "config.toml"
with open(config_file, "rb") as _file:
    config = tomllib.load(_file)
console_logger.debug(f"Loaded config: {config}")

# TODO: Global variables best practices ?
scenario_data = {}
new_data = False
fig = None


def get_unique_scenarios(_dir: str) -> list:
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
    with open(config_file, 'wb') as file:
        tomli_w.dump(config, file)


@app.callback(
    Input('interval-component', 'n_intervals'),
    Output('live-update-text', 'children'),
    Output('do_update', 'data', allow_duplicate=True))
def update_layout(_):
    return f"Last file scan: {datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")}", new_data


@app.callback(
    Input('dropdown-selection', 'value'),
    Output('do_update', 'data', allow_duplicate=True),
    prevent_initial_call=True)
def select_new_scenario(new_scenario):
    console_logger.debug(f"New scenario selected: {new_scenario}")
    config['scenario_to_monitor'] = new_scenario
    update_config()
    return True


@app.callback(
    Input('top_n_scores', 'value'),
    Output('do_update', 'data', allow_duplicate=True),
    prevent_initial_call=True)
def update_top_n_scores(new_top_n_scores):
    if not new_top_n_scores:
        return False
    console_logger.debug(f"New top_n_scores: {new_top_n_scores}")
    config['top_n_scores'] = new_top_n_scores
    update_config()
    return True


@app.callback(
    Input('date-picker', 'value'),
    Output('do_update', 'data', allow_duplicate=True),
    prevent_initial_call=True)
def update_within_n_days(new_date):
    console_logger.debug(f"New date: {new_date}")
    date_object = date.fromisoformat(new_date)
    new_within_n_days = (date.today() - date_object).days

    console_logger.debug(f"New within_n_days: {new_within_n_days}")
    config['within_n_days'] = new_within_n_days
    update_config()
    return True


@app.callback(
    Input('do_update', 'data'),
    Output('graph-content', 'figure'),
    Output("notification-container", "sendNotifications"),
)
def update_graph(do_update):
    global fig, new_data, scenario_data
    if not do_update:
        return fig, no_update

    # No scenario selected yet
    if not config['scenario_to_monitor']:
        return fig, no_update

    console_logger.debug("Performing update...")
    scenario_data = get_scenario_data(config['scenario_to_monitor'])
    if not scenario_data:
        console_logger.warning(
            f"No scenario data for '{config['scenario_to_monitor']}'. Perhaps choose a longer date range?")
        return fig, no_update

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
        html.Div([
            html.Label('Selected Scenario',
                       style={
                           'line-height': '34px',
                           'margin-left': 50,
                           'margin-right': 10,
                           'font-weight': 'bold'}
                       ),
            dcc.Dropdown(
                all_scenarios,
                placeholder='Select a scenario...',
                value=config['scenario_to_monitor'],
                id='dropdown-selection',
                persistence=True,
                maxHeight=1000,
                style={"width": "800px"},
            ),
            html.Label('Top N Scores',
                       style={
                           'line-height': '34px',
                           'margin-left': 50,
                           'margin-right': 10,
                           'font-weight': 'bold'}
                       ),
            dcc.Input(
                id='top_n_scores',
                placeholder='Enter top N scores to consider...',
                type='number',
                value=config['top_n_scores'],
                min=1,
                persistence=True,
                style={"width": "130px", "height": "36px"}
            ),
            html.Label('Oldest date to consider',
                       style={
                           'line-height': '34px',
                           'margin-left': 50,
                           'margin-right': 10,
                           'font-weight': 'bold'}
                       ),
            dmc.DatePickerInput(
                id='date-picker',
                value=(datetime.now() - timedelta(days=config['within_n_days'])),
                maxDate=datetime.now(),
                persistence=True,
            ),
        ], style={"display": "flex"}),
        dcc.Graph(id='graph-content', style={'height': '85vh'}),
        html.Div(id='live-update-text'),
        dcc.Store(id='do_update', storage_type='memory')  # Stores data in browser's memory
    ]
    + log_handler.embed()
)


def extract_data_from_file(filename: str) -> tuple:
    file_path = Path(config['stats_dir'], filename)
    with open(file_path, 'r') as file:
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
        score, sens_scale, horizontal_sens, _ = extract_data_from_file(scenario_file)
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
    console_logger.debug(f"Generating plot for: {config['scenario_to_monitor']}")
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
    def on_created(self, event):
        global new_data, scenario_data
        if event.is_directory:  # Check if it's a file, not a directory
            return
        console_logger.debug(f"Detected new file: {event.src_path}")
        # Add your custom logic here to process the new file
        # For example, you could read its content, move it, or trigger another function.
        file = event.src_path

        # 1. Check if this file is a file that we care about.
        if not is_file_of_interest(file):
            console_logger.debug(f"Not an interesting file: {file}")
            return

        # 2. Extract data from the file, and check if this data will actually change the plot.
        time.sleep(1)  # Wait a second to avoid permission issues with race condition
        score, sens_scale, horizontal_sens, scenario = extract_data_from_file(file)
        should_update = False
        score_to_beat = None  # don't really need to initialize this here, but squelches Python warning
        if horizontal_sens not in scenario_data:
            console_logger.debug(f"New sensitivity detected: {horizontal_sens}")
            should_update = True
        else:
            previous_scores = sorted(scenario_data[horizontal_sens])
            score_to_beat = previous_scores[0]
            if len(previous_scores) > config['top_n_scores']:
                score_to_beat = previous_scores[-config['top_n_scores']]
            if score > score_to_beat:
                console_logger.debug(f"New top {config['top_n_scores']} score: {score}")
                should_update = True
        if not should_update:
            console_logger.debug(
                f"Not a new sensitivity ({horizontal_sens}), and score ({score}) not high enough ({score_to_beat}).")
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
    console_logger.info(f"Monitoring directory: {config['stats_dir']}")

    # Run the Dash app
    app.run(debug=True, use_reloader=False)

    # Probably don't need this but I kept it anyway
    observer.stop()
    observer.join()  # Wait until the observer thread terminates
