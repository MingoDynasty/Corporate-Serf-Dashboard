from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import dash
import dash_mantine_components as dmc
import pytest
from dash import dcc, no_update
from dash.exceptions import PreventUpdate

from source.kovaaks import data_service
from source.kovaaks.data_models import PlaylistData, Scenario
from source.kovaaks.percentile_warmup_service import PercentileWarmupSnapshot

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


def _warmup_snapshot(
    *,
    queued_names=(),
    in_flight=None,
    remaining_count=0,
    paused_until=None,
    fatal_state=None,
    enqueue_generation=0,
    recent_pace_seconds=None,
):
    return PercentileWarmupSnapshot(
        queued_names=queued_names,
        in_flight=in_flight,
        remaining_count=remaining_count,
        paused_until=paused_until,
        backoff_seconds=None,
        fatal_state=fatal_state,
        enqueue_generation=enqueue_generation,
        recent_pace_seconds=recent_pace_seconds,
    )


def test_playlists_overview_page_loads_rows(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-mounted")
    expected_rows = [{"name": "Voltaic Benchmarks", "code": "KovaaKsTestCode"}]
    seen_include_hidden = []

    def fake_build(include_hidden=False, *, record_activity=True):
        seen_include_hidden.append((include_hidden, record_activity))
        return expected_rows

    monkeypatch.setattr(playlists, "build_playlist_overview_rows", fake_build)

    rows, status, *_ = playlists.load_playlist_overview_rows(True, False, None, 0, 0)

    assert rows == expected_rows
    assert status == ""
    assert seen_include_hidden == [(False, True)]


def test_playlists_overview_show_hidden_switch_includes_hidden_rows(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-show-hidden")
    seen_include_hidden = []

    def fake_build(include_hidden=False, *, record_activity=True):
        seen_include_hidden.append((include_hidden, record_activity))
        return [{"code": "KovaaKsTestCode", "hidden": True}]

    monkeypatch.setattr(playlists, "build_playlist_overview_rows", fake_build)

    rows, _status, *_ = playlists.load_playlist_overview_rows(True, True, None, 0, 0)

    assert seen_include_hidden == [(True, True)]
    assert rows[0]["hidden"] is True


def test_playlists_overview_visibility_click_toggles_and_bumps_refresh(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-grid")
    toggled = []
    enqueued = []

    def show_on_toggle(code):
        toggled.append(code)
        return True

    monkeypatch.setattr(playlists, "toggle_playlist_visibility", show_on_toggle)
    monkeypatch.setattr(
        playlists,
        "enqueue_playlist_percentile_warmup",
        enqueued.append,
    )
    rows_refresh = playlists.update_playlist_visibility(
        {"rowId": "KovaaKsTestCode", "colId": playlists.VISIBILITY_COLUMN_ID},
        7,
    )

    assert toggled == ["KovaaKsTestCode"]
    assert enqueued == ["KovaaKsTestCode"]
    assert rows_refresh == 8


def test_playlists_overview_non_visibility_click_changes_nothing(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-grid")
    monkeypatch.setattr(
        playlists,
        "toggle_playlist_visibility",
        lambda _code: pytest.fail("navigation clicks must not toggle visibility"),
    )

    rows_refresh = playlists.update_playlist_visibility(
        {"rowId": "KovaaKsTestCode", "colId": "name"},
        0,
    )

    assert rows_refresh is no_update


def test_playlists_overview_visibility_callback_ignores_phantom_initial_fire(
    monkeypatch,
):
    _trigger(monkeypatch, None)
    monkeypatch.setattr(
        playlists,
        "toggle_playlist_visibility",
        lambda _code: pytest.fail("phantom initial fire must not toggle visibility"),
    )

    assert playlists.update_playlist_visibility(None, 3) is no_update


def test_worker_idle_then_unhide_rearms_live_refresh(monkeypatch):
    state = [_warmup_snapshot()]
    monkeypatch.setattr(playlists, "get_percentile_warmup_state", lambda: state[0])

    disabled, status, generation = playlists._playlist_overview_warmup_state(0)
    assert disabled is True
    assert status == ""
    assert generation == 0

    _trigger(monkeypatch, "playlists-overview-grid")
    monkeypatch.setattr(playlists, "toggle_playlist_visibility", lambda _code: True)

    def enqueue(_code):
        state[0] = _warmup_snapshot(
            queued_names=("Scenario",),
            remaining_count=1,
            enqueue_generation=1,
        )
        return 1

    monkeypatch.setattr(playlists, "enqueue_playlist_percentile_warmup", enqueue)
    rows_refresh = playlists.update_playlist_visibility(
        {"rowId": "KovaaKsTestCode", "colId": playlists.VISIBILITY_COLUMN_ID},
        0,
    )

    disabled, status, generation = playlists._playlist_overview_warmup_state(0)
    assert rows_refresh == 1
    assert disabled is False
    assert status == "Updating percentile data: 1 remaining"
    assert generation == 1


def test_older_warmup_generation_cannot_disable_newer_rearm(monkeypatch):
    monkeypatch.setattr(
        playlists,
        "get_percentile_warmup_state",
        lambda: _warmup_snapshot(enqueue_generation=2),
    )

    disabled, status, generation = playlists._playlist_overview_warmup_state(3)

    assert disabled is False
    assert status is no_update
    assert generation == 3


def test_warmup_status_formats_eta_pause_and_fatal_state(monkeypatch):
    state = [
        _warmup_snapshot(
            queued_names=("A", "B", "C"),
            remaining_count=3,
            enqueue_generation=1,
            recent_pace_seconds=50,
        )
    ]
    monkeypatch.setattr(playlists, "get_percentile_warmup_state", lambda: state[0])

    disabled, status, _generation = playlists._playlist_overview_warmup_state(0)
    assert disabled is False
    assert status == "Updating percentile data: 3 remaining (~3 min)"

    state[0] = _warmup_snapshot(
        queued_names=("A",),
        remaining_count=1,
        paused_until=datetime.now(UTC) + timedelta(minutes=2),
        enqueue_generation=1,
    )
    _disabled, status, _generation = playlists._playlist_overview_warmup_state(1)
    assert status.startswith("Updating percentile data: 1 remaining · paused;")
    assert "retrying at" in status

    state[0] = _warmup_snapshot(fatal_state="unknown username")
    disabled, status, _generation = playlists._playlist_overview_warmup_state(0)
    assert disabled is True
    assert status == "Percentile update stopped: unknown username"


def test_interval_rebuild_does_not_record_interactive_activity(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-warmup-interval")
    seen_record_activity = []

    def fake_build(include_hidden=False, *, record_activity=True):
        seen_record_activity.append(record_activity)
        return [{"code": "KovaaKsTestCode"}]

    monkeypatch.setattr(playlists, "build_playlist_overview_rows", fake_build)

    rows, status, *_ = playlists.load_playlist_overview_rows(True, False, 0, 1, 0)

    assert rows == [{"code": "KovaaKsTestCode"}]
    assert status == ""
    assert seen_record_activity == [False]


def test_final_in_flight_item_keeps_interval_enabled_until_last_rebuild(monkeypatch):
    state = [
        _warmup_snapshot(
            in_flight="Final",
            remaining_count=1,
            enqueue_generation=1,
        )
    ]
    _trigger(monkeypatch, "playlists-overview-warmup-interval")
    events = []
    cache_write_complete = [False]

    def get_state():
        events.append("snapshot")
        return state[0]

    monkeypatch.setattr(playlists, "get_percentile_warmup_state", get_state)

    def build_after_write(include_hidden=False, *, record_activity=True):
        events.append("build")
        assert record_activity is False
        percentile = "ready" if cache_write_complete[0] else "stale"
        return [{"code": "KovaaKsTestCode", "percentile": percentile}]

    monkeypatch.setattr(
        playlists,
        "build_playlist_overview_rows",
        build_after_write,
    )

    rows, _status, disabled, _warmup_status, generation = (
        playlists.load_playlist_overview_rows(True, False, 0, 1, 1)
    )
    assert rows[0]["percentile"] == "stale"
    assert disabled is False
    assert events == ["snapshot", "build"]

    cache_write_complete[0] = True
    state[0] = _warmup_snapshot(enqueue_generation=1)
    events.clear()
    rows, _status, disabled, _warmup_status, _generation = (
        playlists.load_playlist_overview_rows(True, False, 0, 2, generation)
    )

    assert rows[0]["percentile"] == "ready"
    assert disabled is True
    assert events == ["snapshot", "build"]


def test_playlists_overview_page_reports_empty_database(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-mounted")
    monkeypatch.setattr(
        playlists,
        "build_playlist_overview_rows",
        lambda include_hidden=False, *, record_activity=True: [],
    )

    rows, status, *_ = playlists.load_playlist_overview_rows(True, False, None, 0, 0)

    assert rows == []
    assert status == "No playlists are loaded."


def test_playlists_overview_page_reports_all_hidden(monkeypatch):
    _trigger(monkeypatch, "playlists-overview-mounted")
    monkeypatch.setattr(
        playlists,
        "build_playlist_overview_rows",
        lambda include_hidden=False, *, record_activity=True: (
            [{"code": "KovaaKsTestCode", "hidden": True}] if include_hidden else []
        ),
    )

    rows, status, *_ = playlists.load_playlist_overview_rows(True, False, None, 0, 0)

    assert rows == []
    assert status == 'All playlists are hidden. Toggle "Show hidden" to manage them.'


def test_playlists_overview_name_column_uses_link_renderer():
    columns = {column["field"]: column for column in playlists.TABLE_COLUMN_DEFS}

    assert columns["name"]["cellRenderer"] == "PlaylistNameLink"


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


def test_playlists_overview_layout_includes_page_title():
    page = playlists.layout()
    titles = [
        component
        for component in _walk_components(page)
        if isinstance(component, dmc.Title)
    ]

    assert len(titles) == 1
    assert titles[0].children == "Playlists"
    assert titles[0].order == 2


def test_playlists_overview_layout_includes_show_hidden_switch_and_row_muting():
    page = playlists.layout()
    grid = page.children[-1]
    switch = next(
        component
        for component in _walk_components(page)
        if getattr(component, "id", None) == "playlists-overview-show-hidden"
    )

    assert switch.checked is False
    # The toggle is remembered across visits (localStorage) so the management
    # view stays how the user left it.
    assert switch.persistence is True
    assert grid.rowClassRules == {
        "playlist-overview-row-hidden": "params.data.hidden",
    }


def test_playlists_overview_layout_includes_quick_filter_input():
    page = playlists.layout()
    quick_filter = next(
        component
        for component in _walk_components(page)
        if getattr(component, "id", None) == "playlists-overview-quick-filter"
    )
    sink_ids = {getattr(child, "id", None) for child in page.children}

    assert quick_filter.placeholder == "Filter playlists..."
    # The client-side callback needs a sink store to output into.
    assert "playlists-overview-quick-filter-sink" in sink_ids


def test_import_playlist_shows_the_canonical_stored_code(monkeypatch):
    _trigger(monkeypatch, "playlists-import-button")
    # KovaaK's canonicalizes pasted codes; the stored code is what visibility
    # must persist, or a non-canonical paste imports hidden once a
    # preferences file exists.
    monkeypatch.setattr(
        playlists,
        "load_playlist_from_code",
        lambda _code: (None, "CanonicalCode"),
    )
    shown = []
    enqueued = []
    monkeypatch.setattr(playlists, "show_playlist", shown.append)
    monkeypatch.setattr(
        playlists,
        "enqueue_playlist_percentile_warmup",
        enqueued.append,
    )

    notifications, import_refresh, opened, value = playlists.import_playlist(
        1, "  canonicalcode  ", 0
    )

    assert shown == ["CanonicalCode"]
    assert enqueued == ["CanonicalCode"]
    assert notifications[0]["color"] == "green"
    # A successful import bumps the refresh store so the grid rebuilds, then
    # closes the modal and clears the field so the user sees the new row.
    assert import_refresh == 1
    assert opened is False
    assert value == ""


def test_import_playlist_ignores_phantom_initial_fire(monkeypatch):
    _trigger(monkeypatch, None)
    monkeypatch.setattr(
        playlists,
        "load_playlist_from_code",
        lambda _code: pytest.fail("phantom initial fire must not import"),
    )

    result = playlists.import_playlist(None, "KovaaKsTestCode", 2)

    assert result == (no_update, no_update, no_update, no_update)


def test_import_playlist_failure_does_not_show(monkeypatch):
    _trigger(monkeypatch, "playlists-import-button")
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
    _trigger(monkeypatch, "playlists-import-button")
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
    _trigger(monkeypatch, "playlists-import-button")
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
        lambda include_hidden=False, *, record_activity=True: [
            {"code": "KovaaKsTestCode"}
        ],
    )

    rows, status, *_ = playlists.load_playlist_overview_rows(True, False, None, 1, 0)

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
    # Regression: a 110px floor ellipsized the BENCHMARK pill when autoSize
    # ran against a not-yet-loaded grid.
    assert columns["type_display"]["minWidth"] == 140


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


def test_playlists_overview_header_tooltips_cover_exactly_the_cryptic_columns():
    # Pin the exact set so adding a column forces a conscious tooltip decision.
    fields_with_header_tooltip = {
        column["field"]
        for column in playlists.TABLE_COLUMN_DEFS
        if "headerTooltip" in column
    }

    assert fields_with_header_tooltip == {
        "type_display",
        "played_sort",
        "median_percentile_sort",
        "lowest_percentile_sort",
    }


def test_playlists_overview_percentile_header_tooltips_explain_resolution_gate():
    columns = {column["field"]: column for column in playlists.TABLE_COLUMN_DEFS}

    for field in ["median_percentile_sort", "lowest_percentile_sort"]:
        assert "once every played scenario" in columns[field]["headerTooltip"]


def test_playlists_overview_percentile_placeholders_are_dimmed_and_explained():
    columns = {column["field"]: column for column in playlists.TABLE_COLUMN_DEFS}

    for field in ["median_percentile_sort", "lowest_percentile_sort"]:
        column = columns[field]
        cell_class = column["cellClass"]["function"]
        assert "percentile_aggregates_resolved" in cell_class
        assert "playlist-overview-percentile-placeholder" in cell_class
        tooltip = column["tooltipValueGetter"]["function"]
        assert "played_count" in tooltip
        assert "open the playlist to fetch now" in tooltip

    assert columns["median_percentile_sort"]["cellClass"] == {
        "function": playlists.PERCENTILE_CELL_CLASS
    }
    assert columns["lowest_percentile_sort"]["cellClass"] == {
        "function": playlists.LOWEST_PERCENTILE_CELL_CLASS
    }

    assert columns["median_percentile_sort"]["tooltipValueGetter"] == {
        "function": playlists.PERCENTILE_TOOLTIP
    }
    assert columns["lowest_percentile_sort"]["tooltipValueGetter"] == {
        "function": playlists.LOWEST_PERCENTILE_TOOLTIP
    }


def test_playlists_overview_lowest_percentile_values_signal_their_tooltip():
    # The "Lowest: <scenario>" detail is hover-only, so a resolved value must
    # carry the dotted-underline affordance — otherwise nobody knows to hover.
    assert playlists.LOWEST_PERCENTILE_CELL_CLASS == (
        "params.data.percentile_aggregates_resolved"
        " ? (params.value == null ? null : 'cell-tooltip-affordance')"
        " : 'playlist-overview-percentile-placeholder'"
    )


def test_playlists_overview_visibility_column_has_reversibility_tooltip():
    columns = {column["field"]: column for column in playlists.TABLE_COLUMN_DEFS}

    assert columns[playlists.VISIBILITY_COLUMN_ID]["tooltipValueGetter"] == {
        "function": playlists.VISIBILITY_TOOLTIP
    }


def test_playlists_overview_grid_rows_navigate_by_playlist_code():
    page = playlists.layout()
    grid = page.children[-1]

    assert grid.dashGridOptions["getRowId"] == {"function": "params.data.code"}
    assert grid.dashGridOptions["tooltipShowDelay"] == 0
    assert grid.dangerously_allow_code is True


def test_playlists_overview_grid_uses_bounded_viewport_layout():
    page = playlists.layout()
    grid = page.children[-1]

    assert page.style == {
        "height": (
            "calc(100dvh - var(--app-shell-header-offset, 0rem) "
            "- 2*var(--app-shell-padding, 1rem))"
        )
    }
    assert grid.style == {
        "flex": 1,
        "height": "100%",
        "width": "100%",
        "minHeight": 300,
    }
    assert not any(isinstance(component, dcc.Loading) for component in page.children)
    assert grid.columnSize == "autoSize"
    assert grid.columnSizeOptions == playlists.COLUMN_SIZE_OPTIONS


def test_playlists_overview_grid_has_no_initial_row_data():
    grid = playlists.layout().children[-1]

    assert "rowData" not in grid.to_plotly_json()["props"]


def test_playlists_overview_layout_includes_relative_time_refresh_interval():
    page = playlists.layout()
    children_by_id = {getattr(child, "id", None): child for child in page.children}

    interval = children_by_id["playlists-overview-relative-time-interval"]

    assert "playlists-overview-relative-time-refresh" in children_by_id
    assert interval.interval == 30_000
    assert interval.n_intervals == 0


def test_playlists_overview_layout_includes_enable_only_warmup_interval():
    page = playlists.layout()
    children_by_id = {getattr(child, "id", None): child for child in page.children}

    interval = children_by_id["playlists-overview-warmup-interval"]

    assert "playlists-overview-warmup-generation" in children_by_id
    assert interval.interval == playlists.WARMUP_REFRESH_INTERVAL_MS
    assert interval.n_intervals == 0
    assert interval.disabled is True


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


def test_aim_training_journey_playlist_picker_shares_home_scroll_and_height():
    picker = next(
        component
        for component in _walk_components(aim_training_journey.layout())
        if getattr(component, "id", None) == "playlists-multi-select"
    )

    # Adopted from the Home filter via the shared preset so the two dropdowns
    # scroll and cap height consistently once the library grows past a screen.
    assert picker.scrollAreaProps == {"type": "always"}
    assert picker.maxDropdownHeight == "75vh"


def test_aim_training_journey_layout_uses_graph_placeholder():
    graph = next(
        component
        for component in _walk_components(aim_training_journey.layout())
        if getattr(component, "id", None) == "aim-training-journey-graph"
    )

    assert not graph.figure.layout.annotations
    assert graph.figure.layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert graph.figure.layout.plot_bgcolor == "rgba(0,0,0,0)"
    assert graph.figure.layout.xaxis.visible is False
    assert graph.figure.layout.yaxis.visible is False
    assert graph.figure.layout.dragmode is False


def test_aim_training_journey_no_selection_returns_themed_empty_state(monkeypatch):
    dmc.add_figure_templates()
    monkeypatch.setattr(
        aim_training_journey,
        "filter_known_playlist_codes",
        lambda _selected_playlists: [],
    )

    for selected_playlists in (None, ["Unknown playlist"]):
        figure = aim_training_journey.generate_graph(
            selected_playlists,
            10,
            "dark",
        )

        assert figure.layout.annotations[0].text == "<b>No playlists selected</b>"
        assert figure.layout.annotations[1].text == (
            "Choose one or more playlists to compare progress."
        )
        assert figure.layout.template.layout.paper_bgcolor == "#242424"


def test_aim_training_journey_missing_checkpoint_returns_themed_empty_state(
    monkeypatch,
):
    dmc.add_figure_templates()
    monkeypatch.setattr(
        aim_training_journey,
        "filter_known_playlist_codes",
        lambda selected_playlists: selected_playlists,
    )

    figure = aim_training_journey.generate_graph(["Playlist"], None, "light")

    assert figure.layout.annotations[0].text == "<b>Graph settings incomplete</b>"
    assert figure.layout.annotations[1].text == (
        "Choose a Checkpoint Hour value to plot progress."
    )
    assert figure.layout.template.layout.paper_bgcolor == "#ffffff"


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
            "href": playlist_scenarios.scenario_home_href("First", "KovaaKsTestCode"),
        }
    ]
    monkeypatch.setattr(data_service, "playlist_database", {playlist.code: playlist})

    def fake_build_rows(playlist_code, generation_token):
        assert playlist_code == "KovaaKsTestCode"
        assert generation_token == "generation-1"
        return expected_rows

    monkeypatch.setattr(
        playlist_scenarios,
        "build_playlist_scenario_rank_rows",
        fake_build_rows,
    )
    monkeypatch.setattr(
        playlist_scenarios,
        "uuid4",
        lambda: SimpleNamespace(hex="generation-1"),
    )
    monkeypatch.setattr(
        playlist_scenarios,
        "start_playlist_scenario_fill",
        lambda code, token: code == "KovaaKsTestCode" and token == "generation-1",
    )

    rows, status, generation, disabled = playlist_scenarios.load_playlist_scenario_rows(
        "KovaaKsTestCode"
    )

    assert rows == expected_rows
    # Each row gains an anchor href for the ScenarioLink renderer.
    assert rows[0]["href"] == playlist_scenarios.scenario_home_href(
        "First", "KovaaKsTestCode"
    )
    assert status == "Updating positions from KovaaK's… 0/1"
    assert generation == "generation-1"
    assert disabled is False
    assert playlist_scenarios.layout("KovaaKsTestCode") is not None


def test_playlist_scenarios_row_href_encodes_scenario_with_space(monkeypatch):
    playlist = PlaylistData(
        name="Voltaic Benchmarks",
        code="KovaaKsTestCode",
        scenarios=[Scenario(name="VT Pasu Air")],
    )
    monkeypatch.setattr(data_service, "playlist_database", {playlist.code: playlist})
    monkeypatch.setattr(
        playlist_scenarios,
        "build_playlist_scenario_rank_rows",
        lambda _code, _token: [
            {
                "scenario": "VT Pasu Air",
                "href": playlist_scenarios.scenario_home_href(
                    "VT Pasu Air", "KovaaKsTestCode"
                ),
            }
        ],
    )
    monkeypatch.setattr(
        playlist_scenarios, "start_playlist_scenario_fill", lambda *_args: True
    )

    rows, _status, _generation, _disabled = (
        playlist_scenarios.load_playlist_scenario_rows("KovaaKsTestCode")
    )

    assert rows[0]["href"] == "/?playlist_code=KovaaKsTestCode&scenario=VT+Pasu+Air"


def test_playlist_scenarios_layout_includes_quick_filter_input():
    page = playlist_scenarios.layout("KovaaKsTestCode")
    quick_filter = next(
        component
        for component in _walk_components(page)
        if getattr(component, "id", None) == "playlist-scenarios-quick-filter"
    )
    sink_ids = {getattr(child, "id", None) for child in page.children}

    assert quick_filter.placeholder == "Filter scenarios..."
    # The client-side callback needs a sink store to output into.
    assert "playlist-scenarios-quick-filter-sink" in sink_ids


def _text_content(component):
    return "".join(
        str(child.children)
        for child in _walk_components(component)
        if isinstance(child, (dmc.Title, dmc.Text)) and isinstance(child.children, str)
    )


def test_playlist_scenarios_header_shows_display_label_and_code(monkeypatch):
    monkeypatch.setattr(
        playlist_scenarios,
        "get_playlist_display_label",
        lambda code: f"Voltaic Benchmarks ({code})",
    )

    page = playlist_scenarios.layout("KovaaKsTestCode")
    header_text = _text_content(page)

    assert "Voltaic Benchmarks (KovaaKsTestCode)" in header_text
    assert "KovaaKsTestCode" in header_text


def test_playlist_scenarios_layout_without_code_renders_no_header(monkeypatch):
    monkeypatch.setattr(
        playlist_scenarios,
        "get_playlist_display_label",
        lambda _code: pytest.fail("no header must be rendered without a playlist code"),
    )

    page = playlist_scenarios.layout(None)
    titles = [
        component
        for component in _walk_components(page)
        if isinstance(component, dmc.Title)
    ]

    assert titles == []


def test_playlist_scenarios_page_title_carries_label_for_known_code(monkeypatch):
    monkeypatch.setattr(
        playlist_scenarios,
        "get_playlist_display_label",
        lambda code: f"Voltaic Benchmarks ({code})",
    )

    assert (
        playlist_scenarios._page_title("KovaaKsTestCode")
        == "Voltaic Benchmarks (KovaaKsTestCode) - Playlist Scenarios"
    )


def test_playlist_scenarios_page_title_falls_back_without_code(monkeypatch):
    monkeypatch.setattr(
        playlist_scenarios,
        "get_playlist_display_label",
        lambda _code: pytest.fail("falsy code must not reach the label lookup"),
    )

    assert playlist_scenarios._page_title() == "Playlist Scenarios"
    assert playlist_scenarios._page_title(None) == "Playlist Scenarios"


def test_playlist_scenarios_page_handles_unknown_playlist(monkeypatch):
    monkeypatch.setattr(data_service, "playlist_database", {})

    rows, status, generation, disabled = playlist_scenarios.load_playlist_scenario_rows(
        "MissingCode"
    )

    assert rows == []
    assert status == "Playlist code is not imported: MissingCode"
    assert generation is None
    assert disabled is True


def test_playlist_scenarios_page_handles_missing_playlist_code():
    rows, status, generation, disabled = playlist_scenarios.load_playlist_scenario_rows(
        None
    )

    assert rows == []
    assert status == "Select a playlist from the Playlists page."
    assert generation is None
    assert disabled is True


def test_playlist_fill_registration_race_clears_pending_cells(monkeypatch):
    playlist = PlaylistData(
        name="Voltaic Benchmarks",
        code="KovaaKsTestCode",
        scenarios=[Scenario(name="First")],
    )
    monkeypatch.setattr(data_service, "playlist_database", {playlist.code: playlist})
    monkeypatch.setattr(
        playlist_scenarios,
        "build_playlist_scenario_rank_rows",
        lambda _code, _token: [
            {
                "scenario": "First",
                "rank_pending": True,
                "total_pending": True,
                "percentile_pending": True,
            }
        ],
    )
    monkeypatch.setattr(
        playlist_scenarios,
        "start_playlist_scenario_fill",
        lambda *_args: False,
    )

    rows, status, generation, disabled = playlist_scenarios.load_playlist_scenario_rows(
        playlist.code
    )

    assert rows[0]["rank_pending"] is False
    assert rows[0]["total_pending"] is False
    assert rows[0]["percentile_pending"] is False
    assert status == "Update interrupted"
    assert generation is None
    assert disabled is True


def _fill_drain(
    *,
    terminal="complete",
    consuming=True,
    updates=None,
    done=3,
    unknown=0,
    stale=0,
    total=3,
):
    return playlist_scenarios.PlaylistScenarioFillDrain(
        generation_token="generation-1",
        updates=updates or [],
        done_count=done,
        unknown_count=unknown,
        stale_count=stale,
        total=total,
        terminal=terminal,
        consuming_terminal=consuming,
    )


def test_playlist_fill_drain_guards_phantom_initial_call(monkeypatch):
    monkeypatch.setattr(
        playlist_scenarios,
        "drain_playlist_scenario_fill",
        lambda _token: pytest.fail("missing tokens must not touch the registry"),
    )

    result = playlist_scenarios.drain_playlist_scenario_rows(0, None)

    assert result == (no_update, no_update, no_update)


def test_playlist_fill_terminal_one_shots_run_once_and_status_reasserts(
    monkeypatch,
):
    consuming = _fill_drain(
        updates=[{"scenario": "First"}],
        unknown=1,
        stale=1,
    )
    post_consumption = _fill_drain(
        consuming=False,
        unknown=1,
        stale=1,
    )
    drains = iter([consuming, post_consumption])
    monkeypatch.setattr(
        playlist_scenarios,
        "drain_playlist_scenario_fill",
        lambda _token: next(drains),
    )

    first = playlist_scenarios.drain_playlist_scenario_rows(1, "generation-1")
    second = playlist_scenarios.drain_playlist_scenario_rows(2, "generation-1")

    assert first[0] == {"update": [{"scenario": "First"}]}
    assert first[1] == (
        "1 of 3 positions unavailable · 1 from cache — KovaaK's unreachable"
    )
    assert first[2][0]["color"] == "red"
    assert first[2][0]["message"] == (
        "Couldn't update 1 of 3 positions; 1 more served from cache"
    )
    assert second[0] is no_update
    assert second[1] == first[1]
    assert second[2] is no_update


def test_playlist_fill_stale_only_is_yellow_and_clean_is_silent():
    stale = playlist_scenarios._fill_summary_notification(_fill_drain(stale=2))
    clean = playlist_scenarios._fill_summary_notification(_fill_drain())

    assert stale[0]["color"] == "yellow"
    assert stale[0]["message"] == (
        "2 of 3 positions served from cache — KovaaK's was unreachable"
    )
    assert clean is no_update


def test_playlist_fill_cancelled_tick_finalizes_without_toast(monkeypatch):
    cancelled = _fill_drain(
        terminal="cancelled",
        updates=[
            {
                "scenario": "First",
                "rank_pending": False,
                "total_pending": False,
                "percentile_pending": False,
            }
        ],
        done=1,
        total=3,
    )
    monkeypatch.setattr(
        playlist_scenarios,
        "drain_playlist_scenario_fill",
        lambda _token: cancelled,
    )

    transaction, status, notification = playlist_scenarios.drain_playlist_scenario_rows(
        1, "generation-1"
    )

    assert transaction == {"update": cancelled.updates}
    assert status == "Update interrupted · 1 of 3 refreshed"
    assert notification is no_update


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
    grid = playlist_scenarios.layout("KovaaKsTestCode").children[-1]

    assert column["cellClass"] == {
        "function": "params.value == null ? null : 'cell-tooltip-affordance'"
    }
    assert column["tooltipValueGetter"] == {
        "function": (
            "params.value == null ? null : absoluteTime(params.value, 'Never')"
        )
    }
    assert grid.dashGridOptions["tooltipShowDelay"] == 0


def test_playlist_scenarios_rank_columns_use_explicit_pending_flags():
    columns = {
        column["field"]: column for column in playlist_scenarios.TABLE_COLUMN_DEFS
    }

    assert columns["rank_sort"]["valueFormatter"] == {
        "function": "params.data.rank_pending ? '' : params.data.rank_display"
    }
    assert columns["rank_sort"]["cellClass"] == {
        "function": "params.data.rank_pending ? 'playlist-rank-pending' : null"
    }
    assert "total_pending" in columns["total_sort"]["valueFormatter"]["function"]
    assert (
        "percentile_pending" in columns["percentile_sort"]["valueFormatter"]["function"]
    )


def test_playlist_scenarios_table_includes_personal_best_metadata_columns():
    columns = {
        column["field"]: column for column in playlist_scenarios.TABLE_COLUMN_DEFS
    }

    assert columns["pb_cm360_sort"]["headerName"] == "PB cm/360"
    assert columns["pb_accuracy_sort"]["headerName"] == "PB Accuracy"


def test_playlist_scenarios_header_tooltips_cover_exactly_the_jargon_columns():
    # Pin the exact set so adding a column forces a conscious tooltip decision.
    fields_with_header_tooltip = {
        column["field"]
        for column in playlist_scenarios.TABLE_COLUMN_DEFS
        if "headerTooltip" in column
    }

    assert fields_with_header_tooltip == {"percentile_sort", "pb_cm360_sort"}


def test_playlist_scenarios_grid_uses_content_auto_size():
    page = playlist_scenarios.layout("KovaaKsTestCode")
    ag_grid = page.children[-1]

    assert ag_grid.columnSize == "autoSize"
    assert ag_grid.columnSizeOptions == playlist_scenarios.COLUMN_SIZE_OPTIONS


def test_playlist_scenarios_grid_has_no_initial_row_data():
    ag_grid = playlist_scenarios.layout("KovaaKsTestCode").children[-1]

    assert "rowData" not in ag_grid.to_plotly_json()["props"]


def test_playlist_scenarios_grid_uses_bounded_viewport_layout():
    page = playlist_scenarios.layout("KovaaKsTestCode")
    ag_grid = page.children[-1]

    assert page.style == {
        "height": (
            "calc(100dvh - var(--app-shell-header-offset, 0rem) "
            "- 2*var(--app-shell-padding, 1rem))"
        )
    }
    assert "domLayout" not in ag_grid.dashGridOptions
    assert ag_grid.style == {
        "flex": 1,
        "height": "100%",
        "width": "100%",
        "minHeight": 300,
    }
    assert ag_grid.dashGridOptions["getRowId"] == {
        "function": ("params.data.generation_token + ':' + params.data.playlist_order")
    }


def test_playlist_scenarios_layout_includes_relative_time_refresh_interval():
    page = playlist_scenarios.layout("KovaaKsTestCode")
    children_by_id = {getattr(child, "id", None): child for child in page.children}

    interval = children_by_id["playlist-scenarios-relative-time-interval"]

    assert "playlist-scenarios-relative-time-refresh" in children_by_id
    assert interval.interval == 30_000
    assert interval.n_intervals == 0


def test_playlist_scenarios_layout_includes_enable_only_fill_interval():
    page = playlist_scenarios.layout("KovaaKsTestCode")
    children_by_id = {getattr(child, "id", None): child for child in page.children}

    interval = children_by_id["playlist-scenarios-fill-interval"]

    assert "playlist-scenarios-generation" in children_by_id
    assert interval.interval == 1_000
    assert interval.n_intervals == 0
    assert interval.disabled is True


def test_playlist_scenarios_scenario_column_fills_remaining_width():
    column = next(
        column
        for column in playlist_scenarios.TABLE_COLUMN_DEFS
        if column["field"] == "scenario"
    )

    assert column["flex"] == 1
    assert column["maxWidth"] == 400
    # Link styling now rides on the anchor the renderer emits, not the cell.
    assert column["cellRenderer"] == "ScenarioLink"
    assert "cellClass" not in column
    assert "scenario" not in playlist_scenarios.AUTO_SIZE_COLUMN_KEYS
