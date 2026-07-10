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
)

logger = logging.getLogger(__name__)

OverviewRow = dict[str, str | int | float | None]


def _format_int(value: int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,}"


def _format_percentile_with_coverage(
    value: float | None,
    cached_count: int,
    scenario_count: int,
) -> str:
    # The coverage suffix keeps partial aggregates honest: a median over 2 of
    # 20 scenarios must not read as playlist-wide truth.
    if value is None:
        return "N/A"
    return f"{value:.2f}% · {cached_count}/{scenario_count}"


def _cached_rank_percentile(scenario_name: str) -> float | None:
    """Read a scenario's cached percentile without any network I/O."""
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
        )
    except Exception:  # noqa: BLE001 - one bad cache entry must not empty the page
        logger.warning(
            "Failed to read cached rank info for %s",
            scenario_name,
            exc_info=True,
        )
        return None
    if rank_info.status != ScenarioRankStatus.RANKED:
        return None
    return rank_info.percentile


def format_playlist_overview_row(
    display_label: str,
    playlist: PlaylistData,
    stats_by_scenario: dict[str, ScenarioStats],
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
    for scenario_name in scenario_names:
        # Percentile aggregates cover played scenarios with cached rank info
        # (proposal R9): a scenario ranked in cache but absent locally (e.g.
        # pruned CSVs) is excluded, so coverage can never exceed Played.
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
        percentile = _cached_rank_percentile(scenario_name)
        if percentile is not None:
            percentiles.append((percentile, scenario_name))

    median_percentile: float | None = None
    lowest_percentile: float | None = None
    lowest_scenario: str | None = None
    if percentiles:
        median_percentile = statistics.median(
            [percentile for percentile, _ in percentiles]
        )
        lowest_percentile, lowest_scenario = min(percentiles)

    cached_count = len(percentiles)
    is_benchmark = any(scenario.ranks for scenario in playlist.scenarios)
    return {
        "name": display_label,
        "code": playlist.code,
        "type_display": "Benchmark" if is_benchmark else "Playlist",
        "played_display": f"{played_count}/{scenario_count}",
        "played_sort": (played_count / scenario_count) if scenario_count else None,
        "runs_display": _format_int(total_runs),
        "runs_sort": total_runs,
        "last_played_sort": (
            last_played.timestamp() if last_played is not None else None
        ),
        "stalest_scenario": stalest_scenario,
        "stalest_sort": (
            stalest_played.timestamp() if stalest_played is not None else None
        ),
        "median_percentile_display": _format_percentile_with_coverage(
            median_percentile,
            cached_count,
            scenario_count,
        ),
        "median_percentile_sort": median_percentile,
        "lowest_percentile_display": _format_percentile_with_coverage(
            lowest_percentile,
            cached_count,
            scenario_count,
        ),
        "lowest_percentile_sort": lowest_percentile,
        "lowest_scenario": lowest_scenario,
    }


def build_playlist_overview_rows() -> list[OverviewRow]:
    """
    Build one overview row per loaded playlist, in selector label order.

    Reads only local run data and the existing rank caches
    (``allow_network=False``); the overview page must never trigger KovaaK's
    API calls. Percentile cells fill in as drilling into playlists warms the
    rank cache. Scenario stats are snapshotted once at entry (R11) so all
    rows of one render agree about every shared scenario.
    """
    stats_by_scenario = get_scenario_stats_snapshot()
    rows: list[OverviewRow] = []
    for option in get_playlist_selector_options():
        playlist = get_playlist_by_code(option["value"])
        if playlist is None:
            continue
        rows.append(
            format_playlist_overview_row(
                option["label"],
                playlist,
                stats_by_scenario,
            )
        )
    return rows
