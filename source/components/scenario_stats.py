"""Build the Scenario Stats card and wire its callbacks to a page's ids.

The card leads with the typical score, followed by Category and Total runs,
or says no scenario is selected. A page that hosts it fills in a ``ScenarioStatsIds``,
puts ``scenario_stats_panel`` in its layout, and calls
``register_scenario_stats`` with the ids once, at import. The callbacks are
plain functions here and are registered once per page.
"""

import json
from datetime import datetime
from typing import Any, NamedTuple

import dash_mantine_components as dmc
from dash import Input, Output, State, callback, html, no_update
from plotly.io.json import to_json_plotly

from source.components.chart_options import (
    SETTINGS_HELP_TOOLTIP_WIDTH,
    TOOLTIP_EVENTS,
)
from source.components.control_name import control_name
from source.components.latest_run_card import EMPTY_TITLE_CLASS, SCORE_CLASS, TIME_CLASS
from source.components.local_icon import local_icon
from source.components.run_history_list import NO_SCENARIO_TEXT
from source.kovaaks.data_service import (
    get_all_runs,
    get_playlist_by_code,
    get_scenario_stats,
    is_benchmark_playlist,
    is_scenario_in_database,
)
from source.kovaaks.play_sessions import split_into_play_sessions
from source.kovaaks.playlist_scenarios_service import playlist_scenario_groups
from source.kovaaks.typical_score import (
    TOO_FEW_RUNS_TEXT,
    TypicalScore,
    below_minimum_text,
    build_typical_scores,
    format_typical_score,
    typical_score_hover,
    typical_score_recency,
)

SCENARIO_STATS_LABEL = "Typical score"
NO_RUNS_TEXT = "No runs yet"
TOOLTIP_TARGET_CLASS = "scenario-stats-tooltip-target"
WORD_END_CLASS = "scenario-stats-word-end"
DIMMED_CLASS = "scenario-stats-dimmed"


def _help() -> dmc.Tooltip:
    """Explain the figure beside the card's first line."""
    paragraphs: list[Any] = [
        "Your typical score is the median of your last 20 runs of this scenario, "
        "or of all your runs if you have fewer. Runs count regardless of age.",
        [
            "On the chart, the darker band shows the middle 50% of those scores, "
            "and the lighter band the middle 80%. Narrower bands mean more "
            "consistent scores. Turn the line and bands on or off in ",
            control_name("Chart options"),
            ".",
        ],
        "A faded line, or a dimmed number on this card, means fewer than 10 of "
        "the runs behind your typical score are from the last 30 days, so it "
        "may be out of date.",
        "The card shows how recent it is today, and the chart how recent it "
        "was at each run.",
    ]
    return dmc.Tooltip(
        dmc.ActionIcon(
            local_icon("material-symbols:info-outline", width=12),
            className="settings-help-icon",
            color="gray",
            radius="xl",
            size=14,
            variant="subtle",
            **{"aria-label": "About the typical score"},
        ),
        boxWrapperProps={"className": TOOLTIP_TARGET_CLASS},
        label=html.Div([html.P(text) for text in paragraphs]),
        classNames={"tooltip": "scenario-stats-help"},
        events=TOOLTIP_EVENTS,
        multiline=True,
        withArrow=True,
        w=SETTINGS_HELP_TOOLTIP_WIDTH,
    )


def _value_hover(value: TypicalScore, total: int, now: datetime) -> html.Div:
    """Describe the supporting runs, their recency and both bands."""
    hover = typical_score_hover(value, total, now)
    return html.Div(
        [
            html.P(hover.opening),
            *(html.Div([control_name(label), text]) for label, text in hover.lines),
        ],
        className="scenario-stats-value-help",
    )


def get_scenario_typical_score(
    _,
    selected_scenario: str | None,
    _tick,
    current_lead=None,
    current_readout=None,
) -> tuple[Any, Any, bool]:
    """Build the lead from one run snapshot, keeping unchanged tooltips mounted.

    Return the lead's children, the recency readout and whether to hide the
    lead. Unchanged children or readout are ``no_update``; visibility is
    always written. The run-event payload and interval count trigger the
    call and are not read.
    """
    lead: Any = []
    readout: Any = ""
    if selected_scenario:
        # A landing run must not appear in the scenario's window without its
        # session, so both are taken from this one copy of the whole store.
        snapshot = get_all_runs()
        runs = [run for run in snapshot if run.scenario == selected_scenario]
        now = datetime.now()
        if not runs:
            lead = html.Div(NO_RUNS_TEXT, className=EMPTY_TITLE_CLASS)
        else:
            value = build_typical_scores(runs, split_into_play_sessions(snapshot))[-1]
            if value.known:
                recent = typical_score_recency(value, now)
                if recent.run_count < value.run_count:
                    readout = f" · {recent.run_count} of {value.run_count} recent runs"
                assert value.median is not None
                text = format_typical_score(value.median, value.runs)
                css = f"{SCORE_CLASS} {TIME_CLASS}"
                if not recent.recent:
                    css += f" {DIMMED_CLASS}"
                label: Any = _value_hover(value, len(runs), now)
            else:
                text = TOO_FEW_RUNS_TEXT
                css = f"{EMPTY_TITLE_CLASS} {TIME_CLASS}"
                label = below_minimum_text(value)
            lead = dmc.Tooltip(
                html.Span(
                    [text, html.Span(" ", className=WORD_END_CLASS)],
                    className=css,
                    tabIndex=0,
                ),
                boxWrapperProps={"className": TOOLTIP_TARGET_CLASS},
                label=label,
                events=TOOLTIP_EVENTS,
                multiline=True,
                withArrow=True,
                w=360,
            )
    # Dash sends State as JSON. Comparing the rendered tree avoids replacing
    # a tooltip on a tick that changes none of its copy, including at mount.
    if json.loads(to_json_plotly(lead)) == current_lead:
        lead = no_update
    if readout == current_readout:
        readout = no_update
    return lead, readout, not bool(selected_scenario)


class ScenarioStatsIds(NamedTuple):
    """The component ids one page gives its Scenario Stats card.

    Two pages need two sets: the callbacks are registered once per set, and
    Dash allows one callback per output.

    ``scenario_stats_panel`` builds the card from ``category_row``,
    ``category``, ``num_runs_row``, ``num_runs``, ``no_scenario``, ``lead``
    and ``recent_readout``.
    ``run_events``, ``scenario_dropdown`` and ``playlist_filter`` are the
    page's own, as is its ``relative_time_interval``. The card reads them and
    builds none of them: ``run_events``
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
    lead: str
    recent_readout: str
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


def scenario_stats_panel(ids: ScenarioStatsIds) -> dmc.Paper:
    """Build the Scenario Stats card: its first line and the lines under it."""
    return dmc.Paper(
        [
            # Plain text, as the PB card's and the latest-run card's first
            # lines are, and not a heading: the three are one kind of thing on
            # screen.
            html.Div(
                [
                    html.Span(
                        [SCENARIO_STATS_LABEL, html.Span(" ", className=WORD_END_CLASS)]
                    ),
                    _help(),
                    html.Span(
                        id=ids.recent_readout, className="scenario-stats-recency"
                    ),
                ],
                className="scenario-stats-heading",
            ),
            html.Div(id=ids.lead),
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
                            "Total runs: ",
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
        withBorder=True,
        radius="sm",
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
    callback(
        Output(ids.lead, "children"),
        Output(ids.recent_readout, "children"),
        Output(ids.lead, "hidden"),
        Input(ids.run_events, "data"),
        Input(ids.scenario_dropdown, "value"),
        Input(ids.relative_time_interval, "n_intervals"),
        State(ids.lead, "children"),
        State(ids.recent_readout, "children"),
    )(get_scenario_typical_score)
