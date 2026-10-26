"""What the Run History page's PB card shows.

``personal_best`` is one pure function over one scenario's runs, so most of
these tests build records and read the text the card shows. The rest draw
the card, read it from a stubbed run store, and hold how the page registers
it. The card's leaderboard line, today's Position field moved, is
``tests/test_pb_card_position.py``.
"""

import logging
from datetime import datetime, timedelta

import dash
import pytest
from dash import dcc, html
from dash._callback import GLOBAL_CALLBACK_LIST, GLOBAL_INLINE_SCRIPTS
from sortedcontainers import SortedList

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.components import latest_run_card, pb_card  # noqa: E402
from source.components.pb_card import (  # noqa: E402
    NextRank,
    PbCardIds,
    PersonalBest,
    pb_card_content,
    personal_best,
)
from source.kovaaks import data_service  # noqa: E402
from source.kovaaks.data_models import PlaylistData, Rank, RunData, Scenario  # noqa: E402
from source.kovaaks.time_scored_service import PaceBasis  # noqa: E402
from source.pages import run_history  # noqa: E402
from tests.rendered_text import rendered_text  # noqa: E402

SCENARIO = "VT Controlsphere Viscose"
EVENING = datetime(2026, 10, 9, 17, 24, 0)
VERSION = "0123456789abcdef0123456789abcdef"
NEWER_VERSION = "fedcba9876543210fedcba9876543210"
IDS = PbCardIds(*PbCardIds._fields)

CERULEAN = Rank(name="Cerulean", color="#4fc3f7", threshold=3500)
LAVENDER = Rank(name="Lavender", color="#b39ddb", threshold=3700)
LADDER = [CERULEAN, LAVENDER]
# Ground Plaza Sparky V3's two top ranks: time-scored, counting down from 1,000.
PACE_LADDER = [
    Rank(name="Cerulean", color="#4fc3f7", threshold=892.5),
    Rank(name="Lavender", color="#b39ddb", threshold=899),
]


def _run(  # noqa: PLR0913
    score: float,
    minute: int = 0,
    *,
    sensitivity: float = 50.0,
    scale: str = "cm/360",
    accuracy: float = 0.61,
    scenario_hash: str | None = VERSION,
) -> RunData:
    """Build one run of the scenario, ``minute`` minutes into the evening."""
    ended = EVENING + timedelta(minutes=minute)
    return RunData(
        datetime_object=ended,
        score=score,
        sens_scale=scale,
        horizontal_sens=sensitivity,
        scenario=SCENARIO,
        accuracy=accuracy,
        scenario_hash=scenario_hash,
        stats_file_name=f"{SCENARIO} - Challenge - {ended:%Y.%m.%d-%H.%M.%S} Stats.csv",
        run_start=ended - timedelta(seconds=60),
        run_length=timedelta(seconds=60),
    )


def _scored(*scores: float, **fields) -> list[RunData]:
    """Build one run per score, a minute apart, the last one ending last."""
    return [_run(score, minute, **fields) for minute, score in enumerate(scores)]


def _no_pace(_version: str | None) -> PaceBasis | None:
    return None


def _pace_of(constant: float, version: str = VERSION):
    """Answer that ``version`` of the scenario counts down from ``constant``."""

    def basis(asked: str | None) -> PaceBasis | None:
        if asked != version:
            return None
        return PaceBasis(constant=constant, scenario_hash=version)

    return basis


def _shown(
    runs: list[RunData],
    ladder: list[Rank] | None = None,
    pace_basis: PaceBasis | None = None,
    version_pace_basis=_no_pace,
) -> PersonalBest:
    shown = personal_best(runs, ladder, pace_basis, version_pace_basis)
    assert shown is not None
    return shown


def _next_rank_text(shown: PersonalBest) -> str | None:
    """Read the next rank's line as the card prints it, or None where hidden."""
    content = pb_card_content(shown, SCENARIO)
    lines = [rendered_text(line) for line in content.body[1:]]
    assert len(lines) <= 1
    return lines[0] if lines else None


# --- What the card says --------------------------------------------------------


def test_a_scenario_with_no_runs_has_no_pb():
    assert personal_best([], LADDER, None, _no_pace) is None


@pytest.mark.parametrize(
    ("scores", "ladder", "pace_basis", "badge", "next_rank"),
    [
        pytest.param(
            (3000, 3653),
            LADDER,
            None,
            "Cerulean",
            "3,700 Lavender · +1.3% · 47 to go",
            id="a-pb-with-a-rank",
        ),
        pytest.param((3000, 3653), None, None, None, None, id="no-benchmark"),
        pytest.param((3000, 3653), [], None, None, None, id="no-ladder"),
        pytest.param(
            (3000, 3400),
            LADDER,
            None,
            None,
            "3,500 Cerulean · +3.0% · 100 to go",
            id="below-the-first-rank",
        ),
        pytest.param(
            (3000, 3700), LADDER, None, "Lavender", "Top rank", id="at-the-top-rank"
        ),
        pytest.param(
            (880, 896.2),
            PACE_LADDER,
            PaceBasis(constant=1000.0, scenario_hash=VERSION),
            "Cerulean",
            "899 Lavender · +2.8% faster · 2.8 to go",
            id="time-scored-with-a-pace-gap",
        ),
        pytest.param(
            (880, 896.2),
            PACE_LADDER,
            # The scenario's newest version is not the PB's, so the table
            # compares it by score.
            PaceBasis(constant=1000.0, scenario_hash=NEWER_VERSION),
            "Cerulean",
            "899 Lavender · +0.4% · 2.8 to go",
            id="time-scored-without-a-pace-gap",
        ),
        pytest.param(
            (-20, 0), LADDER, None, None, None, id="a-pb-of-zero-compared-by-score"
        ),
        pytest.param(
            (-20, 0),
            [Rank(name="Iron", color="#888888", threshold=100)],
            PaceBasis(constant=1000.0, scenario_hash=VERSION),
            None,
            "100 Iron · +11.2% faster · 100 to go",
            id="a-pb-of-zero-by-pace",
        ),
    ],
)
def test_the_badge_and_the_next_rank_are_the_benchmark_tables(
    scores, ladder, pace_basis, badge, next_rank
):
    shown = _shown(_scored(*scores), ladder, pace_basis)

    assert (None if shown.rank is None else shown.rank.name) == badge
    assert _next_rank_text(shown) == next_rank


def test_the_next_rank_carries_its_own_color_for_its_dot():
    shown = _shown(_scored(3000, 3653), LADDER)

    assert shown.next_rank == NextRank(
        name="Lavender", color="#b39ddb", threshold="3,700", gap="+1.3%", points="47"
    )
    assert shown.rank == CERULEAN


def test_the_score_is_formatted_as_the_scenario_table_formats_pb_score():
    assert _shown(_scored(3000, 3324.0)).score == "3,324"
    assert _shown(_scored(800, 896.20)).score == "896.2"


def test_the_pb_was_set_by_the_earliest_run_to_reach_the_high_score():
    """``get_personal_best_run``'s rule: on a tie the earliest run holds it."""
    runs = _scored(3000, 3653, 3100, 3653)

    shown = _shown(runs)

    assert shown.set_at == runs[1].datetime_object
    assert shown.score_hover == "Up 21.8% on your previous best of 3,000"


@pytest.fixture
def load_runs(monkeypatch):
    """Load runs through the real CSV loader, so the store keeps its own order."""
    monkeypatch.setattr(data_service, "kovaaks_database", {})
    monkeypatch.setattr(
        data_service, "run_database", SortedList(key=lambda run: run.datetime_object)
    )
    monkeypatch.setattr(pb_card, "get_version_pace_basis", lambda _s, _v: None)

    def load(*runs: RunData) -> None:
        pending = iter(runs)
        monkeypatch.setattr(
            data_service, "extract_data_from_file", lambda _file: next(pending)
        )
        for index in range(len(runs)):
            assert data_service.load_csv_file_into_database(f"run-{index}.csv")

    return load


@pytest.mark.parametrize(
    ("stored_first", "faded"),
    [
        pytest.param("began_first", "50 cm/360 · Accuracy 55.00%", id="as-played"),
        pytest.param("began_second", "50 cm/360 · Accuracy 65.00%", id="against-play"),
    ],
)
def test_a_tie_that_ended_in_one_second_is_the_tables_pb_run(
    load_runs, stored_first, faded
):
    """Two runs of the high score that ended in the same second.

    The store keeps such a pair as it was loaded, and ``get_personal_best_run``
    takes the first. Play order puts the one that began first first. The
    card's PB is the table's either way, and its hover is still the line the
    high score landed with, never a gain over the PB's own score.
    """
    tie = []
    for accuracy, seconds in ((0.55, 90), (0.65, 30)):
        run = _run(3653, 5, accuracy=accuracy)
        length = timedelta(seconds=seconds)
        tie.append(
            RunData(
                **{
                    **run.__dict__,
                    "run_start": run.datetime_object - length,
                    "run_length": length,
                }
            )
        )
    if stored_first == "began_second":
        tie.reverse()
    load_runs(_run(3000), *tie)

    shown = pb_card.personal_best_from_store(SCENARIO, None)

    assert data_service.get_personal_best_run(SCENARIO) == tie[0]
    assert shown is not None
    assert shown.faded == faded
    assert shown.score_hover == "Up 21.8% on your previous best of 3,000"


@pytest.mark.parametrize(
    ("scores", "version_pace_basis", "hover"),
    [
        pytest.param(
            (3000, 3324),
            _no_pace,
            "Up 10.8% on your previous best of 3,000",
            id="by-score",
        ),
        pytest.param(
            (960, 980),
            _pace_of(1000.0),
            "100.0% faster than your previous best of 960",
            id="by-pace",
        ),
        pytest.param(
            (0, 12), _no_pace, "Your previous best was 0", id="over-a-pb-of-zero"
        ),
        pytest.param((3324,), _no_pace, None, id="set-by-the-first-run"),
    ],
)
def test_the_scores_hover_is_the_latest_run_cards_line_for_the_pb(
    scores, version_pace_basis, hover
):
    """Word for word what the latest-run card said when this PB landed."""
    runs = _scored(*scores)

    shown = _shown(runs, version_pace_basis=version_pace_basis)
    landed = latest_run_card.latest_run(
        runs,
        runs[-1].scenario,
        None,
        runs[-1].datetime_object,
        lambda _s, v: version_pace_basis(v),
    )

    assert shown.score_hover == hover
    if hover is not None:
        assert landed.comparison == hover


def test_the_scores_hover_is_measured_under_the_pbs_own_version():
    """A later run on another version cannot change what the PB was measured by."""
    runs = [*_scored(960, 980), _run(970, 5, scenario_hash=NEWER_VERSION)]

    shown = _shown(runs, version_pace_basis=_pace_of(1000.0))

    assert shown.score_hover == "100.0% faster than your previous best of 960"


@pytest.mark.parametrize(
    ("fields", "faded"),
    [
        pytest.param({}, "50 cm/360 · Accuracy 61.00%", id="trailing-zeros-dropped"),
        pytest.param(
            {"sensitivity": 34.6375},
            "34.64 cm/360 · Accuracy 61.00%",
            id="two-decimals",
        ),
        pytest.param(
            {"scale": "Valorant", "sensitivity": 0.35},
            "Accuracy 61.00%",
            id="cm360-unknown",
        ),
        pytest.param(
            {"accuracy": 57 / 800},
            "50 cm/360 · Accuracy 7.13%",
            id="a-half-rounds-up",
        ),
    ],
)
def test_the_faded_line_is_the_pb_runs_cm360_and_hit_accuracy(fields, faded):
    """The table's PB cm/360, and the accuracy as the latest-run card shows it."""
    runs = [_run(3000, 0), _run(3653, 1, **fields), _run(3100, 2)]

    assert _shown(runs).faded == faded


# --- The card drawn ------------------------------------------------------------


SHOWN = PersonalBest(
    set_at=datetime(2026, 10, 9, 17, 24),
    score="3,653",
    score_hover="Up 1.0% on your previous best of 3,617",
    rank=CERULEAN,
    at_top_rank=False,
    next_rank=NextRank(
        name="Lavender", color="#b39ddb", threshold="3,700", gap="+1.3%", points="47"
    ),
    faded="50 cm/360 · Accuracy 61.00%",
)


def _walk(component):
    yield component
    children = getattr(component, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk(child)
    elif children is not None and not isinstance(children, str):
        yield from _walk(children)


def _held(component) -> dict:
    return {
        each.id: each
        for each in _walk(component)
        if isinstance(getattr(each, "id", None), str)
    }


def test_the_card_starts_with_nothing_in_it_and_holds_every_id():
    card = pb_card.pb_card(IDS)
    held = _held(card)

    page_owned = {
        IDS.run_events,
        IDS.scenario_dropdown,
        IDS.playlist_filter,
        IDS.polling_interval,
        IDS.relative_time_interval,
    }
    assert set(held) == set(IDS) - page_owned
    assert card.className == "pb-card"
    for store in (IDS.set_at, IDS.rank_updated_ts, IDS.rank_of_total):
        assert isinstance(held[store], dcc.Store)
        assert getattr(held[store], "data", None) is None
    assert getattr(held[IDS.body], "children", None) is None
    assert getattr(held[IDS.faded], "children", None) is None


def test_the_lines_are_the_first_then_the_pb_then_the_leaderboard_then_the_faded():
    """The leaderboard line sits under the PB, which it is sourced apart from."""
    lines = [
        child
        for child in pb_card.pb_card(IDS).children
        if not isinstance(child, dcc.Store)
    ]

    assert [getattr(line, "id", None) or line.className for line in lines] == [
        "pb-card-heading",
        IDS.body,
        IDS.leaderboard,
        IDS.faded,
    ]


def test_the_first_line_reads_pb_and_the_age_is_drawn_once_hidden_until_a_pb():
    """A script writes the age, so it is never part of the server's answer.

    The line is not a flex container, so the spaces either side of the age
    reach a screen reader.
    """
    card = pb_card.pb_card(IDS)
    (heading,) = [
        child
        for child in card.children
        if getattr(child, "className", None) == "pb-card-heading"
    ]
    label = _held(card)[IDS.label]

    assert heading.className == "pb-card-heading"
    assert heading.children[0] == "PB"
    assert heading.children[1] is label
    assert label.hidden is True
    lead, tooltip = label.children
    assert lead == " · set "
    assert tooltip.id == IDS.time_tooltip
    assert tooltip.events == {"hover": True, "focus": True, "touch": True}
    assert tooltip.boxWrapperProps == {"className": "run-history-card-time-target"}
    age = tooltip.children
    assert age.id == IDS.time
    assert (age.className, age.tabIndex, age.inherit, age.span) == (
        "cell-tooltip-affordance",
        0,
        True,
        True,
    )


def test_a_pb_is_its_score_and_badge_then_the_next_rank_then_the_faded_line():
    content = pb_card_content(SHOWN, SCENARIO)
    score_row, next_rank = content.body

    assert content.set_at == SHOWN.set_at.timestamp()
    # A local PB, so the leaderboard line shows under it.
    assert content.leaderboard_hidden is False
    # The score ends on a space a screen reader reads: the row is a flex
    # container, which would hand over "3,653Cerulean" as one word.
    assert [rendered_text(part) for part in score_row.children] == [
        "3,653 ",
        "Cerulean",
    ]
    assert rendered_text(next_rank) == "3,700 Lavender · +1.3% · 47 to go"
    assert content.faded == "50 cm/360 · Accuracy 61.00%"


def test_the_score_with_a_hover_takes_focus_and_shows_it_as_last_played_does():
    tooltip = pb_card_content(SHOWN, SCENARIO).body[0].children[0]
    score = tooltip.children

    assert tooltip.label == "Up 1.0% on your previous best of 3,617"
    assert tooltip.events == {"hover": True, "focus": True, "touch": True}
    value, word_end = score.children
    assert value == "3,653"
    assert (word_end.children, word_end.className) == (" ", "pb-card-word-end")
    assert score.className == "run-history-card-score cell-tooltip-affordance"
    assert score.tabIndex == 0


def test_a_pb_set_by_the_first_run_has_no_hover_and_no_underline():
    shown = PersonalBest(**{**SHOWN.__dict__, "score_hover": None})

    score = pb_card_content(shown, SCENARIO).body[0].children[0]

    assert isinstance(score, html.Span)
    assert score.className == "run-history-card-score"
    assert getattr(score, "tabIndex", None) is None


def test_the_badge_is_the_rank_in_its_own_color_and_sentence_case():
    badge = pb_card_content(SHOWN, SCENARIO).body[0].children[1]

    assert badge.children == "Cerulean"
    assert badge.className == "pb-card-rank-badge"
    assert badge.style == {"--pb-card-rank-color": "#4fc3f7"}
    assert badge.tt == "none"


def test_the_next_ranks_dot_is_its_color_and_hidden_from_a_screen_reader():
    dot, threshold, rest = pb_card_content(SHOWN, SCENARIO).body[1].children

    assert dot.className == "pb-card-rank-dot"
    assert dot.style == {"--pb-card-rank-color": "#b39ddb"}
    assert getattr(dot, "aria-hidden") == "true"
    assert (threshold.className, threshold.children) == ("pb-card-threshold", "3,700")
    assert rest == " Lavender · +1.3% · 47 to go"


def test_a_pb_with_no_badge_and_no_next_rank_is_its_score_alone():
    shown = PersonalBest(**{**SHOWN.__dict__, "rank": None, "next_rank": None})

    content = pb_card_content(shown, SCENARIO)

    assert [rendered_text(line) for line in content.body] == ["3,653 "]


def test_at_the_top_rank_the_line_under_the_score_says_so():
    shown = PersonalBest(
        **{**SHOWN.__dict__, "rank": LAVENDER, "at_top_rank": True, "next_rank": None}
    )

    content = pb_card_content(shown, SCENARIO)

    assert [rendered_text(line) for line in content.body] == [
        "3,653 Lavender",
        "Top rank",
    ]


@pytest.mark.parametrize("selected", [None, ""])
def test_with_no_scenario_selected_the_card_says_so(selected):
    content = pb_card_content(None, selected)

    assert content.set_at is None
    assert [rendered_text(line) for line in content.body] == ["No scenario selected"]
    # Nothing to rank, and Refresh would have nothing to do.
    assert content.leaderboard_hidden is True
    assert content.faded is None


def test_a_scenario_with_no_local_runs_has_no_local_pb_yet():
    content = pb_card_content(None, SCENARIO)

    assert content.set_at is None
    assert [rendered_text(line) for line in content.body] == [
        "No local PB yet",
        "Play this scenario to record one in this app.",
    ]
    # The line follows the local PB, so there is none.
    assert content.leaderboard_hidden is True
    assert content.faded is None


# --- Read from the run store ---------------------------------------------------


BENCHMARK = PlaylistData(
    name="Viscose Benchmark S2 - Medium",
    code="KovaaKsViscoseCode",
    scenarios=[
        Scenario(name=SCENARIO, ranks=LADDER),
        Scenario(name="Ground Plaza Sparky V3", ranks=PACE_LADDER),
        Scenario(name="Unranked Scenario", ranks=None),
    ],
)
PLAYLIST = PlaylistData(
    name="Warmup", code="KovaaKsWarmupCode", scenarios=[Scenario(name=SCENARIO)]
)


@pytest.fixture
def store(monkeypatch):
    """Stub the run store and the loaded playlists the card reads."""
    held: dict = {
        "runs": {},
        "pace_basis": None,
        "pace_asked": [],
        "version_pace_asked": [],
    }
    playlists = {BENCHMARK.code: BENCHMARK, PLAYLIST.code: PLAYLIST}

    def pace_basis(scenario):
        held["pace_asked"].append(scenario)
        if isinstance(held["pace_basis"], Exception):
            raise held["pace_basis"]
        return held["pace_basis"]

    def version_pace_basis(scenario, version):
        held["version_pace_asked"].append((scenario, version))

    # ``held["runs"]`` holds each scenario's runs oldest first.
    monkeypatch.setattr(
        pb_card,
        "get_runs_newest_first",
        lambda s: list(reversed(held["runs"].get(s, []))),
    )
    monkeypatch.setattr(pb_card, "get_playlist_by_code", playlists.get)
    monkeypatch.setattr(pb_card, "get_pace_basis", pace_basis)
    monkeypatch.setattr(pb_card, "get_version_pace_basis", version_pace_basis)
    return held


def _body_text(content) -> list[str]:
    return [rendered_text(line) for line in content.body]


def test_with_no_scenario_or_no_runs_the_store_has_no_pb(store):
    assert pb_card.personal_best_from_store(None, BENCHMARK.code) is None
    assert pb_card.personal_best_from_store(SCENARIO, BENCHMARK.code) is None


@pytest.mark.parametrize(
    ("playlist_code", "scenario", "expected"),
    [
        pytest.param(
            BENCHMARK.code,
            SCENARIO,
            ["3,653 Cerulean", "3,700 Lavender · +1.3% · 47 to go"],
            id="a-benchmark",
        ),
        pytest.param(BENCHMARK.code, "Unranked Scenario", ["3,653 "], id="no-ladder"),
        pytest.param(PLAYLIST.code, SCENARIO, ["3,653 "], id="a-playlist"),
        pytest.param(None, SCENARIO, ["3,653 "], id="no-filter"),
        pytest.param("KovaaKsGoneCode", SCENARIO, ["3,653 "], id="an-unknown-code"),
        pytest.param(
            BENCHMARK.code,
            "Not In The Benchmark",
            ["3,653 "],
            id="a-benchmark-that-does-not-list-it",
        ),
    ],
)
def test_the_ladder_is_the_one_the_playlist_filters_benchmark_gives(
    store, playlist_code, scenario, expected
):
    store["runs"][scenario] = _scored(3000, 3653)

    content = pb_card.show_pb(None, scenario, playlist_code)

    assert _body_text(content) == expected


def test_the_gaps_pace_basis_is_read_only_for_a_scenario_with_a_ladder(store):
    """Read the gap's basis as the table does, and the hover's basis either way."""
    store["runs"][SCENARIO] = _scored(3000, 3653)

    pb_card.show_pb(None, SCENARIO, PLAYLIST.code)
    assert store["pace_asked"] == []
    assert store["version_pace_asked"] == [(SCENARIO, VERSION)]

    pb_card.show_pb(None, SCENARIO, BENCHMARK.code)
    assert store["pace_asked"] == [SCENARIO]
    assert store["version_pace_asked"] == [(SCENARIO, VERSION)] * 2


def test_a_failed_pace_lookup_costs_the_pace_gap_and_never_the_card(store, caplog):
    sparky = "Ground Plaza Sparky V3"
    store["runs"][sparky] = [
        RunData(**{**run.__dict__, "scenario": sparky}) for run in _scored(880, 896.2)
    ]
    store["pace_basis"] = RuntimeError("unreadable")

    with caplog.at_level(logging.WARNING, logger="source.components.pb_card"):
        content = pb_card.show_pb(None, sparky, BENCHMARK.code)

    assert _body_text(content)[1] == "899 Lavender · +0.4% · 2.8 to go"
    assert f'Failed to tell whether "{sparky}" is time-scored' in caplog.text


def test_a_run_of_a_new_version_that_sets_no_pb_switches_the_wording(store):
    """Why every run on the selected scenario rebuilds the card.

    The pace basis follows the scenario's newest version, so a run that beats
    nothing can still turn the next rank's gap from pace to score.
    """
    sparky = "Ground Plaza Sparky V3"
    runs = [
        RunData(**{**run.__dict__, "scenario": sparky})
        for run in [*_scored(880, 896.2), _run(885.0, 5, scenario_hash=NEWER_VERSION)]
    ]
    store["runs"][sparky] = runs[:2]
    store["pace_basis"] = PaceBasis(constant=1000.0, scenario_hash=VERSION)
    before = pb_card.show_pb(None, sparky, BENCHMARK.code)

    store["runs"][sparky] = runs
    store["pace_basis"] = PaceBasis(constant=1000.0, scenario_hash=NEWER_VERSION)
    after = pb_card.show_pb(["run"], sparky, BENCHMARK.code)

    assert _body_text(before)[1] == "899 Lavender · +2.8% faster · 2.8 to go"
    assert _body_text(after)[1] == "899 Lavender · +0.4% · 2.8 to go"
    assert after.faded == before.faded


# --- On the page ---------------------------------------------------------------


def _registration(output_fragment: str) -> dict:
    return next(
        entry for entry in GLOBAL_CALLBACK_LIST if output_fragment in entry["output"]
    )


def _keys(dependencies) -> list[str]:
    return [f"{item['id']}.{item['property']}" for item in dependencies]


def test_the_card_is_rebuilt_by_a_run_on_its_scenario_the_scenario_and_the_filter():
    """Not by a run on another scenario: the run-events store names only this one.

    The page load runs it too, so the card is right with no new run. It shows
    and hides the leaderboard line, which follows the local PB.
    """
    ids = run_history.PB_CARD_IDS
    registration = _registration(f"{ids.body}.children")

    assert registration["output"] == (
        f"..{ids.set_at}.data...{ids.body}.children"
        f"...{ids.leaderboard}.hidden...{ids.faded}.children.."
    )
    assert _keys(registration["inputs"]) == [
        f"{run_history.RUN_EVENTS_STORE_ID}.data",
        f"{run_history.SCENARIO_SELECTION_IDS.scenario_dropdown}.value",
        f"{run_history.SCENARIO_SELECTION_IDS.playlist_filter}.value",
    ]
    assert registration["prevent_initial_call"] is False


def test_the_pbs_age_is_reworded_in_the_browser_on_the_30_second_tick():
    """The latest-run card's own script, as Last played is reworded."""
    ids = run_history.PB_CARD_IDS
    registration = _registration(f"{ids.time}.children")
    script = next(
        source
        for source in GLOBAL_INLINE_SCRIPTS
        if registration["clientside_function"]["function_name"] in source
    )

    assert registration["output"] == (
        f"..{ids.label}.hidden...{ids.time}.children...{ids.time_tooltip}.label.."
    )
    assert _keys(registration["inputs"]) == [
        f"{ids.set_at}.data",
        f"{run_history.RELATIVE_TIME_INTERVAL_ID}.n_intervals",
    ]
    assert latest_run_card.AGE_SCRIPT in script


@pytest.mark.parametrize(
    ("hint", "class_name"),
    [
        ("username_unset", "scenario-rank-hint scenario-rank-hint-username-unset"),
        ("lookup_failed", "scenario-rank-hint"),
        ("served_stale", "scenario-rank-hint"),
    ],
)
def test_only_the_username_hint_is_marked_for_the_top_rows_offset(hint, class_name):
    """The stylesheet drops the score cards' top offset while that hint shows."""
    _value, shown_hint = pb_card._rank_display("N/A", hint)

    assert shown_hint.className == class_name
