from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

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


def test_playlists_overview_visibility_cell_click_does_not_navigate():
    assert (
        playlists.route_to_clicked_playlist(
            {"rowId": "KovaaKsTestCode", "colId": playlists.VISIBILITY_COLUMN_ID}
        )
        is no_update
    )


def _trigger(monkeypatch, triggered_id):
    monkeypatch.setattr(
        playlists,
        "ctx",
        SimpleNamespace(triggered_id=triggered_id),
    )


def test_playlists_overview_page_loads_rows(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-mounted")
    expected_rows = [{"name": "Voltaic Benchmarks", "code": "KovaaKsTestCode"}]
    seen_include_hidden = []

    def fake_build(include_hidden=False):
        seen_include_hidden.append(include_hidden)
        return expected_rows

    monkeypatch.setattr(playlists, "build_playlist_overview_rows", fake_build)

    rows, status = playlists.load_playlist_overview_rows(True, False, None, 0)

    assert rows == expected_rows
    assert status == ""
    assert seen_include_hidden == [False]


def test_playlists_overview_show_hidden_switch_includes_hidden_rows(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-show-hidden")
    seen_include_hidden = []

    def fake_build(include_hidden=False):
        seen_include_hidden.append(include_hidden)
        return [{"code": "KovaaKsTestCode", "hidden": True}]

    monkeypatch.setattr(playlists, "build_playlist_overview_rows", fake_build)

    rows, _status = playlists.load_playlist_overview_rows(True, True, None, 0)

    assert seen_include_hidden == [True]
    assert rows[0]["hidden"] is True


def test_playlists_overview_visibility_click_toggles_and_rebuilds(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-grid")
    toggled = []
    monkeypatch.setattr(playlists, "toggle_playlist_visibility", toggled.append)
    monkeypatch.setattr(
        playlists,
        "build_playlist_overview_rows",
        lambda include_hidden=False: [{"code": "KovaaKsTestCode"}],
    )

    rows, status = playlists.load_playlist_overview_rows(
        True,
        False,
        {"rowId": "KovaaKsTestCode", "colId": playlists.VISIBILITY_COLUMN_ID},
        0,
    )

    assert toggled == ["KovaaKsTestCode"]
    assert rows == [{"code": "KovaaKsTestCode"}]
    assert status == ""


def test_playlists_overview_non_visibility_click_changes_nothing(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-grid")
    monkeypatch.setattr(
        playlists,
        "toggle_playlist_visibility",
        lambda _code: pytest.fail("navigation clicks must not toggle visibility"),
    )

    rows, status = playlists.load_playlist_overview_rows(
        True,
        False,
        {"rowId": "KovaaKsTestCode", "colId": "name"},
        0,
    )

    assert rows is no_update
    assert status is no_update


def test_playlists_overview_page_reports_empty_database(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-mounted")
    monkeypatch.setattr(
        playlists,
        "build_playlist_overview_rows",
        lambda include_hidden=False: [],
    )

    rows, status = playlists.load_playlist_overview_rows(True, False, None, 0)

    assert rows == []
    assert status == "No playlists are loaded."


def test_playlists_overview_page_reports_all_hidden(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-mounted")
    monkeypatch.setattr(
        playlists,
        "build_playlist_overview_rows",
        lambda include_hidden=False: (
            [{"code": "KovaaKsTestCode", "hidden": True}] if include_hidden else []
        ),
    )

    rows, status = playlists.load_playlist_overview_rows(True, False, None, 0)

    assert rows == []
    assert status == 'All playlists are hidden. Toggle "Show hidden" to manage them.'


def test_playlists_overview_visibility_column_config():
    columns = {column["field"]: column for column in playlists.TABLE_COLUMN_DEFS}
    column = columns[playlists.VISIBILITY_COLUMN_ID]

    assert column["cellRenderer"] == "VisibilityAction"
    assert column["sortable"] is False


def test_playlists_overview_delete_column_config():
    columns = {column["field"]: column for column in playlists.TABLE_COLUMN_DEFS}
    column = columns[playlists.DELETE_COLUMN_ID]

    assert column["cellRenderer"] == "DeleteAction"
    assert column["sortable"] is False


def test_playlists_overview_delete_cell_click_does_not_navigate():
    assert (
        playlists.route_to_clicked_playlist(
            {"rowId": "UserCode", "colId": playlists.DELETE_COLUMN_ID}
        )
        is no_update
    )


def test_manage_delete_modal_opens_for_delete_cell(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-grid")
    monkeypatch.setattr(playlists, "get_user_root_playlist_codes", lambda: {"UserCode"})
    monkeypatch.setattr(
        playlists, "get_playlist_display_label", lambda _code: "My Playlist"
    )

    opened, target, message = playlists.manage_delete_modal(
        {"rowId": "UserCode", "colId": playlists.DELETE_COLUMN_ID}, 0
    )

    assert opened is True
    assert target == "UserCode"
    assert "My Playlist" in message
    assert "UserCode" in message


def test_manage_delete_modal_ignores_bundled_delete_cell(monkeypatch):
    # A bundled row renders no Delete link, but its empty delete cell still
    # emits cellClicked; the modal must not open for a non-user code (which
    # delete_user_playlist would refuse anyway, after a misleading dialog).
    _trigger(monkeypatch, "playlists-overview-grid")
    monkeypatch.setattr(playlists, "get_user_root_playlist_codes", lambda: {"UserCode"})
    monkeypatch.setattr(
        playlists,
        "get_playlist_display_label",
        lambda _code: pytest.fail("bundled delete cell must not reach the modal"),
    )

    result = playlists.manage_delete_modal(
        {"rowId": "BundledCode", "colId": playlists.DELETE_COLUMN_ID}, 0
    )

    assert result == (no_update, no_update, no_update)


def test_manage_delete_modal_ignores_non_delete_cells(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-grid")

    result = playlists.manage_delete_modal({"rowId": "UserCode", "colId": "name"}, 0)

    assert result == (no_update, no_update, no_update)


def test_manage_delete_modal_cancel_closes(monkeypatch):
    _trigger(monkeypatch, "playlists-delete-cancel-button")

    opened, target, message = playlists.manage_delete_modal(None, 1)

    assert opened is False
    assert target is no_update
    assert message is no_update


def test_confirm_delete_playlist_success_rebuilds_and_forgets_visibility(monkeypatch):
    deleted = []
    hidden = []
    monkeypatch.setattr(
        playlists,
        "delete_user_playlist",
        lambda code: deleted.append(code) or None,
    )
    monkeypatch.setattr(playlists, "hide_playlist", hidden.append)

    notifications, rows_refresh, opened = playlists.confirm_delete_playlist(
        1, "UserCode", 4
    )

    assert deleted == ["UserCode"]
    # In a show-list, dropping membership IS forgetting the code, so
    # preferences.json does not accumulate dead codes.
    assert hidden == ["UserCode"]
    assert notifications[0]["color"] == "green"
    assert rows_refresh == 5
    assert opened is False


def test_confirm_delete_playlist_failure_leaves_rows_and_visibility(monkeypatch):
    monkeypatch.setattr(playlists, "delete_user_playlist", lambda _code: "boom")
    monkeypatch.setattr(
        playlists,
        "hide_playlist",
        lambda _code: pytest.fail("a failed delete must not forget visibility"),
    )

    notifications, rows_refresh, opened = playlists.confirm_delete_playlist(
        1, "UserCode", 4
    )

    assert notifications[0]["color"] == "red"
    assert notifications[0]["message"] == "boom"
    assert rows_refresh is no_update
    assert opened is False


def test_confirm_delete_playlist_without_target_noops(monkeypatch):
    monkeypatch.setattr(
        playlists,
        "delete_user_playlist",
        lambda _code: pytest.fail("no target must not trigger a delete"),
    )

    result = playlists.confirm_delete_playlist(1, None, 0)

    assert result == (no_update, no_update, no_update)


def test_render_superseded_alert_hidden_when_no_files(monkeypatch):
    monkeypatch.setattr(playlists, "get_superseded_user_playlist_files", lambda: [])

    style, text = playlists.render_superseded_alert(True, 0)

    assert style == {"display": "none"}
    assert text == ""


def test_render_superseded_alert_shows_count_when_files_exist(monkeypatch):
    monkeypatch.setattr(
        playlists,
        "get_superseded_user_playlist_files",
        lambda: [(Path("a.json"), "C1"), (Path("b.json"), "C2")],
    )

    style, text = playlists.render_superseded_alert(True, 1)

    assert style == {}
    assert "2 leftover playlist files" in text


def test_manage_superseded_modal_opens_with_count(monkeypatch):
    _trigger(monkeypatch, "playlists-superseded-delete-button")
    monkeypatch.setattr(
        playlists,
        "get_superseded_user_playlist_files",
        lambda: [(Path("a.json"), "C1")],
    )

    opened, message = playlists.manage_superseded_modal(1, 0)

    assert opened is True
    assert "1 leftover playlist file" in message


def test_manage_superseded_modal_cancel_closes(monkeypatch):
    _trigger(monkeypatch, "playlists-superseded-cancel-button")

    opened, message = playlists.manage_superseded_modal(0, 1)

    assert opened is False
    assert message is no_update


def test_confirm_delete_superseded_success_refreshes(monkeypatch):
    monkeypatch.setattr(
        playlists, "delete_superseded_user_playlist_files", lambda: None
    )

    notifications, rows_refresh, opened = playlists.confirm_delete_superseded(1, 2)

    assert notifications[0]["color"] == "green"
    assert rows_refresh == 3
    assert opened is False


def test_confirm_delete_superseded_failure_still_refreshes(monkeypatch):
    # A partial failure still prunes the files it removed, so the alert must
    # re-render with the reduced count even on error.
    monkeypatch.setattr(
        playlists, "delete_superseded_user_playlist_files", lambda: "nope"
    )

    notifications, rows_refresh, opened = playlists.confirm_delete_superseded(1, 2)

    assert notifications[0]["color"] == "red"
    assert notifications[0]["message"] == "nope"
    assert rows_refresh == 3
    assert opened is False


def test_confirm_delete_superseded_ignores_initial_load(monkeypatch):
    # Regression: under DashProxy an allow_duplicate callback can fire once on
    # initial page load with n_clicks=None; a destructive handler must never
    # delete without a real confirm click.
    monkeypatch.setattr(
        playlists,
        "delete_superseded_user_playlist_files",
        lambda: pytest.fail("must not delete files without a confirm click"),
    )

    assert playlists.confirm_delete_superseded(None, 0) == (
        no_update,
        no_update,
        no_update,
    )


def test_confirm_delete_playlist_ignores_initial_load(monkeypatch):
    monkeypatch.setattr(
        playlists,
        "delete_user_playlist",
        lambda _code: pytest.fail("must not delete without a confirm click"),
    )

    assert playlists.confirm_delete_playlist(None, "UserCode", 0) == (
        no_update,
        no_update,
        no_update,
    )


def test_manage_superseded_modal_ignores_initial_load(monkeypatch):
    _trigger(monkeypatch, None)
    monkeypatch.setattr(
        playlists,
        "get_superseded_user_playlist_files",
        lambda: pytest.fail("initial load must not open the cleanup modal"),
    )

    assert playlists.manage_superseded_modal(None, None) == (no_update, no_update)


def _walk_components(component):
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk_components(child)
        return
    yield from _walk_components(children)


def test_playlists_overview_layout_includes_show_hidden_switch_and_row_muting():
    page = playlists.layout()
    grid = page.children[-1].children
    switch = next(
        component
        for component in _walk_components(page)
        if getattr(component, "id", None) == "playlists-overview-show-hidden"
    )

    assert switch.checked is False
    assert grid.rowClassRules == {
        "playlist-overview-row-hidden": "params.data.hidden",
    }


def test_import_playlist_shows_the_canonical_stored_code(monkeypatch):
    # KovaaK's canonicalizes pasted codes; the stored code is what visibility
    # must persist, or a non-canonical paste imports hidden once a
    # preferences file exists.
    monkeypatch.setattr(
        playlists,
        "load_playlist_from_code",
        lambda _code: (None, "CanonicalCode"),
    )
    shown = []
    monkeypatch.setattr(playlists, "show_playlist", shown.append)

    notifications, import_refresh, opened, value = playlists.import_playlist(
        1, "  canonicalcode  ", 0
    )

    assert shown == ["CanonicalCode"]
    assert notifications[0]["color"] == "green"
    # A successful import bumps the refresh store so the grid rebuilds, then
    # closes the modal and clears the field so the user sees the new row.
    assert import_refresh == 1
    assert opened is False
    assert value == ""


def test_import_playlist_failure_does_not_show(monkeypatch):
    monkeypatch.setattr(
        playlists, "load_playlist_from_code", lambda _code: ("boom", None)
    )
    monkeypatch.setattr(
        playlists,
        "show_playlist",
        lambda _code: pytest.fail("must not mark failed imports as shown"),
    )

    notifications, import_refresh, opened, value = playlists.import_playlist(
        1, "BadCode", 3
    )

    assert notifications[0]["color"] == "red"
    assert notifications[0]["message"] == "boom"
    # A failed import must not rebuild rows, and leaves the modal open with the
    # pasted code intact so the user can correct it.
    assert import_refresh is no_update
    assert opened is no_update
    assert value is no_update


def test_import_playlist_duplicate_of_hidden_appends_unhide_hint(monkeypatch):
    monkeypatch.setattr(
        playlists,
        "load_playlist_from_code",
        lambda _code: (
            "Playlist code already exists: ExistingCode is already imported "
            "as Same Name (ExistingCode).",
            "ExistingCode",
        ),
    )
    monkeypatch.setattr(playlists, "is_playlist_shown", lambda _code: False)
    monkeypatch.setattr(
        playlists,
        "show_playlist",
        lambda _code: pytest.fail("a refused import must not be shown"),
    )

    notifications, import_refresh, opened, value = playlists.import_playlist(
        1, "ExistingCode", 0
    )

    assert notifications[0]["color"] == "red"
    assert notifications[0]["message"].endswith(playlists.HIDDEN_DUPLICATE_HINT)
    assert import_refresh is no_update
    assert opened is no_update
    assert value is no_update


def test_import_playlist_duplicate_of_visible_omits_hint(monkeypatch):
    monkeypatch.setattr(
        playlists,
        "load_playlist_from_code",
        lambda _code: (
            "Playlist code already exists: ExistingCode is already imported "
            "as Same Name (ExistingCode).",
            "ExistingCode",
        ),
    )
    monkeypatch.setattr(playlists, "is_playlist_shown", lambda _code: True)

    notifications, _import_refresh, _opened, _value = playlists.import_playlist(
        1, "ExistingCode", 0
    )

    assert playlists.HIDDEN_DUPLICATE_HINT not in notifications[0]["message"]


def test_import_playlist_refresh_bump_rebuilds_rows(monkeypatch):
    _trigger(monkeypatch, "playlists-rows-refresh")
    monkeypatch.setattr(
        playlists,
        "build_playlist_overview_rows",
        lambda include_hidden=False: [{"code": "KovaaKsTestCode"}],
    )

    rows, status = playlists.load_playlist_overview_rows(True, False, None, 1)

    assert rows == [{"code": "KovaaKsTestCode"}]
    assert status == ""


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
