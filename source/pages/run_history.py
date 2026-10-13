"""Build the Run History page and its callbacks.

The page shows one scenario's runs: a chart of every run in a range, with
the Chart options panel beside it. It is built beside the Scenario
Performance page and replaces it when it goes public. Until then it is
served at its own address with no navbar entry and nothing linking to it.

It never imports the Scenario Performance page's module. Dash Pages loads
each page file as ``pages.<name>``, so a second import path would make a
second copy of that module with its own state. What both pages need lives
under ``source/components/``.
"""

import logging
from datetime import datetime
from typing import Any

import dash
import dash_mantine_components as dmc
from dash import (
    Input,
    NoUpdate,
    Output,
    Patch,
    State,
    callback,
    clientside_callback,
    ctx,
    dcc,
    no_update,
)

from source.app_shell import RUN_EVENTS_BATCH_STORE_ID
from source.components.chart_options import (
    SETTINGS_HELP_TEXT,
    ChartOptionsIds,
    chart_options_panel,
    chart_options_toggle,
    register_chart_options,
    settings_help_label,
)
from source.components.queued_notices import (
    register_run_import_failure_flush,
    register_startup_playlist_warning_flush,
)
from source.components.run_delivery import (
    run_events_were_triggered,
    summarize_run_events,
)
from source.components.run_history_chart import (
    CHART_MODE_DEFAULT,
    CHART_MODE_OPTIONS,
    DAY_RANGE_DEFAULT,
    DAY_RANGE_OPTIONS,
    NO_LOCAL_RUNS_PLOT_MESSAGE,
    NO_LOCAL_RUNS_PLOT_TITLE,
    NO_SCENARIO_PLOT_MESSAGE,
    NO_SCENARIO_PLOT_TITLE,
    RUN_RANGE_DEFAULT,
    RUN_RANGE_OPTIONS,
    SCORE_VS_RUN,
    build_run_history_figure,
)
from source.components.run_verdict_toast import build_run_event_notification
from source.components.scenario_selection import (
    SELECT_HIGHLIGHT_ON_OPEN_CLASS,
    ScenarioSelectionIds,
    deep_link_selection,
    initial_scenario_options,
    playlist_filter_options,
    register_scenario_selection_clearing_filter,
)
from source.components.scenario_stats import (
    ScenarioStatsIds,
    register_scenario_stats,
    scenario_stats_panel,
    scenario_stats_stores,
)
from source.components.score_threshold import (
    normalize_score_threshold_percentage,
    score_threshold_line,
)
from source.components.setup_surfaces import setup_card_children, stats_dir_hint
from source.config.config_service import get_config
from source.kovaaks.data_service import get_high_score, is_scenario_in_database
from source.pages.page_title import page_title
from source.pages.playlist_selector import (
    PLAYLIST_SELECTOR_PRESET,
    PLAYLIST_SELECTOR_SIZING,
)
from source.plot.plot_service import (
    add_high_score_overlay,
    add_score_threshold_overlay,
    generate_empty_plot,
    generate_placeholder_plot,
)
from source.utilities.notifications import (
    TOAST_CHANNEL_REGISTRY_STORE_ID,
    channel_toast,
)

logger = logging.getLogger(__name__)

# Every id below is this page's alone, its stores and intervals included. A
# page that holds one output of a callback has to hold every input of it, so
# two pages cannot share part of a callback, and the Scenario Performance
# page's callbacks are registered for its own ids. The browser also stores
# each remembered control's value under its id, so changing one of these
# resets that value for every user.
RUN_EVENTS_STORE_ID = "run-history-run-events"
POLLING_INTERVAL_ID = "run-history-polling-interval"
RELATIVE_TIME_INTERVAL_ID = "run-history-relative-time-interval"
STARTUP_PLAYLIST_WARNING_INTERVAL_ID = "run-history-startup-playlist-warning-interval"
# The date the chart's ranges of days were last counted back from, as ISO
# text. It is written only when the date moves on, and the chart takes it as
# an input, which is what redraws a chart that is left open past midnight.
TODAY_STORE_ID = "run-history-today"
FOLLOW_SWITCH_ID = "run-history-follow-switch"
CHART_MODE_ID = "run-history-chart-mode"
RUN_RANGE_ID = "run-history-run-range"
DAY_RANGE_ID = "run-history-day-range"
# The two range selects' wrappers. A callback writes each one's class, which
# is how one of the two is hidden.
RUN_RANGE_FIELD_ID = "run-history-run-range-field"
DAY_RANGE_FIELD_ID = "run-history-day-range-field"
# The setup card's container and the stats-folder hint. No callback writes
# either on this page: its card has no Skip.
SETUP_CARD_ID = "run-history-setup-card"
STATS_DIR_HINT_ID = "run-history-stats-dir-hint"

SCENARIO_SELECTION_IDS = ScenarioSelectionIds(
    playlist_filter="run-history-playlist-filter",
    scenario_dropdown="run-history-scenario",
    deep_link="run-history-deep-link",
    playlist_table_link="run-history-playlist-table-link",
)
CHART_OPTIONS_IDS = ChartOptionsIds(
    panel="run-history-chart-options-panel",
    toggle="run-history-chart-options-toggle",
    rank_overlay="run-history-rank-overlay-switch",
    show_all_ranks="run-history-show-all-ranks-switch",
    high_score_overlay="run-history-high-score-overlay-switch",
    point_size="run-history-point-size",
    point_size_label="run-history-point-size-label",
    point_color="run-history-point-color",
    point_color_default="run-history-point-color-default",
    score_threshold_overlay="run-history-score-threshold-overlay-switch",
    score_threshold_percentage="run-history-score-threshold-percentage",
    score_threshold_notification="run-history-score-threshold-notification-switch",
    run_notification="run-history-run-notification-switch",
    graph="run-history-graph",
    cached_plot="run-history-cached-plot",
)
SCENARIO_STATS_IDS = ScenarioStatsIds(
    last_played="run-history-last-played",
    last_played_tooltip="run-history-last-played-tooltip",
    num_runs="run-history-num-runs",
    rank="run-history-position",
    rank_updated_tooltip="run-history-position-updated-tooltip",
    rank_refresh_button="run-history-position-refresh-button",
    last_played_ts="run-history-last-played-ts",
    last_played_empty_value="run-history-last-played-empty-value",
    rank_updated_ts="run-history-position-updated-ts",
    run_events=RUN_EVENTS_STORE_ID,
    scenario_dropdown=SCENARIO_SELECTION_IDS.scenario_dropdown,
    polling_interval=POLLING_INTERVAL_ID,
    relative_time_interval=RELATIVE_TIME_INTERVAL_ID,
)

# The Top N this page's run toast places a run against. The page plots every
# run, so it has no Top N scores control, and the toast keeps today's rule at
# the old control's default until the plain run toast replaces it.
RUN_TOAST_TOP_N_SCORES = 5

# The class the resize script and the zoom fit script find a graph by
# (``assets/homeGraphResize.js``, ``assets/homeGraphZoomFit.js``). Both pages'
# graphs carry it, so both scripts serve both.
GRAPH_CLASS = "home-graph"
RANGE_FIELD_CLASS = "run-history-range-field"
RANGE_FIELD_HIDDEN_CLASS = f"{RANGE_FIELD_CLASS} run-history-range-field-hidden"
# How wide each dropdown's column is in the top row: the shared sizing, which
# joins a line at 200px and stops at 400px, growing twice as fast as the
# latest-run card's slot beside it. A row with room to spare gives it to the
# scenario's name and the Follow switch's label before the card.
DROPDOWN_FIELD_SIZING = {**PLAYLIST_SELECTOR_SIZING, "flex": "2 1 200px"}

_RUN_EVENTS_PROP = f"{RUN_EVENTS_STORE_ID}.data"

dash.register_page(
    __name__,
    path="/run-history",
    name="Run History",
    title=page_title("Run History"),
)


def _empty_plot_json(title: str, message: str) -> str:
    """Serialize an empty-state graph for the cached plot store."""
    return generate_empty_plot(title, message).to_json()


@callback(
    Output(RUN_EVENTS_STORE_ID, "data"),
    Input(RUN_EVENTS_BATCH_STORE_ID, "data"),
    # State, not Input: a Store replays its last value, and a control flip
    # must not forward again a batch already processed. The same reason keeps
    # prevent_initial_call on: coming back to this page mounts it against the
    # batch the shell's store still holds, and a mount must not replay it.
    State(FOLLOW_SWITCH_ID, "checked"),
    State(SCENARIO_SELECTION_IDS.scenario_dropdown, "value"),
    prevent_initial_call=True,
)
def forward_run_events(batch, follow_newly_played, selected_scenario):
    """Forward the shell's run-event batch as one summary for this page.

    The summary names the scenario the page should now show: the one last
    played while Follow is on, and the selected one otherwise. This callback
    writes neither dropdown. The selection callback reads the summary and
    moves them, so the chart, which waits on both, is rebuilt once per batch.
    """
    if not batch:
        return no_update
    _target_scenario, run_events = summarize_run_events(
        batch,
        selected_scenario,
        follow_newly_played,
    )
    return no_update if run_events is None else run_events


register_run_import_failure_flush(POLLING_INTERVAL_ID)
register_scenario_stats(SCENARIO_STATS_IDS)


def _today_text() -> str:
    """Return the app's own date as the ISO text the date store holds."""
    return datetime.now().date().isoformat()


@callback(
    Output(TODAY_STORE_ID, "data"),
    Input(RELATIVE_TIME_INTERVAL_ID, "n_intervals"),
    State(TODAY_STORE_ID, "data"),
    # The layout draws the store with the date already in it. A call on load
    # would write nothing, and the first chart would be held for its answer.
    prevent_initial_call=True,
)
def advance_today(_n_intervals, held_date):
    """Write the app's date to the page once it is no longer the one held.

    A range of days counts back from today, so a point leaves the chart at
    midnight, and nothing a user does at midnight redraws a chart that is
    left open. The chart takes this store as an input, so this write is what
    redraws it, within one tick of the date moving on. A tick inside the same
    date writes nothing, so a tick alone never rebuilds the chart.

    The date is the server's, read as the chart reads it. A date taken from
    the browser's clock could move on when the chart's own had not.
    """
    today = _today_text()
    return no_update if today == held_date else today


@callback(
    Output(CHART_OPTIONS_IDS.cached_plot, "data"),
    # ``allow_duplicate``: the Scenario Performance page's chart callback
    # writes the same three shell-hosted props, and Dash allows one plain
    # writer per output.
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Output("notification-container", "hideNotifications", allow_duplicate=True),
    Output(TOAST_CHANNEL_REGISTRY_STORE_ID, "data", allow_duplicate=True),
    Input(RUN_EVENTS_STORE_ID, "data"),
    Input(SCENARIO_SELECTION_IDS.scenario_dropdown, "value"),
    # An Input, so the rank lines follow the filter at once. A playlist's
    # ladder is drawn from the filter's value, and a chart that kept the old
    # ladder after the filter changed would read as a bug.
    Input(SCENARIO_SELECTION_IDS.playlist_filter, "value"),
    Input(CHART_MODE_ID, "value"),
    Input(RUN_RANGE_ID, "value"),
    Input(DAY_RANGE_ID, "value"),
    # Read for nothing but its change. A range of days counts back from
    # today, and on a page that is left open no other input changes at
    # midnight, so without this the chart would keep the day that left.
    Input(TODAY_STORE_ID, "data"),
    Input(CHART_OPTIONS_IDS.rank_overlay, "checked"),
    Input(CHART_OPTIONS_IDS.show_all_ranks, "checked"),
    Input(CHART_OPTIONS_IDS.high_score_overlay, "checked"),
    Input(CHART_OPTIONS_IDS.score_threshold_overlay, "checked"),
    Input(CHART_OPTIONS_IDS.score_threshold_percentage, "value"),
    Input(CHART_OPTIONS_IDS.score_threshold_notification, "checked"),
    # State, not Input: this preference only decides whether a run event that
    # already triggered the callback gets to toast. Flipping it must not
    # rebuild the plot or reread the scenario's runs.
    State(CHART_OPTIONS_IDS.run_notification, "checked"),
    State(TOAST_CHANNEL_REGISTRY_STORE_ID, "data"),
    # Not ``True``: this callback draws the first chart, so the page load
    # must still run it, but Dash refuses an ``allow_duplicate`` output
    # without one of the ``prevent_initial_call`` forms.
    prevent_initial_call="initial_duplicate",
)
def generate_graph(  # noqa: PLR0913
    run_events,
    selected_scenario,
    selected_playlist,
    chart_mode,
    run_range,
    day_range,
    _held_date,
    rank_overlay_switch,
    show_all_ranks_switch,
    high_score_overlay_switch,
    score_threshold_overlay_switch,
    score_threshold_percentage,
    score_threshold_notification_switch,
    run_notification_switch,
    toast_channels,
):
    """Build the chart, and the toast a run that just landed earned.

    Returns the figure serialized to JSON, the toasts to show, the toast
    instances to hide, and the channel registry patch that records the swap.
    ``run_events`` is the summary of newly landed runs when this call has
    one. A toast is built only on a call that summary triggered, so neither a
    control change nor the date moving on repeats the last run's toast.
    """
    if not selected_scenario:
        return (
            _empty_plot_json(NO_SCENARIO_PLOT_TITLE, NO_SCENARIO_PLOT_MESSAGE),
            no_update,
            no_update,
            no_update,
        )

    if not is_scenario_in_database(selected_scenario):
        logger.warning('No scenario data found for: "%s"', selected_scenario)
        return (
            _empty_plot_json(NO_LOCAL_RUNS_PLOT_TITLE, NO_LOCAL_RUNS_PLOT_MESSAGE),
            no_update,
            no_update,
            no_update,
        )

    plot, supports_overlays = build_run_history_figure(
        chart_mode,
        selected_scenario,
        run_range,
        day_range,
        rank_overlay_switch,
        show_all_ranks_switch,
        selected_playlist,
        datetime.now().date(),
    )

    notifications: list[dict[str, Any]] | NoUpdate = no_update
    hide_notifications: list[str] | NoUpdate = no_update
    next_toast_channels: Patch | NoUpdate = no_update
    if supports_overlays:
        high_score = get_high_score(selected_scenario)
        if high_score_overlay_switch:
            plot = add_high_score_overlay(plot, high_score)

        score_threshold_goal_percentage = normalize_score_threshold_percentage(
            score_threshold_percentage
        )
        if score_threshold_overlay_switch and score_threshold_goal_percentage:
            score_threshold = score_threshold_line(
                selected_scenario,
                high_score,
                score_threshold_goal_percentage,
            )
            plot = add_score_threshold_overlay(plot, score_threshold)

        notifications = []
        hide_notifications = []
        if run_events_were_triggered(ctx.triggered, _RUN_EVENTS_PROP):
            run_verdict = build_run_event_notification(
                run_events,
                selected_scenario,
                RUN_TOAST_TOP_N_SCORES,
                score_threshold_percentage,
                score_threshold_notification_switch,
                run_notification_switch,
            )
            if run_verdict is not None:
                notifications, hide_notifications, next_toast_channels = channel_toast(
                    run_verdict, toast_channels
                )
    return plot.to_json(), notifications, hide_notifications, next_toast_channels


# Which range select shows: the one in runs under Score vs Run, and the one
# in days under the other two modes. Held in a constant because Dash names an
# inline script by a hash of its source, so the text must not move with the
# indentation of the code around it.
_SHOW_RANGE_FOR_MODE_SCRIPT = f"""
    (mode) => {{
        const inRuns = mode === "{SCORE_VS_RUN}";
        return [
            inRuns ? "{RANGE_FIELD_CLASS}" : "{RANGE_FIELD_HIDDEN_CLASS}",
            inRuns ? "{RANGE_FIELD_HIDDEN_CLASS}" : "{RANGE_FIELD_CLASS}",
        ];
    }}
    """

clientside_callback(
    _SHOW_RANGE_FOR_MODE_SCRIPT,
    Output(RUN_RANGE_FIELD_ID, "className"),
    Output(DAY_RANGE_FIELD_ID, "className"),
    Input(CHART_MODE_ID, "value"),
)

register_chart_options(CHART_OPTIONS_IDS)
register_startup_playlist_warning_flush(STARTUP_PLAYLIST_WARNING_INTERVAL_ID)
register_scenario_selection_clearing_filter(
    SCENARIO_SELECTION_IDS,
    run_events=RUN_EVENTS_STORE_ID,
    follow_switch=FOLLOW_SWITCH_ID,
)


def _range_select(
    select_id: str,
    options: list[dict[str, str]],
    default: str,
) -> dmc.Select:
    """Build one of the chart's two range selects.

    Its options carry their unit, so it needs no visible label and takes its
    name from ``aria-label``.
    """
    return dmc.Select(
        allowDeselect=False,
        checkIconPosition="right",
        data=options,
        id=select_id,
        persistence=True,
        # The same on every visit. The browser stores the choice against the
        # value the layout was drawn with, and discards it when a later visit
        # draws another.
        value=default,
        w="10.5rem",
        **{"aria-label": "Range"},
    )


def _top_row(playlist_code: str | None) -> dmc.Box:
    """Build the row above the chart: both dropdowns, the stats, the card's slot."""
    return dmc.Box(
        className="run-history-top-row",
        children=[
            dmc.Box(
                [
                    dmc.Select(
                        **PLAYLIST_SELECTOR_PRESET,
                        allowDeselect=False,
                        autoSelectOnBlur=True,
                        classNames={"input": SELECT_HIGHLIGHT_ON_OPEN_CLASS},
                        clearable=True,
                        data=playlist_filter_options(playlist_code),
                        id=SCENARIO_SELECTION_IDS.playlist_filter,
                        label="Playlist filter",
                        persistence=True,
                        # Never the query parameter, and never omitted. Dash
                        # pins a remembered value to the layout value it was
                        # set against and discards it when a later visit
                        # draws a different one, so a default that varies by
                        # visit would retire the memory. The selection
                        # callback applies the query parameter instead.
                        # Explicit ``None`` because an omitted prop is
                        # ``undefined``, which does not match what a browser
                        # already stored.
                        value=None,
                    ),
                    dmc.Box(id=SCENARIO_SELECTION_IDS.playlist_table_link),
                ],
                className="run-history-playlist-field",
                # The column, not the Select inside it, is the flex item the
                # row breaks lines on.
                **DROPDOWN_FIELD_SIZING,
            ),
            dmc.Stack(
                [
                    dmc.Select(
                        allowDeselect=False,
                        autoSelectOnBlur=True,
                        checkIconPosition="right",
                        classNames={"input": SELECT_HIGHLIGHT_ON_OPEN_CLASS},
                        data=initial_scenario_options(playlist_code),
                        id=SCENARIO_SELECTION_IDS.scenario_dropdown,
                        label="Selected scenario",
                        maxDropdownHeight="75vh",
                        persistence=True,
                        placeholder="Select a scenario",
                        scrollAreaProps={"type": "auto"},
                        searchable=True,
                        # Constant on every visit, for the reason the playlist
                        # filter's default gives.
                        value=None,
                    ),
                    # Selection behavior, not chart presentation: it decides
                    # what the selector does when a new run lands, so it sits
                    # under the selector and not in the Chart options panel.
                    dmc.Switch(
                        id=FOLLOW_SWITCH_ID,
                        labelPosition="right",
                        label=settings_help_label(
                            "Follow newly played scenario",
                            SETTINGS_HELP_TEXT[
                                "automatically-change-scenario-run-history"
                            ],
                        ),
                        checked=True,
                        persistence=True,
                    ),
                ],
                className="run-history-scenario-field",
                gap="xs",
                # Sized as the playlist filter beside it is.
                **DROPDOWN_FIELD_SIZING,
            ),
            scenario_stats_panel(SCENARIO_STATS_IDS),
            # Reserved for the latest-run card, at the size planned for it,
            # so the chart under this row is measured in the layout it will
            # ship in.
            dmc.Box(className="run-history-card-slot"),
        ],
    )


def _chart_column() -> dmc.Box:
    """Build the chart's column: its header, then the graph beside its panel."""
    return dmc.Box(
        className="run-history-chart-column",
        children=[
            dmc.Box(
                className="run-history-chart-header",
                children=[
                    dmc.SegmentedControl(
                        data=CHART_MODE_OPTIONS,
                        id=CHART_MODE_ID,
                        persistence=True,
                        radius="sm",
                        size="sm",
                        value=CHART_MODE_DEFAULT,
                        **{"aria-label": "Chart mode"},
                    ),
                    # Both range selects are always in the layout, and the one
                    # the mode does not use is hidden by a class. Each is
                    # remembered on its own, and a control that is taken out
                    # of the layout stops being an input of the chart
                    # callback. They are two controls and not one because a
                    # remembered control's default cannot change with the
                    # mode.
                    dmc.Box(
                        _range_select(
                            RUN_RANGE_ID, RUN_RANGE_OPTIONS, RUN_RANGE_DEFAULT
                        ),
                        className=RANGE_FIELD_CLASS,
                        id=RUN_RANGE_FIELD_ID,
                    ),
                    dmc.Box(
                        _range_select(
                            DAY_RANGE_ID, DAY_RANGE_OPTIONS, DAY_RANGE_DEFAULT
                        ),
                        className=RANGE_FIELD_HIDDEN_CLASS,
                        id=DAY_RANGE_FIELD_ID,
                    ),
                    chart_options_toggle(CHART_OPTIONS_IDS),
                ],
            ),
            # The wrapper is the box the panel's stacking threshold measures:
            # a container query cannot match on the element that declares the
            # container, so the row carrying the layout sits inside it.
            dmc.Box(
                className="run-history-chart-area",
                children=dmc.Box(
                    className="home-chart-row",
                    children=[
                        dcc.Graph(
                            id=CHART_OPTIONS_IDS.graph,
                            figure=generate_placeholder_plot().to_plotly_json(),
                            className=GRAPH_CLASS,
                            # Redraw the plot whenever its container resizes,
                            # not just on window resize.
                            responsive=True,
                        ),
                        chart_options_panel(
                            CHART_OPTIONS_IDS,
                            score_threshold_percentage_help=SETTINGS_HELP_TEXT[
                                "score-threshold-percentage-run-history"
                            ],
                        ),
                    ],
                ),
            ),
        ],
    )


def layout(
    scenario: str | None = None,
    playlist_code: str | None = None,
    **_kwargs,
):
    """Build the Run History page.

    ``scenario`` and ``playlist_code`` are the two query parameters the page
    reads. ``**_kwargs`` takes any other, which Dash would otherwise refuse:
    a link may carry one only to make its address differ from the last.
    """
    config = get_config()
    return dmc.Box(
        className="run-history-page",
        children=[
            dcc.Store(id=RUN_EVENTS_STORE_ID),
            dcc.Store(
                id=SCENARIO_SELECTION_IDS.deep_link,
                data=deep_link_selection(scenario, playlist_code),
            ),
            # Holds the unstyled figure, so a theme or point change restyles
            # it without rebuilding it.
            dcc.Store(
                id=CHART_OPTIONS_IDS.cached_plot,
                data=generate_placeholder_plot().to_json(),
            ),
            *scenario_stats_stores(SCENARIO_STATS_IDS),
            # The date the page is drawn on. Without it the first tick would
            # find no date held, write one, and rebuild a chart just drawn.
            dcc.Store(id=TODAY_STORE_ID, data=_today_text()),
            dcc.Interval(
                id=STARTUP_PLAYLIST_WARNING_INTERVAL_ID,
                interval=250,
                n_intervals=0,
                max_intervals=1,
            ),
            dcc.Interval(
                id=POLLING_INTERVAL_ID,
                interval=config.polling_interval,
                n_intervals=0,
            ),
            # A 30-second tick of its own for the relative "Last played"
            # text, so how often it is reworded never depends on how often
            # the page polls for data.
            dcc.Interval(
                id=RELATIVE_TIME_INTERVAL_ID,
                interval=30_000,
                n_intervals=0,
            ),
            *stats_dir_hint(STATS_DIR_HINT_ID),
            # With no runs to read, the page says why in place. The account
            # offer is left to the landing page: it explains nothing about an
            # empty chart.
            dmc.Box(
                id=SETUP_CARD_ID,
                children=setup_card_children(offer_account=False),
            ),
            _top_row(playlist_code),
            dmc.Box(
                className="run-history-columns",
                children=[
                    _chart_column(),
                    # Reserved for the run list, at the width planned for it.
                    dmc.Box(className="run-history-list-column"),
                ],
            ),
        ],
    )
