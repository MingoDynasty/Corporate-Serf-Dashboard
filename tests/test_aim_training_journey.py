"""The Journey page explains an empty chart on the canvas, never in a toast."""

import logging
from datetime import datetime

import dash
import dash_mantine_components as dmc
import pytest
from dash.exceptions import PreventUpdate

dash.Dash(__name__, use_pages=True, pages_folder="")
# The light/dark templates the page's figures resolve are registered by the
# app at import time; a page-only test has to register them itself.
dmc.add_figure_templates()

from source.pages import aim_training_journey as journey  # noqa: E402


def _empty_state_title(figure) -> str | None:
    """Return the on-canvas empty-state heading, or None for a real chart."""
    annotations = figure.layout.annotations
    if not annotations:
        return None
    return annotations[0].text


@pytest.fixture
def known_playlists(monkeypatch):
    """Accept every requested code and label it by its code."""
    monkeypatch.setattr(
        journey,
        "filter_known_playlist_codes",
        list,
    )
    monkeypatch.setattr(
        journey,
        "get_playlist_display_label",
        lambda code: f"{code} Playlist",
    )
    monkeypatch.setattr(
        journey,
        "get_aim_training_checkpoints",
        lambda _hour: {},
    )


def test_a_pre_hydration_color_scheme_renders_nothing():
    with pytest.raises(PreventUpdate):
        journey.generate_graph(["A"], 10, None)


@pytest.mark.parametrize("selection", [None, []])
def test_no_selection_says_so_on_the_canvas(selection):
    figure = journey.generate_graph(selection, 10, "light")

    assert "No playlists selected" in _empty_state_title(figure)


def test_only_unknown_codes_says_so_on_the_canvas(monkeypatch):
    monkeypatch.setattr(journey, "filter_known_playlist_codes", lambda _codes: [])

    figure = journey.generate_graph(["Gone"], 10, "light")

    assert "No playlists selected" in _empty_state_title(figure)


def test_a_missing_checkpoint_hour_says_so_on_the_canvas(known_playlists):
    figure = journey.generate_graph(["A"], None, "light")

    assert "Graph settings incomplete" in _empty_state_title(figure)


def test_playlists_without_runs_render_an_in_page_empty_state(
    monkeypatch,
    known_playlists,
    caplog,
):
    monkeypatch.setattr(
        journey,
        "get_aim_training_journey_for_playlists",
        lambda codes: {code: {} for code in codes},
    )

    with caplog.at_level(logging.WARNING, logger=journey.logger.name):
        figure = journey.generate_graph(["A", "B"], 10, "light")

    assert journey._NO_JOURNEY_DATA_PLOT_TITLE in _empty_state_title(figure)
    # The developer record stays in the log; the user reads the canvas.
    assert "Insufficient data for playlist: A Playlist" in caplog.text
    assert "Insufficient data for playlist: B Playlist" in caplog.text


def test_one_playlist_with_runs_still_plots(monkeypatch, known_playlists, caplog):
    monkeypatch.setattr(
        journey,
        "get_aim_training_journey_for_playlists",
        lambda _codes: {
            "A": {datetime(2026, 1, 1): 0.5, datetime(2026, 2, 1): 0.6},
            "B": {},
        },
    )

    with caplog.at_level(logging.WARNING, logger=journey.logger.name):
        figure = journey.generate_graph(["A", "B"], 10, "light")

    # A partial selection is not an empty state: the playlist with runs is
    # plotted, and the one without contributes an empty series as it always
    # has.
    assert _empty_state_title(figure) is None
    plotted = {len(trace.y) for trace in figure.data}
    assert plotted == {0, 2}
    assert "Insufficient data for playlist: B Playlist" in caplog.text
