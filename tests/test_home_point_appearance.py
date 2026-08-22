"""The Run Data Points preferences restyle the cached figure and nothing else.

Point size and color are appearance, so they hang off the cheap callback that
themes the figure Home already built and cached -- never off ``generate_graph``,
which rereads scenario data, rebuilds overlays, and decides notifications. These
tests pin that split, the two controls' persisted layout defaults, and the
fallbacks that keep an unrecognized preference from breaking the graph.
"""

import json
import re
from datetime import datetime
from pathlib import Path

import dash
import dash_mantine_components as dmc
import plotly.graph_objs as go
import pytest

dash.Dash(__name__, use_pages=True, pages_folder="")

from dash._callback import GLOBAL_CALLBACK_MAP  # noqa: E402

from source.kovaaks.data_models import RunData  # noqa: E402
from source.pages import home  # noqa: E402
from source.plot.plot_service import (  # noqa: E402
    POINT_SIZE_PRESET_PX,
    RUN_DATA_POINT_DEFAULT_COLOR,
    RUN_DATA_POINT_TRACE_NAME,
    apply_light_dark_mode,
    generate_sensitivity_plot,
    generate_time_plot,
)

APPEARANCE_INPUT_IDS = {home.POINT_SIZE_INPUT_ID, home.POINT_COLOR_INPUT_ID}
STYLESHEET = Path(__file__).resolve().parents[1] / "assets" / "stylesheet.css"


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


@pytest.fixture
def components(monkeypatch) -> dict:
    """Render Home without touching disk and index the tree by component id."""
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])

    return {
        getattr(component, "id", None): component
        for component in _walk_components(home.layout())
    }


def _run(score: float) -> RunData:
    return RunData(
        datetime_object=datetime(2025, 1, 1, 10),
        score=score,
        sens_scale="Overwatch",
        horizontal_sens=2.0,
        scenario="1w4ts",
        accuracy=0.5,
    )


@pytest.fixture(params=["score_vs_sensitivity", "score_vs_time"])
def cached_plot(request) -> str:
    """A real cached-plot payload, one per graph mode."""
    runs = [_run(100.0), _run(120.0)]
    if request.param == "score_vs_sensitivity":
        figure = generate_sensitivity_plot({"2.0 Overwatch": runs}, "1w4ts", False, [])
    else:
        figure = generate_time_plot(
            {datetime(2025, 1, 1).date(): runs}, "1w4ts", False, []
        )
    return figure.to_json()


def _run_trace(figure: go.Figure):
    return next(
        trace for trace in figure.data if trace.name == RUN_DATA_POINT_TRACE_NAME
    )


def test_run_data_points_group_sits_between_overlays_and_score_threshold(components):
    panel = components[home.CHART_OPTIONS_PANEL_ID]

    titles = [
        component.children
        for component in _walk_components(panel)
        if isinstance(component, dmc.Title)
    ]

    assert titles == ["Overlays", "Run Data Points", "Score Threshold"]


def test_point_controls_are_mounted_with_the_defaults_persistence_relies_on(
    components,
):
    # Dash persistence is keyed by component id, and changing a layout default
    # silently wipes every value the browser already stored under it. Default
    # and an empty color are also what "leave the figure alone" means.
    size = components[home.POINT_SIZE_INPUT_ID]
    color = components[home.POINT_COLOR_INPUT_ID]

    assert size.value == "Default"
    assert size.data == ["Small", "Default", "Large"]
    assert size.fullWidth is True
    assert size.persistence is True

    assert color.value == ""
    assert color.label == "Point color"
    assert color.placeholder == "Default"
    assert color.persistence is True

    assert components[home.POINT_COLOR_DEFAULT_ID].children == "Use default"


def test_empty_point_color_field_previews_the_generated_color(components):
    # Mantine paints the preview of an empty ColorInput white, so the field
    # carries the generated color as a custom property and the stylesheet
    # repaints the swatch from it while the placeholder shows. The Python
    # side names both hooks; this holds the CSS to the same names.
    field = next(
        component
        for component in _walk_components(components[home.CHART_OPTIONS_PANEL_ID])
        if home.POINT_COLOR_FIELD_CLASS in getattr(component, "className", "")
    )

    assert home.POINT_COLOR_INPUT_ID in [
        getattr(child, "id", None) for child in field.children
    ]
    assert field.style == {
        home.POINT_COLOR_DEFAULT_CSS_VARIABLE: RUN_DATA_POINT_DEFAULT_COLOR
    }

    css = re.sub(r"\s+", " ", STYLESHEET.read_text(encoding="utf-8"))
    assert (
        f".{home.POINT_COLOR_FIELD_CLASS}:has(input:placeholder-shown)"
        " .mantine-ColorInput-colorPreview .mantine-ColorSwatch-colorOverlay"
        f" {{ background-color: var({home.POINT_COLOR_DEFAULT_CSS_VARIABLE})"
        " !important; }"
    ) in css


def test_generated_run_points_are_the_color_the_empty_field_previews(cached_plot):
    # px.scatter bakes Plotly's default-template color into the trace when
    # the figure is generated, and the Mantine templates applied afterwards
    # never override a property the trace already sets: the generated color
    # is one value in both themes, and it is the one the swatch shows.
    assert _run_trace(go.Figure(json.loads(cached_plot))).marker.color == (
        RUN_DATA_POINT_DEFAULT_COLOR
    )
    for color_scheme in ("light", "dark"):
        themed = home.apply_graph_appearance(color_scheme, cached_plot, "Default", "")
        assert _run_trace(themed).marker.color == RUN_DATA_POINT_DEFAULT_COLOR


def test_point_color_offers_the_curated_swatches_on_one_row(components):
    color = components[home.POINT_COLOR_INPUT_ID]

    assert color.swatches == [
        "#1c7ed6",
        "#0c8599",
        "#099268",
        "#2b8a3e",
        "#d9480f",
        "#f03e3e",
        "#be4bdb",
        "#e64980",
    ]
    # The component's own default is seven per row, which would strand the
    # eighth swatch on a row of its own.
    assert color.swatchesPerRow == len(color.swatches)
    # Hex keeps alpha out of the feature; the eyedropper waits for a v2.
    assert color.format == "hex"
    assert color.withEyeDropper is False
    # The open dropdown covers Use default, and picking a swatch is a
    # finished choice.
    assert color.closeOnColorSwatchClick is True


def test_point_size_is_named_by_its_own_visible_label(components):
    # SegmentedControl has no Mantine label slot, so the visible text becomes
    # the control's accessible name by reference rather than by proximity.
    size = components[home.POINT_SIZE_INPUT_ID].to_plotly_json()["props"]
    label = components[home.POINT_SIZE_LABEL_ID]

    assert label.children == "Point size"
    assert size["aria-labelledby"] == home.POINT_SIZE_LABEL_ID


def test_default_size_and_empty_color_leave_the_cached_figure_untouched(
    cached_plot,
):
    styled = home.apply_graph_appearance("light", cached_plot, "Default", "").to_json()
    themed_only = apply_light_dark_mode(
        go.Figure(json.loads(cached_plot)), "light"
    ).to_json()

    assert styled == themed_only


def test_size_and_color_reach_only_the_run_trace_in_both_graph_modes(cached_plot):
    figure = home.apply_graph_appearance("dark", cached_plot, "Large", "#f03e3e")

    run_trace = _run_trace(figure)
    assert run_trace.marker.size == POINT_SIZE_PRESET_PX["Large"]
    assert run_trace.marker.color == "#f03e3e"

    average = next(trace for trace in figure.data if trace.name == "Average Score")
    assert average.marker.size is None
    assert average.marker.color is None

    # Appearance is not analysis: the axes and the trace names the legend and
    # hover labels read from stay the ones generate_graph produced.
    untouched = home.apply_graph_appearance("dark", cached_plot, "Default", "")
    assert figure.layout.xaxis.title.text == untouched.layout.xaxis.title.text
    assert figure.layout.yaxis.title.text == untouched.layout.yaxis.title.text
    assert [trace.name for trace in figure.data] == [
        trace.name for trace in untouched.data
    ]


def test_unusable_preferences_fall_back_to_the_generated_appearance(cached_plot):
    base = home.apply_graph_appearance("light", cached_plot, "Default", "").to_json()

    for size, color in (("Enormous", "not-a-color"), (None, None), ("", "#12")):
        assert (
            home.apply_graph_appearance("light", cached_plot, size, color).to_json()
            == base
        )


def test_placeholder_and_empty_figures_tolerate_every_persisted_preference():
    empty = home._empty_plot_json("No runs to plot", "Nothing here yet.")

    for plot_json in (None, "", empty):
        for size in ("Small", "Default", "Large", "Enormous"):
            for color in ("", "#1c7ed6", "not-a-color"):
                figure = home.apply_graph_appearance("dark", plot_json, size, color)

                assert isinstance(figure, go.Figure)
                assert not any(
                    trace.name == RUN_DATA_POINT_TRACE_NAME for trace in figure.data
                )


def test_theme_switches_keep_an_explicit_color_and_leave_default_generated(
    cached_plot,
):
    for color_scheme in ("light", "dark"):
        explicit = _run_trace(
            home.apply_graph_appearance(color_scheme, cached_plot, "Small", "#099268")
        )
        assert explicit.marker.color == "#099268"
        assert explicit.marker.size == POINT_SIZE_PRESET_PX["Small"]

    # Default keeps whatever the cached figure gives it, so the two themes
    # differ only where the base figure does.
    default = [
        _run_trace(
            home.apply_graph_appearance(color_scheme, cached_plot, "Default", "")
        ).marker.color
        for color_scheme in ("light", "dark")
    ]
    base_color = _run_trace(go.Figure(json.loads(cached_plot))).marker.color
    assert default == [base_color, base_color]


def test_use_default_clears_the_color_and_ignores_a_phantom_click():
    assert home.clear_point_color(1) == ""
    # Under DashProxy a callback can fire once on page load with no click.
    assert home.clear_point_color(None) is dash.no_update
    assert home.clear_point_color(0) is dash.no_update


def test_appearance_preferences_never_reach_the_expensive_graph_callback():
    inputs = {
        key: {entry["id"] for entry in spec["inputs"]}
        for key, spec in GLOBAL_CALLBACK_MAP.items()
        if "cached-plot.data" in key or key == "graph-content.figure"
    }

    figure_inputs = inputs.pop("graph-content.figure")
    assert APPEARANCE_INPUT_IDS <= figure_inputs

    # Whatever else it outputs, the callback that writes cached-plot is the one
    # that rereads scenario data and decides notifications.
    (generate_graph_inputs,) = inputs.values()
    assert not APPEARANCE_INPUT_IDS & generate_graph_inputs
