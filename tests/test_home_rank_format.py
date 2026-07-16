import os
from datetime import datetime
from types import SimpleNamespace

import dash
import dash_mantine_components as dmc
import pytest
from dash import dcc, no_update

from source.kovaaks import api_service, data_service
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402

format_scenario_rank = home.format_scenario_rank


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


def test_home_playlist_filter_dropdown_scrollbar_is_always_visible(monkeypatch):
    monkeypatch.setattr(
        home,
        "get_visible_playlist_selector_options",
        lambda: [{"label": "Voltaic Benchmarks", "value": "KovaaKsTestCode"}],
    )
    monkeypatch.setattr(home, "get_unique_scenarios", lambda *_args: ["1wall6targets"])

    playlist_filter = next(
        component
        for component in _walk_components(home.layout())
        if getattr(component, "id", None) == "playlist-dropdown-selection"
    )

    assert playlist_filter.scrollAreaProps == {"type": "always"}
    assert playlist_filter.persistence is True


def test_home_layout_initializes_from_playlist_scenario_query(monkeypatch):
    monkeypatch.setattr(
        home,
        "get_visible_playlist_selector_options",
        lambda: [{"label": "Voltaic Benchmarks", "value": "KovaaKsTestCode"}],
    )
    monkeypatch.setattr(
        home,
        "get_playlist_by_code",
        lambda code: object() if code == "KovaaKsTestCode" else None,
    )
    monkeypatch.setattr(
        home,
        "get_scenarios_from_playlist_code",
        lambda code: [f"{code} Scenario"],
    )
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: ["All"])

    page = home.layout(
        scenario="KovaaKsTestCode Scenario",
        playlist_code="KovaaKsTestCode",
    )
    components = list(_walk_components(page))
    playlist_filter = next(
        component
        for component in components
        if getattr(component, "id", None) == "playlist-dropdown-selection"
    )
    scenario_dropdown = next(
        component
        for component in components
        if getattr(component, "id", None) == "scenario-dropdown-selection"
    )

    assert playlist_filter.value == "KovaaKsTestCode"
    assert playlist_filter.persistence is False
    assert scenario_dropdown.data == ["KovaaKsTestCode Scenario"]
    assert scenario_dropdown.value == "KovaaKsTestCode Scenario"
    assert scenario_dropdown.persistence is False


def test_home_top_n_input_uses_compact_width(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])

    page = home.layout()
    top_n_scores = next(
        component
        for component in _walk_components(page)
        if getattr(component, "id", None) == "top_n_scores"
    )
    controls_flex = next(
        component
        for component in _walk_components(page)
        if isinstance(component, dmc.Flex)
        and any(
            getattr(child, "id", None) == "top_n_scores" for child in component.children
        )
    )

    assert top_n_scores.w == "8rem"
    assert getattr(top_n_scores, "placeholder", None) is None
    assert controls_flex.gap == "sm"
    assert controls_flex.wrap == "wrap"


def test_home_last_played_initial_state_has_no_tooltip_affordance(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])

    components = list(_walk_components(home.layout()))
    last_played = next(
        component
        for component in components
        if getattr(component, "id", None) == "scenario_datetime_last_played"
    )
    tooltip = next(
        component
        for component in components
        if getattr(component, "id", None) == "last-played-tooltip"
    )

    assert last_played.children == "—"
    assert getattr(last_played, "style", None) is None
    assert getattr(last_played, "className", None) is None
    assert getattr(last_played, "tabIndex", None) is None
    assert tooltip.disabled is True
    assert tooltip.label == ""
    assert tooltip.events == home.TOOLTIP_EVENTS


def test_startup_playlist_warnings_flush_after_mount_and_drain_once():
    data_service.playlist_startup_warning_queue.clear()
    warnings = ["First warning", "Second warning"]
    data_service.playlist_startup_warning_queue.extend(warnings)

    notifications = home.flush_startup_playlist_warnings(1)

    assert [notification["message"] for notification in notifications] == warnings
    assert home.flush_startup_playlist_warnings(2) is dash.no_update


def test_home_select_playlist_ignores_stale_persisted_names(monkeypatch):
    monkeypatch.setattr(
        home,
        "get_playlist_by_code",
        lambda code: object() if code == "ValidCode" else None,
    )
    monkeypatch.setattr(
        home,
        "get_scenarios_from_playlist_code",
        lambda code: [f"{code} Scenario"],
    )
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: ["All"])

    assert home.select_playlist("Old Playlist Name") == ["All"]
    assert home.select_playlist("ValidCode") == ["ValidCode Scenario"]


def test_home_section_titles_keep_visual_size_with_accessible_heading_order(
    monkeypatch,
):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])

    titles = {
        component.children: component
        for component in _walk_components(home.layout())
        if isinstance(component, dmc.Title)
    }

    assert titles["Scenario Stats"].order == 2
    assert titles["Scenario Stats"].size == "h6"
    assert titles["Display Settings"].order == 2
    assert titles["Display Settings"].size == "h4"


def test_settings_modal_controls_have_help_tooltips(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])

    components = {
        getattr(component, "id", None): component
        for component in _walk_components(home.layout())
    }
    expected_settings = {
        "automatically-change-scenario-switch": "automatically-change-scenario",
        "rank-overlay-switch": "rank-overlay",
        "high-score-overlay-switch": "high-score-overlay",
        "score-threshold-overlay-switch": "score-threshold-overlay",
        "score-threshold-percentage": "score-threshold-percentage",
        "score-threshold-notification-switch": "score-threshold-notification",
        "top_n_scores": "top-n-scores",
    }

    for component_id, help_key in expected_settings.items():
        label = components[component_id].label
        tooltips = [
            component
            for component in _walk_components(label)
            if isinstance(component, dmc.Tooltip)
        ]

        assert len(tooltips) == 1
        assert tooltips[0].label == home.SETTINGS_HELP_TEXT[help_key]
        assert tooltips[0].events == home.TOOLTIP_EVENTS
        assert tooltips[0].withArrow is True
        assert tooltips[0].multiline is True

    score_threshold_percentage = components["score-threshold-percentage"]
    assert score_threshold_percentage.min == 1


def test_rank_refresh_button_has_tooltip(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])

    tooltips = [
        component
        for component in _walk_components(home.layout())
        if isinstance(component, dmc.Tooltip)
        and any(
            getattr(child, "id", None) == "rank-refresh-button"
            for child in _walk_components(component.children)
        )
    ]

    assert len(tooltips) == 1
    assert tooltips[0].label == home.RANK_REFRESH_TOOLTIP
    assert tooltips[0].events == home.TOOLTIP_EVENTS
    assert tooltips[0].withArrow is True
    assert tooltips[0].multiline is True


def test_get_scenario_num_runs_without_selection():
    assert home.get_scenario_num_runs(None, None) == (
        0,
        None,
        "—",
        "",
        None,
        None,
        True,
    )


def test_get_scenario_num_runs_without_play_data(monkeypatch):
    monkeypatch.setattr(home, "is_scenario_in_database", lambda _scenario: False)

    assert home.get_scenario_num_runs(None, "Unplayed Scenario") == (
        0,
        None,
        "Never",
        "",
        None,
        None,
        True,
    )


def test_get_scenario_num_runs_with_play_data(monkeypatch):
    last_played = datetime(2026, 6, 30, 9, 5, 4)
    scenario_stats = SimpleNamespace(
        number_of_runs=12,
        date_last_played=last_played,
    )
    monkeypatch.setattr(home, "is_scenario_in_database", lambda _scenario: True)
    monkeypatch.setattr(home, "get_scenario_stats", lambda _scenario: scenario_stats)

    assert home.get_scenario_num_runs(None, "Played Scenario") == (
        12,
        last_played.timestamp(),
        "Never",
        "Jun 30, 2026, 9:05 AM",
        "last-played-affordance",
        0,
        False,
    )


def test_format_scenario_rank_with_total_players():
    rank_info = ScenarioRankInfo(
        status=ScenarioRankStatus.RANKED,
        rank=11266,
        total_players=18342,
        percentile=38.58,
    )

    assert format_scenario_rank(rank_info) == "11,266 of 18,342 (38.58% Percentile)"


def test_format_scenario_rank_without_total_players():
    rank_info = ScenarioRankInfo(
        status=ScenarioRankStatus.RANKED,
        rank=11266,
    )

    assert format_scenario_rank(rank_info) == "11,266"


def test_format_scenario_rank_unranked_with_total_players():
    rank_info = ScenarioRankInfo(
        status=ScenarioRankStatus.UNRANKED,
        total_players=63870,
    )

    assert format_scenario_rank(rank_info) == "Unranked (63,870 players)"


def test_format_scenario_rank_unranked_and_unknown():
    assert (
        format_scenario_rank(ScenarioRankInfo(status=ScenarioRankStatus.UNRANKED))
        == "Unranked"
    )
    assert (
        format_scenario_rank(ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN))
        == "N/A"
    )


def test_get_scenario_rank_queries_kovaaks_for_unplayed_local_scenario(monkeypatch):
    queried_scenarios = []

    def fail_is_scenario_in_database(*_args, **_kwargs):
        raise AssertionError("rank lookup should not require local scenario data")

    def fake_get_scenario_rank_info(selected_scenario, *_args, **kwargs):
        queried_scenarios.append((selected_scenario, kwargs["allow_network"]))
        return ScenarioRankInfo(
            status=ScenarioRankStatus.UNRANKED,
            total_players=54702,
        )

    monkeypatch.setattr(home, "is_scenario_in_database", fail_is_scenario_in_database)
    monkeypatch.setattr(home, "get_scenario_rank_info", fake_get_scenario_rank_info)

    assert home._render_scenario_rank("Unplayed Scenario", allow_network=True) == (
        "Unranked (54,702 players)"
    )
    assert queried_scenarios == [("Unplayed Scenario", True)]


def test_rank_trigger_classification_preserves_initial_and_cofired_network_reads():
    interval = {"prop_id": "interval-component.n_intervals"}

    assert home._rank_allows_network([{"prop_id": "."}]) is True
    assert home._rank_allows_network([interval]) is False
    assert (
        home._rank_allows_network(
            [
                interval,
                {"prop_id": "scenario-dropdown-selection.value"},
            ]
        )
        is True
    )


@pytest.mark.parametrize(
    ("total_state", "expected"),
    [
        ("missing", "10"),
        ("expired", "10 of 100 (90.50% Percentile)"),
    ],
)
def test_interval_rank_render_is_ttl_independent_and_never_fetches(
    monkeypatch,
    tmp_path,
    total_state,
    expected,
):
    scenario_name = "Cached Scenario"
    leaderboard_id = 98330
    username = "MingoDynasty"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(home.get_config(), "kovaaks_username", username)
    monkeypatch.setattr(home.get_config(), "steam_id", None)
    api_service.make_cache()
    api_service.save_leaderboard_id(scenario_name, leaderboard_id, "test")
    api_service.save_scenario_rank(
        leaderboard_id,
        username,
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=10,
            leaderboard_id=leaderboard_id,
            scenario_name=scenario_name,
            score=100.0,
        ),
    )
    rank_cache_file = api_service._rank_cache_file(leaderboard_id, username)
    os.utime(rank_cache_file, (1, 1))

    if total_state == "expired":
        api_service.save_leaderboard_total(leaderboard_id, 100)
        total_cache_file = api_service._leaderboard_total_cache_file(leaderboard_id)
        os.utime(total_cache_file, (1, 1))

    def fail_network(*_args, **_kwargs):
        raise AssertionError("interval rank reads must not use the network")

    monkeypatch.setattr(api_service, "_session_get", fail_network)

    assert home._render_scenario_rank(scenario_name, allow_network=False) == expected


def test_interval_rank_render_does_not_fetch_or_cache_unresolved_scenario(
    monkeypatch,
    tmp_path,
):
    scenario_name = "Local Custom Scenario"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(home.get_config(), "kovaaks_username", "MingoDynasty")
    api_service.make_cache()

    def fail_network(*_args, **_kwargs):
        raise AssertionError("unresolved interval rank reads must not use the network")

    monkeypatch.setattr(api_service, "_session_get", fail_network)

    assert home._render_scenario_rank(scenario_name, allow_network=False) == "N/A"
    assert api_service.get_cached_leaderboard_id(scenario_name) is None


def test_allow_network_false_short_circuits_resolution_and_rank_fetch(monkeypatch):
    cached_lookups = []

    def get_cached(scenario_name):
        cached_lookups.append(scenario_name)

    def fail_network_path(*_args, **_kwargs):
        raise AssertionError("cache-only lookup reached a network path")

    monkeypatch.setattr(api_service, "get_cached_leaderboard_id", get_cached)
    monkeypatch.setattr(
        api_service,
        "hydrate_leaderboard_id_cache",
        fail_network_path,
    )
    monkeypatch.setattr(api_service, "search_scenario_exact", fail_network_path)
    monkeypatch.setattr(api_service, "fetch_scenario_rank", fail_network_path)

    rank_info = api_service.get_scenario_rank_info(
        "Unresolved Scenario",
        "MingoDynasty",
        allow_network=False,
    )

    assert rank_info.status == ScenarioRankStatus.UNKNOWN
    assert cached_lookups == ["Unresolved Scenario"]


def test_interval_rank_render_does_not_retoast_derived_warning(
    monkeypatch,
    tmp_path,
):
    scenario_name = "Cached Scenario"
    leaderboard_id = 98330
    username = "MingoDynasty"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(home.get_config(), "kovaaks_username", username)
    monkeypatch.setattr(home.get_config(), "steam_id", "configured-steam-id")
    api_service.make_cache()
    api_service.save_leaderboard_id(scenario_name, leaderboard_id, "test")
    api_service.save_scenario_rank(
        leaderboard_id,
        username,
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=10,
            leaderboard_id=leaderboard_id,
            scenario_name=scenario_name,
            score=100.0,
            matched_steam_id="different-steam-id",
        ),
    )
    api_service.save_leaderboard_total(leaderboard_id, 100)

    warnings = []
    monkeypatch.setattr(home.dash_logger, "warning", warnings.append)

    assert (
        home._render_scenario_rank(scenario_name, allow_network=False)
        == "10 of 100 (90.50% Percentile)"
    )
    assert warnings == []

    assert (
        home._render_scenario_rank(scenario_name, allow_network=True)
        == "10 of 100 (90.50% Percentile)"
    )
    assert len(warnings) == 1


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        (
            ScenarioRankInfo(
                status=ScenarioRankStatus.RANKED,
                rank=25,
                leaderboard_id=98330,
                score=100.0,
            ),
            "25",
        ),
        (
            ScenarioRankInfo(
                status=ScenarioRankStatus.UNRANKED,
                leaderboard_id=98330,
            ),
            "Unranked",
        ),
    ],
)
def test_manual_rank_refresh_is_one_shot_and_authoritative(
    monkeypatch,
    tmp_path,
    candidate,
    expected,
):
    scenario_name = "Reset Scenario"
    leaderboard_id = 98330
    username = "MingoDynasty"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(home.get_config(), "kovaaks_username", username)
    monkeypatch.setattr(home.get_config(), "steam_id", None)
    api_service.make_cache()
    api_service.save_leaderboard_id(scenario_name, leaderboard_id, "test")
    api_service.save_scenario_rank(
        leaderboard_id,
        username,
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=5,
            leaderboard_id=leaderboard_id,
            scenario_name=scenario_name,
            score=110.0,
        ),
    )

    fetched = []

    def fetch_once(*_args):
        fetched.append(True)
        return candidate

    monkeypatch.setattr(api_service, "fetch_scenario_rank", fetch_once)
    monkeypatch.setattr(
        api_service,
        "get_user_scenario_total_play",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        api_service,
        "_with_leaderboard_total",
        lambda rank_info, _ttl: rank_info,
    )

    rank_text, notifications = home.refresh_rank(1, scenario_name)
    assert rank_text == expected
    # Any completed refresh — ranked or unranked — confirms with a green
    # toast; a fresh id per refresh so back-to-back clicks each confirm.
    assert notifications[0]["color"] == "green"
    assert scenario_name in notifications[0]["message"]
    assert notifications[0]["id"].startswith("rank-refresh-notification-")
    assert fetched == [True]
    stored = api_service._cached_rank(leaderboard_id, username)
    assert stored is not None
    assert stored.status == candidate.status
    assert stored.score == candidate.score


def test_manual_rank_refresh_always_surfaces_returned_messages(monkeypatch):
    calls = []
    warnings = []
    errors = []

    def get_rank(*_args, **kwargs):
        calls.append(kwargs)
        return ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            warning_message="Check the configured Steam ID.",
            error_message="Rank lookup failed.",
        )

    monkeypatch.setattr(home, "get_scenario_rank_info", get_rank)
    monkeypatch.setattr(home.dash_logger, "warning", warnings.append)
    monkeypatch.setattr(home.dash_logger, "error", errors.append)

    rank_text, notifications = home.refresh_rank(1, "Scenario")
    assert rank_text == "N/A"
    # The error already toasts red through dash_logger; a green "refreshed"
    # confirmation on top would be contradictory.
    assert notifications is no_update
    assert calls == [{"force_refresh": True}]
    assert warnings == ["Check the configured Steam ID."]
    assert errors == ["Rank lookup failed."]


def test_manual_rank_refresh_warning_suppresses_green_toast(monkeypatch):
    # A failed fetch served from stale cache returns a RANKED result carrying a
    # warning_message (yellow) but no error_message. The green "refreshed"
    # confirmation must not fire on top of it.
    warnings = []

    def get_rank(*_args, **_kwargs):
        return ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=50,
            leaderboard_id=1,
            scenario_name="Scenario",
            warning_message="Couldn't refresh from KovaaK's; showing the last "
            "cached position for Scenario.",
        )

    monkeypatch.setattr(home, "get_scenario_rank_info", get_rank)
    monkeypatch.setattr(home.dash_logger, "warning", warnings.append)

    rank_text, notifications = home.refresh_rank(1, "Scenario")
    assert notifications is no_update
    assert warnings and "last cached position" in warnings[0]
    assert rank_text != "N/A"


def test_manual_rank_refresh_ignores_initial_load_fire(monkeypatch):
    # Under DashProxy an allow_duplicate callback can fire once on page load
    # with n_clicks=None; that must not force a network refresh or toast.
    monkeypatch.setattr(
        home,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: pytest.fail(
            "an initial-load fire must not hit the network"
        ),
    )

    assert home.refresh_rank(None, "Scenario") == (no_update, no_update)


def test_manual_rank_refresh_without_scenario_skips_fetch_and_toast(monkeypatch):
    monkeypatch.setattr(
        home,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: pytest.fail(
            "a refresh without a scenario must not hit the network"
        ),
    )

    assert home.refresh_rank(1, None) == ("N/A", no_update)


def test_scenario_rank_loading_is_delayed_and_not_shown_initially(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])

    page = home.layout()
    rank_loading = next(
        (
            component
            for component in _walk_components(page)
            if isinstance(component, dcc.Loading)
            and getattr(component.children, "id", None) == "scenario_rank"
        ),
        None,
    )

    assert rank_loading is not None
    assert rank_loading.delay_show == home.SCENARIO_RANK_LOADING_DELAY_MS == 250
    assert rank_loading.show_initially is False

    refresh_button = next(
        component
        for component in _walk_components(page)
        if getattr(component, "id", None) == "rank-refresh-button"
    )
    assert refresh_button.children == "Refresh"
