import logging  # Provides access to logging api.
import logging.config  # Provides access to logging configuration file.
import os
import sys
from datetime import datetime
import time
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import plotly.express as px
from pathlib import Path

from dash_extensions import Lottie
from dash_extensions.enrich import DashProxy, Input, Output, html
from dash_extensions.events import add_event_listener, dispatch_event, resolve_event_components
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from dash import Output, Input, html, callback, no_update
from dash import dcc
from dash_extensions.enrich import DashProxy
import threading
from dash_extensions.logging import NotificationsLogHandler

########################
# Constants
scenario_to_monitor = "VT Ground Intermediate S5 Bot 2"
stats_dir = "S:/SteamLibrary/steamapps/common/FPSAimTrainer/FPSAimTrainer/stats"

# Only care about runs within the last N days
within_n_days = 30

# Limit to the top N scores
top_n_scores = 5

# How often to poll for file updates (in milliseconds)
polling_interval = 5 * 1000
# can probably move these to a separate file at some point
########################

df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminder_unfiltered.csv')

log_handler = NotificationsLogHandler()
logger = log_handler.setup_logger(__name__)
app = DashProxy()

# TODO: Some global variables ?
new_data = False
fig = None


@app.callback(Output('live-update-text', 'children'),
              Input('interval-component', 'n_intervals'))
def update_layout(_):
    return f"Last file scan: {datetime.now()}"


@app.callback(
    Output('graph-content', 'figure'),
    Output("notification-container", "sendNotifications"),
    # Input('dropdown-selection', 'value'),
    Input('live-update-text', 'children')
)
def update_graph(_):
    global fig, new_data
    # console_logger.debug("Checking for updates...")
    if not new_data:
        return fig, no_update

    # Get voltaic data
    console_logger.debug("Performing update...")
    voltaic_data = get_voltaic_data()
    fig = initialize_plot(voltaic_data)

    new_data = False
    notification = {
        "action": "show",
        "title": "Notification",
        "message": "Graph has been updated!",
        "color": "blue",
        "id": "notify"
    }
    return fig, [notification]


app.layout = dmc.MantineProvider(
    [
        dmc.NotificationContainer(id="notification-container"),
        html.H1(children='My Dash App', style={'textAlign': 'center'}),
        dcc.Dropdown(df.country.unique(), 'Canada', id='dropdown-selection'),
        # html.Div([
        #     "Input: ",
        #     dcc.Input(id='my-input', value=10, type='text')
        # ]),
        html.Div(id='live-update-text'),
        dcc.Interval(
            id='interval-component',
            interval=polling_interval,
            n_intervals=0
        ),
        dcc.Graph(id='graph-content')
    ]
    + log_handler.embed()
    + resolve_event_components()  # must be called *after* all callbacks have been defined
)


def extract_data_from_file(filename: str) -> tuple:
    file_path = Path(stats_dir, filename)
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
    if scenario_name != scenario_to_monitor:
        return False

    # splits = filename.split(" ")
    splits = file.split(" - Challenge - ")
    datetime_string = splits[1].split(" ")[0]
    format_string = "%Y.%m.%d-%H.%M.%S"
    datetime_object = datetime.strptime(datetime_string, format_string)
    delta = datetime.today() - datetime_object
    if delta.days > within_n_days:
        return False

    return True


def get_voltaic_data() -> dict:
    files = [f for f in os.listdir(stats_dir) if os.path.isfile(os.path.join(stats_dir, f))]
    csv_files = [file for file in files if file.endswith(".csv")]
    voltaic_files = []
    for file in csv_files:
        scenario_name = file.split("-")[0].strip()
        if scenario_name == scenario_to_monitor:
            voltaic_files.append(file)

    # Get the subset of files that we care about;
    # i.e. the files that pertain to the list of scenarios that we care about
    # subset_files = []
    voltaic_data = dict()
    # for benchmark in voltaic_benchmarks:
    voltaic_data[scenario_to_monitor] = dict()
    for file in voltaic_files:
        splits = file.split(" - Challenge - ")
        datetime_string = splits[1].split(" ")[0]
        format_string = "%Y.%m.%d-%H.%M.%S"
        datetime_object = datetime.strptime(datetime_string, format_string)
        delta = datetime.today() - datetime_object
        if delta.days > within_n_days:
            continue

        scenario_name = file.split("-")[0].strip()
        score, sens_scale, horizontal_sens, _ = extract_data_from_file(file)
        # key = horizontal_sens + " " + sens_scale
        key = horizontal_sens
        # console_logger.debug(key)
        scenario_data = voltaic_data[scenario_name]
        if key not in scenario_data:
            scenario_data[key] = []
        scenario_data[key].append(score)
        # subset_files.append(file)

    # Sort by Sensitivity
    for scenario in voltaic_data:
        data = voltaic_data[scenario]
        sorted_dict_by_key = dict(sorted(data.items()))
        voltaic_data[scenario] = sorted_dict_by_key
    return voltaic_data


def initialize_plot(voltaic_data: dict) -> go.Figure:
    for scenario, data in voltaic_data.items():
        # x and y given as array_like objects
        x_data = []
        y_data = []
        average_x_data = []
        average_y_data = []
        for sens, scores in data.items():
            # Get top N scores for each sensitivity
            sorted_list = sorted(scores, reverse=True)
            top_n_largest = sorted_list[:top_n_scores]
            for score in top_n_largest:
                x_data.append(sens)
                y_data.append(score)
            average_x_data.append(sens)
            average_y_data.append(np.mean(top_n_largest))
        if len(data.keys()) <= 2:
            # We need at least 3 sensitivities to generate a trendline
            console_logger.debug(f"WARNING: Skipping '{scenario}' due to insufficient Sensitivity data.")
            return

        current_date = datetime.now().ctime()
        title = f"{scenario} (last updated: {str(current_date)})"
        console_logger.debug(f"Generating plot for: {scenario}")
        fig1 = px.scatter(
            title=title,
            x=x_data,
            y=y_data,
            labels={
                "x": "Sensitivity (cm/360)",
                "y": f"Score (top {top_n_scores})",
            })
        # trendline="lowess")  # TODO: instead of trend line, simply use average?
        fig2 = px.line(
            x=average_x_data,
            y=average_y_data,
            # title="My Title",
            labels={
                "x": "Sensitivity (cm/360)",
                "y": "Average Score",
            },
        )

        fig3 = go.Figure(data=fig1.data + fig2.data, layout=fig1.layout)
        fig3['data'][0]['name'] = 'Score Data'
        fig3['data'][0]['showlegend'] = True
        fig3['data'][1]['name'] = 'Average Score'
        fig3['data'][1]['showlegend'] = True
        # fig3.show()
    return fig3


class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        global new_data
        if event.is_directory:  # Check if it's a file, not a directory
            return
        console_logger.debug(f"Detected new file: {event.src_path}")
        # Add your custom logic here to process the new file
        # For example, you could read its content, move it, or trigger another function.
        # update_plot_with_file(event.src_path)
        file = event.src_path

        # 1. Check if this file is a file that we care about.
        if not is_file_of_interest(file):
            console_logger.debug(f"Not an interesting file: {file}")
            return

        # 2. Extract data from the file, and check if this data will actually change the plot.
        time.sleep(1)  # Wait a second to avoid permission issues with race condition
        score, sens_scale, horizontal_sens, scenario = extract_data_from_file(file)
        should_update = False
        if horizontal_sens not in voltaic_data[scenario]:
            console_logger.debug(f"New sensitivity detected: {horizontal_sens}")
            should_update = True
        else:
            previous_scores = sorted(voltaic_data[scenario][horizontal_sens])

            score_to_beat = previous_scores[0]
            if len(previous_scores) > top_n_scores:
                score_to_beat = previous_scores[-top_n_scores]
            if score > score_to_beat:
                console_logger.debug(f"New top {top_n_scores} score: {score}")
                should_update = True
        if not should_update:
            console_logger.debug(
                f"Not a new sensitivity ({horizontal_sens}), and score ({score}) not high enough ({score_to_beat}).")
            return
        new_data = True
        return

    # def should_update(self, event):


if __name__ == '__main__':
    log_format = "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s"
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=log_format)
    console_logger = logging.getLogger(__name__)

    # Get voltaic data
    voltaic_data = get_voltaic_data()

    # Do first time run and intialize plot
    fig = initialize_plot(voltaic_data)

    # Monitor for new files
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, stats_dir, recursive=True)  # Set recursive=True to monitor subdirectories
    observer.start()
    console_logger.info(f"Monitoring directory: {stats_dir}")

    # try:
    #     while True:
    #         time.sleep(1)  # Keep the main thread alive
    # except KeyboardInterrupt:
    #     observer.stop()
    # observer.join()  # Wait until the observer thread terminates

    app.run(debug=True, use_reloader=False)
