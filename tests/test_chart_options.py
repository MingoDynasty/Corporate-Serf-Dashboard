"""The Chart options panel on the Scenario Performance page.

The panel and its callbacks live in ``source/components/chart_options.py`` and
take their ids from the page that hosts them. These tests render that page and
hold what a browser's stored preferences depend on, each control's id and
layout default, along with the groups, the help text, and the toggle.
"""

import json
from types import SimpleNamespace

import dash
import dash_mantine_components as dmc
import plotly.graph_objects as go
import pytest
from dash import Patch, no_update
from dash._callback import GLOBAL_CALLBACK_LIST, GLOBAL_CALLBACK_MAP

from source.components import chart_options, scenario_selection
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
    monkeypatch.setattr(
        scenario_selection, "get_visible_playlist_selector_options", lambda: []
    )
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])

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


# A second page's ids, none of which the Scenario Performance page uses.
SECOND_PAGE_IDS = chart_options.ChartOptionsIds(
    *(f"second-{field}" for field in chart_options.ChartOptionsIds._fields)
)


@pytest.fixture
def restored_callbacks():
    """Take a test's registrations back out of Dash's process-wide registry."""
    saved_list = list(GLOBAL_CALLBACK_LIST)
    saved_map = dict(GLOBAL_CALLBACK_MAP)
    yield
    GLOBAL_CALLBACK_LIST[:] = saved_list
    GLOBAL_CALLBACK_MAP.clear()
    GLOBAL_CALLBACK_MAP.update(saved_map)


def test_the_page_gives_the_block_the_ids_browsers_store_values_under(monkeypatch):
    # The ids are data the page passes in, so a typo there is a reset of every
    # user's stored setting. The four the other tests reach only through this
    # object are held to their strings here too.
    assert home.CHART_OPTIONS_IDS._asdict() == {
        "panel": "chart-options-panel",
        "toggle": "chart-options-toggle",
        "rank_overlay": "rank-overlay-switch",
        "show_all_ranks": "show-all-ranks-switch",
        "high_score_overlay": "high-score-overlay-switch",
        "point_size": "point-size",
        "point_size_label": "point-size-label",
        "point_color": "point-color",
        "point_color_default": "point-color-default",
        "score_threshold_overlay": "score-threshold-overlay-switch",
        "score_threshold_percentage": "score-threshold-percentage",
        "score_threshold_notification": "score-threshold-notification-switch",
        "run_notification": "run-notification-switch",
        "graph": "graph-content",
        "cached_plot": "cached-plot",
    }

    # The graph and the store are built by the page, not by the block, so
    # nothing but this ties their ids in the layout to the ones passed in.
    assert set(home.CHART_OPTIONS_IDS) <= set(_layout_components(monkeypatch))


def test_the_page_registers_the_block_for_its_own_ids():
    """Registration is a call the page makes; without it all three go quiet."""
    assert {
        "graph-content.figure",
        "point-color.value",
        "..chart-options-panel.className...chart-options-toggle.aria-expanded..",
    } <= set(GLOBAL_CALLBACK_MAP)


def test_a_second_page_builds_a_panel_that_shares_no_id_with_the_first(monkeypatch):
    first_page_ids = set(_layout_components(monkeypatch)) - {None}

    built = {
        component.id
        for tree in (
            chart_options.chart_options_toggle(SECOND_PAGE_IDS),
            chart_options.chart_options_panel(SECOND_PAGE_IDS),
        )
        for component in _walk_components(tree)
        if getattr(component, "id", None) is not None
    }

    # Every id in the tree came from the ids passed in, apart from the graph
    # and the store, which the page builds.
    assert built == set(SECOND_PAGE_IDS) - {
        SECOND_PAGE_IDS.graph,
        SECOND_PAGE_IDS.cached_plot,
    }
    assert not built & first_page_ids


def test_a_second_registration_adds_callbacks_for_its_own_ids_only(
    restored_callbacks,
):
    before = dict(GLOBAL_CALLBACK_MAP)

    chart_options.register_chart_options(SECOND_PAGE_IDS)

    added = {
        key: spec for key, spec in GLOBAL_CALLBACK_MAP.items() if key not in before
    }
    assert set(added) == {
        "second-graph.figure",
        "second-point_color.value",
        "..second-panel.className...second-toggle.aria-expanded..",
    }
    # The theme switch belongs to the shell, so both pages read the same one.
    assert {
        entry["id"]
        for spec in added.values()
        for entry in spec["inputs"] + spec["state"]
    } == {
        "color-scheme-switch",
        "second-cached_plot",
        "second-point_size",
        "second-point_color",
        "second-point_color_default",
        "second-toggle",
        "second-panel",
    }
    assert all(GLOBAL_CALLBACK_MAP[key] is spec for key, spec in before.items())


# --- A page whose figures ring the latest run ----------------------------------------


def _ringed_plot(ringed_run_id: str = "newest.csv") -> str:
    """Build a cached figure: run points, then a ring tagged with a run's id."""
    figure = go.Figure(
        [
            go.Scatter(x=[1, 2], y=[10.0, 12.0], name="Run data point"),
            go.Scatter(x=[2], y=[12.0], name="Latest run", meta=ringed_run_id),
        ]
    )
    return figure.to_json()


def _ring(figure):
    (ring,) = [trace for trace in figure.data if trace.name == "Latest run"]
    return ring


@pytest.mark.parametrize(
    ("latest_run", "opacity"),
    [("newest.csv", 1), ("on-another-scenario.csv", 0), (None, 0)],
)
def test_styling_the_graph_shows_the_ring_only_round_the_last_run_played(
    latest_run, opacity
):
    figure = chart_options.apply_graph_appearance_ringing_latest_run(
        "dark",
        _ringed_plot(),
        "Large",
        "",
        latest_run,
        only_the_latest_run_changed=False,
    )

    assert isinstance(figure, go.Figure)
    assert _ring(figure).opacity == opacity
    # The rest of the styling is the other page's own.
    assert (
        figure.layout.template
        == go.Figure(
            chart_options.apply_graph_appearance("dark", _ringed_plot(), "Large", "")
        ).layout.template
    )
    assert figure.data[0].marker.size == 10


@pytest.mark.parametrize(
    ("latest_run", "opacity"),
    [("newest.csv", 1), ("on-another-scenario.csv", 0), (None, 0)],
)
def test_a_change_of_latest_run_alone_patches_the_ring_and_nothing_else(
    latest_run, opacity
):
    """A whole new figure would undo a zoom on a chart the run did not change."""
    patch = chart_options.apply_graph_appearance_ringing_latest_run(
        "dark",
        _ringed_plot(),
        "Large",
        "#ff0000",
        latest_run,
        only_the_latest_run_changed=True,
    )

    assert isinstance(patch, Patch)
    assert json.loads(json.dumps(patch.to_plotly_json()))["operations"] == [
        {
            "operation": "Assign",
            "location": ["data", 1, "opacity"],
            "params": {"value": opacity},
        }
    ]


@pytest.mark.parametrize(
    "plot_json",
    [
        None,
        "",
        go.Figure(go.Scatter(x=[1], y=[10.0], name="Run data point")).to_json(),
        go.Figure().to_json(),
    ],
)
def test_a_figure_with_no_ring_is_left_alone_when_the_latest_run_changes(plot_json):
    """The empty states, and a range that leaves the newest run out."""
    assert (
        chart_options.apply_graph_appearance_ringing_latest_run(
            "light", plot_json, "Default", "", "a.csv", only_the_latest_run_changed=True
        )
        is no_update
    )


def test_a_page_that_rings_the_latest_run_gives_the_graph_one_more_input(
    restored_callbacks,
):
    chart_options.register_chart_options(SECOND_PAGE_IDS, latest_run="second-latest")

    spec = GLOBAL_CALLBACK_MAP["second-graph.figure"]

    assert [f"{entry['id']}.{entry['property']}" for entry in spec["inputs"]] == [
        "color-scheme-switch.computedColorScheme",
        "second-cached_plot.data",
        "second-point_size.value",
        "second-point_color.value",
        "second-latest.data",
    ]
    assert spec["state"] == []
    # One writer of the figure, and a plain one: the graph is then held for
    # the chart callback and for the latest run's writer alike.
    assert [key for key in GLOBAL_CALLBACK_MAP if "second-graph.figure" in key] == [
        "second-graph.figure"
    ]


@pytest.mark.parametrize(
    ("triggered", "patched"),
    [
        (["second-latest.data"], True),
        # The new figure and the new latest run arrive together when a run
        # lands on the chart's own scenario: the figure is styled whole.
        (["second-cached_plot.data", "second-latest.data"], False),
        (["second-cached_plot.data"], False),
        (["color-scheme-switch.computedColorScheme"], False),
        # The page load, which nothing triggered.
        (["."], False),
    ],
)
def test_the_graph_is_patched_only_when_the_latest_run_is_all_that_changed(
    monkeypatch, restored_callbacks, triggered, patched
):
    chart_options.register_chart_options(SECOND_PAGE_IDS, latest_run="second-latest")
    answer = GLOBAL_CALLBACK_MAP["second-graph.figure"]["callback"].__wrapped__
    monkeypatch.setattr(
        chart_options,
        "ctx",
        SimpleNamespace(
            triggered=[{"prop_id": prop_id, "value": None} for prop_id in triggered]
        ),
    )

    result = answer("light", _ringed_plot(), "Default", "", "newest.csv")

    assert isinstance(result, Patch) == patched
    assert isinstance(result, go.Figure) != patched
