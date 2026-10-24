"""
This module handles functions around plots.
"""

import logging
import re
from collections.abc import Callable, Collection, Mapping, Sequence
from datetime import date, datetime
from itertools import groupby
from operator import attrgetter
from typing import NamedTuple, cast

import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import plotly.io as pio

from source.kovaaks.data_models import Rank, RunData, run_id
from source.kovaaks.typical_score import (
    TypicalScore,
    TypicalScoreRecency,
    format_typical_score,
    typical_score_fade_time,
    typical_score_recency,
)
from source.utilities.utilities import (
    format_absolute_timestamp,
    format_decimal,
    format_short_date,
)

logger = logging.getLogger(__name__)

# The raw-run scatter's trace name. It is the handle the Run Data Points
# preferences select on: index 0 is an implementation detail of how the
# combined figure is assembled, while the name is what the legend, the hover
# template, and the appearance callback all already agree on.
RUN_DATA_POINT_TRACE_NAME = "Run data point"
# The Mantine figure template each color scheme draws with. The run trace
# sets no color of its own, so the template's colorway is what colors the
# points, and it is also where the Point color field's Default preview comes
# from.
_THEME_TEMPLATES = {"light": "mantine_light", "dark": "mantine_dark"}

POINT_SIZE_DEFAULT = "Default"
# The size presets a reader chooses between. Default is deliberately absent
# from the pixel map below: it means "leave marker.size alone", so the graph
# keeps whatever Plotly and the Mantine template give it and future template
# changes flow through without migrating a stored pixel count.
POINT_SIZE_OPTIONS = ("Small", POINT_SIZE_DEFAULT, "Large")
POINT_SIZE_PRESET_PX = {"Small": 4, "Large": 10}

# The trace of stars on the runs that set a new PB, and the handle the Point
# size preference sizes it by. Its name is the legend entry.
NEW_PB_TRACE_NAME = "New PB"
# One gold for both themes. On the light plot background the fill alone is
# too faint to find, so the dark outline is what carries the mark there, and
# the star shape keeps it apart from run points set to the same gold.
_NEW_PB_FILL_COLOR = "#fab005"
_NEW_PB_OUTLINE_COLOR = "#5f3d00"
# A star reads smaller than a circle of the same size, so each of these is
# about twice the run point's size at that preset. The Default size is
# written into the generated figure, where the run points leave theirs to
# plotly: plotly's default is the run point's size, not a star's.
NEW_PB_SIZE_DEFAULT_PX = 12
NEW_PB_SIZE_PRESET_PX = {"Small": 9, "Large": 16}

# The trace that rings one run on a Run History figure: the scenario's newest
# run, matched to the selected scenario's latest run on the card.
# The name is the handle the ring is shown, hidden, and sized by. It is never
# a legend entry.
LATEST_RUN_TRACE_NAME = "Latest run"
# The app's blue, darker on the light plot background and lighter on the
# dark one, so the ring stands off both.
_LATEST_RUN_RING_COLORS = {"light": "#1c7ed6", "dark": "#74c0fc"}
# Wide enough to clear a New PB star at the same preset, so a ringed new PB
# shows both.
LATEST_RUN_RING_SIZE_DEFAULT_PX = 18
LATEST_RUN_RING_SIZE_PRESET_PX = {"Small": 14, "Large": 22}

# The typical score's line and its two bands. Each name is the metric's legend
# entry, its legend group, so a click hides its faded stretches with it, and
# the handle the theme colors it by.
TYPICAL_SCORE_TRACE_NAME = "Typical score"
MIDDLE_50_TRACE_NAME = "Middle 50%"
MIDDLE_80_TRACE_NAME = "Middle 80%"
# After the run points and the stars, which keep plotly's default rank, 1000.
_TYPICAL_SCORE_LEGEND_RANKS = {
    TYPICAL_SCORE_TRACE_NAME: 1001,
    MIDDLE_50_TRACE_NAME: 1002,
    MIDDLE_80_TRACE_NAME: 1003,
}
# One gray per theme, the bands as shares of it. A figure is built with the
# light colors, and the theme step recolors them by trace name.
_TYPICAL_SCORE_COLORS = {
    "light": {
        TYPICAL_SCORE_TRACE_NAME: "#343a40",
        MIDDLE_50_TRACE_NAME: "rgba(52, 58, 64, 0.14)",
        MIDDLE_80_TRACE_NAME: "rgba(52, 58, 64, 0.07)",
    },
    "dark": {
        TYPICAL_SCORE_TRACE_NAME: "#dee2e6",
        MIDDLE_50_TRACE_NAME: "rgba(222, 226, 230, 0.14)",
        MIDDLE_80_TRACE_NAME: "rgba(222, 226, 230, 0.07)",
    },
}
# A stretch whose values weren't recent at their runs.
_TYPICAL_SCORE_FADED_OPACITY = 0.35
_TYPICAL_SCORE_LINE_WIDTH_PX = 2.5
# How wide the stroke and the bars are that mark Score vs Time's only value,
# about a New PB star's width.
_TYPICAL_SCORE_MOMENT_WIDTH_PX = 14

# The legend of every score chart, laid out horizontally above the plot
# instead of in Plotly's default right-hand column: a few entries never
# earned a reserved column, and the plot is the scarce thing on the page. It
# lands in the top margin the title already reserved, so the plot area keeps
# its full height and gains the column's width. Right-anchored to balance the
# left-aligned title. On a narrow chart, such as one beside the open options
# panel, the entries run into the title and can wrap over it. The maintainer
# accepted that and kept this placement over a legend under the plot (#399,
# closed unmerged).
_LEGEND_ABOVE_PLOT = {
    "orientation": "h",
    "x": 1,
    "xanchor": "right",
    "y": 1.02,
    "yanchor": "bottom",
}

_RUN_POINT_HOVER = (
    "%{customdata[0]}<br><br>"
    "<b>Score</b>: %{y}<br>"
    "<b>Run</b>: %{customdata[2]} (overall)<br>"
    "<b>Run</b>: %{customdata[1]} (this session)"
)

# What the Score vs Run axis assumes when it thins its date labels: the width
# of the plot area, and the room one character and one label's margin take.
# The figure is built on the server, which never learns how wide the chart
# is drawn, so the labels are spaced for a narrow one. The plot is 331px wide
# in a 1600px window with the options panel open beside it (measured in Edge
# and Firefox, 2026-10-12). A wider chart shows the same labels further
# apart. On a narrower one plotly.js tilts the labels that no longer fit,
# which is its own default for an axis that sets no tick angle.
_RUN_AXIS_ASSUMED_PLOT_WIDTH_PX = 330
_RUN_AXIS_LABEL_CHARACTER_PX = 8
_RUN_AXIS_LABEL_MARGIN_PX = 14

# ColorInput is set to hex, so this is the whole shape a stored value can
# legitimately have. Anything else -- a cleared field's "", a hand-typed
# fragment, a value from an older format -- means Default.
_HEX_COLOR_PATTERN = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")


def generate_placeholder_plot() -> go.Figure:
    """Build a neutral transparent figure for graph panels awaiting data."""
    figure = go.Figure()
    figure.update_layout(
        dragmode=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return figure


def generate_empty_plot(title: str, message: str) -> go.Figure:
    """Build an intentional empty-state figure for graph panels without data."""
    figure = go.Figure()
    figure.update_layout(
        dragmode=False,
        annotations=[
            {
                "text": f"<b>{title}</b>",
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.58,
                "showarrow": False,
                "align": "center",
                "font": {"size": 22},
            },
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.46,
                "showarrow": False,
                "align": "center",
                "font": {"size": 15},
            },
        ],
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"l": 40, "r": 40, "t": 40, "b": 40},
    )
    return figure


def add_high_score_overlay(figure: go.Figure, high_score: float) -> go.Figure:
    """Add a labeled high-score line to a figure."""
    figure.add_hline(
        name="PB Score",
        annotation_text=f"PB score ({format_decimal(high_score):.2f})",
        y=high_score,
        line_dash="dash",
    )
    return figure


def add_score_threshold_overlay(figure: go.Figure, score_threshold: float) -> go.Figure:
    """Add a labeled score-threshold line to a figure."""
    figure.add_hline(
        name="Score Threshold",
        annotation_text=f"Score threshold ({format_decimal(score_threshold):.2f})",
        y=score_threshold,
        line_dash="dash",
    )
    return figure


def _add_rank_overlays(
    figure: go.Figure,
    rank_overlay_switch: bool,
    rank_data: list[Rank],
    scores: list[float],
    show_all_ranks: bool = False,
) -> None:
    """Overlay rank threshold lines spanning the plotted score range.

    With ``show_all_ranks`` the bracketing selection is skipped and the whole
    ladder is drawn, so the y-axis stretches to cover every threshold.
    """
    if not (rank_overlay_switch and rank_data):
        return

    # Select by threshold value, not ladder index, so the overlay is robust to
    # non-monotonic rank ladders in upstream KovaaK's data. We draw every rank
    # whose threshold lands inside the plotted score range, plus the nearest
    # context rank strictly below and strictly above that range (including any
    # ties at those boundary thresholds). This is a strict generalization of
    # the old index-bracketing: for strictly ascending ladders the selection is
    # identical (with equal thresholds the new code draws all tied ranks where
    # the old drew one).
    low = float(min(scores))
    high = float(max(scores))

    thresholds_below = [r.threshold for r in rank_data if r.threshold < low]
    thresholds_above = [r.threshold for r in rank_data if r.threshold > high]
    nearest_below = max(thresholds_below) if thresholds_below else None
    nearest_above = min(thresholds_above) if thresholds_above else None

    def _is_selected(threshold: float) -> bool:
        if show_all_ranks:
            return True
        return low <= threshold <= high or threshold in (nearest_below, nearest_above)

    # Draw in original ladder order; do not sort or mutate rank_data (shared).
    for rank in rank_data:
        if not _is_selected(rank.threshold):
            continue
        figure.add_hline(
            name=rank.name,
            annotation_text=f"{rank.name} ({format_decimal(rank.threshold)}) ",
            y=rank.threshold,
            line_dash="dash",
            line_color=rank.color,
        )


def _new_high_scores_last(
    runs: list[RunData],
    new_high_score_runs: Collection[RunData],
) -> list[RunData]:
    """Order a group's runs so a new PB follows the runs that tie its score.

    A group's runs with one score are drawn at one point, and plotly.js
    answers a hover there with whichever comes last in the trace (observed on
    the bundled plotly.js, not documented). In time order that is the later
    run, which only tied the PB, so the star's hover would name the wrong
    run. Nothing else moves, and a group with no new PB keeps its order.
    """
    last_with_score = {run.score: index for index, run in enumerate(runs)}

    def draw_order(indexed_run: tuple[int, RunData]) -> tuple[int, bool]:
        index, run = indexed_run
        if run in new_high_score_runs:
            return last_with_score[run.score], True
        return index, False

    return [run for _, run in sorted(enumerate(runs), key=draw_order)]


def _new_pb_trace(
    x_values: Sequence[float | str | date],
    scores: Sequence[float],
    *,
    ids: Sequence[str],
    customdata: Sequence[Sequence[float | str]],
    hovertemplate: str,
) -> go.Scatter:
    """Build the trace of stars drawn over the runs that set a new PB."""
    return go.Scatter(
        x=list(x_values),
        y=list(scores),
        mode="markers",
        name=NEW_PB_TRACE_NAME,
        ids=list(ids),
        meta="run-history-run",
        # Stars remain identifiable with the run-points trace hidden.
        # Reuse each run's tooltip so overlap still names that run.
        customdata=list(customdata),
        hovertemplate=hovertemplate,
        hoverlabel={"font_size": 16},
        marker={
            "symbol": "star",
            "size": NEW_PB_SIZE_DEFAULT_PX,
            "color": _NEW_PB_FILL_COLOR,
            "line": {"color": _NEW_PB_OUTLINE_COLOR, "width": 1},
        },
    )


def _latest_run_ring_trace(
    x_value: float | str | datetime,
    score: float,
    run_id: str,
) -> go.Scatter:
    """Build the ring drawn round one run's point, tagged with that run's id.

    ``show_latest_run_ring`` decides whether it shows, by the id in ``meta``.
    """
    return go.Scatter(
        x=[x_value],
        y=[score],
        mode="markers",
        name=LATEST_RUN_TRACE_NAME,
        meta=run_id,
        # The ring says nothing a legend entry or a hover could add: the run
        # point inside it already answers a hover.
        showlegend=False,
        hoverinfo="skip",
        marker={
            "symbol": "circle-open",
            "size": LATEST_RUN_RING_SIZE_DEFAULT_PX,
            "color": _LATEST_RUN_RING_COLORS["light"],
            "line": {"width": 2},
        },
    )


def latest_run_ring_opacity(ringed_run_id: object, latest_run_id: str | None) -> int:
    """Return the ring's opacity: shown only round the run the card reports.

    The ring is hidden by its opacity and never by ``visible``. plotly.js
    leaves a trace that is not visible out of its axis ranges, and the ring
    is wider than a run point, so hiding it that way would move every point
    on an axis the ring had been padding.
    """
    return 1 if latest_run_id is not None and ringed_run_id == latest_run_id else 0


def show_latest_run_ring(
    figure: go.Figure,
    latest_run_id: str | None,
    color_scheme: str,
) -> go.Figure:
    """Show a figure's ring if it matches the card's run, in place.

    A Run History figure rings its scenario's newest run. ``latest_run_id``
    is the id of the selected scenario's latest run, so the two match while
    the figure and card show the same scenario and run. A figure with no ring, as
    when the newest run is outside the range, is left as it is.
    """
    color = _LATEST_RUN_RING_COLORS.get(color_scheme, _LATEST_RUN_RING_COLORS["light"])
    figure.for_each_trace(
        lambda trace: trace.update(
            opacity=latest_run_ring_opacity(trace.meta, latest_run_id),
            marker={"color": color},
        ),
        selector={"name": LATEST_RUN_TRACE_NAME},
    )
    return figure


class _TypicalScorePoint(NamedTuple):
    """A known typical score at one place on the chart, judged recent at its run.

    ``aged_out`` marks a point on the faded part of a Score vs Time hold whose
    value was recent at its run: its count at the run would read as recent.
    """

    x: float | datetime
    value: TypicalScore
    recency: TypicalScoreRecency
    aged_out: bool = False


def _typical_score_stretches(
    x_values: Sequence[float], values: Sequence[TypicalScore]
) -> tuple[list[list[_TypicalScorePoint]], list[list[_TypicalScorePoint]]]:
    """Split the known values into full-strength and faded stretches.

    A value is judged at its own newest run, the run it is plotted at. A
    faded stretch takes in the full-strength point on each side of it, so
    the two kinds meet at a point and the line has no gap or step there. An
    unknown value ends a stretch and has no point.
    """
    points = [
        _TypicalScorePoint(
            x_value, value, typical_score_recency(value, value.last_date)
        )
        if value.known
        else None
        for x_value, value in zip(x_values, values, strict=True)
    ]
    groups = [
        list(group)
        for _strength, group in groupby(
            points, key=lambda point: None if point is None else point.recency.recent
        )
    ]
    full: list[list[_TypicalScorePoint]] = []
    faded: list[list[_TypicalScorePoint]] = []
    for index, group in enumerate(groups):
        first = group[0]
        if first is None:
            continue
        stretch = cast("list[_TypicalScorePoint]", group)
        if first.recency.recent:
            full.append(stretch)
            continue
        before = groups[index - 1][-1] if index > 0 else None
        after = groups[index + 1][0] if index + 1 < len(groups) else None
        faded.append(
            [
                *([before] if before is not None else []),
                *stretch,
                *([after] if after is not None else []),
            ]
        )
    return full, faded


def _typical_score_hover_template(
    *, middle_50: bool, middle_80: bool, held: bool = False
) -> str:
    """Return the line's hover, its words fixed and its figures from ``customdata``.

    A band's line shows only with its band. The figures are each point's
    ``_typical_score_hover_data``, in this order. ``held`` is Score vs Time,
    whose Recent line is a whole figure: a hold's faded part reads otherwise.
    """
    lines = [
        "<b>Typical score</b>: %{customdata[0]}",
        "<b>Runs</b>: %{customdata[1]}",
        "<b>Recent</b>: %{customdata[2]}"
        if held
        else "<b>Recent</b>: %{customdata[2]} in the 30 days up to this run",
    ]
    index = 3
    for shown, label in ((middle_50, "Middle 50%"), (middle_80, "Middle 80%")):
        if shown:
            lines.append(
                f"<b>{label}</b>: %{{customdata[{index}]}} to "
                f"%{{customdata[{index + 1}]}}"
            )
            index += 2
    return "<br>".join(lines) + "<extra></extra>"


def _typical_score_hover_data(
    point: _TypicalScorePoint,
    today: date,
    *,
    middle_50: bool,
    middle_80: bool,
    held: bool = False,
) -> list[str]:
    """Return the figures the line's hover shows at one point, rounded for display."""
    value = point.value

    def shown(statistic: float | None) -> str:
        # Only a known value has a point, and a known value has every statistic.
        return format_typical_score(cast("float", statistic), value.runs)

    first, last = value.first_date.date(), value.last_date.date()
    span = (
        f"on {format_short_date(first, today)}"
        if first == last
        else f"{format_short_date(first, today)} to {format_short_date(last, today)}"
    )
    sessions = value.session_count
    recent = f"{point.recency.run_count} of {value.run_count}"
    if point.aged_out:
        # The count changes along the hold, so none is given.
        recent = f"too few · last run {format_short_date(last, today)}"
    elif held:
        recent += " in the 30 days up to this run"
    data = [
        shown(value.median),
        f"{value.run_count} in {sessions} "
        f"{'session' if sessions == 1 else 'sessions'} · {span}",
        recent,
    ]
    if middle_50:
        data += [shown(value.p25), shown(value.p75)]
    if middle_80:
        data += [shown(value.p10), shown(value.p90)]
    return data


def _typical_score_trace(
    name: str,
    xs: list[float | datetime | None],
    ys: list[float | None],
    *,
    faded: bool,
    show_legend: bool,
) -> go.Scatter:
    """Build one of the typical score's traces, drawn under the runs."""
    return go.Scatter(
        x=xs,
        y=ys,
        mode="lines",
        name=name,
        legendgroup=name,
        legendrank=_TYPICAL_SCORE_LEGEND_RANKS[name],
        showlegend=show_legend,
        opacity=_TYPICAL_SCORE_FADED_OPACITY if faded else 1,
        # Under every run point, star and ring while added after them, so the
        # run trace stays the figure's first and keeps the colorway's first
        # color (``generated_point_color``). Among these traces, data order
        # draws the line over the bands and full strength over faded.
        zorder=-1,
    )


def _typical_score_line(  # noqa: PLR0913
    stretches: list[list[_TypicalScorePoint]],
    today: date,
    *,
    faded: bool,
    show_legend: bool,
    middle_50: bool,
    middle_80: bool,
    held: bool,
) -> go.Scatter:
    """Build the line through the stretches' values, with its hover at each point."""
    xs: list[float | datetime | None] = []
    ys: list[float | None] = []
    hover_data: list[list[str] | None] = []
    for stretch in stretches:
        if xs:
            xs.append(None)
            ys.append(None)
            hover_data.append(None)
        for point in stretch:
            xs.append(point.x)
            ys.append(point.value.median)
            hover_data.append(
                _typical_score_hover_data(
                    point,
                    today,
                    middle_50=middle_50,
                    middle_80=middle_80,
                    held=held,
                )
            )
    trace = _typical_score_trace(
        TYPICAL_SCORE_TRACE_NAME, xs, ys, faded=faded, show_legend=show_legend
    )
    trace.update(
        line={
            "color": _TYPICAL_SCORE_COLORS["light"][TYPICAL_SCORE_TRACE_NAME],
            "width": _TYPICAL_SCORE_LINE_WIDTH_PX,
        },
        customdata=hover_data,
        hovertemplate=_typical_score_hover_template(
            middle_50=middle_50, middle_80=middle_80, held=held
        ),
        hoverlabel={"font_size": 16},
    )
    return trace


def _typical_score_band(
    name: str,
    stretches: list[list[_TypicalScorePoint]],
    bounds: Callable[[TypicalScore], tuple[float | None, float | None]],
    *,
    faded: bool,
    show_legend: bool,
) -> go.Scatter:
    """Build a band between two percentiles, one filled shape per stretch."""
    xs: list[float | datetime | None] = []
    ys: list[float | None] = []
    for stretch in stretches:
        if xs:
            xs.append(None)
            ys.append(None)
        # Along the top, then back along the bottom: ``toself`` closes each
        # shape between gaps.
        for point in stretch:
            xs.append(point.x)
            ys.append(bounds(point.value)[1])
        for point in reversed(stretch):
            xs.append(point.x)
            ys.append(bounds(point.value)[0])
    trace = _typical_score_trace(name, xs, ys, faded=faded, show_legend=show_legend)
    trace.update(
        fill="toself",
        fillcolor=_TYPICAL_SCORE_COLORS["light"][name],
        line={"width": 0},
        hoverinfo="skip",
    )
    return trace


def typical_score_traces(  # noqa: PLR0913
    x_values: Sequence[float],
    values: Sequence[TypicalScore],
    today: date,
    *,
    line: bool,
    middle_50: bool,
    middle_80: bool,
) -> list[go.Scatter]:
    """Build the typical score's line and bands over the plotted runs.

    ``x_values`` are the plotted runs' places on the run axis, and ``values``
    is in step with them: the value after each plotted run, worked out over
    the scenario's whole history. A stretch is drawn at full strength where
    its values were recent at their runs and faded where they weren't. Each
    metric is drawn only while its switch is on, and a band's hover line only
    shows with its band. ``today`` only decides which hover dates carry a
    year.

    The traces come in drawing order, each only when it has a point: the
    faded middle 80% and middle 50%, the full-strength middle 80% and middle
    50%, then the faded line and the line. A faded trace takes its metric's
    legend entry only when the metric has no full-strength stretch.
    """
    full, faded = _typical_score_stretches(x_values, values)
    if _is_one_point(full, faded):
        # The only known value, as on the run that first makes it known.
        # plotly's lines mode draws a one-point trace as nothing, and its
        # bands would have no width, so it is drawn flat for half a run on
        # either side of its run instead. The point at the run itself stays:
        # the zoom fit counts only points inside the zoomed window, so a
        # zoom on the run alone would otherwise leave the value out of view.
        (point,) = (full or faded)[0]
        run_number = cast("float", point.x)
        stub = [
            point._replace(x=run_number - 0.5),
            point,
            point._replace(x=run_number + 0.5),
        ]
        full, faded = ([stub], []) if full else ([], [stub])
    return _typical_score_trace_set(
        full,
        faded,
        today,
        line=line,
        middle_50=middle_50,
        middle_80=middle_80,
        held=False,
    )


def _is_one_point(
    full: list[list[_TypicalScorePoint]], faded: list[list[_TypicalScorePoint]]
) -> bool:
    """Return whether the stretches hold one point between them, which no line shows."""
    return len(full) + len(faded) == 1 and len((full or faded)[0]) == 1


def _typical_score_hold_parts(
    values: Sequence[TypicalScore],
) -> list[tuple[bool, list[_TypicalScorePoint]]]:
    """Return each known value's hold, in parts, each with whether it is recent.

    Each value sits at its own newest run's time, never at a position in a
    list of runs, and holds flat to the next value's. The newest value is
    one point, the line's last. A value recent at its run holds at full
    strength up to and including ``typical_score_fade_time`` and faded after
    it; one that wasn't holds faded throughout. A value whose next run ended
    in the same second holds for no time and has no part: the step there
    goes straight to the later run's value, the one the line holds from that
    second on.
    """
    known = [value for value in values if value.known]
    parts: list[tuple[bool, list[_TypicalScorePoint]]] = []
    for index, value in enumerate(known):
        start = value.last_date
        point = _TypicalScorePoint(start, value, typical_score_recency(value, start))
        if index + 1 == len(known):
            parts.append((point.recency.recent, [point]))
            break
        end = known[index + 1].last_date
        if end == start:
            continue
        # A known value always has a fade time.
        fade = cast("datetime", typical_score_fade_time(value))
        if not point.recency.recent:
            parts.append((False, [point, point._replace(x=end)]))
        elif fade >= end:
            parts.append((True, [point, point._replace(x=end)]))
        else:
            # Recent at its run, so the fade comes at or after it.
            parts.append(
                (True, [point, *([point._replace(x=fade)] if fade > start else [])])
            )
            aged_out = point._replace(aged_out=True)
            parts.append((False, [aged_out._replace(x=fade), aged_out._replace(x=end)]))
    return parts


def _typical_score_holds(
    values: Sequence[TypicalScore],
) -> tuple[list[list[_TypicalScorePoint]], list[list[_TypicalScorePoint]]]:
    """Join the values' holds into full-strength and faded stretches.

    Parts of one strength in a row make one stretch, with a step at each run.
    A faded stretch takes in the full-strength point on each side of it, so
    the two kinds meet with no gap.
    """
    full: list[list[_TypicalScorePoint]] = []
    faded: list[list[_TypicalScorePoint]] = []
    previous: bool | None = None
    for recent, points in _typical_score_hold_parts(values):
        if recent == previous:
            (full if recent else faded)[-1].extend(points)
        elif recent:
            if previous is not None:
                faded[-1].append(points[0])
            full.append(points)
        else:
            before = [] if previous is None else [full[-1][-1]]
            first = points[0]
            # A hold that fades part way already starts its faded part where
            # its full-strength part ends.
            if before and before[0].x == first.x and before[0].value is first.value:
                before = []
            faded.append([*before, *points])
        previous = recent
    return full, faded


def typical_score_hold_traces(
    values: Sequence[TypicalScore],
    today: date,
    *,
    line: bool,
    middle_50: bool,
    middle_80: bool,
) -> list[go.Scatter]:
    """Build the typical score's line and bands as holds over the plotted runs' times.

    ``values`` is the value after each plotted run, in play order, worked out
    over the scenario's whole history. The traces, their order, legend
    entries and switches are ``typical_score_traces``' own. The line's hover
    on the faded part of a hold whose runs aged out after its run gives no
    count, since the count changes along the hold. ``today`` only decides
    which hover dates carry a year.
    """
    full, faded = _typical_score_holds(values)
    traces = _typical_score_trace_set(
        full,
        faded,
        today,
        line=line,
        middle_50=middle_50,
        middle_80=middle_80,
        held=True,
    )
    if _is_one_point(full, faded):
        # The only value drawn, as on the run that first makes it known. The
        # line ends at the newest run, so it holds for no time, and a flat
        # stretch either side of it would draw it at times before it existed.
        # So it is marked at its run: the line by a short level stroke, each
        # band by a bar from its bottom to its top.
        for trace in traces:
            if trace.name == TYPICAL_SCORE_TRACE_NAME:
                color = trace.line.color
                trace.update(
                    mode="markers",
                    marker={
                        "symbol": "line-ew",
                        "size": _TYPICAL_SCORE_MOMENT_WIDTH_PX,
                        "color": color,
                        "line": {"color": color, "width": _TYPICAL_SCORE_LINE_WIDTH_PX},
                    },
                )
            else:
                trace.update(
                    fill="none",
                    line={
                        "color": trace.fillcolor,
                        "width": _TYPICAL_SCORE_MOMENT_WIDTH_PX,
                    },
                )
    return traces


def _typical_score_trace_set(  # noqa: PLR0913
    full: list[list[_TypicalScorePoint]],
    faded: list[list[_TypicalScorePoint]],
    today: date,
    *,
    line: bool,
    middle_50: bool,
    middle_80: bool,
    held: bool,
) -> list[go.Scatter]:
    """Build the traces of the metrics switched on, in drawing order."""
    traces: list[go.Scatter] = []
    bands = [
        (middle_80, MIDDLE_80_TRACE_NAME, lambda value: (value.p10, value.p90)),
        (middle_50, MIDDLE_50_TRACE_NAME, lambda value: (value.p25, value.p75)),
    ]
    for is_faded, stretches in ((True, faded), (False, full)):
        if not stretches:
            continue
        traces.extend(
            _typical_score_band(
                name,
                stretches,
                bounds,
                faded=is_faded,
                show_legend=not is_faded or not full,
            )
            for shown, name, bounds in bands
            if shown
        )
    if line:
        traces.extend(
            _typical_score_line(
                stretches,
                today,
                faded=is_faded,
                show_legend=not is_faded or not full,
                middle_50=middle_50,
                middle_80=middle_80,
                held=held,
            )
            for is_faded, stretches in ((True, faded), (False, full))
            if stretches
        )
    return traces


def apply_typical_score_colors(figure: go.Figure, color_scheme: str) -> go.Figure:
    """Color the typical score's line and bands for a color scheme, in place.

    A figure without them, such as an empty state's, is left as it is. The
    stroke and the bars that mark Score vs Time's only value are recolored
    too.
    """
    colors = _TYPICAL_SCORE_COLORS.get(color_scheme, _TYPICAL_SCORE_COLORS["light"])
    line_color = colors[TYPICAL_SCORE_TRACE_NAME]
    figure.update_traces(
        line={"color": line_color}, selector={"name": TYPICAL_SCORE_TRACE_NAME}
    )
    figure.update_traces(
        marker={"color": line_color, "line": {"color": line_color}},
        selector={"name": TYPICAL_SCORE_TRACE_NAME, "mode": "markers"},
    )
    for name in (MIDDLE_50_TRACE_NAME, MIDDLE_80_TRACE_NAME):
        figure.update_traces(fillcolor=colors[name], selector={"name": name})
        figure.update_traces(
            line={"color": colors[name]}, selector={"name": name, "fill": "none"}
        )
    return figure


def _generate_run_history_plot(  # noqa: PLR0913
    runs: Sequence[RunData],
    x_values: Sequence[float | str | datetime],
    scenario_name: str,
    xaxis: dict[str, object],
    rank_overlay_switch: bool,
    rank_data: list[Rank],
    show_all_ranks: bool,
    new_high_score_runs: Collection[RunData],
    ringed_run: RunData | None = None,
    ringed_run_id: str = "",
    *,
    run_numbers: Mapping[RunData, tuple[int, int]],
    show_sensitivity: bool = False,
) -> go.Figure:
    """Build a Run History figure: one point per run, at the x value given for it.

    ``runs`` and ``x_values`` are in step, and the run trace keeps their
    order. Each run in ``new_high_score_runs`` that is plotted gets a star,
    in a trace that exists only when there is one to draw. The title is the
    scenario's name alone. No trace here sums the runs up: the caller adds
    the typical score's (``typical_score_traces``).

    ``ringed_run`` gets a ring when it is plotted, tagged ``ringed_run_id``,
    in a trace of its own that comes last so the ring is drawn over a star.

    ``run_numbers`` maps each plotted run to its scenario's session and overall
    ordinals, counted over the whole history before filtering or draw-order changes.
    """
    scores = [run.score for run in runs]
    hover_data: dict[RunData, list[float | str]] = {
        run: [
            format_absolute_timestamp(run.datetime_object, include_seconds=True),
            f"{run_numbers[run][0]:,}",
            f"{run_numbers[run][1]:,}",
        ]
        for run in runs
    }
    hovertemplate = _RUN_POINT_HOVER
    if show_sensitivity:
        hovertemplate += "<br><b>Sensitivity</b>: %{x}"
    hovertemplate += "<extra></extra>"
    figure = go.Figure(
        go.Scatter(
            x=list(x_values),
            y=scores,
            mode="markers",
            name=RUN_DATA_POINT_TRACE_NAME,
            # One trace is not given a legend entry unless it asks for one.
            showlegend=True,
            ids=[run_id(run) for run in runs],
            meta="run-history-run",
            customdata=[hover_data[run] for run in runs],
            hovertemplate=hovertemplate,
            hoverlabel={"font_size": 16},
        )
    )
    starred = [
        (x_value, run)
        for x_value, run in zip(x_values, runs, strict=True)
        # Matched on the run, never on where it is plotted: two runs can
        # share a point, and only one of them beat the PB.
        if run in new_high_score_runs
    ]
    if starred:
        figure.add_trace(
            _new_pb_trace(
                [x_value for x_value, _run in starred],
                [run.score for _x_value, run in starred],
                ids=[run_id(run) for _x_value, run in starred],
                customdata=[hover_data[run] for _x_value, run in starred],
                hovertemplate=hovertemplate,
            )
        )
    ringed_at = next(
        (
            x_value
            for x_value, run in zip(x_values, runs, strict=True)
            if run == ringed_run
        ),
        None,
    )
    if ringed_run is not None and ringed_at is not None:
        figure.add_trace(
            _latest_run_ring_trace(ringed_at, ringed_run.score, ringed_run_id)
        )
    logger.debug('Generating plot for: "%s"', scenario_name)
    figure.update_layout(
        title=scenario_name,
        xaxis=xaxis,
        yaxis={"title": "Score"},
        font={"size": 14},
        legend=_LEGEND_ABOVE_PLOT,
    )
    _add_rank_overlays(figure, rank_overlay_switch, rank_data, scores, show_all_ranks)
    return figure


def _run_axis_date_ticks(
    runs: Sequence[RunData],
    run_numbers: Sequence[int],
    today: date,
) -> tuple[list[int], list[str]]:
    """Label the Score vs Run axis with dates, thinned so they do not collide.

    A date goes at the first plotted run of each day. The labels are then
    thinned from the newest back, so the day being played always keeps its
    own, and a label is dropped when it would sit too close to the one kept
    after it. How close that is comes from the assumed plot width, since the
    server does not know the real one.
    """
    first_of_day: list[tuple[int, str]] = []
    last_day: date | None = None
    for run_number, run in zip(run_numbers, runs, strict=True):
        day = run.datetime_object.date()
        if day != last_day:
            first_of_day.append((run_number, format_short_date(day, today)))
            last_day = day

    pixels_per_run = _RUN_AXIS_ASSUMED_PLOT_WIDTH_PX / max(
        run_numbers[-1] - run_numbers[0], 1
    )

    def half_width(label: str) -> float:
        return (
            len(label) * _RUN_AXIS_LABEL_CHARACTER_PX + _RUN_AXIS_LABEL_MARGIN_PX
        ) / 2

    kept: list[tuple[int, str]] = []
    for run_number, label in reversed(first_of_day):
        if kept:
            later_run_number, later_label = kept[-1]
            room = (later_run_number - run_number) * pixels_per_run
            if room < half_width(label) + half_width(later_label):
                continue
        kept.append((run_number, label))
    kept.reverse()
    return [run_number for run_number, _label in kept], [
        label for _run_number, label in kept
    ]


def generate_score_vs_run_plot(  # noqa: PLR0913
    runs: Sequence[RunData],
    first_run_number: int,
    scenario_name: str,
    rank_overlay_switch: bool,
    rank_data: list[Rank],
    show_all_ranks: bool,
    new_high_score_runs: Collection[RunData],
    today: date,
    ringed_run: RunData | None = None,
    ringed_run_id: str = "",
    *,
    run_numbers: Mapping[RunData, tuple[int, int]],
) -> go.Figure:
    """Build the Score vs Run figure: the runs given, evenly spaced, in their order.

    ``runs`` is in the order the runs were played and must hold at least one.
    A run's x value is its number in the scenario's whole history, counted
    from ``first_run_number`` for the first run given, so a run keeps its
    place on the axis when the range around it changes. The axis is numeric
    and its labels are dates, which is why the ticks are written out here:
    plotly places a point by its value and would label the axis with the run
    numbers. ``today`` only decides which labels carry a year.
    """
    axis_run_numbers = list(range(first_run_number, first_run_number + len(runs)))
    tick_values, tick_labels = _run_axis_date_ticks(runs, axis_run_numbers, today)
    return _generate_run_history_plot(
        runs,
        axis_run_numbers,
        scenario_name,
        {
            "title": "Run",
            "tickmode": "array",
            "tickvals": tick_values,
            "ticktext": tick_labels,
        },
        rank_overlay_switch,
        rank_data,
        show_all_ranks,
        new_high_score_runs,
        ringed_run,
        ringed_run_id,
        run_numbers=run_numbers,
    )


def generate_score_vs_time_plot(  # noqa: PLR0913
    runs: Sequence[RunData],
    scenario_name: str,
    rank_overlay_switch: bool,
    rank_data: list[Rank],
    show_all_ranks: bool,
    new_high_score_runs: Collection[RunData],
    ringed_run: RunData | None = None,
    ringed_run_id: str = "",
    *,
    run_numbers: Mapping[RunData, tuple[int, int]],
) -> go.Figure:
    """Build the Score vs Time figure: each run given, at the time it ended.

    ``runs`` is in the order the runs were played and must hold at least one.
    A run's time is in whole seconds, so two runs that ended in the same
    second with the same score share a point. Among such runs a new PB is
    drawn last, so the hover under its star is its own.
    """
    drawn: list[RunData] = []
    for _ended, ended_together in groupby(runs, key=attrgetter("datetime_object")):
        drawn.extend(_new_high_scores_last(list(ended_together), new_high_score_runs))
    return _generate_run_history_plot(
        drawn,
        [run.datetime_object for run in drawn],
        scenario_name,
        {"title": "Date"},
        rank_overlay_switch,
        rank_data,
        show_all_ranks,
        new_high_score_runs,
        ringed_run,
        ringed_run_id,
        run_numbers=run_numbers,
    )


def generate_score_vs_sensitivity_plot(  # noqa: PLR0913
    runs: Sequence[RunData],
    scenario_name: str,
    rank_overlay_switch: bool,
    rank_data: list[Rank],
    show_all_ranks: bool,
    ringed_run: RunData | None = None,
    ringed_run_id: str = "",
    *,
    run_numbers: Mapping[RunData, tuple[int, int]],
) -> go.Figure:
    """Build the Score vs Sensitivity figure: each run given, at its sensitivity.

    ``runs`` must hold at least one. The axis lists the sensitivities in the
    order their first runs are given in, so the caller hands the runs over
    grouped by sensitivity, lowest first. No run is starred: along this axis
    the stars would have no order to be read in.
    """
    return _generate_run_history_plot(
        runs,
        [f"{run.horizontal_sens} {run.sens_scale}" for run in runs],
        scenario_name,
        {"title": "Sensitivity"},
        rank_overlay_switch,
        rank_data,
        show_all_ranks,
        new_high_score_runs=(),
        ringed_run=ringed_run,
        ringed_run_id=ringed_run_id,
        run_numbers=run_numbers,
        show_sensitivity=True,
    )


def apply_light_dark_mode(figure: go.Figure, color_scheme: str) -> go.Figure:
    """
    Apply light or dark mode to figure.
    :param figure: figure to lighten or darken.
    :param color_scheme: active Mantine color scheme.
    :return: figure with template applied.
    """
    figure.update_layout(template=_theme_template(color_scheme))
    return figure


def _theme_template(color_scheme: str) -> str:
    """Name the Mantine figure template for a color scheme; light unless dark."""
    return _THEME_TEMPLATES.get(color_scheme, _THEME_TEMPLATES["light"])


def generated_point_color(color_scheme: str) -> str:
    """Return the color the run points have in a scheme with no point color chosen.

    The run trace is the figure's first, and carries no color of its own, so
    Plotly draws it in the first colorway entry of the template
    ``apply_light_dark_mode`` applies for that scheme. This reads the same
    entry, so the Point color field can preview the color the graph will use.
    :param color_scheme: active Mantine color scheme.
    :return: a hex color string.
    """
    colorway = pio.templates[_theme_template(color_scheme)].layout.colorway
    return str(colorway[0])


def apply_point_appearance(
    figure: go.Figure,
    point_size: str | None,
    point_color: str | None,
) -> go.Figure:
    """Apply the Run Data Points preferences to a themed figure, in place.

    ``point_size`` is a value from ``POINT_SIZE_OPTIONS`` and ``point_color``
    a hex color string. Both restyle the raw-run trace, and the size also
    sizes the New PB stars and the latest run's ring, which keep their own
    colors whatever the color. Runs after the theme template, so an explicit
    color wins over the colorway the template just applied. Everything
    unrecognized falls through to the generated appearance: the Default size,
    an empty or malformed color, a figure whose traces are the empty state's
    (none), and a figure from a version that named its traces differently.
    """
    marker: dict[str, int | str] = {}
    size = POINT_SIZE_PRESET_PX.get(point_size or "")
    if size is not None:
        marker["size"] = size
    if isinstance(point_color, str) and _HEX_COLOR_PATTERN.fullmatch(point_color):
        marker["color"] = point_color
    # Each update merges into whatever marker its trace already carries, and
    # selects nothing at all on a figure without a trace of that name.
    if marker:
        figure.update_traces(
            marker=marker, selector={"name": RUN_DATA_POINT_TRACE_NAME}
        )
    new_pb_size = NEW_PB_SIZE_PRESET_PX.get(point_size or "")
    if new_pb_size is not None:
        figure.update_traces(
            marker={"size": new_pb_size}, selector={"name": NEW_PB_TRACE_NAME}
        )
    ring_size = LATEST_RUN_RING_SIZE_PRESET_PX.get(point_size or "")
    if ring_size is not None:
        figure.update_traces(
            marker={"size": ring_size}, selector={"name": LATEST_RUN_TRACE_NAME}
        )
    return figure


def generate_aim_training_journey_plot(
    journey_data: dict[str, dict[datetime, float]],
    aim_training_checkpoints: dict[datetime, int],
) -> go.Figure:
    """Plot playlist progress over time with training-hour checkpoints."""
    figures = {}

    # loop through each playlist and data and build a line plot
    for idx, (playlist, journey) in enumerate(journey_data.items()):
        line_plot_data: dict[str, list] = {
            "Date": [],
            "Percentage": [],
        }

        for date_obj, percentage in journey.items():
            line_plot_data["Date"].append(date_obj)
            line_plot_data["Percentage"].append(round(100 * percentage, 2))

        figure_line = px.line(
            data_frame=pd.DataFrame(line_plot_data),
            x="Date",
            y="Percentage",
            markers=True,
            title=playlist,
        )
        figure_line.update_traces(
            line_color=figure_line.layout.template.layout.colorway[idx],
        )
        figures[playlist] = figure_line

    # combined the data for each line plot into a single plot
    data = None
    for figure in figures.values():
        data = figure.data if data is None else data + figure.data

    figure_combined = go.Figure(data=data)
    figure_combined.update_layout(
        title="Aim Training Journey",
        xaxis={"title": "Datetime"},
        yaxis={"title": "Percentage"},
        font={
            "size": 16,
        },
    )

    for idx, playlist in enumerate(figures.keys()):
        figure_combined["data"][idx]["name"] = playlist
        figure_combined["data"][idx]["showlegend"] = True

    # add vertical lines to display aim training hours as checkpoints
    for date_obj, checkpoint in aim_training_checkpoints.items():
        figure_combined.add_vline(
            x=date_obj.timestamp() * 1000,
            line_dash="dash",
            annotation_text=f" {checkpoint} hours",
        )

    return figure_combined
