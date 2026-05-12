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

    def fake_build_rows(playlist_code):
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
    assert status == "Playlist code is not imported: MissingCode"


def test_playlist_scenarios_page_handles_missing_playlist_code():
    rows, status = playlist_scenarios.load_playlist_scenario_rows(None)

    assert rows == []
    assert status == "Select a playlist from the Playlists page."


def test_playlist_scenarios_table_includes_local_stat_columns():
    fields = [column["field"] for column in playlist_scenarios.TABLE_COLUMN_DEFS]

    assert "last_played_sort" in fields
    assert "runs_sort" in fields
    assert "high_score_sort" in fields


def test_playlist_scenarios_last_played_uses_defined_nulls_last_comparator():
    column = next(
        column
        for column in playlist_scenarios.TABLE_COLUMN_DEFS
        if column["field"] == "last_played_sort"
    )

    assert column["comparator"] == {"function": "dagfuncs.nullsLastComparator"}


def test_playlist_scenarios_table_includes_personal_best_metadata_columns():
    columns = {
        column["field"]: column for column in playlist_scenarios.TABLE_COLUMN_DEFS
    }

    assert columns["pb_cm360_sort"]["headerName"] == "PB cm/360"
    assert columns["pb_accuracy_sort"]["headerName"] == "PB Accuracy"


def test_playlist_scenarios_grid_uses_content_auto_size():
    grid = playlist_scenarios.layout("KovaaKsTestCode")
    loading = grid.children[-1]
    ag_grid = loading.children

    assert ag_grid.columnSize == "autoSize"
    assert ag_grid.columnSizeOptions == playlist_scenarios.COLUMN_SIZE_OPTIONS


def test_playlist_scenarios_scenario_column_fills_remaining_width():
    column = next(
        column
        for column in playlist_scenarios.TABLE_COLUMN_DEFS
        if column["field"] == "scenario"
    )

    assert column["flex"] == 1
    assert column["maxWidth"] == 400
    assert "scenario" not in playlist_scenarios.AUTO_SIZE_COLUMN_KEYS
