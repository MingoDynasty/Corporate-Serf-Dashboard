import logging
import threading
import time
from datetime import datetime, timedelta
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
    TypicalSnapshot,
    benchmark_rank_fields,
    build_playlist_scenario_rank_rows,
    format_playlist_scenario_rank_row,
)
from source.kovaaks.scenario_groups import ScenarioGroup
from source.kovaaks.time_scored_service import PaceBasis

# A table build's snapshot of a store with no runs.
NO_TYPICAL = TypicalSnapshot(datetime(2026, 10, 22, 12, 0, 0), {})


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
        "leaderboard_id": "N/A",
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
        "pb_score_display": "3,180",
        "pb_score_sort": 3180,
        "pb_timestamp_sort": datetime(2026, 4, 28, 21, 30, 0).timestamp(),
        "pb_cm360_display": "45",
        "pb_cm360_sort": 45,
        "pb_accuracy_display": "67.00%",
        "pb_accuracy_sort": 67.0,
    }


def test_format_playlist_scenario_rank_row_shows_the_leaderboard_id_as_bare_digits():
    rank_info = ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN)

    mapped = format_playlist_scenario_rank_row(
        "Smoothsphere Viscose", 0, rank_info, leaderboard_id=184106
    )
    unmapped = format_playlist_scenario_rank_row("Unresolved", 0, rank_info)

    # The number gets pasted into a request, so it takes no thousands
    # separator, unlike every count beside it.
    assert mapped["leaderboard_id"] == "184106"
    assert unmapped["leaderboard_id"] == "N/A"


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
    assert row["pb_score_display"] == "N/A"
    assert row["pb_score_sort"] is None
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
    assert row["pb_score_display"] == "863.93"
    assert row["pb_score_sort"] == 863.935
    assert row["pb_timestamp_sort"] is None
    assert row["pb_cm360_display"] == "N/A"
    assert row["pb_cm360_sort"] is None
    assert row["pb_accuracy_display"] == "N/A"
    assert row["pb_accuracy_sort"] is None


@pytest.mark.parametrize(
    ("accuracy", "shown"),
    [
        # The maintainer's VoxTS Click Medium PB: 107 hits of 130 shots, which
        # KovaaK's shows as 82.31 where its damage figure is 41.15%.
        (107 / 130, "82.31%"),
        # A half rounds up, as on Run History, where a ``.2f`` format reads
        # 7.12%.
        (57 / 800, "7.13%"),
    ],
)
def test_pb_accuracy_is_the_hit_accuracy_as_run_history_shows_it(accuracy, shown):
    rank_info = ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN)
    personal_best_run = RunData(
        datetime_object=datetime(2026, 10, 16, 19, 30, 30),
        score=107,
        sens_scale="cm/360",
        horizontal_sens=50,
        scenario="VoxTS Click Medium",
        accuracy=accuracy,
    )

    row = format_playlist_scenario_rank_row(
        "VoxTS Click Medium", 0, rank_info, personal_best_run=personal_best_run
    )

    assert row["pb_accuracy_display"] == shown
    assert row["pb_accuracy_sort"] == pytest.approx(accuracy * 100)


def test_format_playlist_scenario_rank_row_shows_no_cm360_for_a_game_scale_pb():
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
        ),
        "Third": RunData(
            datetime_object=datetime(2026, 4, 3, 12, 0, 0),
            score=3000.5,
            sens_scale="cm/360",
            horizontal_sens=45,
            scenario="Third",
            accuracy=0.72,
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

    rows = build_playlist_scenario_rank_rows(
        "KovaaKsTestCode", "generation-1", typical=NO_TYPICAL
    )

    assert {row["scenario"] for row in rows} == {"First", "Second", "Third"}
    assert set(seen) == {"First", "Second", "Third"}
    assert [row["scenario"] for row in rows] == ["First", "Second", "Third"]
    assert rows[0]["position_display"] == "10"
    assert rows[1]["position_display"] == "N/A"
    assert rows[1]["status"] == "UNKNOWN"
    assert rows[1]["runs_display"] == "0"
    assert rows[1]["pb_score_display"] == "N/A"
    assert rows[1]["pb_cm360_display"] == "N/A"
    assert rows[1]["pb_accuracy_display"] == "N/A"
    assert rows[2]["position_display"] == "30"
    assert rows[2]["runs_display"] == "30"
    assert rows[2]["pb_score_display"] == "3,000.5"
    assert rows[2]["pb_cm360_display"] == "45"
    assert rows[2]["pb_accuracy_display"] == "72.00%"
    assert all(row["generation_token"] == "generation-1" for row in rows)


def test_build_playlist_scenario_rank_rows_returns_empty_for_unknown_playlist():
    rows = build_playlist_scenario_rank_rows(
        "MissingCode", "generation-1", typical=NO_TYPICAL
    )

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
    rows = build_playlist_scenario_rank_rows(
        "KovaaKsTestCode", "generation-1", typical=NO_TYPICAL
    )

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
    rows = build_playlist_scenario_rank_rows(
        "KovaaKsTestCode", "generation-1", typical=NO_TYPICAL
    )

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
    rows = build_playlist_scenario_rank_rows(
        "KovaaKsTestCode", "generation-1", typical=NO_TYPICAL
    )

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
        scenario_groups=(None,),
        typical=NO_TYPICAL,
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
        scenario_groups=(None, None, None),
        typical=NO_TYPICAL,
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
    scenario_groups = (None, None)
    state = playlist_scenarios_service._FillState(
        playlist_code="KovaaKsTestCode",
        scenario_names=scenario_names,
        scenario_ladders=scenario_ladders,
        scenario_groups=scenario_groups,
        typical=NO_TYPICAL,
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
            scenario_groups,
            NO_TYPICAL,
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
                scenario_groups=(),
                typical=NO_TYPICAL,
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
        typical=NO_TYPICAL,
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
        typical=NO_TYPICAL,
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


_VISCOSE_LADDER = [
    Rank(name="Cerulean", color="#ffffff", threshold=892.5),
    Rank(name="Lavender", color="#ffffff", threshold=899),
]


def test_a_time_scored_rows_next_rank_gap_is_a_pace_gap():
    fields = benchmark_rank_fields(_VISCOSE_LADDER, 896.2, 1000.0)

    assert fields == {
        "tier_display": "Cerulean",
        "tier_sort": 1,
        "next_tier_display": "+2.8% faster to Lavender",
        # The sort key is the unrounded pace gap, so a pace row and a score
        # row sort together in the one column.
        "next_tier_sort": pytest.approx(2.7723, abs=1e-4),
        # The tooltip stays in points, and stays true.
        "next_tier_tooltip": "Lavender at 899 · 2.8 to go",
    }


def test_the_same_row_without_a_constant_keeps_the_gap_as_a_share_of_the_pb():
    fields = benchmark_rank_fields(_VISCOSE_LADDER, 896.2)

    assert fields["next_tier_display"] == "+0.4% to Lavender"
    assert fields["next_tier_sort"] == (899 - 896.2) / 896.2 * 100
    assert fields["next_tier_tooltip"] == "Lavender at 899 · 2.8 to go"
    assert fields == benchmark_rank_fields(_VISCOSE_LADDER, 896.2, None)


@pytest.mark.parametrize(
    ("threshold", "pb", "next_tier_display"),
    [
        # 33.33% rounds up, so a gap that remains never reads as smaller.
        pytest.param(999.25, 999, "+33.4% faster to Iron", id="rounds-up"),
        pytest.param(900, 899.9999, "+0.1% faster to Iron", id="floor"),
        pytest.param(999.9, 0, "+999,900.0% faster to Iron", id="thousands"),
    ],
)
def test_a_pace_gap_formats_and_rounds_as_a_score_gap_does(
    threshold, pb, next_tier_display
):
    fields = benchmark_rank_fields(_ladder(threshold), pb, 1000.0)

    assert fields["next_tier_display"] == next_tier_display
    assert fields["next_tier_sort"] > 0


@pytest.mark.parametrize("pb", [0, -5])
def test_a_time_scored_pb_of_zero_or_less_still_has_a_pace_gap(pb):
    """Only the times have to be positive, so the row no longer reads N/A."""
    assert benchmark_rank_fields(_ladder(100), pb)["next_tier_display"] == "N/A"

    fields = benchmark_rank_fields(_ladder(100), pb, 1000.0)

    assert fields["tier_display"] == "No rank"
    assert fields["next_tier_display"].endswith("% faster to Iron")
    assert fields["next_tier_sort"] == pytest.approx(
        ((1000 - pb) / 900 - 1) * 100, rel=1e-9
    )
    assert fields["next_tier_tooltip"] == f"Iron at 100 · {100 - pb} to go"


@pytest.mark.parametrize(
    ("threshold", "pb", "next_tier_display"),
    [
        # A rank at the constant itself would take a time of zero.
        pytest.param(1000, 999, "+0.2% to Iron", id="threshold-at-the-constant"),
        pytest.param(1002, 1001, "+0.1% to Iron", id="pb-above-the-constant"),
    ],
)
def test_an_undefined_pace_gap_falls_back_to_the_share_of_the_pb(
    threshold, pb, next_tier_display
):
    fields = benchmark_rank_fields(_ladder(threshold), pb, 1000.0)

    assert fields["next_tier_display"] == next_tier_display
    assert fields == benchmark_rank_fields(_ladder(threshold), pb)


def test_an_undefined_pace_gap_on_a_pb_of_zero_reads_na_as_it_does_today():
    fields = benchmark_rank_fields(_ladder(1000), 0, 1000.0)

    assert fields["tier_display"] == "No rank"
    assert fields["next_tier_display"] == "N/A"
    assert fields["next_tier_sort"] is None
    assert fields["next_tier_tooltip"] is None


def test_the_rank_column_is_the_same_with_and_without_a_constant():
    """A higher score is always a faster finish, so the walk needs no pace."""
    ladder = _ladder(880, 892.5, 899, 905)

    for pb in (-5, 0, 879.99, 880, 896.2, 899, 904.99, 905, 990):
        by_score = benchmark_rank_fields(ladder, pb)
        by_pace = benchmark_rank_fields(ladder, pb, 1000.0)
        assert by_pace["tier_display"] == by_score["tier_display"]
        assert by_pace["tier_sort"] == by_score["tier_sort"]

    assert benchmark_rank_fields(ladder, 990, 1000.0)["next_tier_display"] == (
        "Top rank"
    )
    assert benchmark_rank_fields(ladder, None, 1000.0)["next_tier_display"] == "N/A"
    assert benchmark_rank_fields([], 896.2, 1000.0)["next_tier_display"] == "N/A"


_CONTROLSPHERE_LADDER = [
    Rank(name="Cerulean", color="#4fc3f7", threshold=3500),
    Rank(name="Lavender", color="#b39ddb", threshold=3700),
]


@pytest.mark.parametrize(
    ("ladder", "pb", "pace_constant", "parts"),
    [
        pytest.param(
            _CONTROLSPHERE_LADDER,
            3653,
            None,
            ("Cerulean", "Lavender", "+1.3%", "3,700", "47"),
            id="by-score",
        ),
        pytest.param(
            _VISCOSE_LADDER,
            896.2,
            1000.0,
            ("Cerulean", "Lavender", "+2.8% faster", "899", "2.8"),
            id="by-pace",
        ),
        pytest.param(
            _CONTROLSPHERE_LADDER,
            3400,
            None,
            (None, "Cerulean", "+3.0%", "3,500", "100"),
            id="below-the-first-rank",
        ),
    ],
)
def test_ladder_standing_gives_the_parts_the_next_rank_cell_is_made_of(
    ladder, pb, pace_constant, parts
):
    """The PB card reads these parts, so they must be the cell's own figures."""
    standing = playlist_scenarios_service.ladder_standing(ladder, pb, pace_constant)
    fields = benchmark_rank_fields(ladder, pb, pace_constant)

    reached, next_name, gap_text, threshold_text, points_text = parts
    next_gap = standing.next_gap
    assert (standing.reached.name if standing.reached else None) == reached
    assert standing.at_top is False
    assert (
        next_gap.rank.name,
        next_gap.gap_text,
        next_gap.threshold_text,
        next_gap.points_text,
    ) == (next_name, gap_text, threshold_text, points_text)
    assert fields["next_tier_display"] == f"{gap_text} to {next_name}"
    assert fields["next_tier_tooltip"] == (
        f"{next_name} at {threshold_text} · {points_text} to go"
    )
    assert fields["next_tier_sort"] == next_gap.gap


def test_ladder_standing_at_the_top_and_where_the_cell_reads_na():
    ladder = _ladder(100, 200)

    top = playlist_scenarios_service.ladder_standing(ladder, 250)
    assert (top.passed, top.reached.name, top.at_top, top.next_gap) == (
        2,
        "Bronze",
        True,
        None,
    )
    # A PB of zero compared by score has no gap, and the cell reads N/A.
    no_gap = playlist_scenarios_service.ladder_standing(ladder, 0)
    assert (no_gap.passed, no_gap.reached, no_gap.at_top, no_gap.next_gap) == (
        0,
        None,
        False,
        None,
    )
    assert playlist_scenarios_service.ladder_standing(ladder, None) is None
    assert playlist_scenarios_service.ladder_standing([], 150) is None


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
# The name-to-ID mapping the row paths read. "Unplayed" and "No Ladder" are
# scenarios the app hasn't resolved.
_LEADERBOARD_IDS = {"Ranked": 184106, "Top": 97841}
# The benchmark's groups, one per scenario. The playlist has none. "Micro"
# ends one category and begins the next, as two real benchmarks have it.
_BENCHMARK_GROUPS = (
    ScenarioGroup("Clicking", "#111111", 0, "Static", "#aaaaaa", 0),
    ScenarioGroup("Clicking", "#111111", 0, "Micro", "#bbbbbb", 1),
    ScenarioGroup("Tracking", "#222222", 1, "Micro", "#bbbbbb", 2),
    ScenarioGroup("Tracking", "#222222", 1, "Reactive", None, 3),
)
GROUP_FIELDS = (
    "category_name",
    "category_color",
    "category_run",
    "subcategory_name",
    "subcategory_color",
    "subcategory_run",
)


@pytest.fixture
def rank_row_sources(monkeypatch):
    """Serve both test playlists and the same local stats to every row path."""
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_cached_leaderboard_id",
        _LEADERBOARD_IDS.get,
    )
    monkeypatch.setattr(
        data_service,
        "playlist_database",
        {playlist.code: playlist for playlist in (_BENCHMARK, _PLAYLIST)},
    )
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_scenario_groups",
        {_BENCHMARK.code: _BENCHMARK_GROUPS}.get,
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
    benchmark_rows = build_playlist_scenario_rank_rows(
        _BENCHMARK.code, "generation-1", typical=NO_TYPICAL
    )
    playlist_rows = build_playlist_scenario_rank_rows(
        _PLAYLIST.code, "generation-1", typical=NO_TYPICAL
    )

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


def test_phase_one_rows_carry_group_fields_only_on_a_grouped_benchmark(
    rank_row_sources,
):
    benchmark_rows = build_playlist_scenario_rank_rows(
        _BENCHMARK.code, "generation-1", typical=NO_TYPICAL
    )
    playlist_rows = build_playlist_scenario_rank_rows(
        _PLAYLIST.code, "generation-1", typical=NO_TYPICAL
    )

    assert [tuple(row[field] for field in GROUP_FIELDS) for row in benchmark_rows] == [
        ("Clicking", "#111111", 0, "Static", "#aaaaaa", 0),
        ("Clicking", "#111111", 0, "Micro", "#bbbbbb", 1),
        ("Tracking", "#222222", 1, "Micro", "#bbbbbb", 2),
        ("Tracking", "#222222", 1, "Reactive", None, 3),
    ]
    # Two neighboring groups with one name stay two groups: the grid merges
    # cells on the run, which is the cell's value.
    assert (
        benchmark_rows[1]["subcategory_name"] == benchmark_rows[2]["subcategory_name"]
    )
    assert benchmark_rows[1]["subcategory_run"] != benchmark_rows[2]["subcategory_run"]
    assert all(not set(GROUP_FIELDS) & set(row) for row in playlist_rows)


def test_a_benchmark_without_groups_carries_no_group_fields(
    monkeypatch, rank_row_sources
):
    monkeypatch.setattr(
        playlist_scenarios_service, "get_scenario_groups", lambda _code: None
    )

    rows = build_playlist_scenario_rank_rows(
        _BENCHMARK.code, "generation-1", typical=NO_TYPICAL
    )

    assert all(not set(GROUP_FIELDS) & set(row) for row in rows)
    assert all(set(RANK_FIELDS) <= set(row) for row in rows)


def test_groups_of_another_length_are_dropped_and_never_shifted(
    monkeypatch, rank_row_sources
):
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_scenario_groups",
        lambda _code: _BENCHMARK_GROUPS[:-1],
    )

    rows = build_playlist_scenario_rank_rows(
        _BENCHMARK.code, "generation-1", typical=NO_TYPICAL
    )

    assert len(rows) == len(_BENCHMARK.scenarios)
    assert all(not set(GROUP_FIELDS) & set(row) for row in rows)


def _register_fill(monkeypatch, playlist_code, generation_token, typical=NO_TYPICAL):
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
            playlist_code, generation_token, typical=typical
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
    phase_one = build_playlist_scenario_rank_rows(
        playlist.code, "generation-1", typical=NO_TYPICAL
    )
    target, args = _register_fill(monkeypatch, playlist.code, "generation-1")

    target(*args)
    drain = playlist_scenarios_service.drain_playlist_scenario_fill("generation-1")

    assert drain is not None
    assert drain.terminal == "complete"
    assert sorted(drain.updates, key=lambda row: row["playlist_order"]) == phase_one
    # The equality above is only as strong as phase 1: say outright that a
    # streamed row of a grouped benchmark holds its group.
    assert all(
        (set(GROUP_FIELDS) <= set(row)) == (playlist is _BENCHMARK)
        for row in drain.updates
    )


@pytest.mark.parametrize(
    "playlist", [_BENCHMARK, _PLAYLIST], ids=["benchmark", "playlist"]
)
def test_cancelled_fill_rebuild_rows_equal_phase_one_rows(
    monkeypatch,
    rank_row_sources,
    isolated_fill_registry,
    playlist,
):
    phase_one = build_playlist_scenario_rank_rows(
        playlist.code, "generation-1", typical=NO_TYPICAL
    )
    _register_fill(monkeypatch, playlist.code, "generation-1")
    # Opening any playlist in another tab cancels this fill before it fetches.
    _register_fill(monkeypatch, _PLAYLIST.code, "generation-2")

    drain = playlist_scenarios_service.drain_playlist_scenario_fill("generation-1")

    assert drain is not None
    assert drain.terminal == "cancelled"
    assert drain.consuming_terminal is True
    assert drain.updates == phase_one
    assert all(
        (set(GROUP_FIELDS) <= set(row)) == (playlist is _BENCHMARK)
        for row in drain.updates
    )
    with playlist_scenarios_service._FILL_REGISTRY_LOCK:
        state = playlist_scenarios_service._FILL_REGISTRY["generation-1"]
        assert state.scenario_names == ()
        assert state.scenario_ladders == ()
        assert state.scenario_groups == ()


# --- every row path carries the scenario's leaderboard ID ---


def _leaderboard_ids_by_scenario(rows) -> dict[str, str]:
    return {row["scenario"]: row["leaderboard_id"] for row in rows}


def test_every_row_path_carries_the_leaderboard_id(
    monkeypatch,
    rank_row_sources,
    isolated_fill_registry,
):
    expected = {
        "Ranked": "184106",
        "Unplayed": "N/A",
        "No Ladder": "N/A",
        "Top": "97841",
    }

    phase_one = build_playlist_scenario_rank_rows(
        _BENCHMARK.code, "generation-1", typical=NO_TYPICAL
    )
    target, args = _register_fill(monkeypatch, _BENCHMARK.code, "generation-1")
    target(*args)
    streamed = playlist_scenarios_service.drain_playlist_scenario_fill("generation-1")
    _register_fill(monkeypatch, _BENCHMARK.code, "generation-2")
    # Opening any playlist in another tab cancels that fill before it fetches.
    _register_fill(monkeypatch, _PLAYLIST.code, "generation-3")
    rebuilt = playlist_scenarios_service.drain_playlist_scenario_fill("generation-2")

    assert streamed is not None
    assert streamed.terminal == "complete"
    assert rebuilt is not None
    assert rebuilt.terminal == "cancelled"
    # The last two replace a row's data whole, so a path that dropped the field
    # would blank the cell.
    for rows in (phase_one, streamed.updates, rebuilt.updates):
        assert _leaderboard_ids_by_scenario(rows) == expected


def test_a_streamed_row_carries_the_leaderboard_id_its_lookup_learned(
    monkeypatch,
    rank_row_sources,
    isolated_fill_registry,
):
    learned: dict[str, int] = {}
    monkeypatch.setattr(
        playlist_scenarios_service, "get_cached_leaderboard_id", learned.get
    )

    def lookup(scenario_name, *, allow_network):
        # Only the fill may reach KovaaK's, which is where an ID is learned.
        if allow_network:
            learned[scenario_name] = 184106
        return ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=10,
            total_players=100,
            percentile=90.0,
        )

    monkeypatch.setattr(playlist_scenarios_service, "_lookup_rank_info", lookup)

    phase_one = build_playlist_scenario_rank_rows(
        _PLAYLIST.code, "generation-1", typical=NO_TYPICAL
    )
    target, args = _register_fill(monkeypatch, _PLAYLIST.code, "generation-1")
    target(*args)
    streamed = playlist_scenarios_service.drain_playlist_scenario_fill("generation-1")

    assert streamed is not None
    assert set(_leaderboard_ids_by_scenario(phase_one).values()) == {"N/A"}
    assert set(_leaderboard_ids_by_scenario(streamed.updates).values()) == {"184106"}


def test_a_failed_mapping_read_still_builds_the_row(
    monkeypatch, rank_row_sources, caplog
):
    def raise_on_read(_scenario_name):
        raise ValueError("unreadable mapping")

    monkeypatch.setattr(
        playlist_scenarios_service, "get_cached_leaderboard_id", raise_on_read
    )

    with caplog.at_level(logging.WARNING, logger=playlist_scenarios_service.__name__):
        rows = build_playlist_scenario_rank_rows(
            _PLAYLIST.code, "generation-1", typical=NO_TYPICAL
        )

    assert _leaderboard_ids_by_scenario(rows) == {"Ranked": "N/A", "Unplayed": "N/A"}
    assert 'Failed to read the leaderboard ID for "Ranked"' in caplog.messages


# --- Time-scored rows on the three row paths --------------------------------

_PACE_HASH = "0123456789abcdef0123456789abcdef"


def _pb_run(scenario_hash: str | None) -> RunData:
    return RunData(
        datetime_object=datetime(2026, 4, 1, 12, 0, 0),
        score=105,
        sens_scale="cm/360",
        horizontal_sens=40.0,
        scenario="Ranked",
        accuracy=0.5,
        scenario_hash=scenario_hash,
    )


def _serve_pace(monkeypatch, *, pb_hash: str | None = _PACE_HASH):
    """Recognize every scenario as time-scored, with one PB run for "Ranked"."""
    asked = []

    def get_pace_basis(scenario_name):
        asked.append(scenario_name)
        return PaceBasis(1000.0, _PACE_HASH)

    monkeypatch.setattr(playlist_scenarios_service, "get_pace_basis", get_pace_basis)
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_personal_best_run",
        lambda scenario_name: _pb_run(pb_hash) if scenario_name == "Ranked" else None,
    )
    return asked


def _next_ranks(rows) -> list[tuple[str, str]]:
    return [(row["scenario"], row["next_tier_display"]) for row in rows]


# 105 against Bronze at 110, at a constant of 1,000: 895 s against 890 s.
_PACE_NEXT_RANKS = [
    ("Ranked", "+0.6% faster to Bronze"),
    ("Unplayed", "N/A"),
    ("No Ladder", "N/A"),
    ("Top", "Top rank"),
]


def test_phase_one_rows_measure_a_time_scored_scenario_by_pace(
    monkeypatch, rank_row_sources
):
    asked = _serve_pace(monkeypatch)

    rows = build_playlist_scenario_rank_rows(
        _BENCHMARK.code, "generation-1", typical=NO_TYPICAL
    )

    assert _next_ranks(rows) == _PACE_NEXT_RANKS
    assert rows[0]["next_tier_sort"] == pytest.approx((895 / 890 - 1) * 100)
    assert rows[0]["tier_display"] == "Iron"
    # A row with no ladder or no PB shows no gap, so nothing asks about it.
    assert asked == ["Ranked"]


def test_fill_rows_carry_the_same_pace_gap_as_phase_one(
    monkeypatch, rank_row_sources, isolated_fill_registry
):
    _serve_pace(monkeypatch)
    phase_one = build_playlist_scenario_rank_rows(
        _BENCHMARK.code, "generation-1", typical=NO_TYPICAL
    )
    target, args = _register_fill(monkeypatch, _BENCHMARK.code, "generation-1")

    target(*args)
    drain = playlist_scenarios_service.drain_playlist_scenario_fill("generation-1")

    assert drain is not None
    assert drain.terminal == "complete"
    fill_rows = sorted(drain.updates, key=lambda row: row["playlist_order"])
    assert _next_ranks(fill_rows) == _PACE_NEXT_RANKS
    assert fill_rows == phase_one


def test_a_cancelled_fills_rebuild_carries_the_same_pace_gap_as_phase_one(
    monkeypatch, rank_row_sources, isolated_fill_registry
):
    _serve_pace(monkeypatch)
    phase_one = build_playlist_scenario_rank_rows(
        _BENCHMARK.code, "generation-1", typical=NO_TYPICAL
    )
    _register_fill(monkeypatch, _BENCHMARK.code, "generation-1")
    _register_fill(monkeypatch, _PLAYLIST.code, "generation-2")

    drain = playlist_scenarios_service.drain_playlist_scenario_fill("generation-1")

    assert drain is not None
    assert drain.terminal == "cancelled"
    assert _next_ranks(drain.updates) == _PACE_NEXT_RANKS
    assert drain.updates == phase_one


@pytest.mark.parametrize("pb_hash", ["ffffffffffffffffffffffffffffffff", None])
def test_a_pb_from_another_version_keeps_the_gap_as_a_share_of_the_pb(
    monkeypatch, rank_row_sources, pb_hash
):
    """The constant was read from one version, and the PB is not of it."""
    _serve_pace(monkeypatch, pb_hash=pb_hash)

    rows = build_playlist_scenario_rank_rows(
        _BENCHMARK.code, "generation-1", typical=NO_TYPICAL
    )

    assert _next_ranks(rows)[0] == ("Ranked", "+4.8% to Bronze")


def test_a_playlists_table_never_asks_whether_a_scenario_is_time_scored(
    monkeypatch, rank_row_sources
):
    asked = _serve_pace(monkeypatch)

    rows = build_playlist_scenario_rank_rows(
        _PLAYLIST.code, "generation-1", typical=NO_TYPICAL
    )

    assert len(rows) == 2
    assert asked == []


def test_a_failed_pace_lookup_costs_the_pace_gap_and_never_the_row(
    monkeypatch, rank_row_sources, caplog
):
    _serve_pace(monkeypatch)

    def fail(_scenario_name):
        raise RuntimeError("the run list changed size during iteration")

    monkeypatch.setattr(playlist_scenarios_service, "get_pace_basis", fail)

    with caplog.at_level(logging.WARNING, logger=playlist_scenarios_service.__name__):
        rows = build_playlist_scenario_rank_rows(
            _BENCHMARK.code, "generation-1", typical=NO_TYPICAL
        )

    assert _next_ranks(rows)[0] == ("Ranked", "+4.8% to Bronze")
    failures = [
        record
        for record in caplog.records
        if record.getMessage() == 'Failed to tell whether "Ranked" is time-scored'
    ]
    assert len(failures) == 1
    assert failures[0].exc_info is not None


# --- the typical score's two columns ---

TYPICAL_MOMENT = datetime(2026, 10, 22, 12, 0, 0)
# Iron, Bronze, Silver and Gold.
FOUR_RANKS = _ladder(400, 500, 600, 700)


class _FrozenClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return TYPICAL_MOMENT


def _typical_run(
    end: datetime,
    score: float,
    scenario: str = "Ranked",
    scenario_hash: str | None = None,
) -> RunData:
    return RunData(
        datetime_object=end,
        score=score,
        scenario=scenario,
        sens_scale="cm/360",
        horizontal_sens=40.0,
        accuracy=0.5,
        run_start=end - timedelta(seconds=60),
        run_length=timedelta(seconds=60),
        scenario_hash=scenario_hash,
    )


def _daily_runs(scores, *, last: datetime, scenario: str = "Ranked") -> list[RunData]:
    """One run a day, each its own session, the newest ending at ``last``."""
    scores = list(scores)
    return [
        _typical_run(last - timedelta(days=len(scores) - 1 - index), score, scenario)
        for index, score in enumerate(scores)
    ]


def _typical(monkeypatch, runs, names=("Ranked",)):
    """Take a table build's snapshot of ``runs`` at ``TYPICAL_MOMENT``."""
    store = sorted(runs, key=lambda run: run.datetime_object)
    monkeypatch.setattr(playlist_scenarios_service, "get_all_runs", lambda: list(store))
    monkeypatch.setattr(playlist_scenarios_service, "datetime", _FrozenClock)
    return playlist_scenarios_service.take_typical_snapshot(names)


@pytest.mark.parametrize(
    ("score", "display", "position"),
    [
        (500, "Bronze · 0%", 2.0),
        (500.5, "Bronze · 0%", 2.005),
        (540, "Bronze · 40%", 2.4),
        (599.999, "Bronze · 99%", 2.99999),
        (700, "Gold", 4.0),
        (750, "Gold", 4.0),
    ],
)
def test_typical_rank_reads_the_rank_and_how_far_toward_the_next(
    score, display, position
):
    fields = playlist_scenarios_service.typical_tier_fields(FOUR_RANKS, score)

    assert fields["typical_tier_display"] == display
    # The sort key is unrounded, so two rows that both read 0% still order.
    assert fields["typical_tier_sort"] == pytest.approx(position)


def test_typical_rank_hover_is_the_gap_and_an_old_values_line():
    recent = playlist_scenarios_service.typical_tier_fields(FOUR_RANKS, 540)
    old = playlist_scenarios_service.typical_tier_fields(
        FOUR_RANKS, 540, not_recent=True
    )

    assert recent["typical_tier_hover"] == "+11.2% to Silver · 60 to go"
    assert old["typical_tier_hover"] == (
        "+11.2% to Silver · 60 to go\n"
        "Fewer than 10 of the typical score's runs are from the last 30 days, "
        "so it may be out of date."
    )


def test_typical_rank_at_the_top_has_a_hover_only_when_old():
    recent = playlist_scenarios_service.typical_tier_fields(FOUR_RANKS, 750)
    old = playlist_scenarios_service.typical_tier_fields(
        FOUR_RANKS, 750, not_recent=True
    )

    assert recent["typical_tier_hover"] is None
    assert old["typical_tier_hover"] == playlist_scenarios_service.TYPICAL_RANK_OLD_LINE


@pytest.mark.parametrize(
    ("thresholds", "score", "display", "position"),
    [
        # A tie: the walk passes both equal thresholds.
        ((400, 500, 500, 600), 550, "Silver · 50%", 3.5),
        # A dip: the walk stops at the first threshold above the score.
        ((400, 600, 500, 700), 550, "Iron · 75%", 1.75),
    ],
    ids=["tie", "dip"],
)
def test_typical_rank_on_a_ladder_that_ties_or_dips(
    thresholds, score, display, position
):
    fields = playlist_scenarios_service.typical_tier_fields(_ladder(*thresholds), score)

    assert fields["typical_tier_display"] == display
    assert fields["typical_tier_sort"] == pytest.approx(position)


@pytest.mark.parametrize(
    "thresholds",
    [(400, 500, 600), (400, 500, 500, 600), (400, 600, 500, 700), (500, 500, 500)],
)
def test_the_fraction_toward_the_next_rank_is_never_a_whole_rank(thresholds):
    ladder = _ladder(*thresholds)
    for score in [quarter / 4 for quarter in range(1600, 2900)]:
        standing = playlist_scenarios_service.ladder_standing(ladder, score)
        assert standing is not None
        position = playlist_scenarios_service.rank_position(ladder, score, standing)
        if standing.at_top:
            assert position == len(ladder)
        elif standing.passed:
            assert standing.passed <= position < standing.passed + 1


def test_the_percent_never_reads_as_the_next_rank():
    ladder = _ladder(1000, 10000, 20000)

    under = playlist_scenarios_service.typical_tier_fields(ladder, 9999.999999)
    at = playlist_scenarios_service.typical_tier_fields(ladder, 10000)

    # The noise-stripping round alone would carry this to 100%.
    assert under["typical_tier_display"] == "Iron · 99%"
    assert under["typical_tier_sort"] < 2
    assert at["typical_tier_display"] == "Bronze · 0%"
    assert at["typical_tier_sort"] == 2.0


@pytest.mark.parametrize("constant", [1000.0, 200.0])
def test_below_the_first_rank_a_pace_row_sorts_by_time_whatever_its_constant(
    constant,
):
    # A 120-second typical run against a 100-second first rank, and an
    # ordinary row at 90 against 100.
    pace = playlist_scenarios_service.typical_tier_fields(
        _ladder(constant - 100, constant), constant - 120, constant
    )
    ordinary = playlist_scenarios_service.typical_tier_fields(_ladder(100, 200), 90)

    assert pace["typical_tier_display"] == "No rank"
    assert pace["typical_tier_sort"] == pytest.approx(1 / 1.2)
    assert ordinary["typical_tier_display"] == "No rank"
    assert ordinary["typical_tier_sort"] == pytest.approx(0.9)
    # A ratio of scores would put the pace row above the ordinary one at a
    # constant of 1,000 and below it at 200.
    assert pace["typical_tier_sort"] < ordinary["typical_tier_sort"]
    assert pace["typical_tier_hover"] == "+20.0% faster to Iron · 20 to go"


@pytest.mark.parametrize("score", [0, -5])
def test_below_the_first_rank_with_no_gap_keys_zero(score):
    fields = playlist_scenarios_service.typical_tier_fields(_ladder(100, 200), score)

    assert fields["typical_tier_display"] == "No rank"
    assert fields["typical_tier_sort"] == 0.0
    assert fields["typical_tier_hover"] is None


def test_every_below_first_row_sorts_under_every_ranked_row():
    ladder = _ladder(100, 200)
    below = playlist_scenarios_service.typical_tier_fields(ladder, 99.999)
    on_the_first = playlist_scenarios_service.typical_tier_fields(ladder, 100)

    assert below["typical_tier_sort"] < 1 <= on_the_first["typical_tier_sort"]


def test_a_known_recent_value_fills_both_typical_cells(monkeypatch):
    runs = _daily_runs(range(500, 520), last=TYPICAL_MOMENT - timedelta(hours=1))

    fields = playlist_scenarios_service.typical_row_fields(
        "Ranked", FOUR_RANKS, _typical(monkeypatch, runs)
    )

    assert fields == {
        "typical_score_display": "510",
        "typical_score_sort": 509.5,
        "typical_not_recent": False,
        "typical_score_hover": {
            "lead": "The median of your 20 runs.",
            "lines": [
                ["Runs:", " 20 in 20 sessions · Oct 3 to Oct 22"],
                ["Recent:", " 20 of 20 from the last 30 days"],
                ["Middle 50%:", " 505 to 514"],
                ["Middle 80%:", " 502 to 517"],
            ],
        },
        "typical_tier_display": "Bronze · 9%",
        "typical_tier_sort": pytest.approx(2.095),
        "typical_tier_hover": "+17.8% to Silver · 90.5 to go",
    }


def test_a_value_from_the_last_of_more_runs_says_so(monkeypatch):
    runs = _daily_runs(range(500, 525), last=TYPICAL_MOMENT - timedelta(hours=1))

    fields = playlist_scenarios_service.typical_row_fields(
        "Ranked", None, _typical(monkeypatch, runs)
    )

    assert fields["typical_score_hover"]["lead"] == "The median of your last 20 runs."


def test_an_old_value_is_marked_and_its_hovers_say_why(monkeypatch):
    runs = _daily_runs(range(500, 520), last=TYPICAL_MOMENT - timedelta(days=40))

    fields = playlist_scenarios_service.typical_row_fields(
        "Ranked", FOUR_RANKS, _typical(monkeypatch, runs)
    )

    assert fields["typical_not_recent"] is True
    assert fields["typical_score_display"] == "510"
    assert fields["typical_score_hover"]["lead"] == (
        "The median of your 20 runs. Fewer than 10 of them are from the last 30 "
        "days, so it may be out of date."
    )
    assert fields["typical_score_hover"]["lines"][1] == [
        "Recent:",
        " 0 of 20 from the last 30 days",
    ]
    # An old value still has its rank, and sorts with the others.
    assert fields["typical_tier_display"] == "Bronze · 9%"
    assert fields["typical_tier_hover"].splitlines() == [
        "+17.8% to Silver · 90.5 to go",
        playlist_scenarios_service.TYPICAL_RANK_OLD_LINE,
    ]


def test_runs_dated_after_the_build_never_make_a_value_recent(monkeypatch):
    # 10 runs in the last 30 days and 11 dated after the build's moment, as
    # after a system clock correction. The window is the newest 20: 9 recent
    # and the 11 later ones.
    earlier = _daily_runs(range(500, 510), last=TYPICAL_MOMENT - timedelta(hours=1))
    later = [
        _typical_run(TYPICAL_MOMENT + timedelta(days=day), 510 + day)
        for day in range(1, 12)
    ]

    fields = playlist_scenarios_service.typical_row_fields(
        "Ranked", None, _typical(monkeypatch, earlier + later)
    )

    assert fields["typical_not_recent"] is True
    # The hover counts the runs behind the value, not the scenario's 10.
    assert fields["typical_score_hover"]["lines"][1] == [
        "Recent:",
        " 9 of 20 from the last 30 days",
    ]


@pytest.mark.parametrize(
    ("days", "runs_per_day", "text"),
    [
        (1, 1, "You have 1 run in 1 session."),
        (1, 3, "You have 3 runs in 1 session."),
        (2, 4, "You have 8 runs in 2 sessions."),
    ],
)
def test_a_value_below_the_minimum_reads_too_few_runs_and_is_never_old(
    monkeypatch, days, runs_per_day, text
):
    start = TYPICAL_MOMENT - timedelta(days=60)
    runs = [
        _typical_run(start + timedelta(days=day, minutes=2 * index), 500)
        for day in range(days)
        for index in range(runs_per_day)
    ]

    fields = playlist_scenarios_service.typical_row_fields(
        "Ranked", FOUR_RANKS, _typical(monkeypatch, runs)
    )

    assert fields == {
        "typical_score_display": "Too few runs",
        "typical_score_sort": None,
        "typical_not_recent": False,
        "typical_score_hover": {
            "lead": "A typical score needs 10 runs across 2 or more sessions, "
            f"or 20 in one session. {text}",
            "lines": [],
        },
        "typical_tier_display": "N/A",
        "typical_tier_sort": None,
        "typical_tier_hover": None,
    }


def test_a_scenario_with_no_runs_reads_na_in_both_cells(monkeypatch):
    fields = playlist_scenarios_service.typical_row_fields(
        "Ranked", FOUR_RANKS, _typical(monkeypatch, [])
    )

    assert fields == {
        "typical_score_display": "N/A",
        "typical_score_sort": None,
        "typical_not_recent": False,
        "typical_score_hover": None,
        "typical_tier_display": "N/A",
        "typical_tier_sort": None,
        "typical_tier_hover": None,
    }


def test_a_playlists_row_carries_no_typical_rank(monkeypatch):
    runs = _daily_runs(range(500, 520), last=TYPICAL_MOMENT - timedelta(hours=1))

    fields = playlist_scenarios_service.typical_row_fields(
        "Ranked", None, _typical(monkeypatch, runs)
    )

    assert not any(key.startswith("typical_tier") for key in fields)


def test_a_benchmark_scenario_without_a_ladder_reads_na_in_typical_rank(monkeypatch):
    runs = _daily_runs(range(500, 520), last=TYPICAL_MOMENT - timedelta(days=40))

    fields = playlist_scenarios_service.typical_row_fields(
        "Ranked", [], _typical(monkeypatch, runs)
    )

    assert fields["typical_tier_display"] == "N/A"
    assert fields["typical_tier_sort"] is None
    assert fields["typical_tier_hover"] is None


@pytest.mark.parametrize(
    ("hashes", "hover"),
    [
        ((_PACE_HASH,) * 20, "+10.0% faster to Silver · 10 to go"),
        ((_PACE_HASH,) * 19 + ("another-version",), "+2.1% to Silver · 10 to go"),
    ],
    ids=["one-version", "mixed-versions"],
)
def test_typical_rank_is_measured_by_pace_only_on_one_version(
    monkeypatch, hashes, hover
):
    # A constant of 600: the typical 490 took 110 s, and Silver at 500 is 100 s.
    runs = [
        _typical_run(
            TYPICAL_MOMENT - timedelta(days=20 - index),
            490,
            scenario_hash=scenario_hash,
        )
        for index, scenario_hash in enumerate(hashes)
    ]

    fields = playlist_scenarios_service.typical_row_fields(
        "Ranked",
        _ladder(300, 400, 500),
        _typical(monkeypatch, runs),
        PaceBasis(600.0, _PACE_HASH),
    )

    assert fields["typical_tier_hover"] == hover


def test_a_snapshot_splits_sessions_from_the_whole_store(monkeypatch):
    # Two runs 49 minutes apart are one session only because another
    # scenario was played between them.
    start = TYPICAL_MOMENT - timedelta(days=1)
    runs = [
        _typical_run(start, 500),
        _typical_run(start + timedelta(minutes=25), 10, scenario="Other"),
        _typical_run(start + timedelta(minutes=50), 510),
    ]

    typical = _typical(monkeypatch, runs, names=("Ranked", "Unplayed"))

    assert typical.moment == TYPICAL_MOMENT
    assert set(typical.values) == {"Ranked"}
    value, total = typical.values["Ranked"]
    assert total == 2
    assert value.session_count == 1


def _row_path_runs():
    """Runs for two of the shared fixture's scenarios: Ranked recent, Top old."""
    return [
        *_daily_runs(range(100, 120), last=TYPICAL_MOMENT - timedelta(hours=1)),
        *_daily_runs(
            range(120, 140), last=TYPICAL_MOMENT - timedelta(days=40), scenario="Top"
        ),
    ]


def _typical_cells(rows):
    return [
        {key: value for key, value in row.items() if key.startswith("typical_")}
        for row in rows
    ]


def test_phase_one_rows_carry_the_typical_fields(monkeypatch, rank_row_sources):
    names = [scenario.name for scenario in _BENCHMARK.scenarios]
    typical = _typical(monkeypatch, _row_path_runs(), names)

    rows = build_playlist_scenario_rank_rows(
        _BENCHMARK.code, "generation-1", typical=typical
    )

    by_scenario = {row["scenario"]: row for row in rows}
    assert by_scenario["Ranked"]["typical_tier_display"] == "Iron · 95%"
    assert by_scenario["Ranked"]["typical_not_recent"] is False
    assert by_scenario["Top"]["typical_tier_display"] == "Silver"
    assert by_scenario["Top"]["typical_not_recent"] is True
    assert by_scenario["Unplayed"]["typical_score_display"] == "N/A"
    assert by_scenario["No Ladder"]["typical_tier_display"] == "N/A"


def test_fill_and_cancelled_rows_carry_phase_ones_typical_fields(
    monkeypatch, rank_row_sources, isolated_fill_registry
):
    names = [scenario.name for scenario in _BENCHMARK.scenarios]
    typical = _typical(monkeypatch, _row_path_runs(), names)
    phase_one = build_playlist_scenario_rank_rows(
        _BENCHMARK.code, "generation-1", typical=typical
    )
    # A run landing after phase 1 must not reach the fill's rows: they take
    # phase 1's snapshot, never a new one.
    monkeypatch.setattr(
        playlist_scenarios_service,
        "get_all_runs",
        lambda: pytest.fail("a fill row read the run store"),
    )
    target, args = _register_fill(monkeypatch, _BENCHMARK.code, "generation-1", typical)
    target(*args)
    _register_fill(monkeypatch, _BENCHMARK.code, "generation-2", typical)
    # Opening any playlist in another tab cancels the second fill unstarted.
    _register_fill(monkeypatch, _PLAYLIST.code, "generation-3")

    filled = playlist_scenarios_service.drain_playlist_scenario_fill("generation-1")
    cancelled = playlist_scenarios_service.drain_playlist_scenario_fill("generation-2")

    assert filled is not None
    assert filled.terminal == "complete"
    assert cancelled is not None
    assert cancelled.terminal == "cancelled"
    filled_rows = sorted(filled.updates, key=lambda row: row["playlist_order"])
    assert _typical_cells(filled_rows) == _typical_cells(phase_one)
    assert _typical_cells(cancelled.updates) == _typical_cells(phase_one)
