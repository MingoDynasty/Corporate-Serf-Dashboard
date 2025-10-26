import logging  # Provides access to logging api.
import logging.config  # Provides access to logging configuration file.
import os
import sys
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from dash import Output, Input, html, callback
from dash import dcc
from dash_extensions.enrich import DashProxy
from dash_extensions.logging import NotificationsLogHandler

df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminder_unfiltered.csv')

log_handler = NotificationsLogHandler()
logger = log_handler.setup_logger(__name__)
app = DashProxy()

# app.layout = Lottie(
#     options=dict(
#         loop=True,
#         autoplay=True,
#         style=dict(width="25%", margin="auto"),
#     ),
#     url="https://assets6.lottiefiles.com/packages/lf20_rwwvwgka.json",
# )

app.layout = dmc.MantineProvider([
                                     dmc.NotificationContainer(id="notification-container"),
                                     html.H1(children='Title of Dash App', style={'textAlign': 'center'}),
                                     dcc.Dropdown(df.country.unique(), 'Canada', id='dropdown-selection'),
                                     dcc.Graph(id='graph-content')
                                 ] + log_handler.embed()
                                 )


@callback(
    Output('graph-content', 'figure'),
    Output("notification-container", "sendNotifications"),
    Input('dropdown-selection', 'value'),
    log=True
)
def update_graph(value):
    console_logger.debug("mingotest update graph")
    np.random.seed(1)

    N = 10
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


if __name__ == '__main__':
    log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=log_format)
    console_logger = logging.getLogger(__name__)

    # Get voltaic data
    # voltaic_data = get_voltaic_data()
    #
    # # Do first time run and intialize plot
    # initialize_plot(voltaic_data)
    #
    # df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminder_unfiltered.csv')
    # app = Dash()
    # # Requires Dash 2.17.0 or later
    # app.layout = [
    #     html.H1(children='Title of Dash App', style={'textAlign': 'center'}),
    #     dcc.Dropdown(df.country.unique(), 'Canada', id='dropdown-selection'),
    #     dcc.Graph(id='graph-content')
    # ]
    #
    # # Monitor for new files
    # event_handler = NewFileHandler()
    # observer = Observer()
    # observer.schedule(event_handler, stats_dir, recursive=True)  # Set recursive=True to monitor subdirectories
    # observer.start()
    # logger.info(f"Monitoring directory: {stats_dir}")
    #
    # try:
    #     while True:
    #         time.sleep(1)  # Keep the main thread alive
    # except KeyboardInterrupt:
    #     observer.stop()
    # observer.join()  # Wait until the observer thread terminates

    app.run(debug=True)
