"""What the Run History page's PB card shows: the selected scenario's personal best.

``personal_best`` works out, from one scenario's runs, what the card says
about its PB as this app records it: when it was set, its score, how far it
beat the PB before it, the rank it has reached on the ladder the Playlist
filter holds and the gap to the next one, and the PB run's sensitivity and
accuracy. The card is worked out from the run store each time, as the
latest-run card is, so it is right on a page that has just been drawn, with
no new run.

Under the PB, sourced apart from it, is the card's leaderboard line: the
player's position on KovaaK's leaderboard, led by its percentile, with its
Refresh button. It is shown only while the scenario has a local PB. Its
callbacks are plain functions here, registered once per page with that
page's ids, as the card's are.

What the leaderboard line remembers between calls is module-level state:
``_session_notices_sent`` and ``_last_rank_hints``. Every page that
registers the card reads and writes the same objects, so the Steam ID
mismatch toast fires once per run of the server, whichever page is open.
"""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, NamedTuple

import dash_mantine_components as dmc
from dash import (
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    ctx,
    dcc,
    html,
    no_update,
)

from source.components.chart_options import (
    SETTINGS_HELP_TOOLTIP_WIDTH,
    TOOLTIP_EVENTS,
)
from source.components.latest_run_card import (
    AGE_SCRIPT,
    BODY_CLASS,
    EMPTY_MESSAGE_CLASS,
    EMPTY_TITLE_CLASS,
    RESULT_CLASS,
    SCORE_CLASS,
    SCORE_ROW_CLASS,
    TIME_CLASS,
    TIME_TARGET_CLASS,
)
from source.components.local_icon import local_icon
from source.components.run_marks import new_pb_gain, what_runs_chased
from source.config.config_service import get_config
from source.config.settings_service import get_identity, get_kovaaks_username
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from source.kovaaks.api_service import get_scenario_rank_info, steam_id_mismatch_warning
from source.kovaaks.data_models import Rank, RunData
from source.kovaaks.data_service import (
    get_playlist_by_code,
    get_runs_in_play_order,
    is_benchmark_playlist,
    is_scenario_in_database,
)
from source.kovaaks.playlist_scenarios_service import (
    ladder_standing,
    personal_best_cm360,
)
from source.kovaaks.time_scored_service import (
    PaceBasis,
    eligible_pace_constant,
    get_pace_basis,
    get_version_pace_basis,
)
from source.utilities.notifications import (
    TOAST_CHANNEL_REGISTRY_STORE_ID,
    channel_toast,
    toast,
)
from source.utilities.utilities import format_score, format_whole_percent

logger = logging.getLogger(__name__)

PB_LABEL = "PB"
TOP_RANK_TEXT = "Top rank"
NO_SCENARIO_TEXT = "No scenario selected"
NO_LOCAL_PB_TEXT = "No local PB yet"
NO_LOCAL_PB_MESSAGE = "Play this scenario to record one in this app."

CARD_CLASS = "pb-card"
HEADING_CLASS = "pb-card-heading"
RANK_BADGE_CLASS = "pb-card-rank-badge"
NEXT_RANK_CLASS = f"{RESULT_CLASS} pb-card-next-rank"
RANK_DOT_CLASS = "pb-card-rank-dot"
THRESHOLD_CLASS = "pb-card-threshold"
FADED_CLASS = "pb-card-faded"
# The score with a hover, with the affordance Last played's has.
SCORE_HOVER_CLASS = f"{SCORE_CLASS} {TIME_CLASS}"
LEADERBOARD_CLASS = f"{RESULT_CLASS} pb-card-leaderboard"
FLEX_TARGET_CLASS = "pb-card-flex-target"
WORD_END_CLASS = "pb-card-word-end"
POSITION_LABEL_CLASS = "pb-card-position-label"
POSITION_TOOLTIP_CLASS = "pb-card-position-tooltip"
_ARIA_HIDDEN: dict[str, Any] = {"aria-hidden": "true"}

SCENARIO_RANK_LOADING_DELAY_MS = 250
POSITION_LABEL = "Position: "
RANK_REFRESH_TOOLTIP = (
    "Fetch your current position live from the KovaaK's leaderboard. The "
    "displayed value can come from a local cache and may lag the live board."
)
# How a trigger's ``prop_id`` ends when it is a tick of the polling interval.
# The property, not one page's id: every page that registers the card has an
# interval of its own, and the poll is the only ``n_intervals`` the Position
# callback takes.
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


@dataclass(frozen=True)
class NextRank:
    """The next rank's line, in the benchmark table's own figures.

    ``threshold`` is the rank's threshold formatted as PB Score, ``gap`` the
    Next Rank cell's figure (``+1.3%``, or ``+2.8% faster`` by pace), and
    ``points`` the points still to go, as the cell's tooltip gives them.
    ``color`` is the rank's color from the benchmark's file.
    """

    name: str
    color: str
    threshold: str
    gap: str
    points: str


@dataclass(frozen=True)
class PersonalBest:
    """What the card says about a scenario's PB, as the text it shows.

    ``set_at`` is when the PB run ended, which the browser words as an age.
    ``score_hover`` is the line the latest-run card showed when this PB
    landed, and ``None`` for a PB the scenario's first run set, which beat
    nothing. ``rank`` is the rank the PB has reached on the ladder the
    Playlist filter holds, ``None`` below its first threshold and with no
    ladder. ``at_top_rank`` is whether every rank is reached, and
    ``next_rank`` is the next one's line, ``None`` at the top and where the
    benchmark table's Next Rank cell would read ``N/A``. ``faded`` is the
    card's last line.
    """

    set_at: datetime
    score: str
    score_hover: str | None
    rank: Rank | None
    at_top_rank: bool
    next_rank: NextRank | None
    faded: str


def _faded_line(run: RunData) -> str:
    """Word the PB run's sensitivity and its hit accuracy.

    The sensitivity is the scenario table's PB cm/360, formatted as that
    column formats it. The accuracy is the hit accuracy, as the latest-run
    card and the run list show a run's, which can differ from the table's PB
    Accuracy: that column prefers the damage accuracy.
    """
    accuracy = f"Accuracy {format_whole_percent(run.accuracy)}"
    cm360 = personal_best_cm360(run)
    if cm360 is None:
        return accuracy
    return f"{format_score(cm360)} cm/360 · {accuracy}"


def personal_best(
    runs: Sequence[RunData],
    ladder: list[Rank] | None,
    pace_basis: PaceBasis | None,
    version_pace_basis: Callable[[str | None], PaceBasis | None],
) -> PersonalBest | None:
    """Work out what the card says about the PB among ``runs``.

    ``runs`` is one scenario's whole history in the order it was played, and
    ``None`` comes back when it is empty. ``ladder`` is the scenario's ladder
    in the benchmark the Playlist filter holds, ``None`` with no benchmark
    selected. ``pace_basis`` is what the scenario's newest run says of its
    pace, which is how the benchmark table chooses whether the next rank's
    gap is by pace. ``version_pace_basis`` answers for one version of the
    scenario, which is how the latest-run card measured the PB when it
    landed.

    The PB run is the earliest run to reach the high score, the run
    ``get_personal_best_run`` finds, taken from this one copy of the runs so
    that it is always among them.
    """
    if not runs:
        return None
    # ``max`` keeps the first of equal scores, so the earliest run holds a tie.
    run = max(runs, key=lambda each: each.score)
    chased = what_runs_chased(runs, version_pace_basis)[run]
    score_hover = (
        None
        if chased.previous_best is None
        else new_pb_gain(run.score, chased.previous_best, chased)
    )
    standing = (
        ladder_standing(ladder, run.score, eligible_pace_constant(pace_basis, run))
        if ladder
        else None
    )
    next_rank = None
    if standing is not None and standing.next_gap is not None:
        gap = standing.next_gap
        next_rank = NextRank(
            name=gap.rank.name,
            color=gap.rank.color,
            threshold=gap.threshold_text,
            gap=gap.gap_text,
            points=gap.points_text,
        )
    return PersonalBest(
        set_at=run.datetime_object,
        score=format_score(run.score),
        score_hover=score_hover,
        rank=None if standing is None else standing.reached,
        at_top_rank=standing is not None and standing.at_top,
        next_rank=next_rank,
        faded=_faded_line(run),
    )


def _ladder(playlist_code: str | None, scenario: str) -> list[Rank] | None:
    """Find the scenario's ladder in the playlist the filter holds.

    ``None`` unless the playlist is a benchmark that lists the scenario, as
    the benchmark table gives a row no Rank fields on a playlist's table. A
    benchmark scenario without a ladder has an empty one.
    """
    playlist = None if not playlist_code else get_playlist_by_code(playlist_code)
    if playlist is None or not is_benchmark_playlist(playlist):
        return None
    for listed in playlist.scenarios:
        if listed.name == scenario:
            return listed.ranks or []
    return None


def personal_best_from_store(
    selected_scenario: str | None,
    playlist_code: str | None,
) -> PersonalBest | None:
    """Work out what the card says from the run store, ``None`` with no PB.

    The runs are copied from the store once, so the PB, the run before it and
    the figures come from the same moment.
    """
    if not selected_scenario:
        return None
    runs = get_runs_in_play_order(selected_scenario)
    if not runs:
        return None
    ladder = _ladder(playlist_code, selected_scenario)
    pace_basis = None
    # As the benchmark table does: only a scenario with a ladder shows a gap,
    # so only then is a performance file read.
    if ladder:
        try:
            pace_basis = get_pace_basis(selected_scenario)
        except Exception:  # noqa: BLE001 -- it must cost the pace gap, never the card.
            # The lookup handles a missing or unreadable performance file
            # itself. Anything else falls back to the gap as a percentage of
            # the PB, as the table's cell does.
            logger.warning(
                'Failed to tell whether "%s" is time-scored',
                selected_scenario,
                exc_info=True,
            )
    return personal_best(
        runs,
        ladder,
        pace_basis,
        lambda version: get_version_pace_basis(selected_scenario, version),
    )


# --- The leaderboard line: the player's position on KovaaK's board -------------


class PositionShown(NamedTuple):
    """What the leaderboard line shows of a lookup, before any hint.

    ``value`` is the line's value: the percentile where there is one, and
    otherwise the Position field's readout, after a ``Position:`` label.
    ``of_total`` is the first line of the hover where the percentile leads,
    and ``None`` wherever the label shows instead.
    """

    value: str
    of_total: str | None


class PositionOutputs(NamedTuple):
    """What a render writes to the leaderboard line, one field per prop.

    ``value`` is the value with its hint, ``label_hidden`` hides the
    ``Position:`` label where the percentile leads, ``updated_ts`` is when
    the position was stored, and ``of_total`` the hover's first line.
    """

    value: str | list
    label_hidden: bool
    updated_ts: float | None
    of_total: str | None


# What the line holds with no scenario, and for a scenario with no local runs.
# The card hides the line then, so nothing is looked up for it. KovaaK's can
# hold a record of such a scenario from another computer, but every position
# the maintainer's cache held for one was Unranked, and showing a remote
# record is the remote personal best reconciliation work's.
_NOTHING_TO_RANK = PositionOutputs("N/A", False, None, None)

# Notices that fire once per app session rather than once per trigger, by id.
# A set, so the check-and-set needs no ``global`` rebinding; sound under
# Waitress's single-process thread pool, and a lost race is benign because the
# stable id makes the loser's duplicate payload a no-op at the container.
_session_notices_sent: set[str] = set()
# What each scenario's last network-backed render concluded, as (what the line
# showed, hint), so the cache-only interval path can repeat the hint instead of
# recomputing it from a read that cannot see the failure -- and can tell when a
# background writer has moved the cache on. See _rank_hint.
_last_rank_hints: dict[str, tuple[PositionShown, str | None]] = {}


# Rank display states deliberately map to distinct user-facing text.
def format_scenario_rank(rank_info: ScenarioRankInfo) -> PositionShown:  # noqa: PLR0911
    """Format what the leaderboard line shows of a lookup.

    The percentile leads where there is one, and the position and the total
    move to its hover. Every other state reads as the Position field did,
    after its label.
    """
    match rank_info.status:
        case ScenarioRankStatus.RANKED:
            if rank_info.rank is None:
                return PositionShown("N/A", None)
            if rank_info.total_players is not None:
                if rank_info.percentile is not None:
                    return PositionShown(
                        f"{rank_info.percentile:.2f}% percentile",
                        f"Position {rank_info.rank:,} of {rank_info.total_players:,}",
                    )
                return PositionShown(
                    f"{rank_info.rank:,} of {rank_info.total_players:,}", None
                )
            return PositionShown(f"{rank_info.rank:,}", None)
        case ScenarioRankStatus.UNRANKED:
            if rank_info.total_players is not None:
                return PositionShown(
                    f"Unranked ({rank_info.total_players:,} players)", None
                )
            return PositionShown("Unranked", None)
        case ScenarioRankStatus.UNKNOWN:
            return PositionShown("N/A", None)
    return PositionShown("N/A", None)


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


def _position_outputs(
    shown: PositionShown,
    hint: str | None,
    rank_info: ScenarioRankInfo,
) -> PositionOutputs:
    """Build what a render writes to the line for one lookup and its hint."""
    return PositionOutputs(
        value=_rank_display(shown.value, hint),
        label_hidden=shown.of_total is not None,
        updated_ts=_rank_updated_ts(rank_info),
        of_total=shown.of_total,
    )


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
    shown: PositionShown,
) -> str | None:
    """Resolve the hint for a render, keeping it stable across interval ticks.

    Only the network path can tell a degraded read from a healthy one: a
    served-stale result is an ordinary cache hit by the time the cache-only
    interval re-reads it a second later. Remembering the last network verdict
    per scenario keeps the affordance on screen instead of blinking off on the
    next tick.

    The memo is tied to what the line showed, the hover's position included,
    because the warmup worker and the score-aware refresh Timer both write the
    rank cache from background threads. When the interval reads a position
    the verdict was never about, the cache has moved on: the memo is retired
    rather than left claiming the lookup failed over a position that has
    since arrived.

    An unset username is visible on both paths, so it is derived rather than
    remembered and clears the moment Settings gains a name.
    """
    if not username:
        return _RANK_HINT_USERNAME_UNSET
    if allow_network:
        hint = _derive_rank_hint(rank_info)
        _last_rank_hints[selected_scenario] = (shown, hint)
        return hint
    remembered = _last_rank_hints.get(selected_scenario)
    if remembered is not None:
        if remembered[0] == shown:
            return remembered[1]
        # pop, not del: concurrent interval ticks for the same scenario (two
        # tabs of the page on Waitress's thread pool) can pass the same read, and the
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
) -> tuple[PositionOutputs, list[dict[str, object]]]:
    """Render rank through either the normal lookup or the cache-only interval path.

    Returns what the line shows and any toast the render earned. Passive
    renders do not toast their own state: an unconfigured username, a failed
    lookup, and a value served from a stale cache are persistent conditions,
    so the line says so itself. The Steam-ID mismatch has no such in-place
    home and is the single exception.

    ``allow_notifications=False`` renders the value without spending the
    session's one mismatch toast -- for the render nobody triggered.
    """
    if not selected_scenario or not is_scenario_in_database(selected_scenario):
        return _NOTHING_TO_RANK, []

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
        failed = PositionOutputs(
            _rank_display("N/A", _RANK_HINT_LOOKUP_FAILED), False, None, None
        )
        return failed, []

    shown = format_scenario_rank(rank_info)
    outputs = _position_outputs(
        shown,
        _rank_hint(rank_info, username, selected_scenario, allow_network, shown),
        rank_info,
    )
    if not allow_notifications:
        return outputs, []
    return outputs, _steam_mismatch_notifications(rank_info, username, steam_id)


def get_scenario_rank(_, selected_scenario, _n_intervals):
    """Render scenario rank, keeping interval-only calls cache-only.

    Under DashProxy an ``allow_duplicate`` callback can still fire once on page
    load with nothing triggering it. The value has to render either way, but a
    fire nobody caused must not spend the session's one mismatch toast on a
    moment the user may not be looking at.
    """
    triggered = ctx.triggered
    outputs, notifications = _render_scenario_rank(
        selected_scenario,
        _rank_allows_network(triggered),
        allow_notifications=bool(triggered),
    )
    return *outputs, notifications or no_update


# The hover is worded in the browser, on each store change and every 30s tick,
# so its age stays current while a cached position sits untouched. Where the
# percentile leads the line, the position and the total come first, as a line
# of their own. "Last updated", not "checked": a fetch that fails, and an
# automatic read whose result the cache refuses, both leave the stored
# position and its time alone, so the label stays true of the data while the
# app goes on trying.
#
# The tooltip is a fixed part of the layout rather than part of the value's
# children: the interval rewrites those every tick, and Dash remounts component
# children on each write, which blinks an open tooltip.
_RANK_UPDATED_SCRIPT = """
    (seconds, ofTotal, _nIntervals) => {
        const lines = [];
        if (ofTotal) {
            lines.push(ofTotal);
        }
        if (seconds !== null && seconds !== undefined) {
            const dagfuncs = window.dashAgGridFunctions;
            lines.push(
                "Last updated " +
                dagfuncs.relativeTime(seconds, "") +
                " · " +
                dagfuncs.absoluteTime(seconds, "")
            );
        }
        if (lines.length === 0) {
            return ["", true, null, null];
        }
        return [lines.join("\\n"), false, "cell-tooltip-affordance", 0];
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
    line is showing.
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
    read rather than the service's error copy. The passive line already
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
        return (no_update,) * 7
    # The button is on a line the card hides without a local PB, so a click
    # can only reach here as the selection moves away from one.
    if not selected_scenario or not is_scenario_in_database(selected_scenario):
        return *_NOTHING_TO_RANK, no_update, no_update, no_update
    # What the line shows of a position: every outcome moves all of it or none.
    unchanged = (no_update,) * len(PositionOutputs._fields)
    if not get_kovaaks_username():
        # ``no_update``: the line already reads "N/A · set your KovaaK's
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
    shown = format_scenario_rank(rank_info)
    hint = _derive_rank_hint(rank_info)
    _last_rank_hints[selected_scenario] = (shown, hint)
    outputs = _position_outputs(shown, hint, rank_info)
    if rank_info.served_stale:
        logger.warning(
            'Manual rank refresh for "%s" served a cached position: %s',
            selected_scenario,
            rank_info.warning_message,
        )
        return *outputs, *channel_toast(
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
        return *outputs, *channel_toast(
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
    return *outputs, *channel_toast(
        _rank_refresh_success_notification(selected_scenario),
        toast_channels,
        clears=(
            _RANK_REFRESH_PROBLEM_CHANNEL,
            _RANK_REFRESH_USERNAME_UNSET_CHANNEL,
        ),
    )


# --- The card on a page --------------------------------------------------------


class PbCardIds(NamedTuple):
    """The component ids one page gives its PB card.

    ``set_at`` is a store holding when the PB run ended, in epoch seconds, or
    nothing with no PB. A script on the page words it into ``label``, the
    first line's words after ``PB``, hidden with no PB: ``time`` is the PB's
    age in it and ``time_tooltip`` the age's hover. ``body`` holds the lines
    from the score down to the next rank, or the card's empty state, and
    ``faded`` its last line.

    ``leaderboard`` is the leaderboard line, hidden with no local PB. In it,
    ``rank_label`` is its ``Position:`` label, hidden where the percentile
    leads, and ``rank`` its value, whose hover ``rank_updated_tooltip`` is
    worded from two stores: ``rank_updated_ts``, when the position was
    stored, and ``rank_of_total``, the position and the total where the
    percentile leads. ``rank_refresh_button`` is Refresh.

    ``run_events``, ``scenario_dropdown``, ``playlist_filter``,
    ``polling_interval`` and ``relative_time_interval`` are the page's own.
    The card reads them and builds none of them:

    - ``run_events`` is the store the page's run delivery writes when new
      runs land on the scenario it shows.
    - ``polling_interval`` is the ``dcc.Interval`` the page polls on. A tick
      of it alone reads the position from caches and never fetches.
    - ``relative_time_interval`` is a ``dcc.Interval`` that ticks every 30
      seconds, so the PB's age and the position hover's stay current on a
      page left open.
    """

    set_at: str
    label: str
    time: str
    time_tooltip: str
    body: str
    leaderboard: str
    rank_label: str
    rank: str
    rank_updated_tooltip: str
    rank_refresh_button: str
    rank_updated_ts: str
    rank_of_total: str
    faded: str
    run_events: str
    scenario_dropdown: str
    playlist_filter: str
    polling_interval: str
    relative_time_interval: str


class PbCardContent(NamedTuple):
    """What a page writes to its card, one field per prop it writes."""

    set_at: float | None
    body: list[Any]
    leaderboard_hidden: bool
    faded: str | None


def _leaderboard_line(ids: PbCardIds) -> html.Div:
    """Build the leaderboard line: the position's value, then Refresh.

    The label and the value are one run of text, so a hint too long for the
    line wraps as a sentence does, and Refresh follows on the same line where
    it fits. dmc wraps a tooltip's target in a block box, made inline here as
    the PB's age is.
    """
    return html.Div(
        id=ids.leaderboard,
        className=LEADERBOARD_CLASS,
        # The card's callback shows it once there is a local PB to rank.
        hidden=True,
        children=[
            dcc.Loading(
                html.Span(
                    [
                        html.Span(
                            POSITION_LABEL,
                            className=POSITION_LABEL_CLASS,
                            id=ids.rank_label,
                        ),
                        dmc.Tooltip(
                            dmc.Text(id=ids.rank, inherit=True, span=True),
                            boxWrapperProps={"className": TIME_TARGET_CLASS},
                            # The hover takes two lines where the percentile
                            # leads, and the stylesheet keeps its line break.
                            classNames={"tooltip": POSITION_TOOLTIP_CLASS},
                            disabled=True,
                            events=TOOLTIP_EVENTS,
                            id=ids.rank_updated_tooltip,
                            label="",
                        ),
                    ]
                ),
                delay_show=SCENARIO_RANK_LOADING_DELAY_MS,
                show_initially=False,
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
                # As a block, dmc's box round the button would be a line
                # taller than the button.
                boxWrapperProps={"className": FLEX_TARGET_CLASS},
                label=RANK_REFRESH_TOOLTIP,
                events=TOOLTIP_EVENTS,
                multiline=True,
                withArrow=True,
                w=SETTINGS_HELP_TOOLTIP_WIDTH,
            ),
        ],
    )


def pb_card(ids: PbCardIds) -> dmc.Box:
    """Build the card with nothing in it yet.

    The page's callbacks write what it shows. What a script writes, the PB's
    age and the position's hover, is in the layout from the start: it would
    come and go under the script if the server's answer drew it. So is the
    leaderboard line, whose callbacks a page must hold every input of.
    """
    return dmc.Box(
        className=CARD_CLASS,
        children=[
            dcc.Store(id=ids.set_at),
            # When the position was stored, and the hover's first line.
            dcc.Store(id=ids.rank_updated_ts),
            dcc.Store(id=ids.rank_of_total),
            # Not a flex container, which would drop the spaces either side of
            # the age and hand a screen reader the words run together.
            html.Div(
                className=HEADING_CLASS,
                children=[
                    PB_LABEL,
                    html.Span(
                        [
                            " · set ",
                            dmc.Tooltip(
                                dmc.Text(
                                    className=TIME_CLASS,
                                    id=ids.time,
                                    inherit=True,
                                    span=True,
                                    tabIndex=0,
                                ),
                                # dmc wraps the tooltip's target in a block
                                # box, which would break the line round it.
                                boxWrapperProps={"className": TIME_TARGET_CLASS},
                                events=TOOLTIP_EVENTS,
                                id=ids.time_tooltip,
                                label="",
                            ),
                        ],
                        hidden=True,
                        id=ids.label,
                    ),
                ],
            ),
            html.Div(id=ids.body, className=BODY_CLASS),
            _leaderboard_line(ids),
            html.Div(id=ids.faded, className=FADED_CLASS),
        ],
    )


def _score(shown: PersonalBest) -> Any:
    """Draw the PB score, with its hover where it beat a previous best.

    The score ends on a space a screen reader reads and the eye does not see:
    the score row is a flex container, which drops the space between the
    score and the badge, and the two would be handed over as one word.
    """
    text = [shown.score, html.Span(" ", className=WORD_END_CLASS)]
    if shown.score_hover is None:
        return html.Span(text, className=SCORE_CLASS)
    return dmc.Tooltip(
        html.Span(text, className=SCORE_HOVER_CLASS, tabIndex=0),
        # dmc wraps the target in a block box, whose line would make the row
        # 2px taller with a hover than without one.
        boxWrapperProps={"className": FLEX_TARGET_CLASS},
        events=TOOLTIP_EVENTS,
        label=shown.score_hover,
    )


def _rank_badge(rank: Rank) -> dmc.Badge:
    """Draw the rank the PB has reached, in its color from the benchmark's file.

    The stylesheet draws it in the page's text color on a tint of the rank's
    color, with a border in that color, so a pale rank stays legible in both
    themes.
    """
    return dmc.Badge(
        rank.name,
        className=RANK_BADGE_CLASS,
        style={"--pb-card-rank-color": rank.color},
        # The app's sentence case, where the badge's own style would print
        # capitals.
        tt="none",
    )


def _next_rank_line(next_rank: NextRank) -> html.Div:
    """Draw the next rank's line, its threshold under the PB score."""
    return html.Div(
        [
            html.Span(
                className=RANK_DOT_CLASS,
                style={"--pb-card-rank-color": next_rank.color},
                **_ARIA_HIDDEN,
            ),
            html.Span(next_rank.threshold, className=THRESHOLD_CLASS),
            f" {next_rank.name} · {next_rank.gap} · {next_rank.points} to go",
        ],
        className=NEXT_RANK_CLASS,
    )


def pb_card_content(
    shown: PersonalBest | None,
    selected_scenario: str | None,
) -> PbCardContent:
    """Build what the card shows for a PB, or for a scenario with none.

    The leaderboard line follows the local PB: with none, there is nothing
    the line could sit under, and no line.
    """
    if not selected_scenario:
        return PbCardContent(
            set_at=None,
            body=[html.Div(NO_SCENARIO_TEXT, className=EMPTY_TITLE_CLASS)],
            leaderboard_hidden=True,
            faded=None,
        )
    if shown is None:
        return PbCardContent(
            set_at=None,
            body=[
                html.Div(NO_LOCAL_PB_TEXT, className=EMPTY_TITLE_CLASS),
                html.Div(NO_LOCAL_PB_MESSAGE, className=EMPTY_MESSAGE_CLASS),
            ],
            leaderboard_hidden=True,
            faded=None,
        )
    score_row: list[Any] = [_score(shown)]
    if shown.rank is not None:
        score_row.append(_rank_badge(shown.rank))
    body: list[Any] = [html.Div(score_row, className=SCORE_ROW_CLASS)]
    if shown.at_top_rank:
        body.append(html.Div(TOP_RANK_TEXT, className=NEXT_RANK_CLASS))
    elif shown.next_rank is not None:
        body.append(_next_rank_line(shown.next_rank))
    return PbCardContent(
        set_at=shown.set_at.timestamp(),
        body=body,
        leaderboard_hidden=False,
        faded=shown.faded,
    )


def show_pb(_run_events, selected_scenario, selected_playlist) -> PbCardContent:
    """Write what the card shows, from the run store.

    The first argument is the page's run-events store, which triggers the
    call and is not read. Every run that lands on the selected scenario
    rebuilds the card, a new PB or not: whether the next rank's gap is by
    pace follows the scenario's newest version, so a run of a new version
    can change it without beating anything.
    """
    return pb_card_content(
        personal_best_from_store(selected_scenario, selected_playlist),
        selected_scenario,
    )


def register_pb_card(ids: PbCardIds) -> None:
    """Register the card's callbacks for one page's ids.

    Call once per page, at import, with the ids its layout is built from.
    The leaderboard line's toasts go to the shell's notification container
    and channel registry, which every page shares.
    """
    callback(
        Output(ids.set_at, "data"),
        Output(ids.body, "children"),
        Output(ids.leaderboard, "hidden"),
        Output(ids.faded, "children"),
        Input(ids.run_events, "data"),
        Input(ids.scenario_dropdown, "value"),
        # The badge and the next rank follow the filter's benchmark at once,
        # as the chart's rank lines do.
        Input(ids.playlist_filter, "value"),
    )(show_pb)
    clientside_callback(
        AGE_SCRIPT,
        Output(ids.label, "hidden"),
        Output(ids.time, "children"),
        Output(ids.time_tooltip, "label"),
        Input(ids.set_at, "data"),
        Input(ids.relative_time_interval, "n_intervals"),
    )
    callback(
        Output(ids.rank, "children"),
        Output(ids.rank_label, "hidden"),
        Output(ids.rank_updated_ts, "data"),
        Output(ids.rank_of_total, "data"),
        Output("notification-container", "sendNotifications", allow_duplicate=True),
        Input(ids.run_events, "data"),
        Input(ids.scenario_dropdown, "value"),
        Input(ids.polling_interval, "n_intervals"),
        # Not ``True``: this callback renders the initial position, so the page
        # load must still run it -- but Dash refuses an ``allow_duplicate``
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
        Input(ids.rank_of_total, "data"),
        Input(ids.relative_time_interval, "n_intervals"),
    )
    callback(
        Output(ids.rank, "children", allow_duplicate=True),
        Output(ids.rank_label, "hidden", allow_duplicate=True),
        Output(ids.rank_updated_ts, "data", allow_duplicate=True),
        Output(ids.rank_of_total, "data", allow_duplicate=True),
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
