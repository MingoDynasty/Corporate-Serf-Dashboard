from datetime import datetime
from types import SimpleNamespace

import dash
import dash_mantine_components as dmc
import pytest
from dash import no_update
from dash.exceptions import PreventUpdate

from source.kovaaks import data_service
from source.kovaaks.data_models import PlaylistData, Scenario
from source.pages import playlist_components

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import (  # noqa: E402
    aim_training_journey,
    playlist_scenarios,
    playlists,
)


def test_bare_playlists_route_callback_builds_playlist_path():
    assert playlists.route_to_selected_playlist("KovaaKsTestCode") == (
        "/playlists/KovaaKsTestCode"
    )


def test_playlist_scenarios_selector_callback_builds_playlist_path(monkeypatch):
    monkeypatch.setattr(
        playlist_scenarios,
        "ctx",
        SimpleNamespace(triggered_id="playlist-scenarios-selector"),
    )

    assert (
        playlist_scenarios.route_from_playlist_interaction(
            "KovaaKsTestCode",
            None,
            "/playlists/OldCode",
            "OldCode",
        )
        == "/playlists/KovaaKsTestCode"
    )


def test_playlist_scenarios_selector_callback_skips_current_path(monkeypatch):
    monkeypatch.setattr(
        playlist_scenarios,
        "ctx",
        SimpleNamespace(triggered_id="playlist-scenarios-selector"),
    )

    assert (
        playlist_scenarios.route_from_playlist_interaction(
            "KovaaKsTestCode",
            None,
            "/playlists/KovaaKsTestCode",
            "KovaaKsTestCode",
        )
        is no_update
    )


def test_playlist_scenarios_cell_click_callback_builds_home_link(monkeypatch):
    monkeypatch.setattr(
        playlist_scenarios,
        "ctx",
        SimpleNamespace(triggered_id="playlist-scenarios-grid"),
    )

    assert (
        playlist_scenarios.route_from_playlist_interaction(
            None,
            {"colId": "scenario", "value": "VT Pasu & Friends"},
            "/playlists/Code/One",
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


def test_playlist_selector_dropdown_scrollbar_is_always_visible():
    selector = playlist_components.playlist_selector("playlists-selector")

    assert selector.scrollAreaProps == {"type": "always"}


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
