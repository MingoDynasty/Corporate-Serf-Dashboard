"""Politely warm scenario-rank caches used by the playlists overview."""

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from statistics import fmean

import requests
from pydantic import ValidationError

from source.config.config_service import ConfigData, get_config
from source.kovaaks.api_models import ScenarioRankStatus
from source.kovaaks.api_service import (
    UnknownKovaaksUserError,
    _cached_leaderboard_total,
    _cached_rank,
    _save_rank_monotonic,
    fetch_scenario_rank,
    get_api_activity_timestamps,
    get_cached_leaderboard_id,
    get_cached_leaderboard_total,
    get_cached_scenario_rank,
    get_leaderboard_total,
    get_user_scenario_total_play,
    hydrate_leaderboard_id_cache,
    resolve_leaderboard_id,
)
from source.kovaaks.data_models import PlaylistData, ScenarioStats
from source.kovaaks.data_service import (
    get_playlist_by_code,
    get_scenario_stats_snapshot,
)
from source.kovaaks.playlist_visibility_service import get_shown_playlist_codes
from source.utilities.dash_logging import get_dash_logger
from source.utilities.utilities import format_approximate_duration

logger = logging.getLogger(__name__)
dash_logger = get_dash_logger(__name__)

POLITENESS_GAP_SECONDS = 2.0
INTERACTIVE_QUIET_SECONDS = 5.0
INTERACTIVE_POLL_SECONDS = 1.0
BACKOFF_SLICE_SECONDS = 10.0
BACKOFF_DELAYS_SECONDS = (30.0, 120.0, 300.0, 900.0, 1800.0)
MAX_TRANSIENT_ATTEMPTS = 3
PACE_SAMPLE_SIZE = 10
PROGRESS_HEARTBEAT_EVERY_ITEMS = 10
_USERNAME_VALIDATION_OUTCOME = "\0username-validation"


class StepDisposition(StrEnum):
    """Tell the thin queue loop what to do with one processed item."""

    COMPLETE = "complete"
    RETRY = "retry"
    TERMINAL = "terminal"
    FATAL = "fatal"


@dataclass
class SessionOutcome:
    """Per-session retry and terminal state for one scenario or validation."""

    transient_attempts: int = 0
    terminal: bool = False
    reason: str | None = None


@dataclass
class WarmupContext:
    """Mutable session state shared by pure one-item processing steps."""

    config: ConfigData
    outcomes: dict[str, SessionOutcome] = field(default_factory=dict)
    username_validated: bool = False


@dataclass(frozen=True)
class WarmupStepResult:
    """One item's bounded outcome, independent of queue mechanics."""

    disposition: StepDisposition
    reason: str | None = None
    trip_backoff: bool = False
    success: bool = False


@dataclass(frozen=True)
class PercentileWarmupSnapshot:
    """Read-only worker state for the follow-up overview status UI."""

    queued_names: tuple[str, ...]
    in_flight: str | None
    remaining_count: int
    paused_until: datetime | None
    backoff_seconds: float | None
    fatal_state: str | None
    enqueue_generation: int
    recent_pace_seconds: float | None


def _outcome(context: WarmupContext, key: str) -> SessionOutcome:
    return context.outcomes.setdefault(key, SessionOutcome())


def _is_transient_failure(exc: BaseException) -> bool:
    if isinstance(exc, requests.ConnectionError):
        return True
    if not isinstance(exc, requests.HTTPError) or exc.response is None:
        return False
    status_code = exc.response.status_code
    return status_code == 429 or status_code >= 500


def _failure_result(
    context: WarmupContext,
    outcome_key: str,
    exc: BaseException,
) -> WarmupStepResult:
    """Classify one expected API/domain failure and update its attempt budget."""
    if isinstance(exc, UnknownKovaaksUserError):
        return WarmupStepResult(StepDisposition.FATAL, str(exc))

    outcome = _outcome(context, outcome_key)
    if isinstance(exc, requests.ReadTimeout):
        outcome.terminal = True
        outcome.reason = "read timeout"
        return WarmupStepResult(
            StepDisposition.TERMINAL,
            outcome.reason,
            trip_backoff=True,
        )

    if _is_transient_failure(exc):
        outcome.transient_attempts += 1
        if outcome.transient_attempts >= MAX_TRANSIENT_ATTEMPTS:
            outcome.terminal = True
            outcome.reason = "transient attempt cap exhausted"
            return WarmupStepResult(
                StepDisposition.TERMINAL,
                outcome.reason,
                trip_backoff=True,
            )
        return WarmupStepResult(
            StepDisposition.RETRY,
            f"transient failure {outcome.transient_attempts}/{MAX_TRANSIENT_ATTEMPTS}",
            trip_backoff=True,
        )

    outcome.terminal = True
    outcome.reason = f"permanent failure: {type(exc).__name__}"
    return WarmupStepResult(StepDisposition.TERMINAL, outcome.reason)


def _username_validation_result(context: WarmupContext) -> WarmupStepResult:
    """Validate the configured username once before caching any UNRANKED row."""
    if context.username_validated:
        return WarmupStepResult(StepDisposition.COMPLETE, success=True)

    prior = context.outcomes.get(_USERNAME_VALIDATION_OUTCOME)
    if prior is not None and prior.terminal:
        return WarmupStepResult(
            StepDisposition.TERMINAL,
            prior.reason or "username validation unavailable",
        )

    username = context.config.kovaaks_username
    if not username:
        return WarmupStepResult(
            StepDisposition.FATAL,
            "KovaaK's username is not configured.",
        )
    try:
        get_user_scenario_total_play(
            username,
            context.config.scenario_metadata_cache_ttl_hours,
        )
    except (
        UnknownKovaaksUserError,
        requests.RequestException,
        ValidationError,
        OSError,
        ValueError,
    ) as exc:
        return _failure_result(context, _USERNAME_VALIDATION_OUTCOME, exc)

    context.username_validated = True
    return WarmupStepResult(StepDisposition.COMPLETE, success=True)


def process_warmup_hydration(context: WarmupContext) -> WarmupStepResult:
    """Run the worker's one up-front metadata hydration/validation step."""
    if context.username_validated:
        return WarmupStepResult(StepDisposition.COMPLETE, success=True)

    prior = context.outcomes.get(_USERNAME_VALIDATION_OUTCOME)
    if prior is not None and prior.terminal:
        return WarmupStepResult(StepDisposition.TERMINAL, prior.reason)

    username = context.config.kovaaks_username
    if not username:
        return WarmupStepResult(
            StepDisposition.FATAL,
            "KovaaK's username is not configured.",
        )
    try:
        hydrate_leaderboard_id_cache(
            username,
            context.config.scenario_metadata_cache_ttl_hours,
        )
    except (
        UnknownKovaaksUserError,
        requests.RequestException,
        ValidationError,
        OSError,
        ValueError,
    ) as exc:
        return _failure_result(context, _USERNAME_VALIDATION_OUTCOME, exc)

    # A successful cached or live total-play response positively validates the
    # user; the API helper rejects fresh and stale unknown-user markers.
    context.username_validated = True
    return WarmupStepResult(StepDisposition.COMPLETE, success=True)


def _expected_failure_result(
    context: WarmupContext,
    scenario_name: str,
    exc: BaseException,
) -> WarmupStepResult:
    logger.warning(
        "Percentile warmup failed for %s: %s",
        scenario_name,
        exc,
    )
    return _failure_result(context, scenario_name, exc)


def process_warmup_item(  # noqa: PLR0911, PLR0912
    scenario_name: str,
    context: WarmupContext,
) -> WarmupStepResult:
    """Process one scenario without owning queue, pacing, or thread state."""
    config = context.config
    username = config.kovaaks_username
    if not username:
        return WarmupStepResult(
            StepDisposition.FATAL,
            "KovaaK's username is not configured.",
        )

    logger.debug("Percentile warmup processing %s", scenario_name)
    try:
        leaderboard_id = resolve_leaderboard_id(
            scenario_name,
            username,
            config.scenario_metadata_cache_ttl_hours,
            allow_hydration=False,
        )
    except (
        UnknownKovaaksUserError,
        requests.RequestException,
        ValidationError,
        OSError,
        ValueError,
    ) as exc:
        return _expected_failure_result(context, scenario_name, exc)

    if leaderboard_id is None:
        outcome = _outcome(context, scenario_name)
        outcome.terminal = True
        outcome.reason = "leaderboard could not be resolved"
        logger.warning("Percentile warmup could not resolve %s", scenario_name)
        return WarmupStepResult(StepDisposition.TERMINAL, outcome.reason)

    rank_info = get_cached_scenario_rank(
        leaderboard_id,
        username,
        config.scenario_rank_cache_ttl_hours,
    )
    if rank_info is not None and rank_info.status not in (
        ScenarioRankStatus.RANKED,
        ScenarioRankStatus.UNRANKED,
    ):
        rank_info = None

    wrote_rank = True
    if rank_info is None:
        try:
            candidate = fetch_scenario_rank(
                leaderboard_id,
                username,
                config.steam_id,
            ).model_copy(update={"scenario_name": scenario_name})
        except (
            UnknownKovaaksUserError,
            requests.RequestException,
            ValidationError,
            OSError,
            ValueError,
        ) as exc:
            return _expected_failure_result(context, scenario_name, exc)

        if candidate.status == ScenarioRankStatus.RANKED:
            # An exact leaderboard player match is itself positive validation.
            context.username_validated = True
        elif candidate.status == ScenarioRankStatus.UNRANKED:
            validation_result = _username_validation_result(context)
            if validation_result.disposition != StepDisposition.COMPLETE:
                if validation_result.disposition == StepDisposition.TERMINAL:
                    outcome = _outcome(context, scenario_name)
                    outcome.terminal = True
                    outcome.reason = validation_result.reason
                return validation_result
        else:
            outcome = _outcome(context, scenario_name)
            outcome.terminal = True
            outcome.reason = "rank endpoint returned no usable state"
            return WarmupStepResult(StepDisposition.TERMINAL, outcome.reason)

        try:
            rank_info, wrote_rank = _save_rank_monotonic(
                leaderboard_id,
                username,
                candidate,
            )
        except (ValidationError, OSError, ValueError) as exc:
            return _expected_failure_result(context, scenario_name, exc)

    if rank_info.status == ScenarioRankStatus.RANKED:
        try:
            get_leaderboard_total(
                leaderboard_id,
                config.leaderboard_total_cache_ttl_hours,
            )
        except (
            requests.RequestException,
            ValidationError,
            OSError,
            ValueError,
        ) as exc:
            return _expected_failure_result(context, scenario_name, exc)

    if not wrote_rank:
        # The monotonic winner may be newer in score but old by TTL. Do not
        # touch its metadata merely to satisfy freshness, and suppress any
        # duplicate queue entries for the rest of this session.
        outcome = _outcome(context, scenario_name)
        outcome.terminal = True
        outcome.reason = "newer cached rank preserved"
        return WarmupStepResult(
            StepDisposition.TERMINAL,
            outcome.reason,
            success=True,
        )

    return WarmupStepResult(StepDisposition.COMPLETE, success=True)


def _freshly_satisfied(scenario_name: str, config: ConfigData) -> bool:
    """Implement R4's dequeue-time fresh-rank/fresh-total predicate."""
    username = config.kovaaks_username
    if not username:
        return True
    leaderboard_id = get_cached_leaderboard_id(scenario_name)
    if leaderboard_id is None:
        return False
    rank_info = get_cached_scenario_rank(
        leaderboard_id,
        username,
        config.scenario_rank_cache_ttl_hours,
    )
    if rank_info is None:
        return False
    if rank_info.status == ScenarioRankStatus.UNRANKED:
        return True
    return (
        rank_info.status == ScenarioRankStatus.RANKED
        and get_cached_leaderboard_total(
            leaderboard_id,
            config.leaderboard_total_cache_ttl_hours,
        )
        is not None
    )


def _has_displayable_percentile(scenario_name: str, config: ConfigData) -> bool:
    """Read presence-only caches for R3 ordering, without recording activity."""
    username = config.kovaaks_username
    if not username:
        return False
    leaderboard_id = get_cached_leaderboard_id(scenario_name)
    if leaderboard_id is None:
        return False
    rank_info = _cached_rank(leaderboard_id, username)
    total_players = _cached_leaderboard_total(leaderboard_id)
    return (
        rank_info is not None
        and rank_info.status == ScenarioRankStatus.RANKED
        and rank_info.rank is not None
        and total_players is not None
        and total_players > 0
    )


def _ordered_played_scenarios(
    playlist: PlaylistData,
    stats_by_scenario: dict[str, ScenarioStats],
    config: ConfigData,
) -> list[str]:
    played = [
        (index, scenario.name, stats_by_scenario[scenario.name])
        for index, scenario in enumerate(playlist.scenarios)
        if scenario.name in stats_by_scenario
    ]
    played.sort(
        key=lambda item: (
            _has_displayable_percentile(item[1], config),
            -item[2].date_last_played.timestamp(),
            item[0],
        )
    )
    return [scenario_name for _, scenario_name, _ in played]


def _startup_queue(config: ConfigData) -> list[str]:
    """Build R2/R3's played-visible queue in playlist-completion order."""
    stats_by_scenario = get_scenario_stats_snapshot()
    batches: list[tuple[datetime, str, str, list[str]]] = []
    for playlist_code in get_shown_playlist_codes():
        playlist = get_playlist_by_code(playlist_code)
        if playlist is None:
            continue
        scenarios = _ordered_played_scenarios(playlist, stats_by_scenario, config)
        if not scenarios:
            continue
        most_recent = max(
            stats_by_scenario[name].date_last_played for name in scenarios
        )
        batches.append((most_recent, playlist.name, playlist.code, scenarios))

    batches.sort(
        key=lambda batch: (
            -batch[0].timestamp(),
            batch[1].casefold(),
            batch[2],
        )
    )
    queue: list[str] = []
    for _, playlist_name, playlist_code, scenarios in batches:
        logger.info(
            "Percentile warmup queued playlist %s (%s): %d played scenarios",
            playlist_name,
            playlist_code,
            len(scenarios),
        )
        queue.extend(scenarios)
    return queue


class PercentileWarmupWorker:
    """Own the app-lifetime condition queue and its one daemon consumer."""

    def __init__(
        self,
        config: ConfigData,
        initial_queue: list[str] | None = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        activity_timestamps: Callable[
            [], tuple[float, float]
        ] = get_api_activity_timestamps,
    ) -> None:
        """Initialize one worker with injectable time and activity primitives."""
        self.context = WarmupContext(config=config)
        self._queue = deque(initial_queue or [])
        self._condition = threading.Condition()
        self._sleep = sleep
        self._clock = clock
        self._activity_timestamps = activity_timestamps
        self._thread: threading.Thread | None = None
        self._in_flight: str | None = None
        self._paused_until: datetime | None = None
        self._backoff_seconds: float | None = None
        self._backoff_level = 0
        self._fatal_state: str | None = None
        self._enqueue_generation = 0
        self._recent_paces: deque[float] = deque(maxlen=PACE_SAMPLE_SIZE)
        self._hydration_pending = True
        self._batch_active = bool(self._queue)
        self._batch_started_at = self._clock() if self._queue else None
        self._batch_processed = 0
        self._batch_terminal = 0
        self._batch_skipped = 0

    def start(self) -> threading.Thread:
        """Start this worker exactly once."""
        with self._condition:
            if self._thread is not None:
                return self._thread
            self._thread = threading.Thread(
                target=self._run,
                name="percentile-warmup",
                daemon=True,
            )
            self._thread.start()
            return self._thread

    def enqueue_playlist(self, playlist_code: str) -> int:
        """Batch-prepend one playlist's played scenarios and wake the worker."""
        with self._condition:
            if self._fatal_state is not None:
                return 0
        stats_by_scenario = get_scenario_stats_snapshot()
        playlist = get_playlist_by_code(playlist_code)
        if playlist is None:
            return 0
        scenarios = _ordered_played_scenarios(
            playlist,
            stats_by_scenario,
            self.context.config,
        )
        if not scenarios:
            return 0
        with self._condition:
            if self._fatal_state is not None:
                return 0
            for scenario_name in reversed(scenarios):
                self._queue.appendleft(scenario_name)
            self._enqueue_generation += 1
            if not self._batch_active:
                self._begin_batch_locked()
            self._condition.notify()
        logger.info(
            "Percentile warmup prepended playlist %s (%s): %d played scenarios",
            playlist.name,
            playlist.code,
            len(scenarios),
        )
        return len(scenarios)

    def snapshot(self) -> PercentileWarmupSnapshot:
        """Return a stable, spam-proof view of current worker progress."""
        with self._condition:
            terminal_names = {
                name
                # Item processing mutates this worker-owned map without
                # holding the condition across slow HTTP. Snapshot the items
                # in one C-level operation so UI reads cannot race iteration.
                for name, outcome in list(self.context.outcomes.items())
                if name != _USERNAME_VALIDATION_OUTCOME and outcome.terminal
            }
            queued_names = tuple(
                dict.fromkeys(
                    name for name in self._queue if name not in terminal_names
                )
            )
            remaining_names = set(queued_names)
            if self._in_flight is not None and self._in_flight not in terminal_names:
                remaining_names.add(self._in_flight)
            recent_pace = fmean(self._recent_paces) if self._recent_paces else None
            return PercentileWarmupSnapshot(
                queued_names=queued_names,
                in_flight=self._in_flight,
                remaining_count=len(remaining_names),
                paused_until=self._paused_until,
                backoff_seconds=self._backoff_seconds,
                fatal_state=self._fatal_state,
                enqueue_generation=self._enqueue_generation,
                recent_pace_seconds=recent_pace,
            )

    def _begin_batch_locked(self) -> None:
        self._batch_active = True
        self._batch_started_at = self._clock()
        self._batch_processed = 0
        self._batch_terminal = 0
        self._batch_skipped = 0

    def _log_completed_batch_locked(self) -> None:
        if not self._batch_active or self._in_flight is not None or self._queue:
            return
        elapsed = (
            self._clock() - self._batch_started_at
            if self._batch_started_at is not None
            else 0.0
        )
        logger.info(
            "Percentile warmup complete: processed=%d terminal=%d skipped=%d "
            "elapsed=%.1fs",
            self._batch_processed,
            self._batch_terminal,
            self._batch_skipped,
            elapsed,
        )
        self._batch_active = False
        self._batch_started_at = None

    def _log_progress_heartbeat(self, processed: int) -> None:
        """Emit one INFO progress line per few completed items.

        Console-visible progress between the startup queue dump and the
        completion summary; per-item detail stays at DEBUG.
        """
        state = self.snapshot()
        if state.recent_pace_seconds is None:
            logger.info(
                "Percentile warmup progress: processed=%d remaining=%d",
                processed,
                state.remaining_count,
            )
            return
        logger.info(
            "Percentile warmup progress: processed=%d remaining=%d (~%s)",
            processed,
            state.remaining_count,
            format_approximate_duration(
                state.remaining_count * state.recent_pace_seconds
            ),
        )

    def _next_item(self) -> str | None:
        with self._condition:
            while True:
                if self._fatal_state is not None:
                    return None
                while self._queue:
                    scenario_name = self._queue.popleft()
                    outcome = self.context.outcomes.get(scenario_name)
                    if (outcome is not None and outcome.terminal) or _freshly_satisfied(
                        scenario_name,
                        self.context.config,
                    ):
                        self._batch_skipped += 1
                        continue
                    self._in_flight = scenario_name
                    return scenario_name
                self._log_completed_batch_locked()
                self._condition.wait()

    def _wait_for_interactive_quiet(self) -> None:
        while True:
            last_interactive, _ = self._activity_timestamps()
            if last_interactive <= 0:
                return
            remaining = INTERACTIVE_QUIET_SECONDS - (self._clock() - last_interactive)
            if remaining <= 0:
                return
            self._sleep(min(INTERACTIVE_POLL_SECONDS, remaining))

    def _reset_backoff(self) -> None:
        with self._condition:
            self._backoff_level = 0

    def _wait_for_backoff(self) -> None:
        delay = BACKOFF_DELAYS_SECONDS[
            min(self._backoff_level, len(BACKOFF_DELAYS_SECONDS) - 1)
        ]
        self._backoff_level = min(
            self._backoff_level + 1,
            len(BACKOFF_DELAYS_SECONDS) - 1,
        )
        _, baseline_network_success = self._activity_timestamps()
        deadline = self._clock() + delay
        with self._condition:
            self._backoff_seconds = delay
            self._paused_until = datetime.now(UTC) + timedelta(seconds=delay)
        logger.info("Percentile warmup entering %.0fs outage backoff", delay)

        recovered = False
        while True:
            remaining = deadline - self._clock()
            if remaining <= 0:
                break
            self._sleep(min(BACKOFF_SLICE_SECONDS, remaining))
            _, network_success = self._activity_timestamps()
            if network_success > baseline_network_success:
                recovered = True
                break

        with self._condition:
            self._backoff_seconds = None
            self._paused_until = None
        if recovered:
            self._backoff_level = 0
            logger.info("Percentile warmup left backoff after network recovery")
        else:
            logger.info("Percentile warmup backoff elapsed")

    def _set_fatal(self, message: str, *, notify: bool) -> None:
        with self._condition:
            if self._fatal_state is not None:
                return
            self._fatal_state = message
            self._in_flight = None
            self._queue.clear()
        logger.info("Percentile warmup stopped: %s", message)
        if notify:
            dash_logger.error(
                "Percentile update stopped: KovaaK's username may be misconfigured."
            )

    def _apply_hydration_result(self, result: WarmupStepResult) -> bool:
        self._hydration_pending = False
        if result.success:
            self._reset_backoff()
        if result.disposition == StepDisposition.FATAL:
            self._set_fatal(result.reason or "unknown username", notify=True)
            return False
        if result.trip_backoff:
            self._wait_for_backoff()
        return True

    def _apply_item_result(
        self,
        scenario_name: str,
        result: WarmupStepResult,
        elapsed: float,
    ) -> bool:
        heartbeat_processed: int | None = None
        with self._condition:
            self._in_flight = None
            self._recent_paces.append(elapsed + POLITENESS_GAP_SECONDS)
            if result.disposition == StepDisposition.COMPLETE:
                self._batch_processed += 1
                if self._batch_processed % PROGRESS_HEARTBEAT_EVERY_ITEMS == 0:
                    heartbeat_processed = self._batch_processed
            elif result.disposition == StepDisposition.RETRY:
                self._queue.append(scenario_name)
            elif result.disposition == StepDisposition.TERMINAL:
                outcome = _outcome(self.context, scenario_name)
                outcome.terminal = True
                outcome.reason = result.reason
                self._batch_terminal += 1
            elif result.disposition == StepDisposition.FATAL:
                pass

        if heartbeat_processed is not None:
            self._log_progress_heartbeat(heartbeat_processed)
        if result.success:
            self._reset_backoff()
        if result.disposition == StepDisposition.FATAL:
            self._set_fatal(result.reason or "unknown username", notify=True)
            return False
        if result.trip_backoff:
            self._wait_for_backoff()
        else:
            self._sleep(POLITENESS_GAP_SECONDS)
        return True

    def _run(self) -> None:
        logger.info("Percentile warmup worker started")
        # Answer "how much is queued?" before the first fetch — the cadence
        # heartbeat stays silent for ten items, and remaining=0 is the
        # positive confirmation that nothing needs warming.
        self._log_progress_heartbeat(0)
        while True:
            # Hydration is deferred until actual work exists and only begins in
            # a quiet window; an empty startup queue therefore touches no API.
            with self._condition:
                while not self._queue and self._fatal_state is None:
                    self._log_completed_batch_locked()
                    self._condition.wait()
                if self._fatal_state is not None:
                    return
                hydration_pending = self._hydration_pending
            if hydration_pending:
                self._wait_for_interactive_quiet()
                try:
                    hydration_result = process_warmup_hydration(self.context)
                except Exception as exc:  # noqa: BLE001 - daemon safety net
                    logger.exception("Unexpected percentile warmup hydration failure")
                    self._set_fatal(str(exc), notify=False)
                    return
                if not self._apply_hydration_result(hydration_result):
                    return
                continue

            scenario_name = self._next_item()
            if scenario_name is None:
                return
            self._wait_for_interactive_quiet()
            started = self._clock()
            try:
                result = process_warmup_item(scenario_name, self.context)
            except Exception as exc:  # noqa: BLE001 - daemon safety net
                logger.exception(
                    "Unexpected percentile warmup failure for %s",
                    scenario_name,
                )
                self._set_fatal(str(exc), notify=False)
                return
            if not self._apply_item_result(
                scenario_name,
                result,
                self._clock() - started,
            ):
                return


_worker_lock = threading.Lock()
_worker: PercentileWarmupWorker | None = None


def start_percentile_warmup_worker(config: ConfigData | None = None) -> bool:
    """Start the singleton worker; return False for either off configuration."""
    global _worker  # noqa: PLW0603
    config = config or get_config()
    # Guard before playlist/stats enumeration: empty username is fully offline.
    if not config.percentile_warmup_enabled or not config.kovaaks_username:
        logger.info("Percentile warmup disabled by configuration")
        return False

    with _worker_lock:
        if _worker is not None:
            return True
        initial_queue = _startup_queue(config)
        _worker = PercentileWarmupWorker(config, initial_queue)
        _worker.start()
    return True


def enqueue_playlist_percentile_warmup(playlist_code: str) -> int:
    """Prepend one newly visible/imported playlist, or no-op while disabled."""
    config = get_config()
    # Same pre-enumeration guards as startup (R15).
    if not config.percentile_warmup_enabled or not config.kovaaks_username:
        return 0
    with _worker_lock:
        worker = _worker
    if worker is None:
        return 0
    return worker.enqueue_playlist(playlist_code)


def get_percentile_warmup_state() -> PercentileWarmupSnapshot:
    """Return singleton progress, including a stable disabled/idle snapshot."""
    with _worker_lock:
        worker = _worker
    if worker is None:
        return PercentileWarmupSnapshot(
            queued_names=(),
            in_flight=None,
            remaining_count=0,
            paused_until=None,
            backoff_seconds=None,
            fatal_state=None,
            enqueue_generation=0,
            recent_pace_seconds=None,
        )
    return worker.snapshot()
