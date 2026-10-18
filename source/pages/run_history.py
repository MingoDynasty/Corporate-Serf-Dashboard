"""Build the Run History page and its callbacks.

The page shows one scenario's runs: a chart of every run in a range, with
the Chart options panel beside it, and a list of the runs grouped by session.
The list has a second view, All scenarios, of each session whole. Cards in
its top row report the selected scenario's personal best and its latest run.

It never imports another page's module. Dash Pages loads each page file as
``pages.<name>``, so a second import path would make a second copy of that
module with its own state. What it shares with the Home page, the setup
surfaces and the queued notices, lives under ``source/components/``.
"""

import json
import logging
from datetime import datetime

import dash
import dash_mantine_components as dmc
from dash import (
    Input,
    Output,
    State,
    callback,
    clientside_callback,
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
from source.components.latest_run_card import (
    AGE_SCRIPT,
    LatestRunCardIds,
    latest_run_card,
    latest_run_card_content,
    latest_run_from_store,
)
from source.components.pb_card import PbCardIds, pb_card, register_pb_card
from source.components.queued_notices import (
    register_run_import_failure_flush,
    register_startup_playlist_warning_flush,
)
from source.components.run_delivery import summarize_run_events
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
from source.components.run_history_list import (
    SESSIONS_PER_LOAD,
    VIEW_ALL,
    RunListIds,
    is_session_in_progress,
    register_run_list,
    run_list_class,
    run_list_from_store,
    run_list_panel,
    run_list_stores,
)
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
from source.pages.playlist_selector import PLAYLIST_SELECTOR_PRESET
from source.plot.plot_service import (
    add_high_score_overlay,
    add_score_threshold_overlay,
    generate_empty_plot,
    generate_placeholder_plot,
)

logger = logging.getLogger(__name__)

# Every id below is this page's alone, its stores and intervals included. A
# page that holds one output of a callback has to hold every input of it, so
# two pages cannot share part of a callback. The browser also stores each
# remembered control's value under its id, so changing one of these resets
# that value for every user.
RUN_EVENTS_STORE_ID = "run-history-run-events"
POLLING_INTERVAL_ID = "run-history-polling-interval"
RELATIVE_TIME_INTERVAL_ID = "run-history-relative-time-interval"
STARTUP_PLAYLIST_WARNING_INTERVAL_ID = "run-history-startup-playlist-warning-interval"
# The date the chart's ranges of days were last counted back from, as ISO
# text. It is written only when the date moves on, and the chart takes it as
# an input, which is what redraws a chart that is left open past midnight.
TODAY_STORE_ID = "run-history-today"
# The id of the newest run in the last batch the shell published, whatever
# scenario it was on. The summary store names only a run on the scenario the
# page shows, so a run on another scenario leaves it unwritten, and what
# counts every scenario's runs would never hear of that run: a session row's
# count, a divider, the latest run. This one is written for every batch.
RUN_LANDED_STORE_ID = "run-history-run-landed"
# Whether the run store's newest session is in progress. It is written only
# when the answer changes, and the run list takes it as an input, which is
# what takes "In progress" off a session nothing more is played in.
SESSION_IN_PROGRESS_STORE_ID = "run-history-session-in-progress"
# The id of the newest run in the run store, on whatever scenario. The
# latest-run card's callback writes it from the store it reads the card's run
# from, only when it is another run than the one held. The graph takes it as
# an input: a figure rings its own scenario's newest run, and the ring shows
# while this names the same run.
LATEST_RUN_STORE_ID = "run-history-latest-run"
# A store nothing reads. The script that hands keyboard focus on from the
# card's scenario button writes nothing, and a clientside callback has to
# have an output.
CARD_FOCUS_SINK_ID = "run-history-card-focus-sink"
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
    graph="run-history-graph",
    cached_plot="run-history-cached-plot",
)
RUN_LIST_IDS = RunListIds(
    panel="run-history-list",
    heading="run-history-list-heading",
    view="run-history-list-view",
    expand_all="run-history-list-expand-all",
    columns_menu="run-history-list-columns",
    grid="run-history-list-grid",
    empty="run-history-list-empty",
    announcer="run-history-list-announcer",
    model="run-history-list-model",
    session_limit="run-history-list-session-limit",
    all_session_limit="run-history-list-all-session-limit",
    jump="run-history-list-jump",
    scenario_asked="run-history-list-scenario-asked",
    apply_sink="run-history-list-apply-sink",
    expand_all_sink="run-history-list-expand-all-sink",
    figures_sink="run-history-list-figures-sink",
)
LATEST_RUN_CARD_IDS = LatestRunCardIds(
    played_at="run-history-card-played-at",
    label="run-history-card-lead",
    time="run-history-card-time",
    time_tooltip="run-history-card-time-tooltip",
    heading="run-history-card-heading",
    scenario_button="run-history-card-scenario-button",
    body="run-history-card-body",
)
SCENARIO_STATS_IDS = ScenarioStatsIds(
    category_row="run-history-category-row",
    category="run-history-category",
    last_played="run-history-last-played",
    last_played_tooltip="run-history-last-played-tooltip",
    num_runs="run-history-num-runs",
    last_played_ts="run-history-last-played-ts",
    last_played_empty_value="run-history-last-played-empty-value",
    run_events=RUN_EVENTS_STORE_ID,
    scenario_dropdown=SCENARIO_SELECTION_IDS.scenario_dropdown,
    playlist_filter=SCENARIO_SELECTION_IDS.playlist_filter,
    relative_time_interval=RELATIVE_TIME_INTERVAL_ID,
)
# The position's ids are the ones it had in the Scenario Stats card. No browser
# remembers a value under any of them.
PB_CARD_IDS = PbCardIds(
    set_at="run-history-pb-set-at",
    label="run-history-pb-label",
    time="run-history-pb-time",
    time_tooltip="run-history-pb-time-tooltip",
    body="run-history-pb-body",
    leaderboard="run-history-pb-leaderboard",
    rank_label="run-history-position-label",
    rank="run-history-position",
    rank_updated_tooltip="run-history-position-updated-tooltip",
    rank_refresh_button="run-history-position-refresh-button",
    rank_updated_ts="run-history-position-updated-ts",
    rank_of_total="run-history-position-of-total",
    faded="run-history-pb-faded",
    run_events=RUN_EVENTS_STORE_ID,
    scenario_dropdown=SCENARIO_SELECTION_IDS.scenario_dropdown,
    playlist_filter=SCENARIO_SELECTION_IDS.playlist_filter,
    polling_interval=POLLING_INTERVAL_ID,
    relative_time_interval=RELATIVE_TIME_INTERVAL_ID,
)

# The class the resize script and the zoom fit script find a graph by
# (``assets/homeGraphResize.js``, ``assets/homeGraphZoomFit.js``).
GRAPH_CLASS = "home-graph"
RANGE_FIELD_CLASS = "run-history-range-field"
RANGE_FIELD_HIDDEN_CLASS = f"{RANGE_FIELD_CLASS} run-history-range-field-hidden"

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
    Output(RUN_LANDED_STORE_ID, "data"),
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

    The second output is the id of the batch's newest run, written whether or
    not there is a summary. Both are written in this one answer on purpose.
    What rebuilds on the second also reads the scenario dropdown, and Dash
    holds a callback back only for a writer that is already queued. Written
    together, the selection callback is queued for the summary when the run
    list is queued for the run, so the list waits for the selection to move
    and is built once, for the scenario the page ends up on.
    """
    if not batch or not batch["runs"]:
        return no_update, no_update
    _target_scenario, run_events = summarize_run_events(
        batch,
        selected_scenario,
        follow_newly_played,
    )
    return (
        no_update if run_events is None else run_events,
        batch["runs"][-1]["run_id"],
    )


register_run_import_failure_flush(POLLING_INTERVAL_ID)
register_scenario_stats(SCENARIO_STATS_IDS)
register_pb_card(PB_CARD_IDS)


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
    Output(SESSION_IN_PROGRESS_STORE_ID, "data"),
    Input(RELATIVE_TIME_INTERVAL_ID, "n_intervals"),
    # A run that lands can start a session or reopen one. Taking it here puts
    # this callback in the queue with the run list, which then waits for this
    # answer and is built once per run, not once for the run and again on the
    # next tick.
    Input(RUN_LANDED_STORE_ID, "data"),
    State(SESSION_IN_PROGRESS_STORE_ID, "data"),
    # The layout draws the store with the answer already in it, as it does
    # the date.
    prevent_initial_call=True,
)
def track_session_in_progress(_n_intervals, _run_landed, held_answer):
    """Write whether a session is in progress, once that is no longer what is held.

    A session is in progress until 30 minutes after its last run, and nothing
    happens at that moment: no run lands and no control changes. The run
    list takes this store as an input, so this write is what clears
    "In progress", within one tick. A tick that finds the same answer writes
    nothing, so a tick alone never rebuilds the list.

    The answer is the app's own, from its own clock. A browser's clock can be
    in another time zone than the stats files were written in.
    """
    in_progress = is_session_in_progress(datetime.now())
    return no_update if in_progress == held_answer else in_progress


@callback(
    Output(RUN_LIST_IDS.model, "data"),
    Output(RUN_LIST_IDS.heading, "children"),
    Output(RUN_LIST_IDS.empty, "children"),
    Output(RUN_LIST_IDS.panel, "className"),
    # The view, and each view's count of loaded sessions. A jump writes the
    # view and All scenarios' count in one answer, both plain outputs, so
    # Dash holds this callback until both are in and builds the tree once.
    Input(RUN_LIST_IDS.view, "value"),
    Input(SCENARIO_SELECTION_IDS.scenario_dropdown, "value"),
    # Any run, on any scenario: a session row counts all of a session's runs.
    # The list is still built from the run store and never from the batch.
    Input(RUN_LANDED_STORE_ID, "data"),
    Input(RUN_LIST_IDS.session_limit, "data"),
    Input(RUN_LIST_IDS.all_session_limit, "data"),
    # A change to the percentage marks every run again, at once.
    Input(CHART_OPTIONS_IDS.score_threshold_percentage, "value"),
    # The next two are read for nothing but their change. A session's name
    # leaves the year out only while it is this year's, and "In progress"
    # ends with no run landing.
    Input(TODAY_STORE_ID, "data"),
    Input(SESSION_IN_PROGRESS_STORE_ID, "data"),
)
def build_run_list_rows(  # noqa: PLR0913
    view,
    selected_scenario,
    _run_landed,
    session_limit,
    all_session_limit,
    score_threshold_percentage,
    _held_date,
    _held_in_progress,
):
    """Build the run list's rows in the view on screen, from the run store.

    Under This scenario the rows are the selected scenario's. Under All
    scenarios they are every session's, and the selected scenario's rows are
    marked. Returns the rows and what the script needs with them, the
    heading line, the text shown when there is nothing to list, and the
    list's class, which is how that text takes the grid's place.
    """
    limit = all_session_limit if view == VIEW_ALL else session_limit
    model = run_list_from_store(
        view,
        selected_scenario,
        limit or SESSIONS_PER_LOAD,
        score_threshold_percentage,
        datetime.now(),
    )
    return model, model["heading"], model["empty"], run_list_class(model)


@callback(
    Output(LATEST_RUN_CARD_IDS.played_at, "data"),
    Output(LATEST_RUN_CARD_IDS.heading, "children"),
    Output(LATEST_RUN_CARD_IDS.scenario_button, "children"),
    Output(LATEST_RUN_CARD_IDS.scenario_button, "value"),
    Output(LATEST_RUN_CARD_IDS.scenario_button, "aria-label"),
    Output(LATEST_RUN_CARD_IDS.body, "children"),
    Output(LATEST_RUN_STORE_ID, "data"),
    # Any run, on any scenario. A run on another scenario moves the ring's
    # store, and can change which session the card's run is in: a new
    # session makes the old one "last" or older. The card is still worked
    # out from the run store and never from the batch.
    Input(RUN_LANDED_STORE_ID, "data"),
    Input(SCENARIO_SELECTION_IDS.scenario_dropdown, "value"),
    # The percentage decides the badge of a run that is not a new PB.
    Input(CHART_OPTIONS_IDS.score_threshold_percentage, "value"),
    # The next two are read for nothing but their change. "This session"
    # becomes "last session" with no run landing, and an older session's
    # name leaves its year out only while it is this year's.
    Input(SESSION_IN_PROGRESS_STORE_ID, "data"),
    Input(TODAY_STORE_ID, "data"),
    State(LATEST_RUN_STORE_ID, "data"),
)
def show_latest_run(  # noqa: PLR0913
    _run_landed,
    selected_scenario,
    score_threshold_percentage,
    _held_in_progress,
    _held_date,
    held_latest_run,
):
    """Write what the latest-run card shows, from the run store.

    The card reports the selected scenario's latest run. The page load runs
    it, so the card is right with no new run. It takes the scenario dropdown
    and the session store, both written by callbacks a run that lands also
    calls, so it waits for them and writes the card once per batch, for the
    scenario the page ends up on.

    The first output is when the run ended, which a script words as its age.
    The last is the id of the newest run on any scenario, which the chart's
    ring and the run list's highlight mark, so during a lookup they leave the
    card's run. It is written only when it is another run than the one held.
    The graph takes that store as an input, so writing the same id again
    would restyle a chart that nothing had changed.
    """
    shown, newest_run_id = latest_run_from_store(
        selected_scenario, score_threshold_percentage, datetime.now()
    )
    return (
        *latest_run_card_content(
            shown, selected_scenario, store_has_runs=newest_run_id is not None
        ),
        no_update if newest_run_id == held_latest_run else newest_run_id,
    )


clientside_callback(
    AGE_SCRIPT,
    Output(LATEST_RUN_CARD_IDS.label, "hidden"),
    Output(LATEST_RUN_CARD_IDS.time, "children"),
    Output(LATEST_RUN_CARD_IDS.time_tooltip, "label"),
    Input(LATEST_RUN_CARD_IDS.played_at, "data"),
    Input(RELATIVE_TIME_INTERVAL_ID, "n_intervals"),
)


@callback(
    Output(CHART_OPTIONS_IDS.cached_plot, "data"),
    # Read for nothing but its change: a run that lands on the scenario the
    # page shows is what redraws the chart with it.
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
)
def generate_graph(  # noqa: PLR0913
    _run_events,
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
):
    """Build the chart, and return the figure serialized to JSON.

    The page load runs it, which is what draws the first chart.
    """
    if not selected_scenario:
        return _empty_plot_json(NO_SCENARIO_PLOT_TITLE, NO_SCENARIO_PLOT_MESSAGE)

    if not is_scenario_in_database(selected_scenario):
        logger.warning('No scenario data found for: "%s"', selected_scenario)
        return _empty_plot_json(NO_LOCAL_RUNS_PLOT_TITLE, NO_LOCAL_RUNS_PLOT_MESSAGE)

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
    return plot.to_json()


# Which range select shows: the one in runs under Score vs Run, and the one
# in days under the other two modes.
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

# Pressing the card's scenario button selects its scenario, and the button
# then leaves the page, which drops keyboard focus to the document: the next
# Tab would start again from the top of the page. So once the button has
# gone, focus goes to the Selected scenario dropdown, which then names the
# scenario that was asked for. It waits for the button to go because that is
# when the new value is in the dropdown, and it stands down if focus has
# moved elsewhere meanwhile.
#
# Only for a press from the keyboard, which is what ``:focus-visible`` on the
# button says. A click with the mouse loses nothing by losing focus, and
# focus on a searchable dropdown opens its list.
_HAND_FOCUS_TO_SCENARIO_SCRIPT = """
(clicks) => {
    const button = document.getElementById(BUTTON_ID);
    if (clicks && button && button.matches(":focus-visible")) {
        const started = Date.now();
        const handOn = () => {
            if (button.offsetParent !== null) {
                if (Date.now() - started < 5000) {
                    window.setTimeout(handOn, 50);
                }
                return;
            }
            const held = document.activeElement;
            if (!held || held === button || held === document.body) {
                const field = document.getElementById(SCENARIO_ID);
                if (field) {
                    field.focus();
                }
            }
        };
        handOn();
    }
    return window.dash_clientside.no_update;
}
""".replace("BUTTON_ID", json.dumps(LATEST_RUN_CARD_IDS.scenario_button)).replace(
    "SCENARIO_ID", json.dumps(SCENARIO_SELECTION_IDS.scenario_dropdown)
)

clientside_callback(
    _HAND_FOCUS_TO_SCENARIO_SCRIPT,
    Output(CARD_FOCUS_SINK_ID, "data"),
    Input(LATEST_RUN_CARD_IDS.scenario_button, "n_clicks"),
    prevent_initial_call=True,
)

register_chart_options(CHART_OPTIONS_IDS, latest_run=LATEST_RUN_STORE_ID)
register_run_list(RUN_LIST_IDS, follow_switch=FOLLOW_SWITCH_ID)
register_startup_playlist_warning_flush(STARTUP_PLAYLIST_WARNING_INTERVAL_ID)
register_scenario_selection_clearing_filter(
    SCENARIO_SELECTION_IDS,
    run_events=RUN_EVENTS_STORE_ID,
    follow_switch=FOLLOW_SWITCH_ID,
    run_landed=RUN_LANDED_STORE_ID,
    scenario_button=LATEST_RUN_CARD_IDS.scenario_button,
    scenario_asked=RUN_LIST_IDS.scenario_asked,
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


def _dropdown_column(playlist_code: str | None) -> dmc.Box:
    """Build the playlist filter over the scenario dropdown.

    Each Select keeps its own label, which names its input. The link and the
    switch come after the Select, and the stylesheet places them on the
    label's line, beside the label. Inside the label they would join the
    name a screen reader gives the dropdown.
    """
    return dmc.Box(
        className="run-history-dropdown-column",
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
                    dmc.Box(
                        className="run-history-playlist-table-link",
                        id=SCENARIO_SELECTION_IDS.playlist_table_link,
                    ),
                ],
                className="run-history-playlist-field",
            ),
            dmc.Box(
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
                    # Small, with a 16px help icon, so the line it adds to
                    # the dropdowns' column is 16px tall.
                    dmc.Switch(
                        className="run-history-follow-switch",
                        id=FOLLOW_SWITCH_ID,
                        labelPosition="right",
                        label=settings_help_label(
                            "Follow newly played scenario",
                            SETTINGS_HELP_TEXT["automatically-change-scenario"],
                            icon_size=16,
                        ),
                        checked=True,
                        persistence=True,
                        size="xs",
                    ),
                ],
                className="run-history-scenario-field",
            ),
        ],
    )


def _top_row(playlist_code: str | None) -> dmc.Box:
    """Build the row above the chart, in the columns of the chart and the run list.

    The first column holds the dropdowns, the Scenario Stats card, the room
    kept for notes, and the PB card at its right end. The second holds the
    latest-run card, over the run list, so the PB card sits beside it.
    """
    return dmc.Box(
        className="run-history-top-row",
        children=[
            dmc.Box(
                [
                    _dropdown_column(playlist_code),
                    scenario_stats_panel(SCENARIO_STATS_IDS),
                    pb_card(PB_CARD_IDS),
                ],
                className="run-history-top-row-left",
            ),
            latest_run_card(LATEST_RUN_CARD_IDS),
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
                        chart_options_panel(CHART_OPTIONS_IDS),
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
            dcc.Store(id=RUN_LANDED_STORE_ID),
            dcc.Store(id=LATEST_RUN_STORE_ID),
            dcc.Store(id=CARD_FOCUS_SINK_ID),
            # Drawn with the answer already in it, for the reason the date
            # is: the first tick would otherwise write it and rebuild a list
            # just drawn.
            dcc.Store(
                id=SESSION_IN_PROGRESS_STORE_ID,
                data=is_session_in_progress(datetime.now()),
            ),
            *run_list_stores(RUN_LIST_IDS),
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
            # A 30-second tick of its own for the relative times, Last played
            # and the two cards' ages, so how often they are reworded never
            # depends on how often the page polls for data.
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
                    dmc.Box(
                        run_list_panel(RUN_LIST_IDS),
                        className="run-history-list-column",
                    ),
                ],
            ),
        ],
    )
