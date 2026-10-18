"""Build the Scenario Stats card and wire its callbacks to a page's ids.

The card holds Category, Last played and Number of runs under its heading.
A page that hosts it fills in a ``ScenarioStatsIds``, puts
``scenario_stats_stores`` and ``scenario_stats_panel`` in its layout, and
calls ``register_scenario_stats`` with the ids once, at import. The callbacks
are plain functions here and are registered once per page.
"""

from typing import NamedTuple

import dash_mantine_components as dmc
from dash import (
    Input,
    Output,
    callback,
    clientside_callback,
    dcc,
    html,
)

from source.components.chart_options import TOOLTIP_EVENTS
from source.kovaaks.data_service import (
    get_playlist_by_code,
    get_scenario_stats,
    is_benchmark_playlist,
    is_scenario_in_database,
)
from source.kovaaks.playlist_scenarios_service import playlist_scenario_groups
from source.utilities.utilities import format_absolute_timestamp


class ScenarioStatsIds(NamedTuple):
    """The component ids one page gives its Scenario Stats card.

    Two pages need two sets: the callbacks are registered once per set, and
    Dash allows one callback per output.

    ``scenario_stats_stores`` builds the stores, whose ids here end in
    ``_ts`` or ``_empty_value``, and ``scenario_stats_panel`` builds the
    rest of the card. ``run_events``, ``scenario_dropdown``, ``playlist_filter`` and
    ``relative_time_interval`` are the page's own. The card reads them and
    builds none of them:

    - ``run_events`` is the store the page's run delivery writes when new
      runs land on the scenario it shows.
    - ``relative_time_interval`` is a ``dcc.Interval`` that ticks every 30
      seconds, so the Last played text stays current on a page left open.
    """

    category_row: str
    category: str
    last_played: str
    last_played_tooltip: str
    num_runs: str
    last_played_ts: str
    last_played_empty_value: str
    run_events: str
    scenario_dropdown: str
    playlist_filter: str
    relative_time_interval: str


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


def get_scenario_num_runs(
    _, selected_scenario
) -> tuple[int, float | None, str, str, str | None, int | None, bool]:
    """Fill in the run count and what the Last played text is built from.

    The relative "Last played" string is rendered client-side from the raw epoch
    written to the ``last_played_ts`` store. This callback owns the empty-state
    value and tooltip affordance, while a clientside callback owns the visible
    ``children``. The first argument is the page's run-events store, which
    triggers the call and is not read.
    """
    if not selected_scenario:
        return 0, None, "—", "", None, None, True

    if not is_scenario_in_database(selected_scenario):
        return 0, None, "Never", "", None, None, True

    scenario_stats = get_scenario_stats(selected_scenario)

    return (
        scenario_stats.number_of_runs,
        scenario_stats.date_last_played.timestamp(),
        "Never",  # Defensive fallback; unused for a valid timestamp.
        format_absolute_timestamp(scenario_stats.date_last_played),
        "cell-tooltip-affordance",
        0,
        False,
    )


# The visible "Last played" text is recomputed in the browser on each store
# change and on every 30s interval tick, so the relative string stays current
# without a reload. It uses the full window.* path (dagfuncs is not a bare
# global here) and the server-selected empty-state sentinel.
_LAST_PLAYED_SCRIPT = """
    (seconds, emptyValue, _nIntervals) => {
        return window.dashAgGridFunctions.relativeTime(seconds, emptyValue);
    }
    """


def scenario_stats_stores(ids: ScenarioStatsIds) -> list[dcc.Store]:
    """Build the stores the card's callbacks pass their values through."""
    return [
        # raw epoch for the relative "Last played" text
        dcc.Store(id=ids.last_played_ts),
        dcc.Store(id=ids.last_played_empty_value, data=""),
    ]


def scenario_stats_panel(ids: ScenarioStatsIds) -> dmc.Box:
    """Build the Scenario Stats card: its heading and the rows under it."""
    return dmc.Box(
        [
            # An h2 for the page's outline, drawn as the card's quiet first
            # line, as the latest-run card's is.
            dmc.Title(
                "Scenario Stats",
                className="scenario-stats-heading",
                order=2,
            ),
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
            dmc.Group(
                [
                    dmc.Text(
                        "Last played:",
                        fw=700,
                        span=True,
                        size="sm",
                    ),
                    dmc.Tooltip(
                        dmc.Text(
                            "",
                            id=ids.last_played,
                            span=True,
                            size="sm",
                        ),
                        disabled=True,
                        events=TOOLTIP_EVENTS,
                        id=ids.last_played_tooltip,
                        label="",
                    ),
                ],
                gap="0.25em",
            ),
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
        Output(ids.last_played_ts, "data"),
        Output(ids.last_played_empty_value, "data"),
        Output(ids.last_played_tooltip, "label"),
        Output(ids.last_played, "className"),
        Output(ids.last_played, "tabIndex"),
        Output(ids.last_played_tooltip, "disabled"),
        Input(ids.run_events, "data"),
        Input(ids.scenario_dropdown, "value"),
    )(get_scenario_num_runs)
    clientside_callback(
        _LAST_PLAYED_SCRIPT,
        Output(ids.last_played, "children"),
        Input(ids.last_played_ts, "data"),
        Input(ids.last_played_empty_value, "data"),
        Input(ids.relative_time_interval, "n_intervals"),
    )
