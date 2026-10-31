"""The Chart options panel on the Run History page.

The panel and its callbacks live in ``source/components/chart_options.py`` and
take their ids from the page that hosts them. These tests render that page and
hold what a browser's stored preferences depend on, each control's layout
default, along with the groups, the help text, the toggle, and the stylesheet
rules that open and collapse the panel beside the graph.
"""

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import dash
import dash_mantine_components as dmc
import plotly.graph_objects as go
import pytest
from dash import Patch, no_update
from dash._callback import GLOBAL_CALLBACK_LIST, GLOBAL_CALLBACK_MAP

from source.components import chart_options, scenario_selection
from source.kovaaks.data_models import RunData
from source.kovaaks.play_sessions import split_into_play_sessions
from source.kovaaks.typical_score import build_typical_scores
from source.plot.plot_service import (
    MIDDLE_50_TRACE_NAME,
    MIDDLE_80_TRACE_NAME,
    TYPICAL_SCORE_TRACE_NAME,
    RunPointContext,
    generate_score_vs_run_plot,
    generate_score_vs_time_plot,
    generated_point_color,
    typical_score_hold_traces,
    typical_score_traces,
)
from tests.rendered_text import rendered_text

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import run_history  # noqa: E402

IDS = run_history.CHART_OPTIONS_IDS
STYLESHEET = Path(__file__).resolve().parents[1] / "assets" / "stylesheet.css"


def _context(runs):
    """Give figure-builder tests a single-session context."""
    return {
        run: RunPointContext(
            session_number=index,
            runs_ago=len(runs) - index,
            session_total=len(runs),
            session_name="Oct 10, 12:00 PM",
        )
        for index, run in enumerate(runs, 1)
    }


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
    """Render the page without touching disk and index the tree by component id."""
    monkeypatch.setattr(
        scenario_selection, "get_visible_playlist_selector_options", lambda: []
    )
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])

    return {
        component.id: component
        for component in _walk_components(run_history.layout())
        # A pattern-matching id is a dict, which cannot key this one.
        if isinstance(getattr(component, "id", None), str)
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
# tests/test_chart_point_appearance.py, where the rest of their behavior lives.
CHART_OPTIONS_INPUT_DEFAULTS = {
    IDS.rank_overlay: ("checked", True),
    IDS.show_all_ranks: ("checked", False),
    IDS.accuracy_targets: ("checked", False),
    IDS.high_score_overlay: ("checked", True),
    IDS.typical_score_overlay: ("checked", True),
    IDS.middle_50_overlay: ("checked", True),
    IDS.middle_80_overlay: ("checked", True),
    IDS.score_threshold_overlay: ("checked", True),
    IDS.score_threshold_percentage: ("value", 95),
}
COLLAPSED_PANEL_CLASS = (
    f"{chart_options.CHART_OPTIONS_PANEL_CLASS} "
    f"{chart_options.CHART_OPTIONS_PANEL_HIDDEN_CLASS}"
)


def test_chart_options_controls_have_help_tooltips(monkeypatch):
    """Coverage is per control id, wherever the control now lives."""
    components = _layout_components(monkeypatch)
    expected_settings = {
        run_history.FOLLOW_SWITCH_ID: "automatically-change-scenario",
        IDS.rank_overlay: "rank-overlay",
        IDS.show_all_ranks: "show-all-ranks",
        IDS.accuracy_targets: "accuracy-targets",
        IDS.high_score_overlay: "high-score-overlay",
        IDS.typical_score_overlay: "typical-score-overlay",
        IDS.middle_50_overlay: "middle-50-overlay",
        IDS.middle_80_overlay: "middle-80-overlay",
        IDS.score_threshold_overlay: "score-threshold-overlay",
        IDS.score_threshold_percentage: "score-threshold-percentage",
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
        # The panel's icons keep Mantine's sm; the Follow switch's is small to
        # keep its line short under the scenario dropdown.
        small = component_id == run_history.FOLLOW_SWITCH_ID
        assert tooltips[0].children.size == (16 if small else "sm")
        assert tooltips[0].boxWrapperProps == {
            "className": chart_options.SETTINGS_HELP_TARGET_CLASS
        }

    score_threshold_percentage = components[IDS.score_threshold_percentage]
    assert score_threshold_percentage.min == 1


def test_help_texts_state_the_ratified_copy_with_control_names_in_bold(monkeypatch):
    components = _layout_components(monkeypatch)
    expected = {
        IDS.show_all_ranks: (
            "Draws every rank in the playlist's ladder instead of only the ones "
            "around your plotted scores. Needs **Rank thresholds** turned on."
        ),
        IDS.accuracy_targets: (
            "Shows beside each rank line an estimate of the accuracy that rank "
            "needs when you hold the fire button for the whole run. It's "
            "calculated from your runs, on scenarios where your score follows "
            "your accuracy, such as tracking. Needs **Rank thresholds** turned on."
        ),
        IDS.score_threshold_percentage: (
            "Sets the score goal as a percentage of your personal best. On a "
            "scenario scored by completion time, it's a percentage of your "
            "personal best's pace instead, when the app can measure pace "
            "reliably. Otherwise, it stays a percentage of your score. The "
            "overlay line tracks your current personal best. A run is judged "
            "against the personal best you had before the run."
        ),
        IDS.typical_score_overlay: (
            "Draws your typical score: the median of your last 20 runs, or of "
            "all your runs if you have fewer. It's faded where too few of them "
            "are recent. **Score vs Sensitivity** doesn't show the line or bands."
        ),
        IDS.middle_50_overlay: (
            "Shades the middle 50% of the runs behind your typical score. A "
            "narrower band means more consistent scores. **Score vs "
            "Sensitivity** doesn't show this band."
        ),
        IDS.middle_80_overlay: (
            "Shades the middle 80% of the runs behind your typical score, in a "
            "lighter shade than the middle 50%. **Score vs Sensitivity** "
            "doesn't show this band."
        ),
    }

    for component_id, text in expected.items():
        (tooltip,) = [
            component
            for component in _walk_components(components[component_id].label)
            if isinstance(component, dmc.Tooltip)
        ]
        assert rendered_text(tooltip.label) == text


def test_chart_options_inputs_keep_their_defaults(monkeypatch):
    components = _layout_components(monkeypatch)

    for component_id, (prop, default) in CHART_OPTIONS_INPUT_DEFAULTS.items():
        control = components[component_id]

        assert getattr(control, prop) == default
        assert control.persistence is True


def test_chart_options_inputs_are_grouped_by_the_concept_they_share(monkeypatch):
    components = _layout_components(monkeypatch)
    panel = components[IDS.panel]

    labels = {
        component.id: _label_text(component)
        for component in _walk_components(panel)
        if getattr(component, "id", None) in CHART_OPTIONS_INPUT_DEFAULTS
    }

    assert labels == {
        IDS.rank_overlay: "Rank thresholds",
        IDS.show_all_ranks: "Show all ranks",
        IDS.accuracy_targets: "Accuracy targets",
        IDS.high_score_overlay: "PB score",
        IDS.typical_score_overlay: "Typical score",
        IDS.middle_50_overlay: "Middle 50%",
        IDS.middle_80_overlay: "Middle 80%",
        IDS.score_threshold_overlay: "Score threshold overlay",
        IDS.score_threshold_percentage: "Score threshold percentage",
    }


def test_the_typical_scores_switches_follow_pb_score_under_their_chosen_ids(
    monkeypatch,
):
    """A browser remembers each switch under its id, so the ids never change."""
    components = _layout_components(monkeypatch)
    (overlays,) = [
        group
        for group in components[IDS.panel].children
        if group.children[0].children == "Overlays"
    ]

    assert [control.id for control in overlays.children[1:]] == [
        IDS.rank_overlay,
        IDS.show_all_ranks,
        "run-history-accuracy-targets-switch",
        IDS.high_score_overlay,
        "run-history-typical-score-overlay-switch",
        "run-history-middle-50-overlay-switch",
        "run-history-middle-80-overlay-switch",
    ]
    # Each help icon is named for its switch, as every icon in the panel is.
    for control in overlays.children[3:]:
        (icon,) = [
            component
            for component in _walk_components(control.label)
            if isinstance(component, dmc.ActionIcon)
        ]
        assert icon.to_plotly_json()["props"]["aria-label"] == (
            f"{_label_text(control)} help"
        )


def test_the_panel_holds_three_groups_eleven_controls_and_no_notification_control(
    monkeypatch,
):
    """The run toast is app-wide, so its switch is on the Settings page.

    The Score threshold verdict switch went with the verdict it gated. An
    empty percentage is the one way left to stop runs being judged.
    """
    components = _layout_components(monkeypatch)
    panel = components[IDS.panel]

    assert [group.children[0].children for group in panel.children] == [
        "Overlays",
        "Run Data Points",
        "Score Threshold",
    ]
    controls = {
        component.id
        for component in _walk_components(panel)
        if isinstance(
            component,
            (dmc.Switch, dmc.NumberInput, dmc.SegmentedControl, dmc.ColorInput),
        )
    }
    assert controls == {
        IDS.rank_overlay,
        IDS.show_all_ranks,
        IDS.accuracy_targets,
        IDS.high_score_overlay,
        IDS.typical_score_overlay,
        IDS.middle_50_overlay,
        IDS.middle_80_overlay,
        IDS.point_size,
        IDS.point_color,
        IDS.score_threshold_overlay,
        IDS.score_threshold_percentage,
    }
    drawn = rendered_text(run_history.layout())
    for gone in ("Notifications", "Run notifications", "Score threshold verdict"):
        assert gone not in drawn
    # A browser's stored value for either is left behind, unused: no control
    # is drawn under the old ids, and nothing clears them.
    assert not {
        "run-history-run-notification-switch",
        "run-history-score-threshold-notification-switch",
    } & set(components)
    assert not hasattr(IDS, "run_notification")
    assert not hasattr(IDS, "score_threshold_notification")


def test_chart_options_panel_starts_collapsed_with_its_controls_mounted(monkeypatch):
    components = _layout_components(monkeypatch)
    panel = components[IDS.panel]
    toggle = components[IDS.toggle].to_plotly_json()["props"]

    # Collapsed is a class, never conditional rendering: the inputs stay in the
    # layout tree feeding their callbacks with their persisted values.
    assert panel.className == COLLAPSED_PANEL_CLASS
    mounted = {getattr(child, "id", None) for child in _walk_components(panel)}
    assert set(CHART_OPTIONS_INPUT_DEFAULTS) <= mounted

    assert toggle["children"] == "Chart options"
    assert toggle["aria-expanded"] == "false"
    assert toggle["aria-controls"] == IDS.panel


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


# A second page's ids, none of which the Run History page uses.
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


def test_the_page_registers_the_block_for_its_own_ids():
    """Registration is a call the page makes; without it all three go quiet."""
    assert {
        f"{IDS.graph}.figure",
        f"{IDS.point_color}.value",
        f"..{IDS.panel}.className...{IDS.toggle}.aria-expanded..",
    } <= set(GLOBAL_CALLBACK_MAP)


def test_a_second_page_builds_a_panel_that_shares_no_id_with_the_first(monkeypatch):
    first_page_ids = set(_layout_components(monkeypatch)) - {None}
    first_page_ids.add(IDS.point_size_label)

    # Mantine renders ``labelProps`` ids without a separate Dash component.
    built = {
        component_id
        for tree in (
            chart_options.chart_options_toggle(SECOND_PAGE_IDS),
            chart_options.chart_options_panel(SECOND_PAGE_IDS),
        )
        for component in _walk_components(tree)
        for component_id in (
            getattr(component, "id", None),
            getattr(component, "labelProps", {}).get("id"),
        )
        if component_id is not None
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

    chart_options.register_chart_options(SECOND_PAGE_IDS, latest_run="second-latest")

    added = {
        key: spec for key, spec in GLOBAL_CALLBACK_MAP.items() if key not in before
    }
    assert set(added) == {
        "second-graph.figure",
        "second-point_color.value",
        "..second-panel.className...second-toggle.aria-expanded..",
    }
    # The theme switch belongs to the shell, so both pages read the same one.
    # The store that names the latest run is the page's own.
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
        "second-latest",
    }
    assert all(GLOBAL_CALLBACK_MAP[key] is spec for key, spec in before.items())


# --- The ring round the latest run ---------------------------------------------------


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
def test_styling_the_graph_rings_only_the_run_reported_by_the_card(latest_run, opacity):
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
    # The rest of the styling is ``apply_graph_appearance``'s own.
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


def test_a_registration_gives_the_graph_one_writer_that_takes_the_latest_run(
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


# --- The typical score's colors ------------------------------------------------------


def _typical_score_plot() -> str:
    """Build a cached Score vs Run figure with the typical score's six traces.

    Twenty runs in one sitting make run 20's value known, and five runs two
    months later are faded, so both strengths of each metric are drawn.
    """
    runs = [
        RunData(
            datetime_object=first + timedelta(minutes=index),
            score=100.0 + index,
            sens_scale="cm/360",
            horizontal_sens=40.0,
            scenario="Scenario",
            accuracy=0.5,
        )
        for first, count in ((datetime(2026, 8, 1, 10), 20), (datetime(2026, 10, 1), 5))
        for index in range(count)
    ]
    today = date(2026, 10, 12)
    figure = generate_score_vs_run_plot(
        runs,
        1,
        "Scenario",
        False,
        [],
        False,
        (),
        today,
        run_context=_context(runs),
    )
    figure.add_traces(
        typical_score_traces(
            range(1, len(runs) + 1),
            build_typical_scores(runs, split_into_play_sessions(runs)),
            today,
            line=True,
            middle_50=True,
            middle_80=True,
        )
    )
    return figure.to_json()


@pytest.mark.parametrize(
    ("scheme", "line", "middle_50", "middle_80"),
    [
        ("light", "#343a40", "rgba(52, 58, 64, 0.14)", "rgba(52, 58, 64, 0.07)"),
        ("dark", "#dee2e6", "rgba(222, 226, 230, 0.14)", "rgba(222, 226, 230, 0.07)"),
    ],
)
def test_the_typical_scores_line_and_bands_take_each_themes_gray(
    scheme, line, middle_50, middle_80
):
    """Faded or not, by trace name; the run points keep their generated color."""
    plot_json = _typical_score_plot()
    figure = chart_options.apply_graph_appearance(scheme, plot_json, "Default", "")
    typical = [
        trace
        for trace in figure.data
        if trace.name
        in {TYPICAL_SCORE_TRACE_NAME, MIDDLE_50_TRACE_NAME, MIDDLE_80_TRACE_NAME}
    ]

    colors = {
        (trace.name, trace.opacity): trace.line.color
        if trace.name == TYPICAL_SCORE_TRACE_NAME
        else trace.fillcolor
        for trace in typical
    }
    assert colors == {
        (MIDDLE_80_TRACE_NAME, 0.35): middle_80,
        (MIDDLE_50_TRACE_NAME, 0.35): middle_50,
        (MIDDLE_80_TRACE_NAME, 1): middle_80,
        (MIDDLE_50_TRACE_NAME, 1): middle_50,
        (TYPICAL_SCORE_TRACE_NAME, 0.35): line,
        (TYPICAL_SCORE_TRACE_NAME, 1): line,
    }
    # The run points set no color, so they draw in the template's first.
    assert figure.data[0].name == "Run data point"
    assert figure.data[0].marker.color is None
    assert figure.layout.template.layout.colorway[0] == generated_point_color(scheme)
    # The line keeps its width, and the bands no outline, whatever the theme.
    assert {trace.line.width for trace in typical} == {0, 2.5}


def test_the_cached_figure_is_built_with_the_light_colors():
    """As the ring is, so a theme change only recolors."""
    figure = go.Figure(json.loads(_typical_score_plot()))

    assert {
        trace.line.color
        for trace in figure.data
        if trace.name == TYPICAL_SCORE_TRACE_NAME
    } == {"#343a40"}
    assert {
        trace.fillcolor for trace in figure.data if trace.name == MIDDLE_50_TRACE_NAME
    } == {"rgba(52, 58, 64, 0.14)"}


@pytest.mark.parametrize(
    ("scheme", "line", "middle_50", "middle_80"),
    [
        ("light", "#343a40", "rgba(52, 58, 64, 0.14)", "rgba(52, 58, 64, 0.07)"),
        ("dark", "#dee2e6", "rgba(222, 226, 230, 0.14)", "rgba(222, 226, 230, 0.07)"),
    ],
)
def test_score_vs_times_only_value_takes_each_themes_gray(
    scheme, line, middle_50, middle_80
):
    """The stroke and the bars that mark it are colored by their line, not a fill.

    Ten runs from two sessions: only the tenth is known.
    """
    runs = [
        RunData(
            datetime_object=datetime(2026, 10, 11 + index // 5, 10, index % 5),
            score=100.0 + index,
            sens_scale="cm/360",
            horizontal_sens=40.0,
            scenario="Scenario",
            accuracy=0.5,
        )
        for index in range(10)
    ]
    figure = generate_score_vs_time_plot(
        runs,
        "Scenario",
        False,
        [],
        False,
        (),
        run_context=_context(runs),
    )
    figure.add_traces(
        typical_score_hold_traces(
            build_typical_scores(runs, split_into_play_sessions(runs)),
            date(2026, 10, 12),
            line=True,
            middle_50=True,
            middle_80=True,
        )
    )

    themed = chart_options.apply_graph_appearance(
        scheme, figure.to_json(), "Default", ""
    )

    (stroke,) = [t for t in themed.data if t.name == TYPICAL_SCORE_TRACE_NAME]
    assert (stroke.marker.color, stroke.marker.line.color) == (line, line)
    bars = {t.name: t.line.color for t in themed.data if t.fill == "none"}
    assert bars == {MIDDLE_50_TRACE_NAME: middle_50, MIDDLE_80_TRACE_NAME: middle_80}
    assert themed.data[0].marker.color is None


# --- The stylesheet rules that open and collapse the panel ---------------------------


@pytest.fixture
def stylesheet():
    return STYLESHEET.read_text(encoding="utf-8")


def _css_block(css, selector):
    """Return the declarations of one top-level rule, by exact selector."""
    match = re.search(rf"(?m)^{re.escape(selector)} \{{(.*?)^\}}", css, re.DOTALL)
    assert match, f"no {selector} rule in the stylesheet"
    return match.group(1)


def test_collapsing_the_inspector_animates_the_track_the_graph_grows_into(
    stylesheet,
):
    """The graph has to grow and shrink, not jump.

    Plotly redraws off the ResizeObserver, so the animation is what turns one
    jump into a sequence of redraws -- and the panel holding its own width
    while the track moves under it is what keeps a lagging redraw from
    painting over the controls.
    """
    row = _css_block(stylesheet, ".home-chart-row")
    collapsed = _css_block(
        stylesheet,
        ".home-chart-row:has(> .chart-options-panel-hidden)",
    )
    panel = _css_block(stylesheet, ".chart-options-panel")

    assert "transition:" in row
    assert "grid-template-columns var(--chart-options-collapse-duration)" in row
    assert "overflow: hidden;" in row
    assert "grid-template-columns: minmax(0, 1fr) 0;" in collapsed
    assert "column-gap: 0;" in collapsed
    assert "width: 20rem;" in panel


def test_the_collapsed_panel_leaves_the_tab_order_after_the_animation(stylesheet):
    """display: none is what removes it; allow-discrete is what defers that
    flip to the end of the collapse instead of cancelling the animation."""
    hidden = _css_block(stylesheet, ".chart-options-panel-hidden")
    deferred = _css_block(
        stylesheet,
        ".chart-options-panel,\n.chart-options-panel-hidden",
    )

    assert "display: none;" in hidden
    assert "allow-discrete" in deferred
