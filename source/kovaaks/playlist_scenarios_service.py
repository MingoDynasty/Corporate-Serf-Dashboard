"""Build and progressively refresh rows for the playlist scenarios page."""

import logging
import math
import threading
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, TypeAlias
from urllib.parse import urlencode

import requests

from source.config.config_service import get_config
from source.config.settings_service import get_identity, get_kovaaks_username
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from source.kovaaks.api_service import (
    UnknownKovaaksUserError,
    get_cached_leaderboard_id,
    get_scenario_rank_info,
    hydrate_leaderboard_id_cache,
)
from source.kovaaks.data_models import PlaylistData, Rank, RunData, ScenarioStats
from source.kovaaks.data_service import (
    get_all_runs,
    get_personal_best_run,
    get_playlist_by_code,
    get_scenario_groups,
    get_scenario_stats,
    is_benchmark_playlist,
    is_scenario_in_database,
)
from source.kovaaks.pace import percent_faster
from source.kovaaks.play_sessions import split_into_play_sessions
from source.kovaaks.request_logging import request_exception_summary
from source.kovaaks.scenario_groups import ScenarioGroup
from source.kovaaks.time_scored_service import (
    PaceBasis,
    eligible_pace_constant,
    get_pace_basis,
)
from source.kovaaks.typical_score import (
    TOO_FEW_RUNS_TEXT,
    TypicalScore,
    below_minimum_text,
    build_typical_scores,
    format_typical_score,
    typical_score_hover,
    typical_score_recency,
)
from source.utilities.stopwatch import Stopwatch
from source.utilities.utilities import format_percent, format_score

PLAYLIST_RANK_MAX_WORKERS = 4
FILL_TOMBSTONE_LIMIT = 8

TYPICAL_SCORE_OLD_SENTENCE = (
    "Fewer than 10 of them are from the last 30 days, so it may be out of date."
)
TYPICAL_RANK_OLD_LINE = (
    "Fewer than 10 of the typical score's runs are from the last 30 days, "
    "so it may be out of date."
)

FillTerminal: TypeAlias = Literal["complete", "cancelled"]
# A dict holds a hover whose lines a tooltip draws with bold labels.
RowValue: TypeAlias = str | int | float | bool | dict[str, Any] | None
PlaylistScenarioRow: TypeAlias = dict[str, RowValue]

logger = logging.getLogger(__name__)
_FILL_REGISTRY_LOCK = threading.Lock()
_FILL_REGISTRY: dict[str, "_FillState"] = {}
_terminal_sequence = 0


@dataclass(frozen=True)
class TypicalSnapshot:
    """Each scenario's newest typical score, from one copy of the run store.

    ``values`` maps a scenario with runs to its newest value and how many runs
    it has; a scenario with none is absent. Recency is judged at ``moment``,
    when the copy was taken, so every row built from one snapshot agrees.
    """

    moment: datetime
    values: Mapping[str, tuple[TypicalScore, int]]


def take_typical_snapshot(scenario_names: Iterable[str]) -> TypicalSnapshot:
    """Build the newest typical score of each named scenario from one store copy.

    A table build takes one and gives it to every row it builds, the fill's
    and a cancelled fill's rebuild included, so a run landing while the
    table opens can't give its rows two different values.
    """
    # The sessions are split from the same copy the scenarios' runs come
    # from: a run must never appear in a window without its session.
    snapshot = get_all_runs()
    moment = datetime.now()
    wanted = set(scenario_names)
    runs_by_scenario: defaultdict[str, list[RunData]] = defaultdict(list)
    for run in snapshot:
        if run.scenario in wanted:
            runs_by_scenario[run.scenario].append(run)
    if not runs_by_scenario:
        return TypicalSnapshot(moment, {})
    sessions = split_into_play_sessions(snapshot)
    return TypicalSnapshot(
        moment,
        {
            name: (build_typical_scores(runs, sessions)[-1], len(runs))
            for name, runs in runs_by_scenario.items()
        },
    )


@dataclass
class _FillState:
    """Mutable state for one generation, always guarded by the registry lock."""

    playlist_code: str
    scenario_names: tuple[str, ...]
    # Captured with the names, from the same playlist object. The fill's rows
    # and a cancelled fill's rebuild replace phase-1 rows whole, so a row built
    # without its ladder would flip its Rank and Next Rank cells to N/A.
    scenario_ladders: tuple[list[Rank] | None, ...]
    # Captured the same way, for the same reason: a row built without its
    # group would blank its Category and Subcategory cells.
    scenario_groups: tuple[ScenarioGroup | None, ...]
    # Phase 1's snapshot, for the same reason: a row rebuilt from a later one
    # could change its typical cells while the page is open.
    typical: TypicalSnapshot
    total: int
    unresolved_indices: set[int]
    cancel_event: threading.Event = field(default_factory=threading.Event)
    pending_updates: list[PlaylistScenarioRow] = field(default_factory=list)
    done_count: int = 0
    unknown_count: int = 0
    stale_count: int = 0
    terminal: FillTerminal | None = None
    consumed: bool = False
    terminal_order: int | None = None


@dataclass(frozen=True)
class PlaylistScenarioFillDrain:
    """One interval tick's atomically captured generation state."""

    generation_token: str
    updates: list[PlaylistScenarioRow]
    done_count: int
    unknown_count: int
    stale_count: int
    total: int
    terminal: FillTerminal | None
    consuming_terminal: bool


def scenario_run_history_href(
    scenario_name: str,
    playlist_code: str | None = None,
    *,
    run_id: str | None = None,
) -> str:
    """Build the address that opens a scenario on Run History.

    Every link to a scenario on that page is built here, so the page's
    address and its parameters are written in one place. ``playlist_code``
    filters the page to a playlist, and a link that names none leaves the
    parameter out.

    ``run_id`` is for a link that can be offered again for the same scenario,
    as each run's toast offers one. The page does not read it. A link to the
    address the page already holds changes nothing, so without it the second
    such link would do nothing once the selection had been changed by hand.
    """
    parameters = {"scenario": scenario_name}
    if playlist_code is not None:
        parameters = {"playlist_code": playlist_code, **parameters}
    if run_id is not None:
        parameters["run"] = run_id
    return "/run-history?" + urlencode(parameters)


def _format_int(value: int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,}"


def _format_id(value: int | None) -> str:
    # Never through ``_format_int``: an ID gets pasted into a request, so it
    # takes no thousands separator.
    if value is None:
        return "N/A"
    return str(value)


def _format_percentile(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}%"


def _format_score(value: float | None) -> str:
    if value is None:
        return "N/A"
    return format_score(value)


def _format_accuracy(fraction: float | None) -> str:
    if fraction is None:
        return "N/A"
    return format_percent(fraction)


def _round_up(value: float, decimals: int) -> float:
    # The inner round strips float noise that a bare ceiling would round up:
    # 3.08 - 2.8 is 0.28000000000000025, which would read 0.29. It runs after
    # scaling, because 0.28 * 100 is itself 28.000000000000004. The floor of
    # one final unit keeps a remaining gap from reading "+0.0%" or "0 to go".
    scale = 10**decimals
    return max(1 / scale, math.ceil(round(value * scale, 6)) / scale)


def _scenario_ladders(playlist: PlaylistData) -> tuple[list[Rank] | None, ...]:
    """Pick each row's ladder: ``None`` on a playlist, a list on a benchmark.

    A benchmark scenario without a ladder gets an empty list, so its row still
    carries the Rank and Next Rank fields and reads ``N/A`` in both.
    """
    if not is_benchmark_playlist(playlist):
        return (None,) * len(playlist.scenarios)
    return tuple(scenario.ranks or [] for scenario in playlist.scenarios)


def playlist_scenario_groups(
    playlist: PlaylistData,
) -> tuple[ScenarioGroup | None, ...]:
    """Pick each row's group: ``None`` wherever the playlist has no groups."""
    groups = get_scenario_groups(playlist.code)
    # The join sizes the groups to the scenario list it was given. A list of
    # another length would hand rows their neighbors' groups.
    if groups is None or len(groups) != len(playlist.scenarios):
        return (None,) * len(playlist.scenarios)
    return groups


def scenario_group_fields(group: ScenarioGroup) -> PlaylistScenarioRow:
    """Build the fields a row carries when its benchmark has groups.

    The two runs are the group cells' values, never the names: the grid
    merges neighboring cells whose values are equal, and two groups can share
    a name across a category boundary.
    """
    return {
        "category_name": group.category,
        "category_color": group.category_color,
        "category_run": group.category_run,
        "subcategory_name": group.subcategory,
        "subcategory_color": group.subcategory_color,
        "subcategory_run": group.subcategory_run,
    }


@dataclass(frozen=True)
class NextRankGap:
    """How far a PB is from the next rank on its ladder, in the table's figures.

    ``gap`` is the unrounded percentage the Next Rank column sorts by, and
    ``gap_text`` the cell's figure: ``+1.3%``, or ``+2.8% faster`` where the
    gap is measured by pace. ``threshold_text`` and ``points_text`` are the
    figures of the cell's tooltip, the rank's threshold and the points still
    to go, each formatted as PB Score.
    """

    rank: Rank
    gap: float
    gap_text: str
    threshold_text: str
    points_text: str


@dataclass(frozen=True)
class LadderStanding:
    """Where a PB stands on its scenario's ladder.

    ``passed`` counts the ranks the PB has reached, and ``reached`` is the
    highest of them, ``None`` below the first. ``next_gap`` is ``None`` at the
    top rank, and wherever the gap is undefined, where the Next Rank cell
    reads ``N/A``.
    """

    passed: int
    reached: Rank | None
    at_top: bool
    next_gap: NextRankGap | None


def ladder_standing(
    ladder: list[Rank],
    high_score: float | None,
    pace_constant: float | None = None,
) -> LadderStanding | None:
    """Walk a PB up its ladder, or return ``None`` with no PB or no ladder.

    The benchmark table and Run History's PB card both read a PB's rank and
    its gap to the next one from here, so the card's figures are the table's
    and the two can never disagree about one scenario.

    The walk starts at the bottom of the ladder and stops at the first
    threshold above the PB, so a PB equal to a threshold has reached it. The
    ladder keeps its stored order: a few upstream ladders tie or dip, and the
    walk still never grants a rank past an unmet threshold, which also keeps
    every gap positive. The figures round up, so a gap that remains never
    reads as reached.

    ``pace_constant`` is the constant of a time-scored scenario whose PB is
    eligible for a pace comparison, and ``None`` for every other row. With it
    the gap is how much faster the PB run has to finish, and the figure reads
    "faster". A pace gap needs only positive times, so it is defined for a PB
    of zero or less. Where it is undefined, the gap falls back to a
    percentage of the PB. The walk is the same either way, because a higher
    score is always a faster finish.
    """
    if high_score is None or not ladder:
        return None
    passed = 0
    for rank in ladder:
        if rank.threshold > high_score:
            break
        passed += 1
    reached = ladder[passed - 1] if passed else None
    if passed == len(ladder):
        return LadderStanding(passed, reached, at_top=True, next_gap=None)
    next_rank = ladder[passed]
    points = next_rank.threshold - high_score
    gap = None
    if pace_constant is not None:
        gap = percent_faster(pace_constant, high_score, next_rank.threshold)
    if gap is not None:
        gap_text = f"+{_round_up(gap, 1):,.1f}% faster"
    elif high_score > 0:
        gap = points / high_score * 100
        gap_text = f"+{_round_up(gap, 1):,.1f}%"
    else:
        return LadderStanding(passed, reached, at_top=False, next_gap=None)
    return LadderStanding(
        passed,
        reached,
        at_top=False,
        next_gap=NextRankGap(
            rank=next_rank,
            gap=gap,
            gap_text=gap_text,
            threshold_text=_format_score(next_rank.threshold),
            points_text=_format_score(_round_up(points, 2)),
        ),
    )


def benchmark_rank_fields(
    ladder: list[Rank],
    high_score: float | None,
    pace_constant: float | None = None,
) -> PlaylistScenarioRow:
    """Compute a benchmark row's Rank and Next Rank fields from its PB.

    The figures are ``ladder_standing``'s. ``tier_sort`` counts the ranks
    passed, so No rank is 0. ``next_tier_sort`` is the unrounded gap, and Top
    rank and ``N/A`` sort as null.
    """
    fields: PlaylistScenarioRow = {
        "tier_display": "N/A",
        "tier_sort": None,
        "next_tier_display": "N/A",
        "next_tier_sort": None,
        "next_tier_tooltip": None,
    }
    standing = ladder_standing(ladder, high_score, pace_constant)
    if standing is None:
        return fields
    fields["tier_display"] = (
        "No rank" if standing.reached is None else standing.reached.name
    )
    fields["tier_sort"] = standing.passed
    if standing.at_top:
        fields["next_tier_display"] = "Top rank"
    elif standing.next_gap is not None:
        next_gap = standing.next_gap
        fields["next_tier_display"] = f"{next_gap.gap_text} to {next_gap.rank.name}"
        fields["next_tier_sort"] = next_gap.gap
        fields["next_tier_tooltip"] = (
            f"{next_gap.rank.name} at {next_gap.threshold_text} · "
            f"{next_gap.points_text} to go"
        )
    return fields


def rank_position(ladder: list[Rank], score: float, standing: LadderStanding) -> float:
    """Return where a score sits on its ladder: the ranks reached plus a fraction.

    The fraction is how far the score is from the last rank reached to the
    next one, at least 0 and below 1, because the walk stops at the first
    threshold above the score. At the top rank the position is the rank
    count. Below the first rank there is no lower threshold, so the position
    is ``1 / (1 + gap / 100)``, ``gap`` being the next-rank gap by its own
    rule. On a time-scored scenario that gap is a ratio of times, which the
    scenario's arbitrary starting constant doesn't move, where a ratio of
    scores would. With no gap, a score of zero or less on score math, it is 0.
    """
    if standing.at_top:
        return float(standing.passed)
    if standing.passed == 0:
        if standing.next_gap is None:
            return 0.0
        return 1 / (1 + standing.next_gap.gap / 100)
    lower = ladder[standing.passed - 1].threshold
    upper = ladder[standing.passed].threshold
    return standing.passed + (score - lower) / (upper - lower)


def band_percent(fraction: float) -> int:
    """Show how far a score is toward the next rank, in whole percent rounded down.

    The inner round strips float noise, as the Next Rank gap's does, but it
    can carry a score a hair under the next threshold to 100, which would
    read as the next rank. The cap keeps it at 99.
    """
    return min(99, math.floor(round(fraction * 100, 6)))


def typical_tier_fields(
    ladder: list[Rank],
    typical_score: float | None,
    pace_constant: float | None = None,
    *,
    not_recent: bool = False,
) -> PlaylistScenarioRow:
    """Compute a benchmark row's Typical Rank fields from its typical score.

    ``typical_tier_sort`` is the unrounded rank position, and ``N/A`` sorts as
    null. The hover is the gap to the next rank, as Next Rank's figures read,
    then, on a value that is not recent, a line saying so. The rank, the
    percent and the gap all count from the exact median, never the rounded
    value the Typical Score cell shows.
    """
    fields: PlaylistScenarioRow = {
        "typical_tier_display": "N/A",
        "typical_tier_sort": None,
        "typical_tier_hover": None,
    }
    if typical_score is None:
        return fields
    standing = ladder_standing(ladder, typical_score, pace_constant)
    if standing is None:
        return fields
    position = rank_position(ladder, typical_score, standing)
    fields["typical_tier_sort"] = position
    if standing.reached is None:
        fields["typical_tier_display"] = "No rank"
    elif standing.at_top:
        fields["typical_tier_display"] = standing.reached.name
    else:
        percent = band_percent(position - standing.passed)
        fields["typical_tier_display"] = f"{standing.reached.name} · {percent}%"
    lines = []
    if standing.next_gap is not None:
        next_gap = standing.next_gap
        lines.append(
            f"{next_gap.gap_text} to {next_gap.rank.name} · "
            f"{next_gap.points_text} to go"
        )
    if not_recent:
        lines.append(TYPICAL_RANK_OLD_LINE)
    fields["typical_tier_hover"] = "\n".join(lines) or None
    return fields


def typical_row_fields(
    scenario_name: str,
    ladder: list[Rank] | None,
    typical: TypicalSnapshot,
    pace_basis: PaceBasis | None = None,
) -> PlaylistScenarioRow:
    """Compute a row's Typical Score fields, and on a benchmark its Typical Rank's.

    ``ladder`` is ``None`` on a playlist's table, whose rows carry no Typical
    Rank fields. ``pace_basis`` is the scenario's, read once for the row; the
    rank is measured by pace only when every run behind the value is of its
    version. A value is marked not recent only when it is known: an unknown
    one reads Too few runs, and unknown is not the same as old.
    """
    fields: PlaylistScenarioRow = {
        "typical_score_display": "N/A",
        "typical_score_sort": None,
        "typical_not_recent": False,
        "typical_score_hover": None,
    }
    median = None
    pace_constant = None
    not_recent = False
    entry = typical.values.get(scenario_name)
    if entry is not None:
        value, total = entry
        median = value.median
        if median is None:
            fields["typical_score_display"] = TOO_FEW_RUNS_TEXT
            fields["typical_score_hover"] = {
                "lead": below_minimum_text(value),
                "lines": [],
            }
        else:
            not_recent = not typical_score_recency(value, typical.moment).recent
            hover = typical_score_hover(value, total, typical.moment)
            fields["typical_score_display"] = format_typical_score(median, value.runs)
            fields["typical_score_sort"] = median
            fields["typical_not_recent"] = not_recent
            fields["typical_score_hover"] = {
                "lead": (
                    f"{hover.opening} {TYPICAL_SCORE_OLD_SENTENCE}"
                    if not_recent
                    else hover.opening
                ),
                "lines": [list(line) for line in hover.lines],
            }
            pace_constant = eligible_pace_constant(pace_basis, *value.runs)
    if ladder is not None:
        fields.update(
            typical_tier_fields(ladder, median, pace_constant, not_recent=not_recent)
        )
    return fields


def _get_local_stats(scenario_name: str) -> ScenarioStats | None:
    if not is_scenario_in_database(scenario_name):
        return None
    return get_scenario_stats(scenario_name)


def _get_personal_best_run(scenario_name: str) -> RunData | None:
    if not is_scenario_in_database(scenario_name):
        return None
    return get_personal_best_run(scenario_name)


def personal_best_cm360(run_data: RunData | None) -> float | None:
    """Return a PB run's sensitivity in cm/360, as the PB cm/360 column shows it.

    A run's sensitivity is cm/360 either natively or by the parser's
    conversion from the file's own increment and DPI. It stays unknown only
    for a legacy run that carries neither field, and those stay unknown
    instead of mislabeled.
    """
    if run_data is None or run_data.sens_scale != "cm/360":
        return None
    return run_data.horizontal_sens


def format_playlist_scenario_rank_row(  # noqa: PLR0913
    scenario_name: str,
    playlist_order: int,
    rank_info: ScenarioRankInfo,
    scenario_stats: ScenarioStats | None = None,
    personal_best_run: RunData | None = None,
    *,
    leaderboard_id: int | None = None,
    ladder: list[Rank] | None = None,
    pace_constant: float | None = None,
    group: ScenarioGroup | None = None,
    generation_token: str | None = None,
    playlist_code: str | None = None,
    mark_unresolved_pending: bool = False,
) -> PlaylistScenarioRow:
    """Create one complete AG Grid row with display and numeric sort values.

    ``leaderboard_id`` is the scenario's entry in the name-to-ID mapping, or
    ``None`` for a scenario the app hasn't resolved. ``ladder`` is ``None`` on
    a playlist's table, whose rows carry no Rank or Next Rank fields, and the
    scenario's ladder on a benchmark's table. ``pace_constant`` is set only
    where the Next Rank gap is measured by pace. ``group`` is the scenario's
    category and subcategory, or ``None`` on a table without groups, whose
    rows carry none of the group fields.
    """
    date_last_played = None
    number_of_runs = 0
    high_score = None
    if scenario_stats is not None:
        date_last_played = scenario_stats.date_last_played
        number_of_runs = scenario_stats.number_of_runs
        high_score = scenario_stats.high_score

    pb_cm360 = personal_best_cm360(personal_best_run)
    # Hit accuracy, the figure KovaaK's shows for the run. Not damage done over
    # damage possible: the leaderboard field named ``accuracyDamage`` holds
    # hits over shots too (docs/kovaaks_api_notes.md).
    pb_accuracy = None if personal_best_run is None else personal_best_run.accuracy
    row: PlaylistScenarioRow = {
        "scenario": scenario_name,
        "leaderboard_id": _format_id(leaderboard_id),
        "playlist_order": playlist_order,
        "status": rank_info.status.value,
        "position_display": "N/A",
        "position_sort": None,
        "total_display": "N/A",
        "total_sort": None,
        "percentile_display": "N/A",
        "percentile_sort": None,
        "last_played_sort": (
            date_last_played.timestamp() if date_last_played is not None else None
        ),
        "runs_display": _format_int(number_of_runs),
        "runs_sort": number_of_runs,
        "pb_score_display": _format_score(high_score),
        "pb_score_sort": high_score,
        "pb_timestamp_sort": (
            personal_best_run.datetime_object.timestamp()
            if personal_best_run is not None
            else None
        ),
        "pb_cm360_display": _format_score(pb_cm360),
        "pb_cm360_sort": pb_cm360,
        "pb_accuracy_display": _format_accuracy(pb_accuracy),
        # Unrounded, so the order never disagrees with the rounded display.
        "pb_accuracy_sort": None if pb_accuracy is None else pb_accuracy * 100,
    }
    if ladder is not None:
        row.update(benchmark_rank_fields(ladder, high_score, pace_constant))
    if group is not None:
        row.update(scenario_group_fields(group))

    if rank_info.status == ScenarioRankStatus.RANKED:
        row["position_display"] = _format_int(rank_info.rank)
        row["position_sort"] = rank_info.rank
        row["total_display"] = _format_int(rank_info.total_players)
        row["total_sort"] = rank_info.total_players
        row["percentile_display"] = _format_percentile(rank_info.percentile)
        row["percentile_sort"] = rank_info.percentile
    elif rank_info.status == ScenarioRankStatus.UNRANKED:
        row["position_display"] = "Unranked"
        row["total_display"] = _format_int(rank_info.total_players)
        row["total_sort"] = rank_info.total_players

    if generation_token is not None:
        row["generation_token"] = generation_token
        row["position_pending"] = mark_unresolved_pending and not (
            rank_info.status == ScenarioRankStatus.UNRANKED
            or rank_info.rank is not None
        )
        row["total_pending"] = (
            mark_unresolved_pending and rank_info.total_players is None
        )
        row["percentile_pending"] = (
            mark_unresolved_pending and rank_info.percentile is None
        )
    if playlist_code is not None:
        row["href"] = scenario_run_history_href(scenario_name, playlist_code)
    return row


def _lookup_rank_info(
    scenario_name: str,
    *,
    allow_network: bool,
) -> ScenarioRankInfo:
    config = get_config()
    username, steam_id = get_identity()
    # Phase 2 hydrates once before its fan-out; phase 1 is cache-only. Neither
    # per-scenario path may start another total-play hydration.
    return get_scenario_rank_info(
        scenario_name,
        username,
        steam_id,
        config.scenario_metadata_cache_ttl_hours,
        config.scenario_rank_cache_ttl_hours,
        config.leaderboard_total_cache_ttl_hours,
        allow_network=allow_network,
        allow_hydration=False,
    )


def _unknown_rank_info(scenario_name: str, exc: Exception) -> ScenarioRankInfo:
    logger.warning(
        'Failed to fetch playlist scenario rank for "%s"',
        scenario_name,
        exc_info=True,
    )
    return ScenarioRankInfo(
        status=ScenarioRankStatus.UNKNOWN,
        scenario_name=scenario_name,
        error_message=str(exc),
    )


def _hydrate_playlist_leaderboard_ids(scenario_names: list[str]) -> None:
    """Hydrate the leaderboard mapping once before the phase-2 fan-out."""
    config = get_config()
    username = get_kovaaks_username()
    if not username:
        return
    try:
        if all(get_cached_leaderboard_id(name) is not None for name in scenario_names):
            return
        hydrate_leaderboard_id_cache(
            username,
            config.scenario_metadata_cache_ttl_hours,
        )
    except requests.RequestException as exc:
        # Expected whenever KovaaK's is slow or unreachable, and it recurs on
        # every open, so it logs a one-line summary rather than a traceback.
        logger.warning(
            "Failed to hydrate leaderboard metadata for playlist open: %s",
            request_exception_summary(exc),
        )
    except UnknownKovaaksUserError as exc:
        # An unknown configured username is rejected here on every open while
        # a scenario stays unmapped. The message names the user, and a
        # traceback per open would bury the log.
        logger.warning(
            "Failed to hydrate leaderboard metadata for playlist open: %s",
            exc,
        )
    except Exception:  # noqa: BLE001
        # Best-effort: the per-scenario path can still resolve ranks without
        # this optimization, and it converts expected API failures itself.
        # What reaches here is unexpected, so it keeps the traceback.
        logger.warning(
            "Failed to hydrate leaderboard metadata for playlist open",
            exc_info=True,
        )


def _build_row(  # noqa: PLR0913
    scenario_name: str,
    playlist_order: int,
    rank_info: ScenarioRankInfo,
    generation_token: str,
    playlist_code: str,
    *,
    ladder: list[Rank] | None,
    group: ScenarioGroup | None,
    typical: TypicalSnapshot,
    mark_unresolved_pending: bool,
) -> PlaylistScenarioRow:
    """Re-read local data and build a complete transaction-safe row.

    The typical fields come from ``typical``, never from a fresh read, so
    every row path gives a scenario the same typical cells.
    """
    try:
        scenario_stats = _get_local_stats(scenario_name)
    except Exception:  # noqa: BLE001
        logger.warning(
            'Failed to read local stats for "%s"', scenario_name, exc_info=True
        )
        scenario_stats = None
    try:
        personal_best_run = _get_personal_best_run(scenario_name)
    except Exception:  # noqa: BLE001
        logger.warning(
            'Failed to read the personal best for "%s"',
            scenario_name,
            exc_info=True,
        )
        personal_best_run = None
    # Read from the mapping, the value the app itself sends to KovaaK's, and
    # read on every row path: the fill's rows and a cancelled fill's rebuild
    # replace a row whole, so a row built without it would blank the cell. The
    # fill looks the position up first, so its row carries an ID it just
    # learned.
    try:
        leaderboard_id = get_cached_leaderboard_id(scenario_name)
    except Exception:  # noqa: BLE001 - a bad mapping read must not cost the row
        logger.warning(
            'Failed to read the leaderboard ID for "%s"',
            scenario_name,
            exc_info=True,
        )
        leaderboard_id = None
    pace_basis = None
    entry = typical.values.get(scenario_name)
    # Only a row with a ladder and a PB or a typical score shows a gap, so a
    # playlist's table never reads a performance file.
    if ladder and (
        personal_best_run is not None
        or (entry is not None and entry[0].median is not None)
    ):
        try:
            pace_basis = get_pace_basis(scenario_name)
        except Exception:  # noqa: BLE001 -- a fill worker's exception ends the fill.
            # The lookup handles a missing or unreadable performance file
            # itself. Anything else must cost the pace gaps only, never the
            # row, so each falls back to a percentage of its score.
            logger.warning(
                'Failed to tell whether "%s" is time-scored',
                scenario_name,
                exc_info=True,
            )
    pace_constant = (
        eligible_pace_constant(pace_basis, personal_best_run)
        if ladder and personal_best_run is not None
        else None
    )
    row = format_playlist_scenario_rank_row(
        scenario_name,
        playlist_order,
        rank_info,
        scenario_stats,
        personal_best_run,
        leaderboard_id=leaderboard_id,
        ladder=ladder,
        pace_constant=pace_constant,
        group=group,
        generation_token=generation_token,
        playlist_code=playlist_code,
        mark_unresolved_pending=mark_unresolved_pending,
    )
    row.update(typical_row_fields(scenario_name, ladder, typical, pace_basis))
    return row


def build_playlist_scenario_rank_rows(
    playlist_code: str,
    generation_token: str,
    *,
    typical: TypicalSnapshot,
) -> list[PlaylistScenarioRow]:
    """Build phase-1 rows from local data and TTL-ignored disk caches only.

    ``typical`` is the table build's snapshot, which its fill gets too.
    """
    playlist = get_playlist_by_code(playlist_code)
    if playlist is None:
        return []

    rows = []
    ladders = _scenario_ladders(playlist)
    groups = playlist_scenario_groups(playlist)
    for index, (scenario, ladder, group) in enumerate(
        zip(playlist.scenarios, ladders, groups, strict=True)
    ):
        try:
            rank_info = _lookup_rank_info(scenario.name, allow_network=False)
        except Exception as exc:  # noqa: BLE001
            rank_info = _unknown_rank_info(scenario.name, exc)
        rows.append(
            _build_row(
                scenario.name,
                index,
                rank_info,
                generation_token,
                playlist_code,
                ladder=ladder,
                group=group,
                typical=typical,
                mark_unresolved_pending=True,
            )
        )
    return rows


def _next_terminal_order_locked() -> int:
    global _terminal_sequence  # noqa: PLW0603
    _terminal_sequence += 1
    return _terminal_sequence


def _enforce_tombstone_limit_locked() -> None:
    """Evict consumed tombstones first, oldest first within each class."""
    terminal_items = [
        (token, state)
        for token, state in _FILL_REGISTRY.items()
        if state.terminal is not None
    ]
    excess = len(terminal_items) - FILL_TOMBSTONE_LIMIT
    if excess <= 0:
        return
    terminal_items.sort(
        key=lambda item: (
            0 if item[1].consumed else 1,
            item[1].terminal_order or 0,
        )
    )
    for token, _state in terminal_items[:excess]:
        del _FILL_REGISTRY[token]


def _transition_terminal_locked(state: _FillState, terminal: FillTerminal) -> None:
    if state.terminal is not None:
        return
    if terminal == "cancelled":
        state.cancel_event.set()
    state.terminal = terminal
    state.terminal_order = _next_terminal_order_locked()
    _enforce_tombstone_limit_locked()


def _cancel_live_fills_locked() -> None:
    for state in list(_FILL_REGISTRY.values()):
        if state.terminal is None:
            _transition_terminal_locked(state, "cancelled")


def start_playlist_scenario_fill(
    playlist_code: str,
    generation_token: str,
    *,
    typical: TypicalSnapshot,
) -> bool:
    """Cancel older fills, register this generation, and start its daemon.

    ``typical`` is the snapshot phase 1 built its rows from.
    """
    playlist = get_playlist_by_code(playlist_code)
    if playlist is None:
        return False
    scenario_names = tuple(scenario.name for scenario in playlist.scenarios)
    state = _FillState(
        playlist_code=playlist_code,
        scenario_names=scenario_names,
        scenario_ladders=_scenario_ladders(playlist),
        scenario_groups=playlist_scenario_groups(playlist),
        typical=typical,
        total=len(scenario_names),
        unresolved_indices=set(range(len(scenario_names))),
    )
    with _FILL_REGISTRY_LOCK:
        _cancel_live_fills_locked()
        _FILL_REGISTRY[generation_token] = state

    thread = threading.Thread(
        target=_run_playlist_scenario_fill,
        args=(
            generation_token,
            scenario_names,
            state.scenario_ladders,
            state.scenario_groups,
            typical,
            state.cancel_event,
        ),
        name=f"playlist-fill-{generation_token[:8]}",
        daemon=True,
    )
    thread.start()
    return True


def _fetch_fill_row(  # noqa: PLR0913
    generation_token: str,
    playlist_code: str,
    playlist_order: int,
    scenario_name: str,
    ladder: list[Rank] | None,
    group: ScenarioGroup | None,
    typical: TypicalSnapshot,
    cancel_event: threading.Event,
) -> tuple[int, ScenarioRankInfo, PlaylistScenarioRow] | None:
    if cancel_event.is_set():
        return None
    try:
        rank_info = _lookup_rank_info(scenario_name, allow_network=True)
    except Exception as exc:  # noqa: BLE001
        rank_info = _unknown_rank_info(scenario_name, exc)
    row = _build_row(
        scenario_name,
        playlist_order,
        rank_info,
        generation_token,
        playlist_code,
        ladder=ladder,
        group=group,
        typical=typical,
        mark_unresolved_pending=False,
    )
    return playlist_order, rank_info, row


def _record_fill_result(
    generation_token: str,
    playlist_order: int,
    rank_info: ScenarioRankInfo,
    row: PlaylistScenarioRow,
) -> None:
    with _FILL_REGISTRY_LOCK:
        state = _FILL_REGISTRY.get(generation_token)
        if state is None or state.terminal is not None:
            return
        state.pending_updates.append(row)
        state.unresolved_indices.discard(playlist_order)
        state.done_count += 1
        if rank_info.status == ScenarioRankStatus.UNKNOWN:
            state.unknown_count += 1
        elif rank_info.served_stale is True:
            state.stale_count += 1


def _run_playlist_scenario_fill(  # noqa: PLR0913
    generation_token: str,
    scenario_names: tuple[str, ...],
    scenario_ladders: tuple[list[Rank] | None, ...],
    scenario_groups: tuple[ScenarioGroup | None, ...],
    typical: TypicalSnapshot,
    cancel_event: threading.Event,
) -> None:
    """Hydrate once, fan out rank lookups, and stream results to the registry."""
    stopwatch = Stopwatch()
    stopwatch.start()
    playlist_code = ""
    completed_normally = False
    completion_metrics: tuple[Counter[str], int, int] | None = None
    try:
        if not cancel_event.is_set():
            _hydrate_playlist_leaderboard_ids(list(scenario_names))

        with _FILL_REGISTRY_LOCK:
            state = _FILL_REGISTRY.get(generation_token)
            playlist_code = state.playlist_code if state is not None else ""

        if playlist_code and not cancel_event.is_set():
            max_workers = max(1, PLAYLIST_RANK_MAX_WORKERS)
            with ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix="playlist-fetch",
            ) as executor:
                futures = [
                    executor.submit(
                        _fetch_fill_row,
                        generation_token,
                        playlist_code,
                        index,
                        scenario_name,
                        ladder,
                        group,
                        typical,
                        cancel_event,
                    )
                    for index, (scenario_name, ladder, group) in enumerate(
                        zip(
                            scenario_names,
                            scenario_ladders,
                            scenario_groups,
                            strict=True,
                        )
                    )
                ]
                for future in as_completed(futures):
                    result = future.result()
                    if result is None:
                        continue
                    playlist_order, rank_info, row = result
                    _record_fill_result(
                        generation_token,
                        playlist_order,
                        rank_info,
                        row,
                    )
        completed_normally = True
    except Exception:  # noqa: BLE001
        logger.exception(
            "Playlist scenario fill failed for generation %s",
            generation_token,
        )
    finally:
        stopwatch.stop()
        with _FILL_REGISTRY_LOCK:
            state = _FILL_REGISTRY.get(generation_token)
            if state is not None and state.terminal is None:
                if completed_normally:
                    _transition_terminal_locked(state, "complete")
                    status_counts = Counter(
                        {
                            "unknown": state.unknown_count,
                            "stale": state.stale_count,
                            "fresh": state.done_count
                            - state.unknown_count
                            - state.stale_count,
                        }
                    )
                    completion_metrics = status_counts, state.done_count, state.total
                else:
                    _transition_terminal_locked(state, "cancelled")

    if completion_metrics is None:
        return
    status_counts, done_count, total = completion_metrics
    logger.info(
        "Filled playlist scenario rows for %s (%d/%d: %d fresh, %d stale, "
        "%d unknown) in %.2f seconds",
        playlist_code,
        done_count,
        total,
        status_counts["fresh"],
        status_counts["stale"],
        status_counts["unknown"],
        stopwatch.elapsed(),
    )


def _build_cancelled_finalization_rows(  # noqa: PLR0913
    playlist_code: str,
    scenario_names: tuple[str, ...],
    scenario_ladders: tuple[list[Rank] | None, ...],
    scenario_groups: tuple[ScenarioGroup | None, ...],
    typical: TypicalSnapshot,
    generation_token: str,
    unresolved_indices: list[int],
) -> list[PlaylistScenarioRow]:
    rows = []
    for index in unresolved_indices:
        scenario_name = scenario_names[index]
        try:
            rank_info = _lookup_rank_info(scenario_name, allow_network=False)
        except Exception as exc:  # noqa: BLE001
            rank_info = _unknown_rank_info(scenario_name, exc)
        rows.append(
            _build_row(
                scenario_name,
                index,
                rank_info,
                generation_token,
                playlist_code,
                ladder=scenario_ladders[index],
                group=scenario_groups[index],
                typical=typical,
                mark_unresolved_pending=False,
            )
        )
    return rows


def drain_playlist_scenario_fill(
    generation_token: str | None,
) -> PlaylistScenarioFillDrain | None:
    """Drain one generation and consume terminal one-shots atomically once."""
    if not generation_token:
        return None

    with _FILL_REGISTRY_LOCK:
        state = _FILL_REGISTRY.get(generation_token)
        if state is None:
            return None

        updates = list(state.pending_updates)
        state.pending_updates.clear()
        consuming_terminal = state.terminal is not None and not state.consumed
        unresolved_indices: list[int] = []
        scenario_names: tuple[str, ...] = ()
        scenario_ladders: tuple[list[Rank] | None, ...] = ()
        scenario_groups: tuple[ScenarioGroup | None, ...] = ()
        if consuming_terminal:
            if state.terminal == "cancelled":
                unresolved_indices = sorted(state.unresolved_indices)
                scenario_names = state.scenario_names
                scenario_ladders = state.scenario_ladders
                scenario_groups = state.scenario_groups
            state.consumed = True
            state.unresolved_indices.clear()
            state.scenario_names = ()
            state.scenario_ladders = ()
            state.scenario_groups = ()

        snapshot = PlaylistScenarioFillDrain(
            generation_token=generation_token,
            updates=updates,
            done_count=state.done_count,
            unknown_count=state.unknown_count,
            stale_count=state.stale_count,
            total=state.total,
            terminal=state.terminal,
            consuming_terminal=consuming_terminal,
        )

    if snapshot.terminal == "cancelled" and snapshot.consuming_terminal:
        final_rows = _build_cancelled_finalization_rows(
            state.playlist_code,
            scenario_names,
            scenario_ladders,
            scenario_groups,
            state.typical,
            generation_token,
            unresolved_indices,
        )
        return PlaylistScenarioFillDrain(
            generation_token=snapshot.generation_token,
            updates=[*snapshot.updates, *final_rows],
            done_count=snapshot.done_count,
            unknown_count=snapshot.unknown_count,
            stale_count=snapshot.stale_count,
            total=snapshot.total,
            terminal=snapshot.terminal,
            consuming_terminal=True,
        )
    return snapshot
