from datetime import datetime

import dash
import dash_mantine_components as dmc
import pytest
from dash import no_update
from dash.exceptions import PreventUpdate

from source.kovaaks import data_service
from source.kovaaks.data_models import PlaylistData, Scenario

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import (  # noqa: E402
    aim_training_journey,
    playlist_scenarios,
    playlists,
)


def test_playlists_overview_cell_click_routes_to_playlist():
    assert playlists.route_to_clicked_playlist(
        {"rowId": "KovaaKsTestCode", "colId": "name", "rowIndex": 0}
    ) == ("/playlists/KovaaKsTestCode")


def test_playlists_overview_cell_click_ignores_malformed_payloads():
    assert playlists.route_to_clicked_playlist(None) is no_update
    assert playlists.route_to_clicked_playlist({"colId": "name"}) is no_update
    assert playlists.route_to_clicked_playlist({"rowId": ""}) is no_update
    assert playlists.route_to_clicked_playlist({"rowId": 3}) is no_update


def test_playlists_overview_page_loads_rows(monkeypatch):
    expected_rows = [{"name": "Voltaic Benchmarks", "code": "KovaaKsTestCode"}]
    monkeypatch.setattr(
        playlists,
        "build_playlist_overview_rows",
        lambda: expected_rows,
    )

    rows, status = playlists.load_playlist_overview_rows(True)

    assert rows == expected_rows
    assert status == ""


def test_playlists_overview_page_reports_empty_database(monkeypatch):
    monkeypatch.setattr(playlists, "build_playlist_overview_rows", lambda: [])

    rows, status = playlists.load_playlist_overview_rows(True)

    assert rows == []
    assert status == "No playlists are loaded."


def test_playlists_overview_sortable_columns_use_nulls_last_comparator():
    columns = {column["field"]: column for column in playlists.TABLE_COLUMN_DEFS}

    for field in [
        "played_sort",
        "runs_sort",
        "last_played_sort",
        "median_percentile_sort",
        "lowest_percentile_sort",
    ]:
        assert columns[field]["comparator"] == {"function": "nullsLastComparator"}


def test_playlists_overview_type_column_uses_badge_renderer():
    columns = {column["field"]: column for column in playlists.TABLE_COLUMN_DEFS}

    assert columns["type_display"]["cellRenderer"] == "TypeBadge"


def test_playlists_overview_defaults_to_staleness_sort():
    columns = {column["field"]: column for column in playlists.TABLE_COLUMN_DEFS}

    assert columns["last_played_sort"]["sort"] == "desc"
    assert all(
        "sort" not in column
        for column in playlists.TABLE_COLUMN_DEFS
        if column["field"] != "last_played_sort"
    )


def test_playlists_overview_last_played_follows_relative_time_conventions():
    columns = {column["field"]: column for column in playlists.TABLE_COLUMN_DEFS}
    column = columns["last_played_sort"]

    assert column["valueFormatter"] == {
        "function": "relativeTime(params.value, 'Never')"
    }
    assert column["tooltipValueGetter"] == {"function": playlists.LAST_PLAYED_TOOLTIP}
    assert "stalest_scenario" in playlists.LAST_PLAYED_TOOLTIP
    assert "relativeTime(params.data.stalest_sort" in playlists.LAST_PLAYED_TOOLTIP


def test_playlists_overview_grid_rows_navigate_by_playlist_code():
    page = playlists.layout()
    grid = page.children[-1].children

    assert grid.dashGridOptions["getRowId"] == {"function": "params.data.code"}
    assert grid.dashGridOptions["tooltipShowDelay"] == 0
    assert grid.dangerously_allow_code is True


def test_playlists_overview_grid_uses_bounded_viewport_layout():
    page = playlists.layout()
    loading = page.children[-1]
    grid = loading.children

    assert page.style == {
        "height": (
            "calc(100dvh - var(--app-shell-header-offset, 0rem) "
            "- 2*var(--app-shell-padding, 1rem))"
        )
    }
    assert loading.parent_style == {
        "flex": 1,
        "minHeight": 0,
        "display": "flex",
        "flexDirection": "column",
    }
    assert grid.columnSize == "autoSize"
    assert grid.columnSizeOptions == playlists.COLUMN_SIZE_OPTIONS


def test_playlists_overview_layout_includes_relative_time_refresh_interval():
    page = playlists.layout()
    children_by_id = {getattr(child, "id", None): child for child in page.children}

    interval = children_by_id["playlists-overview-relative-time-interval"]

    assert "playlists-overview-relative-time-refresh" in children_by_id
    assert interval.interval == 30_000
    assert interval.n_intervals == 0


def test_playlist_scenarios_cell_click_callback_builds_home_link():
    assert (
        playlist_scenarios.route_to_scenario_home(
            {"colId": "scenario", "value": "VT Pasu & Friends"},
            "Code/One",
        )
        == "/?playlist_code=Code%2FOne&scenario=VT+Pasu+%26+Friends"
    )


def test_aim_training_journey_page_inherits_shell_theme_provider():
    page = aim_training_journey.layout()

    assert isinstance(page, dmc.Box)
    assert all(not isinstance(child, dmc.MantineProvider) for child in page.children)


def test_aim_training_journey_graph_applies_selected_theme(monkeypatch):
    dmc.add_figure_templates()

    monkeypatch.setattr(
        aim_training_journey,
        "filter_known_playlist_codes",
        lambda selected_playlists: selected_playlists,
    )
    monkeypatch.setattr(
        aim_training_journey,
        "get_playlist_display_label",
        lambda playlist_code: playlist_code,
    )
    monkeypatch.setattr(
        aim_training_journey,
        "get_aim_training_journey_for_playlists",
        lambda selected_playlists: {
            selected_playlists[0]: {datetime(2025, 1, 1): 0.5},
        },
    )
    monkeypatch.setattr(
        aim_training_journey,
        "get_aim_training_checkpoints",
        lambda checkpoint_hour: {},
    )

    light_figure = aim_training_journey.generate_graph(["Playlist"], 10, "light")
    dark_figure = aim_training_journey.generate_graph(["Playlist"], 10, "dark")

    assert light_figure.layout.template.layout.paper_bgcolor == "#ffffff"
    assert dark_figure.layout.template.layout.paper_bgcolor == "#242424"


def test_aim_training_journey_filters_stale_values_and_disambiguates_labels(
    monkeypatch,
):
    dmc.add_figure_templates()
    seen_codes = []

    monkeypatch.setattr(
        aim_training_journey,
        "filter_known_playlist_codes",
        lambda selected_playlists: [
            playlist_code
            for playlist_code in selected_playlists
            if playlist_code in {"CodeA", "CodeB"}
        ],
    )

    def fake_journey(selected_playlists):
        seen_codes.append(selected_playlists)
        return {
            "CodeA": {datetime(2025, 1, 1): 0.5},
            "CodeB": {datetime(2025, 1, 1): 0.75},
        }

    monkeypatch.setattr(
        aim_training_journey,
        "get_aim_training_journey_for_playlists",
        fake_journey,
    )
    monkeypatch.setattr(
        aim_training_journey,
        "get_aim_training_checkpoints",
        lambda checkpoint_hour: {},
    )
    monkeypatch.setattr(
        aim_training_journey,
        "get_playlist_display_label",
        lambda playlist_code: {
            "CodeA": "Same Name (CodeA)",
            "CodeB": "Same Name (CodeB)",
        }[playlist_code],
    )

    figure = aim_training_journey.generate_graph(
        ["Old Playlist Name", "CodeA", "CodeB"],
        10,
        "light",
    )

    assert seen_codes == [["CodeA", "CodeB"]]
    assert [trace.name for trace in figure.data] == [
        "Same Name (CodeA)",
        "Same Name (CodeB)",
    ]


def test_aim_training_journey_waits_for_color_scheme():
    with pytest.raises(PreventUpdate):
        aim_training_journey.generate_graph(["Playlist"], 10, None)


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
    monkeypatch.setattr(data_service, "playlist_database", {playlist.code: playlist})

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


def test_playlist_scenarios_scenario_home_href_url_encodes_values():
    href = playlist_scenarios.scenario_home_href(
        "VT Pasu & Friends",
        "Code/One",
    )

    assert href == "/?playlist_code=Code%2FOne&scenario=VT+Pasu+%26+Friends"


def test_playlist_scenarios_last_played_uses_defined_nulls_last_comparator():
    column = next(
        column
        for column in playlist_scenarios.TABLE_COLUMN_DEFS
        if column["field"] == "last_played_sort"
    )

    assert column["comparator"] == {"function": "nullsLastComparator"}


def test_playlist_scenarios_last_played_has_immediate_tooltip_affordance():
    column = next(
        column
        for column in playlist_scenarios.TABLE_COLUMN_DEFS
        if column["field"] == "last_played_sort"
    )
    grid = playlist_scenarios.layout("KovaaKsTestCode").children[-1].children

    assert column["cellClass"] == {
        "function": "params.value == null ? null : 'last-played-affordance'"
    }
    assert column["tooltipValueGetter"] == {
        "function": (
            "params.value == null ? null : absoluteTime(params.value, 'Never')"
        )
    }
    assert grid.dashGridOptions["tooltipShowDelay"] == 0


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


def test_playlist_scenarios_grid_uses_bounded_viewport_layout():
    page = playlist_scenarios.layout("KovaaKsTestCode")
    loading = page.children[-1]
    ag_grid = loading.children

    assert page.style == {
        "height": (
            "calc(100dvh - var(--app-shell-header-offset, 0rem) "
            "- 2*var(--app-shell-padding, 1rem))"
        )
    }
    assert loading.parent_style == {
        "flex": 1,
        "minHeight": 0,
        "display": "flex",
        "flexDirection": "column",
    }
    assert "domLayout" not in ag_grid.dashGridOptions
    assert ag_grid.style == {
        "height": "100%",
        "width": "100%",
        "minHeight": 300,
    }


def test_playlist_scenarios_layout_includes_relative_time_refresh_interval():
    page = playlist_scenarios.layout("KovaaKsTestCode")
    children_by_id = {getattr(child, "id", None): child for child in page.children}

    interval = children_by_id["playlist-scenarios-relative-time-interval"]

    assert "playlist-scenarios-relative-time-refresh" in children_by_id
    assert interval.interval == 30_000
    assert interval.n_intervals == 0


def test_playlist_scenarios_scenario_column_fills_remaining_width():
    column = next(
        column
        for column in playlist_scenarios.TABLE_COLUMN_DEFS
        if column["field"] == "scenario"
    )

    assert column["flex"] == 1
    assert column["maxWidth"] == 400
    assert column["cellClass"] == "playlist-scenario-link-cell"
    assert "scenario" not in playlist_scenarios.AUTO_SIZE_COLUMN_KEYS
