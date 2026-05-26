from datetime import datetime
from types import SimpleNamespace

from source.kovaaks import data_service
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from source.kovaaks.data_models import PlaylistData, RunData, Scenario, ScenarioStats
from source.kovaaks import playlist_scenarios_service
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
    monkeypatch.setattr(data_service, "playlist_database", {playlist.name: playlist})

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
        "last_played_display": "2026-04-28",
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
    assert row["last_played_display"] == "N/A"
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
    assert row["last_played_display"] == "2026-05-01"
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
    monkeypatch.setattr(data_service, "playlist_database", {playlist.name: playlist})
    monkeypatch.setattr(
        playlist_scenarios_service,
        "config",
        SimpleNamespace(
            kovaaks_username="MingoDynasty",
            steam_id="steam-id",
            scenario_metadata_cache_ttl_hours=24,
            scenario_rank_cache_ttl_hours=168,
            leaderboard_total_cache_ttl_hours=24,
        ),
    )
    seen = []

    def fake_rank_lookup(
        scenario_name,
        username,
        steam_id,
        metadata_cache_ttl_hours,
        rank_cache_ttl_hours,
        leaderboard_total_cache_ttl_hours,
    ):
        seen.append(scenario_name)
        assert username == "MingoDynasty"
        assert steam_id == "steam-id"
        assert metadata_cache_ttl_hours == 24
        assert rank_cache_ttl_hours == 168
        assert leaderboard_total_cache_ttl_hours == 24
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

    rows = build_playlist_scenario_rank_rows("KovaaKsTestCode")

    assert {row["scenario"] for row in rows} == {"First", "Second", "Third"}
    assert set(seen) == {"First", "Second", "Third"}
    assert [row["scenario"] for row in rows] == ["First", "Second", "Third"]
    assert rows[0]["rank_display"] == "10"
    assert rows[1]["rank_display"] == "N/A"
    assert rows[1]["status"] == "UNKNOWN"
    assert rows[1]["last_played_display"] == "N/A"
    assert rows[1]["runs_display"] == "0"
    assert rows[1]["high_score_display"] == "N/A"
    assert rows[1]["pb_cm360_display"] == "N/A"
    assert rows[1]["pb_accuracy_display"] == "N/A"
    assert rows[2]["rank_display"] == "30"
    assert rows[2]["last_played_display"] == "2026-04-03"
    assert rows[2]["runs_display"] == "30"
    assert rows[2]["high_score_display"] == "3,000.5"
    assert rows[2]["pb_cm360_display"] == "45"
    assert rows[2]["pb_accuracy_display"] == "82.34%"


def test_build_playlist_scenario_rank_rows_returns_empty_for_unknown_playlist():
    rows = build_playlist_scenario_rank_rows("MissingCode")

    assert rows == []
