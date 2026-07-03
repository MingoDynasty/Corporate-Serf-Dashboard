import logging
import os
import shutil
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from source.kovaaks import api_service
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus

LEADERBOARD_ID = 98330
SCENARIO_NAME = "VT Pasu Intermediate S5"
USERNAME = "MingoDynasty"
TEST_CACHE_DIR = Path("tests/fixtures/generated/scenario_rank_freshness_cache")


def _ranked(score: float | None, rank: int = 100) -> ScenarioRankInfo:
    return ScenarioRankInfo(
        status=ScenarioRankStatus.RANKED,
        rank=rank,
        leaderboard_id=LEADERBOARD_ID,
        score=score,
    )


def _unranked() -> ScenarioRankInfo:
    return ScenarioRankInfo(
        status=ScenarioRankStatus.UNRANKED,
        leaderboard_id=LEADERBOARD_ID,
    )


def _capture_log(messages):
    def capture(message, *args):
        messages.append(message % args if args else message)

    return capture


@pytest.fixture
def rank_cache(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()
    yield TEST_CACHE_DIR
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


@pytest.mark.parametrize(
    ("rank_info", "expected_score", "expected"),
    [
        (_ranked(100.0), 100.0, True),
        (_ranked(101.0), 100.0, True),
        (_ranked(913.41), 913.419861, True),
        (_ranked(99.99), 100.0, False),
        (_ranked(None), 100.0, False),
        (_unranked(), 100.0, False),
    ],
)
def test_score_is_fresh_uses_two_decimal_floor(
    rank_info,
    expected_score,
    expected,
):
    assert api_service._score_is_fresh(rank_info, expected_score) is expected


@pytest.mark.parametrize(
    ("existing", "candidate", "allow_regression", "expected"),
    [
        (_ranked(110.0), _ranked(100.0), False, False),
        (_ranked(100.0), _ranked(99.99), False, False),
        (_ranked(100.0), _unranked(), False, False),
        (_ranked(100.0), _ranked(None), False, False),
        (_ranked(None), _ranked(100.0), False, True),
        (_unranked(), _ranked(100.0), False, True),
        (_ranked(100.0), _ranked(100.0), False, True),
        (_unranked(), _unranked(), False, True),
        (_ranked(100.0), _unranked(), True, True),
        (_ranked(110.0), _ranked(100.0), True, True),
    ],
)
def test_is_forward_rule_table(
    existing,
    candidate,
    allow_regression,
    expected,
):
    assert api_service._is_forward(existing, candidate, allow_regression) is expected


def test_save_rank_monotonic_writes_with_empty_cache(rank_cache):
    candidate = _ranked(100.0)

    winner, wrote = api_service._save_rank_monotonic(
        LEADERBOARD_ID,
        USERNAME,
        candidate,
    )

    assert wrote is True
    assert winner == candidate
    assert api_service._cached_rank(LEADERBOARD_ID, USERNAME) == candidate


def test_save_rank_monotonic_replaces_malformed_cache(rank_cache):
    cache_file = api_service._rank_cache_file(LEADERBOARD_ID, USERNAME)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text('{"status": "BROKEN"}', encoding="utf-8")
    candidate = _ranked(100.0)

    winner, wrote = api_service._save_rank_monotonic(
        LEADERBOARD_ID,
        USERNAME,
        candidate,
    )

    assert wrote is True
    assert winner == candidate
    assert api_service._cached_rank(LEADERBOARD_ID, USERNAME) == candidate


def test_save_rank_monotonic_rejects_one_cent_regression_without_touching_file(
    rank_cache,
):
    api_service.save_scenario_rank(LEADERBOARD_ID, USERNAME, _ranked(100.0))
    cache_file = api_service._rank_cache_file(LEADERBOARD_ID, USERNAME)
    old_timestamp = time.time() - 3600
    os.utime(cache_file, (old_timestamp, old_timestamp))
    original_bytes = cache_file.read_bytes()
    original_mtime = cache_file.stat().st_mtime_ns

    winner, wrote = api_service._save_rank_monotonic(
        LEADERBOARD_ID,
        USERNAME,
        _ranked(99.99),
    )

    assert wrote is False
    assert winner.score == 100.0
    assert cache_file.read_bytes() == original_bytes
    assert cache_file.stat().st_mtime_ns == original_mtime


@pytest.mark.parametrize("candidate", [_unranked(), _ranked(100.0)])
def test_save_rank_monotonic_allows_explicit_regression(rank_cache, candidate):
    api_service.save_scenario_rank(LEADERBOARD_ID, USERNAME, _ranked(110.0))
    cache_file = api_service._rank_cache_file(LEADERBOARD_ID, USERNAME)
    old_timestamp = time.time() - 3600
    os.utime(cache_file, (old_timestamp, old_timestamp))
    original_mtime = cache_file.stat().st_mtime_ns

    winner, wrote = api_service._save_rank_monotonic(
        LEADERBOARD_ID,
        USERNAME,
        candidate,
        allow_regression=True,
    )

    assert wrote is True
    assert winner == candidate
    assert api_service._cached_rank(LEADERBOARD_ID, USERNAME) == candidate
    assert cache_file.stat().st_mtime_ns > original_mtime


@pytest.mark.parametrize("candidate", [_ranked(100.0), _unranked()])
def test_read_path_returns_cached_winner_without_clobber(
    rank_cache,
    monkeypatch,
    candidate,
):
    api_service.save_leaderboard_id(SCENARIO_NAME, LEADERBOARD_ID, "test")
    existing = _ranked(110.0, rank=50).model_copy(
        update={"scenario_name": SCENARIO_NAME}
    )
    api_service.save_scenario_rank(LEADERBOARD_ID, USERNAME, existing)
    cache_file = api_service._rank_cache_file(LEADERBOARD_ID, USERNAME)
    old_timestamp = time.time() - 7200
    os.utime(cache_file, (old_timestamp, old_timestamp))
    original_bytes = cache_file.read_bytes()
    original_mtime = cache_file.stat().st_mtime_ns

    monkeypatch.setattr(api_service, "fetch_scenario_rank", lambda *_args: candidate)
    monkeypatch.setattr(
        api_service,
        "get_user_scenario_total_play",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        api_service,
        "_with_leaderboard_total",
        lambda rank_info, leaderboard_total_cache_ttl_hours: rank_info,
    )

    result = api_service.get_scenario_rank_info(
        SCENARIO_NAME,
        USERNAME,
        rank_cache_ttl_hours=1,
    )

    assert result.score == 110.0
    assert result.rank == 50
    assert cache_file.read_bytes() == original_bytes
    assert cache_file.stat().st_mtime_ns == original_mtime


def test_run_attempt_retries_stale_results_then_saves_fresh_rank(
    rank_cache,
    monkeypatch,
):
    results = [_unranked(), _ranked(99.99), _ranked(100.0)]
    total_refreshes = []

    monkeypatch.setattr(
        api_service,
        "resolve_leaderboard_id",
        lambda *_args: LEADERBOARD_ID,
    )
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: results.pop(0),
    )
    monkeypatch.setattr(
        api_service,
        "_with_leaderboard_total",
        lambda rank_info, leaderboard_total_cache_ttl_hours: total_refreshes.append(
            (rank_info, leaderboard_total_cache_ttl_hours)
        ),
    )

    def run_immediately(*args, **kwargs):
        api_service._run_attempt(*args, **kwargs)

    monkeypatch.setattr(api_service, "_schedule_attempt", run_immediately)

    api_service._run_attempt(
        SCENARIO_NAME,
        USERNAME,
        None,
        100.0,
        24,
        0,
    )

    assert results == []
    assert api_service._cached_rank(LEADERBOARD_ID, USERNAME).score == 100.0
    assert len(total_refreshes) == 1
    assert total_refreshes[0][1] == 0


def test_run_attempt_does_not_refresh_total_when_higher_cache_wins(
    rank_cache,
    monkeypatch,
):
    api_service.save_scenario_rank(LEADERBOARD_ID, USERNAME, _ranked(110.0))
    monkeypatch.setattr(
        api_service,
        "resolve_leaderboard_id",
        lambda *_args: LEADERBOARD_ID,
    )
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: _ranked(100.0),
    )
    monkeypatch.setattr(
        api_service,
        "_with_leaderboard_total",
        lambda *_args, **_kwargs: pytest.fail("total refresh should be skipped"),
    )

    api_service._run_attempt(
        SCENARIO_NAME,
        USERNAME,
        None,
        100.0,
        24,
        0,
    )

    assert api_service._cached_rank(LEADERBOARD_ID, USERNAME).score == 110.0


def test_total_refresh_failure_does_not_undo_rank_save(
    rank_cache,
    monkeypatch,
    caplog,
):
    monkeypatch.setattr(
        api_service,
        "resolve_leaderboard_id",
        lambda *_args: LEADERBOARD_ID,
    )
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: _ranked(100.0),
    )

    def fail_total_refresh(*_args, **_kwargs):
        raise RuntimeError("total cache failure")

    monkeypatch.setattr(
        api_service,
        "_with_leaderboard_total",
        fail_total_refresh,
    )

    with caplog.at_level(logging.WARNING, logger=api_service.__name__):
        api_service._run_attempt(
            SCENARIO_NAME,
            USERNAME,
            None,
            100.0,
            24,
            0,
        )

    assert api_service._cached_rank(LEADERBOARD_ID, USERNAME).score == 100.0
    assert "Total refresh failed after fresh rank" in caplog.text


def test_unknown_user_stops_and_notifies(monkeypatch):
    notifications = []

    def fail_resolution(*_args):
        raise api_service.UnknownKovaaksUserError("unknown user")

    monkeypatch.setattr(api_service, "resolve_leaderboard_id", fail_resolution)
    monkeypatch.setattr(api_service.dash_logger, "error", _capture_log(notifications))
    monkeypatch.setattr(
        api_service,
        "_schedule_attempt",
        lambda *_args, **_kwargs: pytest.fail("must not retry"),
    )

    api_service._run_attempt(SCENARIO_NAME, USERNAME, None, 100.0, 24, 0)

    assert len(notifications) == 1
    assert "username may be misconfigured" in notifications[0]


def test_transient_resolver_error_retries_without_notification_or_traceback(
    rank_cache,
    monkeypatch,
    caplog,
):
    resolution_results = [
        api_service.requests.ConnectionError("temporary outage"),
        LEADERBOARD_ID,
    ]
    notifications = []

    def resolve(*_args):
        result = resolution_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(api_service, "resolve_leaderboard_id", resolve)
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: _ranked(100.0),
    )
    monkeypatch.setattr(api_service.dash_logger, "error", _capture_log(notifications))
    monkeypatch.setattr(
        api_service,
        "_with_leaderboard_total",
        lambda rank_info, leaderboard_total_cache_ttl_hours: rank_info,
    )
    monkeypatch.setattr(
        api_service,
        "_schedule_attempt",
        lambda *args, **kwargs: api_service._run_attempt(*args, **kwargs),
    )

    with caplog.at_level(logging.WARNING, logger=api_service.__name__):
        api_service._run_attempt(
            SCENARIO_NAME,
            USERNAME,
            None,
            100.0,
            24,
            0,
        )

    retry_records = [
        record
        for record in caplog.records
        if "Transient failure resolving leaderboard" in record.getMessage()
    ]
    assert len(retry_records) == 1
    assert retry_records[0].exc_info is None
    assert notifications == []
    assert api_service._cached_rank(LEADERBOARD_ID, USERNAME).score == 100.0


def test_transient_fetch_error_retries(monkeypatch):
    fetch_results = [
        api_service.requests.ConnectionError("temporary outage"),
        _ranked(100.0),
    ]

    def fetch(*_args):
        result = fetch_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(
        api_service,
        "resolve_leaderboard_id",
        lambda *_args: LEADERBOARD_ID,
    )
    monkeypatch.setattr(api_service, "fetch_scenario_rank", fetch)
    monkeypatch.setattr(
        api_service,
        "_save_rank_monotonic",
        lambda *_args: (_ranked(100.0), False),
    )
    monkeypatch.setattr(
        api_service,
        "_schedule_attempt",
        lambda *args, **kwargs: api_service._run_attempt(*args, **kwargs),
    )

    api_service._run_attempt(SCENARIO_NAME, USERNAME, None, 100.0, 24, 0)

    assert fetch_results == []


def test_unresolved_leaderboard_is_warning_only(monkeypatch, caplog):
    notifications = []
    monkeypatch.setattr(
        api_service,
        "resolve_leaderboard_id",
        lambda *_args: None,
    )
    monkeypatch.setattr(api_service.dash_logger, "error", _capture_log(notifications))
    monkeypatch.setattr(
        api_service,
        "_schedule_attempt",
        lambda *_args, **_kwargs: pytest.fail("must not retry"),
    )

    with caplog.at_level(logging.WARNING, logger=api_service.__name__):
        api_service._run_attempt(SCENARIO_NAME, USERNAME, None, 100.0, 24, 0)

    assert "Could not resolve leaderboard" in caplog.text
    assert notifications == []


def test_unexpected_attempt_error_is_caught_and_notified(monkeypatch, caplog):
    notifications = []

    def fail_resolution(*_args):
        raise ValueError("unexpected")

    monkeypatch.setattr(api_service, "resolve_leaderboard_id", fail_resolution)
    monkeypatch.setattr(api_service.dash_logger, "error", _capture_log(notifications))
    monkeypatch.setattr(
        api_service,
        "_schedule_attempt",
        lambda *_args, **_kwargs: pytest.fail("must not retry"),
    )

    with caplog.at_level(logging.ERROR, logger=api_service.__name__):
        api_service._run_attempt(SCENARIO_NAME, USERNAME, None, 100.0, 24, 0)

    matching_records = [
        record
        for record in caplog.records
        if "Unexpected error during rank refresh" in record.getMessage()
    ]
    assert len(matching_records) == 1
    assert matching_records[0].exc_info is not None
    assert notifications == [f"Rank update for {SCENARIO_NAME} failed unexpectedly."]


def test_smoke_stale_scores_retry_on_schedule_and_exhaust_without_cache_writes(
    rank_cache,
    monkeypatch,
    caplog,
):
    api_service.save_scenario_rank(LEADERBOARD_ID, USERNAME, _ranked(90.0))
    api_service.save_leaderboard_total(LEADERBOARD_ID, 1000)
    rank_file = api_service._rank_cache_file(LEADERBOARD_ID, USERNAME)
    total_file = api_service._leaderboard_total_cache_file(LEADERBOARD_ID)
    original_rank = rank_file.read_bytes()
    original_total = total_file.read_bytes()
    pending: list[tuple[Callable, tuple]] = []
    scheduled_delays = []
    fetch_count = 0
    notifications = []

    class FakeTimer:
        def __init__(self, delay, function, args):
            self.delay = delay
            self.function = function
            self.args = args
            self.daemon = False
            scheduled_delays.append(delay)

        def start(self):
            pending.append((self.function, self.args))

    def fetch_stale(*_args):
        nonlocal fetch_count
        fetch_count += 1
        return _ranked(99.99)

    monkeypatch.setattr(api_service.threading, "Timer", FakeTimer)
    monkeypatch.setattr(
        api_service,
        "resolve_leaderboard_id",
        lambda *_args: LEADERBOARD_ID,
    )
    monkeypatch.setattr(api_service, "fetch_scenario_rank", fetch_stale)
    monkeypatch.setattr(api_service.dash_logger, "error", _capture_log(notifications))

    with caplog.at_level(logging.WARNING, logger=api_service.__name__):
        api_service.schedule_rank_freshness_refresh(
            SCENARIO_NAME,
            USERNAME,
            None,
            100.0,
        )
        while pending:
            function, args = pending.pop(0)
            function(*args)

    assert scheduled_delays == list(api_service.ATTEMPT_DELAYS_SECONDS)
    assert fetch_count == len(api_service.ATTEMPT_DELAYS_SECONDS)
    assert rank_file.read_bytes() == original_rank
    assert total_file.read_bytes() == original_total
    assert notifications == [
        f"Rank update timed out for {SCENARIO_NAME}. KovaaK's may still be catching up."
    ]
    assert "Possible score-precision drift" in caplog.text


def test_exhaustion_without_stale_rank_has_no_precision_drift_warning(
    monkeypatch,
    caplog,
):
    monkeypatch.setattr(
        api_service.dash_logger,
        "error",
        lambda _message, *_args: None,
    )

    with caplog.at_level(logging.WARNING, logger=api_service.__name__):
        api_service._notify_exhaustion(SCENARIO_NAME, 100.0, _unranked())

    assert "Rank freshness refresh exhausted" in caplog.text
    assert "Possible score-precision drift" not in caplog.text
