import numpy as np
import pandas as pd
import plotly.graph_objs as go
from dash import Dash, html, dcc, callback, Output, Input

df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminder_unfiltered.csv')

app = Dash()

# Requires Dash 2.17.0 or later
app.layout = [
    html.H1(children='Title of Dash App', style={'textAlign': 'center'}),
    dcc.Dropdown(df.country.unique(), 'Canada', id='dropdown-selection'),
    dcc.Graph(id='graph-content')
]


@callback(
    Output('graph-content', 'figure'),
    Input('dropdown-selection', 'value')
)
def update_graph(value):
    print(value)
    # dff = df[df.country == value]
    # return px.line(dff, x='year', y='pop')
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
    # fig.show()
    return fig


if __name__ == '__main__':
    app.run(debug=True)
