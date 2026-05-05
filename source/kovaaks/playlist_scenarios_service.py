"""Build playlist scenario table rows for the playlist overview page."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import logging

from source.config.config_service import config
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from source.kovaaks.api_service import get_scenario_rank_info
from source.kovaaks.data_models import ScenarioStats
from source.kovaaks.data_service import (
    get_playlist_by_code,
    get_scenario_stats,
    is_scenario_in_database,
)

PLAYLIST_RANK_MAX_WORKERS = 4
logger = logging.getLogger(__name__)


def _format_int(value: int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,}"


def _format_percentile(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}%"


def _format_score(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _format_last_played(value: datetime | None) -> str:
    if value is None:
        return "N/A"
    return value.strftime("%Y-%m-%d")


def _get_local_stats(scenario_name: str) -> ScenarioStats | None:
    if not is_scenario_in_database(scenario_name):
        return None
    return get_scenario_stats(scenario_name)


def format_playlist_scenario_rank_row(
    scenario_name: str,
    playlist_order: int,
    rank_info: ScenarioRankInfo,
    scenario_stats: ScenarioStats | None = None,
) -> dict[str, str | int | float | None]:
    """Create one AG Grid row with separate display and numeric sort values."""
    date_last_played = None
    number_of_runs = 0
    high_score = None
    if scenario_stats is not None:
        date_last_played = scenario_stats.date_last_played
        number_of_runs = scenario_stats.number_of_runs
        high_score = scenario_stats.high_score

    row: dict[str, str | int | float | None] = {
        "scenario": scenario_name,
        "playlist_order": playlist_order,
        "status": rank_info.status.value,
        "rank_display": "N/A",
        "rank_sort": None,
        "total_display": "N/A",
        "total_sort": None,
        "percentile_display": "N/A",
        "percentile_sort": None,
        "last_played_display": _format_last_played(date_last_played),
        "last_played_sort": date_last_played.timestamp()
        if date_last_played is not None
        else None,
        "runs_display": _format_int(number_of_runs),
        "runs_sort": number_of_runs,
        "high_score_display": _format_score(high_score),
        "high_score_sort": high_score,
    }

    if rank_info.status == ScenarioRankStatus.RANKED:
        row["rank_display"] = _format_int(rank_info.rank)
        row["rank_sort"] = rank_info.rank
        row["total_display"] = _format_int(rank_info.total_players)
        row["total_sort"] = rank_info.total_players
        row["percentile_display"] = _format_percentile(rank_info.percentile)
        row["percentile_sort"] = rank_info.percentile
    elif rank_info.status == ScenarioRankStatus.UNRANKED:
        row["rank_display"] = "Unranked"
        row["total_display"] = _format_int(rank_info.total_players)
        row["total_sort"] = rank_info.total_players

    return row


def _lookup_rank_info(
    scenario_name: str,
) -> ScenarioRankInfo:
    return get_scenario_rank_info(
        scenario_name,
        config.kovaaks_username,
        config.steam_id,
        config.scenario_metadata_cache_ttl_hours,
        config.scenario_rank_cache_ttl_hours,
        config.leaderboard_total_cache_ttl_hours,
    )


def _unknown_rank_info(scenario_name: str, exc: Exception) -> ScenarioRankInfo:
    logger.warning(
        "Failed to fetch playlist scenario rank for %s",
        scenario_name,
        exc_info=True,
    )
    return ScenarioRankInfo(
        status=ScenarioRankStatus.UNKNOWN,
        scenario_name=scenario_name,
        error_message=str(exc),
    )


def build_playlist_scenario_rank_rows(
    playlist_code: str,
) -> list[dict[str, str | int | float | None]]:
    """
    Build all rank table rows for a playlist.

    Rank lookups run in parallel because each scenario is independent. Results
    are returned in playlist order so the first render matches KovaaK's order.
    """
    playlist = get_playlist_by_code(playlist_code)
    if playlist is None:
        return []

    max_workers = max(1, PLAYLIST_RANK_MAX_WORKERS)
    rows: list[dict[str, str | int | float | None] | None] = [
        None for _ in playlist.scenarios
    ]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _lookup_rank_info,
                scenario.name,
            ): (index, scenario.name)
            for index, scenario in enumerate(playlist.scenarios)
        }
        for future in as_completed(futures):
            index, scenario_name = futures[future]
            try:
                rank_info = future.result()
            except Exception as exc:  # noqa: BLE001
                rank_info = _unknown_rank_info(scenario_name, exc)
            rows[index] = format_playlist_scenario_rank_row(
                scenario_name,
                index,
                rank_info,
                _get_local_stats(scenario_name),
            )

    return [row for row in rows if row is not None]
