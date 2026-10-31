"""The run viewer: one run of Run History, in the chart's place until it is closed.

``run_viewer_content`` draws what the viewer shows of a run from what
``source.kovaaks.run_viewer`` works out: the header, the score line, the line
that names the run's typical runs, the tiles, Settings and Everything
Recorded. ``show_run`` decides what a press does, and ``register_run_viewer``
wires both to a page.

A run opens from a Run row of the run list, by a click or by Enter or Space
on the row, and from a run point or a PB star of the chart. The list's and
the chart's scripts hand the run's id to ``assets/runViewer.js``, which writes
it to the viewer's request store. Close, Esc, which presses Close, and a
change of the selected scenario close it. While a run is open the chart's
column hides the chart's own parts with a class and keeps them mounted, so
the chart comes back as it was left: its mode, zoom, ranges and hidden
traces. The open run is held in a store that no reload keeps.
"""

import logging
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, NamedTuple

import dash_mantine_components as dmc
from dash import (
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    ctx,
    dcc,
    html,
    no_update,
)

from source.components.latest_run_card import (
    ScoreLine,
    comparison_children,
    score_badge,
    score_line,
)
from source.components.score_threshold import normalize_score_threshold_percentage
from source.kovaaks.data_models import RunData
from source.kovaaks.data_service import get_all_runs
from source.kovaaks.play_sessions import in_play_order
from source.kovaaks.run_viewer import (
    RunFigures,
    RunFile,
    RunTable,
    RunView,
    Setting,
    SettingCard,
    Tile,
    view_run_from_store,
)
from source.kovaaks.time_scored_service import get_version_pace_basis
from source.kovaaks.typical_score import format_typical_score
from source.utilities.utilities import (
    format_absolute_timestamp,
    format_percent,
    format_score,
    format_short_date,
    format_short_timestamp,
)

logger = logging.getLogger(__name__)

# --- Copy ----------------------------------------------------------------------

CLOSE_LABEL = "Close"
ESC_HINT = "Esc"
HEADER_LINE = "{scenario} · ended {ended}"
TITLE = "Run {number} · {session} session"
UNREADABLE_TEXT = "This run's file couldn't be read. See data/logs/debug.log."
REFERENCE_ON_TEXT = (
    "Typical comes from your {count} runs before this session, played on {date}."
)
REFERENCE_SPAN_TEXT = (
    "Typical comes from your {count} runs before this session, "
    "played from {first} to {last}."
)
FIRST_SESSION_TEXT = (
    "This is the scenario's first session, so there's no typical run to compare "
    "with yet."
)
TOO_FEW_TEXT = (
    "There's no typical run for this run's session yet: it had {count} before "
    "it, and a typical score needs 10 runs across 2 or more sessions, or 20 in "
    "one session."
)
SCORE_LABEL = "Score"
ACCURACY_LABEL = "Accuracy"
SHOTS_FIRED_LABEL = "Shots fired"
RELOADS_LABEL = "Reloads"
TIME_LABEL = "Time"
TYPICAL_LINE = "Typical {value}"
MEDIAN_OF_SOME_TEXT = "Median of {count} of your {total} typical runs"
MEDIAN_OF_ALL_TEXT = "Median of your {total} typical runs"
SETTINGS_HEADING = "Settings"
SETTINGS_SUBTITLE = (
    "A setting that differs from its most common value over your typical runs "
    "is marked, with that value under it."
)
SETTING_LABELS = {
    Setting.SENSITIVITY: "Sensitivity",
    Setting.VERTICAL_SENSITIVITY: "Vertical sensitivity",
    Setting.DPI: "DPI",
    Setting.FOV: "FOV",
    Setting.CROSSHAIR: "Crosshair",
    Setting.CROSSHAIR_SCALE: "Crosshair scale",
    Setting.HIDE_GUN: "Hide gun",
    Setting.RESOLUTION: "Resolution",
    Setting.RESOLUTION_SCALE: "Resolution scale",
    Setting.FRAME_CAP: "Frame cap",
    Setting.INPUT_LAG: "Input lag",
}
NOT_RECORDED_TEXT = "Not recorded"
NOT_RECORDED_HOVER = (
    "The run file doesn't have this setting. Older versions of KovaaK's didn't "
    "record it."
)
MARKED_HOVER = "{value}\nTypical {typical} · on {count} of your {total} typical runs"
RECORDED_HEADING = "Everything Recorded"
RECORDED_SUBTITLE = "The run file as KovaaK's wrote it, grouped by kind."
OTHER_GROUP = "Other"
FILES_GROUP = "Files"
WEAPONS_GROUP = "Weapons"
KILLS_GROUP = "Kills"
ALL_ZERO_TEXT = "All zero: {fields}"
RUN_FILE_LABEL = "Run file"
PERFORMANCE_FILE_LABEL = "Performance file"
FOUND_TEXT = "Found"
NONE_TEXT = "None"
NO_KILLS_TEXT = "This run's file records no kills."

# The stats file's fields by kind, each group in this order. A field no group
# names goes to Other, in file order, so a game update never hides one.
RECORDED_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Result",
        (
            "Score",
            "Kills",
            "Deaths",
            "Hit Count",
            "Miss Count",
            "Total Overshots",
            "Reloads",
            "Damage Done",
            "Damage Taken",
            "Avg TTK",
            "Fight Time",
            "Time Remaining",
        ),
    ),
    (
        "Other Counters",
        (
            "Midairs",
            "Midaired",
            "Directs",
            "Directed",
            "Distance Traveled",
            "MBS Points",
        ),
    ),
    (
        "Run",
        (
            "Scenario",
            "Hash",
            "Game Version",
            "Challenge Start",
            "Pause Count",
            "Pause Duration",
            "Avg Target Scale",
            "Avg Time Dilation",
            "Avg FPS",
        ),
    ),
    (
        "Settings",
        (
            "Sens Scale",
            "Sens Increment",
            "Horiz Sens",
            "Vert Sens",
            "DPI",
            "FOV",
            "FOVScale",
            "Hide Gun",
            "Crosshair",
            "Crosshair Scale",
            "Crosshair Color",
            "Resolution",
            "Resolution Scale",
            "Max FPS (config)",
            "Input Lag",
        ),
    ),
)

# --- Classes -------------------------------------------------------------------

COLUMN_CLASS = "run-history-chart-column"
# The chart's column while a run is open: the chart's own parts are hidden,
# and the viewer shows in their place.
COLUMN_OPEN_CLASS = f"{COLUMN_CLASS} run-viewer-open"
VIEWER_CLASS = "run-viewer"
_BETTER_CLASS = "run-viewer-better"
_WORSE_CLASS = "run-viewer-worse"
_MARKED_CLASS = "run-viewer-card run-viewer-card-marked"
_UNRECORDED_CLASS = "run-viewer-card run-viewer-card-unrecorded"
_CARD_CLASS = "run-viewer-card"

# The minus sign, not a hyphen, before a difference below zero.
_MINUS = "−"


# --- What the viewer shows -----------------------------------------------------


def _count(count: int, noun: str) -> str:
    return f"{count} {noun if count == 1 else noun + 's'}"


def _reference_text(figures: RunFigures, today: date) -> str:
    """Say which runs are the run's typical runs, or why it has none."""
    typical_score = figures.typical_score
    if typical_score is None:
        return FIRST_SESSION_TEXT
    if not figures.typical_runs:
        return TOO_FEW_TEXT.format(count=_count(typical_score.run_count, "run"))
    first = figures.typical_runs[0].datetime_object.date()
    last = figures.typical_runs[-1].datetime_object.date()
    count = len(figures.typical_runs)
    if first == last:
        return REFERENCE_ON_TEXT.format(
            count=count, date=format_short_date(first, today)
        )
    return REFERENCE_SPAN_TEXT.format(
        count=count,
        first=format_short_date(first, today),
        last=format_short_date(last, today),
    )


def _signed(difference: Decimal, text: str) -> str:
    """Put a difference's sign before its unsigned text; zero takes none."""
    if difference > 0:
        return f"+{text}"
    if difference < 0:
        return f"{_MINUS}{text}"
    return text


def _plain(text: str) -> Decimal:
    """Read back a number this module formatted, for arithmetic on what is shown."""
    return Decimal(text.replace(",", "").removesuffix("%"))


def _rounded(value: float, places: str) -> Decimal:
    """Round half up, as the app's other formatters round a half.

    The inner round strips float noise that would land a half under its
    rounding point: 70 less 12.55 is 57.449999999999996, which would read
    57.4 where the run's 57.45 seconds rounds up to 57.5.
    """
    return Decimal(str(round(value, 6))).quantize(
        Decimal(places), rounding=ROUND_HALF_UP
    )


def completion_time_text(seconds: Decimal) -> str:
    """Write a completion time as ``m:ss.s``, from seconds already rounded to tenths."""
    minutes, rest = divmod(seconds, 60)
    return f"{int(minutes)}:{rest:04.1f}"


class _TileText(NamedTuple):
    """One tile as it reads: its value, its typical, and the difference.

    ``difference`` is worked out from the two values as shown, so the three
    always add up on screen. ``better`` is 1 where a higher value is better,
    -1 where a lower one is, and 0 where neither is. ``typical_count`` is
    how many typical runs the typical took.
    """

    label: str
    value: str | None
    typical: str | None
    difference: Decimal | None
    difference_text: str | None
    better: int
    typical_count: int | None


def _score_tile(tile: Tile, typical_runs: tuple[RunData, ...]) -> _TileText:
    assert tile.run is not None
    value = format_score(tile.run)
    if tile.typical is None:
        return _TileText(SCORE_LABEL, value, None, None, None, 1, None)
    # Formatted as Scenario Stats formats the typical score: to its runs' own
    # precision.
    typical = format_typical_score(tile.typical.value, typical_runs)
    difference = _plain(value) - _plain(typical)
    return _TileText(
        SCORE_LABEL,
        value,
        typical,
        difference,
        format_score(float(abs(difference))),
        1,
        tile.typical.count,
    )


def _accuracy_tile(tile: Tile) -> _TileText:
    assert tile.run is not None
    value = format_percent(tile.run)
    if tile.typical is None:
        return _TileText(ACCURACY_LABEL, value, None, None, None, 1, None)
    typical = format_percent(tile.typical.value)
    difference = _plain(value) - _plain(typical)
    return _TileText(
        ACCURACY_LABEL,
        value,
        typical,
        difference,
        f"{abs(difference):.2f} pts",
        1,
        tile.typical.count,
    )


def _count_tile(label: str, tile: Tile, better: int) -> _TileText:
    """Shots fired and Reloads: whole numbers, with a median that can be a half."""
    value = None if tile.run is None else f"{int(tile.run):,}"
    if tile.typical is None:
        return _TileText(label, value, None, None, None, better, None)
    typical = format_score(tile.typical.value)
    difference = None if value is None else _plain(value) - _plain(typical)
    return _TileText(
        label,
        value,
        typical,
        difference,
        None if difference is None else format_score(float(abs(difference))),
        better,
        tile.typical.count,
    )


def _time_tile(tile: Tile) -> _TileText:
    run = None if tile.run is None else _rounded(tile.run, "0.1")
    value = None if run is None else completion_time_text(run)
    if tile.typical is None:
        return _TileText(TIME_LABEL, value, None, None, None, -1, None)
    typical = _rounded(tile.typical.value, "0.1")
    difference = None if run is None else run - typical
    return _TileText(
        TIME_LABEL,
        value,
        completion_time_text(typical),
        difference,
        None if difference is None else f"{abs(difference):.1f} s",
        -1,
        tile.typical.count,
    )


def _median_hover(count: int, total: int) -> str:
    if count == total:
        return MEDIAN_OF_ALL_TEXT.format(total=total)
    return MEDIAN_OF_SOME_TEXT.format(count=count, total=total)


def _tile(text: _TileText, total: int, *, unrecorded: str) -> html.Div:
    """Draw one tile: its label, the run's value, and its typical with the difference."""
    value: Any = text.value
    value_class = "run-viewer-tile-value"
    if value is None:
        value = unrecorded
        value_class += " run-viewer-unrecorded"
    typical: list[Any] = []
    hover = None
    if text.typical is not None:
        typical = [TYPICAL_LINE.format(value=text.typical)]
        if text.difference is not None and text.difference_text is not None:
            direction = text.difference * text.better
            typical += [
                " · ",
                html.Span(
                    _signed(text.difference, text.difference_text),
                    className=(
                        _BETTER_CLASS
                        if direction > 0
                        else _WORSE_CLASS
                        if direction < 0
                        else None
                    ),
                ),
            ]
        assert text.typical_count is not None
        hover = _median_hover(text.typical_count, total)
    return html.Div(
        [
            html.Div(text.label, className="run-viewer-tile-label"),
            html.Div(value, className=value_class),
            html.Div(typical, className="run-viewer-tile-typical", title=hover),
        ],
        className="run-viewer-tile",
    )


def _tiles(figures: RunFigures) -> html.Div:
    tiles = figures.tiles
    total = len(figures.typical_runs)
    texts = [
        _score_tile(tiles.score, figures.typical_runs),
        _accuracy_tile(tiles.accuracy),
        _count_tile(SHOTS_FIRED_LABEL, tiles.shots_fired, better=0),
        _count_tile(RELOADS_LABEL, tiles.reloads, better=-1),
    ]
    drawn = [_tile(text, total, unrecorded=NOT_RECORDED_TEXT) for text in texts]
    if tiles.time is not None:
        # A time of zero or less isn't a time: the tile shows none.
        drawn.append(_tile(_time_tile(tiles.time), total, unrecorded=""))
    return html.Div(drawn, className="run-viewer-tiles")


def _card(card: SettingCard, total: int) -> html.Div:
    """Draw one setting's card, tinted with its typical value when it differs."""
    label = html.Div(SETTING_LABELS[card.setting], className="run-viewer-card-label")
    if card.value is None:
        return html.Div(
            [
                label,
                html.Div(NOT_RECORDED_TEXT, className="run-viewer-card-value"),
                html.Div(className="run-viewer-card-typical"),
            ],
            className=_UNRECORDED_CLASS,
            title=NOT_RECORDED_HOVER,
        )
    if not card.marked:
        return html.Div(
            [
                label,
                html.Div(card.value, className="run-viewer-card-value"),
                html.Div(className="run-viewer-card-typical"),
            ],
            className=_CARD_CLASS,
            title=card.value,
        )
    assert card.typical is not None
    return html.Div(
        [
            label,
            html.Div(card.value, className="run-viewer-card-value"),
            html.Div(
                TYPICAL_LINE.format(value=card.typical.value),
                className="run-viewer-card-typical",
            ),
        ],
        className=_MARKED_CLASS,
        title=MARKED_HOVER.format(
            value=card.value,
            typical=card.typical.value,
            count=card.typical.count,
            total=total,
        ),
    )


def _settings(figures: RunFigures) -> html.Section:
    total = len(figures.typical_runs)
    return html.Section(
        [
            html.H3(SETTINGS_HEADING, className="run-viewer-heading"),
            html.P(SETTINGS_SUBTITLE, className="run-viewer-subtitle"),
            html.Div(
                [_card(card, total) for card in figures.settings],
                className="run-viewer-cards",
            ),
        ],
        className="run-viewer-section",
    )


def _is_zero(value: str) -> bool:
    """Return whether a field reads zero. An empty or missing value isn't zero."""
    try:
        return float(value) == 0
    except ValueError:
        return False


def recorded_groups(file: RunFile) -> list[tuple[str, list[tuple[str, str]], bool]]:
    """Sort a stats file's fields into Everything Recorded's groups.

    Each group is its name, its fields, and whether it folds to one line. A
    group folds only when every field it names is in the file and reads
    zero: a field the file doesn't have, or has with no value, isn't zero.
    Other holds every field no group names, in file order, and folds when
    each reads zero. A group with no field in the file is left out.
    """
    place = {
        key: (group_index, key_index)
        for group_index, (_name, keys) in enumerate(RECORDED_GROUPS)
        for key_index, key in enumerate(keys)
    }
    grouped: list[list[tuple[str, str]]] = [[] for _ in RECORDED_GROUPS]
    other: list[tuple[str, str]] = []
    for key, value in file.fields:
        if key in place:
            grouped[place[key][0]].append((key, value))
        else:
            other.append((key, value))
    groups = []
    for (name, keys), fields in zip(RECORDED_GROUPS, grouped, strict=True):
        if not fields:
            continue
        fields.sort(key=lambda field: place[field[0]][1])
        present = {key for key, _value in fields}
        folds = present == set(keys) and all(_is_zero(value) for _key, value in fields)
        groups.append((name, fields, folds))
    if other:
        groups.append(
            (OTHER_GROUP, other, all(_is_zero(value) for _key, value in other))
        )
    return groups


def _table(table: RunTable) -> dmc.Table:
    """Draw a table of the stats file as data, never as one component per cell.

    A kill table runs to hundreds of rows, and Dash's renderer slows with
    every component it draws: Mantine draws ``data`` itself.
    """
    return dmc.Table(
        data={"head": list(table.header), "body": [list(row) for row in table.rows]},
        className="run-viewer-table",
        tabularNums=True,
        withRowBorders=False,
    )


def _field_table(rows: list[tuple[str, str]]) -> dmc.Table:
    return dmc.Table(
        data={"body": [[key, value] for key, value in rows]},
        className="run-viewer-table run-viewer-field-table",
        tabularNums=True,
        withRowBorders=False,
    )


def _group(name: str, content: Any, *, wide: bool = False) -> html.Div:
    return html.Div(
        [html.H4(name, className="run-viewer-group-heading"), content],
        className="run-viewer-group run-viewer-group-wide"
        if wide
        else "run-viewer-group",
    )


def _everything_recorded(run: RunData, figures: RunFigures) -> html.Details:
    file = figures.file
    blocks = []
    for name, fields, folds in recorded_groups(file):
        if folds:
            content: Any = html.P(
                ALL_ZERO_TEXT.format(fields=", ".join(key for key, _value in fields)),
                className="run-viewer-quiet",
            )
        else:
            content = _field_table(fields)
        blocks.append(_group(name, content))
    blocks.append(
        _group(
            FILES_GROUP,
            _field_table(
                [
                    (RUN_FILE_LABEL, run.stats_file_name or ""),
                    (
                        PERFORMANCE_FILE_LABEL,
                        FOUND_TEXT if figures.performance_file_found else NONE_TEXT,
                    ),
                ]
            ),
        )
    )
    if file.weapons.rows:
        blocks.append(
            _group(
                WEAPONS_GROUP,
                html.Div(_table(file.weapons), className="run-viewer-table-scroll"),
                wide=True,
            )
        )
    blocks.append(
        _group(
            KILLS_GROUP,
            html.Div(_table(file.kills), className="run-viewer-table-scroll")
            if file.kills.rows
            else html.P(NO_KILLS_TEXT, className="run-viewer-quiet"),
            wide=True,
        )
    )
    return html.Details(
        [
            html.Summary(RECORDED_HEADING, className="run-viewer-summary"),
            html.P(RECORDED_SUBTITLE, className="run-viewer-subtitle"),
            html.Div(blocks, className="run-viewer-groups"),
        ],
        className="run-viewer-section run-viewer-recorded",
    )


def _score_line(line: ScoreLine) -> html.Div:
    """Draw the score, its badge and the comparison as the latest-run card words them.

    A line of inline boxes with spaces between them, not a flex container: a
    flex container drops the spaces, and a screen reader would be handed the
    badge and the comparison as one word.
    """
    children: list[Any] = [html.Span(line.score, className="run-viewer-score")]
    if line.badge is not None:
        children += [" ", score_badge(line.badge)]
    comparison = comparison_children(line.typical, line.pb_comparison)
    if comparison:
        children += [" ", html.Span(comparison, className="run-viewer-comparison")]
    return html.Div(children, className="run-viewer-score-line")


class ViewerContent(NamedTuple):
    """What the viewer shows of one run: its header's lines, then everything under them."""

    heading: list[Any]
    body: list[Any]


def run_viewer_content(
    view: RunView,
    line: ScoreLine | None,
    today: date,
) -> ViewerContent:
    """Draw what the viewer shows of a run.

    ``line`` is the run's score line, None when its file can't be read: the
    viewer then shows the header and says so. ``today`` is the app's own
    date, which decides the years a date leaves out.
    """
    run = view.run
    heading = [
        html.Div(
            HEADER_LINE.format(
                scenario=run.scenario,
                ended=format_absolute_timestamp(
                    run.datetime_object, include_seconds=True
                ),
            ),
            className="run-viewer-kicker",
        ),
        html.H2(
            TITLE.format(
                number=view.number,
                session=format_short_timestamp(view.session.start, today),
            ),
            className="run-viewer-title",
        ),
    ]
    figures = view.figures
    if figures is None or line is None:
        return ViewerContent(
            heading, [html.P(UNREADABLE_TEXT, className="run-viewer-unreadable")]
        )
    return ViewerContent(
        heading,
        [
            _score_line(line),
            html.P(_reference_text(figures, today), className="run-viewer-reference"),
            _tiles(figures),
            # By Bot goes here, between the tiles and Settings. Everything
            # Recorded stays open through a switch to another run only while
            # it keeps its place among these children, where React keeps
            # the open element: a section shown on some runs and not others
            # has to leave something in its place.
            _settings(figures),
            _everything_recorded(run, figures),
        ],
    )


def run_viewer_from_store(
    viewed_run_id: str,
    score_threshold_percentage: float | str | None,
    now: datetime,
) -> ViewerContent | None:
    """Draw what the viewer shows of a run in the run store, or None with no such run.

    ``score_threshold_percentage`` is the percentage field's value as the
    browser sends it, which judges the run's badge.
    """
    view = view_run_from_store(viewed_run_id)
    if view is None:
        return None
    line = None
    if view.figures is not None:
        run = view.run
        line = score_line(
            run,
            in_play_order(r for r in get_all_runs() if r.scenario == run.scenario),
            view.figures.typical_score,
            view.session,
            normalize_score_threshold_percentage(score_threshold_percentage),
            get_version_pace_basis,
        )
    return run_viewer_content(view, line, now.date())


# --- Opening and closing -------------------------------------------------------


class RunViewerIds(NamedTuple):
    """The component ids one page gives its run viewer.

    ``column`` is the chart's column, whose class hides the chart while a run
    is open. ``request`` is the store ``assets/runViewer.js`` writes a run to
    open to, ``open`` holds the open run, and ``shown`` is written with every
    change, for the script to move focus and mark the run's row.
    ``shown_sink`` is the output the script's callback needs and never
    writes.
    """

    column: str
    viewer: str
    heading: str
    close: str
    body: str
    request: str
    open: str
    shown: str
    shown_sink: str


def run_viewer(ids: RunViewerIds, *, return_focus: str) -> html.Div:
    """Build the viewer, hidden and empty until a run opens.

    ``return_focus`` is the id of the chart's mode control, where focus goes
    back when a run a chart point opened is closed. The script reads both
    ids from the viewer's ``data-`` attributes.
    """
    for_script: dict[str, Any] = {
        "data-request-store": ids.request,
        "data-return-focus": return_focus,
    }
    return html.Div(
        id=ids.viewer,
        className=VIEWER_CLASS,
        children=[
            dcc.Store(id=ids.request),
            dcc.Store(id=ids.open),
            dcc.Store(id=ids.shown),
            dcc.Store(id=ids.shown_sink),
            html.Div(
                [
                    html.Div(id=ids.heading, className="run-viewer-heading-lines"),
                    dmc.Button(
                        CLOSE_LABEL,
                        id=ids.close,
                        className="run-viewer-close",
                        rightSection=dmc.Kbd(ESC_HINT, size="xs"),
                        size="xs",
                        variant="default",
                        # The key hint is not part of the button's name.
                        **{"aria-label": CLOSE_LABEL, "aria-keyshortcuts": "Escape"},
                    ),
                ],
                className="run-viewer-header",
            ),
            html.Div(id=ids.body, className="run-viewer-body"),
        ],
        **for_script,
    )


# What called ``show_run``.
REQUEST = "request"
CLOSE = "close"
SELECTION = "selection"

# How focus moves once the change is drawn, for ``assets/runViewer.js``.
FOCUS_CLOSE = "close"
FOCUS_ROW = "row"
FOCUS_CHART = "chart"
FROM_LIST = "list"
FROM_CHART = "chart"

_NO_CHANGE = (no_update,) * 5


def _closed(held: dict, focus: str | None) -> tuple:
    return (
        None,
        COLUMN_CLASS,
        [],
        [],
        {"open": None, "focus": focus, "run": held["run_id"]},
    )


def show_run(  # noqa: PLR0911, PLR0913
    trigger: str | None,
    request: dict | None,
    selected_scenario: str | None,
    held: dict | None,
    score_threshold_percentage: float | str | None,
    now: datetime,
) -> tuple:
    """Decide what a press does to the viewer, and draw it.

    ``trigger`` names what called: a run asked for, Close, or the selected
    scenario. ``held`` is the open run: its id, what opened it, ``"list"`` or
    ``"chart"``, and the scenario selected when it opened. Returns what the
    callback writes: the open run, the chart column's class, the header's
    lines, the body, and what the script does once they are drawn.

    A run asked for opens, or replaces the open run. Close returns focus to
    what opened the run. A change of the selected scenario closes the run
    and leaves focus where the player is. The dropdown can be written with
    the value it holds, as when a run lands with Follow on, which is no
    change.
    """
    if trigger == CLOSE:
        if not held:
            return _NO_CHANGE
        return _closed(
            held, FOCUS_ROW if held.get("from") == FROM_LIST else FOCUS_CHART
        )
    if trigger == SELECTION:
        if not held or selected_scenario == held.get("selected"):
            return _NO_CHANGE
        return _closed(held, None)
    if trigger != REQUEST or not request or not request.get("run_id"):
        return _NO_CHANGE
    viewed = request["run_id"]
    source = request.get("from")
    if held and held.get("run_id") == viewed:
        if held.get("from") == source:
            return _NO_CHANGE
        # The same run pressed again in the list after a chart point opened
        # it: Close now returns to its row.
        return ({**held, "from": source}, *_NO_CHANGE[1:])
    content = run_viewer_from_store(viewed, score_threshold_percentage, now)
    if content is None:
        logger.warning(
            "The run viewer was asked for a run the store doesn't hold: %r", viewed
        )
        return _closed(held, None) if held else _NO_CHANGE
    return (
        {"run_id": viewed, "from": source, "selected": selected_scenario},
        COLUMN_OPEN_CLASS,
        content.heading,
        content.body,
        # Switching runs from the list leaves focus on the row pressed.
        {"open": viewed, "focus": None if held else FOCUS_CLOSE, "run": viewed},
    )


# Once a change is drawn: move focus, mark the open run's row in the list, and
# start a newly shown run from the top.
_SHOWN_SCRIPT = """
(shown) => {
    if (shown && window.runViewer) {
        window.runViewer.shown(shown);
    }
    return window.dash_clientside.no_update;
}
"""


def register_run_viewer(
    ids: RunViewerIds,
    *,
    scenario_dropdown: str,
    score_threshold_percentage: str,
) -> None:
    """Register what opens and closes the viewer, for one page's ids.

    Call once per page, at import. ``scenario_dropdown`` is the selected
    scenario's control: a change of it closes the run. The score threshold's
    percentage judges the run's badge; its control is in the chart's column,
    hidden while a run is open, so it is read and not listened to.
    """

    @callback(
        Output(ids.open, "data"),
        Output(ids.column, "className"),
        Output(ids.heading, "children"),
        Output(ids.body, "children"),
        Output(ids.shown, "data"),
        Input(ids.request, "data"),
        Input(ids.close, "n_clicks"),
        Input(scenario_dropdown, "value"),
        State(ids.open, "data"),
        State(score_threshold_percentage, "value"),
        # Nothing is open when the page is drawn.
        prevent_initial_call=True,
    )
    def show_requested_run(
        request, _close_clicks, selected_scenario, held, percentage
    ) -> tuple:
        trigger = {
            ids.request: REQUEST,
            ids.close: CLOSE,
            scenario_dropdown: SELECTION,
        }.get(ctx.triggered_id)
        return show_run(
            trigger, request, selected_scenario, held, percentage, datetime.now()
        )

    clientside_callback(
        _SHOWN_SCRIPT,
        Output(ids.shown_sink, "data"),
        Input(ids.shown, "data"),
        prevent_initial_call=True,
    )
