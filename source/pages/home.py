"""Build the dashboard home page and its interactive callbacks."""

import json
import logging
from datetime import datetime
from typing import TypedDict

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
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from source.kovaaks.api_service import get_scenario_rank_info
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
from source.plot.plot_service import (
    add_high_score_overlay,
    add_score_threshold_overlay,
    apply_light_dark_mode,
    generate_empty_plot,
    generate_sensitivity_plot,
    generate_time_plot,
)
from source.utilities.dash_logging import get_dash_logger
from source.utilities.utilities import format_absolute_timestamp, ordinal

logger = logging.getLogger(__name__)
dash_logger = get_dash_logger(__name__)
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
        "Notifies after each new run whether the score reached the score threshold."
    ),
}
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
dash.register_page(
    __name__,
    path="/",
    title="Corporate Serf Dashboard",
    redirect_from=["/home", "/index"],
)


def _empty_plot_json(title: str, message: str) -> str:
    """Serialize an empty-state graph for the cached plot store."""
    return generate_empty_plot(title, message).to_json()


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
            dmc.Text(label, span=True),
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
        "last-played-affordance",
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


def _emit_rank_messages(rank_info: ScenarioRankInfo) -> None:
    """Surface rank warnings and errors through the dashboard notification logger."""
    if rank_info.warning_message:
        logger.warning("Scenario rank warning: %s", rank_info.warning_message)
        dash_logger.warning(rank_info.warning_message)
    if rank_info.error_message:
        logger.warning("Scenario rank unavailable: %s", rank_info.error_message)
        dash_logger.error(rank_info.error_message)


def _rank_lookup_config() -> tuple[str | None, str | None, int, int, int]:
    """Return the shared rank-service arguments sourced from app configuration."""
    rank_config = get_config()
    return (
        rank_config.kovaaks_username,
        rank_config.steam_id,
        rank_config.scenario_metadata_cache_ttl_hours,
        rank_config.scenario_rank_cache_ttl_hours,
        rank_config.leaderboard_total_cache_ttl_hours,
    )


def _render_scenario_rank(selected_scenario: str | None, allow_network: bool) -> str:
    """Render rank through either the normal lookup or the cache-only interval path."""
    if not selected_scenario:
        return "N/A"

    try:
        rank_info = get_scenario_rank_info(
            selected_scenario,
            *_rank_lookup_config(),
            allow_network=allow_network,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to fetch scenario rank for %s", selected_scenario)
        return "N/A"

    if allow_network:
        _emit_rank_messages(rank_info)
    return format_scenario_rank(rank_info)


@callback(
    Output("scenario_rank", "children"),
    Input("run-events", "data"),
    Input("scenario-dropdown-selection", "value"),
    Input("interval-component", "n_intervals"),
)
def get_scenario_rank(_, selected_scenario, _n_intervals) -> str:
    """Render scenario rank, keeping interval-only calls cache-only."""
    return _render_scenario_rank(
        selected_scenario,
        _rank_allows_network(ctx.triggered),
    )


@callback(
    Output("scenario_rank", "children", allow_duplicate=True),
    Input("rank-refresh-button", "n_clicks"),
    State("scenario-dropdown-selection", "value"),
    prevent_initial_call=True,
)
def refresh_rank(_, selected_scenario: str | None) -> str:
    """Fetch and display authoritative board truth after an explicit user request."""
    if not selected_scenario:
        return "N/A"

    try:
        rank_info = get_scenario_rank_info(
            selected_scenario,
            *_rank_lookup_config(),
            force_refresh=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Manual rank refresh failed for %s", selected_scenario)
        dash_logger.error("Position refresh for %s failed.", selected_scenario)
        return "N/A"

    _emit_rank_messages(rank_info)
    return format_scenario_rank(rank_info)


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


def _build_run_event_notifications(
    run_events: RunEventsPayload | None,
    selected_scenario: str,
    top_n_scores: int,
    score_threshold_percentage: float | str | None,
    score_threshold_notification_switch: bool,
) -> list[dict[str, object]]:
    """Build either the legacy single-run toasts or one backlog summary."""
    if run_events is None or run_events["latest"]["scenario_name"] != selected_scenario:
        return []

    score_threshold_goal_percentage = _normalize_score_threshold_percentage(
        score_threshold_percentage
    )
    latest = run_events["latest"]
    if run_events["count"] > 1:
        message = (
            f"{run_events['count']} new {selected_scenario} runs while you were away. "
            f"Latest: {latest['sensitivity']} has a new "
            f"{ordinal(latest['nth_score'])} place score: {latest['score']:.2f}."
        )
        color = "blue"
        if (
            score_threshold_notification_switch
            and score_threshold_goal_percentage
            and latest["previous_high_score"] is not None
            and latest["previous_high_score"] > 0
        ):
            percentage = latest["score"] / latest["previous_high_score"] * 100
            if (
                latest["score"]
                >= latest["previous_high_score"] * score_threshold_goal_percentage / 100
            ):
                message += (
                    f" Current score percentage ({percentage:.1f}%) successfully "
                    "passed the score threshold! Ready to move onto the next scenario."
                )
                color = "green"
            else:
                message += (
                    f" Current score percentage ({percentage:.1f}%) failed to meet "
                    "the score threshold. Keep grinding..."
                )
                color = "yellow"
        return [
            {
                "action": "show",
                "title": "Run Summary",
                "message": message,
                "color": color,
                "id": "run-summary-notification",
                "icon": local_icon("fontisto:line-chart"),
                "autoClose": 8000,
            }
        ]

    notifications: list[dict[str, object]] = []
    if latest["nth_score"] <= top_n_scores:
        notification_message = (
            f"{latest['sensitivity']} has a new "
            f"{ordinal(latest['nth_score'])} place score: {latest['score']:.2f}"
        )
        notifications.append(
            {
                "action": "show",
                "title": "Notification",
                "message": notification_message,
                "color": "green",
                "id": "new-top-n-score-notification",
                "icon": local_icon("fontisto:line-chart"),
                "autoClose": 8000,
            }
        )

    if (
        score_threshold_notification_switch
        and score_threshold_goal_percentage
        and latest["previous_high_score"] is not None
        and latest["previous_high_score"] > 0
    ):
        percentage = latest["score"] / latest["previous_high_score"] * 100
        if (
            latest["score"]
            >= latest["previous_high_score"] * score_threshold_goal_percentage / 100
        ):
            notifications.append(
                {
                    "action": "show",
                    "title": "Score Threshold",
                    "message": (
                        f"Current score percentage ({percentage:.1f}%) "
                        "successfully passed the score threshold! Ready to "
                        "move onto the next scenario."
                    ),
                    "color": "green",
                    "id": "score-threshold-notification",
                    "icon": local_icon("material-symbols:check"),
                    "autoClose": 8000,
                }
            )
        else:
            notifications.append(
                {
                    "action": "show",
                    "title": "Score Threshold",
                    "message": (
                        f"Current score percentage ({percentage:.1f}%) "
                        "failed to meet the score threshold. Keep grinding..."
                    ),
                    "color": "yellow",
                    "id": "score-threshold-notification",
                    "icon": local_icon("material-symbols:warning-outline"),
                    "autoClose": 8000,
                }
            )
    else:
        notifications.append(
            {
                "action": "show",
                "title": "Notification",
                "message": "Graph updated!",
                "color": "blue",
                "id": "graph-updated-notification",
                "icon": local_icon("material-symbols:refresh-rounded"),
            }
        )
    return notifications


def _empty_state_graph_response(title: str, message: str) -> tuple[str, object]:
    """Return a cached empty-state plot with notifications left unchanged."""
    return _empty_plot_json(title, message), no_update


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
            dash_logger.warning("No scenario data for the given date range.")
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
            dash_logger.warning("No scenario data for the given date range.")
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
    :return: Figure serialized to JSON, Notification
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
        dash_logger.warning("No scenario data found.")
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
            notifications = _build_run_event_notifications(
                run_events,
                selected_scenario,
                top_n_scores,
                score_threshold_percentage,
                score_threshold_notification_switch,
            )
    return plot.to_json(), notifications


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
        plot_json = _empty_plot_json(
            _SELECT_SCENARIO_PLOT_TITLE,
            _SELECT_SCENARIO_PLOT_MESSAGE,
        )
    return apply_light_dark_mode(go.Figure(json.loads(plot_json)), color_scheme)


def _build_startup_playlist_warning_notifications(
    warnings: list[str],
) -> list[dict[str, object]]:
    return [
        {
            "action": "show",
            "title": "Playlist Warning",
            "message": warning,
            "color": "yellow",
            "id": f"startup-playlist-warning-{idx}",
            "icon": local_icon("material-symbols:warning-outline"),
            "autoClose": 10000,
        }
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


@callback(
    Output("settings-modal", "opened"),
    Input("settings-modal-open-button", "n_clicks"),
    State("settings-modal", "opened"),
    prevent_initial_call=True,
)
def modal_demo(_, opened):
    """This function simply handles opening/closing the Settings modal."""
    return not opened


@callback(
    Output("scenario-dropdown-selection", "data"),
    Input("playlist-dropdown-selection", "value"),
)
def select_playlist(selected_playlist):
    """List scenarios for the selected playlist or all local scenarios."""
    if not selected_playlist or get_playlist_by_code(selected_playlist) is None:
        return get_unique_scenarios(get_config().stats_dir)
    return get_scenarios_from_playlist_code(selected_playlist)


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
        else get_unique_scenarios(get_config().stats_dir)
    )
    return selected_playlist, scenario_options, scenario or None


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
        children=[
            dcc.Store(id="run-events"),
            dcc.Store(
                id="cached-plot",
                data=_empty_plot_json(
                    _SELECT_SCENARIO_PLOT_TITLE,
                    _SELECT_SCENARIO_PLOT_MESSAGE,
                ),
            ),  # caches the plot for easy light/dark mode
            dcc.Store(
                id="last-played-ts"
            ),  # raw epoch for the relative "Last played" text
            dcc.Store(
                id="last-played-empty-value",
                data="—",
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
            dmc.Grid(
                children=[
                    dmc.GridCol(
                        dmc.Flex(
                            children=[
                                dmc.Select(
                                    allowDeselect=False,
                                    autoSelectOnBlur=True,
                                    checkIconPosition="right",
                                    clearSearchOnFocus=True,
                                    clearable=True,
                                    data=get_visible_playlist_selector_options(),
                                    id="playlist-dropdown-selection",
                                    label="Playlist filter",
                                    maxDropdownHeight="75vh",
                                    miw=400,
                                    ml="xl",
                                    persistence=playlist_persistence,
                                    placeholder="Select a playlist...",
                                    scrollAreaProps={"type": "always"},
                                    searchable=True,
                                    value=selected_playlist,
                                ),
                                dmc.Select(
                                    allowDeselect=False,
                                    autoSelectOnBlur=True,
                                    checkIconPosition="right",
                                    clearSearchOnFocus=True,
                                    data=scenario_options,
                                    id="scenario-dropdown-selection",
                                    label="Selected scenario",
                                    maxDropdownHeight="75vh",
                                    miw=400,
                                    persistence=scenario_persistence,
                                    placeholder="Select a scenario...",
                                    scrollAreaProps={"type": "auto"},
                                    searchable=True,
                                    value=selected_scenario,
                                ),
                                dmc.Space(h="xl"),
                                dmc.Space(h="xl"),
                                dmc.NumberInput(
                                    id="top_n_scores",
                                    label="Top N scores",
                                    min=1,
                                    persistence=True,
                                    placeholder="Top N scores to consider...",
                                    radius="sm",
                                    size="sm",
                                    variant="default",
                                    value=5,
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
                                                        "—",
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
                                                dmc.Text(
                                                    [
                                                        dmc.Text(
                                                            "Position: ",
                                                            fw=700,
                                                            span=True,
                                                        ),
                                                        dcc.Loading(
                                                            dmc.Text(
                                                                id="scenario_rank",
                                                                span=True,
                                                            ),
                                                            delay_show=SCENARIO_RANK_LOADING_DELAY_MS,
                                                            show_initially=False,
                                                            parent_style={
                                                                "display": "inline-block",
                                                                "verticalAlign": "baseline",
                                                            },
                                                            style={
                                                                "display": "inline-block",
                                                            },
                                                        ),
                                                    ],
                                                    size="sm",
                                                ),
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
                                            ],
                                            gap="xs",
                                            align="center",
                                        ),
                                    ],
                                    w=300,
                                ),
                            ],
                            gap="md",
                            justify="flex-start",
                            align="flex-start",
                            direction="row",
                            wrap="wrap",
                        ),
                        span=10,
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
                                dmc.Tooltip(
                                    dmc.Button(
                                        "Settings",
                                        id="settings-modal-open-button",
                                        variant="default",
                                        leftSection=local_icon(
                                            "clarity:settings-line",
                                            width=25,
                                        ),
                                    ),
                                    label="Settings",
                                ),
                                dmc.Modal(
                                    title="Settings",
                                    id="settings-modal",
                                    children=[
                                        dmc.Title(
                                            "Display Settings",
                                            order=2,
                                            size="h4",
                                        ),
                                        dmc.Space(h="xs"),
                                        dmc.Switch(
                                            id="automatically-change-scenario-switch",
                                            labelPosition="right",
                                            label=_settings_help_label(
                                                "Automatically Change Scenario",
                                                SETTINGS_HELP_TEXT[
                                                    "automatically-change-scenario"
                                                ],
                                            ),
                                            checked=True,
                                            persistence=True,
                                        ),
                                        dmc.Space(h="xs"),
                                        dmc.Switch(
                                            id="rank-overlay-switch",
                                            labelPosition="right",
                                            label=_settings_help_label(
                                                "Rank Overlay",
                                                SETTINGS_HELP_TEXT["rank-overlay"],
                                            ),
                                            checked=True,
                                            persistence=True,
                                        ),
                                        dmc.Space(h="xs"),
                                        dmc.Switch(
                                            id="high-score-overlay-switch",
                                            labelPosition="right",
                                            label=_settings_help_label(
                                                "PB Score Overlay",
                                                SETTINGS_HELP_TEXT[
                                                    "high-score-overlay"
                                                ],
                                            ),
                                            checked=True,
                                            persistence=True,
                                        ),
                                        dmc.Space(h="xs"),
                                        dmc.Switch(
                                            id="score-threshold-overlay-switch",
                                            labelPosition="right",
                                            label=_settings_help_label(
                                                "Score Threshold Overlay",
                                                SETTINGS_HELP_TEXT[
                                                    "score-threshold-overlay"
                                                ],
                                            ),
                                            checked=True,
                                            persistence=True,
                                        ),
                                        dmc.Space(h="xs"),
                                        dmc.NumberInput(
                                            id="score-threshold-percentage",
                                            label=_settings_help_label(
                                                "Score Threshold Percentage",
                                                SETTINGS_HELP_TEXT[
                                                    "score-threshold-percentage"
                                                ],
                                            ),
                                            min=1,
                                            persistence=True,
                                            placeholder="Score Percentage...",
                                            radius="sm",
                                            size="sm",
                                            variant="default",
                                            value=95,
                                            w="12em",
                                        ),
                                        dmc.Space(h="xs"),
                                        dmc.Switch(
                                            id="score-threshold-notification-switch",
                                            labelPosition="right",
                                            label=_settings_help_label(
                                                "Score Threshold Notification",
                                                SETTINGS_HELP_TEXT[
                                                    "score-threshold-notification"
                                                ],
                                            ),
                                            checked=True,
                                            persistence=True,
                                        ),
                                    ],
                                ),
                            ],
                            gap="md",
                            justify="flex-end",
                            align="center",
                            direction="row",
                            wrap="wrap",
                        ),
                        span="auto",
                    ),
                ],
                gutter="xl",
                overflow="hidden",
            ),
            dcc.Graph(
                id="graph-content",
                figure=generate_empty_plot(
                    _SELECT_SCENARIO_PLOT_TITLE,
                    _SELECT_SCENARIO_PLOT_MESSAGE,
                ).to_plotly_json(),
                style={"height": "80vh"},
            ),
        ],
    )
