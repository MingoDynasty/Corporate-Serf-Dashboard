"""Build the Chart options panel and wire its callbacks to a page's ids.

A page that hosts the panel fills in a ``ChartOptionsIds``, builds
``chart_options_toggle`` and ``chart_options_panel`` from it in its layout,
and calls ``register_chart_options`` with it once, at import. The callbacks
are plain functions here and are registered once per page.
"""

import json
from typing import NamedTuple

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
# What the Score threshold percentage help says on both pages, before the
# sentence about what judges a run, which each page words for itself.
_SCORE_THRESHOLD_PERCENTAGE_HELP = (
    "Sets the score goal as a percentage of your personal best. On a "
    "scenario scored by completion time, it's a percentage of your "
    "personal best's pace instead, when the app can measure pace "
    "reliably. Otherwise, it stays a percentage of your score. The "
    "overlay line tracks your current personal best. "
)
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
        _SCORE_THRESHOLD_PERCENTAGE_HELP
        + "Notifications judge a run against the personal best you had before "
        "the run."
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
    # The Run History page's wording of two of the texts above. Its Follow
    # clears a playlist filter that does not list the scenario just played,
    # and on it a toast is not the only thing that judges a run.
    "automatically-change-scenario-run-history": [
        "Automatically selects the scenario you just played when a new run is "
        "detected. If the ",
        control_name("Playlist filter"),
        " doesn't list that scenario, the filter is cleared.",
    ],
    "score-threshold-percentage-run-history": (
        _SCORE_THRESHOLD_PERCENTAGE_HELP
        + "A run is judged against the personal best you had before the run."
    ),
}
# The chart options inspector. Its collapsed class is the open state: hiding
# with ``display: none`` takes the controls out of the tab order and the
# accessibility tree while leaving them mounted, so their persisted values keep
# feeding the graph callbacks either way.
CHART_OPTIONS_PANEL_CLASS = "chart-options-panel"
CHART_OPTIONS_PANEL_HIDDEN_CLASS = "chart-options-panel-hidden"
# The Run Data Points group. Both controls persist in the browser like their
# siblings, so their layout defaults -- Default and an empty color -- must not
# move: changing a persisted control's layout default silently discards every
# value the browser already stored under its id.
CHART_OPTIONS_FIELD_CLASS = "chart-options-field"
CHART_OPTIONS_FIELD_LABEL_CLASS = "chart-options-field-label"
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
# omitted; the 2026-08-20 entry in docs/decision_log/ carries the reasoning
# and the contrast table.
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


class ChartOptionsIds(NamedTuple):
    """The component ids one page gives its Chart options block.

    Two pages need two sets: the callbacks are registered once per set, and
    Dash allows one callback per output. The browser stores a remembered
    control's value under its id, so changing an id a page already uses
    resets that setting for every user.

    ``graph`` and ``cached_plot`` are the page's own. The block reads the
    unstyled figure from the store and writes the styled one to the graph,
    and builds neither.
    """

    panel: str
    toggle: str
    rank_overlay: str
    show_all_ranks: str
    high_score_overlay: str
    point_size: str
    point_size_label: str
    point_color: str
    point_color_default: str
    score_threshold_overlay: str
    score_threshold_percentage: str
    score_threshold_notification: str
    run_notification: str
    graph: str
    cached_plot: str


def settings_help_label(label: str, help_text: str | list) -> dmc.Group:
    """Build a control's label with a help icon that shows the text on hover."""
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


def apply_graph_appearance(color_scheme, plot_json, point_size, point_color):
    """Apply the theme and the Run Data Points preferences to the graph.

    Everything here is presentation over the figure the page's chart callback
    already built and cached, which is what keeps a size or color change from
    rereading scenario data, rebuilding overlays, or firing notifications.
    ``plot_json`` is that cached figure, and ``point_color`` is an explicit
    color or empty for Default.
    """
    if not plot_json:
        plot_json = generate_placeholder_plot().to_json()
    figure = apply_light_dark_mode(go.Figure(json.loads(plot_json)), color_scheme)
    return apply_point_appearance(figure, point_size, point_color)


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


def chart_options_panel(
    ids: ChartOptionsIds,
    *,
    score_threshold_percentage_help: str | list = SETTINGS_HELP_TEXT[
        "score-threshold-percentage"
    ],
    score_threshold_percentage_waits_for_commit: bool = False,
) -> dmc.Box:
    """Build the collapsible inspector that sits beside the chart.

    ``score_threshold_percentage_help`` is the help text of the Score
    threshold percentage field, which says what judges a run and so differs
    between the pages that host the panel.

    ``score_threshold_percentage_waits_for_commit`` makes that field send its
    value on Enter or on losing focus, where it otherwise sends every
    keystroke. A page that marks every listed run by the percentage sets it:
    typing 90 over 95 passes through 9, and every mark would flicker through
    it.
    """
    # Left out unless asked for. An explicit ``False`` is still a prop in the
    # layout a browser is sent, and a page that does not ask for this must go
    # on serving the layout it serves.
    percentage_commit = (
        {"debounce": True} if score_threshold_percentage_waits_for_commit else {}
    )
    return dmc.Box(
        id=ids.panel,
        className=_chart_options_panel_class(False),
        children=[
            _chart_options_group(
                "Overlays",
                [
                    dmc.Switch(
                        id=ids.rank_overlay,
                        labelPosition="right",
                        label=settings_help_label(
                            "Rank thresholds",
                            SETTINGS_HELP_TEXT["rank-overlay"],
                        ),
                        checked=True,
                        persistence=True,
                    ),
                    dmc.Switch(
                        id=ids.show_all_ranks,
                        labelPosition="right",
                        label=settings_help_label(
                            "Show all ranks",
                            SETTINGS_HELP_TEXT["show-all-ranks"],
                        ),
                        checked=False,
                        persistence=True,
                    ),
                    dmc.Switch(
                        id=ids.high_score_overlay,
                        labelPosition="right",
                        label=settings_help_label(
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
                                id=ids.point_size_label,
                                className=CHART_OPTIONS_FIELD_LABEL_CLASS,
                            ),
                            dmc.SegmentedControl(
                                id=ids.point_size,
                                data=list(POINT_SIZE_OPTIONS),
                                value=POINT_SIZE_DEFAULT,
                                fullWidth=True,
                                persistence=True,
                                radius="sm",
                                size="sm",
                                **{"aria-labelledby": ids.point_size_label},
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
                                id=ids.point_color,
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
                                    id=ids.point_color_default,
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
                        id=ids.score_threshold_overlay,
                        labelPosition="right",
                        label=settings_help_label(
                            "Score threshold overlay",
                            SETTINGS_HELP_TEXT["score-threshold-overlay"],
                        ),
                        checked=True,
                        persistence=True,
                    ),
                    dmc.NumberInput(
                        id=ids.score_threshold_percentage,
                        label=settings_help_label(
                            "Score threshold percentage",
                            score_threshold_percentage_help,
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
                        **percentage_commit,
                    ),
                    # Stays in this group, beside the percentage it judges
                    # against, even though the master switch it depends on
                    # lives in Notifications.
                    dmc.Switch(
                        id=ids.score_threshold_notification,
                        labelPosition="right",
                        label=settings_help_label(
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
                        id=ids.run_notification,
                        labelPosition="right",
                        label=settings_help_label(
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


def chart_options_toggle(ids: ChartOptionsIds) -> dmc.Button:
    """Build the disclosure button that opens and collapses the inspector."""
    return dmc.Button(
        "Chart options",
        id=ids.toggle,
        variant="default",
        rightSection=local_icon(
            "material-symbols:keyboard-arrow-down",
            className="chart-options-toggle-chevron",
            width=20,
        ),
        **{"aria-controls": ids.panel, "aria-expanded": "false"},
    )


def register_chart_options(ids: ChartOptionsIds) -> None:
    """Register the block's callbacks for one page's ids.

    Call once per page, at import, with the ids its layout is built from. The
    theme comes from the shell's color scheme switch, which every page shares.
    """
    callback(
        Output(ids.graph, "figure"),
        Input("color-scheme-switch", "computedColorScheme"),
        Input(ids.cached_plot, "data"),
        Input(ids.point_size, "value"),
        Input(ids.point_color, "value"),
    )(apply_graph_appearance)
    callback(
        Output(ids.point_color, "value"),
        Input(ids.point_color_default, "n_clicks"),
        prevent_initial_call=True,
    )(clear_point_color)
    callback(
        Output(ids.panel, "className"),
        Output(ids.toggle, "aria-expanded"),
        Input(ids.toggle, "n_clicks"),
        State(ids.panel, "className"),
        prevent_initial_call=True,
    )(toggle_chart_options)


# Add Dash Mantine Component figure templates to Plotly's templates.
dmc.add_figure_templates()
