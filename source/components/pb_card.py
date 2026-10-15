"""What the Run History page's PB card shows: the selected scenario's personal best.

``personal_best`` works out, from one scenario's runs, what the card says
about its PB as this app records it: when it was set, its score, how far it
beat the PB before it, the rank it has reached on the ladder the Playlist
filter holds and the gap to the next one, and the PB run's sensitivity and
accuracy. The rest of the module draws that in the card.

The card is worked out from the run store each time, as the latest-run card
is, so it is right on a page that has just been drawn, with no new run.
"""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, NamedTuple

import dash_mantine_components as dmc
from dash import Input, Output, callback, clientside_callback, dcc, html

from source.components.chart_options import TOOLTIP_EVENTS
from source.components.latest_run_card import (
    AGE_SCRIPT,
    BODY_CLASS,
    EMPTY_MESSAGE_CLASS,
    EMPTY_TITLE_CLASS,
    RESULT_CLASS,
    SCORE_CLASS,
    SCORE_ROW_CLASS,
    TIME_CLASS,
    TIME_TARGET_CLASS,
)
from source.components.run_marks import new_pb_gain, what_runs_chased
from source.kovaaks.data_models import Rank, RunData
from source.kovaaks.data_service import (
    get_playlist_by_code,
    get_runs_in_play_order,
    is_benchmark_playlist,
)
from source.kovaaks.playlist_scenarios_service import (
    ladder_standing,
    personal_best_cm360,
)
from source.kovaaks.time_scored_service import (
    PaceBasis,
    eligible_pace_constant,
    get_pace_basis,
    get_version_pace_basis,
)
from source.utilities.utilities import format_score, format_whole_percent

logger = logging.getLogger(__name__)

PB_LABEL = "PB"
TOP_RANK_TEXT = "Top rank"
NO_SCENARIO_TEXT = "No scenario selected"
NO_LOCAL_PB_TEXT = "No local PB yet"
NO_LOCAL_PB_MESSAGE = "Play this scenario to record one in this app."

CARD_CLASS = "pb-card"
HEADING_CLASS = "pb-card-heading"
RANK_BADGE_CLASS = "pb-card-rank-badge"
NEXT_RANK_CLASS = f"{RESULT_CLASS} pb-card-next-rank"
RANK_DOT_CLASS = "pb-card-rank-dot"
THRESHOLD_CLASS = "pb-card-threshold"
FADED_CLASS = "pb-card-faded"
# The score with a hover, with the affordance Last played's has.
SCORE_HOVER_CLASS = f"{SCORE_CLASS} {TIME_CLASS}"
_ARIA_HIDDEN: dict[str, Any] = {"aria-hidden": "true"}


@dataclass(frozen=True)
class NextRank:
    """The next rank's line, in the benchmark table's own figures.

    ``threshold`` is the rank's threshold formatted as PB Score, ``gap`` the
    Next Rank cell's figure (``+1.3%``, or ``+2.8% faster`` by pace), and
    ``points`` the points still to go, as the cell's tooltip gives them.
    ``color`` is the rank's color from the benchmark's file.
    """

    name: str
    color: str
    threshold: str
    gap: str
    points: str


@dataclass(frozen=True)
class PersonalBest:
    """What the card says about a scenario's PB, as the text it shows.

    ``set_at`` is when the PB run ended, which the browser words as an age.
    ``score_hover`` is the line the latest-run card showed when this PB
    landed, and ``None`` for a PB the scenario's first run set, which beat
    nothing. ``rank`` is the rank the PB has reached on the ladder the
    Playlist filter holds, ``None`` below its first threshold and with no
    ladder. ``at_top_rank`` is whether every rank is reached, and
    ``next_rank`` is the next one's line, ``None`` at the top and where the
    benchmark table's Next Rank cell would read ``N/A``. ``faded`` is the
    card's last line.
    """

    set_at: datetime
    score: str
    score_hover: str | None
    rank: Rank | None
    at_top_rank: bool
    next_rank: NextRank | None
    faded: str


def _faded_line(run: RunData) -> str:
    """Word the PB run's sensitivity and its hit accuracy.

    The sensitivity is the scenario table's PB cm/360, formatted as that
    column formats it. The accuracy is the hit accuracy, as the latest-run
    card and the run list show a run's, which can differ from the table's PB
    Accuracy: that column prefers the damage accuracy.
    """
    accuracy = f"Accuracy {format_whole_percent(run.accuracy)}"
    cm360 = personal_best_cm360(run)
    if cm360 is None:
        return accuracy
    return f"{format_score(cm360)} cm/360 · {accuracy}"


def personal_best(
    runs: Sequence[RunData],
    ladder: list[Rank] | None,
    pace_basis: PaceBasis | None,
    version_pace_basis: Callable[[str | None], PaceBasis | None],
) -> PersonalBest | None:
    """Work out what the card says about the PB among ``runs``.

    ``runs`` is one scenario's whole history in the order it was played, and
    ``None`` comes back when it is empty. ``ladder`` is the scenario's ladder
    in the benchmark the Playlist filter holds, ``None`` with no benchmark
    selected. ``pace_basis`` is what the scenario's newest run says of its
    pace, which is how the benchmark table chooses whether the next rank's
    gap is by pace. ``version_pace_basis`` answers for one version of the
    scenario, which is how the latest-run card measured the PB when it
    landed.

    The PB run is the earliest run to reach the high score, the run
    ``get_personal_best_run`` finds, taken from this one copy of the runs so
    that it is always among them.
    """
    if not runs:
        return None
    # ``max`` keeps the first of equal scores, so the earliest run holds a tie.
    run = max(runs, key=lambda each: each.score)
    chased = what_runs_chased(runs, version_pace_basis)[run]
    score_hover = (
        None
        if chased.previous_best is None
        else new_pb_gain(run.score, chased.previous_best, chased)
    )
    standing = (
        ladder_standing(ladder, run.score, eligible_pace_constant(pace_basis, run))
        if ladder
        else None
    )
    next_rank = None
    if standing is not None and standing.next_gap is not None:
        gap = standing.next_gap
        next_rank = NextRank(
            name=gap.rank.name,
            color=gap.rank.color,
            threshold=gap.threshold_text,
            gap=gap.gap_text,
            points=gap.points_text,
        )
    return PersonalBest(
        set_at=run.datetime_object,
        score=format_score(run.score),
        score_hover=score_hover,
        rank=None if standing is None else standing.reached,
        at_top_rank=standing is not None and standing.at_top,
        next_rank=next_rank,
        faded=_faded_line(run),
    )


def _ladder(playlist_code: str | None, scenario: str) -> list[Rank] | None:
    """Find the scenario's ladder in the playlist the filter holds.

    ``None`` unless the playlist is a benchmark that lists the scenario, as
    the benchmark table gives a row no Rank fields on a playlist's table. A
    benchmark scenario without a ladder has an empty one.
    """
    playlist = None if not playlist_code else get_playlist_by_code(playlist_code)
    if playlist is None or not is_benchmark_playlist(playlist):
        return None
    for listed in playlist.scenarios:
        if listed.name == scenario:
            return listed.ranks or []
    return None


def personal_best_from_store(
    selected_scenario: str | None,
    playlist_code: str | None,
) -> PersonalBest | None:
    """Work out what the card says from the run store, ``None`` with no PB.

    The runs are copied from the store once, so the PB, the run before it and
    the figures come from the same moment.
    """
    if not selected_scenario:
        return None
    runs = get_runs_in_play_order(selected_scenario)
    if not runs:
        return None
    ladder = _ladder(playlist_code, selected_scenario)
    pace_basis = None
    # As the benchmark table does: only a scenario with a ladder shows a gap,
    # so only then is a performance file read.
    if ladder:
        try:
            pace_basis = get_pace_basis(selected_scenario)
        except Exception:  # noqa: BLE001 -- it must cost the pace gap, never the card.
            # The lookup handles a missing or unreadable performance file
            # itself. Anything else falls back to the gap as a percentage of
            # the PB, as the table's cell does.
            logger.warning(
                'Failed to tell whether "%s" is time-scored',
                selected_scenario,
                exc_info=True,
            )
    return personal_best(
        runs,
        ladder,
        pace_basis,
        lambda version: get_version_pace_basis(selected_scenario, version),
    )


# --- The card on a page --------------------------------------------------------


class PbCardIds(NamedTuple):
    """The component ids one page gives its PB card.

    ``set_at`` is a store holding when the PB run ended, in epoch seconds, or
    nothing with no PB. A script on the page words it into ``label``, the
    first line's words after ``PB``, hidden with no PB: ``time`` is the PB's
    age in it and ``time_tooltip`` the age's hover. ``body`` holds the lines
    from the score down to the next rank, or the card's empty state, and
    ``faded`` its last line.

    ``run_events``, ``scenario_dropdown``, ``playlist_filter`` and
    ``relative_time_interval`` are the page's own. The card reads them and
    builds none of them:

    - ``run_events`` is the store the page's run delivery writes when new
      runs land on the scenario it shows.
    - ``relative_time_interval`` is a ``dcc.Interval`` that ticks every 30
      seconds, so the PB's age stays current on a page left open.
    """

    set_at: str
    label: str
    time: str
    time_tooltip: str
    body: str
    faded: str
    run_events: str
    scenario_dropdown: str
    playlist_filter: str
    relative_time_interval: str


class PbCardContent(NamedTuple):
    """What a page writes to its card, one field per prop it writes."""

    set_at: float | None
    body: list[Any]
    faded: str | None


def pb_card(ids: PbCardIds) -> dmc.Box:
    """Build the card with nothing in it yet.

    The page's callbacks write what it shows. The PB's age is written by a
    script, so it is in the layout from the start: it would come and go under
    the script if the server's answer drew it.
    """
    return dmc.Box(
        className=CARD_CLASS,
        children=[
            dcc.Store(id=ids.set_at),
            # Not a flex container, which would drop the spaces either side of
            # the age and hand a screen reader the words run together.
            html.Div(
                className=HEADING_CLASS,
                children=[
                    PB_LABEL,
                    html.Span(
                        [
                            " · set ",
                            dmc.Tooltip(
                                dmc.Text(
                                    className=TIME_CLASS,
                                    id=ids.time,
                                    inherit=True,
                                    span=True,
                                    tabIndex=0,
                                ),
                                # dmc wraps the tooltip's target in a block
                                # box, which would break the line round it.
                                boxWrapperProps={"className": TIME_TARGET_CLASS},
                                events=TOOLTIP_EVENTS,
                                id=ids.time_tooltip,
                                label="",
                            ),
                        ],
                        hidden=True,
                        id=ids.label,
                    ),
                ],
            ),
            html.Div(id=ids.body, className=BODY_CLASS),
            html.Div(id=ids.faded, className=FADED_CLASS),
        ],
    )


def _score(shown: PersonalBest) -> Any:
    """Draw the PB score, with its hover where it beat a previous best."""
    if shown.score_hover is None:
        return html.Span(shown.score, className=SCORE_CLASS)
    return dmc.Tooltip(
        html.Span(shown.score, className=SCORE_HOVER_CLASS, tabIndex=0),
        events=TOOLTIP_EVENTS,
        label=shown.score_hover,
    )


def _rank_badge(rank: Rank) -> dmc.Badge:
    """Draw the rank the PB has reached, in its color from the benchmark's file.

    The stylesheet draws it in the page's text color on a tint of the rank's
    color, with a border in that color, so a pale rank stays legible in both
    themes.
    """
    return dmc.Badge(
        rank.name,
        className=RANK_BADGE_CLASS,
        style={"--pb-card-rank-color": rank.color},
        # The app's sentence case, where the badge's own style would print
        # capitals.
        tt="none",
    )


def _next_rank_line(next_rank: NextRank) -> html.Div:
    """Draw the next rank's line, its threshold under the PB score."""
    return html.Div(
        [
            html.Span(
                className=RANK_DOT_CLASS,
                style={"--pb-card-rank-color": next_rank.color},
                **_ARIA_HIDDEN,
            ),
            html.Span(next_rank.threshold, className=THRESHOLD_CLASS),
            f" {next_rank.name} · {next_rank.gap} · {next_rank.points} to go",
        ],
        className=NEXT_RANK_CLASS,
    )


def pb_card_content(
    shown: PersonalBest | None,
    selected_scenario: str | None,
) -> PbCardContent:
    """Build what the card shows for a PB, or for a scenario with none."""
    if not selected_scenario:
        return PbCardContent(
            set_at=None,
            body=[html.Div(NO_SCENARIO_TEXT, className=EMPTY_TITLE_CLASS)],
            faded=None,
        )
    if shown is None:
        return PbCardContent(
            set_at=None,
            body=[
                html.Div(NO_LOCAL_PB_TEXT, className=EMPTY_TITLE_CLASS),
                html.Div(NO_LOCAL_PB_MESSAGE, className=EMPTY_MESSAGE_CLASS),
            ],
            faded=None,
        )
    score_row: list[Any] = [_score(shown)]
    if shown.rank is not None:
        score_row.append(_rank_badge(shown.rank))
    body: list[Any] = [html.Div(score_row, className=SCORE_ROW_CLASS)]
    if shown.at_top_rank:
        body.append(html.Div(TOP_RANK_TEXT, className=NEXT_RANK_CLASS))
    elif shown.next_rank is not None:
        body.append(_next_rank_line(shown.next_rank))
    return PbCardContent(
        set_at=shown.set_at.timestamp(),
        body=body,
        faded=shown.faded,
    )


def show_pb(_run_events, selected_scenario, selected_playlist) -> PbCardContent:
    """Write what the card shows, from the run store.

    The first argument is the page's run-events store, which triggers the
    call and is not read. Every run that lands on the selected scenario
    rebuilds the card, a new PB or not: whether the next rank's gap is by
    pace follows the scenario's newest version, so a run of a new version
    can change it without beating anything.
    """
    return pb_card_content(
        personal_best_from_store(selected_scenario, selected_playlist),
        selected_scenario,
    )


def register_pb_card(ids: PbCardIds) -> None:
    """Register the card's callbacks for one page's ids.

    Call once per page, at import, with the ids its layout is built from.
    """
    callback(
        Output(ids.set_at, "data"),
        Output(ids.body, "children"),
        Output(ids.faded, "children"),
        Input(ids.run_events, "data"),
        Input(ids.scenario_dropdown, "value"),
        # The badge and the next rank follow the filter's benchmark at once,
        # as the chart's rank lines do.
        Input(ids.playlist_filter, "value"),
    )(show_pb)
    clientside_callback(
        AGE_SCRIPT,
        Output(ids.label, "hidden"),
        Output(ids.time, "children"),
        Output(ids.time_tooltip, "label"),
        Input(ids.set_at, "data"),
        Input(ids.relative_time_interval, "n_intervals"),
    )
