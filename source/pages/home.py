"""Build the dashboard home page and its interactive callbacks."""

import logging
from datetime import datetime
from typing import Any

import dash
import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import (
    Input,
    NoUpdate,
    Output,
    Patch,
    State,
    callback,
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
from source.components.local_icon import local_icon
from source.components.queued_notices import (
    register_run_import_failure_flush,
    register_startup_playlist_warning_flush,
)
from source.components.run_delivery import summarize_run_events
from source.components.run_verdict_toast import build_run_event_notification
from source.components.scenario_selection import (
    ScenarioSelectionIds,
    deep_link_selection,
    initial_scenario_options,
    playlist_filter_options,
    register_scenario_selection,
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
from source.components.setup_surfaces import (
    SETUP_CARD_SKIP_ID,
    setup_card_children,
    stats_dir_hint,
)
from source.config.config_service import get_config
from source.config.settings_service import decline_identity
from source.kovaaks.data_service import (
    get_high_score,
    get_new_high_score_runs,
    get_rank_data_from_playlist_code,
    get_sensitivities_vs_runs_filtered,
    get_time_vs_runs,
    is_scenario_in_database,
)
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
    generate_sensitivity_plot,
    generate_time_plot,
)
from source.utilities.notifications import (
    TOAST_CHANNEL_REGISTRY_STORE_ID,
    channel_toast,
    toast,
)
from source.utilities.store_schema import UnsupportedSchemaError

logger = logging.getLogger(__name__)
# The controls grid measures these against its own width rather than the
# window's (``type="container"``). The AppShell navbar is fixed-position and
# 225px wide, so a media query splits the columns on space the content area
# does not have: with the navbar open the row crossed the threshold while
# still 225px short of fitting, then wrapped. The threshold values are the
# Mantine defaults, unchanged -- only the box they are measured against moves.
#
# Copied, not aliased: this is a Dash prop, and the theme dict is shared
# process-wide. Mantine also renders the container element only when a Grid
# passes both ``type="container"`` and ``breakpoints``, so dropping this
# constant would leave the ``@container`` queries with nothing to match and
# collapse every column to its ``base`` span.
HOME_GRID_BREAKPOINTS = dict(dmc.DEFAULT_THEME["breakpoints"])
PLAYLIST_FIELD_CLASS = "home-playlist-field"
# Marks a dropdown's input for ``assets/selectHighlightOnOpen.js``, which
# highlights the selected name when the list opens. dmc's
# ``clearSearchOnFocus`` buys the same click-and-type search by emptying the
# field instead, which leaves no name on screen to copy; setting it beside
# this class empties the field before the script can highlight anything.
SELECT_HIGHLIGHT_ON_OPEN_CLASS = "select-highlight-on-open"
# The ids this page gives its playlist filter and scenario dropdown. The
# browser stores each dropdown's value under its id, so changing one resets
# that selection for every user.
SCENARIO_SELECTION_IDS = ScenarioSelectionIds(
    playlist_filter="playlist-dropdown-selection",
    scenario_dropdown="scenario-dropdown-selection",
    deep_link="home-deep-link",
    playlist_table_link="playlist-table-link",
)

# The ids this page gives the Chart options block. The browser stores each
# remembered control's value under its id, so changing one resets that setting
# for every user.
CHART_OPTIONS_IDS = ChartOptionsIds(
    panel="chart-options-panel",
    toggle="chart-options-toggle",
    rank_overlay="rank-overlay-switch",
    show_all_ranks="show-all-ranks-switch",
    high_score_overlay="high-score-overlay-switch",
    point_size="point-size",
    point_size_label="point-size-label",
    point_color="point-color",
    point_color_default="point-color-default",
    score_threshold_overlay="score-threshold-overlay-switch",
    score_threshold_percentage="score-threshold-percentage",
    score_threshold_notification="score-threshold-notification-switch",
    run_notification="run-notification-switch",
    graph="graph-content",
    cached_plot="cached-plot",
)
# The ids this page gives the Scenario Stats block. The run-events store, the
# scenario dropdown and the two intervals are built by this page's layout,
# and the block only reads them.
SCENARIO_STATS_IDS = ScenarioStatsIds(
    last_played="scenario_datetime_last_played",
    last_played_tooltip="last-played-tooltip",
    num_runs="scenario_num_runs",
    rank="scenario_rank",
    rank_updated_tooltip="rank-updated-tooltip",
    rank_refresh_button="rank-refresh-button",
    last_played_ts="last-played-ts",
    last_played_empty_value="last-played-empty-value",
    rank_updated_ts="rank-updated-ts",
    run_events="run-events",
    scenario_dropdown=SCENARIO_SELECTION_IDS.scenario_dropdown,
    polling_interval="interval-component",
    relative_time_interval="relative-time-interval",
)
# Below this much room for the chart row, the inspector stacks above the chart
# instead of sitting beside it (assets/stylesheet.css measures the row's own
# width with an ``@container`` query, never the window's). ``md`` is where a
# 20rem rail stops leaving a chart worth reading.
CHART_OPTIONS_REFLOW_BREAKPOINT = HOME_GRID_BREAKPOINTS["md"]
# The first-run setup card. Its container is always in the layout so the Skip
# callback has an output to write to; the card itself is what comes and goes.
SETUP_CARD_ID = "setup-card"
# Shown when Skip cannot be recorded, either because the settings file belongs
# to a newer build or because the write itself failed. The card has to stay up
# (nothing was written), so the toast is what explains why the click appeared
# to do nothing. The two outcomes are mutually exclusive answers to the same
# click, so they share one channel: a second attempt replaces whatever the
# first one said instead of stacking a contradiction beside it.
SETUP_CARD_SKIP_PROBLEM_CHANNEL = "setup-card-skip-problem"
SETUP_CARD_SKIP_REFUSED_TITLE = "Skip wasn't saved"
SETUP_CARD_SKIP_REFUSED_MESSAGE = (
    "The settings file was written by a newer version of this app. Update the "
    "app to change settings."
)
SETUP_CARD_SKIP_FAILED_MESSAGE = (
    "Nothing was written. Try again. See data/logs/debug.log."
)
_RUN_EVENTS_PROP = "run-events.data"
_SELECT_SCENARIO_PLOT_TITLE = "No scenario selected"
_SELECT_SCENARIO_PLOT_MESSAGE = "Select a scenario to see your score history."
_INCOMPLETE_GRAPH_CONTROLS_TITLE = "Graph settings incomplete"
# The empty-state messages are plotly annotation text, which cannot hold a
# component, so a control name is bolded with ``<b>`` inside the string.
_INCOMPLETE_GRAPH_CONTROLS_MESSAGE = (
    "Set <b>Top N scores</b> and the oldest date to plot this scenario."
)
_NO_SCENARIO_DATA_PLOT_TITLE = "No local runs found"
_NO_SCENARIO_DATA_PLOT_MESSAGE = "Play this scenario once and the graph will fill in."
_NO_DATE_RANGE_DATA_PLOT_TITLE = "No runs in this date range"
_NO_DATE_RANGE_DATA_PLOT_MESSAGE = "Choose an older date or play more runs."
_UNSUPPORTED_GRAPH_OPTION_PLOT_TITLE = "Unsupported graph option"
_UNSUPPORTED_GRAPH_OPTION_PLOT_MESSAGE = (
    "Choose <b>Score vs Sensitivity</b> or <b>Score vs Time</b>."
)
dash.register_page(
    __name__,
    path="/",
    name="Scenario Performance",
    title=page_title("Scenario Performance"),
    redirect_from=["/home", "/index"],
)


def _empty_plot_json(title: str, message: str) -> str:
    """Serialize an empty-state graph for the cached plot store."""
    return generate_empty_plot(title, message).to_json()


def _placeholder_plot_json() -> str:
    """Serialize the neutral pre-hydration graph placeholder."""
    return generate_placeholder_plot().to_json()


@callback(
    Output("run-events", "data"),
    Output("scenario-dropdown-selection", "value"),
    Input(RUN_EVENTS_BATCH_STORE_ID, "data"),
    # State, not Input: the old drain was destructive, so a control-triggered
    # rerun found nothing. A Store replays its last value instead, and a
    # control flip must not re-forward a batch already processed. The same
    # reason keeps prevent_initial_call on: navigating back here remounts the
    # page against a retained store value, and a mount must not replay it.
    State("automatically-change-scenario-switch", "checked"),
    State("scenario-dropdown-selection", "value"),
    prevent_initial_call=True,
)
def check_for_new_data(batch, automatically_change_scenario, selected_scenario):
    """Forward the shell's run-event batch as one summary for this page."""
    if not batch:
        return no_update, no_update

    target_scenario, run_events = summarize_run_events(
        batch,
        selected_scenario,
        automatically_change_scenario,
    )
    if run_events is None:
        return no_update, no_update

    scenario_update = (
        target_scenario if target_scenario != selected_scenario else no_update
    )
    return run_events, scenario_update


register_run_import_failure_flush("interval-component")
register_scenario_stats(SCENARIO_STATS_IDS)


def _run_events_were_triggered(triggered: list[dict[str, str]]) -> bool:
    """Return whether a callback invocation was caused by new run events."""
    return any(trigger["prop_id"] == _RUN_EVENTS_PROP for trigger in triggered)


def _empty_state_graph_response(
    title: str,
    message: str,
) -> tuple[str, object, object, object]:
    """Return a cached empty-state plot with notifications left unchanged."""
    return _empty_plot_json(title, message), no_update, no_update, no_update


def _build_scenario_figure(  # noqa: PLR0913
    x_axis_radiogroup: str,
    selected_scenario: str,
    top_n_scores: int,
    oldest_datetime: datetime,
    rank_overlay_switch: bool,
    show_all_ranks_switch: bool,
    selected_playlist: str | None,
) -> tuple[go.Figure, bool]:
    """Query the selected x-axis mode and build its figure.

    Returns the figure plus whether score overlays apply to it. Empty-range and
    unsupported-mode placeholders return ``False`` so the caller skips overlays
    and notifications.
    """
    if x_axis_radiogroup == "score_vs_sensitivity":
        sensitivities_vs_runs = get_sensitivities_vs_runs_filtered(
            selected_scenario,
            top_n_scores,
            oldest_datetime,
        )
        if not sensitivities_vs_runs:
            logger.warning(
                'No scenario data found for "%s" for date range: %s',
                selected_scenario,
                oldest_datetime,
            )
            return (
                generate_empty_plot(
                    _NO_DATE_RANGE_DATA_PLOT_TITLE,
                    _NO_DATE_RANGE_DATA_PLOT_MESSAGE,
                ),
                False,
            )

        rank_data = (
            get_rank_data_from_playlist_code(selected_playlist, selected_scenario)
            if selected_playlist
            else []
        )

        return (
            generate_sensitivity_plot(
                sensitivities_vs_runs,
                selected_scenario,
                rank_overlay_switch,
                rank_data,
                show_all_ranks_switch,
            ),
            True,
        )

    if x_axis_radiogroup == "score_vs_time":
        time_vs_runs = get_time_vs_runs(
            selected_scenario,
            top_n_scores,
            oldest_datetime,
        )
        if not time_vs_runs:
            logger.warning(
                'No scenario data found for "%s" for date range: %s',
                selected_scenario,
                oldest_datetime,
            )
            return (
                generate_empty_plot(
                    _NO_DATE_RANGE_DATA_PLOT_TITLE,
                    _NO_DATE_RANGE_DATA_PLOT_MESSAGE,
                ),
                False,
            )

        rank_data = (
            get_rank_data_from_playlist_code(selected_playlist, selected_scenario)
            if selected_playlist
            else []
        )

        return (
            generate_time_plot(
                time_vs_runs,
                selected_scenario,
                rank_overlay_switch,
                rank_data,
                show_all_ranks_switch,
                get_new_high_score_runs(selected_scenario),
            ),
            True,
        )

    logger.error("Unsupported radio option: %r", x_axis_radiogroup)
    return (
        generate_empty_plot(
            _UNSUPPORTED_GRAPH_OPTION_PLOT_TITLE,
            _UNSUPPORTED_GRAPH_OPTION_PLOT_MESSAGE,
        ),
        False,
    )


@callback(
    Output("cached-plot", "data"),
    Output("notification-container", "sendNotifications"),
    Output("notification-container", "hideNotifications"),
    Output(TOAST_CHANNEL_REGISTRY_STORE_ID, "data"),
    Input("run-events", "data"),
    Input("scenario-dropdown-selection", "value"),
    Input("top_n_scores", "value"),
    Input("date-picker", "value"),
    Input("x-axis-radiogroup", "value"),
    Input("rank-overlay-switch", "checked"),
    Input("show-all-ranks-switch", "checked"),
    Input("high-score-overlay-switch", "checked"),
    Input("score-threshold-overlay-switch", "checked"),
    Input("score-threshold-percentage", "value"),
    Input("score-threshold-notification-switch", "checked"),
    # State, not Input: this preference only decides whether a run event that
    # already triggered the callback gets to toast. Flipping it must not
    # rebuild the plot or reread the scenario's runs.
    State("run-notification-switch", "checked"),
    State("playlist-dropdown-selection", "value"),
    State(TOAST_CHANNEL_REGISTRY_STORE_ID, "data"),
)
# This callback coordinates the page's graph controls and notification states.
def generate_graph(  # noqa: PLR0913
    run_events,
    selected_scenario,
    top_n_scores,
    selected_date,
    x_axis_radiogroup,
    rank_overlay_switch,
    show_all_ranks_switch,
    high_score_overlay_switch,
    score_threshold_overlay_switch,
    score_threshold_percentage,
    score_threshold_notification_switch,
    run_notification_switch,
    selected_playlist,
    toast_channels,
):
    """
    Updates to the graph.
    :param run_events: summary of newly ingested runs, when this invocation has one.
    :param selected_scenario: user-selected scenario name.
    :param top_n_scores: user-selected top n scores.
    :param selected_date: user-selected date.
    :param x_axis_radiogroup: user-selected x-axis radio group.
    :param rank_overlay_switch: rank overlay switch. True=show rank overlay.
    :param show_all_ranks_switch: show all ranks switch. True=draw the full
        ladder instead of the ranks bracketing the plotted scores.
    :param run_notification_switch: run notifications master switch.
        False=this run's toast is not built at all.
    :param selected_playlist: user-selected playlist code.
    :param toast_channels: this client's toast channel instance registry.
    :return: Figure serialized to JSON, the toasts to show, the instance ids to
        hide, and the registry patch that records the rotation
    """
    if not selected_scenario:
        return _empty_state_graph_response(
            _SELECT_SCENARIO_PLOT_TITLE,
            _SELECT_SCENARIO_PLOT_MESSAGE,
        )

    if not top_n_scores or not selected_date:
        return _empty_state_graph_response(
            _INCOMPLETE_GRAPH_CONTROLS_TITLE,
            _INCOMPLETE_GRAPH_CONTROLS_MESSAGE,
        )

    if not is_scenario_in_database(selected_scenario):
        logger.warning('No scenario data found for: "%s"', selected_scenario)
        return _empty_state_graph_response(
            _NO_SCENARIO_DATA_PLOT_TITLE,
            _NO_SCENARIO_DATA_PLOT_MESSAGE,
        )

    oldest_datetime = datetime.combine(
        datetime.fromisoformat(selected_date).date(),
        datetime.min.time(),
    )

    plot, supports_overlays = _build_scenario_figure(
        x_axis_radiogroup,
        selected_scenario,
        top_n_scores,
        oldest_datetime,
        rank_overlay_switch,
        show_all_ranks_switch,
        selected_playlist,
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
        if _run_events_were_triggered(ctx.triggered):
            run_verdict = build_run_event_notification(
                run_events,
                selected_scenario,
                top_n_scores,
                score_threshold_percentage,
                score_threshold_notification_switch,
                run_notification_switch,
            )
            if run_verdict is not None:
                notifications, hide_notifications, next_toast_channels = channel_toast(
                    run_verdict, toast_channels
                )
    return plot.to_json(), notifications, hide_notifications, next_toast_channels


register_chart_options(CHART_OPTIONS_IDS)
register_startup_playlist_warning_flush("startup-playlist-warning-interval")
register_scenario_selection(SCENARIO_SELECTION_IDS)


@callback(
    Output(SETUP_CARD_ID, "children"),
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Output("notification-container", "hideNotifications", allow_duplicate=True),
    Output(TOAST_CHANNEL_REGISTRY_STORE_ID, "data", allow_duplicate=True),
    # ``allow_optional``: Skip renders only in the identity state, while the
    # container it writes to is always mounted. Without it, every other state
    # of the page -- the stats-folder card, and every configured install --
    # logs "ID not found in layout" for this input on each load.
    Input(SETUP_CARD_SKIP_ID, "n_clicks", allow_optional=True),
    State(TOAST_CHANNEL_REGISTRY_STORE_ID, "data"),
    prevent_initial_call=True,
)
def skip_identity_setup(n_clicks, toast_channels):
    """Record the declined identity ask and take the card away.

    The write goes through the settings service's decline operation rather than
    a read-merge-write here: this callback's page was rendered at some earlier
    moment, and a settings save made since must not be undone by a card click.

    Nothing else follows from it. The warmup worker is not started -- there is
    no username to warm anything for -- and nothing pins, because the identity
    pin freezes only on a read that sees a configured username, so the click
    produces no restart notice either.

    Guard on ``n_clicks`` and the trigger: under DashProxy a callback can fire
    once on page load with nothing having triggered it, and a page load must
    never answer a question the user has not been asked yet.

    Two things can stop the write. A settings file stamped by a newer build
    refuses it, and the write itself can fail on an unwritable ``data/``. Both
    leave the card up -- taking it away would claim a decline that was never
    recorded, and it would be back on the next load anyway -- so the toast is
    what explains why the click appeared to do nothing. Without the ``OSError``
    guard the callback 500s instead, and the click reads as nothing at all.

    Both report on one channel, so a second Skip click re-pops the current
    answer instead of clicking into silence, and a retry that fails differently
    replaces the first explanation rather than sitting beside it.
    """
    if not n_clicks or ctx.triggered_id != SETUP_CARD_SKIP_ID:
        return no_update, no_update, no_update, no_update
    try:
        decline_identity()
    except UnsupportedSchemaError:
        logger.warning("Refused to record the declined identity ask")
        notification = toast(
            SETUP_CARD_SKIP_PROBLEM_CHANNEL,
            SETUP_CARD_SKIP_REFUSED_TITLE,
            SETUP_CARD_SKIP_REFUSED_MESSAGE,
            color="red",
            icon=local_icon("material-symbols:warning-outline"),
        )
        return no_update, *channel_toast(notification, toast_channels)
    except OSError:
        # A locked, full, or read-only ``data/`` leaves the store exactly as it
        # was: the write is a temp file plus an atomic replace, so there is
        # nothing to clean up and nothing to undo. Separate from the refusal
        # above because the remedy is the opposite -- retrying, not updating
        # the app.
        logger.exception("Failed to record the declined identity ask")
        notification = toast(
            SETUP_CARD_SKIP_PROBLEM_CHANNEL,
            SETUP_CARD_SKIP_REFUSED_TITLE,
            SETUP_CARD_SKIP_FAILED_MESSAGE,
            color="red",
            icon=local_icon("material-symbols:warning-outline"),
        )
        return no_update, *channel_toast(notification, toast_channels)
    return [], no_update, no_update, no_update


# Per Dash documentation, we should include **kwargs in case the layout receives unexpected query strings.
def layout(
    scenario: str | None = None,
    playlist_code: str | None = None,
    **_kwargs,
):
    """Build the interactive home dashboard."""
    config = get_config()
    playlist_options = playlist_filter_options(playlist_code)
    scenario_options = initial_scenario_options(playlist_code)

    return dmc.Box(
        className="home-page",
        children=[
            dcc.Store(id="run-events"),
            dcc.Store(
                id=SCENARIO_SELECTION_IDS.deep_link,
                data=deep_link_selection(scenario, playlist_code),
            ),
            dcc.Store(
                id="cached-plot",
                data=_placeholder_plot_json(),
            ),  # caches the plot for easy light/dark mode
            *scenario_stats_stores(SCENARIO_STATS_IDS),
            dcc.Interval(
                id="startup-playlist-warning-interval",
                interval=250,
                n_intervals=0,
                max_intervals=1,
            ),
            dcc.Interval(
                id="interval-component",
                interval=config.polling_interval,
                n_intervals=0,
            ),
            # Dedicated 30s tick for the relative "Last played" text, decoupled
            # from polling_interval so display cadence is right-sized for minute
            # granularity and never coupled to data-polling cadence.
            dcc.Interval(
                id="relative-time-interval",
                interval=30_000,
                n_intervals=0,
            ),
            *stats_dir_hint(),
            dmc.Box(id=SETUP_CARD_ID, children=setup_card_children()),
            dmc.Grid(
                children=[
                    dmc.GridCol(
                        dmc.Flex(
                            children=[
                                dmc.Box(
                                    [
                                        dmc.Select(
                                            **PLAYLIST_SELECTOR_PRESET,
                                            allowDeselect=False,
                                            autoSelectOnBlur=True,
                                            classNames={
                                                "input": SELECT_HIGHLIGHT_ON_OPEN_CLASS
                                            },
                                            clearable=True,
                                            data=playlist_options,
                                            id="playlist-dropdown-selection",
                                            label="Playlist filter",
                                            persistence=True,
                                            # Never the query parameter, and
                                            # never omitted. Dash pins a
                                            # persisted edit to the layout
                                            # value it was made against and
                                            # discards the edit when a later
                                            # visit renders a different one,
                                            # so a default that varies per
                                            # visit silently retires
                                            # persistence. ``apply_deep_link``
                                            # carries the query parameter
                                            # instead. Explicit ``None``
                                            # because an omitted prop is
                                            # ``undefined``, which no longer
                                            # matches what a browser already
                                            # stored.
                                            value=None,
                                        ),
                                        dmc.Box(
                                            id=SCENARIO_SELECTION_IDS.playlist_table_link
                                        ),
                                    ],
                                    className=PLAYLIST_FIELD_CLASS,
                                    # The column, not the Select inside it, is
                                    # the flex item this row breaks lines on.
                                    **PLAYLIST_SELECTOR_SIZING,
                                ),
                                dmc.Stack(
                                    [
                                        dmc.Select(
                                            allowDeselect=False,
                                            autoSelectOnBlur=True,
                                            checkIconPosition="right",
                                            classNames={
                                                "input": SELECT_HIGHLIGHT_ON_OPEN_CLASS
                                            },
                                            data=scenario_options,
                                            id="scenario-dropdown-selection",
                                            label="Selected scenario",
                                            maxDropdownHeight="75vh",
                                            persistence=True,
                                            placeholder="Select a scenario",
                                            scrollAreaProps={"type": "auto"},
                                            searchable=True,
                                            # Constant on every visit, for the
                                            # reason the playlist filter's own
                                            # default carries;
                                            # ``apply_deep_link`` is what
                                            # applies ``?scenario=``.
                                            value=None,
                                        ),
                                        # Selection behavior, not chart
                                        # presentation: it decides what the
                                        # selector does when a new run lands,
                                        # so it sits under the selector rather
                                        # than in the chart options inspector.
                                        dmc.Switch(
                                            id="automatically-change-scenario-switch",
                                            labelPosition="right",
                                            label=settings_help_label(
                                                "Follow newly played scenario",
                                                SETTINGS_HELP_TEXT[
                                                    "automatically-change-scenario"
                                                ],
                                            ),
                                            checked=True,
                                            persistence=True,
                                        ),
                                    ],
                                    className="home-scenario-field",
                                    # The column, not the Select inside it, is
                                    # the flex item this row breaks lines on.
                                    # Mirrors the playlist filter beside it;
                                    # see PLAYLIST_SELECTOR_SIZING for why the
                                    # basis is the floor and not the 400px
                                    # target.
                                    flex="1 1 200px",
                                    gap="xs",
                                    maw="min(400px, 100%)",
                                    miw="min(200px, 100%)",
                                ),
                                dmc.Space(h="xl"),
                                dmc.Space(h="xl"),
                                dmc.NumberInput(
                                    id="top_n_scores",
                                    label=settings_help_label(
                                        "Top N scores",
                                        SETTINGS_HELP_TEXT["top-n-scores"],
                                    ),
                                    min=1,
                                    persistence=True,
                                    radius="sm",
                                    size="sm",
                                    variant="default",
                                    value=5,
                                    w="8rem",
                                ),
                                dmc.DatePickerInput(
                                    id="date-picker",
                                    label="Oldest date to consider",
                                    maxDate=datetime.now().isoformat(),
                                    persistence=True,
                                    rightSection=local_icon("clarity:date-line"),
                                    value=datetime(
                                        datetime.now().year,
                                        month=1,
                                        day=1,
                                    ).isoformat(),
                                ),
                                scenario_stats_panel(SCENARIO_STATS_IDS),
                            ],
                            gap="sm",
                            justify="flex-start",
                            align="flex-start",
                            direction="row",
                            wrap="wrap",
                        ),
                        span={"base": 12, "lg": 10},
                    ),
                    dmc.GridCol(
                        dmc.Flex(
                            children=[
                                dmc.RadioGroup(
                                    children=dmc.Stack(
                                        [
                                            dmc.Radio(label, value=value)
                                            for value, label in [
                                                [
                                                    "score_vs_sensitivity",
                                                    "Score vs Sensitivity",
                                                ],
                                                ["score_vs_time", "Score vs Time"],
                                            ]
                                        ],
                                    ),
                                    id="x-axis-radiogroup",
                                    value="score_vs_sensitivity",
                                    persistence=True,
                                ),
                                dmc.Space(h="xl"),
                                chart_options_toggle(CHART_OPTIONS_IDS),
                            ],
                            gap="md",
                            justify="flex-end",
                            align="center",
                            direction="row",
                            wrap="wrap",
                        ),
                        span={"base": 12, "lg": "auto"},
                    ),
                ],
                breakpoints=HOME_GRID_BREAKPOINTS,
                gutter="xl",
                overflow="hidden",
                type="container",
            ),
            # The chart and its inspector share one row. The wrapper is the box
            # the reflow threshold measures: a container query cannot match on
            # the element that declares the container, so the row carrying the
            # layout sits inside it.
            dmc.Box(
                className="home-chart-area",
                children=dmc.Box(
                    className="home-chart-row",
                    children=[
                        dcc.Graph(
                            id="graph-content",
                            figure=generate_placeholder_plot().to_plotly_json(),
                            className="home-graph",
                            # Redraw the plot whenever the flex container
                            # resizes, not just on window resize.
                            responsive=True,
                        ),
                        chart_options_panel(CHART_OPTIONS_IDS),
                    ],
                ),
            ),
        ],
    )
