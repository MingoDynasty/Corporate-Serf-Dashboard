from source.kovaaks import data_service
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from source.kovaaks.data_models import PlaylistData, Scenario
from source.kovaaks.playlist_scenarios_service import (
    PlaylistRankLookupConfig,
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


def test_format_playlist_scenario_rank_row_ranked():
    rank_info = ScenarioRankInfo(
        status=ScenarioRankStatus.RANKED,
        rank=11290,
        total_players=63892,
        percentile=82.33,
    )

    row = format_playlist_scenario_rank_row("VT Pasu Intermediate S5", 3, rank_info)

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


def test_format_playlist_scenario_rank_row_unknown():
    rank_info = ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN)

    row = format_playlist_scenario_rank_row("Unknown Scenario", 0, rank_info)

    assert row["rank_display"] == "N/A"
    assert row["rank_sort"] is None
    assert row["total_display"] == "N/A"
    assert row["total_sort"] is None
    assert row["percentile_display"] == "N/A"
    assert row["percentile_sort"] is None


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

    rows = build_playlist_scenario_rank_rows(
        "KovaaKsTestCode",
        PlaylistRankLookupConfig(
            username="MingoDynasty",
            steam_id="steam-id",
            scenario_metadata_cache_ttl_hours=24,
            scenario_rank_cache_ttl_hours=168,
            leaderboard_total_cache_ttl_hours=24,
            max_workers=2,
        ),
        rank_lookup=fake_rank_lookup,
    )

    assert {row["scenario"] for row in rows} == {"First", "Second", "Third"}
    assert set(seen) == {"First", "Second", "Third"}
    assert [row["scenario"] for row in rows] == ["First", "Second", "Third"]
    assert rows[0]["rank_display"] == "10"
    assert rows[1]["rank_display"] == "N/A"
    assert rows[1]["status"] == "UNKNOWN"
    assert rows[2]["rank_display"] == "30"


def test_build_playlist_scenario_rank_rows_returns_empty_for_unknown_playlist():
    rows = build_playlist_scenario_rank_rows(
        "MissingCode",
        PlaylistRankLookupConfig(
            username="MingoDynasty",
            steam_id=None,
            scenario_metadata_cache_ttl_hours=24,
            scenario_rank_cache_ttl_hours=168,
            leaderboard_total_cache_ttl_hours=24,
        ),
    )

    assert rows == []
