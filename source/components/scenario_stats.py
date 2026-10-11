"""Build the Scenario Stats block and wire its callbacks to a page's ids.

The block is what sits under the Scenario Stats heading: Last played,
Number of runs, and Position with its Refresh button. A page that hosts it
fills in a ``ScenarioStatsIds``, puts ``scenario_stats_stores`` and
``scenario_stats_panel`` in its layout, and calls
``register_scenario_stats`` with the ids once, at import. The callbacks are
plain functions here and are registered once per page.

What the Position field remembers between calls is module-level state:
``_session_notices_sent`` and ``_last_rank_hints``. Every page that
registers the block reads and writes the same objects, so the Steam ID
mismatch toast fires once per run of the server, whichever page is open.
"""

import logging
from typing import NamedTuple

import dash_mantine_components as dmc
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

from source.components.chart_options import (
    SETTINGS_HELP_TOOLTIP_WIDTH,
    TOOLTIP_EVENTS,
)
from source.components.local_icon import local_icon
from source.config.config_service import get_config
from source.config.settings_service import get_identity, get_kovaaks_username
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from source.kovaaks.api_service import get_scenario_rank_info, steam_id_mismatch_warning
from source.kovaaks.data_service import get_scenario_stats, is_scenario_in_database
from source.utilities.notifications import (
    TOAST_CHANNEL_REGISTRY_STORE_ID,
    channel_toast,
    toast,
)
from source.utilities.utilities import format_absolute_timestamp

logger = logging.getLogger(__name__)
SCENARIO_RANK_LOADING_DELAY_MS = 250
RANK_REFRESH_TOOLTIP = (
    "Fetch your current position live from the KovaaK's leaderboard. The "
    "displayed value can come from a local cache and may lag the live board."
)
# How a trigger's ``prop_id`` ends when it is a tick of the polling interval.
# The property, not one page's id: every page that registers the block has
# an interval of its own, and the poll is the only ``n_intervals`` the
# Position callback takes.
_INTERVAL_TICK = ".n_intervals"
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
_RANK_REFRESH_FAILED_TITLE = "Position refresh failed"
_RANK_REFRESH_STALE_TITLE = "Refresh failed · data from cache"
_RANK_REFRESH_FAILED_MESSAGE = "Couldn't refresh. The position shown is unchanged."
_RANK_REFRESH_STALE_MESSAGE = "Couldn't refresh. The position shown is from cache."
_RANK_REFRESH_STALE_WITH_TOTAL_MESSAGE = (
    "Couldn't refresh. The position and total shown are from cache."
)
_RANK_REFRESH_TOTAL_STALE_TITLE = "Position refreshed but total from cache"
_RANK_REFRESH_TOTAL_MISSING_TITLE = "Position refreshed but no total"
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


class ScenarioStatsIds(NamedTuple):
    """The component ids one page gives its Scenario Stats block.

    Two pages need two sets: the callbacks are registered once per set, and
    Dash allows one callback per output.

    ``scenario_stats_stores`` builds the stores, whose ids here end in
    ``_ts`` or ``_empty_value``, and ``scenario_stats_panel`` builds the
    rest of the block. ``run_events``, ``scenario_dropdown``,
    ``polling_interval`` and ``relative_time_interval`` are the page's own.
    The block reads them and builds none of them:

    - ``run_events`` is the store the page's run delivery writes when new
      runs land on the scenario it shows.
    - ``polling_interval`` is the ``dcc.Interval`` the page polls on. A
      tick of it alone reads the Position from caches and never fetches.
    - ``relative_time_interval`` is a ``dcc.Interval`` that ticks every 30
      seconds, so the Last played text and the Position hover's age stay
      current on a page left open.
    """

    last_played: str
    last_played_tooltip: str
    num_runs: str
    rank: str
    rank_updated_tooltip: str
    rank_refresh_button: str
    last_played_ts: str
    last_played_empty_value: str
    rank_updated_ts: str
    run_events: str
    scenario_dropdown: str
    polling_interval: str
    relative_time_interval: str


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
                        f"({rank_info.percentile:.2f}% percentile)"
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


def _rank_allows_network(triggered: list[dict[str, str]]) -> bool:
    """Allow network access unless the interval is the callback's only trigger."""
    return any(not trigger["prop_id"].endswith(_INTERVAL_TICK) for trigger in triggered)


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
            " · set your KovaaK's username in ",
            dmc.Anchor("Settings", href="/settings", refresh=False),
        ]
    if hint == _RANK_HINT_LOOKUP_FAILED:
        return [" · lookup failed"]
    return [" · from cache"]


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


def _rank_updated_ts(rank_info: ScenarioRankInfo) -> float | None:
    """Return when the displayed position was stored, as epoch seconds.

    ``None`` when no position is displayed, and for a cache entry written
    without a time: the hover then has nothing to date.
    """
    displayed = rank_info.status == ScenarioRankStatus.UNRANKED or (
        rank_info.status == ScenarioRankStatus.RANKED and rank_info.rank is not None
    )
    if not displayed or rank_info.fetched_at is None:
        return None
    return rank_info.fetched_at.timestamp()


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
) -> tuple[str | list, float | None, list[dict[str, object]]]:
    """Render rank through either the normal lookup or the cache-only interval path.

    Returns the Position value, when that position was stored, and any toast
    the render earned. Passive renders do not toast their own state: an
    unconfigured username, a failed lookup, and a value served from a stale
    cache are persistent conditions, so the field says so itself. The Steam-ID
    mismatch has no such in-place home and is the single exception.

    ``allow_notifications=False`` renders the value without spending the
    session's one mismatch toast -- for the render nobody triggered.
    """
    if not selected_scenario:
        return "N/A", None, []

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
        logger.exception('Failed to fetch scenario rank for "%s"', selected_scenario)
        return _rank_display("N/A", _RANK_HINT_LOOKUP_FAILED), None, []

    value = format_scenario_rank(rank_info)
    display = _rank_display(
        value,
        _rank_hint(rank_info, username, selected_scenario, allow_network, value),
    )
    updated_ts = _rank_updated_ts(rank_info)
    if not allow_notifications:
        return display, updated_ts, []
    notifications = _steam_mismatch_notifications(rank_info, username, steam_id)
    return display, updated_ts, notifications


def get_scenario_rank(_, selected_scenario, _n_intervals):
    """Render scenario rank, keeping interval-only calls cache-only.

    Under DashProxy an ``allow_duplicate`` callback can still fire once on page
    load with nothing triggering it. The value has to render either way, but a
    fire nobody caused must not spend the session's one mismatch toast on a
    moment the user may not be looking at.
    """
    triggered = ctx.triggered
    display, updated_ts, notifications = _render_scenario_rank(
        selected_scenario,
        _rank_allows_network(triggered),
        allow_notifications=bool(triggered),
    )
    return display, updated_ts, notifications or no_update


# The hover's age is worded in the browser, on each store change and every 30s
# tick, so it stays current while a cached position sits untouched. "Last
# updated", not "checked": a fetch that fails, and an automatic read whose
# result the cache refuses, both leave the stored position and its time alone,
# so the label stays true of the data while the app goes on trying.
#
# The tooltip is a fixed part of the layout rather than part of the value's
# children: the interval rewrites those every tick, and Dash remounts component
# children on each write, which blinks an open tooltip.
_RANK_UPDATED_SCRIPT = """
    (seconds, _nIntervals) => {
        if (seconds === null || seconds === undefined) {
            return ["", true, null, null];
        }
        const dagfuncs = window.dashAgGridFunctions;
        const label =
            "Last updated " +
            dagfuncs.relativeTime(seconds, "") +
            " · " +
            dagfuncs.absoluteTime(seconds, "");
        return [label, false, "cell-tooltip-affordance", 0];
    }
    """


def _rank_refresh_problem_notification(
    *,
    served_stale: bool,
    has_total: bool = False,
) -> dict[str, object]:
    """Report what went wrong with the latest manual refresh.

    One channel, two flavors: the hard failure came back with nothing usable,
    the served-stale one re-served the cached position. They are the mutually
    exclusive verdicts on one attempt, so they replace each other rather than
    stacking two contradictory claims about the same click.

    ``has_total`` applies to the served-stale flavor only. A failed position
    request asks for no total, so a total beside the cached position is cached
    too, and naming only the position would read as though the total had
    refreshed. With no total on screen, naming it would claim one that isn't
    there. The hard failure keeps one message because it never sees what the
    field is showing.
    """
    if served_stale:
        return toast(
            _RANK_REFRESH_PROBLEM_CHANNEL,
            _RANK_REFRESH_STALE_TITLE,
            _RANK_REFRESH_STALE_WITH_TOTAL_MESSAGE
            if has_total
            else _RANK_REFRESH_STALE_MESSAGE,
            color="yellow",
            icon=local_icon("material-symbols:refresh-rounded"),
        )
    return toast(
        _RANK_REFRESH_PROBLEM_CHANNEL,
        _RANK_REFRESH_FAILED_TITLE,
        _RANK_REFRESH_FAILED_MESSAGE,
        color="red",
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


def _rank_refresh_total_failed_notification(
    selected_scenario: str,
    has_total: bool,
) -> dict[str, object]:
    """Report a refresh whose position landed but whose total did not.

    Orange is the partial-success rung: the position the click asked for is
    live, the count beside it is not. Green would assert a freshness the
    readout does not have, and the served-stale yellow would claim the position
    came from cache when it is the one part that did refresh. It shares the
    success channel because a re-click is the recovery, so the green it earns
    must replace this rather than stack under a contradicting verdict.

    The consequence names the total, which is what failed, rather than the
    percentile, which is recomputed from it and usually moves under the user's
    eyes as the position refreshes. Naming the failed thing also stays true for
    an unranked readout, which shows a count and never a percentile.
    """
    if has_total:
        return toast(
            _rank_refresh_success_channel(selected_scenario),
            _RANK_REFRESH_TOTAL_STALE_TITLE,
            f"Refreshed position for {selected_scenario}. Couldn't refresh the "
            f"total, so the total shown is from cache.",
            color="orange",
            icon=local_icon("material-symbols:refresh-rounded"),
        )
    return toast(
        _rank_refresh_success_channel(selected_scenario),
        _RANK_REFRESH_TOTAL_MISSING_TITLE,
        f"Refreshed position for {selected_scenario}. Couldn't fetch the "
        f"total, so no total is shown.",
        color="orange",
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


# One return per outcome the click can have. Collapsing any pair would only
# hide which answer a reader is looking at.
def refresh_rank(  # noqa: PLR0911
    n_clicks,
    selected_scenario: str | None,
    toast_channels,
):
    """Fetch and display authoritative board truth after an explicit user request.

    The user asked, so every outcome answers on this callback's own
    notification output: red when the refresh failed outright, yellow when it
    failed but a cached position was served in its place, orange when the
    position refreshed but the leaderboard total behind the percentile did not,
    green only on a genuinely fresh result, and blue when there is no username
    to look anything up with.

    The unset-username case is caught before the lookup, on the direct settings
    read rather than the service's error copy. The passive field already
    explains the condition in place, but it was explaining it before the click
    too, so it cannot answer the click itself -- and a user clicking Refresh
    beside that hint plausibly clicked because they had not read it.

    A failed refresh returns ``no_update`` for the value rather than ``N/A``,
    so whatever was on screen stays put -- usually the cached position -- and
    the red toast's "The position shown is unchanged." is true either way.

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
        return no_update, no_update, no_update, no_update, no_update
    if not selected_scenario:
        return "N/A", None, no_update, no_update, no_update
    # The value and the time it was stored: every outcome moves both or neither.
    unchanged = (no_update, no_update)
    if not get_kovaaks_username():
        # ``no_update``: the field already reads "N/A · set your KovaaK's
        # username in Settings", so only the toast is new.
        return *unchanged, *channel_toast(
            _rank_refresh_username_unset_notification(), toast_channels
        )

    try:
        rank_info = get_scenario_rank_info(
            selected_scenario,
            *_rank_lookup_config(),
            force_refresh=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception('Manual rank refresh failed for "%s"', selected_scenario)
        return *unchanged, *channel_toast(
            _rank_refresh_problem_notification(served_stale=False), toast_channels
        )

    if rank_info.error_message:
        # The console/file record the log bridge used to keep, kept here now.
        logger.error(
            'Manual rank refresh for "%s" failed: %s',
            selected_scenario,
            rank_info.error_message,
        )
        return *unchanged, *channel_toast(
            _rank_refresh_problem_notification(served_stale=False), toast_channels
        )

    # A manual refresh is a network verdict too, so the interval path must not
    # go on repeating what the last passive render concluded.
    rank_text = format_scenario_rank(rank_info)
    hint = _derive_rank_hint(rank_info)
    _last_rank_hints[selected_scenario] = (rank_text, hint)
    shown = (_rank_display(rank_text, hint), _rank_updated_ts(rank_info))
    if rank_info.served_stale:
        logger.warning(
            'Manual rank refresh for "%s" served a cached position: %s',
            selected_scenario,
            rank_info.warning_message,
        )
        return *shown, *channel_toast(
            _rank_refresh_problem_notification(
                served_stale=True,
                has_total=rank_info.total_players is not None,
            ),
            toast_channels,
        )
    # Same clears as the green below: the position did refresh, which falsifies
    # both the unchanged-position claim and the no-username one.
    if rank_info.total_refresh_failed:
        logger.warning(
            'Manual rank refresh for "%s" could not re-read the leaderboard total.',
            selected_scenario,
        )
        return *shown, *channel_toast(
            _rank_refresh_total_failed_notification(
                selected_scenario,
                has_total=rank_info.total_players is not None,
            ),
            toast_channels,
            clears=(
                _RANK_REFRESH_PROBLEM_CHANNEL,
                _RANK_REFRESH_USERNAME_UNSET_CHANNEL,
            ),
        )
    return *shown, *channel_toast(
        _rank_refresh_success_notification(selected_scenario),
        toast_channels,
        clears=(
            _RANK_REFRESH_PROBLEM_CHANNEL,
            _RANK_REFRESH_USERNAME_UNSET_CHANNEL,
        ),
    )


def scenario_stats_stores(ids: ScenarioStatsIds) -> list[dcc.Store]:
    """Build the stores the block's callbacks pass their values through."""
    return [
        # raw epoch for the relative "Last played" text
        dcc.Store(id=ids.last_played_ts),
        dcc.Store(id=ids.last_played_empty_value, data=""),
        # raw epoch for the Position hover
        dcc.Store(id=ids.rank_updated_ts),
    ]


def scenario_stats_panel(ids: ScenarioStatsIds) -> dmc.Box:
    """Build the Scenario Stats heading and the rows under it."""
    return dmc.Box(
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
                            # dcc.Loading renders divs, which cannot nest
                            # inside a Text's default <p> root, so it sits
                            # beside the label in a Group (like "Last played:"
                            # above).
                            dcc.Loading(
                                dmc.Tooltip(
                                    dmc.Text(
                                        id=ids.rank,
                                        span=True,
                                        size="sm",
                                    ),
                                    disabled=True,
                                    events=TOOLTIP_EVENTS,
                                    id=ids.rank_updated_tooltip,
                                    label="",
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
                            id=ids.rank_refresh_button,
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
    )


def register_scenario_stats(ids: ScenarioStatsIds) -> None:
    """Register the block's callbacks for one page's ids.

    Call once per page, at import, with the ids its layout is built from.
    The toasts go to the shell's notification container and channel
    registry, which every page shares.
    """
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
    callback(
        Output(ids.rank, "children"),
        Output(ids.rank_updated_ts, "data"),
        Output("notification-container", "sendNotifications", allow_duplicate=True),
        Input(ids.run_events, "data"),
        Input(ids.scenario_dropdown, "value"),
        Input(ids.polling_interval, "n_intervals"),
        # Not ``True``: this callback renders the initial Position value, so the
        # page load must still run it -- but Dash refuses an ``allow_duplicate``
        # output without one of the ``prevent_initial_call`` forms.
        prevent_initial_call="initial_duplicate",
    )(get_scenario_rank)
    clientside_callback(
        _RANK_UPDATED_SCRIPT,
        Output(ids.rank_updated_tooltip, "label"),
        Output(ids.rank_updated_tooltip, "disabled"),
        Output(ids.rank, "className"),
        Output(ids.rank, "tabIndex"),
        Input(ids.rank_updated_ts, "data"),
        Input(ids.relative_time_interval, "n_intervals"),
    )
    callback(
        Output(ids.rank, "children", allow_duplicate=True),
        Output(ids.rank_updated_ts, "data", allow_duplicate=True),
        Output("notification-container", "sendNotifications", allow_duplicate=True),
        Output("notification-container", "hideNotifications", allow_duplicate=True),
        Output(TOAST_CHANNEL_REGISTRY_STORE_ID, "data", allow_duplicate=True),
        Input(ids.rank_refresh_button, "n_clicks"),
        State(ids.scenario_dropdown, "value"),
        State(TOAST_CHANNEL_REGISTRY_STORE_ID, "data"),
        # Show the button's spinner for the duration of the fetch. Mantine's
        # loading state also swallows clicks, so the button cannot be spammed
        # into repeat KovaaK's calls while one refresh is in flight.
        running=[(Output(ids.rank_refresh_button, "loading"), True, False)],
        prevent_initial_call=True,
    )(refresh_rank)
