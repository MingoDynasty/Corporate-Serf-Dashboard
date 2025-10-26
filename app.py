import logging  # Provides access to logging api.
import logging.config  # Provides access to logging configuration file.
import os
import sys
import datetime
import time
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from dash_extensions import Lottie
from dash_extensions.enrich import DashProxy, Input, Output, html
from dash_extensions.events import add_event_listener, dispatch_event, resolve_event_components
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from dash import Output, Input, html, callback
from dash import dcc
from dash_extensions.enrich import DashProxy
import threading
from dash_extensions.logging import NotificationsLogHandler

df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminder_unfiltered.csv')

log_handler = NotificationsLogHandler()
logger = log_handler.setup_logger(__name__)
app = DashProxy()


# @app.callback(Output('live-update-text', 'children'),
#               Output('my-input', 'value'),
#               Input('interval-component', 'n_intervals'))
# def update_layout(n):
#     # This function will be called every 3 second
#     return f"Last updated: {datetime.datetime.now()}", np.random.randint(0, 10)


@app.callback(
    Output('graph-content', 'figure'),
    Output("notification-container", "sendNotifications"),
    # Input('dropdown-selection', 'value'),
    Input('my-input', 'value')
)
def update_graph(value):
    console_logger.debug("mingotest update graph debug")
    # console_logger.info("mingotest update graph info")
    # console_logger.error("mingotest update graph error")
    np.random.seed(1)

    # N = 10
    N = value
    random_x = np.linspace(0, 1, N)
    random_y0 = np.random.randn(N) + 5
    random_y1 = np.random.randn(N)
    random_y2 = np.random.randn(N) - 5

    # Create traces
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=random_x, y=random_y0,
                             mode='lines',
                             name='lines'))
    fig.add_trace(go.Scatter(x=random_x, y=random_y1,
                             mode='lines+markers',
                             name='lines+markers'))
    fig.add_trace(go.Scatter(x=random_x, y=random_y2,
                             mode='markers', name='markers'))

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
        html.H1(children='Title of Dash App', style={'textAlign': 'center'}),
        dcc.Dropdown(df.country.unique(), 'Canada', id='dropdown-selection'),
        html.Div([
            "Input: ",
            dcc.Input(id='my-input', value=10, type='text')
        ]),
        html.Div(id='live-update-text'),
        dcc.Interval(
            id='interval-component',
            interval=3 * 1000,  # in milliseconds, updates every 1 second
            n_intervals=0
        ),
        dcc.Graph(id='graph-content')
    ]
    + log_handler.embed()
    + resolve_event_components()  # must be called *after* all callbacks have been defined
)


class NewFileHandler(FileSystemEventHandler):
    # global fig3

    def on_created(self, event):
        if event.is_directory:  # Check if it's a file, not a directory
            return
        console_logger.debug(f"Detected new file: {event.src_path}")
        # print(fig3)
        # df = pd.DataFrame(dict(
        #     x=[1, 3, 2, 4],
        #     y=[1, 2, 3, 4]
        # ))
        # fig3.data[0] = df
        # print(fig_widget.data)
        # trace1 = go.Scattergl(x=[1, 2, 3],
        #                       y=[5, -1, 7],
        #                       )
        # fig3.add_trace(trace1)
        # fig3.show()
        # update_plot_with_file(event.src_path)
        time.sleep(5)
        console_logger.debug("Update complete.")
        # Add your custom logic here to process the new file
        # For example, you could read its content, move it, or trigger another function.


if __name__ == '__main__':
    log_format = "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s"
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=log_format)
    console_logger = logging.getLogger(__name__)

    # # Create a thread and set it as a daemon
    # daemon_thread = threading.Thread(target=background_task, daemon=True)
    #
    # # Start the daemon thread
    # daemon_thread.start()

    # Get voltaic data
    # voltaic_data = get_voltaic_data()
    #
    # # Do first time run and intialize plot
    # initialize_plot(voltaic_data)
    #

    stats_dir = "S:/SteamLibrary/steamapps/common/FPSAimTrainer/FPSAimTrainer/stats"

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
