"""Build playlist-level overview rows for the playlists landing page."""

import logging
import statistics
from datetime import datetime

from source.config.config_service import get_config
from source.kovaaks.api_models import ScenarioRankStatus
from source.kovaaks.api_service import get_scenario_rank_info
from source.kovaaks.data_models import PlaylistData, ScenarioStats
from source.kovaaks.data_service import (
    get_playlist_by_code,
    get_playlist_selector_options,
    get_scenario_stats_snapshot,
    get_user_root_playlist_codes,
)
from source.kovaaks.playlist_visibility_service import get_shown_playlist_codes

logger = logging.getLogger(__name__)

OverviewRow = dict[str, str | int | float | bool | None]


def _format_int(value: int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,}"


def _format_percentile_aggregate(
    value: float | None,
    resolved_count: int,
    played_count: int,
) -> str:
    if resolved_count != played_count:
        return f"{resolved_count}/{played_count} cached"
    if value is None:
        return "N/A"
    return f"{value:.2f}%"


def _cached_rank_resolution(
    scenario_name: str,
    *,
    record_activity: bool = True,
) -> tuple[bool, float | None]:
    """Classify one scenario from a single cache-only rank lookup.

    UNRANKED is resolved without a percentile. RANKED is resolved only when
    the totals cache supplied a percentile; UNKNOWN and cache read failures
    remain unresolved.
    """
    config = get_config()
    try:
        rank_info = get_scenario_rank_info(
            scenario_name,
            config.kovaaks_username,
            config.steam_id,
            config.scenario_metadata_cache_ttl_hours,
            config.scenario_rank_cache_ttl_hours,
            config.leaderboard_total_cache_ttl_hours,
            allow_network=False,
            record_activity=record_activity,
        )
    except Exception:  # noqa: BLE001 - one bad cache entry must not empty the page
        logger.warning(
            "Failed to read cached rank info for %s",
            scenario_name,
            exc_info=True,
        )
        return False, None
    if rank_info.status == ScenarioRankStatus.UNRANKED:
        return True, None
    if rank_info.status == ScenarioRankStatus.RANKED:
        return rank_info.percentile is not None, rank_info.percentile
    return False, None


def format_playlist_overview_row(
    display_label: str,
    playlist: PlaylistData,
    stats_by_scenario: dict[str, ScenarioStats],
    *,
    record_activity: bool = True,
) -> OverviewRow:
    """Create one overview AG Grid row with separate display and sort values.

    ``stats_by_scenario`` is the callback-wide snapshot (R11): every row of
    one render is built from the same mapping, so a run recorded mid-render
    cannot make overlapping playlists disagree about a shared scenario.
    """
    scenario_names = [scenario.name for scenario in playlist.scenarios]
    scenario_count = len(scenario_names)

    played_count = 0
    total_runs = 0
    last_played: datetime | None = None
    stalest_played: datetime | None = None
    stalest_scenario: str | None = None
    percentiles: list[tuple[float, str]] = []
    resolved_count = 0
    for scenario_name in scenario_names:
        # Percentile aggregates cover played scenarios (proposal R2/R18): a
        # scenario ranked in cache but absent locally (e.g. pruned CSVs) is
        # excluded, so resolution can never exceed Played.
        stats = stats_by_scenario.get(scenario_name)
        if stats is None:
            continue
        played_count += 1
        total_runs += stats.number_of_runs
        if last_played is None or stats.date_last_played > last_played:
            last_played = stats.date_last_played
        if stalest_played is None or stats.date_last_played < stalest_played:
            stalest_played = stats.date_last_played
            stalest_scenario = scenario_name
        resolved, percentile = _cached_rank_resolution(
            scenario_name,
            record_activity=record_activity,
        )
        if resolved:
            resolved_count += 1
        if percentile is not None:
            percentiles.append((percentile, scenario_name))

    percentile_aggregates_resolved = resolved_count == played_count
    median_percentile: float | None = None
    lowest_percentile: float | None = None
    lowest_scenario: str | None = None
    if percentile_aggregates_resolved and percentiles:
        median_percentile = statistics.median(
            [percentile for percentile, _ in percentiles]
        )
        lowest_percentile, lowest_scenario = min(percentiles)

    is_benchmark = any(scenario.ranks for scenario in playlist.scenarios)
    return {
        "name": display_label,
        "code": playlist.code,
        "type_display": "Benchmark" if is_benchmark else "Playlist",
        "played_display": f"{played_count}/{scenario_count}",
        "played_sort": (played_count / scenario_count) if scenario_count else None,
        "played_count": played_count,
        "runs_display": _format_int(total_runs),
        "runs_sort": total_runs,
        "last_played_sort": (
            last_played.timestamp() if last_played is not None else None
        ),
        "stalest_scenario": stalest_scenario,
        "stalest_sort": (
            stalest_played.timestamp() if stalest_played is not None else None
        ),
        "percentile_aggregates_resolved": percentile_aggregates_resolved,
        "median_percentile_display": _format_percentile_aggregate(
            median_percentile,
            resolved_count,
            played_count,
        ),
        "median_percentile_sort": median_percentile,
        "lowest_percentile_display": _format_percentile_aggregate(
            lowest_percentile,
            resolved_count,
            played_count,
        ),
        "lowest_percentile_sort": lowest_percentile,
        "lowest_scenario": lowest_scenario,
    }


def build_playlist_overview_rows(
    include_hidden: bool = False,
    *,
    record_activity: bool = True,
) -> list[OverviewRow]:
    """
    Build one overview row per visible playlist, in selector label order.

    Reads only local run data and the existing rank caches
    (``allow_network=False``); the overview page must never trigger KovaaK's
    API calls. Percentile cells fill in as drilling into playlists warms the
    rank cache. Scenario stats are snapshotted once at entry (R11) so all
    rows of one render agree about every shared scenario.

    ``include_hidden=True`` (the overview's "show hidden" mode) adds hidden
    playlists' rows; every row carries a ``hidden`` flag for row muting and
    the hide/unhide action cell. Automated warmup-interval builds pass
    ``record_activity=False`` so cache polling does not postpone the worker.
    """
    shown_codes = get_shown_playlist_codes()
    # Only user-root playlists can be deleted (bundled benchmarks offer hide,
    # not delete — proposal R5); the delete action cell keys off this flag.
    deletable_codes = get_user_root_playlist_codes()
    stats_by_scenario = get_scenario_stats_snapshot()
    rows: list[OverviewRow] = []
    for option in get_playlist_selector_options():
        hidden = option["value"] not in shown_codes
        if hidden and not include_hidden:
            continue
        playlist = get_playlist_by_code(option["value"])
        if playlist is None:
            continue
        row = format_playlist_overview_row(
            option["label"],
            playlist,
            stats_by_scenario,
            record_activity=record_activity,
        )
        row["hidden"] = hidden
        row["deletable"] = option["value"] in deletable_codes
        rows.append(row)
    return rows
