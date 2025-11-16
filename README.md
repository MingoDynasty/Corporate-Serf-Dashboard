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

## First Time Setup

1. Make a copy of the `example.toml`. Name the new file `config.toml`.
2. Inside `config.toml`, update the `stats_dir` variable to point to your Kovaak's stats file directory.
3. Feel free to change any other settings inside the TOML file, or leave them at their defaults.

## Usage

Step 1: Run the app in your terminal:

```shell
uv sync
uv run python source/app.py
```

Step 2: Open a browser and navigate to: <http://localhost:8080/>

## Example

![Corporate Serf Dashboard example](docs/example.png "Corporate Serf Dashboard example")

## Rank Data

In essence, "benchmarks" are basically just "playlists" but with rank data attached. With the help of
the <http://Evxl.app>'s author, I combined his benchmarks data with playlist data from KovaaK's API, for most of the
common benchmarks. These files are in `ressources/playlists/generated`. If you wish to include a specific benchmark into
the app, then simply copy the desired JSON file from `resources/playlists/generated` to `resources/playlists`. Then
restart the app.

## Import Playlist

In the `Settings` modal, there is an option to import a playlist via share code. This is the only part of the app that
requires an internet connection, as the app queries the KovaaK's API with your input share code to retrieve the playlist
data.

Note that by importing playlists this way, the playlist will not include rank data. If you want to include rank data for
the rank overlays, then see the **Rank Data** section.
