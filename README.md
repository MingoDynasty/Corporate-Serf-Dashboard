# Corporate Serf Dashboard

The name of this app is in honor of [Corporate Serf](https://www.youtube.com/watch?v=a-MShVYe3kY).

This app scans your Kovaak's Stats directory, and builds a plot of the given scenario, plotting Sensitivity vs Score. As
you keep playing and generating new scores, the plot will automatically update in the background.

## Tech Stack

1. Python
2. Dash
    1. Plotly.js
    2. Dash Mantine Components
    3. React
    4. Flask

## Requirements

1. Python 3.13 (Dash is bugged with Python 3.14)

## Installation / First Time Setup

1. Install the Python package dependencies: `pip install -r requirements.txt`
2. Make a copy of the `example.toml`. Name the new file `config.toml`.
3. Inside `config.toml`, update the `stats_dir` variable to point to your Kovaak's stats file directory.
4. Feel free to change any other settings inside the TOML file, or leave them at their defaults.

## Usage

1. Run the app in your terminal: `python source/app.py`
2. Open a browser and navigate to: http://localhost:8080/

## Example

![Corporate Serf Dashboard example](./assets/example.png "Corporate Serf Dashboard example")
