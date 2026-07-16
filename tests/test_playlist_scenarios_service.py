import threading
import time
from datetime import datetime
from types import SimpleNamespace

import pytest
import requests

from source.kovaaks import data_service, playlist_scenarios_service
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from source.kovaaks.data_models import PlaylistData, RunData, Scenario, ScenarioStats
from source.kovaaks.playlist_scenarios_service import (
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
    scenario_stats = ScenarioStats(
        date_last_played=datetime(2026, 4, 28, 21, 30, 0),
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
        "rank_display": "11,290",
        "rank_sort": 11290,
        "total_display": "63,892",
        "total_sort": 63892,
        "percentile_display": "82.33%",
        "percentile_sort": 82.33,
        "last_played_sort": datetime(2026, 4, 28, 21, 30, 0).timestamp(),
        "runs_display": "1,234",
        "runs_sort": 1234,
        "high_score_display": "3,180",
        "high_score_sort": 3180,
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

    assert row["rank_display"] == "Unranked"
    assert row["rank_sort"] is None
    assert row["total_display"] == "63,892"
    assert row["total_sort"] == 63892
    assert row["percentile_display"] == "N/A"
    assert row["percentile_sort"] is None
    assert row["last_played_sort"] is None
    assert row["runs_display"] == "0"
    assert row["runs_sort"] == 0
    assert row["high_score_display"] == "N/A"
    assert row["high_score_sort"] is None
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

    assert row["rank_display"] == "N/A"
    assert row["rank_sort"] is None
    assert row["total_display"] == "N/A"
    assert row["total_sort"] is None
    assert row["percentile_display"] == "N/A"
    assert row["percentile_sort"] is None
    assert row["runs_display"] == "3"
    assert row["runs_sort"] == 3
    assert row["high_score_display"] == "863.93"
    assert row["high_score_sort"] == 863.935
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
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_config",
        lambda: SimpleNamespace(
            kovaaks_username="MingoDynasty",
            steam_id="steam-id",
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
    assert rows[0]["rank_display"] == "10"
    assert rows[1]["rank_display"] == "N/A"
    assert rows[1]["status"] == "UNKNOWN"
    assert rows[1]["runs_display"] == "0"
    assert rows[1]["high_score_display"] == "N/A"
    assert rows[1]["pb_cm360_display"] == "N/A"
    assert rows[1]["pb_accuracy_display"] == "N/A"
    assert rows[2]["rank_display"] == "30"
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
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_config",
        lambda: SimpleNamespace(
            kovaaks_username=username,
            steam_id="steam-id",
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

    assert row["rank_sort"] is None
    assert row["rank_display"] == "Unranked"
    assert row["rank_pending"] is False
    assert row["total_pending"] is False
    assert row["percentile_pending"] is True
    assert row["href"].endswith("scenario=Cached+Unranked")


def test_fill_drain_consumes_terminal_updates_once(isolated_fill_registry):
    state = playlist_scenarios_service._FillState(
        playlist_code="KovaaKsTestCode",
        scenario_names=("First",),
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
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_config",
        lambda: SimpleNamespace(
            kovaaks_username="MingoDynasty",
            steam_id="steam-id",
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
    assert all(row["rank_pending"] is False for row in drain.updates)
    assert all(row["total_pending"] is False for row in drain.updates)
    assert all(row["percentile_pending"] is False for row in drain.updates)
