"""Build the dashboard home page and its interactive callbacks."""

import json
import logging
from datetime import datetime
from typing import NamedTuple, TypedDict

import dash
import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import (
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    ctx,
    dcc,
    no_update,
)

from source.app_shell import (
    RUN_EVENTS_BATCH_STORE_ID,
    RunEventBatch,
    RunEventData,
)
from source.components.local_icon import local_icon
from source.config.config_service import get_config
from source.config.settings_service import (
    KOVAAKS_USERNAME_KEY,
    STATS_DIR_KEY,
    decline_identity,
    get_identity,
    get_kovaaks_username,
    get_settings,
    get_settings_store_state,
    get_usable_stats_dir,
    is_stats_dir_change_pending,
)
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from source.kovaaks.api_service import get_scenario_rank_info, steam_id_mismatch_warning
from source.kovaaks.data_service import (
    drain_startup_playlist_warnings,
    get_high_score,
    get_playlist_by_code,
    get_rank_data_from_playlist_code,
    get_scenario_stats,
    get_scenarios_from_playlist_code,
    get_sensitivities_vs_runs_filtered,
    get_time_vs_runs,
    get_unique_scenarios,
    is_scenario_in_database,
)
from source.kovaaks.playlist_visibility_service import (
    get_visible_playlist_selector_options,
)
from source.my_watchdog.file_watchdog import drain_run_import_failures
from source.pages.page_title import page_title
from source.pages.playlist_selector import PLAYLIST_SELECTOR_PRESET
from source.plot.plot_service import (
    POINT_SIZE_DEFAULT,
    POINT_SIZE_OPTIONS,
    add_high_score_overlay,
    add_score_threshold_overlay,
    apply_light_dark_mode,
    apply_point_appearance,
    generate_empty_plot,
    generate_placeholder_plot,
    generate_sensitivity_plot,
    generate_time_plot,
    generated_point_color,
)
from source.utilities.notifications import (
    TOAST_CHANNEL_REGISTRY_STORE_ID,
    channel_toast,
    toast,
)
from source.utilities.store_schema import StoreState, UnsupportedSchemaError
from source.utilities.utilities import format_absolute_timestamp, ordinal

logger = logging.getLogger(__name__)
SCENARIO_RANK_LOADING_DELAY_MS = 250
TOOLTIP_EVENTS = {"hover": True, "focus": True, "touch": True}
SETTINGS_HELP_TOOLTIP_WIDTH = 280
SETTINGS_HELP_TEXT = {
    "automatically-change-scenario": (
        "Automatically selects the scenario you just played when a new run is detected."
    ),
    "rank-overlay": (
        "Shows the selected playlist's rank threshold lines on the graph when "
        "rank data is available."
    ),
    "show-all-ranks": (
        "Draws every rank in the playlist's ladder instead of only the ones "
        "around your plotted scores. Needs Rank Thresholds turned on."
    ),
    "high-score-overlay": (
        "Shows your current personal best score as a reference line on the graph."
    ),
    "score-threshold-overlay": (
        "Shows a score goal line based on the selected percentage of your "
        "current personal best."
    ),
    "score-threshold-percentage": (
        "Sets the score goal as a percentage of your personal best. The "
        "overlay line tracks your current personal best; notifications judge "
        "the run against the personal best it was chasing."
    ),
    "score-threshold-notification": (
        "Adds a pass or fail verdict to run notifications when the run can be "
        "judged against the score threshold. Needs Run Notifications turned on."
    ),
    "run-notification": (
        "Controls threshold verdict and placement notifications for your runs. "
        "Personal best celebrations use their own setting."
    ),
    "top-n-scores": (
        "How many of your best scores to plot per sensitivity — or per day in "
        "Score vs Time — within the selected date range. A new run that lands "
        "in the top N also triggers a notification."
    ),
}
RANK_REFRESH_TOOLTIP = (
    "Fetch your current position live from the KovaaK's leaderboard. The "
    "displayed value can come from a local cache and may lag the live board."
)
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
# The chart options inspector. Its collapsed class is the open state: hiding
# with ``display: none`` takes the controls out of the tab order and the
# accessibility tree while leaving them mounted, so their persisted values keep
# feeding the graph callbacks either way.
CHART_OPTIONS_PANEL_ID = "chart-options-panel"
CHART_OPTIONS_TOGGLE_ID = "chart-options-toggle"
CHART_OPTIONS_PANEL_CLASS = "chart-options-panel"
CHART_OPTIONS_PANEL_HIDDEN_CLASS = "chart-options-panel-hidden"
# Below this much room for the chart row, the inspector stacks above the chart
# instead of sitting beside it (assets/stylesheet.css measures the row's own
# width with an ``@container`` query, never the window's). ``md`` is where a
# 20rem rail stops leaving a chart worth reading.
CHART_OPTIONS_REFLOW_BREAKPOINT = HOME_GRID_BREAKPOINTS["md"]
# The Run Data Points group. Both controls persist in the browser like their
# siblings, so their layout defaults -- Default and an empty color -- must not
# move: changing a persisted control's layout default silently discards every
# value the browser already stored under its id.
CHART_OPTIONS_FIELD_CLASS = "chart-options-field"
CHART_OPTIONS_FIELD_LABEL_CLASS = "chart-options-field-label"
POINT_SIZE_INPUT_ID = "point-size"
POINT_SIZE_LABEL_ID = "point-size-label"
POINT_COLOR_INPUT_ID = "point-color"
POINT_COLOR_DEFAULT_ID = "point-color-default"
POINT_COLOR_DEFAULT = ""
# The empty field previews the generated point color. Mantine paints the
# preview of an empty ColorInput white, so the stylesheet repaints it from
# these custom properties while the placeholder shows, one per color scheme
# because the graph's templates differ; the values come from plot_service so
# the swatch and the graph cannot disagree.
POINT_COLOR_FIELD_CLASS = "point-color-field"
POINT_COLOR_DEFAULT_CSS_VARIABLES = {
    "light": "--point-color-default-light",
    "dark": "--point-color-default-dark",
}
# Eight color families, one shade each, chosen per family against both real
# plot backgrounds (#ffffff light, #242424 dark) rather than by taking one
# Mantine shade index across the board. Yellow, lime, gray, and dark are
# omitted; docs/decision_log.md carries the reasoning and the contrast table.
POINT_COLOR_SWATCHES = [
    "#1c7ed6",  # blue-7
    "#0c8599",  # cyan-8
    "#099268",  # teal-8
    "#2b8a3e",  # green-9
    "#d9480f",  # orange-9
    "#f03e3e",  # red-7
    "#be4bdb",  # grape-6
    "#e64980",  # pink-6
]
# The first-run setup card. Its container is always in the layout so the Skip
# callback has an output to write to; the card itself is what comes and goes.
SETUP_CARD_ID = "setup-card"
SETUP_CARD_SKIP_ID = "setup-card-skip"
SETUP_CARD_IDENTITY_TITLE = "Add your KovaaK's account"
SETUP_CARD_IDENTITY_BODY = (
    "See your leaderboard position and percentiles for every scenario."
)
SETUP_CARD_SKIP_FINE_PRINT = (
    "Skipping username disables rank lookups. You can set it anytime in Settings."
)
SETUP_CARD_STATS_DIR_TITLE = "Finish setting up"
SETUP_CARD_STATS_DIR_BODY = (
    "No KovaaK's stats folder was found, so the dashboard can't read your runs "
    "yet. Set it in Settings."
)
# Shown when the settings file exists but cannot be used. The key-absence
# states below cannot speak for it: an unusable store reads as no keys at all,
# so they would claim a fresh install when a configured one is sitting on disk.
SETUP_CARD_STORE_TITLE = "Your settings can't be read"
SETUP_CARD_STORE_BODY = (
    "A settings file exists, but this version of the app can't use it, so the "
    "dashboard started without your settings. Open Settings to see what's "
    "wrong and how to fix it."
)
SETUP_CARD_OPEN_SETTINGS_LABEL = "Open Settings"
SETUP_CARD_SKIP_LABEL = "Skip"
# Shown when Skip cannot be recorded, either because the settings file belongs
# to a newer build or because the write itself failed. The card has to stay up
# (nothing was written), so the toast is what explains why the click appeared
# to do nothing. The two outcomes are mutually exclusive answers to the same
# click, so they share one channel: a second attempt replaces whatever the
# first one said instead of stacking a contradiction beside it.
SETUP_CARD_SKIP_PROBLEM_CHANNEL = "setup-card-skip-problem"
SETUP_CARD_SKIP_REFUSED_TITLE = "Skip was not saved"
SETUP_CARD_SKIP_REFUSED_MESSAGE = (
    "The settings file was written by a newer version of this app. Update the "
    "app to change settings."
)
SETUP_CARD_SKIP_FAILED_MESSAGE = (
    "Nothing was written. Try again, or see data/logs/debug.log for details."
)
# The primary action navigates, so it ships as one link wearing the button's
# styling. A ``dmc.Button`` inside a ``dmc.Anchor`` renders a focusable
# ``<button>`` inside a focusable ``<a>``: two tab stops with the same name,
# and interactive content nested where HTML does not allow it. Mantine's own
# escape hatch (``component="a"``) is not exposed by the dmc 2.8.0 wrapper, so
# the styling lives in ``assets/stylesheet.css`` instead.
SETUP_CARD_CTA_CLASS = "setup-card-cta"
# The card wears the shared alert anatomy on the ``dmc.Paper`` it already is.
# Blue is the informational default; the caution modifier swaps in the yellow
# tokens for the stats-folder state, which blocks every plot on the page and
# cannot be dismissed.
SETUP_CARD_CLASS = "alert-panel setup-card"
SETUP_CARD_CAUTION_CLASS = f"{SETUP_CARD_CLASS} alert-panel-caution"
SETUP_CARD_CAUTION_ICON = "material-symbols:warning-outline"
SETUP_CARD_INFO_ICON = "material-symbols:info-outline"
_INTERVAL_PROP = "interval-component.n_intervals"
_RUN_EVENTS_PROP = "run-events.data"
_SELECT_SCENARIO_PLOT_TITLE = "No scenario selected"
_SELECT_SCENARIO_PLOT_MESSAGE = "Select a scenario to see your score history."
_INCOMPLETE_GRAPH_CONTROLS_TITLE = "Graph settings incomplete"
_INCOMPLETE_GRAPH_CONTROLS_MESSAGE = (
    "Choose a Top N value and start date to plot this scenario."
)
_NO_SCENARIO_DATA_PLOT_TITLE = "No local runs found"
_NO_SCENARIO_DATA_PLOT_MESSAGE = "Play this scenario once and the graph will fill in."
_NO_DATE_RANGE_DATA_PLOT_TITLE = "No runs in this date range"
_NO_DATE_RANGE_DATA_PLOT_MESSAGE = "Choose an older start date or play more runs."
_UNSUPPORTED_GRAPH_OPTION_PLOT_TITLE = "Unsupported graph option"
_UNSUPPORTED_GRAPH_OPTION_PLOT_MESSAGE = "Choose Score vs Sensitivity or Score vs Time."
_RANK_HINT_USERNAME_UNSET = "username_unset"
_RANK_HINT_LOOKUP_FAILED = "lookup_failed"
_RANK_HINT_SERVED_STALE = "served_stale"
_STEAM_MISMATCH_NOTIFICATION_ID = "steam-id-mismatch"
# One channel for the whole refresh problem lane. The hard failure and the
# served-stale serve are mutually exclusive verdicts on the same attempt, so
# under separate ids a stale retry after a hard failure would leave both on
# screen contradicting each other about the latest click.
_RANK_REFRESH_PROBLEM_CHANNEL = "rank-refresh-problem"
# The standing condition a Refresh click can report, and its own channel: a
# repeat click reproduces byte-identical copy, which is the stacking the policy
# forbids.
_RANK_REFRESH_USERNAME_UNSET_CHANNEL = "rank-refresh-username-unset"
_RUN_IMPORT_FAILURE_NOTIFICATION_ID = "run-import-failure"
# One run, one toast: every run verdict shares this channel key, so the newest
# one replaces whatever is on screen instead of stacking. The celebration toast
# is deliberately not in this lane -- it has its own id and stays until
# dismissed.
_RUN_VERDICT_CHANNEL = "run-verdict"
_RANK_REFRESH_FAILED_TITLE = "Position refresh failed"
# Both refresh-failure paths leave the displayed value alone, so one line
# covers them: the hard failure keeps whatever was on screen, and the
# served-stale path keeps the cached position it just re-served.
_RANK_REFRESH_FAILED_MESSAGE = "Couldn't refresh — position unchanged."
_RANK_REFRESH_STALE_MESSAGE = "Couldn't refresh — showing the cached position."
# Notices that fire once per app session rather than once per trigger, by id.
# A set, so the check-and-set needs no ``global`` rebinding; sound under
# Waitress's single-process thread pool, and a lost race is benign because the
# stable id makes the loser's duplicate payload a no-op at the container.
_session_notices_sent: set[str] = set()
# What each scenario's last network-backed render concluded, as
# (displayed value, hint), so the cache-only interval path can repeat the hint
# instead of recomputing it from a read that cannot see the failure -- and can
# tell when a background writer has moved the cache on. See _rank_hint.
_last_rank_hints: dict[str, tuple[str, str | None]] = {}
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


class RunEventsPayload(TypedDict):
    """Summary passed from the batch-store consumer to Home's callbacks."""

    latest: RunEventData
    celebrated_run_id: str | None


def _settings_help_label(label: str, help_text: str) -> dmc.Group:
    return dmc.Group(
        [
            # `inherit` so the label text takes the enclosing <label>'s font
            # instead of dmc.Text's own defaults (md/400). Without it these
            # labels render 16px/400 beside the 14px/700 of every label
            # passed as a plain string.
            dmc.Text(label, span=True, inherit=True),
            dmc.Tooltip(
                dmc.ActionIcon(
                    local_icon("material-symbols:info-outline", width=16),
                    className="settings-help-icon",
                    color="gray",
                    radius="xl",
                    size="sm",
                    variant="subtle",
                    **{"aria-label": f"{label} help"},
                ),
                label=help_text,
                events=TOOLTIP_EVENTS,
                multiline=True,
                withArrow=True,
                w=SETTINGS_HELP_TOOLTIP_WIDTH,
            ),
        ],
        align="center",
        gap="xs",
        wrap="nowrap",
    )


# Rank display states deliberately map to distinct user-facing text.
def format_scenario_rank(rank_info: ScenarioRankInfo) -> str:  # noqa: PLR0911
    """Format the compact Scenario Stats rank value shown after the fixed label."""
    match rank_info.status:
        case ScenarioRankStatus.RANKED:
            if rank_info.rank is None:
                return "N/A"
            if rank_info.total_players is not None:
                if rank_info.percentile is not None:
                    return (
                        f"{rank_info.rank:,} of {rank_info.total_players:,} "
                        f"({rank_info.percentile:.2f}% Percentile)"
                    )
                return f"{rank_info.rank:,} of {rank_info.total_players:,}"
            return f"{rank_info.rank:,}"
        case ScenarioRankStatus.UNRANKED:
            if rank_info.total_players is not None:
                return f"Unranked ({rank_info.total_players:,} players)"
            return "Unranked"
        case ScenarioRankStatus.UNKNOWN:
            return "N/A"
    return "N/A"


def _summarize_run_events(
    batch: RunEventBatch,
    selected_scenario: str | None,
    automatically_change_scenario: bool,
) -> tuple[str | None, RunEventsPayload | None]:
    """Summarize one shell batch for the scenario this page should show."""
    runs = batch["runs"]
    if not runs:
        return selected_scenario, None

    target_scenario = (
        runs[-1]["scenario_name"]
        if automatically_change_scenario
        else selected_scenario
    )
    if target_scenario is None:
        return None, None

    matching_runs = [run for run in runs if run["scenario_name"] == target_scenario]
    if not matching_runs:
        return target_scenario, None

    # Coalescing, as before: several runs rebuild the plot once and only the
    # latest matching one is narrated. The drain's decision travels with it,
    # because the celebrated run may belong to another scenario entirely.
    return target_scenario, {
        "latest": matching_runs[-1],
        "celebrated_run_id": batch["celebrated_run_id"],
    }


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

    target_scenario, run_events = _summarize_run_events(
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


def _build_run_import_failure_notification(
    failures: list[str],
) -> dict[str, object]:
    """Fold a batch of failed run imports into one red toast.

    Red is earned here: the user played those runs and nothing else tells them
    the runs never landed.
    """
    message = (
        failures[0]
        if len(failures) == 1
        else (
            f"{len(failures)} new run files could not be processed. "
            "See debug.log for details."
        )
    )
    return toast(
        _RUN_IMPORT_FAILURE_NOTIFICATION_ID,
        "Run not recorded",
        message,
        color="red",
        icon=local_icon("material-symbols:warning-outline"),
    )


@callback(
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Input("interval-component", "n_intervals"),
    prevent_initial_call=True,
)
def flush_run_import_failures(_n_intervals):
    """Deliver run imports the watchdog thread could not complete.

    Home-gated, like the delivery it replaces: a missing run is a Home-visible
    fact, so the next poll tick is soon enough.
    """
    failures = drain_run_import_failures()
    if not failures:
        return no_update
    return [_build_run_import_failure_notification(failures)]


@callback(
    Output("scenario_num_runs", "children"),
    Output("last-played-ts", "data"),
    Output("last-played-empty-value", "data"),
    Output("last-played-tooltip", "label"),
    Output("scenario_datetime_last_played", "className"),
    Output("scenario_datetime_last_played", "tabIndex"),
    Output("last-played-tooltip", "disabled"),
    Input("run-events", "data"),
    Input("scenario-dropdown-selection", "value"),
)
def get_scenario_num_runs(
    _, selected_scenario
) -> tuple[int, float | None, str, str, str | None, int | None, bool]:
    """
    Updates the Scenario Stats on the UI.

    The relative "Last played" string is rendered client-side from the raw epoch
    written to the ``last-played-ts`` store. This callback owns the empty-state
    value and tooltip affordance, while a clientside callback owns the visible
    ``children``.
    :param _: trigger from the interval component. Its actual value is not used.
    :param selected_scenario: user-selected scenario name.
    :return: Scenario Stats data
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
# without a reload. Home uses the full window.* path (dagfuncs is not a bare
# global here) and the server-selected empty-state sentinel.
clientside_callback(
    """
    (seconds, emptyValue, _nIntervals) => {
        return window.dashAgGridFunctions.relativeTime(seconds, emptyValue);
    }
    """,
    Output("scenario_datetime_last_played", "children"),
    Input("last-played-ts", "data"),
    Input("last-played-empty-value", "data"),
    Input("relative-time-interval", "n_intervals"),
)


def _rank_allows_network(triggered: list[dict[str, str]]) -> bool:
    """Allow network access unless the interval is the callback's only trigger."""
    return any(trigger["prop_id"] != _INTERVAL_PROP for trigger in triggered)


def _steam_mismatch_notifications(
    rank_info: ScenarioRankInfo,
    username: str | None,
    steam_id: str | None,
) -> list[dict[str, object]]:
    """Announce a Steam-ID mismatch once per app session, persistently.

    The mismatch is a persistent condition with no in-place home, so it is the
    one passive-path toast: one per session rather than one per scenario
    switch, and it stays up until dismissed because it can fire while nobody
    is looking at the page.
    """
    if not username or _STEAM_MISMATCH_NOTIFICATION_ID in _session_notices_sent:
        return []

    warning = steam_id_mismatch_warning(username, steam_id, rank_info.matched_steam_id)
    if warning is None:
        return []

    _session_notices_sent.add(_STEAM_MISMATCH_NOTIFICATION_ID)
    logger.warning(warning)
    return [
        toast(
            _STEAM_MISMATCH_NOTIFICATION_ID,
            "Steam ID mismatch",
            warning,
            color="yellow",
            icon=local_icon("material-symbols:warning-outline"),
            auto_close=False,
        )
    ]


def _rank_hint_children(hint: str) -> list:
    """Render one inline Position hint, including its repair affordance."""
    if hint == _RANK_HINT_USERNAME_UNSET:
        return [
            " — set your KovaaK's username in ",
            dmc.Anchor("Settings", href="/settings", refresh=False),
        ]
    if hint == _RANK_HINT_LOOKUP_FAILED:
        return [" — lookup failed, Refresh to retry"]
    return [" — from cache, Refresh to update"]


def _rank_display(value: str, hint: str | None) -> str | list:
    """Pair the formatted Position value with the hint that explains it."""
    if hint is None:
        return value
    return [
        value,
        dmc.Text(
            _rank_hint_children(hint),
            className="scenario-rank-hint",
            span=True,
        ),
    ]


def _derive_rank_hint(rank_info: ScenarioRankInfo) -> str | None:
    """Classify a rank result into the inline hint its value should carry."""
    if rank_info.served_stale:
        return _RANK_HINT_SERVED_STALE
    if rank_info.error_message:
        return _RANK_HINT_LOOKUP_FAILED
    return None


def _rank_hint(
    rank_info: ScenarioRankInfo,
    username: str | None,
    selected_scenario: str,
    allow_network: bool,
    value: str,
) -> str | None:
    """Resolve the hint for a render, keeping it stable across interval ticks.

    Only the network path can tell a degraded read from a healthy one: a
    served-stale result is an ordinary cache hit by the time the cache-only
    interval re-reads it a second later. Remembering the last network verdict
    per scenario keeps the affordance on screen instead of blinking off on the
    next tick.

    The memo is tied to the value it explained, because the warmup worker and
    the score-aware refresh Timer both write the rank cache from background
    threads. When the interval reads a value the verdict was never about, the
    cache has moved on: the memo is retired rather than left claiming the
    lookup failed over a position that has since arrived.

    An unset username is visible on both paths, so it is derived rather than
    remembered and clears the moment Settings gains a name.
    """
    if not username:
        return _RANK_HINT_USERNAME_UNSET
    if allow_network:
        hint = _derive_rank_hint(rank_info)
        _last_rank_hints[selected_scenario] = (value, hint)
        return hint
    remembered = _last_rank_hints.get(selected_scenario)
    if remembered is not None:
        if remembered[0] == value:
            return remembered[1]
        # pop, not del: concurrent interval ticks for the same scenario (two
        # Home tabs on Waitress's thread pool) can pass the same read, and the
        # loser's KeyError would land outside the caller's try/except.
        _last_rank_hints.pop(selected_scenario, None)
    return _derive_rank_hint(rank_info)


def _rank_lookup_config() -> tuple[str | None, str | None, int, int, int]:
    """Return the shared rank-service arguments sourced from app configuration."""
    rank_config = get_config()
    username, steam_id = get_identity()
    return (
        username,
        steam_id,
        rank_config.scenario_metadata_cache_ttl_hours,
        rank_config.scenario_rank_cache_ttl_hours,
        rank_config.leaderboard_total_cache_ttl_hours,
    )


def _render_scenario_rank(
    selected_scenario: str | None,
    allow_network: bool,
    allow_notifications: bool = True,
) -> tuple[str | list, list[dict[str, object]]]:
    """Render rank through either the normal lookup or the cache-only interval path.

    Returns the Position value and any toast the render earned. Passive renders
    do not toast their own state: an unconfigured username, a failed lookup,
    and a value served from a stale cache are persistent conditions, so the
    field says so itself. The Steam-ID mismatch has no such in-place home and
    is the single exception.

    ``allow_notifications=False`` renders the value without spending the
    session's one mismatch toast -- for the render nobody triggered.
    """
    if not selected_scenario:
        return "N/A", []

    lookup_config = _rank_lookup_config()
    username, steam_id = lookup_config[0], lookup_config[1]
    try:
        rank_info = get_scenario_rank_info(
            selected_scenario,
            *lookup_config,
            allow_network=allow_network,
            record_activity=allow_network,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to fetch scenario rank for %s", selected_scenario)
        return _rank_display("N/A", _RANK_HINT_LOOKUP_FAILED), []

    value = format_scenario_rank(rank_info)
    display = _rank_display(
        value,
        _rank_hint(rank_info, username, selected_scenario, allow_network, value),
    )
    if not allow_notifications:
        return display, []
    return display, _steam_mismatch_notifications(rank_info, username, steam_id)


@callback(
    Output("scenario_rank", "children"),
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Input("run-events", "data"),
    Input("scenario-dropdown-selection", "value"),
    Input("interval-component", "n_intervals"),
    # Not ``True``: this callback renders the initial Position value, so the
    # page load must still run it -- but Dash refuses an ``allow_duplicate``
    # output without one of the ``prevent_initial_call`` forms.
    prevent_initial_call="initial_duplicate",
)
def get_scenario_rank(_, selected_scenario, _n_intervals):
    """Render scenario rank, keeping interval-only calls cache-only.

    Under DashProxy an ``allow_duplicate`` callback can still fire once on page
    load with nothing triggering it. The value has to render either way, but a
    fire nobody caused must not spend the session's one mismatch toast on a
    moment the user may not be looking at.
    """
    triggered = ctx.triggered
    display, notifications = _render_scenario_rank(
        selected_scenario,
        _rank_allows_network(triggered),
        allow_notifications=bool(triggered),
    )
    return display, notifications or no_update


def _rank_refresh_problem_notification(*, served_stale: bool) -> dict[str, object]:
    """Report what went wrong with the latest manual refresh.

    One channel, two flavors: the hard failure came back with nothing usable,
    the served-stale one re-served the cached position. They are the mutually
    exclusive verdicts on one attempt, so they replace each other rather than
    stacking two contradictory claims about the same click.
    """
    return toast(
        _RANK_REFRESH_PROBLEM_CHANNEL,
        _RANK_REFRESH_FAILED_TITLE,
        _RANK_REFRESH_STALE_MESSAGE if served_stale else _RANK_REFRESH_FAILED_MESSAGE,
        color="yellow" if served_stale else "red",
        icon=local_icon("material-symbols:refresh-rounded"),
    )


def _rank_refresh_success_channel(selected_scenario: str) -> str:
    """Name the success channel for one scenario.

    The scenario name goes in verbatim. Toast ids are internal -- never parsed
    back apart, never rendered -- so the identity function is the stable,
    collision-free derivation the policy asks for, and a hash would only add a
    collision it cannot have.
    """
    return f"rank-refresh-success-{selected_scenario}"


def _rank_refresh_success_notification(selected_scenario: str) -> dict[str, object]:
    """Confirm a genuinely fresh manual refresh.

    A channel per scenario: repeat refreshes of one scenario carry identical
    copy and replace each other, while refreshes of different scenarios are
    distinct facts and stack.
    """
    return toast(
        _rank_refresh_success_channel(selected_scenario),
        "Position refreshed",
        f"Refreshed position for {selected_scenario}.",
        color="green",
        icon=local_icon("material-symbols:refresh-rounded"),
    )


def _rank_refresh_username_unset_notification() -> dict[str, object]:
    """Answer a Refresh click that has no identity to look anything up with.

    Blue, not red: nothing failed and no data is degraded -- the username is
    simply not configured yet, and the title carries that verdict.
    """
    return toast(
        _RANK_REFRESH_USERNAME_UNSET_CHANNEL,
        "KovaaK's username not set",
        "Set your KovaaK's username in Settings to see your leaderboard position.",
        color="blue",
        icon=local_icon("material-symbols:refresh-rounded"),
    )


@callback(
    Output("scenario_rank", "children", allow_duplicate=True),
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Output("notification-container", "hideNotifications", allow_duplicate=True),
    Output(TOAST_CHANNEL_REGISTRY_STORE_ID, "data", allow_duplicate=True),
    Input("rank-refresh-button", "n_clicks"),
    State("scenario-dropdown-selection", "value"),
    State(TOAST_CHANNEL_REGISTRY_STORE_ID, "data"),
    # Show the button's spinner for the duration of the fetch. Mantine's
    # loading state also swallows clicks, so the button cannot be spammed
    # into repeat KovaaK's calls while one refresh is in flight.
    running=[(Output("rank-refresh-button", "loading"), True, False)],
    prevent_initial_call=True,
)
# One return per outcome the click can have -- three guards and four verdicts.
# Collapsing any pair would only hide which answer a reader is looking at.
def refresh_rank(  # noqa: PLR0911
    n_clicks,
    selected_scenario: str | None,
    toast_channels,
):
    """Fetch and display authoritative board truth after an explicit user request.

    The user asked, so every outcome answers on this callback's own
    notification output: red when the refresh failed outright, yellow when it
    failed but a cached position was served in its place, green only on a
    genuinely fresh result, and blue when there is no username to look
    anything up with.

    The unset-username case is caught before the lookup, on the direct settings
    read rather than the service's error copy. The passive field already
    explains the condition in place, but it was explaining it before the click
    too, so it cannot answer the click itself -- and a user clicking Refresh
    beside that hint plausibly clicked because they had not read it.

    A failed refresh returns ``no_update`` for the value rather than ``N/A``,
    so whatever was on screen stays put -- usually the cached position -- and
    the red toast's "position unchanged" is true either way.

    Every verdict is a channel emission, so a repeat click always re-pops its
    answer instead of being swallowed by ``show``'s dedupe. A fresh position
    also clears the two claims it falsifies: the problem channel, whose latest
    attempt just succeeded, and the unset-username channel, since a lookup that
    returned cannot have run without a username.

    Guard on ``n_clicks``: under DashProxy an ``allow_duplicate`` callback can
    fire once on initial page load despite ``prevent_initial_call``, and a
    page load must not force a network refresh or pop a stray toast.
    """
    if not n_clicks:
        return no_update, no_update, no_update, no_update
    if not selected_scenario:
        return "N/A", no_update, no_update, no_update
    if not get_kovaaks_username():
        # ``no_update``: the field already reads "N/A — set your KovaaK's
        # username in Settings", so only the toast is new.
        return no_update, *channel_toast(
            _rank_refresh_username_unset_notification(), toast_channels
        )

    try:
        rank_info = get_scenario_rank_info(
            selected_scenario,
            *_rank_lookup_config(),
            force_refresh=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Manual rank refresh failed for %s", selected_scenario)
        return no_update, *channel_toast(
            _rank_refresh_problem_notification(served_stale=False), toast_channels
        )

    if rank_info.error_message:
        # The console/file record the log bridge used to keep, kept here now.
        logger.error(
            "Manual rank refresh for %s failed: %s",
            selected_scenario,
            rank_info.error_message,
        )
        return no_update, *channel_toast(
            _rank_refresh_problem_notification(served_stale=False), toast_channels
        )

    # A manual refresh is a network verdict too, so the interval path must not
    # go on repeating what the last passive render concluded.
    rank_text = format_scenario_rank(rank_info)
    hint = _derive_rank_hint(rank_info)
    _last_rank_hints[selected_scenario] = (rank_text, hint)
    display = _rank_display(rank_text, hint)
    if rank_info.served_stale:
        logger.warning(
            "Manual rank refresh for %s served a cached position: %s",
            selected_scenario,
            rank_info.warning_message,
        )
        return display, *channel_toast(
            _rank_refresh_problem_notification(served_stale=True), toast_channels
        )
    return display, *channel_toast(
        _rank_refresh_success_notification(selected_scenario),
        toast_channels,
        clears=(
            _RANK_REFRESH_PROBLEM_CHANNEL,
            _RANK_REFRESH_USERNAME_UNSET_CHANNEL,
        ),
    )


def _run_events_were_triggered(triggered: list[dict[str, str]]) -> bool:
    """Return whether a callback invocation was caused by new run events."""
    return any(trigger["prop_id"] == _RUN_EVENTS_PROP for trigger in triggered)


def _normalize_score_threshold_percentage(
    score_threshold_percentage: float | str | None,
) -> float | None:
    """Return a usable threshold percentage, or None while the input is empty."""
    if not score_threshold_percentage:
        return None

    try:
        return float(score_threshold_percentage)
    except TypeError:
        return None
    except ValueError:
        return None


class _ThresholdVerdict(NamedTuple):
    """How a run measured up against the score threshold it was judged on."""

    passed: bool
    percentage: float
    goal_percentage: float


def _threshold_verdict(
    latest: RunEventData,
    score_threshold_percentage: float | str | None,
    score_threshold_notification_switch: bool,
) -> _ThresholdVerdict | None:
    """Judge a run against the threshold, or return None when nothing judges it.

    A run goes unjudged when the switch is off, the goal percentage is blank,
    the run is the first at its sensitivity, or the scenario has no positive
    previous best to be a percentage of -- there is no denominator, not a
    failing one. The message carries the facts and this derives the gate; the
    two used to be bundled into one nullable field that meant both.
    """
    goal_percentage = _normalize_score_threshold_percentage(score_threshold_percentage)
    scenario_previous_best = latest["scenario_previous_best"]
    if (
        not score_threshold_notification_switch
        or not goal_percentage
        or latest["is_new_sensitivity"]
        or scenario_previous_best is None
        or scenario_previous_best <= 0
    ):
        return None
    return _ThresholdVerdict(
        passed=latest["score"] >= scenario_previous_best * goal_percentage / 100,
        percentage=latest["score"] / scenario_previous_best * 100,
        goal_percentage=goal_percentage,
    )


def _placement_phrase(nth_score: int) -> str:
    """Name a top-N placement: first place is "best", the rest are "Nth-best"."""
    return "best" if nth_score == 1 else f"{ordinal(nth_score)}-best"


def _build_live_run_notification(
    latest: RunEventData,
    selected_scenario: str,
    top_n_scores: int,
    verdict: _ThresholdVerdict | None,
) -> dict[str, object] | None:
    """Build the one toast a just-played run earned, if it earned one.

    The threshold verdict is the headline whenever there is one; a top-N
    placement is the trailing detail. A run that is neither judged nor placed
    says nothing worth interrupting for -- its new point on the plot is the
    confirmation that it landed.
    """
    placed = latest["nth_score"] <= top_n_scores
    placement = (
        f"your {_placement_phrase(latest['nth_score'])} at {latest['sensitivity']}"
    )
    score = f"{selected_scenario} — {latest['score']:.2f}"

    if verdict is None:
        if not placed:
            return None
        return toast(
            _RUN_VERDICT_CHANNEL,
            f"New {_placement_phrase(latest['nth_score'])} score",
            f"{score} at {latest['sensitivity']}.",
            color="green",
            icon=local_icon("fontisto:line-chart"),
        )

    if verdict.passed:
        detail = f"Also {placement}." if placed else "Ready to move on."
        return toast(
            _RUN_VERDICT_CHANNEL,
            "Threshold passed",
            f"{score}, {verdict.percentage:.1f}% of PB. {detail}",
            color="green",
            icon=local_icon("material-symbols:check"),
        )

    shortfall = f"{score}, {verdict.percentage:.1f}% of PB — "
    shortfall += f"need {verdict.goal_percentage:.1f}%."
    if placed:
        shortfall += f" Still {placement}."
    return toast(
        _RUN_VERDICT_CHANNEL,
        "Below threshold",
        f"{shortfall} Keep grinding...",
        color="yellow",
        icon=local_icon("material-symbols:warning-outline"),
    )


def _build_run_event_notification(  # noqa: PLR0913
    run_events: RunEventsPayload | None,
    selected_scenario: str,
    top_n_scores: int,
    score_threshold_percentage: float | str | None,
    score_threshold_notification_switch: bool,
    run_notification_switch: bool,
) -> dict[str, object] | None:
    """Build the at-most-one toast this page's latest matching run earned.

    Nothing here predicts or re-derives: the drain stamped the celebration and
    each run's liveness, and this reads the stamps. The master switch is
    checked first, so it gates the whole page-built family, and the yield to
    the celebration comes second -- with celebrations reporting a run, that
    run's one notification is the celebration toast.

    A batch's other runs earn nothing: the plot is their record, which is what
    retires the "While you were away" digest.
    """
    if not run_notification_switch:
        return None
    if run_events is None or run_events["latest"]["scenario_name"] != selected_scenario:
        return None

    latest = run_events["latest"]
    if run_events["celebrated_run_id"] == latest["run_id"]:
        return None
    if not latest["is_live"]:
        return None

    verdict = _threshold_verdict(
        latest,
        score_threshold_percentage,
        score_threshold_notification_switch,
    )
    return _build_live_run_notification(
        latest,
        selected_scenario,
        top_n_scores,
        verdict,
    )


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
                "No scenario data found for (%s) for date range: %s",
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
                "No scenario data found for (%s) for date range: %s",
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
            ),
            True,
        )

    logger.error("Unsupported radio option: %s", x_axis_radiogroup)
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
        logger.warning("No scenario data found for: %s", selected_scenario)
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

    notifications = no_update
    hide_notifications = no_update
    next_toast_channels = no_update
    if supports_overlays:
        high_score = get_high_score(selected_scenario)
        if high_score_overlay_switch:
            plot = add_high_score_overlay(plot, high_score)

        score_threshold_goal_percentage = _normalize_score_threshold_percentage(
            score_threshold_percentage
        )
        if score_threshold_overlay_switch and score_threshold_goal_percentage:
            score_threshold = high_score * score_threshold_goal_percentage / 100
            plot = add_score_threshold_overlay(plot, score_threshold)

        notifications = []
        hide_notifications = []
        if _run_events_were_triggered(ctx.triggered):
            run_verdict = _build_run_event_notification(
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


@callback(
    Output("graph-content", "figure"),
    Input("color-scheme-switch", "computedColorScheme"),
    Input("cached-plot", "data"),
    Input(POINT_SIZE_INPUT_ID, "value"),
    Input(POINT_COLOR_INPUT_ID, "value"),
)
def apply_graph_appearance(color_scheme, plot_json, point_size, point_color):
    """
    Applies the theme and the Run Data Points preferences to the graph.

    Everything here is presentation over the figure ``generate_graph`` already
    built and cached, which is what keeps a size or color change from
    rereading scenario data, rebuilding overlays, or firing notifications.
    :param color_scheme: active Mantine color scheme.
    :param plot_json: json object with plotted data.
    :param point_size: selected point size preset.
    :param point_color: explicit point color, or empty for Default.
    :return: Figure with theme and point preferences applied.
    """
    if not plot_json:
        plot_json = _placeholder_plot_json()
    figure = apply_light_dark_mode(go.Figure(json.loads(plot_json)), color_scheme)
    return apply_point_appearance(figure, point_size, point_color)


@callback(
    Output(POINT_COLOR_INPUT_ID, "value"),
    Input(POINT_COLOR_DEFAULT_ID, "n_clicks"),
    prevent_initial_call=True,
)
def clear_point_color(n_clicks):
    """
    Returns the point color to Default.
    :param n_clicks: clicks on the Use default action.
    :return: the empty value that means Default.
    """
    if not n_clicks:
        return no_update
    return POINT_COLOR_DEFAULT


def _build_startup_playlist_warning_notifications(
    warnings: list[str],
) -> list[dict[str, object]]:
    """Report the playlists that did not survive the startup scan.

    Persistent, not timed: these fire once per boot, seconds after the server
    starts, which is exactly when nobody is guaranteed to be watching.
    """
    return [
        toast(
            f"startup-playlist-warning-{idx}",
            "Playlist not loaded",
            warning,
            color="yellow",
            icon=local_icon("material-symbols:warning-outline"),
            auto_close=False,
        )
        for idx, warning in enumerate(warnings)
    ]


@callback(
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Input("startup-playlist-warning-interval", "n_intervals"),
    prevent_initial_call=True,
)
def flush_startup_playlist_warnings(_):
    """Deliver import-time playlist warnings after Dash has mounted."""
    warnings = drain_startup_playlist_warnings()
    if not warnings:
        return no_update
    return _build_startup_playlist_warning_notifications(warnings)


def _chart_options_panel_class(opened: bool) -> str:
    """Return the inspector's class list for the open or collapsed state."""
    if opened:
        return CHART_OPTIONS_PANEL_CLASS
    return f"{CHART_OPTIONS_PANEL_CLASS} {CHART_OPTIONS_PANEL_HIDDEN_CLASS}"


@callback(
    Output(CHART_OPTIONS_PANEL_ID, "className"),
    Output(CHART_OPTIONS_TOGGLE_ID, "aria-expanded"),
    Input(CHART_OPTIONS_TOGGLE_ID, "n_clicks"),
    State(CHART_OPTIONS_PANEL_ID, "className"),
    prevent_initial_call=True,
)
def toggle_chart_options(n_clicks, panel_class):
    """Open or collapse the chart options inspector.

    The panel's class is the open state and ``aria-expanded`` rides with it, so
    the ``n_clicks`` guard is unconditional: the inspector starts closed on
    every visit, and under DashProxy a callback can fire once on page load with
    nothing triggering it, which would spring the panel open on arrival.
    """
    if not n_clicks:
        return no_update, no_update

    will_open = CHART_OPTIONS_PANEL_HIDDEN_CLASS in (panel_class or "")
    return _chart_options_panel_class(will_open), "true" if will_open else "false"


def _local_scenario_options() -> list:
    """List the scenarios in the stats directory, or none without a usable one."""
    stats_dir = get_usable_stats_dir()
    return get_unique_scenarios(stats_dir) if stats_dir else []


@callback(
    Output("scenario-dropdown-selection", "data"),
    Input("playlist-dropdown-selection", "value"),
)
def select_playlist(selected_playlist):
    """List scenarios for the selected playlist or all local scenarios."""
    if not selected_playlist or get_playlist_by_code(selected_playlist) is None:
        return _local_scenario_options()
    return get_scenarios_from_playlist_code(selected_playlist)


def _stats_dir_hint() -> list:
    """Say so, persistently, when the app booted without a stats directory.

    Unset and unusable read the same to the user, and both are repaired in the
    same place, so the hint carries one link to the settings page.

    A save this process has not applied yet is neither: a directory is
    configured, so claiming nothing is would tell the user the save failed. The
    hint defers to the restart instead, the same pin-versus-store
    reconciliation the settings page's notice derives from.

    What that branch must not do is confirm the save. It renders on every visit
    while the change is pending, so a user returning days later would be told
    they had just saved. It names the restart and what the restart applies, in
    the settings page's vocabulary: "the app", never "the dashboard", which a
    user reads as the browser page they would merely reload.

    That deferral is doubly narrow, because the restart copy carries no link
    and whatever it displaces has to be worth displacing. The pending change
    has to be to the *stats directory*: an identity change leaves the directory
    as unconfigured as it was, and no restart will configure it. And it has to
    leave one *set*: clearing the field is a pending change too -- rightly so
    for the settings page's notice, since this process serves the old directory
    until it restarts -- but what the restart would then apply is nothing
    configured, which is what the plain hint below already says, and it says it
    with the link.

    The plain hint is narrower still: it speaks only for a ``stats_dir`` key
    that *exists* and cannot be used -- deliberately emptied, or a stored path
    that has since vanished. A key that was never written is the never-asked
    case, which the setup card owns, so each condition is explained by exactly
    one surface instead of two stacked lines saying the same thing.
    """
    settings = get_settings()
    if get_usable_stats_dir() is not None:
        return []
    if is_stats_dir_change_pending() and settings.get(STATS_DIR_KEY):
        return [
            dmc.Text(
                "Restart the app to apply your saved settings.",
                className="stats-dir-hint",
                id="stats-dir-hint",
            )
        ]
    if STATS_DIR_KEY not in settings:
        return []
    return [
        dmc.Text(
            [
                "No stats directory configured — set it in ",
                dmc.Anchor("Settings", href="/settings", refresh=False),
            ],
            className="stats-dir-hint",
            id="stats-dir-hint",
        )
    ]


def _setup_card(
    title: str,
    body: str,
    *,
    offer_skip: bool,
    caution: bool,
) -> dmc.Paper:
    """Build one state of the setup card: a heading, a reason, and a way out.

    Navigation and dismissal only. The primary action is a link to the settings
    page, where detection and Save already live, so the card never grows a
    second detection UI and opening it costs no KovaaK's request. Skip comes
    with the fine print that says what it gives up, because a dismissal the
    user cannot interpret is worse than the question.

    The two actions are deliberately different elements: one navigates and is a
    link, the other acts on this page and is a button.

    ``caution`` picks the severity treatment rather than being read off
    ``offer_skip``: the two happen to agree today, but one is about how loud the
    card is and the other about whether it can be dismissed. It stays a
    ``dmc.Paper`` wearing the alert anatomy through CSS, because the card holds
    a link and a button and ``role="alert"`` is for text content.
    """
    actions = [
        dmc.Anchor(
            SETUP_CARD_OPEN_SETTINGS_LABEL,
            href="/settings",
            refresh=False,
            className=SETUP_CARD_CTA_CLASS,
            underline="never",
        )
    ]
    if offer_skip:
        actions.append(
            dmc.Button(
                SETUP_CARD_SKIP_LABEL,
                id=SETUP_CARD_SKIP_ID,
                # Secondary to the one action that finishes the setup.
                variant="subtle",
            )
        )
    children = [
        dmc.Group(
            [
                local_icon(
                    SETUP_CARD_CAUTION_ICON if caution else SETUP_CARD_INFO_ICON,
                    className="alert-panel-icon",
                ),
                dmc.Text(title, className="alert-panel-title"),
            ],
            gap="xs",
            align="center",
        ),
        dmc.Text(body),
        dmc.Group(actions, gap="sm"),
    ]
    if offer_skip:
        children.append(
            dmc.Text(SETUP_CARD_SKIP_FINE_PRINT, className="setup-card-fine-print")
        )
    return dmc.Paper(
        dmc.Stack(children, gap="xs"),
        className=SETUP_CARD_CAUTION_CLASS if caution else SETUP_CARD_CLASS,
        withBorder=True,
    )


def _setup_card_children() -> list:
    """Ask, once, for whatever setup the app could not do on the user's behalf.

    Read from the stored view rather than the pinned accessors, and keyed on
    key *absence*: the card is the "never asked" surface, so a key that exists
    -- with any value, ``""`` included -- retires it permanently. A degraded
    setting that does exist is explained where it bites instead, by the hints
    above and beside the values it affects.

    The missing stats directory wins when both are missing: without it the app
    has nothing to plot, so it is not dismissible and the identity ask can wait
    for a page that shows something.

    Nothing renders while a saved stats-directory change is waiting on a
    restart. The user is mid-setup, the restart hint owns that moment, and
    stacking the identity ask on top of it would be two banners for one
    unfinished action. The card comes back after the restart if identity is
    still unasked.

    Key absence only means "never asked" for a store the app can read. An
    unusable one -- a hand-edited typo, or a file stamped by a newer build --
    yields no keys either, and startup detection declines to run against it, so
    the key-absence states below would report a fresh install and a search that
    never happened. That state gets its own card, which does nothing but route
    to the Settings page, where the store alert already names the real problem
    and distinguishes the two ways a store can be unusable.
    """
    if is_stats_dir_change_pending():
        return []
    if get_settings_store_state() in (StoreState.ERROR, StoreState.FUTURE):
        return [
            _setup_card(
                SETUP_CARD_STORE_TITLE,
                SETUP_CARD_STORE_BODY,
                offer_skip=False,
                caution=True,
            )
        ]
    settings = get_settings()
    if STATS_DIR_KEY not in settings:
        return [
            _setup_card(
                SETUP_CARD_STATS_DIR_TITLE,
                SETUP_CARD_STATS_DIR_BODY,
                offer_skip=False,
                caution=True,
            )
        ]
    if KOVAAKS_USERNAME_KEY not in settings:
        return [
            _setup_card(
                SETUP_CARD_IDENTITY_TITLE,
                SETUP_CARD_IDENTITY_BODY,
                offer_skip=True,
                caution=False,
            )
        ]
    return []


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


def _home_initial_selection(
    scenario: str | None,
    playlist_code: str | None,
) -> tuple[str | None, list[str], str | None]:
    """Resolve optional Home query params into dropdown initial state."""
    selected_playlist = (
        playlist_code
        if playlist_code and get_playlist_by_code(playlist_code) is not None
        else None
    )
    scenario_options = (
        get_scenarios_from_playlist_code(selected_playlist)
        if selected_playlist
        else _local_scenario_options()
    )
    return selected_playlist, scenario_options, scenario or None


def _chart_options_group(title: str, controls: list) -> dmc.Stack:
    """Group the inspector's controls under the concept they share."""
    return dmc.Stack(
        [dmc.Title(title, order=3, size="h6"), *controls],
        gap="xs",
    )


def _chart_options_panel() -> dmc.Box:
    """Build the collapsible inspector that sits beside the chart."""
    return dmc.Box(
        id=CHART_OPTIONS_PANEL_ID,
        className=_chart_options_panel_class(False),
        children=[
            _chart_options_group(
                "Overlays",
                [
                    dmc.Switch(
                        id="rank-overlay-switch",
                        labelPosition="right",
                        label=_settings_help_label(
                            "Rank Thresholds",
                            SETTINGS_HELP_TEXT["rank-overlay"],
                        ),
                        checked=True,
                        persistence=True,
                    ),
                    dmc.Switch(
                        id="show-all-ranks-switch",
                        labelPosition="right",
                        label=_settings_help_label(
                            "Show all ranks",
                            SETTINGS_HELP_TEXT["show-all-ranks"],
                        ),
                        checked=False,
                        persistence=True,
                    ),
                    dmc.Switch(
                        id="high-score-overlay-switch",
                        labelPosition="right",
                        label=_settings_help_label(
                            "PB Score",
                            SETTINGS_HELP_TEXT["high-score-overlay"],
                        ),
                        checked=True,
                        persistence=True,
                    ),
                ],
            ),
            _chart_options_group(
                "Run Data Points",
                [
                    # SegmentedControl has no Mantine label slot, so the field
                    # carries its own and points the control at it -- the
                    # visible text is then the control's accessible name
                    # rather than a second one announced beside it.
                    dmc.Box(
                        className=CHART_OPTIONS_FIELD_CLASS,
                        children=[
                            dmc.Text(
                                "Point size",
                                id=POINT_SIZE_LABEL_ID,
                                className=CHART_OPTIONS_FIELD_LABEL_CLASS,
                            ),
                            dmc.SegmentedControl(
                                id=POINT_SIZE_INPUT_ID,
                                data=list(POINT_SIZE_OPTIONS),
                                value=POINT_SIZE_DEFAULT,
                                fullWidth=True,
                                persistence=True,
                                radius="sm",
                                size="sm",
                                **{"aria-labelledby": POINT_SIZE_LABEL_ID},
                            ),
                        ],
                    ),
                    dmc.Box(
                        className=f"{CHART_OPTIONS_FIELD_CLASS} {POINT_COLOR_FIELD_CLASS}",
                        style={
                            variable: generated_point_color(scheme)
                            for scheme, variable in POINT_COLOR_DEFAULT_CSS_VARIABLES.items()
                        },
                        children=[
                            dmc.ColorInput(
                                id=POINT_COLOR_INPUT_ID,
                                label="Point color",
                                value=POINT_COLOR_DEFAULT,
                                # An empty field is Default, and says so.
                                placeholder="Default",
                                format="hex",
                                swatches=POINT_COLOR_SWATCHES,
                                # The component defaults to seven per row,
                                # which would wrap the eighth onto a row of
                                # its own.
                                swatchesPerRow=len(POINT_COLOR_SWATCHES),
                                withEyeDropper=False,
                                # Picking a swatch is a finished choice, and
                                # the dropdown covers Use default while it
                                # is open.
                                closeOnColorSwatchClick=True,
                                persistence=True,
                                radius="sm",
                                size="sm",
                                w="100%",
                            ),
                            # The only way back to Default: the field has no
                            # clear affordance of its own, and re-typing an
                            # empty hex value is not one.
                            dmc.Group(
                                dmc.Button(
                                    "Use default",
                                    id=POINT_COLOR_DEFAULT_ID,
                                    variant="subtle",
                                    size="compact-xs",
                                ),
                                gap="xs",
                            ),
                        ],
                    ),
                ],
            ),
            _chart_options_group(
                "Score Threshold",
                [
                    dmc.Switch(
                        id="score-threshold-overlay-switch",
                        labelPosition="right",
                        label=_settings_help_label(
                            "Score Threshold Overlay",
                            SETTINGS_HELP_TEXT["score-threshold-overlay"],
                        ),
                        checked=True,
                        persistence=True,
                    ),
                    dmc.NumberInput(
                        id="score-threshold-percentage",
                        label=_settings_help_label(
                            "Score Threshold Percentage",
                            SETTINGS_HELP_TEXT["score-threshold-percentage"],
                        ),
                        min=1,
                        persistence=True,
                        placeholder="Score Percentage...",
                        radius="sm",
                        size="sm",
                        variant="default",
                        value=95,
                        # Fills the rail. A Mantine label is only as wide as
                        # its input, so the modal's 12em box would wrap this
                        # label and strand its help icon on the line above.
                        w="100%",
                    ),
                    # Stays in this group, beside the percentage it judges
                    # against, even though the master switch it depends on
                    # lives in Notifications.
                    dmc.Switch(
                        id="score-threshold-notification-switch",
                        labelPosition="right",
                        label=_settings_help_label(
                            "Score Threshold Verdict",
                            SETTINGS_HELP_TEXT["score-threshold-notification"],
                        ),
                        checked=True,
                        persistence=True,
                    ),
                ],
            ),
            _chart_options_group(
                "Notifications",
                [
                    dmc.Switch(
                        id="run-notification-switch",
                        labelPosition="right",
                        label=_settings_help_label(
                            "Run Notifications",
                            SETTINGS_HELP_TEXT["run-notification"],
                        ),
                        checked=True,
                        persistence=True,
                    ),
                ],
            ),
        ],
    )


def _chart_options_toggle() -> dmc.Button:
    """Build the disclosure button that opens and collapses the inspector."""
    return dmc.Button(
        "Chart options",
        id=CHART_OPTIONS_TOGGLE_ID,
        variant="default",
        rightSection=local_icon(
            "material-symbols:keyboard-arrow-down",
            className="chart-options-toggle-chevron",
            width=20,
        ),
        **{"aria-controls": CHART_OPTIONS_PANEL_ID, "aria-expanded": "false"},
    )


# Add Dash Mantine Component figure templates to Plotly's templates.
dmc.add_figure_templates()


# Per Dash documentation, we should include **kwargs in case the layout receives unexpected query strings.
def layout(
    scenario: str | None = None,
    playlist_code: str | None = None,
    **_kwargs,
):
    """Build the interactive home dashboard."""
    config = get_config()
    selected_playlist, scenario_options, selected_scenario = _home_initial_selection(
        scenario,
        playlist_code,
    )
    playlist_persistence = playlist_code is None
    scenario_persistence = scenario is None

    return dmc.Box(
        className="home-page",
        children=[
            dcc.Store(id="run-events"),
            dcc.Store(
                id="cached-plot",
                data=_placeholder_plot_json(),
            ),  # caches the plot for easy light/dark mode
            dcc.Store(
                id="last-played-ts"
            ),  # raw epoch for the relative "Last played" text
            dcc.Store(
                id="last-played-empty-value",
                data="",
            ),
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
            *_stats_dir_hint(),
            dmc.Box(id=SETUP_CARD_ID, children=_setup_card_children()),
            dmc.Grid(
                children=[
                    dmc.GridCol(
                        dmc.Flex(
                            children=[
                                dmc.Select(
                                    **PLAYLIST_SELECTOR_PRESET,
                                    allowDeselect=False,
                                    autoSelectOnBlur=True,
                                    clearSearchOnFocus=True,
                                    clearable=True,
                                    data=get_visible_playlist_selector_options(),
                                    id="playlist-dropdown-selection",
                                    label="Playlist filter",
                                    persistence=playlist_persistence,
                                    value=selected_playlist,
                                ),
                                dmc.Stack(
                                    [
                                        dmc.Select(
                                            allowDeselect=False,
                                            autoSelectOnBlur=True,
                                            checkIconPosition="right",
                                            clearSearchOnFocus=True,
                                            data=scenario_options,
                                            id="scenario-dropdown-selection",
                                            label="Selected scenario",
                                            maxDropdownHeight="75vh",
                                            persistence=scenario_persistence,
                                            placeholder="Select a scenario...",
                                            scrollAreaProps={"type": "auto"},
                                            searchable=True,
                                            value=selected_scenario,
                                        ),
                                        # Selection behavior, not chart
                                        # presentation: it decides what the
                                        # selector does when a new run lands,
                                        # so it sits under the selector rather
                                        # than in the chart options inspector.
                                        dmc.Switch(
                                            id="automatically-change-scenario-switch",
                                            labelPosition="right",
                                            label=_settings_help_label(
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
                                    # see PLAYLIST_SELECTOR_PRESET for why the
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
                                    label=_settings_help_label(
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
                                dmc.Box(
                                    [
                                        dmc.Title(
                                            "Scenario Stats",
                                            order=2,
                                            size="h6",
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
                                                        id="scenario_datetime_last_played",
                                                        span=True,
                                                        size="sm",
                                                    ),
                                                    disabled=True,
                                                    events=TOOLTIP_EVENTS,
                                                    id="last-played-tooltip",
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
                                                    id="scenario_num_runs",
                                                    span=True,
                                                ),
                                            ],
                                            size="sm",
                                        ),
                                        dmc.Group(
                                            [
                                                dmc.Group(
                                                    [
                                                        dmc.Text(
                                                            "Position:",
                                                            fw=700,
                                                            span=True,
                                                            size="sm",
                                                        ),
                                                        # dcc.Loading renders
                                                        # divs, which cannot
                                                        # nest inside a Text's
                                                        # default <p> root, so
                                                        # it sits beside the
                                                        # label in a Group
                                                        # (like "Last played:"
                                                        # above).
                                                        dcc.Loading(
                                                            dmc.Text(
                                                                id="scenario_rank",
                                                                span=True,
                                                                size="sm",
                                                            ),
                                                            delay_show=SCENARIO_RANK_LOADING_DELAY_MS,
                                                            show_initially=False,
                                                        ),
                                                    ],
                                                    gap="0.25em",
                                                ),
                                                dmc.Tooltip(
                                                    dmc.Button(
                                                        "Refresh",
                                                        id="rank-refresh-button",
                                                        variant="subtle",
                                                        size="compact-xs",
                                                        leftSection=local_icon(
                                                            "material-symbols:refresh-rounded",
                                                            width=14,
                                                        ),
                                                    ),
                                                    label=RANK_REFRESH_TOOLTIP,
                                                    events=TOOLTIP_EVENTS,
                                                    multiline=True,
                                                    withArrow=True,
                                                    w=SETTINGS_HELP_TOOLTIP_WIDTH,
                                                ),
                                            ],
                                            gap="xs",
                                            align="center",
                                        ),
                                    ],
                                    w=300,
                                    maw="100%",
                                ),
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
                                _chart_options_toggle(),
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
                        _chart_options_panel(),
                    ],
                ),
            ),
        ],
    )
