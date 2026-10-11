"""The Chart options panel on the Scenario Performance page.

The panel and its callbacks live in ``source/components/chart_options.py`` and
take their ids from the page that hosts them. These tests render that page and
hold what a browser's stored preferences depend on, each control's id and
layout default, along with the groups, the help text, and the toggle.
"""

import dash
import dash_mantine_components as dmc
from dash import no_update

from source.components import chart_options
from tests.rendered_text import rendered_text

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402


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
    f"{chart_options.CHART_OPTIONS_PANEL_CLASS} "
    f"{chart_options.CHART_OPTIONS_PANEL_HIDDEN_CLASS}"
)


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
        assert tooltips[0].label == chart_options.SETTINGS_HELP_TEXT[help_key]
        assert tooltips[0].events == chart_options.TOOLTIP_EVENTS
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
            "Sets the score goal as a percentage of your personal best. On a "
            "scenario scored by completion time, it's a percentage of your "
            "personal best's pace instead, when the app can measure pace "
            "reliably. Otherwise, it stays a percentage of your score. The "
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


def test_chart_options_inputs_keep_their_ids_and_defaults(monkeypatch):
    components = _layout_components(monkeypatch)

    for component_id, (prop, default) in CHART_OPTIONS_INPUT_DEFAULTS.items():
        control = components[component_id]

        assert getattr(control, prop) == default
        assert control.persistence is True


def test_chart_options_inputs_are_grouped_by_the_concept_they_share(monkeypatch):
    components = _layout_components(monkeypatch)
    panel = components[home.CHART_OPTIONS_IDS.panel]

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
    panel = components[home.CHART_OPTIONS_IDS.panel]

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
    panel = components[home.CHART_OPTIONS_IDS.panel]
    toggle = components[home.CHART_OPTIONS_IDS.toggle].to_plotly_json()["props"]

    # Collapsed is a class, never conditional rendering: the inputs stay in the
    # layout tree feeding their callbacks with their persisted values.
    assert panel.className == COLLAPSED_PANEL_CLASS
    mounted = {getattr(child, "id", None) for child in _walk_components(panel)}
    assert set(CHART_OPTIONS_INPUT_DEFAULTS) <= mounted

    assert toggle["children"] == "Chart options"
    assert toggle["aria-expanded"] == "false"
    assert toggle["aria-controls"] == home.CHART_OPTIONS_IDS.panel


def test_chart_options_toggle_flips_the_panel_class_and_aria_expanded():
    assert chart_options.toggle_chart_options(1, COLLAPSED_PANEL_CLASS) == (
        chart_options.CHART_OPTIONS_PANEL_CLASS,
        "true",
    )
    assert chart_options.toggle_chart_options(
        2, chart_options.CHART_OPTIONS_PANEL_CLASS
    ) == (
        COLLAPSED_PANEL_CLASS,
        "false",
    )


def test_chart_options_toggle_ignores_a_fire_no_click_caused():
    # Under DashProxy a callback can fire once on page load with n_clicks=None.
    # The inspector starts closed on every visit, so that fire must change
    # neither the panel class nor the state the button announces.
    assert chart_options.toggle_chart_options(None, COLLAPSED_PANEL_CLASS) == (
        no_update,
        no_update,
    )
