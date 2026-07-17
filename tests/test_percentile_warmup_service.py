import os
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests

from source.config.config_service import ConfigData
from source.kovaaks import api_service
from source.kovaaks import percentile_warmup_service as warmup
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from source.kovaaks.data_models import PlaylistData, Scenario, ScenarioStats


def _config(
    *,
    username: str | None = "ValidUser",
    enabled: bool = True,
) -> ConfigData:
    return ConfigData(
        stats_dir="stats",
        polling_interval=1000,
        port=8080,
        sens_round_decimal_places=2,
        kovaaks_username=username,
        percentile_warmup_enabled=enabled,
    )


def _stats(day: int) -> ScenarioStats:
    return ScenarioStats(
        date_last_played=datetime(2026, 7, day, 12, 0),
        number_of_runs=1,
        high_score=100.0,
    )


def _playlist(name: str, code: str, *scenarios: str) -> PlaylistData:
    return PlaylistData(
        name=name,
        code=code,
        scenarios=[Scenario(name=scenario) for scenario in scenarios],
    )


def test_startup_queue_groups_recent_playlists_and_prioritizes_missing_percentiles(
    monkeypatch,
):
    playlists = {
        "Recent": _playlist("Recent playlist", "Recent", "A", "B", "Unplayed"),
        "Older": _playlist("Older playlist", "Older", "C", "D"),
    }
    stats = {"A": _stats(10), "B": _stats(1), "C": _stats(5), "D": _stats(4)}
    displayable = {"A": True, "B": False, "C": False, "D": False}
    monkeypatch.setattr(warmup, "get_shown_playlist_codes", lambda: set(playlists))
    monkeypatch.setattr(warmup, "get_playlist_by_code", playlists.get)
    monkeypatch.setattr(warmup, "get_scenario_stats_snapshot", lambda: stats)
    monkeypatch.setattr(
        warmup,
        "_has_displayable_percentile",
        lambda scenario_name, _config: displayable[scenario_name],
    )

    assert warmup._startup_queue(_config()) == ["B", "A", "C", "D"]


def test_snapshot_deduplicates_queue_and_counts_in_flight_once():
    worker = warmup.PercentileWarmupWorker(
        _config(),
        ["Duplicate", "Duplicate", "Other", "Terminal"],
    )
    worker._in_flight = "Duplicate"
    worker.context.outcomes["Terminal"] = warmup.SessionOutcome(
        terminal=True,
        reason="done",
    )

    state = worker.snapshot()

    assert state.queued_names == ("Duplicate", "Other")
    assert state.in_flight == "Duplicate"
    assert state.remaining_count == 2


def test_terminal_duplicate_entries_skip_without_refetch(monkeypatch):
    worker = warmup.PercentileWarmupWorker(
        _config(),
        ["Duplicate", "Duplicate", "Other"],
    )
    worker.context.outcomes["Duplicate"] = warmup.SessionOutcome(terminal=True)
    monkeypatch.setattr(warmup, "_freshly_satisfied", lambda *_args: False)

    assert worker._next_item() == "Other"
    assert worker.snapshot().in_flight == "Other"


def test_enqueue_batch_prepends_in_order_and_bumps_generation(monkeypatch):
    playlist = _playlist("New", "Code", "A", "B")
    monkeypatch.setattr(warmup, "get_playlist_by_code", lambda _code: playlist)
    monkeypatch.setattr(
        warmup,
        "get_scenario_stats_snapshot",
        lambda: {"A": _stats(10), "B": _stats(1)},
    )
    monkeypatch.setattr(
        warmup,
        "_has_displayable_percentile",
        lambda scenario_name, _config: scenario_name == "A",
    )
    worker = warmup.PercentileWarmupWorker(_config(), ["Tail"])

    assert worker.enqueue_playlist("Code") == 2

    state = worker.snapshot()
    assert state.queued_names == ("B", "A", "Tail")
    assert state.enqueue_generation == 1


@pytest.mark.parametrize(
    ("rank_status", "total_players", "expected"),
    [
        (ScenarioRankStatus.UNRANKED, None, True),
        (ScenarioRankStatus.RANKED, 100, True),
        (ScenarioRankStatus.RANKED, None, False),
    ],
)
def test_dequeue_predicate_requires_fresh_total_only_for_ranked(
    monkeypatch,
    rank_status,
    total_players,
    expected,
):
    monkeypatch.setattr(warmup, "get_cached_leaderboard_id", lambda _name: 42)
    monkeypatch.setattr(
        warmup,
        "get_cached_scenario_rank",
        lambda *_args, **_kwargs: ScenarioRankInfo(status=rank_status),
    )
    monkeypatch.setattr(
        warmup,
        "get_cached_leaderboard_total",
        lambda *_args, **_kwargs: total_players,
    )

    assert warmup._freshly_satisfied("Scenario", _config()) is expected


def test_rejected_stale_rank_preserves_newer_cache_metadata_and_is_terminal(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path)
    api_service.make_cache()
    existing = ScenarioRankInfo(
        status=ScenarioRankStatus.RANKED,
        rank=1,
        leaderboard_id=42,
        scenario_name="Scenario",
        score=100.0,
        fetched_at=datetime.now(UTC),
    )
    api_service.save_scenario_rank(42, "ValidUser", existing)
    cache_file = api_service._rank_cache_file(42, "ValidUser")
    stale_time = time.time() - (8 * 24 * 60 * 60)
    os.utime(cache_file, (stale_time, stale_time))
    modified_before = cache_file.stat().st_mtime_ns

    candidate = existing.model_copy(update={"rank": 2, "score": 90.0})
    monkeypatch.setattr(warmup, "resolve_leaderboard_id", lambda *_a, **_k: 42)
    monkeypatch.setattr(warmup, "fetch_scenario_rank", lambda *_a, **_k: candidate)
    monkeypatch.setattr(warmup, "get_leaderboard_total", lambda *_a, **_k: 100)
    context = warmup.WarmupContext(_config())

    result = warmup.process_warmup_item("Scenario", context)

    assert result.disposition == warmup.StepDisposition.TERMINAL
    assert result.success is True
    assert context.outcomes["Scenario"].terminal is True
    assert cache_file.stat().st_mtime_ns == modified_before
    assert api_service._cached_rank(42, "ValidUser").score == 100.0


def test_partial_rank_success_retries_only_the_total(monkeypatch):
    cached_rank = [None]
    fetches = []
    saves = []
    total_calls = []
    candidate = ScenarioRankInfo(
        status=ScenarioRankStatus.RANKED,
        rank=5,
        leaderboard_id=42,
        score=95.0,
    )
    monkeypatch.setattr(warmup, "resolve_leaderboard_id", lambda *_a, **_k: 42)
    monkeypatch.setattr(
        warmup,
        "get_cached_scenario_rank",
        lambda *_a, **_k: cached_rank[0],
    )

    def fetch(*_args, **_kwargs):
        fetches.append(True)
        return candidate

    def save(_leaderboard_id, _username, rank_info):
        saves.append(True)
        cached_rank[0] = rank_info
        return rank_info, True

    def total(*_args, **_kwargs):
        total_calls.append(True)
        if len(total_calls) == 1:
            raise requests.ConnectionError("offline")
        return 100

    monkeypatch.setattr(warmup, "fetch_scenario_rank", fetch)
    monkeypatch.setattr(warmup, "_save_rank_monotonic", save)
    monkeypatch.setattr(warmup, "get_leaderboard_total", total)
    context = warmup.WarmupContext(_config())

    first = warmup.process_warmup_item("Scenario", context)
    second = warmup.process_warmup_item("Scenario", context)

    assert first.disposition == warmup.StepDisposition.RETRY
    assert second.disposition == warmup.StepDisposition.COMPLETE
    assert len(fetches) == 1
    assert len(saves) == 1
    assert len(total_calls) == 2


@pytest.mark.parametrize(
    "config",
    [
        _config(username=None, enabled=True),
        _config(username="ValidUser", enabled=False),
    ],
    ids=["offline", "kill-switch"],
)
def test_disabled_start_does_not_enumerate_or_create_worker(monkeypatch, config):
    monkeypatch.setattr(warmup, "_worker", None)
    monkeypatch.setattr(
        warmup,
        "_startup_queue",
        lambda _config: pytest.fail("disabled startup must not enumerate"),
    )
    monkeypatch.setattr(
        warmup,
        "PercentileWarmupWorker",
        lambda *_a, **_k: pytest.fail("disabled startup must not create a worker"),
    )

    assert warmup.start_percentile_warmup_worker(config) is False


@pytest.mark.parametrize(
    "config",
    [
        _config(username=None, enabled=True),
        _config(username="ValidUser", enabled=False),
    ],
    ids=["offline", "kill-switch"],
)
def test_disabled_enqueue_does_not_enumerate(monkeypatch, config):
    monkeypatch.setattr(warmup, "get_config", lambda: config)

    class FailWorker:
        def enqueue_playlist(self, _code):
            pytest.fail("disabled enqueue must not enumerate")

    monkeypatch.setattr(warmup, "_worker", FailWorker())

    assert warmup.enqueue_playlist_percentile_warmup("Code") == 0


def test_unknown_user_stops_unranked_item_without_writing(monkeypatch):
    candidate = ScenarioRankInfo(
        status=ScenarioRankStatus.UNRANKED,
        leaderboard_id=42,
    )
    monkeypatch.setattr(warmup, "resolve_leaderboard_id", lambda *_a, **_k: 42)
    monkeypatch.setattr(warmup, "get_cached_scenario_rank", lambda *_a, **_k: None)
    monkeypatch.setattr(warmup, "fetch_scenario_rank", lambda *_a, **_k: candidate)
    monkeypatch.setattr(
        warmup,
        "get_user_scenario_total_play",
        lambda *_a, **_k: (_ for _ in ()).throw(
            warmup.UnknownKovaaksUserError("unknown user")
        ),
    )
    monkeypatch.setattr(
        warmup,
        "_save_rank_monotonic",
        lambda *_a, **_k: pytest.fail("unvalidated UNRANKED must not be written"),
    )

    result = warmup.process_warmup_item(
        "Scenario",
        warmup.WarmupContext(_config()),
    )

    assert result.disposition == warmup.StepDisposition.FATAL


@pytest.mark.parametrize(
    ("failure", "expected_disposition"),
    [
        (requests.ConnectionError("offline"), warmup.StepDisposition.RETRY),
        (requests.ReadTimeout("slow"), warmup.StepDisposition.TERMINAL),
    ],
)
def test_unranked_validation_failure_controls_item_without_writing(
    monkeypatch,
    failure,
    expected_disposition,
):
    candidate = ScenarioRankInfo(
        status=ScenarioRankStatus.UNRANKED,
        leaderboard_id=42,
    )
    monkeypatch.setattr(warmup, "resolve_leaderboard_id", lambda *_a, **_k: 42)
    monkeypatch.setattr(warmup, "get_cached_scenario_rank", lambda *_a, **_k: None)
    monkeypatch.setattr(warmup, "fetch_scenario_rank", lambda *_a, **_k: candidate)

    def fail_validation(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(warmup, "get_user_scenario_total_play", fail_validation)
    monkeypatch.setattr(
        warmup,
        "_save_rank_monotonic",
        lambda *_a, **_k: pytest.fail("unvalidated UNRANKED must not be written"),
    )
    context = warmup.WarmupContext(_config())

    result = warmup.process_warmup_item("Scenario", context)

    assert result.disposition == expected_disposition
    assert result.trip_backoff is True
    validation = context.outcomes[warmup._USERNAME_VALIDATION_OUTCOME]
    assert validation.terminal is (
        expected_disposition == warmup.StepDisposition.TERMINAL
    )


def test_validation_retries_share_reserved_three_attempt_budget(monkeypatch):
    candidate = ScenarioRankInfo(
        status=ScenarioRankStatus.UNRANKED,
        leaderboard_id=42,
    )
    monkeypatch.setattr(warmup, "resolve_leaderboard_id", lambda *_a, **_k: 42)
    monkeypatch.setattr(warmup, "get_cached_scenario_rank", lambda *_a, **_k: None)
    monkeypatch.setattr(warmup, "fetch_scenario_rank", lambda *_a, **_k: candidate)
    monkeypatch.setattr(
        warmup,
        "get_user_scenario_total_play",
        lambda *_a, **_k: (_ for _ in ()).throw(requests.ConnectionError()),
    )
    monkeypatch.setattr(
        warmup,
        "_save_rank_monotonic",
        lambda *_a, **_k: pytest.fail("unvalidated UNRANKED must not be written"),
    )
    context = warmup.WarmupContext(_config())

    results = [warmup.process_warmup_item("Scenario", context) for _ in range(3)]

    assert [result.disposition for result in results] == [
        warmup.StepDisposition.RETRY,
        warmup.StepDisposition.RETRY,
        warmup.StepDisposition.TERMINAL,
    ]
    validation = context.outcomes[warmup._USERNAME_VALIDATION_OUTCOME]
    assert validation.transient_attempts == 3
    assert validation.terminal is True
    assert context.outcomes["Scenario"].terminal is True


def test_rank_read_timeout_is_terminal_and_trips_global_backoff(monkeypatch):
    monkeypatch.setattr(warmup, "resolve_leaderboard_id", lambda *_a, **_k: 42)
    monkeypatch.setattr(warmup, "get_cached_scenario_rank", lambda *_a, **_k: None)

    def time_out(*_args, **_kwargs):
        raise requests.ReadTimeout("slow")

    monkeypatch.setattr(warmup, "fetch_scenario_rank", time_out)
    context = warmup.WarmupContext(_config())

    result = warmup.process_warmup_item("Scenario", context)

    assert result.disposition == warmup.StepDisposition.TERMINAL
    assert result.trip_backoff is True
    assert context.outcomes["Scenario"].terminal is True
    assert context.outcomes["Scenario"].transient_attempts == 0


@pytest.mark.parametrize(
    ("status_code", "expected", "trip_backoff"),
    [
        (429, warmup.StepDisposition.RETRY, True),
        (503, warmup.StepDisposition.RETRY, True),
        (400, warmup.StepDisposition.TERMINAL, False),
    ],
)
def test_http_failure_taxonomy(status_code, expected, trip_backoff):
    response = requests.Response()
    response.status_code = status_code
    failure = requests.HTTPError(response=response)
    context = warmup.WarmupContext(_config())

    result = warmup._failure_result(context, "Scenario", failure)

    assert result.disposition == expected
    assert result.trip_backoff is trip_backoff


def test_successful_hydration_counts_as_username_validation(monkeypatch):
    calls = []
    monkeypatch.setattr(
        warmup,
        "hydrate_leaderboard_id_cache",
        lambda *_args, **_kwargs: calls.append(True),
    )
    context = warmup.WarmupContext(_config())

    result = warmup.process_warmup_hydration(context)

    assert result.disposition == warmup.StepDisposition.COMPLETE
    assert context.username_validated is True
    assert calls == [True]


def test_backoff_wakes_on_network_success_within_one_slice():
    now = [0.0]
    network_success = [1.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds
        network_success[0] += 1

    worker = warmup.PercentileWarmupWorker(
        _config(),
        sleep=sleep,
        clock=lambda: now[0],
        activity_timestamps=lambda: (999.0, network_success[0]),
    )

    worker._wait_for_backoff()

    assert sleeps == [warmup.BACKOFF_SLICE_SECONDS]
    assert worker.snapshot().paused_until is None
    assert worker._backoff_level == 0


def test_interactive_activity_does_not_wake_backoff():
    now = [0.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    worker = warmup.PercentileWarmupWorker(
        _config(),
        sleep=sleep,
        clock=lambda: now[0],
        activity_timestamps=lambda: (now[0] + 1000.0, 1.0),
    )

    worker._wait_for_backoff()

    assert sleeps == [10.0, 10.0, 10.0]
