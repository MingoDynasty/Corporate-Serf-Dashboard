import os
from datetime import datetime
from types import SimpleNamespace

import dash
import dash_mantine_components as dmc
import pytest
import requests
from dash import dcc, no_update
from dash._callback import GLOBAL_CALLBACK_LIST

from source.config import settings_service
from source.kovaaks import api_service, data_service
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus
from tests.rendered_text import rendered_text

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402

format_scenario_rank = home.format_scenario_rank


@pytest.fixture(autouse=True)
def _forget_rank_hints():
    """Keep the cross-tick hint memo from leaking between tests."""
    home._last_rank_hints.clear()
    yield
    home._last_rank_hints.clear()


@pytest.fixture(autouse=True)
def _forget_session_notices():
    """Give each test a fresh app session's worth of once-per-session toasts."""
    home._session_notices_sent.clear()
    yield
    home._session_notices_sent.clear()


def _rendered_rank(*args, **kwargs):
    """Render the Position value, discarding any toast the render earned."""
    display, _notifications = home._render_scenario_rank(*args, **kwargs)
    return display


class _RefreshClient:
    """One browser clicking Refresh, carrying the shell's channel registry."""

    def __init__(self) -> None:
        self.toast_channels: dict[str, str | None] = {}
        self.clicks = 0

    def click(self, scenario: str | None):
        """Return this click's (display, shown payloads, hidden ids)."""
        self.clicks += 1
        display, shown, hidden, patch = home.refresh_rank(
            self.clicks, scenario, self.toast_channels
        )
        self.toast_channels.update(_registry_writes(patch))
        return display, shown, hidden


def _registry_writes(patch) -> dict[str, str | None]:
    """Read a per-key ``dash.Patch`` as the assignments it will apply."""
    if patch is no_update:
        return {}
    return {
        operation["location"][0]: operation["params"]["value"]
        for operation in patch._operations
    }


def _rank_text(rendered) -> str:
    """Flatten a rendered Position value into the text a reader would see."""
    if isinstance(rendered, str):
        return rendered
    return "".join(
        component
        for child in rendered
        for component in _walk_components(child)
        if isinstance(component, str)
    )


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


def _layout_components(monkeypatch) -> dict:
    """Render Home without touching disk and index the tree by component id."""
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_scenario_names", lambda: [])

    return {
        getattr(component, "id", None): component
        for component in _walk_components(home.layout())
    }


def _label_text(component) -> str:
    """Flatten a control's label into the text a reader would see."""
    return "".join(
        part for part in _walk_components(component.label) if isinstance(part, str)
    )


# The chart options inspector's label-bearing inputs, with the defaults that
# must not move: Dash persistence is keyed by component id, and changing a
# layout default silently wipes every value the browser already stored under
# it. The Run Data Points controls answer to the same rule; they are covered in
# tests/test_home_point_appearance.py, where the rest of their behavior lives.
CHART_OPTIONS_INPUT_DEFAULTS = {
    "rank-overlay-switch": ("checked", True),
    "show-all-ranks-switch": ("checked", False),
    "high-score-overlay-switch": ("checked", True),
    "score-threshold-overlay-switch": ("checked", True),
    "score-threshold-percentage": ("value", 95),
    "score-threshold-notification-switch": ("checked", True),
    "run-notification-switch": ("checked", True),
}
COLLAPSED_PANEL_CLASS = (
    f"{home.CHART_OPTIONS_PANEL_CLASS} {home.CHART_OPTIONS_PANEL_HIDDEN_CLASS}"
)


def test_home_playlist_filter_dropdown_scrollbar_is_always_visible(monkeypatch):
    monkeypatch.setattr(
        home,
        "get_visible_playlist_selector_options",
        lambda: [{"label": "Voltaic Benchmarks", "value": "KovaaKsTestCode"}],
    )
    monkeypatch.setattr(home, "get_scenario_names", lambda: ["1wall6targets"])

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
    monkeypatch.setattr(home, "get_scenario_names", lambda: ["All"])

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
    deep_link_store = next(
        component
        for component in components
        if getattr(component, "id", None) == home.HOME_DEEP_LINK_STORE_ID
    )

    # The query parameters reach the dropdowns through the store, never as
    # the layout value: a persisted control's default has to be the same on
    # every visit or Dash discards the stored edit instead of restoring it.
    assert deep_link_store.data == {
        "playlist": "KovaaKsTestCode",
        "scenario": "KovaaKsTestCode Scenario",
    }
    assert playlist_filter.value is None
    assert playlist_filter.persistence is True
    assert scenario_dropdown.value is None
    assert scenario_dropdown.persistence is True
    # Still resolved in the layout, so the first paint already lists the
    # deep-linked playlist's scenarios.
    assert scenario_dropdown.data == ["KovaaKsTestCode Scenario"]


def _known_playlist(monkeypatch):
    monkeypatch.setattr(
        home,
        "get_playlist_by_code",
        lambda code: object() if code == "KovaaKsTestCode" else None,
    )


def test_home_deep_link_records_only_the_parameters_the_url_carried(monkeypatch):
    """An absent parameter leaves its control on the restored value."""
    _known_playlist(monkeypatch)

    assert home._home_deep_link(None, None) == {}
    assert home._home_deep_link("Scenario A", None) == {"scenario": "Scenario A"}
    assert home._home_deep_link(None, "KovaaKsTestCode") == {
        "playlist": "KovaaKsTestCode"
    }


def test_home_deep_link_clears_the_filter_for_an_unknown_playlist_code(monkeypatch):
    """The URL's selection is applied as given: no playlist means no filter."""
    _known_playlist(monkeypatch)

    assert home._home_deep_link(None, "KovaaKsGoneCode") == {"playlist": None}


def test_home_deep_link_treats_an_empty_scenario_as_no_scenario(monkeypatch):
    _known_playlist(monkeypatch)

    assert home._home_deep_link("", "KovaaKsTestCode") == {
        "playlist": "KovaaKsTestCode",
        "scenario": None,
    }


def test_apply_deep_link_writes_only_the_controls_the_url_named():
    assert home.apply_deep_link({}) == (no_update, no_update)
    assert home.apply_deep_link(None) == (no_update, no_update)
    assert home.apply_deep_link({"scenario": "Scenario A"}) == (
        no_update,
        "Scenario A",
    )
    assert home.apply_deep_link({"playlist": None}) == (None, no_update)
    assert home.apply_deep_link(
        {"playlist": "KovaaKsTestCode", "scenario": "Scenario A"}
    ) == ("KovaaKsTestCode", "Scenario A")


def test_apply_deep_link_is_a_second_writer_of_the_scenario_value():
    """It shares the scenario value with the run-event consumer.

    ``initial_duplicate`` rather than ``True``: applying the deep link is the
    mount's whole job, and Dash refuses an ``allow_duplicate`` output without
    one of the ``prevent_initial_call`` forms.
    """
    registration = _deep_link_registration()
    playlist_output, scenario_output = registration["output"].strip(".").split("...")

    assert playlist_output == "playlist-dropdown-selection.value"
    # The suffix Dash appends to an allow_duplicate output. The scenario value
    # already has a writer in check_for_new_data; the playlist filter does not.
    assert scenario_output.startswith("scenario-dropdown-selection.value@")
    # What Dash stores for "initial_duplicate": the mount still runs it.
    assert registration["prevent_initial_call"] is False


def _deep_link_registration() -> dict:
    """Find apply_deep_link's registration. The store has more than one reader."""
    (registration,) = [
        entry
        for entry in GLOBAL_CALLBACK_LIST
        if any(dep["id"] == home.HOME_DEEP_LINK_STORE_ID for dep in entry["inputs"])
        and "playlist-dropdown-selection.value" in entry["output"]
    ]
    return registration


def _output_keys(registration: dict) -> set[str]:
    """Read a registration's outputs as ``id.prop``, without duplicate hashes."""
    return {
        output.split("@")[0]
        for output in registration["output"].strip(".").split("...")
    }


def test_no_callback_depends_only_on_what_apply_deep_link_conditionally_writes():
    """Guard the regression that shipped once: a starved single-Input dependent.

    ``apply_deep_link`` returns ``no_update`` for a control the URL did not
    name, which is every control on an ordinary visit. dash-renderer drops a
    ready callback when none of its Inputs was written and every one of them
    is a declared output of a group member that already ran, so a callback
    whose Inputs are all written by ``apply_deep_link`` never makes its
    initial call on those visits. ``select_playlist`` was exactly that, and
    the scenario dropdown kept the full local list while the filter named a
    playlist. Its second Input is what this test protects.
    """
    deep_link = _deep_link_registration()
    written = _output_keys(deep_link)

    starved = [
        entry["output"]
        for entry in GLOBAL_CALLBACK_LIST
        if entry is not deep_link
        and entry["inputs"]
        and {f"{dep['id']}.{dep['property']}" for dep in entry["inputs"]} <= written
    ]

    assert starved == [], (
        "these callbacks would not make their initial call on a visit with no "
        f"query parameters: {starved}"
    )


def test_home_top_n_input_uses_compact_width(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_scenario_names", lambda: [])

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
    monkeypatch.setattr(home, "get_scenario_names", lambda: [])

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
    empty_value = next(
        component
        for component in components
        if getattr(component, "id", None) == "last-played-empty-value"
    )

    assert last_played.children == ""
    assert empty_value.data == ""
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
    # They fire seconds after a server start, when nobody is guaranteed to be
    # looking, so they wait for a dismissal instead of timing out.
    assert [notification["title"] for notification in notifications] == [
        "Playlist not loaded",
        "Playlist not loaded",
    ]
    assert [notification["autoClose"] for notification in notifications] == [
        False,
        False,
    ]
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
    monkeypatch.setattr(home, "get_scenario_names", lambda: ["All"])

    # The second argument is the deep-link store: a scheduling Input the
    # callback never reads. See select_playlist.
    assert home.select_playlist("Old Playlist Name", None) == ["All"]
    assert home.select_playlist("ValidCode", None) == ["ValidCode Scenario"]


def test_page_is_named_scenario_performance_and_keeps_the_root_route():
    """The rename is labels-only: the product name moved, the route did not."""
    page = dash.page_registry["source.pages.home"]

    assert page["name"] == "Scenario Performance"
    # Registered as a callable so the optional build-label prefix can be read
    # per request; unprefixed here because the flag defaults off.
    assert page["title"]() == "Scenario Performance"
    assert page["path"] == "/"


def test_home_section_titles_keep_visual_size_with_accessible_heading_order(
    monkeypatch,
):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_scenario_names", lambda: [])

    titles = {
        component.children: component
        for component in _walk_components(home.layout())
        if isinstance(component, dmc.Title)
    }

    assert titles["Scenario Stats"].order == 2
    assert titles["Scenario Stats"].size == "h6"
    # The inspector's groups sit under the page's h2 sections.
    for group in ("Overlays", "Run Data Points", "Score Threshold", "Notifications"):
        assert titles[group].order == 3
        assert titles[group].size == "h6"


def test_chart_options_controls_have_help_tooltips(monkeypatch):
    """Coverage is per control id, wherever the control now lives."""
    components = _layout_components(monkeypatch)
    expected_settings = {
        "automatically-change-scenario-switch": "automatically-change-scenario",
        "rank-overlay-switch": "rank-overlay",
        "show-all-ranks-switch": "show-all-ranks",
        "high-score-overlay-switch": "high-score-overlay",
        "score-threshold-overlay-switch": "score-threshold-overlay",
        "score-threshold-percentage": "score-threshold-percentage",
        "score-threshold-notification-switch": "score-threshold-notification",
        "run-notification-switch": "run-notification",
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


def test_help_texts_state_the_ratified_copy_with_control_names_in_bold(monkeypatch):
    components = _layout_components(monkeypatch)
    expected = {
        "show-all-ranks-switch": (
            "Draws every rank in the playlist's ladder instead of only the ones "
            "around your plotted scores. Needs **Rank thresholds** turned on."
        ),
        "score-threshold-percentage": (
            "Sets the score goal as a percentage of your personal best. The "
            "overlay line tracks your current personal best. Notifications judge "
            "a run against the personal best you had before the run."
        ),
        "score-threshold-notification-switch": (
            "Adds a pass or fail verdict to run notifications when the run can be "
            "judged against the score threshold. Needs **Run notifications** "
            "turned on."
        ),
        "top_n_scores": (
            "How many of your best scores to plot per sensitivity within the "
            "selected date range, or per day in **Score vs Time**. A new run that "
            "lands in the top N also triggers a notification."
        ),
    }

    for component_id, text in expected.items():
        (tooltip,) = [
            component
            for component in _walk_components(components[component_id].label)
            if isinstance(component, dmc.Tooltip)
        ]
        assert rendered_text(tooltip.label) == text


def test_home_no_longer_builds_the_settings_modal(monkeypatch):
    components = _layout_components(monkeypatch)

    assert "settings-modal" not in components
    assert "settings-modal-open-button" not in components
    assert not [
        component
        for component in components.values()
        if isinstance(component, dmc.Modal)
    ]


def test_chart_options_inputs_keep_their_ids_and_defaults(monkeypatch):
    components = _layout_components(monkeypatch)

    for component_id, (prop, default) in CHART_OPTIONS_INPUT_DEFAULTS.items():
        control = components[component_id]

        assert getattr(control, prop) == default
        assert control.persistence is True


def test_chart_options_inputs_are_grouped_by_the_concept_they_share(monkeypatch):
    components = _layout_components(monkeypatch)
    panel = components[home.CHART_OPTIONS_PANEL_ID]

    labels = {
        component.id: _label_text(component)
        for component in _walk_components(panel)
        if getattr(component, "id", None) in CHART_OPTIONS_INPUT_DEFAULTS
    }

    assert labels == {
        "rank-overlay-switch": "Rank thresholds",
        "show-all-ranks-switch": "Show all ranks",
        "high-score-overlay-switch": "PB score",
        "score-threshold-overlay-switch": "Score threshold overlay",
        "score-threshold-percentage": "Score threshold percentage",
        "score-threshold-notification-switch": "Score threshold verdict",
        "run-notification-switch": "Run notifications",
    }


def test_the_notifications_group_holds_the_master_switch_last(monkeypatch):
    """Ordered relative to Score Threshold, not pinned to a group count.

    Groups are added to this panel by parallel work; what this change owns is
    that Notifications is the trailing group and holds the master switch.
    """
    components = _layout_components(monkeypatch)
    panel = components[home.CHART_OPTIONS_PANEL_ID]

    groups = [
        (
            group.children[0].children,
            [getattr(control, "id", None) for control in group.children[1:]],
        )
        for group in panel.children
    ]
    titles = [title for title, _control_ids in groups]

    assert titles[-1] == "Notifications"
    assert titles.index("Score Threshold") < titles.index("Notifications")
    assert groups[-1][1] == ["run-notification-switch"]


def test_chart_options_panel_starts_collapsed_with_its_controls_mounted(monkeypatch):
    components = _layout_components(monkeypatch)
    panel = components[home.CHART_OPTIONS_PANEL_ID]
    toggle = components[home.CHART_OPTIONS_TOGGLE_ID].to_plotly_json()["props"]

    # Collapsed is a class, never conditional rendering: the inputs stay in the
    # layout tree feeding their callbacks with their persisted values.
    assert panel.className == COLLAPSED_PANEL_CLASS
    mounted = {getattr(child, "id", None) for child in _walk_components(panel)}
    assert set(CHART_OPTIONS_INPUT_DEFAULTS) <= mounted

    assert toggle["children"] == "Chart options"
    assert toggle["aria-expanded"] == "false"
    assert toggle["aria-controls"] == home.CHART_OPTIONS_PANEL_ID


def test_chart_options_toggle_flips_the_panel_class_and_aria_expanded():
    assert home.toggle_chart_options(1, COLLAPSED_PANEL_CLASS) == (
        home.CHART_OPTIONS_PANEL_CLASS,
        "true",
    )
    assert home.toggle_chart_options(2, home.CHART_OPTIONS_PANEL_CLASS) == (
        COLLAPSED_PANEL_CLASS,
        "false",
    )


def test_chart_options_toggle_ignores_a_fire_no_click_caused():
    # Under DashProxy a callback can fire once on page load with n_clicks=None.
    # The inspector starts closed on every visit, so that fire must change
    # neither the panel class nor the state the button announces.
    assert home.toggle_chart_options(None, COLLAPSED_PANEL_CLASS) == (
        no_update,
        no_update,
    )


def test_follow_switch_sits_under_the_scenario_selector_it_governs(monkeypatch):
    """It is stacked with the selector, not spread across the controls row."""
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_scenario_names", lambda: [])

    scenario_field = next(
        component
        for component in _walk_components(home.layout())
        if getattr(component, "className", None) == "home-scenario-field"
    )
    switch = scenario_field.children[1]

    assert [getattr(child, "id", None) for child in scenario_field.children] == [
        "scenario-dropdown-selection",
        "automatically-change-scenario-switch",
    ]
    assert _label_text(switch) == "Follow newly played scenario"
    assert switch.checked is True
    assert switch.persistence is True


def test_rank_refresh_button_has_tooltip(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_scenario_names", lambda: [])

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
        "cell-tooltip-affordance",
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

    assert format_scenario_rank(rank_info) == "11,266 of 18,342 (38.58% percentile)"


def test_format_scenario_rank_with_total_players_but_no_percentile():
    rank_info = ScenarioRankInfo(
        status=ScenarioRankStatus.RANKED,
        rank=11266,
        total_players=18342,
    )

    assert format_scenario_rank(rank_info) == "11,266 of 18,342"


def test_format_scenario_rank_drops_the_parenthetical_over_a_stale_total():
    """A rank past the cached total still shows both numbers, without a percentile."""
    rank_info = api_service._with_percentile(
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            leaderboard_id=98330,
            scenario_name="Some Scenario",
            rank=900,
            total_players=500,
        )
    )

    assert format_scenario_rank(rank_info) == "900 of 500"


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
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})

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

    assert _rendered_rank("Unplayed Scenario", allow_network=True) == (
        "Unranked (54,702 players)"
    )
    assert queried_scenarios == [("Unplayed Scenario", True)]


def test_rank_trigger_classification_preserves_initial_and_cofired_network_reads():
    interval = {"prop_id": "interval-component.n_intervals"}

    assert home._rank_allows_network([{"prop_id": "."}]) is True
    assert home._rank_allows_network([interval]) is False
    assert home._rank_allows_network([{"prop_id": "run-events.data"}]) is True
    assert (
        home._rank_allows_network(
            [
                interval,
                {"prop_id": "scenario-dropdown-selection.value"},
            ]
        )
        is True
    )


def test_rank_render_records_only_interactive_activity(monkeypatch, tmp_path):
    scenario_name = "Cached Scenario"
    leaderboard_id = 98330
    username = "MingoDynasty"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    settings_service.save_settings({"kovaaks_username": username})
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
    api_service.save_leaderboard_total(leaderboard_id, 100)
    monkeypatch.setattr(api_service, "_last_interactive_activity", 10.0)

    assert (
        _rendered_rank(scenario_name, allow_network=False)
        == "10 of 100 (90.50% percentile)"
    )
    interval_activity, _network_success = api_service.get_api_activity_timestamps()
    assert interval_activity == 10.0

    assert (
        _rendered_rank(scenario_name, allow_network=True)
        == "10 of 100 (90.50% percentile)"
    )
    interactive_activity, _network_success = api_service.get_api_activity_timestamps()
    assert interactive_activity > interval_activity


@pytest.mark.parametrize(
    ("total_state", "expected"),
    [
        ("missing", "10"),
        ("expired", "10 of 100 (90.50% percentile)"),
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
    settings_service.save_settings({"kovaaks_username": username})
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

    assert _rendered_rank(scenario_name, allow_network=False) == expected


def test_interval_rank_render_does_not_fetch_or_cache_unresolved_scenario(
    monkeypatch,
    tmp_path,
):
    scenario_name = "Local Custom Scenario"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    api_service.make_cache()

    def fail_network(*_args, **_kwargs):
        raise AssertionError("unresolved interval rank reads must not use the network")

    monkeypatch.setattr(api_service, "_session_get", fail_network)

    rendered = _rendered_rank(scenario_name, allow_network=False)
    assert _rank_text(rendered) == "N/A · lookup failed"
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


def _seed_mismatched_rank_cache(monkeypatch, tmp_path) -> str:
    """Cache a ranked position that matched a different Steam account."""
    scenario_name = "Cached Scenario"
    leaderboard_id = 98330
    username = "MingoDynasty"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    settings_service.save_settings(
        {"kovaaks_username": username, "steam_id": "configured-steam-id"}
    )
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
    return scenario_name


def test_passive_rank_render_reports_a_steam_id_mismatch_once_per_session(
    monkeypatch,
    tmp_path,
):
    # The mismatch is the one persistent condition with no in-place home, so
    # it toasts -- but once for the session, not once per scenario switch.
    scenario_name = _seed_mismatched_rank_cache(monkeypatch, tmp_path)

    display, notifications = home._render_scenario_rank(
        scenario_name,
        allow_network=True,
    )

    assert display == "10 of 100 (90.50% percentile)"
    assert len(notifications) == 1
    assert notifications[0]["title"] == "Steam ID mismatch"
    assert notifications[0]["color"] == "yellow"
    assert notifications[0]["id"] == "steam-id-mismatch"
    assert "different-steam-id" in notifications[0]["message"]

    for allow_network in (False, True):
        assert home._render_scenario_rank(
            scenario_name,
            allow_network=allow_network,
        ) == (display, [])


def test_steam_id_mismatch_toast_persists_until_dismissed(monkeypatch, tmp_path):
    # It can fire while nobody is looking at the page, so it must not expire.
    scenario_name = _seed_mismatched_rank_cache(monkeypatch, tmp_path)

    _display, notifications = home._render_scenario_rank(
        scenario_name,
        allow_network=True,
    )

    assert notifications[0]["autoClose"] is False


def test_matching_steam_id_never_toasts(monkeypatch, tmp_path):
    scenario_name = _seed_mismatched_rank_cache(monkeypatch, tmp_path)
    settings_service.save_settings(
        {"kovaaks_username": "MingoDynasty", "steam_id": "different-steam-id"}
    )

    _display, notifications = home._render_scenario_rank(
        scenario_name,
        allow_network=True,
    )

    assert notifications == []


def test_a_rank_render_nobody_triggered_keeps_the_sessions_mismatch_toast(
    monkeypatch,
    tmp_path,
):
    # Under DashProxy an allow_duplicate callback can fire once on page load
    # with an empty trigger list. The value still renders, but the session's
    # one mismatch toast must survive for a render the user actually caused.
    scenario_name = _seed_mismatched_rank_cache(monkeypatch, tmp_path)
    monkeypatch.setattr(home, "ctx", SimpleNamespace(triggered=[]))

    display, notifications = home.get_scenario_rank(None, scenario_name, 0)

    assert display == "10 of 100 (90.50% percentile)"
    assert notifications is no_update

    monkeypatch.setattr(
        home,
        "ctx",
        SimpleNamespace(triggered=[{"prop_id": "scenario-dropdown-selection.value"}]),
    )
    _display, notifications = home.get_scenario_rank(None, scenario_name, 0)

    assert [notification["id"] for notification in notifications] == [
        "steam-id-mismatch"
    ]


def test_rank_render_without_notifications_reports_no_update(monkeypatch, tmp_path):
    scenario_name = _seed_mismatched_rank_cache(monkeypatch, tmp_path)
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    monkeypatch.setattr(
        home,
        "ctx",
        SimpleNamespace(triggered=[{"prop_id": "scenario-dropdown-selection.value"}]),
    )

    _display, notifications = home.get_scenario_rank(None, scenario_name, 0)

    assert notifications is no_update


def test_passive_rank_render_points_an_unset_username_at_settings():
    # The fixture store leaves identity unset -- the fresh-install default.
    rendered, notifications = home._render_scenario_rank(
        "Scenario",
        allow_network=True,
    )

    assert _rank_text(rendered) == "N/A · set your KovaaK's username in Settings"
    anchors = [
        component
        for child in rendered
        for component in _walk_components(child)
        if isinstance(component, dmc.Anchor)
    ]
    assert [anchor.href for anchor in anchors] == ["/settings"]
    assert notifications == []


def test_passive_rank_render_offers_refresh_when_the_lookup_failed(monkeypatch):
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    monkeypatch.setattr(
        home,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            error_message="Failed to fetch leaderboard position for Scenario.",
        ),
    )

    rendered, notifications = home._render_scenario_rank(
        "Scenario",
        allow_network=True,
    )

    assert _rank_text(rendered) == "N/A · lookup failed"
    assert notifications == []


def test_passive_rank_render_marks_a_stale_cached_position(monkeypatch):
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    monkeypatch.setattr(
        home,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=1240,
            served_stale=True,
            warning_message="Couldn't refresh from KovaaK's; showing the last "
            "cached position for Scenario.",
        ),
    )

    rendered, notifications = home._render_scenario_rank(
        "Scenario",
        allow_network=True,
    )

    assert _rank_text(rendered) == "1,240 · from cache"
    assert notifications == []


def test_stale_affordance_survives_the_cache_only_interval_tick(monkeypatch):
    # The interval re-reads the same rank from cache, where the served-stale
    # marker is gone; the hint must not blink off a tick after it appears.
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})

    def rank_for(*_args, **kwargs):
        return ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=1240,
            served_stale=True if kwargs["allow_network"] else None,
        )

    monkeypatch.setattr(home, "get_scenario_rank_info", rank_for)

    assert (
        _rank_text(_rendered_rank("Scenario", allow_network=True))
        == "1,240 · from cache"
    )
    assert (
        _rank_text(_rendered_rank("Scenario", allow_network=False))
        == "1,240 · from cache"
    )


@pytest.mark.parametrize(
    ("hint", "stale_value"),
    [
        (home._RANK_HINT_SERVED_STALE, "1,240"),
        (home._RANK_HINT_LOOKUP_FAILED, "N/A"),
    ],
)
def test_a_background_cache_write_retires_the_memoized_hint(
    monkeypatch,
    hint,
    stale_value,
):
    # The warmup worker and the score-aware refresh Timer both write the rank
    # cache off a background thread. Once the interval reads a value the last
    # network verdict was never about, that verdict must not keep claiming the
    # lookup failed over a position that has since arrived.
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    home._last_rank_hints["Scenario"] = (stale_value, hint)
    monkeypatch.setattr(
        home,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=1180,
        ),
    )

    assert _rendered_rank("Scenario", allow_network=False) == "1,180"
    assert "Scenario" not in home._last_rank_hints


def test_a_successful_manual_refresh_retires_the_stale_affordance(monkeypatch):
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    home._last_rank_hints["Scenario"] = ("1,240", home._RANK_HINT_SERVED_STALE)
    monkeypatch.setattr(
        home,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=1240,
        ),
    )

    _RefreshClient().click("Scenario")

    assert home._last_rank_hints["Scenario"] == ("1,240", None)
    assert _rendered_rank("Scenario", allow_network=False) == "1,240"


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
    settings_service.save_settings({"kovaaks_username": username})
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
        lambda rank_info, _ttl=168, force_refresh=False: rank_info,
    )

    rank_text, notifications, _hidden = _RefreshClient().click(scenario_name)
    assert rank_text == expected
    # Any completed refresh — ranked or unranked — confirms with a green
    # toast, on a channel keyed to the scenario it refreshed.
    assert notifications[0]["color"] == "green"
    assert notifications[0]["title"] == "Position refreshed"
    assert scenario_name in notifications[0]["message"]
    assert notifications[0]["id"].startswith(f"rank-refresh-success-{scenario_name}-")
    assert fetched == [True]
    stored = api_service._cached_rank(leaderboard_id, username)
    assert stored is not None
    assert stored.status == candidate.status
    assert stored.score == candidate.score


def _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id):
    """Cache one resolved, ranked scenario for a Refresh click to act on."""
    username = "MingoDynasty"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    settings_service.save_settings({"kovaaks_username": username})
    api_service.make_cache()
    api_service.save_leaderboard_id(scenario, leaderboard_id, "test")
    api_service.save_scenario_rank(
        leaderboard_id,
        username,
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=40,
            leaderboard_id=leaderboard_id,
            scenario_name=scenario,
            score=110.0,
        ),
    )
    monkeypatch.setattr(
        api_service,
        "get_user_scenario_total_play",
        lambda *_args: None,
    )


def _refreshed_rank(leaderboard_id, rank=25):
    """Return the board-authoritative result a click's rank fetch would give."""
    return ScenarioRankInfo(
        status=ScenarioRankStatus.RANKED,
        rank=rank,
        leaderboard_id=leaderboard_id,
    )


def test_manual_rank_refresh_re_reads_the_total_behind_the_percentile(
    monkeypatch,
    tmp_path,
):
    """A fresh totals cache does not spare the click its total lookup.

    The denominator is refreshed with the numerator: a live position over a
    week-old count is two moments presented as one fact, and on a growing
    board it understates the percentile.
    """
    scenario = "Reset Scenario"
    leaderboard_id = 98330
    _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id)
    api_service.save_leaderboard_total(leaderboard_id, 500)

    totals = []

    def fetch_total(_leaderboard_id):
        totals.append(True)
        return 1000

    monkeypatch.setattr(api_service, "fetch_leaderboard_total", fetch_total)
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: _refreshed_rank(leaderboard_id),
    )

    display, notifications, _hidden = _RefreshClient().click(scenario)

    assert totals == [True]
    # 95.10% is what the cached 500 would have printed.
    assert _rank_text(display) == "25 of 1,000 (97.55% percentile)"
    assert notifications[0]["color"] == "green"


def test_a_passive_render_still_honors_the_leaderboard_total_ttl(
    monkeypatch,
    tmp_path,
):
    """Only the click is board-authoritative; bulk and interval paths keep the TTL."""
    scenario = "Reset Scenario"
    leaderboard_id = 98330
    _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id)
    api_service.save_leaderboard_total(leaderboard_id, 500)

    monkeypatch.setattr(
        api_service,
        "fetch_leaderboard_total",
        lambda *_args: pytest.fail("a passive render must not refetch the total"),
    )
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: pytest.fail("a passive render must not refetch the rank"),
    )

    assert _rank_text(_rendered_rank(scenario, True)) == "40 of 500 (92.10% percentile)"


def test_a_failed_total_refresh_toasts_orange_and_keeps_the_cached_percentile(
    monkeypatch,
    tmp_path,
):
    """Orange is partial success: the position committed, the total did not.

    Green would assert a freshness the readout does not have, and the
    served-stale yellow would claim the position came from cache when it is
    the one part that did refresh.
    """
    scenario = "Reset Scenario"
    leaderboard_id = 98330
    _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id)
    api_service.save_leaderboard_total(leaderboard_id, 500)

    def fetch_total(_leaderboard_id):
        raise requests.RequestException("leaderboard unreachable")

    monkeypatch.setattr(api_service, "fetch_leaderboard_total", fetch_total)
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: _refreshed_rank(leaderboard_id),
    )

    display, notifications, _hidden = _RefreshClient().click(scenario)

    assert _rank_text(display) == "25 of 500 (95.10% percentile)"
    assert notifications[0]["color"] == "orange"
    assert notifications[0]["title"] == "Position refreshed but total from cache"
    assert scenario in notifications[0]["message"]
    # The percentile moved under the user's eyes this click (92.10 to 95.10),
    # so the copy names the total, which is the part that came from cache.
    assert "the total shown is from cache" in notifications[0]["message"]
    assert notifications[0]["id"].startswith(f"rank-refresh-success-{scenario}-")


def test_a_failed_total_refresh_with_nothing_cached_toasts_orange_without_a_total(
    monkeypatch,
    tmp_path,
):
    """No count was ever cached, so the position stands alone and says so."""
    scenario = "Reset Scenario"
    leaderboard_id = 98330
    _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id)

    def fetch_total(_leaderboard_id):
        raise requests.RequestException("leaderboard unreachable")

    monkeypatch.setattr(api_service, "fetch_leaderboard_total", fetch_total)
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: _refreshed_rank(leaderboard_id),
    )

    display, notifications, _hidden = _RefreshClient().click(scenario)

    assert _rank_text(display) == "25"
    assert notifications[0]["color"] == "orange"
    assert notifications[0]["title"] == "Position refreshed but no total"
    assert "no total is shown" in notifications[0]["message"]


def test_a_failed_total_refresh_on_an_unranked_result_stays_true(
    monkeypatch,
    tmp_path,
):
    """An unranked readout has no percentile, so the copy must not claim one.

    ``format_scenario_rank`` renders UNRANKED as ``Unranked (N players)``. The
    total is the only thing the failed re-read touched, and naming it is what
    keeps one string true for both statuses.
    """
    scenario = "Reset Scenario"
    leaderboard_id = 98330
    _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id)
    api_service.save_leaderboard_total(leaderboard_id, 500)

    def fetch_total(_leaderboard_id):
        raise requests.RequestException("leaderboard unreachable")

    monkeypatch.setattr(api_service, "fetch_leaderboard_total", fetch_total)
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: ScenarioRankInfo(
            status=ScenarioRankStatus.UNRANKED,
            leaderboard_id=leaderboard_id,
        ),
    )

    display, notifications, _hidden = _RefreshClient().click(scenario)

    assert _rank_text(display) == "Unranked (500 players)"
    assert notifications[0]["color"] == "orange"
    assert notifications[0]["title"] == "Position refreshed but total from cache"
    assert "the total shown is from cache" in notifications[0]["message"]
    assert "percentile" not in notifications[0]["message"]


def test_a_failed_rank_refresh_asks_for_no_total(monkeypatch, tmp_path):
    """A host that just failed the rank is not asked for the count as well."""
    scenario = "Reset Scenario"
    leaderboard_id = 98330
    _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id)
    api_service.save_leaderboard_total(leaderboard_id, 500)

    monkeypatch.setattr(
        api_service,
        "fetch_leaderboard_total",
        lambda *_args: pytest.fail("a failed rank fetch must not ask for the total"),
    )

    def fetch_rank(*_args):
        raise requests.RequestException("leaderboard unreachable")

    monkeypatch.setattr(api_service, "fetch_scenario_rank", fetch_rank)

    display, notifications, _hidden = _RefreshClient().click(scenario)

    # The cached position carries the served-stale hint; its count comes from
    # the TTL-free read in the fallback, not from a second request.
    assert _rank_text(display) == "40 of 500 (92.10% percentile) · from cache"
    assert notifications[0]["color"] == "yellow"


def test_manual_rank_refresh_failure_toasts_red_and_leaves_the_value_alone(
    monkeypatch,
):
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    calls = []

    def get_rank(*_args, **kwargs):
        calls.append(kwargs)
        return ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            error_message="Rank lookup failed.",
        )

    monkeypatch.setattr(home, "get_scenario_rank_info", get_rank)

    rank_display, notifications, _hidden = _RefreshClient().click("Scenario")

    # no_update, not "N/A": whatever the field showed -- usually the cached
    # position -- stays put, which is what the toast copy promises.
    assert rank_display is no_update
    assert calls == [{"force_refresh": True}]
    assert [notification["color"] for notification in notifications] == ["red"]
    assert notifications[0]["title"] == "Position refresh failed"
    assert (
        notifications[0]["message"]
        == "Couldn't refresh. The position shown is unchanged."
    )


def test_manual_rank_refresh_crash_toasts_red_and_leaves_the_value_alone(monkeypatch):
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})

    def explode(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(home, "get_scenario_rank_info", explode)

    rank_display, notifications, _hidden = _RefreshClient().click("Scenario")

    assert rank_display is no_update
    assert [notification["color"] for notification in notifications] == ["red"]
    assert notifications[0]["title"] == "Position refresh failed"


def test_manual_rank_refresh_served_stale_toasts_yellow_and_marks_the_value(
    monkeypatch,
):
    # A failed fetch served from cache is neither a failure the user must act
    # on nor a refresh worth confirming: yellow, and the value says so too.
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})

    def get_rank(*_args, **_kwargs):
        return ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=50,
            leaderboard_id=1,
            scenario_name="Scenario",
            served_stale=True,
            warning_message="Couldn't refresh from KovaaK's; showing the last "
            "cached position for Scenario.",
        )

    monkeypatch.setattr(home, "get_scenario_rank_info", get_rank)

    rank_display, notifications, _hidden = _RefreshClient().click("Scenario")

    assert _rank_text(rank_display) == "50 · from cache"
    assert [notification["color"] for notification in notifications] == ["yellow"]
    assert notifications[0]["title"] == "Refresh failed · position from cache"
    assert (
        notifications[0]["message"]
        == "Couldn't refresh. The position shown is from cache."
    )


def test_manual_rank_refresh_reports_a_steam_mismatch_as_a_clean_refresh(monkeypatch):
    # The fetch succeeded; the mismatch is the passive path's once-per-session
    # toast, not a per-click complaint about a refresh that worked.
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})

    def get_rank(*_args, **_kwargs):
        return ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=50,
            leaderboard_id=1,
            scenario_name="Scenario",
            matched_steam_id="different-steam-id",
            warning_message="Configured Steam ID 'x' does not match.",
        )

    monkeypatch.setattr(home, "get_scenario_rank_info", get_rank)

    rank_display, notifications, _hidden = _RefreshClient().click("Scenario")

    assert rank_display == "50"
    assert [notification["color"] for notification in notifications] == ["green"]


def test_back_to_back_manual_refreshes_each_render_their_result(monkeypatch):
    # ``show`` swallows a repeated id while the first toast is still up, so
    # each deliberate click shows a fresh instance and hides the one before it.
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    monkeypatch.setattr(
        home,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=50,
            leaderboard_id=1,
            scenario_name="Scenario",
        ),
    )

    client = _RefreshClient()
    _first_display, first, first_hidden = client.click("Scenario")
    _second_display, second, second_hidden = client.click("Scenario")

    assert first[0]["color"] == second[0]["color"] == "green"
    assert first[0]["id"] != second[0]["id"]
    assert first[0]["id"].startswith("rank-refresh-success-Scenario-")
    assert second[0]["id"].startswith("rank-refresh-success-Scenario-")
    # The replacement: the second click retires the first click's instance.
    assert first_hidden == []
    assert second_hidden == [first[0]["id"]]


def test_manual_rank_refresh_without_a_username_names_the_condition(monkeypatch):
    # Nothing failed: with no username the lookup would never touch the
    # network, so the click is answered with the verdict rather than the
    # generic red failure -- and the field's own hint is left alone.
    monkeypatch.setattr(
        home,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: pytest.fail(
            "an unset username must not reach the rank service"
        ),
    )

    rank_display, notifications, _hidden = _RefreshClient().click("Scenario")

    assert rank_display is no_update
    assert [notification["color"] for notification in notifications] == ["blue"]
    assert notifications[0]["title"] == "KovaaK's username not set"
    assert notifications[0]["message"] == (
        "Set your KovaaK's username in Settings to see your leaderboard position."
    )


def test_back_to_back_unset_username_refreshes_each_answer(monkeypatch):
    # Same reason the green confirmation re-pops: a stable id would be
    # swallowed while the first toast is still on screen.
    monkeypatch.setattr(
        home,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: pytest.fail(
            "an unset username must not reach the rank service"
        ),
    )

    client = _RefreshClient()
    _first_display, first, first_hidden = client.click("Scenario")
    _second_display, second, second_hidden = client.click("Scenario")

    assert first[0]["id"] != second[0]["id"]
    assert first[0]["id"].startswith("rank-refresh-username-unset-")
    assert second[0]["id"].startswith("rank-refresh-username-unset-")
    assert first_hidden == []
    assert second_hidden == [first[0]["id"]]


def test_the_two_refresh_problems_share_one_channel(monkeypatch):
    """A hard failure and a served-stale retry are verdicts on one attempt.

    Under the separate ids they used to carry, a stale retry after a hard
    failure left both toasts on screen contradicting each other about the same
    click. One channel makes each attempt's verdict replace the last.
    """
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    outcomes = [
        ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            error_message="Rank lookup failed.",
        ),
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=50,
            leaderboard_id=1,
            scenario_name="Scenario",
            served_stale=True,
            warning_message="Showing the last cached position.",
        ),
    ]
    monkeypatch.setattr(
        home, "get_scenario_rank_info", lambda *_a, **_k: outcomes.pop(0)
    )

    client = _RefreshClient()
    _display, failed, failed_hidden = client.click("Scenario")
    _display, stale, stale_hidden = client.click("Scenario")

    assert failed[0]["color"] == "red"
    assert stale[0]["color"] == "yellow"
    assert failed[0]["id"].startswith(f"{home._RANK_REFRESH_PROBLEM_CHANNEL}-")
    assert stale[0]["id"].startswith(f"{home._RANK_REFRESH_PROBLEM_CHANNEL}-")
    assert failed_hidden == []
    assert stale_hidden == [failed[0]["id"]]


def test_refreshes_of_two_scenarios_keep_separate_success_channels(monkeypatch):
    """Different scenarios are different facts, so their confirmations stack."""
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    monkeypatch.setattr(
        home,
        "get_scenario_rank_info",
        lambda scenario, *_a, **_k: ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=50,
            leaderboard_id=1,
            scenario_name=scenario,
        ),
    )

    client = _RefreshClient()
    _display, first, first_hidden = client.click("Scenario A")
    _display, second, second_hidden = client.click("Scenario B")

    assert first_hidden == second_hidden == []
    assert client.toast_channels["rank-refresh-success-Scenario A"] == first[0]["id"]
    assert client.toast_channels["rank-refresh-success-Scenario B"] == second[0]["id"]


def test_a_successful_refresh_clears_the_problem_and_username_channels(monkeypatch):
    """The success falsifies both standing claims about the same scenario."""
    outcomes = [
        ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            error_message="Rank lookup failed.",
        ),
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=50,
            leaderboard_id=1,
            scenario_name="Scenario",
        ),
    ]
    monkeypatch.setattr(
        home, "get_scenario_rank_info", lambda *_a, **_k: outcomes.pop(0)
    )

    # No username first: the blue notice stands, and nothing reached the
    # service. Then the username is set and the refresh fails, then succeeds.
    client = _RefreshClient()
    _display, unset, _hidden = client.click("Scenario")
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    _display, failed, _hidden = client.click("Scenario")
    _display, success, success_hidden = client.click("Scenario")

    assert success[0]["color"] == "green"
    assert set(success_hidden) == {failed[0]["id"], unset[0]["id"]}
    assert client.toast_channels[home._RANK_REFRESH_PROBLEM_CHANNEL] is None
    assert client.toast_channels[home._RANK_REFRESH_USERNAME_UNSET_CHANNEL] is None


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

    assert home.refresh_rank(None, "Scenario", {}) == (
        no_update,
        no_update,
        no_update,
        no_update,
    )


def test_manual_rank_refresh_without_scenario_skips_fetch_and_toast(monkeypatch):
    monkeypatch.setattr(
        home,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: pytest.fail(
            "a refresh without a scenario must not hit the network"
        ),
    )

    assert home.refresh_rank(1, None, {}) == (
        "N/A",
        no_update,
        no_update,
        no_update,
    )


def test_scenario_rank_loading_is_delayed_and_not_shown_initially(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_scenario_names", lambda: [])

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
