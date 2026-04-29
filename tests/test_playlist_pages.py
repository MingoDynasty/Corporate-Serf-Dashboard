import dash

from source.kovaaks import data_service
from source.kovaaks.data_models import PlaylistData, Scenario

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import playlist_scenarios, playlists  # noqa: E402


def test_bare_playlists_route_callback_builds_playlist_path():
    assert playlists.route_to_selected_playlist("KovaaKsTestCode") == (
        "/playlists/KovaaKsTestCode"
    )


def test_playlist_scenarios_page_loads_rows_for_imported_playlist(monkeypatch):
    playlist = PlaylistData(
        name="Voltaic Benchmarks",
        code="KovaaKsTestCode",
        scenarios=[Scenario(name="First")],
    )
    expected_rows = [
        {
            "scenario": "First",
            "playlist_order": 0,
            "status": "RANKED",
            "rank_display": "10",
            "rank_sort": 10,
            "total_display": "100",
            "total_sort": 100,
            "percentile_display": "90.50%",
            "percentile_sort": 90.5,
        }
    ]
    monkeypatch.setattr(data_service, "playlist_database", {playlist.name: playlist})

    def fake_build_rows(playlist_code, _lookup_config):
        assert playlist_code == "KovaaKsTestCode"
        return expected_rows

    monkeypatch.setattr(
        playlist_scenarios,
        "build_playlist_scenario_rank_rows",
        fake_build_rows,
    )

    rows, status = playlist_scenarios.load_playlist_scenario_rows("KovaaKsTestCode")

    assert rows == expected_rows
    assert status == ""
    assert playlist_scenarios.layout("KovaaKsTestCode") is not None


def test_playlist_scenarios_page_handles_unknown_playlist(monkeypatch):
    monkeypatch.setattr(data_service, "playlist_database", {})

    rows, status = playlist_scenarios.load_playlist_scenario_rows("MissingCode")

    assert rows == []
    assert status == "The selected playlist is not imported."
