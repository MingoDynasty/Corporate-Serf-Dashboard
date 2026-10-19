"""Build the Scenario Stats card and wire its callbacks to a page's ids.

The card holds Category and Number of runs under its first line, or says no
scenario is selected. A page that hosts it fills in a ``ScenarioStatsIds``,
puts ``scenario_stats_panel`` in its layout, and calls
``register_scenario_stats`` with the ids once, at import. The callbacks are
plain functions here and are registered once per page.
"""

from typing import NamedTuple

import dash_mantine_components as dmc
from dash import Input, Output, callback, html

from source.components.latest_run_card import EMPTY_TITLE_CLASS
from source.components.run_history_list import NO_SCENARIO_TEXT
from source.kovaaks.data_service import (
    get_playlist_by_code,
    get_scenario_stats,
    is_benchmark_playlist,
    is_scenario_in_database,
)
from source.kovaaks.playlist_scenarios_service import playlist_scenario_groups

SCENARIO_STATS_LABEL = "Scenario stats"


class ScenarioStatsIds(NamedTuple):
    """The component ids one page gives its Scenario Stats card.

    Two pages need two sets: the callbacks are registered once per set, and
    Dash allows one callback per output.

    ``scenario_stats_panel`` builds the card from ``category_row``,
    ``category``, ``num_runs_row``, ``num_runs`` and ``no_scenario``.
    ``run_events``, ``scenario_dropdown`` and ``playlist_filter`` are the
    page's own. The card reads them and builds none of them: ``run_events``
    is the store the page's run delivery writes when new runs land on the
    scenario it shows.
    """

    category_row: str
    category: str
    num_runs_row: str
    num_runs: str
    no_scenario: str
    run_events: str
    scenario_dropdown: str
    playlist_filter: str


def get_scenario_category(
    _, selected_scenario: str | None, playlist_code: str | None
) -> tuple[str, bool]:
    """Read the selected benchmark's table group and whether to hide its row."""
    if not selected_scenario or not playlist_code:
        return "", True
    playlist = get_playlist_by_code(playlist_code)
    if playlist is None or not is_benchmark_playlist(playlist):
        return "", True
    groups = playlist_scenario_groups(playlist)
    for scenario, group in zip(playlist.scenarios, groups, strict=True):
        if scenario.name == selected_scenario and group is not None:
            return (
                f"{group.category} · {group.subcategory}"
                if group.subcategory
                else group.category,
                False,
            )
    return "", True


def get_scenario_num_runs(_, selected_scenario) -> tuple[int | None, bool, bool]:
    """Count the selected scenario's runs, and choose between that line and no selection.

    Returns the count, whether to hide its line, and whether to hide the line
    that says no scenario is selected. With nothing selected the card says
    so, as the PB card and the latest-run card beside it do: a count of zero
    there would read as a fact about a scenario. The first argument is the
    page's run-events store, which triggers the call and is not read.
    """
    if not selected_scenario:
        return None, True, False
    if not is_scenario_in_database(selected_scenario):
        return 0, False, True
    return get_scenario_stats(selected_scenario).number_of_runs, False, True


def scenario_stats_panel(ids: ScenarioStatsIds) -> dmc.Box:
    """Build the Scenario Stats card: its first line and the lines under it."""
    return dmc.Box(
        [
            # Plain text, as the PB card's and the latest-run card's first
            # lines are, and not a heading: the three are one kind of thing on
            # screen.
            html.Div(SCENARIO_STATS_LABEL, className="scenario-stats-heading"),
            html.Div(
                dmc.Text(
                    [
                        dmc.Text("Category: ", fw=700, span=True),
                        dmc.Text(id=ids.category, span=True),
                    ],
                    size="sm",
                ),
                id=ids.category_row,
                hidden=True,
            ),
            html.Div(
                dmc.Text(
                    [
                        dmc.Text(
                            "Number of runs: ",
                            fw=700,
                            span=True,
                        ),
                        dmc.Text(
                            id=ids.num_runs,
                            span=True,
                        ),
                    ],
                    size="sm",
                ),
                id=ids.num_runs_row,
            ),
            html.Div(
                NO_SCENARIO_TEXT,
                className=EMPTY_TITLE_CLASS,
                hidden=True,
                id=ids.no_scenario,
            ),
        ],
        className="scenario-stats-card",
    )


def register_scenario_stats(ids: ScenarioStatsIds) -> None:
    """Register the card's callbacks for one page's ids.

    Call once per page, at import, with the ids its layout is built from.
    """
    callback(
        Output(ids.category, "children"),
        Output(ids.category_row, "hidden"),
        # On a visit without query parameters the selection callback writes
        # neither dropdown. An independent Input keeps Dash from pruning
        # this initial call, so a remembered benchmark still gets its row.
        Input(ids.run_events, "data"),
        Input(ids.scenario_dropdown, "value"),
        Input(ids.playlist_filter, "value"),
    )(get_scenario_category)
    callback(
        Output(ids.num_runs, "children"),
        Output(ids.num_runs_row, "hidden"),
        Output(ids.no_scenario, "hidden"),
        Input(ids.run_events, "data"),
        Input(ids.scenario_dropdown, "value"),
    )(get_scenario_num_runs)
