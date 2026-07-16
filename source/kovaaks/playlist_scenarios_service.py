"""Build and progressively refresh rows for the playlist scenarios page."""

import logging
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Literal, TypeAlias
from urllib.parse import urlencode

from source.config.config_service import get_config
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from source.kovaaks.api_service import (
    get_cached_leaderboard_id,
    get_scenario_rank_info,
    hydrate_leaderboard_id_cache,
)
from source.kovaaks.data_models import RunData, ScenarioStats
from source.kovaaks.data_service import (
    get_personal_best_run,
    get_playlist_by_code,
    get_scenario_stats,
    is_scenario_in_database,
)
from source.utilities.stopwatch import Stopwatch

PLAYLIST_RANK_MAX_WORKERS = 4
FILL_TOMBSTONE_LIMIT = 8

FillTerminal: TypeAlias = Literal["complete", "cancelled"]
RowValue: TypeAlias = str | int | float | bool | None
PlaylistScenarioRow: TypeAlias = dict[str, RowValue]

logger = logging.getLogger(__name__)
_FILL_REGISTRY_LOCK = threading.Lock()
_FILL_REGISTRY: dict[str, "_FillState"] = {}
_terminal_sequence = 0


@dataclass
class _FillState:
    """Mutable state for one generation, always guarded by the registry lock."""

    playlist_code: str
    scenario_names: tuple[str, ...]
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


def scenario_home_href(scenario_name: str, playlist_code: str) -> str:
    """Build the Home URL carried by each complete AG Grid row."""
    return "/?" + urlencode(
        {
            "playlist_code": playlist_code,
            "scenario": scenario_name,
        }
    )


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


def _format_accuracy(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}%"


def _get_local_stats(scenario_name: str) -> ScenarioStats | None:
    if not is_scenario_in_database(scenario_name):
        return None
    return get_scenario_stats(scenario_name)


def _get_personal_best_run(scenario_name: str) -> RunData | None:
    if not is_scenario_in_database(scenario_name):
        return None
    return get_personal_best_run(scenario_name)


def _personal_best_cm360(run_data: RunData | None) -> float | None:
    # Local CSVs only expose cm360 directly when the run was recorded with the
    # cm/360 sensitivity scale. Other scales stay unknown instead of mislabeled.
    if run_data is None or run_data.sens_scale != "cm/360":
        return None
    return run_data.horizontal_sens


def _personal_best_accuracy(run_data: RunData | None) -> float | None:
    if run_data is None:
        return None
    # Prefer damage accuracy because it most closely matches KovaaK's
    # leaderboard metadata; fall back to hit accuracy for older/incomplete CSVs.
    accuracy = (
        run_data.damage_accuracy
        if run_data.damage_accuracy is not None
        else run_data.accuracy
    )
    return round(accuracy * 100, 2)


def format_playlist_scenario_rank_row(  # noqa: PLR0913
    scenario_name: str,
    playlist_order: int,
    rank_info: ScenarioRankInfo,
    scenario_stats: ScenarioStats | None = None,
    personal_best_run: RunData | None = None,
    *,
    generation_token: str | None = None,
    playlist_code: str | None = None,
    mark_unresolved_pending: bool = False,
) -> PlaylistScenarioRow:
    """Create one complete AG Grid row with display and numeric sort values."""
    date_last_played = None
    number_of_runs = 0
    high_score = None
    if scenario_stats is not None:
        date_last_played = scenario_stats.date_last_played
        number_of_runs = scenario_stats.number_of_runs
        high_score = scenario_stats.high_score

    personal_best_cm360 = _personal_best_cm360(personal_best_run)
    personal_best_accuracy = _personal_best_accuracy(personal_best_run)
    row: PlaylistScenarioRow = {
        "scenario": scenario_name,
        "playlist_order": playlist_order,
        "status": rank_info.status.value,
        "rank_display": "N/A",
        "rank_sort": None,
        "total_display": "N/A",
        "total_sort": None,
        "percentile_display": "N/A",
        "percentile_sort": None,
        "last_played_sort": (
            date_last_played.timestamp() if date_last_played is not None else None
        ),
        "runs_display": _format_int(number_of_runs),
        "runs_sort": number_of_runs,
        "high_score_display": _format_score(high_score),
        "high_score_sort": high_score,
        "pb_cm360_display": _format_score(personal_best_cm360),
        "pb_cm360_sort": personal_best_cm360,
        "pb_accuracy_display": _format_accuracy(personal_best_accuracy),
        "pb_accuracy_sort": personal_best_accuracy,
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

    if generation_token is not None:
        row["generation_token"] = generation_token
        row["rank_pending"] = mark_unresolved_pending and not (
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
        row["href"] = scenario_home_href(scenario_name, playlist_code)
    return row


def _lookup_rank_info(
    scenario_name: str,
    *,
    allow_network: bool,
) -> ScenarioRankInfo:
    config = get_config()
    # Phase 2 hydrates once before its fan-out; phase 1 is cache-only. Neither
    # per-scenario path may start another total-play hydration.
    return get_scenario_rank_info(
        scenario_name,
        config.kovaaks_username,
        config.steam_id,
        config.scenario_metadata_cache_ttl_hours,
        config.scenario_rank_cache_ttl_hours,
        config.leaderboard_total_cache_ttl_hours,
        allow_network=allow_network,
        allow_hydration=False,
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


def _hydrate_playlist_leaderboard_ids(scenario_names: list[str]) -> None:
    """Hydrate the leaderboard mapping once before the phase-2 fan-out."""
    config = get_config()
    username = config.kovaaks_username
    if not username:
        return
    try:
        if all(get_cached_leaderboard_id(name) is not None for name in scenario_names):
            return
        hydrate_leaderboard_id_cache(
            username,
            config.scenario_metadata_cache_ttl_hours,
        )
    except Exception as exc:  # noqa: BLE001
        # Best-effort: the per-scenario path can still resolve ranks without
        # this optimization, and it converts expected API failures itself.
        logger.warning(
            "Failed to hydrate leaderboard metadata for playlist open: %s",
            exc,
        )


def _build_row(  # noqa: PLR0913
    scenario_name: str,
    playlist_order: int,
    rank_info: ScenarioRankInfo,
    generation_token: str,
    playlist_code: str,
    *,
    mark_unresolved_pending: bool,
) -> PlaylistScenarioRow:
    """Re-read local data and build a complete transaction-safe row."""
    try:
        scenario_stats = _get_local_stats(scenario_name)
    except Exception:  # noqa: BLE001
        logger.warning(
            "Failed to read local stats for %s", scenario_name, exc_info=True
        )
        scenario_stats = None
    try:
        personal_best_run = _get_personal_best_run(scenario_name)
    except Exception:  # noqa: BLE001
        logger.warning(
            "Failed to read the personal best for %s",
            scenario_name,
            exc_info=True,
        )
        personal_best_run = None
    return format_playlist_scenario_rank_row(
        scenario_name,
        playlist_order,
        rank_info,
        scenario_stats,
        personal_best_run,
        generation_token=generation_token,
        playlist_code=playlist_code,
        mark_unresolved_pending=mark_unresolved_pending,
    )


def build_playlist_scenario_rank_rows(
    playlist_code: str,
    generation_token: str,
) -> list[PlaylistScenarioRow]:
    """Build phase-1 rows from local data and TTL-ignored disk caches only."""
    playlist = get_playlist_by_code(playlist_code)
    if playlist is None:
        return []

    rows = []
    for index, scenario in enumerate(playlist.scenarios):
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
) -> bool:
    """Cancel older fills, register this generation, and start its daemon."""
    playlist = get_playlist_by_code(playlist_code)
    if playlist is None:
        return False
    scenario_names = tuple(scenario.name for scenario in playlist.scenarios)
    state = _FillState(
        playlist_code=playlist_code,
        scenario_names=scenario_names,
        total=len(scenario_names),
        unresolved_indices=set(range(len(scenario_names))),
    )
    with _FILL_REGISTRY_LOCK:
        _cancel_live_fills_locked()
        _FILL_REGISTRY[generation_token] = state

    thread = threading.Thread(
        target=_run_playlist_scenario_fill,
        args=(generation_token, scenario_names, state.cancel_event),
        name=f"playlist-fill-{generation_token[:8]}",
        daemon=True,
    )
    thread.start()
    return True


def _fetch_fill_row(
    generation_token: str,
    playlist_code: str,
    playlist_order: int,
    scenario_name: str,
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


def _run_playlist_scenario_fill(
    generation_token: str,
    scenario_names: tuple[str, ...],
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
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(
                        _fetch_fill_row,
                        generation_token,
                        playlist_code,
                        index,
                        scenario_name,
                        cancel_event,
                    )
                    for index, scenario_name in enumerate(scenario_names)
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


def _build_cancelled_finalization_rows(
    playlist_code: str,
    scenario_names: tuple[str, ...],
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
        if consuming_terminal:
            if state.terminal == "cancelled":
                unresolved_indices = sorted(state.unresolved_indices)
                scenario_names = state.scenario_names
            state.consumed = True
            state.unresolved_indices.clear()
            state.scenario_names = ()

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
