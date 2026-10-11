"""Build the Chart options panel and its callbacks."""

import json

import dash_mantine_components as dmc
import plotly.graph_objects as go
from dash import Input, Output, State, callback, no_update

from source.components.control_name import control_name
from source.components.local_icon import local_icon
from source.plot.plot_service import (
    POINT_SIZE_DEFAULT,
    POINT_SIZE_OPTIONS,
    apply_light_dark_mode,
    apply_point_appearance,
    generate_placeholder_plot,
    generated_point_color,
)

TOOLTIP_EVENTS = {"hover": True, "focus": True, "touch": True}
SETTINGS_HELP_TOOLTIP_WIDTH = 280
SETTINGS_HELP_TEXT: dict[str, str | list] = {
    "automatically-change-scenario": (
        "Automatically selects the scenario you just played when a new run is detected."
    ),
    "rank-overlay": (
        "Shows the selected playlist's rank threshold lines on the graph when "
        "rank data is available."
    ),
    "show-all-ranks": [
        "Draws every rank in the playlist's ladder instead of only the ones "
        "around your plotted scores. Needs ",
        control_name("Rank thresholds"),
        " turned on.",
    ],
    "high-score-overlay": (
        "Shows your current personal best score as a reference line on the graph."
    ),
    "score-threshold-overlay": (
        "Shows a score goal line based on the selected percentage of your "
        "current personal best."
    ),
    "score-threshold-percentage": (
        "Sets the score goal as a percentage of your personal best. On a "
        "scenario scored by completion time, it's a percentage of your "
        "personal best's pace instead, when the app can measure pace "
        "reliably. Otherwise, it stays a percentage of your score. The "
        "overlay line tracks your current personal best. Notifications judge "
        "a run against the personal best you had before the run."
    ),
    "score-threshold-notification": [
        "Adds a pass or fail verdict to run notifications when the run can be "
        "judged against the score threshold. Needs ",
        control_name("Run notifications"),
        " turned on.",
    ],
    "run-notification": (
        "Controls threshold verdict and placement notifications for your runs. "
        "Personal best celebrations use their own setting."
    ),
    "top-n-scores": [
        "How many of your best scores to plot per sensitivity within the "
        "selected date range, or per day in ",
        control_name("Score vs Time"),
        ". A new run that lands in the top N also triggers a notification.",
    ],
}
# The chart options inspector. Its collapsed class is the open state: hiding
# with ``display: none`` takes the controls out of the tab order and the
# accessibility tree while leaving them mounted, so their persisted values keep
# feeding the graph callbacks either way.
CHART_OPTIONS_PANEL_ID = "chart-options-panel"
CHART_OPTIONS_TOGGLE_ID = "chart-options-toggle"
CHART_OPTIONS_PANEL_CLASS = "chart-options-panel"
CHART_OPTIONS_PANEL_HIDDEN_CLASS = "chart-options-panel-hidden"
# The Run Data Points group. Both controls persist in the browser like their
# siblings, so their layout defaults -- Default and an empty color -- must not
# move: changing a persisted control's layout default silently discards every
# value the browser already stored under its id.
CHART_OPTIONS_FIELD_CLASS = "chart-options-field"
CHART_OPTIONS_FIELD_LABEL_CLASS = "chart-options-field-label"
POINT_SIZE_INPUT_ID = "point-size"
POINT_SIZE_LABEL_ID = "point-size-label"
POINT_COLOR_INPUT_ID = "point-color"
POINT_COLOR_DEFAULT_ID = "point-color-default"
POINT_COLOR_DEFAULT = ""
# The empty field previews the generated point color. Mantine paints the
# preview of an empty ColorInput white, so the stylesheet repaints it from
# these custom properties while the placeholder shows, one per color scheme
# because the graph's templates differ; the values come from plot_service so
# the swatch and the graph cannot disagree.
POINT_COLOR_FIELD_CLASS = "point-color-field"
POINT_COLOR_DEFAULT_CSS_VARIABLES = {
    "light": "--point-color-default-light",
    "dark": "--point-color-default-dark",
}
# Eight color families, one shade each, chosen per family against both real
# plot backgrounds (#ffffff light, #242424 dark) rather than by taking one
# Mantine shade index across the board. Yellow, lime, gray, and dark are
# omitted; docs/decision_log.md carries the reasoning and the contrast table.
POINT_COLOR_SWATCHES = [
    "#1c7ed6",  # blue-7
    "#0c8599",  # cyan-8
    "#099268",  # teal-8
    "#2b8a3e",  # green-9
    "#d9480f",  # orange-9
    "#f03e3e",  # red-7
    "#be4bdb",  # grape-6
    "#e64980",  # pink-6
]


def _settings_help_label(label: str, help_text: str | list) -> dmc.Group:
    return dmc.Group(
        [
            # `inherit` so the label text takes the enclosing <label>'s font
            # instead of dmc.Text's own defaults (md/400). Without it these
            # labels render 16px/400 beside the 14px/700 of every label
            # passed as a plain string.
            dmc.Text(label, span=True, inherit=True),
            dmc.Tooltip(
                dmc.ActionIcon(
                    local_icon("material-symbols:info-outline", width=16),
                    className="settings-help-icon",
                    color="gray",
                    radius="xl",
                    size="sm",
                    variant="subtle",
                    **{"aria-label": f"{label} help"},
                ),
                label=help_text,
                events=TOOLTIP_EVENTS,
                multiline=True,
                withArrow=True,
                w=SETTINGS_HELP_TOOLTIP_WIDTH,
            ),
        ],
        align="center",
        gap="xs",
        wrap="nowrap",
    )


@callback(
    Output("graph-content", "figure"),
    Input("color-scheme-switch", "computedColorScheme"),
    Input("cached-plot", "data"),
    Input(POINT_SIZE_INPUT_ID, "value"),
    Input(POINT_COLOR_INPUT_ID, "value"),
)
def apply_graph_appearance(color_scheme, plot_json, point_size, point_color):
    """
    Applies the theme and the Run Data Points preferences to the graph.

    Everything here is presentation over the figure ``generate_graph`` already
    built and cached, which is what keeps a size or color change from
    rereading scenario data, rebuilding overlays, or firing notifications.
    :param color_scheme: active Mantine color scheme.
    :param plot_json: json object with plotted data.
    :param point_size: selected point size preset.
    :param point_color: explicit point color, or empty for Default.
    :return: Figure with theme and point preferences applied.
    """
    if not plot_json:
        plot_json = generate_placeholder_plot().to_json()
    figure = apply_light_dark_mode(go.Figure(json.loads(plot_json)), color_scheme)
    return apply_point_appearance(figure, point_size, point_color)


@callback(
    Output(POINT_COLOR_INPUT_ID, "value"),
    Input(POINT_COLOR_DEFAULT_ID, "n_clicks"),
    prevent_initial_call=True,
)
def clear_point_color(n_clicks):
    """
    Returns the point color to Default.
    :param n_clicks: clicks on the Use default action.
    :return: the empty value that means Default.
    """
    if not n_clicks:
        return no_update
    return POINT_COLOR_DEFAULT


def _chart_options_panel_class(opened: bool) -> str:
    """Return the inspector's class list for the open or collapsed state."""
    if opened:
        return CHART_OPTIONS_PANEL_CLASS
    return f"{CHART_OPTIONS_PANEL_CLASS} {CHART_OPTIONS_PANEL_HIDDEN_CLASS}"


@callback(
    Output(CHART_OPTIONS_PANEL_ID, "className"),
    Output(CHART_OPTIONS_TOGGLE_ID, "aria-expanded"),
    Input(CHART_OPTIONS_TOGGLE_ID, "n_clicks"),
    State(CHART_OPTIONS_PANEL_ID, "className"),
    prevent_initial_call=True,
)
def toggle_chart_options(n_clicks, panel_class):
    """Open or collapse the chart options inspector.

    The panel's class is the open state and ``aria-expanded`` rides with it, so
    the ``n_clicks`` guard is unconditional: the inspector starts closed on
    every visit, and under DashProxy a callback can fire once on page load with
    nothing triggering it, which would spring the panel open on arrival.
    """
    if not n_clicks:
        return no_update, no_update

    will_open = CHART_OPTIONS_PANEL_HIDDEN_CLASS in (panel_class or "")
    return _chart_options_panel_class(will_open), "true" if will_open else "false"


def _chart_options_group(title: str, controls: list) -> dmc.Stack:
    """Group the inspector's controls under the concept they share."""
    return dmc.Stack(
        [dmc.Title(title, order=3, size="h6"), *controls],
        gap="xs",
    )


def _chart_options_panel() -> dmc.Box:
    """Build the collapsible inspector that sits beside the chart."""
    return dmc.Box(
        id=CHART_OPTIONS_PANEL_ID,
        className=_chart_options_panel_class(False),
        children=[
            _chart_options_group(
                "Overlays",
                [
                    dmc.Switch(
                        id="rank-overlay-switch",
                        labelPosition="right",
                        label=_settings_help_label(
                            "Rank thresholds",
                            SETTINGS_HELP_TEXT["rank-overlay"],
                        ),
                        checked=True,
                        persistence=True,
                    ),
                    dmc.Switch(
                        id="show-all-ranks-switch",
                        labelPosition="right",
                        label=_settings_help_label(
                            "Show all ranks",
                            SETTINGS_HELP_TEXT["show-all-ranks"],
                        ),
                        checked=False,
                        persistence=True,
                    ),
                    dmc.Switch(
                        id="high-score-overlay-switch",
                        labelPosition="right",
                        label=_settings_help_label(
                            "PB score",
                            SETTINGS_HELP_TEXT["high-score-overlay"],
                        ),
                        checked=True,
                        persistence=True,
                    ),
                ],
            ),
            _chart_options_group(
                "Run Data Points",
                [
                    # SegmentedControl has no Mantine label slot, so the field
                    # carries its own and points the control at it -- the
                    # visible text is then the control's accessible name
                    # rather than a second one announced beside it.
                    dmc.Box(
                        className=CHART_OPTIONS_FIELD_CLASS,
                        children=[
                            dmc.Text(
                                "Point size",
                                id=POINT_SIZE_LABEL_ID,
                                className=CHART_OPTIONS_FIELD_LABEL_CLASS,
                            ),
                            dmc.SegmentedControl(
                                id=POINT_SIZE_INPUT_ID,
                                data=list(POINT_SIZE_OPTIONS),
                                value=POINT_SIZE_DEFAULT,
                                fullWidth=True,
                                persistence=True,
                                radius="sm",
                                size="sm",
                                **{"aria-labelledby": POINT_SIZE_LABEL_ID},
                            ),
                        ],
                    ),
                    dmc.Box(
                        className=f"{CHART_OPTIONS_FIELD_CLASS} {POINT_COLOR_FIELD_CLASS}",
                        style={
                            variable: generated_point_color(scheme)
                            for scheme, variable in POINT_COLOR_DEFAULT_CSS_VARIABLES.items()
                        },
                        children=[
                            dmc.ColorInput(
                                id=POINT_COLOR_INPUT_ID,
                                label="Point color",
                                value=POINT_COLOR_DEFAULT,
                                # An empty field is Default, and says so.
                                placeholder="Default",
                                format="hex",
                                swatches=POINT_COLOR_SWATCHES,
                                # The component defaults to seven per row,
                                # which would wrap the eighth onto a row of
                                # its own.
                                swatchesPerRow=len(POINT_COLOR_SWATCHES),
                                withEyeDropper=False,
                                # Picking a swatch is a finished choice, and
                                # the dropdown covers Use default while it
                                # is open.
                                closeOnColorSwatchClick=True,
                                persistence=True,
                                radius="sm",
                                size="sm",
                                w="100%",
                            ),
                            # The only way back to Default: the field has no
                            # clear affordance of its own, and re-typing an
                            # empty hex value is not one.
                            dmc.Group(
                                dmc.Button(
                                    "Use default",
                                    id=POINT_COLOR_DEFAULT_ID,
                                    variant="subtle",
                                    size="compact-xs",
                                ),
                                gap="xs",
                            ),
                        ],
                    ),
                ],
            ),
            _chart_options_group(
                "Score Threshold",
                [
                    dmc.Switch(
                        id="score-threshold-overlay-switch",
                        labelPosition="right",
                        label=_settings_help_label(
                            "Score threshold overlay",
                            SETTINGS_HELP_TEXT["score-threshold-overlay"],
                        ),
                        checked=True,
                        persistence=True,
                    ),
                    dmc.NumberInput(
                        id="score-threshold-percentage",
                        label=_settings_help_label(
                            "Score threshold percentage",
                            SETTINGS_HELP_TEXT["score-threshold-percentage"],
                        ),
                        min=1,
                        persistence=True,
                        placeholder="Percentage",
                        radius="sm",
                        size="sm",
                        variant="default",
                        value=95,
                        # Fills the rail. A Mantine label is only as wide as
                        # its input, so the modal's 12em box would wrap this
                        # label and strand its help icon on the line above.
                        w="100%",
                    ),
                    # Stays in this group, beside the percentage it judges
                    # against, even though the master switch it depends on
                    # lives in Notifications.
                    dmc.Switch(
                        id="score-threshold-notification-switch",
                        labelPosition="right",
                        label=_settings_help_label(
                            "Score threshold verdict",
                            SETTINGS_HELP_TEXT["score-threshold-notification"],
                        ),
                        checked=True,
                        persistence=True,
                    ),
                ],
            ),
            _chart_options_group(
                "Notifications",
                [
                    dmc.Switch(
                        id="run-notification-switch",
                        labelPosition="right",
                        label=_settings_help_label(
                            "Run notifications",
                            SETTINGS_HELP_TEXT["run-notification"],
                        ),
                        checked=True,
                        persistence=True,
                    ),
                ],
            ),
        ],
    )


def _chart_options_toggle() -> dmc.Button:
    """Build the disclosure button that opens and collapses the inspector."""
    return dmc.Button(
        "Chart options",
        id=CHART_OPTIONS_TOGGLE_ID,
        variant="default",
        rightSection=local_icon(
            "material-symbols:keyboard-arrow-down",
            className="chart-options-toggle-chevron",
            width=20,
        ),
        **{"aria-controls": CHART_OPTIONS_PANEL_ID, "aria-expanded": "false"},
    )


# Add Dash Mantine Component figure templates to Plotly's templates.
dmc.add_figure_templates()
