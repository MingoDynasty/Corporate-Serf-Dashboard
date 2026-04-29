"""Build playlist scenario table rows for the M1 playlist overview page."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from source.config.config_service import config
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from source.kovaaks.api_service import get_scenario_rank_info
from source.kovaaks.data_service import get_playlist_by_code

PLAYLIST_RANK_MAX_WORKERS = 4
logger = logging.getLogger(__name__)

RankLookup = Callable[
    [str, str | None, str | None, int, int, int],
    ScenarioRankInfo,
]


def _format_int(value: int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,}"


def _format_percentile(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}%"


def format_playlist_scenario_rank_row(
    scenario_name: str,
    playlist_order: int,
    rank_info: ScenarioRankInfo,
) -> dict[str, str | int | float | None]:
    """Create one AG Grid row with separate display and numeric sort values."""
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
    rank_lookup: RankLookup,
) -> ScenarioRankInfo:
    return rank_lookup(
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
    rank_lookup: RankLookup = get_scenario_rank_info,
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
                rank_lookup,
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
            )

    return [row for row in rows if row is not None]
