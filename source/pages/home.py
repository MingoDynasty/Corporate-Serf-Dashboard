"""Build the dashboard home page and its interactive callbacks."""

import json
import logging
import uuid
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

from source.components.local_icon import local_icon
from source.config.config_service import get_config
from source.config.settings_service import (
    STATS_DIR_KEY,
    get_identity,
    get_settings,
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
from source.my_queue.message_queue import NewFileMessage, message_queue
from source.my_watchdog.file_watchdog import drain_run_import_failures
from source.pages.playlist_selector import PLAYLIST_SELECTOR_PRESET
from source.plot.plot_service import (
    add_high_score_overlay,
    add_score_threshold_overlay,
    apply_light_dark_mode,
    generate_empty_plot,
    generate_placeholder_plot,
    generate_sensitivity_plot,
    generate_time_plot,
)
from source.utilities.notifications import (
    TOAST_LIFETIME_STORE_ID,
    toast,
    upsert_toast,
)
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
        "Notifies after each new run whether it reached the score threshold."
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
_RANK_REFRESH_FAILED_NOTIFICATION_ID = "rank-refresh-failed"
_RANK_REFRESH_STALE_NOTIFICATION_ID = "rank-refresh-stale"
_RUN_IMPORT_FAILURE_NOTIFICATION_ID = "run-import-failure"
# One run, one toast: every run verdict and the catch-up digest share this id,
# so the newest verdict replaces whatever is on screen instead of stacking.
_RUN_VERDICT_NOTIFICATION_ID = "run-verdict"
_BACKLOG_NOTIFICATION_TITLE = "While you were away"
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
    title="Scenario Performance",
    redirect_from=["/home", "/index"],
)


def _empty_plot_json(title: str, message: str) -> str:
    """Serialize an empty-state graph for the cached plot store."""
    return generate_empty_plot(title, message).to_json()


def _placeholder_plot_json() -> str:
    """Serialize the neutral pre-hydration graph placeholder."""
    return generate_placeholder_plot().to_json()


class RunEventData(TypedDict):
    """JSON-safe fields from the latest run event in a drained batch."""

    scenario_name: str
    sensitivity: str
    nth_score: int
    score: float
    previous_high_score: float | None


class RunEventsPayload(TypedDict):
    """Summary passed from the queue consumer to Home's other callbacks."""

    count: int
    latest: RunEventData


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


def _drain_run_events(
    selected_scenario: str | None,
    automatically_change_scenario: bool,
) -> tuple[str | None, RunEventsPayload | None]:
    """Drain pending run messages and summarize the landing scenario."""
    drained: list[NewFileMessage] = []
    while True:
        try:
            drained.append(message_queue.popleft())
        except IndexError:
            break

    if not drained:
        return selected_scenario, None

    target_scenario = (
        drained[-1].scenario_name
        if automatically_change_scenario
        else selected_scenario
    )
    if target_scenario is None:
        return None, None

    matching_messages = [
        message for message in drained if message.scenario_name == target_scenario
    ]
    if not matching_messages:
        return target_scenario, None

    latest = matching_messages[-1]
    return target_scenario, {
        "count": len(matching_messages),
        "latest": {
            "scenario_name": latest.scenario_name,
            "sensitivity": latest.sensitivity,
            "nth_score": latest.nth_score,
            "score": latest.score,
            "previous_high_score": latest.previous_high_score,
        },
    }


@callback(
    Output("run-events", "data"),
    Output("scenario-dropdown-selection", "value"),
    Input("interval-component", "n_intervals"),
    Input("automatically-change-scenario-switch", "checked"),
    Input("scenario-dropdown-selection", "value"),
    prevent_initial_call=True,
)
def check_for_new_data(_, automatically_change_scenario, selected_scenario):
    """Drain pending run events and forward one summary to Home callbacks."""
    target_scenario, run_events = _drain_run_events(
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


def _rank_refresh_failed_notification() -> dict[str, object]:
    """Report a manual refresh that came back with nothing usable."""
    return toast(
        _RANK_REFRESH_FAILED_NOTIFICATION_ID,
        _RANK_REFRESH_FAILED_TITLE,
        _RANK_REFRESH_FAILED_MESSAGE,
        color="red",
        icon=local_icon("material-symbols:refresh-rounded"),
    )


def _rank_refresh_success_notification(selected_scenario: str) -> dict[str, object]:
    """Confirm a genuinely fresh manual refresh.

    Fresh id per refresh: ``show`` silently ignores a duplicate id while the
    previous toast is still visible, which would eat the "done" cue on
    back-to-back refreshes.
    """
    return toast(
        f"rank-refresh-notification-{uuid.uuid4()}",
        "Position refreshed",
        f"Refreshed position for {selected_scenario}.",
        color="green",
        icon=local_icon("material-symbols:refresh-rounded"),
    )


@callback(
    Output("scenario_rank", "children", allow_duplicate=True),
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Input("rank-refresh-button", "n_clicks"),
    State("scenario-dropdown-selection", "value"),
    # Show the button's spinner for the duration of the fetch. Mantine's
    # loading state also swallows clicks, so the button cannot be spammed
    # into repeat KovaaK's calls while one refresh is in flight.
    running=[(Output("rank-refresh-button", "loading"), True, False)],
    prevent_initial_call=True,
)
def refresh_rank(n_clicks, selected_scenario: str | None):
    """Fetch and display authoritative board truth after an explicit user request.

    The user asked, so every outcome answers on this callback's own
    notification output: red when the refresh failed outright, yellow when it
    failed but a cached position was served in its place, green only on a
    genuinely fresh result.

    A failed refresh returns ``no_update`` for the value rather than ``N/A``,
    so whatever was on screen stays put -- usually the cached position -- and
    the red toast's "position unchanged" is true either way.

    Guard on ``n_clicks``: under DashProxy an ``allow_duplicate`` callback can
    fire once on initial page load despite ``prevent_initial_call``, and a
    page load must not force a network refresh or pop a stray toast.
    """
    if not n_clicks:
        return no_update, no_update
    if not selected_scenario:
        return "N/A", no_update

    try:
        rank_info = get_scenario_rank_info(
            selected_scenario,
            *_rank_lookup_config(),
            force_refresh=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Manual rank refresh failed for %s", selected_scenario)
        return no_update, [_rank_refresh_failed_notification()]

    if rank_info.error_message:
        # The console/file record the log bridge used to keep, kept here now.
        logger.error(
            "Manual rank refresh for %s failed: %s",
            selected_scenario,
            rank_info.error_message,
        )
        return no_update, [_rank_refresh_failed_notification()]

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
        return display, [
            toast(
                _RANK_REFRESH_STALE_NOTIFICATION_ID,
                _RANK_REFRESH_FAILED_TITLE,
                _RANK_REFRESH_STALE_MESSAGE,
                color="yellow",
                icon=local_icon("material-symbols:refresh-rounded"),
            )
        ]
    return display, [_rank_refresh_success_notification(selected_scenario)]


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
    or the scenario/sensitivity has no previous high score to be a percentage
    of -- there is no denominator, not a failing one.
    """
    goal_percentage = _normalize_score_threshold_percentage(score_threshold_percentage)
    previous_high_score = latest["previous_high_score"]
    if (
        not score_threshold_notification_switch
        or not goal_percentage
        or previous_high_score is None
        or previous_high_score <= 0
    ):
        return None
    return _ThresholdVerdict(
        passed=latest["score"] >= previous_high_score * goal_percentage / 100,
        percentage=latest["score"] / previous_high_score * 100,
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
            _RUN_VERDICT_NOTIFICATION_ID,
            f"New {_placement_phrase(latest['nth_score'])} score",
            f"{score} at {latest['sensitivity']}.",
            color="green",
            icon=local_icon("fontisto:line-chart"),
        )

    if verdict.passed:
        detail = f"Also {placement}." if placed else "Ready to move on."
        return toast(
            _RUN_VERDICT_NOTIFICATION_ID,
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
        _RUN_VERDICT_NOTIFICATION_ID,
        "Below threshold",
        f"{shortfall} Keep grinding...",
        color="yellow",
        icon=local_icon("material-symbols:warning-outline"),
    )


def _build_backlog_notification(
    run_events: RunEventsPayload,
    selected_scenario: str,
    verdict: _ThresholdVerdict | None,
) -> dict[str, object]:
    """Summarize runs that accrued while Home was closed.

    Shares the live run's id, so playing again replaces this digest with the
    fresher verdict rather than stacking beside it.
    """
    latest = run_events["latest"]
    summary = (
        f"{run_events['count']} new {selected_scenario} runs. "
        f"Latest: {latest['score']:.2f}"
    )
    if verdict is None:
        return toast(
            _RUN_VERDICT_NOTIFICATION_ID,
            _BACKLOG_NOTIFICATION_TITLE,
            f"{summary} at {latest['sensitivity']}.",
            color="blue",
            icon=local_icon("fontisto:line-chart"),
        )
    if verdict.passed:
        return toast(
            _RUN_VERDICT_NOTIFICATION_ID,
            _BACKLOG_NOTIFICATION_TITLE,
            f"{summary} — {verdict.percentage:.1f}% of PB, passed threshold.",
            color="green",
            icon=local_icon("material-symbols:check"),
        )
    return toast(
        _RUN_VERDICT_NOTIFICATION_ID,
        _BACKLOG_NOTIFICATION_TITLE,
        f"{summary} — {verdict.percentage:.1f}% of PB, below the "
        f"{verdict.goal_percentage:.1f}% threshold.",
        color="yellow",
        icon=local_icon("material-symbols:warning-outline"),
    )


def _build_run_event_notification(
    run_events: RunEventsPayload | None,
    selected_scenario: str,
    top_n_scores: int,
    score_threshold_percentage: float | str | None,
    score_threshold_notification_switch: bool,
) -> dict[str, object] | None:
    """Build the at-most-one toast a batch of run events earned."""
    if run_events is None or run_events["latest"]["scenario_name"] != selected_scenario:
        return None

    latest = run_events["latest"]
    verdict = _threshold_verdict(
        latest,
        score_threshold_percentage,
        score_threshold_notification_switch,
    )
    if run_events["count"] > 1:
        return _build_backlog_notification(run_events, selected_scenario, verdict)
    return _build_live_run_notification(
        latest,
        selected_scenario,
        top_n_scores,
        verdict,
    )


def _empty_state_graph_response(title: str, message: str) -> tuple[str, object, object]:
    """Return a cached empty-state plot with notifications left unchanged."""
    return _empty_plot_json(title, message), no_update, no_update


def _build_scenario_figure(  # noqa: PLR0913
    x_axis_radiogroup: str,
    selected_scenario: str,
    top_n_scores: int,
    oldest_datetime: datetime,
    rank_overlay_switch: bool,
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
    Output(TOAST_LIFETIME_STORE_ID, "data"),
    Input("run-events", "data"),
    Input("scenario-dropdown-selection", "value"),
    Input("top_n_scores", "value"),
    Input("date-picker", "value"),
    Input("x-axis-radiogroup", "value"),
    Input("rank-overlay-switch", "checked"),
    Input("high-score-overlay-switch", "checked"),
    Input("score-threshold-overlay-switch", "checked"),
    Input("score-threshold-percentage", "value"),
    Input("score-threshold-notification-switch", "checked"),
    State("playlist-dropdown-selection", "value"),
    State(TOAST_LIFETIME_STORE_ID, "data"),
)
# This callback coordinates the page's graph controls and notification states.
def generate_graph(  # noqa: PLR0913
    run_events,
    selected_scenario,
    top_n_scores,
    selected_date,
    x_axis_radiogroup,
    rank_overlay_switch,
    high_score_overlay_switch,
    score_threshold_overlay_switch,
    score_threshold_percentage,
    score_threshold_notification_switch,
    selected_playlist,
    toast_lifetime_sequence,
):
    """
    Updates to the graph.
    :param run_events: summary of newly ingested runs, when this invocation has one.
    :param selected_scenario: user-selected scenario name.
    :param top_n_scores: user-selected top n scores.
    :param selected_date: user-selected date.
    :param x_axis_radiogroup: user-selected x-axis radio group.
    :param rank_overlay_switch: rank overlay switch. True=show rank overlay.
    :param selected_playlist: user-selected playlist code.
    :param toast_lifetime_sequence: this client's run-verdict emission counter.
    :return: Figure serialized to JSON, Notification, next emission counter
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
        selected_playlist,
    )

    notifications = no_update
    next_toast_lifetime_sequence = no_update
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
        if _run_events_were_triggered(ctx.triggered):
            run_verdict = _build_run_event_notification(
                run_events,
                selected_scenario,
                top_n_scores,
                score_threshold_percentage,
                score_threshold_notification_switch,
            )
            if run_verdict is not None:
                notifications = upsert_toast(run_verdict, toast_lifetime_sequence)
                next_toast_lifetime_sequence = (toast_lifetime_sequence or 0) + 1
    return plot.to_json(), notifications, next_toast_lifetime_sequence


@callback(
    Output("graph-content", "figure"),
    Input("color-scheme-switch", "computedColorScheme"),
    Input("cached-plot", "data"),
)
def apply_light_dark_theme_to_graph(color_scheme, plot_json):
    """
    Applies the light or dark theme to the graph.
    :param color_scheme: active Mantine color scheme.
    :param plot_json: json object with plotted data.
    :return: Figure with theme applied.
    """
    if not plot_json:
        plot_json = _placeholder_plot_json()
    return apply_light_dark_mode(go.Figure(json.loads(plot_json)), color_scheme)


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

    A save this process has not applied yet is neither: the settings page just
    confirmed the save, so claiming nothing is configured would tell the user
    it failed. The hint defers to the restart instead, the same pin-versus-store
    reconciliation the settings page's notice derives from.

    That deferral is doubly narrow, because the restart copy carries no link
    and whatever it displaces has to be worth displacing. The pending change
    has to be to the *stats directory*: an identity change leaves the directory
    as unconfigured as it was, and no restart will configure it. And it has to
    leave one *set*: clearing the field is a pending change too -- rightly so
    for the settings page's notice, since this process serves the old directory
    until it restarts -- but what the restart would then apply is nothing
    configured, which is what the plain hint below already says, and it says it
    with the link.
    """
    if get_usable_stats_dir() is not None:
        return []
    if is_stats_dir_change_pending() and get_settings().get(STATS_DIR_KEY):
        return [
            dmc.Text(
                "Settings saved — restart the dashboard to apply them.",
                className="stats-dir-hint",
                id="stats-dir-hint",
            )
        ]
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
                    # The modal's wording, kept for now (2026-08-08): it reads
                    # as though it gates run notifications wholesale, when
                    # since the notification redesign it decides only whether
                    # a run is judged against the threshold -- placement
                    # toasts fire either way. Revisit with the rest of the
                    # group's copy.
                    dmc.Switch(
                        id="score-threshold-notification-switch",
                        labelPosition="right",
                        label=_settings_help_label(
                            "Score Threshold Notification",
                            SETTINGS_HELP_TEXT["score-threshold-notification"],
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
