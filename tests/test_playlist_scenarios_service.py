import logging
import threading
import time
from datetime import datetime
from types import SimpleNamespace

import pytest
import requests

from source.config import settings_service
from source.kovaaks import data_service, playlist_scenarios_service
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from source.kovaaks.api_service import UnknownKovaaksUserError
from source.kovaaks.data_models import (
    PlaylistData,
    Rank,
    RunData,
    Scenario,
    ScenarioStats,
)
from source.kovaaks.playlist_scenarios_service import (
    benchmark_rank_fields,
    build_playlist_scenario_rank_rows,
    format_playlist_scenario_rank_row,
)


def test_playlist_helpers_find_playlist_by_code(monkeypatch):
    playlist = PlaylistData(
        name="Voltaic Benchmarks",
        code="KovaaKsTestCode",
        scenarios=[Scenario(name="First"), Scenario(name="Second")],
    )
    monkeypatch.setattr(data_service, "playlist_database", {playlist.code: playlist})

    assert data_service.get_playlist_by_code("KovaaKsTestCode") == playlist
    assert data_service.get_scenarios_from_playlist_code("KovaaKsTestCode") == [
        "First",
        "Second",
    ]
    assert data_service.get_playlist_selector_options() == [
        {
            "label": "Voltaic Benchmarks",
            "value": "KovaaKsTestCode",
        }
    ]


def test_get_personal_best_run_returns_highest_score(monkeypatch):
    lower_score = RunData(
        datetime_object=datetime(2026, 4, 1, 12, 0, 0),
        score=900,
        sens_scale="cm/360",
        horizontal_sens=42,
        scenario="First",
        accuracy=0.5,
    )
    higher_score = RunData(
        datetime_object=datetime(2026, 4, 2, 12, 0, 0),
        score=1000,
        sens_scale="cm/360",
        horizontal_sens=45,
        scenario="First",
        accuracy=0.6,
    )
    monkeypatch.setattr(
        data_service,
        "kovaaks_database",
        {"First": {"time_vs_runs": [higher_score, lower_score]}},
    )

    assert data_service.get_personal_best_run("First") == higher_score
    assert data_service.get_personal_best_run("Missing") is None


def test_format_playlist_scenario_rank_row_ranked():
    rank_info = ScenarioRankInfo(
        status=ScenarioRankStatus.RANKED,
        rank=11290,
        total_players=63892,
        percentile=82.33,
    )
    # Last played is deliberately later than the PB run: the row must keep the
    # two timestamps distinct ("played since you last improved").
    scenario_stats = ScenarioStats(
        date_last_played=datetime(2026, 5, 3, 19, 0, 0),
        number_of_runs=1234,
        high_score=3180,
    )
    personal_best_run = RunData(
        datetime_object=datetime(2026, 4, 28, 21, 30, 0),
        score=3180,
        sens_scale="cm/360",
        horizontal_sens=45,
        scenario="VT Pasu Intermediate S5",
        accuracy=0.67,
        damage_accuracy=0.7615,
    )

    row = format_playlist_scenario_rank_row(
        "VT Pasu Intermediate S5",
        3,
        rank_info,
        scenario_stats,
        personal_best_run,
    )

    assert row == {
        "scenario": "VT Pasu Intermediate S5",
        "playlist_order": 3,
        "status": "RANKED",
        "position_display": "11,290",
        "position_sort": 11290,
        "total_display": "63,892",
        "total_sort": 63892,
        "percentile_display": "82.33%",
        "percentile_sort": 82.33,
        "last_played_sort": datetime(2026, 5, 3, 19, 0, 0).timestamp(),
        "runs_display": "1,234",
        "runs_sort": 1234,
        "high_score_display": "3,180",
        "high_score_sort": 3180,
        "pb_timestamp_sort": datetime(2026, 4, 28, 21, 30, 0).timestamp(),
        "pb_cm360_display": "45",
        "pb_cm360_sort": 45,
        "pb_accuracy_display": "76.15%",
        "pb_accuracy_sort": 76.15,
    }


def test_format_playlist_scenario_rank_row_unranked_with_total():
    rank_info = ScenarioRankInfo(
        status=ScenarioRankStatus.UNRANKED,
        total_players=63892,
    )

    row = format_playlist_scenario_rank_row("Unplayed Scenario", 0, rank_info)

    assert row["position_display"] == "Unranked"
    assert row["position_sort"] is None
    assert row["total_display"] == "63,892"
    assert row["total_sort"] == 63892
    assert row["percentile_display"] == "N/A"
    assert row["percentile_sort"] is None
    assert row["last_played_sort"] is None
    assert row["runs_display"] == "0"
    assert row["runs_sort"] == 0
    assert row["high_score_display"] == "N/A"
    assert row["high_score_sort"] is None
    assert row["pb_timestamp_sort"] is None
    assert row["pb_cm360_display"] == "N/A"
    assert row["pb_cm360_sort"] is None
    assert row["pb_accuracy_display"] == "N/A"
    assert row["pb_accuracy_sort"] is None


def test_format_playlist_scenario_rank_row_unknown():
    rank_info = ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN)
    scenario_stats = ScenarioStats(
        date_last_played=datetime(2026, 5, 1, 8, 15, 0),
        number_of_runs=3,
        high_score=863.935,
    )

    row = format_playlist_scenario_rank_row(
        "Unknown Scenario",
        0,
        rank_info,
        scenario_stats,
    )

    assert row["position_display"] == "N/A"
    assert row["position_sort"] is None
    assert row["total_display"] == "N/A"
    assert row["total_sort"] is None
    assert row["percentile_display"] == "N/A"
    assert row["percentile_sort"] is None
    assert row["runs_display"] == "3"
    assert row["runs_sort"] == 3
    assert row["high_score_display"] == "863.93"
    assert row["high_score_sort"] == 863.935
    assert row["pb_timestamp_sort"] is None
    assert row["pb_cm360_display"] == "N/A"
    assert row["pb_cm360_sort"] is None
    assert row["pb_accuracy_display"] == "N/A"
    assert row["pb_accuracy_sort"] is None


def test_format_playlist_scenario_rank_row_uses_hit_accuracy_fallback():
    rank_info = ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN)
    personal_best_run = RunData(
        datetime_object=datetime(2026, 4, 28, 21, 30, 0),
        score=1000,
        sens_scale="Overwatch",
        horizontal_sens=6,
        scenario="Unknown Scenario",
        accuracy=0.5,
    )

    row = format_playlist_scenario_rank_row(
        "Unknown Scenario",
        0,
        rank_info,
        personal_best_run=personal_best_run,
    )

    assert row["pb_cm360_display"] == "N/A"
    assert row["pb_cm360_sort"] is None
    assert row["pb_accuracy_display"] == "50.00%"
    assert row["pb_accuracy_sort"] == 50
    # The PB timestamp does not depend on the run's sensitivity scale.
    assert row["pb_timestamp_sort"] == datetime(2026, 4, 28, 21, 30, 0).timestamp()


def test_build_playlist_scenario_rank_rows_preserves_order_and_isolates_failures(
    monkeypatch,
):
    playlist = PlaylistData(
        name="Voltaic Benchmarks",
        code="KovaaKsTestCode",
        scenarios=[
            Scenario(name="First"),
            Scenario(name="Second"),
            Scenario(name="Third"),
        ],
    )
    monkeypatch.setattr(data_service, "playlist_database", {playlist.code: playlist})
    settings_service.save_settings(
        {"kovaaks_username": "MingoDynasty", "steam_id": "steam-id"}
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_config",
        lambda: SimpleNamespace(
            scenario_metadata_cache_ttl_hours=24,
            scenario_rank_cache_ttl_hours=168,
            leaderboard_total_cache_ttl_hours=24,
        ),
    )
    # All scenarios already mapped, so the hoisted hydration is skipped.
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_cached_leaderboard_id",
        lambda scenario_name: 1,
    )
    seen = []

    def fake_rank_lookup(
        scenario_name,
        username,
        steam_id,
        metadata_cache_ttl_hours,
        rank_cache_ttl_hours,
        leaderboard_total_cache_ttl_hours,
        allow_network=True,
        allow_hydration=True,
    ):
        seen.append(scenario_name)
        assert username == "MingoDynasty"
        assert steam_id == "steam-id"
        assert metadata_cache_ttl_hours == 24
        assert rank_cache_ttl_hours == 168
        assert leaderboard_total_cache_ttl_hours == 24
        assert allow_network is False
        assert allow_hydration is False
        if scenario_name == "Second":
            raise RuntimeError("simulated rank failure")
        return ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=10 if scenario_name == "First" else 30,
            total_players=100,
            percentile=90.5 if scenario_name == "First" else 70.5,
        )

    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_scenario_rank_info",
        fake_rank_lookup,
    )
    local_stats = {
        "First": ScenarioStats(
            date_last_played=datetime(2026, 4, 1, 12, 0, 0),
            number_of_runs=10,
            high_score=1000,
        ),
        "Third": ScenarioStats(
            date_last_played=datetime(2026, 4, 3, 12, 0, 0),
            number_of_runs=30,
            high_score=3000.5,
        ),
    }
    personal_best_runs = {
        "First": RunData(
            datetime_object=datetime(2026, 4, 1, 12, 0, 0),
            score=1000,
            sens_scale="cm/360",
            horizontal_sens=42.5,
            scenario="First",
            accuracy=0.65,
            damage_accuracy=0.8125,
        ),
        "Third": RunData(
            datetime_object=datetime(2026, 4, 3, 12, 0, 0),
            score=3000.5,
            sens_scale="cm/360",
            horizontal_sens=45,
            scenario="Third",
            accuracy=0.72,
            damage_accuracy=0.8234,
        ),
    }
    monkeypatch.setattr(
        playlist_scenarios_service,
        "is_scenario_in_database",
        lambda scenario_name: scenario_name in local_stats,
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_scenario_stats",
        local_stats.__getitem__,
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_personal_best_run",
        personal_best_runs.__getitem__,
    )

    rows = build_playlist_scenario_rank_rows("KovaaKsTestCode", "generation-1")

    assert {row["scenario"] for row in rows} == {"First", "Second", "Third"}
    assert set(seen) == {"First", "Second", "Third"}
    assert [row["scenario"] for row in rows] == ["First", "Second", "Third"]
    assert rows[0]["position_display"] == "10"
    assert rows[1]["position_display"] == "N/A"
    assert rows[1]["status"] == "UNKNOWN"
    assert rows[1]["runs_display"] == "0"
    assert rows[1]["high_score_display"] == "N/A"
    assert rows[1]["pb_cm360_display"] == "N/A"
    assert rows[1]["pb_accuracy_display"] == "N/A"
    assert rows[2]["position_display"] == "30"
    assert rows[2]["runs_display"] == "30"
    assert rows[2]["high_score_display"] == "3,000.5"
    assert rows[2]["pb_cm360_display"] == "45"
    assert rows[2]["pb_accuracy_display"] == "82.34%"
    assert all(row["generation_token"] == "generation-1" for row in rows)


def test_build_playlist_scenario_rank_rows_returns_empty_for_unknown_playlist():
    rows = build_playlist_scenario_rank_rows("MissingCode", "generation-1")

    assert rows == []


def _setup_playlist_for_hydration(monkeypatch, *, mapped, username="MingoDynasty"):
    """Register a two-scenario playlist and stub the per-scenario rank lookup.

    ``mapped`` maps scenario name -> cached leaderboard id (or None to mark it
    unmapped), driving the any-unmapped hydration gate.
    """
    playlist = PlaylistData(
        name="Voltaic Benchmarks",
        code="KovaaKsTestCode",
        scenarios=[Scenario(name="First"), Scenario(name="Second")],
    )
    monkeypatch.setattr(data_service, "playlist_database", {playlist.code: playlist})
    settings_service.save_settings(
        {"kovaaks_username": username or "", "steam_id": "steam-id"}
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_config",
        lambda: SimpleNamespace(
            scenario_metadata_cache_ttl_hours=24,
            scenario_rank_cache_ttl_hours=168,
            leaderboard_total_cache_ttl_hours=24,
        ),
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_cached_leaderboard_id",
        mapped.get,
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "is_scenario_in_database",
        lambda scenario_name: False,
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_scenario_rank_info",
        lambda *args, **kwargs: ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=10,
            total_players=100,
            percentile=90.0,
        ),
    )


def test_hydration_runs_once_when_a_scenario_is_unmapped(monkeypatch):
    _setup_playlist_for_hydration(monkeypatch, mapped={"First": 1, "Second": None})
    calls = []
    monkeypatch.setattr(
        playlist_scenarios_service,
        "hydrate_leaderboard_id_cache",
        lambda username, ttl: calls.append((username, ttl)),
    )

    playlist_scenarios_service._hydrate_playlist_leaderboard_ids(["First", "Second"])

    assert calls == [("MingoDynasty", 24)]


def test_hydration_skipped_when_every_scenario_is_mapped(monkeypatch):
    _setup_playlist_for_hydration(monkeypatch, mapped={"First": 1, "Second": 2})
    calls = []
    monkeypatch.setattr(
        playlist_scenarios_service,
        "hydrate_leaderboard_id_cache",
        lambda username, ttl: calls.append((username, ttl)),
    )

    playlist_scenarios_service._hydrate_playlist_leaderboard_ids(["First", "Second"])

    assert calls == []


def test_hydration_skipped_when_username_unset(monkeypatch):
    _setup_playlist_for_hydration(
        monkeypatch, mapped={"First": None, "Second": None}, username=None
    )
    calls = []
    monkeypatch.setattr(
        playlist_scenarios_service,
        "hydrate_leaderboard_id_cache",
        lambda username, ttl: calls.append((username, ttl)),
    )

    playlist_scenarios_service._hydrate_playlist_leaderboard_ids(["First", "Second"])

    assert calls == []


def test_hydration_failure_still_yields_full_rows(monkeypatch):
    _setup_playlist_for_hydration(monkeypatch, mapped={"First": None, "Second": None})

    def failing_hydrate(username, ttl):
        raise requests.RequestException("simulated total-play failure")

    monkeypatch.setattr(
        playlist_scenarios_service,
        "hydrate_leaderboard_id_cache",
        failing_hydrate,
    )

    playlist_scenarios_service._hydrate_playlist_leaderboard_ids(["First", "Second"])
    rows = build_playlist_scenario_rank_rows("KovaaKsTestCode", "generation-1")

    assert [row["scenario"] for row in rows] == ["First", "Second"]


def test_hydration_unexpected_error_still_yields_full_rows(monkeypatch):
    # A schema-drifted total-play cache can raise ValidationError/KeyError, not
    # just RequestException. The hoisted hydration is best-effort, so an
    # unexpected error must not take down the whole playlist page.
    _setup_playlist_for_hydration(monkeypatch, mapped={"First": None, "Second": None})

    def failing_hydrate(username, ttl):
        raise KeyError("data")

    monkeypatch.setattr(
        playlist_scenarios_service,
        "hydrate_leaderboard_id_cache",
        failing_hydrate,
    )

    playlist_scenarios_service._hydrate_playlist_leaderboard_ids(["First", "Second"])
    rows = build_playlist_scenario_rank_rows("KovaaKsTestCode", "generation-1")

    assert [row["scenario"] for row in rows] == ["First", "Second"]


@pytest.mark.parametrize(
    ("make_error", "message", "has_traceback"),
    [
        # Empty text: the summary helper falls back to the class name.
        (
            requests.ConnectionError,
            "Failed to hydrate leaderboard metadata for playlist open: ConnectionError",
            False,
        ),
        (
            lambda: UnknownKovaaksUserError(
                "KovaaK's username \"Ghost\" wasn't found."
            ),
            "Failed to hydrate leaderboard metadata for playlist open: "
            "KovaaK's username \"Ghost\" wasn't found.",
            False,
        ),
        (
            lambda: KeyError("data"),
            "Failed to hydrate leaderboard metadata for playlist open",
            True,
        ),
    ],
)
def test_hydration_failure_logs_each_route(
    monkeypatch, caplog, make_error, message, has_traceback
):
    _setup_playlist_for_hydration(monkeypatch, mapped={"First": None, "Second": None})

    def failing_hydrate(username, ttl):
        raise make_error()

    monkeypatch.setattr(
        playlist_scenarios_service,
        "hydrate_leaderboard_id_cache",
        failing_hydrate,
    )

    with caplog.at_level(
        logging.WARNING, logger=playlist_scenarios_service.logger.name
    ):
        playlist_scenarios_service._hydrate_playlist_leaderboard_ids(
            ["First", "Second"]
        )

    [record] = caplog.records
    assert record.getMessage() == message
    assert (record.exc_info is not None) is has_traceback


def test_hydration_probe_error_still_yields_full_rows(monkeypatch):
    # get_cached_leaderboard_id can raise (e.g. int() on a malformed cached id).
    # The any-unmapped probe runs inside the best-effort guard, so a probe
    # failure must not take down the whole playlist page either.
    _setup_playlist_for_hydration(monkeypatch, mapped={"First": 1, "Second": 2})

    def failing_probe(scenario_name):
        raise ValueError("malformed leaderboard_id in mapping cache")

    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_cached_leaderboard_id",
        failing_probe,
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "hydrate_leaderboard_id_cache",
        lambda username, ttl: None,
    )

    playlist_scenarios_service._hydrate_playlist_leaderboard_ids(["First", "Second"])
    rows = build_playlist_scenario_rank_rows("KovaaKsTestCode", "generation-1")

    assert [row["scenario"] for row in rows] == ["First", "Second"]


@pytest.fixture
def isolated_fill_registry():
    with playlist_scenarios_service._FILL_REGISTRY_LOCK:
        for state in playlist_scenarios_service._FILL_REGISTRY.values():
            state.cancel_event.set()
        playlist_scenarios_service._FILL_REGISTRY.clear()
    yield
    with playlist_scenarios_service._FILL_REGISTRY_LOCK:
        for state in playlist_scenarios_service._FILL_REGISTRY.values():
            state.cancel_event.set()
        playlist_scenarios_service._FILL_REGISTRY.clear()


def test_phase_one_pending_flags_are_explicit_per_cell():
    rank_info = ScenarioRankInfo(
        status=ScenarioRankStatus.UNRANKED,
        total_players=100,
    )

    row = format_playlist_scenario_rank_row(
        "Cached Unranked",
        0,
        rank_info,
        generation_token="generation-1",
        playlist_code="KovaaKsTestCode",
        mark_unresolved_pending=True,
    )

    assert row["position_sort"] is None
    assert row["position_display"] == "Unranked"
    assert row["position_pending"] is False
    assert row["total_pending"] is False
    assert row["percentile_pending"] is True
    assert row["href"].endswith("scenario=Cached+Unranked")


def test_fill_drain_consumes_terminal_updates_once(isolated_fill_registry):
    state = playlist_scenarios_service._FillState(
        playlist_code="KovaaKsTestCode",
        scenario_names=("First",),
        scenario_ladders=(None,),
        total=1,
        unresolved_indices=set(),
        pending_updates=[{"scenario": "First"}],
        done_count=1,
        terminal="complete",
    )
    with playlist_scenarios_service._FILL_REGISTRY_LOCK:
        playlist_scenarios_service._FILL_REGISTRY["generation-1"] = state

    consuming = playlist_scenarios_service.drain_playlist_scenario_fill("generation-1")
    post_consumption = playlist_scenarios_service.drain_playlist_scenario_fill(
        "generation-1"
    )

    assert consuming is not None
    assert consuming.consuming_terminal is True
    assert consuming.updates == [{"scenario": "First"}]
    assert post_consumption is not None
    assert post_consumption.consuming_terminal is False
    assert post_consumption.updates == []


def test_fill_outcomes_use_structural_stale_marker(isolated_fill_registry):
    state = playlist_scenarios_service._FillState(
        playlist_code="KovaaKsTestCode",
        scenario_names=("Mismatch", "Stale", "Unknown"),
        scenario_ladders=(None, None, None),
        total=3,
        unresolved_indices={0, 1, 2},
    )
    with playlist_scenarios_service._FILL_REGISTRY_LOCK:
        playlist_scenarios_service._FILL_REGISTRY["generation-1"] = state

    playlist_scenarios_service._record_fill_result(
        "generation-1",
        0,
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            warning_message="Configured Steam ID differs.",
        ),
        {"scenario": "Mismatch"},
    )
    playlist_scenarios_service._record_fill_result(
        "generation-1",
        1,
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            warning_message="Showing cached data.",
            served_stale=True,
        ),
        {"scenario": "Stale"},
    )
    playlist_scenarios_service._record_fill_result(
        "generation-1",
        2,
        ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN),
        {"scenario": "Unknown"},
    )

    snapshot = playlist_scenarios_service.drain_playlist_scenario_fill("generation-1")

    assert snapshot is not None
    assert snapshot.done_count == 3
    assert snapshot.stale_count == 1
    assert snapshot.unknown_count == 1


def test_fill_worker_exception_cancels_and_finalizes_pending_rows(
    monkeypatch,
    caplog,
    isolated_fill_registry,
):
    scenario_names = ("First", "Second")
    scenario_ladders = (None, None)
    state = playlist_scenarios_service._FillState(
        playlist_code="KovaaKsTestCode",
        scenario_names=scenario_names,
        scenario_ladders=scenario_ladders,
        total=len(scenario_names),
        unresolved_indices=set(range(len(scenario_names))),
    )
    with playlist_scenarios_service._FILL_REGISTRY_LOCK:
        playlist_scenarios_service._FILL_REGISTRY["generation-1"] = state

    monkeypatch.setattr(
        playlist_scenarios_service,
        "_hydrate_playlist_leaderboard_ids",
        lambda _scenario_names: None,
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "_fetch_fill_row",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "_lookup_rank_info",
        lambda scenario_name, *, allow_network: ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            scenario_name=scenario_name,
        ),
    )

    with caplog.at_level(logging.ERROR):
        playlist_scenarios_service._run_playlist_scenario_fill(
            "generation-1",
            scenario_names,
            scenario_ladders,
            state.cancel_event,
        )

    with playlist_scenarios_service._FILL_REGISTRY_LOCK:
        assert state.terminal == "cancelled"
        assert state.cancel_event.is_set()
    assert "Playlist scenario fill failed for generation generation-1" in caplog.text

    drain = playlist_scenarios_service.drain_playlist_scenario_fill("generation-1")

    assert drain is not None
    assert drain.terminal == "cancelled"
    assert drain.consuming_terminal is True
    assert len(drain.updates) == len(scenario_names)
    assert all(row["position_pending"] is False for row in drain.updates)
    assert all(row["total_pending"] is False for row in drain.updates)
    assert all(row["percentile_pending"] is False for row in drain.updates)


def test_tombstone_retention_evicts_consumed_before_unconsumed(
    monkeypatch,
    isolated_fill_registry,
):
    monkeypatch.setattr(playlist_scenarios_service, "FILL_TOMBSTONE_LIMIT", 3)

    with playlist_scenarios_service._FILL_REGISTRY_LOCK:
        for token, consumed in (
            ("unconsumed-old", False),
            ("consumed-newer", True),
            ("unconsumed-newer", False),
            ("incoming", False),
        ):
            state = playlist_scenarios_service._FillState(
                playlist_code=token,
                scenario_names=(),
                scenario_ladders=(),
                total=0,
                unresolved_indices=set(),
                consumed=consumed,
            )
            playlist_scenarios_service._FILL_REGISTRY[token] = state
            playlist_scenarios_service._transition_terminal_locked(
                state,
                "complete",
            )

        retained = set(playlist_scenarios_service._FILL_REGISTRY)

    assert retained == {"unconsumed-old", "unconsumed-newer", "incoming"}


def test_new_fill_cancels_synchronously_and_banks_inflight_fetch(
    monkeypatch,
    isolated_fill_registry,
):
    playlist = PlaylistData(
        name="Voltaic Benchmarks",
        code="KovaaKsTestCode",
        scenarios=[
            Scenario(name="First"),
            Scenario(name="Second"),
            Scenario(name="Third"),
        ],
    )
    monkeypatch.setattr(data_service, "playlist_database", {playlist.code: playlist})
    settings_service.save_settings(
        {"kovaaks_username": "MingoDynasty", "steam_id": "steam-id"}
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_config",
        lambda: SimpleNamespace(
            scenario_metadata_cache_ttl_hours=24,
            scenario_rank_cache_ttl_hours=168,
            leaderboard_total_cache_ttl_hours=24,
        ),
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_cached_leaderboard_id",
        lambda _name: 1,
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "is_scenario_in_database",
        lambda _name: False,
    )
    monkeypatch.setattr(playlist_scenarios_service, "PLAYLIST_RANK_MAX_WORKERS", 1)

    network_started = threading.Event()
    release_network = threading.Event()
    network_finished = threading.Event()
    network_calls = []

    def fake_rank_lookup(scenario_name, *_args, **kwargs):
        if kwargs["allow_network"]:
            network_calls.append(scenario_name)
            network_started.set()
            assert release_network.wait(timeout=2)
            network_finished.set()
        return ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=10,
            total_players=100,
            percentile=90.5,
        )

    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_scenario_rank_info",
        fake_rank_lookup,
    )

    assert playlist_scenarios_service.start_playlist_scenario_fill(
        playlist.code,
        "generation-1",
    )
    assert network_started.wait(timeout=2)

    class UnstartedThread:
        def __init__(self, **_kwargs):
            pass

        def start(self):
            pass

    monkeypatch.setattr(threading, "Thread", UnstartedThread)
    assert playlist_scenarios_service.start_playlist_scenario_fill(
        playlist.code,
        "generation-2",
    )

    with playlist_scenarios_service._FILL_REGISTRY_LOCK:
        cancelled = playlist_scenarios_service._FILL_REGISTRY["generation-1"]
        assert cancelled.terminal == "cancelled"
        assert cancelled.cancel_event.is_set()

    release_network.set()
    assert network_finished.wait(timeout=2)
    time.sleep(0.05)

    drain = playlist_scenarios_service.drain_playlist_scenario_fill("generation-1")

    assert network_calls == ["First"]
    assert drain is not None
    assert drain.terminal == "cancelled"
    assert drain.done_count == 0
    assert len(drain.updates) == 3
    assert all(row["position_pending"] is False for row in drain.updates)
    assert all(row["total_pending"] is False for row in drain.updates)
    assert all(row["percentile_pending"] is False for row in drain.updates)


def test_format_playlist_scenario_rank_row_fills_pb_cm360_for_a_converted_run(
    monkeypatch,
    tmp_path,
):
    # The other "N/A" cases build a non-cm/360 ``RunData`` directly, which at
    # this layer is exactly a legacy run. A converted PB only exists downstream
    # of the parser, so this one goes through it: a real Valorant-era stats
    # file, whose increment and DPI make its sensitivity 40.8 cm/360.
    file_path = tmp_path / "Converted PB - Challenge - 2025.03.04-21.30.00 Stats.csv"
    file_path.write_text(
        "\n".join(
            [
                "Score:,1000",
                "Sens Scale:,Valorant",
                "Sens Increment:,0.199886",
                "Horiz Sens:,0.2",
                "Vert Sens:,0.2",
                "DPI:,1600",
                "Scenario:,Converted PB",
                data_service.POSSIBLE_SUB_CSV_HEADERS[0],
                "Rifle,100,50,75,100,,Valorant,0.2,0.2,103,0,0,0,0,0,0,0,0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    personal_best_run = data_service.extract_data_from_file(str(file_path))
    assert personal_best_run is not None
    assert personal_best_run.sens_scale == "cm/360"

    row = format_playlist_scenario_rank_row(
        "Converted PB",
        0,
        ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN),
        personal_best_run=personal_best_run,
    )

    assert row["pb_cm360_sort"] == 40.8
    assert row["pb_cm360_display"] == "40.8"


# --- benchmark Rank and Next Rank ---

RANK_NAMES = ("Iron", "Bronze", "Silver", "Gold", "Platinum", "Diamond")
RANK_FIELDS = (
    "tier_display",
    "tier_sort",
    "next_tier_display",
    "next_tier_sort",
    "next_tier_tooltip",
)


def _ladder(*thresholds: float) -> list[Rank]:
    return [
        Rank(name=RANK_NAMES[index], color="#ffffff", threshold=threshold)
        for index, threshold in enumerate(thresholds)
    ]


@pytest.mark.parametrize(
    (
        "thresholds",
        "pb",
        "tier_display",
        "tier_sort",
        "next_tier_display",
        "next_threshold",
        "next_tier_tooltip",
    ),
    [
        # A strictly ascending ladder.
        pytest.param(
            (100, 110, 120),
            90,
            "No rank",
            0,
            "+11.2% to Iron",
            100,
            "Iron at 100 · 10 to go",
            id="below-first",
        ),
        pytest.param(
            (100, 110, 120),
            105,
            "Iron",
            1,
            "+4.8% to Bronze",
            110,
            "Bronze at 110 · 5 to go",
            id="mid-band",
        ),
        pytest.param(
            (100, 110, 120),
            110,
            "Bronze",
            2,
            "+9.1% to Silver",
            120,
            "Silver at 120 · 10 to go",
            id="on-threshold",
        ),
        pytest.param(
            (100, 110, 120),
            120,
            "Silver",
            3,
            "Top rank",
            None,
            None,
            id="on-last",
        ),
        pytest.param(
            (100, 110, 120),
            500,
            "Silver",
            3,
            "Top rank",
            None,
            None,
            id="past-last",
        ),
        # Tied thresholds: a PB on the tie passes both.
        pytest.param(
            (130, 142, 142),
            141,
            "Iron",
            1,
            "+0.8% to Bronze",
            142,
            "Bronze at 142 · 1 to go",
            id="tie-below",
        ),
        pytest.param(
            (130, 142, 142),
            142,
            "Silver",
            3,
            "Top rank",
            None,
            None,
            id="tie-on",
        ),
        # Non-monotonic: the walk stops at the first unmet threshold, even when
        # the PB beats a later, lower one.
        pytest.param(
            (36, 54, 50, 58),
            52,
            "Iron",
            1,
            "+3.9% to Bronze",
            54,
            "Bronze at 54 · 2 to go",
            id="early-dip",
        ),
        pytest.param(
            (2800, 2850, 2900, 2950, 2900, 3000),
            2920,
            "Silver",
            3,
            "+1.1% to Gold",
            2950,
            "Gold at 2,950 · 30 to go",
            id="mid-dip-below",
        ),
        pytest.param(
            (2800, 2850, 2900, 2950, 2900, 3000),
            2960,
            "Platinum",
            5,
            "+1.4% to Diamond",
            3000,
            "Diamond at 3,000 · 40 to go",
            id="mid-dip-past",
        ),
        pytest.param(
            (1700, 2000, 1933),
            1950,
            "Iron",
            1,
            "+2.6% to Bronze",
            2000,
            "Bronze at 2,000 · 50 to go",
            id="final-descent-below",
        ),
        pytest.param(
            (1700, 2000, 1933),
            2000,
            "Silver",
            3,
            "Top rank",
            None,
            None,
            id="final-descent-past",
        ),
        # Zero thresholds: a PB of zero reaches them.
        pytest.param(
            (0, 250, 275),
            100,
            "Iron",
            1,
            "+150.0% to Bronze",
            250,
            "Bronze at 250 · 150 to go",
            id="zero-first",
        ),
        pytest.param(
            (0, 250, 275),
            0,
            "Iron",
            1,
            "N/A",
            None,
            None,
            id="zero-first-pb-zero",
        ),
        pytest.param(
            (0, 0, 0, 0),
            0,
            "Gold",
            4,
            "Top rank",
            None,
            None,
            id="all-zero-pb-zero",
        ),
        pytest.param(
            (0, 0, 0, 0),
            50,
            "Gold",
            4,
            "Top rank",
            None,
            None,
            id="all-zero",
        ),
        # A single rank.
        pytest.param(
            (1000,),
            900,
            "No rank",
            0,
            "+11.2% to Iron",
            1000,
            "Iron at 1,000 · 100 to go",
            id="single-below",
        ),
        pytest.param(
            (1000,),
            1000,
            "Iron",
            1,
            "Top rank",
            None,
            None,
            id="single-on",
        ),
        # No PB, a PB of zero or less, and no ladder.
        pytest.param(
            (100, 110),
            None,
            "N/A",
            None,
            "N/A",
            None,
            None,
            id="no-pb",
        ),
        pytest.param(
            (100, 110),
            0,
            "No rank",
            0,
            "N/A",
            None,
            None,
            id="pb-zero",
        ),
        pytest.param(
            (100, 110),
            -5,
            "No rank",
            0,
            "N/A",
            None,
            None,
            id="pb-negative",
        ),
        pytest.param(
            (),
            100,
            "N/A",
            None,
            "N/A",
            None,
            None,
            id="no-ladder",
        ),
        # Number formats and rounding up.
        pytest.param(
            (940,),
            50,
            "No rank",
            0,
            "+1,780.0% to Iron",
            940,
            "Iron at 940 · 890 to go",
            id="thousands",
        ),
        pytest.param(
            (1000,),
            999.96,
            "No rank",
            0,
            "+0.1% to Iron",
            1000,
            "Iron at 1,000 · 0.04 to go",
            id="gap-rounds-up",
        ),
        pytest.param(
            (1000,),
            999.999,
            "No rank",
            0,
            "+0.1% to Iron",
            1000,
            "Iron at 1,000 · 0.01 to go",
            id="points-round-up",
        ),
        pytest.param(
            (3.08,),
            2.8,
            "No rank",
            0,
            "+10.0% to Iron",
            3.08,
            "Iron at 3.08 · 0.28 to go",
            id="float-noise",
        ),
        pytest.param(
            (10000,),
            9999.999999,
            "No rank",
            0,
            "+0.1% to Iron",
            10000,
            "Iron at 10,000 · 0.01 to go",
            id="gap-floor",
        ),
        pytest.param(
            (1000,),
            999.999999999,
            "No rank",
            0,
            "+0.1% to Iron",
            1000,
            "Iron at 1,000 · 0.01 to go",
            id="points-floor",
        ),
    ],
)
def test_benchmark_rank_fields(
    thresholds,
    pb,
    tier_display,
    tier_sort,
    next_tier_display,
    next_threshold,
    next_tier_tooltip,
):
    fields = benchmark_rank_fields(_ladder(*thresholds), pb)

    # The sort key is the unrounded gap, whatever the cell shows.
    next_tier_sort = (
        None if next_threshold is None else (next_threshold - pb) / pb * 100
    )
    assert fields == {
        "tier_display": tier_display,
        "tier_sort": tier_sort,
        "next_tier_display": next_tier_display,
        "next_tier_sort": next_tier_sort,
        "next_tier_tooltip": next_tier_tooltip,
    }


@pytest.mark.parametrize(
    "thresholds",
    [
        pytest.param((130, 142, 142), id="tie"),
        pytest.param((36, 54, 50, 58), id="early-dip"),
        pytest.param((2800, 2850, 2900, 2950, 2900, 3000), id="mid-dip"),
        pytest.param((1700, 2000, 1933), id="final-descent"),
        pytest.param((0, 250, 275), id="zero-first"),
    ],
)
def test_benchmark_rank_fields_never_pass_an_unmet_threshold(thresholds):
    ladder = _ladder(*thresholds)
    pbs = sorted(
        {pb for threshold in thresholds for pb in (threshold - 1, threshold)}
        | {threshold + 0.5 for threshold in thresholds}
    )

    for pb in pbs:
        fields = benchmark_rank_fields(ladder, pb)
        passed = fields["tier_sort"]
        assert all(rank.threshold <= pb for rank in ladder[:passed])
        if passed < len(ladder):
            assert ladder[passed].threshold > pb
        if fields["next_tier_sort"] is not None:
            assert fields["next_tier_sort"] > 0


def test_format_playlist_scenario_rank_row_adds_rank_fields_for_a_ladder():
    scenario_stats = ScenarioStats(
        date_last_played=datetime(2026, 5, 1, 8, 15, 0),
        number_of_runs=3,
        high_score=105,
    )

    benchmark_row = format_playlist_scenario_rank_row(
        "First",
        0,
        ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN),
        scenario_stats,
        ladder=_ladder(100, 110, 120),
    )
    playlist_row = format_playlist_scenario_rank_row(
        "First",
        0,
        ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN),
        scenario_stats,
    )

    assert {field: benchmark_row[field] for field in RANK_FIELDS} == {
        "tier_display": "Iron",
        "tier_sort": 1,
        "next_tier_display": "+4.8% to Bronze",
        "next_tier_sort": (110 - 105) / 105 * 100,
        "next_tier_tooltip": "Bronze at 110 · 5 to go",
    }
    assert not set(RANK_FIELDS) & set(playlist_row)
    assert {
        field: value
        for field, value in benchmark_row.items()
        if field not in RANK_FIELDS
    } == playlist_row


_BENCHMARK = PlaylistData(
    name="Test Benchmark",
    code="KovaaKsBenchmarkCode",
    scenarios=[
        Scenario(name="Ranked", ranks=_ladder(100, 110, 120)),
        Scenario(name="Unplayed", ranks=_ladder(100, 110, 120)),
        Scenario(name="No Ladder"),
        Scenario(name="Top", ranks=_ladder(100, 110, 120)),
    ],
)
_PLAYLIST = PlaylistData(
    name="Test Playlist",
    code="KovaaKsPlaylistCode",
    scenarios=[Scenario(name="Ranked"), Scenario(name="Unplayed")],
)


@pytest.fixture
def rank_row_sources(monkeypatch):
    """Serve both test playlists and the same local stats to every row path."""
    monkeypatch.setattr(
        data_service,
        "playlist_database",
        {playlist.code: playlist for playlist in (_BENCHMARK, _PLAYLIST)},
    )
    settings_service.save_settings(
        {"kovaaks_username": "MingoDynasty", "steam_id": "steam-id"}
    )
    local_stats = {
        name: ScenarioStats(
            date_last_played=datetime(2026, 4, 1, 12, 0, 0),
            number_of_runs=10,
            high_score=high_score,
        )
        for name, high_score in (("Ranked", 105), ("No Ladder", 50), ("Top", 130))
    }
    monkeypatch.setattr(
        playlist_scenarios_service,
        "is_scenario_in_database",
        lambda scenario_name: scenario_name in local_stats,
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_scenario_stats",
        local_stats.__getitem__,
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_personal_best_run",
        lambda _scenario_name: None,
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "_hydrate_playlist_leaderboard_ids",
        lambda _scenario_names: None,
    )
    # Every path sees the same position, so its rows can equal phase 1's whole.
    monkeypatch.setattr(
        playlist_scenarios_service,
        "_lookup_rank_info",
        lambda _scenario_name, *, allow_network: ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=10,
            total_players=100,
            percentile=90.0,
        ),
    )


def test_phase_one_rows_carry_rank_fields_only_on_a_benchmark(rank_row_sources):
    benchmark_rows = build_playlist_scenario_rank_rows(_BENCHMARK.code, "generation-1")
    playlist_rows = build_playlist_scenario_rank_rows(_PLAYLIST.code, "generation-1")

    assert [
        (row["scenario"], row["tier_display"], row["next_tier_display"])
        for row in benchmark_rows
    ] == [
        ("Ranked", "Iron", "+4.8% to Bronze"),
        ("Unplayed", "N/A", "N/A"),
        ("No Ladder", "N/A", "N/A"),
        ("Top", "Silver", "Top rank"),
    ]
    assert all(not set(RANK_FIELDS) & set(row) for row in playlist_rows)


def _register_fill(monkeypatch, playlist_code, generation_token):
    """Register a fill without starting its daemon; return the daemon's call.

    Only the fill's own thread is held back. Patching ``threading.Thread`` for
    longer would also capture the fill's worker pool.
    """
    calls = []

    class HeldThread:
        def __init__(self, *, target, args, **_kwargs):
            calls.append((target, args))

        def start(self):
            pass

    with monkeypatch.context() as patch:
        patch.setattr(threading, "Thread", HeldThread)
        assert playlist_scenarios_service.start_playlist_scenario_fill(
            playlist_code, generation_token
        )
    [(target, args)] = calls
    return target, args


@pytest.mark.parametrize(
    "playlist", [_BENCHMARK, _PLAYLIST], ids=["benchmark", "playlist"]
)
def test_fill_rows_equal_phase_one_rows(
    monkeypatch,
    rank_row_sources,
    isolated_fill_registry,
    playlist,
):
    phase_one = build_playlist_scenario_rank_rows(playlist.code, "generation-1")
    target, args = _register_fill(monkeypatch, playlist.code, "generation-1")

    target(*args)
    drain = playlist_scenarios_service.drain_playlist_scenario_fill("generation-1")

    assert drain is not None
    assert drain.terminal == "complete"
    assert sorted(drain.updates, key=lambda row: row["playlist_order"]) == phase_one


@pytest.mark.parametrize(
    "playlist", [_BENCHMARK, _PLAYLIST], ids=["benchmark", "playlist"]
)
def test_cancelled_fill_rebuild_rows_equal_phase_one_rows(
    monkeypatch,
    rank_row_sources,
    isolated_fill_registry,
    playlist,
):
    phase_one = build_playlist_scenario_rank_rows(playlist.code, "generation-1")
    _register_fill(monkeypatch, playlist.code, "generation-1")
    # Opening any playlist in another tab cancels this fill before it fetches.
    _register_fill(monkeypatch, _PLAYLIST.code, "generation-2")

    drain = playlist_scenarios_service.drain_playlist_scenario_fill("generation-1")

    assert drain is not None
    assert drain.terminal == "cancelled"
    assert drain.consuming_terminal is True
    assert drain.updates == phase_one
    with playlist_scenarios_service._FILL_REGISTRY_LOCK:
        state = playlist_scenarios_service._FILL_REGISTRY["generation-1"]
        assert state.scenario_names == ()
        assert state.scenario_ladders == ()
