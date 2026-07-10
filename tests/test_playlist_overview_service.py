from datetime import datetime
from types import SimpleNamespace

from source.kovaaks import data_service, playlist_overview_service
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from source.kovaaks.data_models import PlaylistData, Rank, Scenario, ScenarioStats
from source.kovaaks.playlist_overview_service import (
    build_playlist_overview_rows,
    format_playlist_overview_row,
)

RANKS = [Rank(name="Bronze", color="#a97142", threshold=100)]


def _configure(monkeypatch):
    monkeypatch.setattr(
        playlist_overview_service,
        "get_config",
        lambda: SimpleNamespace(
            kovaaks_username="MingoDynasty",
            steam_id="steam-id",
            scenario_metadata_cache_ttl_hours=24,
            scenario_rank_cache_ttl_hours=168,
            leaderboard_total_cache_ttl_hours=24,
        ),
    )


def _install_cached_ranks(monkeypatch, rank_infos_by_scenario):
    """Serve canned cache-only rank info and enforce the zero-network seam."""

    def fake_rank_lookup(
        scenario_name,
        username,
        steam_id,
        metadata_cache_ttl_hours,
        rank_cache_ttl_hours,
        leaderboard_total_cache_ttl_hours,
        allow_network=True,
    ):
        assert allow_network is False
        assert username == "MingoDynasty"
        assert steam_id == "steam-id"
        assert metadata_cache_ttl_hours == 24
        assert rank_cache_ttl_hours == 168
        assert leaderboard_total_cache_ttl_hours == 24
        return rank_infos_by_scenario.get(
            scenario_name,
            ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN),
        )

    monkeypatch.setattr(
        playlist_overview_service,
        "get_scenario_rank_info",
        fake_rank_lookup,
    )


def _install_stats_snapshot(monkeypatch, stats_by_scenario):
    monkeypatch.setattr(
        playlist_overview_service,
        "get_scenario_stats_snapshot",
        lambda: dict(stats_by_scenario),
    )


def _install_shown_codes(monkeypatch, shown_codes):
    monkeypatch.setattr(
        playlist_overview_service,
        "get_shown_playlist_codes",
        lambda: set(shown_codes),
    )


def test_format_playlist_overview_row_aggregates_played_and_cached_scenarios(
    monkeypatch,
):
    _configure(monkeypatch)
    playlist = PlaylistData(
        name="Voltaic Benchmarks",
        code="KovaaKsTestCode",
        scenarios=[
            Scenario(name="First", ranks=RANKS),
            Scenario(name="Second", ranks=RANKS),
            Scenario(name="Third", ranks=RANKS),
        ],
    )
    stats_by_scenario = {
        "First": ScenarioStats(
            date_last_played=datetime(2026, 4, 1, 12, 0, 0),
            number_of_runs=10,
            high_score=1000,
        ),
        "Third": ScenarioStats(
            date_last_played=datetime(2026, 6, 3, 12, 0, 0),
            number_of_runs=20,
            high_score=3000,
        ),
    }
    _install_cached_ranks(
        monkeypatch,
        {
            "First": ScenarioRankInfo(
                status=ScenarioRankStatus.RANKED,
                rank=10,
                total_players=100,
                percentile=90.5,
            ),
            "Third": ScenarioRankInfo(
                status=ScenarioRankStatus.RANKED,
                rank=30,
                total_players=100,
                percentile=70.5,
            ),
        },
    )

    row = format_playlist_overview_row(
        "Voltaic Benchmarks", playlist, stats_by_scenario
    )

    assert row == {
        "name": "Voltaic Benchmarks",
        "code": "KovaaKsTestCode",
        "type_display": "Benchmark",
        "played_display": "2/3",
        "played_sort": 2 / 3,
        "runs_display": "30",
        "runs_sort": 30,
        "last_played_sort": datetime(2026, 6, 3, 12, 0, 0).timestamp(),
        "stalest_scenario": "First",
        "stalest_sort": datetime(2026, 4, 1, 12, 0, 0).timestamp(),
        "median_percentile_display": "80.50% · 2/3",
        "median_percentile_sort": 80.5,
        "lowest_percentile_display": "70.50% · 2/3",
        "lowest_percentile_sort": 70.5,
        "lowest_scenario": "Third",
    }


def test_format_playlist_overview_row_never_played(monkeypatch):
    _configure(monkeypatch)
    playlist = PlaylistData(
        name="Untouched",
        code="KovaaKsUntouched",
        scenarios=[Scenario(name="First"), Scenario(name="Second")],
    )
    _install_cached_ranks(monkeypatch, {})

    row = format_playlist_overview_row("Untouched", playlist, {})

    assert row["type_display"] == "Playlist"
    assert row["played_display"] == "0/2"
    assert row["played_sort"] == 0
    assert row["runs_display"] == "0"
    assert row["runs_sort"] == 0
    assert row["last_played_sort"] is None
    assert row["stalest_scenario"] is None
    assert row["stalest_sort"] is None
    assert row["median_percentile_display"] == "N/A"
    assert row["median_percentile_sort"] is None
    assert row["lowest_percentile_display"] == "N/A"
    assert row["lowest_percentile_sort"] is None
    assert row["lowest_scenario"] is None


def test_format_playlist_overview_row_empty_playlist(monkeypatch):
    _configure(monkeypatch)
    playlist = PlaylistData(name="Empty", code="KovaaKsEmpty", scenarios=[])
    _install_cached_ranks(monkeypatch, {})

    row = format_playlist_overview_row("Empty", playlist, {})

    assert row["played_display"] == "0/0"
    assert row["played_sort"] is None
    assert row["runs_sort"] == 0
    assert row["median_percentile_sort"] is None


def _played_stats(*scenario_names):
    return {
        scenario_name: ScenarioStats(
            date_last_played=datetime(2026, 5, 1, 12, 0, 0),
            number_of_runs=1,
            high_score=100,
        )
        for scenario_name in scenario_names
    }


def test_format_playlist_overview_row_excludes_uncached_and_unranked(monkeypatch):
    _configure(monkeypatch)
    playlist = PlaylistData(
        name="Partial",
        code="KovaaKsPartial",
        scenarios=[
            Scenario(name="Cached", ranks=RANKS),
            Scenario(name="RankedNoTotal", ranks=RANKS),
            Scenario(name="Unranked", ranks=RANKS),
            Scenario(name="ColdCache", ranks=RANKS),
        ],
    )
    stats_by_scenario = _played_stats(
        "Cached", "RankedNoTotal", "Unranked", "ColdCache"
    )
    _install_cached_ranks(
        monkeypatch,
        {
            "Cached": ScenarioRankInfo(
                status=ScenarioRankStatus.RANKED,
                rank=5,
                total_players=100,
                percentile=95.0,
            ),
            # Rank cached but leaderboard total missing: no percentile yet.
            "RankedNoTotal": ScenarioRankInfo(
                status=ScenarioRankStatus.RANKED,
                rank=5,
            ),
            "Unranked": ScenarioRankInfo(
                status=ScenarioRankStatus.UNRANKED,
                total_players=100,
            ),
        },
    )

    row = format_playlist_overview_row("Partial", playlist, stats_by_scenario)

    assert row["median_percentile_display"] == "95.00% · 1/4"
    assert row["median_percentile_sort"] == 95.0
    assert row["lowest_percentile_display"] == "95.00% · 1/4"
    assert row["lowest_scenario"] == "Cached"


def test_format_playlist_overview_row_excludes_ranked_but_unplayed_scenarios(
    monkeypatch,
):
    """R9: cached rank info without local run data stays out of the aggregate."""
    _configure(monkeypatch)
    playlist = PlaylistData(
        name="Pruned",
        code="KovaaKsPruned",
        scenarios=[
            Scenario(name="Played", ranks=RANKS),
            Scenario(name="PrunedCsvs", ranks=RANKS),
        ],
    )
    stats_by_scenario = _played_stats("Played")
    _install_cached_ranks(
        monkeypatch,
        {
            "Played": ScenarioRankInfo(
                status=ScenarioRankStatus.RANKED,
                rank=10,
                total_players=100,
                percentile=90.0,
            ),
            # Ranked in cache, but its local CSVs are gone: excluded so the
            # coverage numerator can never exceed the Played numerator.
            "PrunedCsvs": ScenarioRankInfo(
                status=ScenarioRankStatus.RANKED,
                rank=90,
                total_players=100,
                percentile=10.0,
            ),
        },
    )

    row = format_playlist_overview_row("Pruned", playlist, stats_by_scenario)

    assert row["played_display"] == "1/2"
    assert row["median_percentile_display"] == "90.00% · 1/2"
    assert row["lowest_percentile_sort"] == 90.0
    assert row["lowest_scenario"] == "Played"


def test_format_playlist_overview_row_isolates_cache_read_failures(monkeypatch):
    _configure(monkeypatch)
    playlist = PlaylistData(
        name="Fragile",
        code="KovaaKsFragile",
        scenarios=[
            Scenario(name="Good", ranks=RANKS),
            Scenario(name="Broken", ranks=RANKS),
        ],
    )
    stats_by_scenario = _played_stats("Good", "Broken")

    def fragile_rank_lookup(scenario_name, *args, **kwargs):
        assert kwargs["allow_network"] is False
        if scenario_name == "Broken":
            raise RuntimeError("simulated cache corruption")
        return ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=5,
            total_players=100,
            percentile=95.0,
        )

    monkeypatch.setattr(
        playlist_overview_service,
        "get_scenario_rank_info",
        fragile_rank_lookup,
    )

    row = format_playlist_overview_row("Fragile", playlist, stats_by_scenario)

    assert row["median_percentile_display"] == "95.00% · 1/2"


def test_build_playlist_overview_rows_uses_disambiguated_selector_labels(
    monkeypatch,
):
    _configure(monkeypatch)
    first = PlaylistData(
        name="Same Name",
        code="CodeA",
        scenarios=[Scenario(name="First")],
    )
    second = PlaylistData(
        name="Same Name",
        code="CodeB",
        scenarios=[Scenario(name="Second")],
    )
    other = PlaylistData(
        name="Another Playlist",
        code="CodeC",
        scenarios=[Scenario(name="Third")],
    )
    monkeypatch.setattr(
        data_service,
        "playlist_database",
        {first.code: first, second.code: second, other.code: other},
    )
    _install_stats_snapshot(monkeypatch, {})
    _install_cached_ranks(monkeypatch, {})
    _install_shown_codes(monkeypatch, {"CodeA", "CodeB", "CodeC"})

    rows = build_playlist_overview_rows()

    assert [(row["name"], row["code"]) for row in rows] == [
        ("Another Playlist", "CodeC"),
        ("Same Name (CodeA)", "CodeA"),
        ("Same Name (CodeB)", "CodeB"),
    ]
    assert all(row["hidden"] is False for row in rows)


def test_build_playlist_overview_rows_filters_hidden_playlists(monkeypatch):
    _configure(monkeypatch)
    shown = PlaylistData(
        name="Shown",
        code="ShownCode",
        scenarios=[Scenario(name="First")],
    )
    hidden = PlaylistData(
        name="Hidden",
        code="HiddenCode",
        scenarios=[Scenario(name="Second")],
    )
    monkeypatch.setattr(
        data_service,
        "playlist_database",
        {shown.code: shown, hidden.code: hidden},
    )
    _install_stats_snapshot(monkeypatch, {})
    _install_cached_ranks(monkeypatch, {})
    _install_shown_codes(monkeypatch, {"ShownCode"})

    default_rows = build_playlist_overview_rows()
    all_rows = build_playlist_overview_rows(include_hidden=True)

    assert [row["code"] for row in default_rows] == ["ShownCode"]
    assert [(row["code"], row["hidden"]) for row in all_rows] == [
        ("HiddenCode", True),
        ("ShownCode", False),
    ]


def test_build_playlist_overview_rows_skips_unknown_selector_codes(monkeypatch):
    _configure(monkeypatch)
    _install_stats_snapshot(monkeypatch, {})
    _install_shown_codes(monkeypatch, {"MissingCode"})
    monkeypatch.setattr(
        playlist_overview_service,
        "get_playlist_selector_options",
        lambda: [{"label": "Ghost", "value": "MissingCode"}],
    )
    monkeypatch.setattr(
        playlist_overview_service,
        "get_playlist_by_code",
        lambda playlist_code: None,
    )

    assert build_playlist_overview_rows() == []
