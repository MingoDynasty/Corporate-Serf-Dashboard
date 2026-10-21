"""The Scenario Stats card on the Run History page.

The callbacks live in ``source/components/scenario_stats.py`` and take their
ids from the page that hosts them. These tests hold the card's lines, the run
count with its no-selection state, and the card's registration. The ones that
read a layout or a registration read the page's own. The Position field the
card held until the PB card took it is ``tests/test_pb_card_position.py``.
"""

from types import SimpleNamespace

import dash
import dash_mantine_components as dmc
import pytest
from dash import html
from dash._callback import (
    GLOBAL_CALLBACK_LIST,
    GLOBAL_CALLBACK_MAP,
    GLOBAL_INLINE_SCRIPTS,
)

from source.components import latest_run_card, scenario_selection, scenario_stats
from source.kovaaks import data_service, playlist_scenarios_service
from source.kovaaks.data_models import PlaylistData, Rank, Scenario
from source.kovaaks.scenario_groups import GROUP_EXCLUDED_PLAYLIST_CODES, ScenarioGroup

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import run_history  # noqa: E402

IDS = run_history.SCENARIO_STATS_IDS


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


def _output_keys(registration: dict) -> set[str]:
    """Read a registration's outputs as ``id.prop``, without duplicate hashes."""
    return {
        output.split("@")[0]
        for output in registration["output"].strip(".").split("...")
    }


@pytest.mark.parametrize("selected", [None, ""])
def test_with_no_scenario_selected_the_card_says_so_in_place_of_its_lines(selected):
    """A count of zero there would read as a fact about a scenario."""
    assert scenario_stats.get_scenario_num_runs(None, selected) == (None, True, False)


def test_a_scenario_with_no_runs_counts_zero(monkeypatch):
    monkeypatch.setattr(
        scenario_stats, "is_scenario_in_database", lambda _scenario: False
    )

    assert scenario_stats.get_scenario_num_runs(None, "Unplayed Scenario") == (
        0,
        False,
        True,
    )


def test_a_played_scenario_counts_its_runs(monkeypatch):
    played = SimpleNamespace(number_of_runs=12)
    monkeypatch.setattr(
        scenario_stats, "is_scenario_in_database", lambda _scenario: True
    )
    monkeypatch.setattr(scenario_stats, "get_scenario_stats", lambda _scenario: played)

    assert scenario_stats.get_scenario_num_runs(None, "Played Scenario") == (
        12,
        False,
        True,
    )


# A second page's ids, none of which the Run History page uses.
SECOND_PAGE_IDS = scenario_stats.ScenarioStatsIds(
    *(f"second-{field}" for field in scenario_stats.ScenarioStatsIds._fields)
)
# The ids of what a page builds itself and the card only reads.
PAGE_BUILT_FIELDS = (
    "run_events",
    "scenario_dropdown",
    "playlist_filter",
    "relative_time_interval",
)


def _keys(dependencies: list[dict]) -> list[str]:
    """Read a registration's Inputs or State as ``id.prop``, in their order."""
    return [f"{dep['id']}.{dep['property']}" for dep in dependencies]


def _answering(registration: dict):
    """Return the function a registration runs, or None when the browser runs it."""
    wrapper = GLOBAL_CALLBACK_MAP[registration["output"]].get("callback")
    return getattr(wrapper, "__wrapped__", None)


def _card_registrations(ids) -> list[tuple]:
    """List what is registered to write a card's own components, in order."""
    built = set(ids) - {getattr(ids, field) for field in PAGE_BUILT_FIELDS}
    return [
        (_answering(entry), _keys(entry["inputs"]), _keys(entry["state"]))
        for entry in GLOBAL_CALLBACK_LIST
        if {key.rpartition(".")[0] for key in _output_keys(entry)} & built
    ]


def _expected_registrations(ids) -> list[tuple]:
    """List what ``register_scenario_stats`` registers for ``ids``, in order.

    No clientside callback: Last played's ticking text went with its row.
    """
    return [
        (
            scenario_stats.get_scenario_category,
            [
                f"{ids.run_events}.data",
                f"{ids.scenario_dropdown}.value",
                f"{ids.playlist_filter}.value",
            ],
            [],
        ),
        (
            scenario_stats.get_scenario_num_runs,
            [f"{ids.run_events}.data", f"{ids.scenario_dropdown}.value"],
            [],
        ),
        (
            scenario_stats.get_scenario_typical_score,
            [
                f"{ids.run_events}.data",
                f"{ids.scenario_dropdown}.value",
                f"{ids.relative_time_interval}.n_intervals",
            ],
            [f"{ids.lead}.children", f"{ids.recent_readout}.children"],
        ),
    ]


@pytest.fixture
def restored_callbacks():
    """Take a test's registrations back out of Dash's process-wide registries."""
    saved_list = list(GLOBAL_CALLBACK_LIST)
    saved_map = dict(GLOBAL_CALLBACK_MAP)
    saved_scripts = list(GLOBAL_INLINE_SCRIPTS)
    yield
    GLOBAL_CALLBACK_LIST[:] = saved_list
    GLOBAL_CALLBACK_MAP.clear()
    GLOBAL_CALLBACK_MAP.update(saved_map)
    GLOBAL_INLINE_SCRIPTS[:] = saved_scripts


def _card():
    return next(
        component
        for component in _walk_components(run_history.layout())
        if getattr(component, "className", None) == "scenario-stats-card"
    )


def test_the_card_holds_category_and_the_run_count_and_no_last_played(monkeypatch):
    """Last played went: the latest-run card beside it says when the scenario was played.

    Position moved to the PB card's leaderboard line, ids and all.
    """
    components = _layout_components(monkeypatch)
    card = _card()
    texts = [
        component
        for component in _walk_components(card)
        if isinstance(component, str) and component
    ]

    assert texts == [
        "Typical score",
        " ",
        "Category: ",
        "Total runs: ",
        "No scenario selected",
    ]
    assert not [text for text in texts if "Last played" in text]
    assert components[IDS.category_row].hidden is True
    assert components[IDS.category_row].children.children[0].fw == 700
    assert components[IDS.category_row].children.size == "sm"
    assert components[IDS.num_runs_row].children.size == "sm"
    assert run_history.PB_CARD_IDS.rank in components
    assert run_history.PB_CARD_IDS.rank not in {
        getattr(component, "id", None) for component in _walk_components(card)
    }


def test_the_first_line_is_plain_text_in_sentence_case_and_not_a_heading():
    """As the PB card's ``PB`` and the latest-run card's ``Latest run`` are."""
    first_line = _card().children[0]

    assert isinstance(first_line, html.Div)
    assert not isinstance(first_line, dmc.Title)
    assert first_line.children[0].children[0] == "Typical score"
    assert first_line.className == "scenario-stats-heading"
    assert not [
        component
        for component in _walk_components(_card())
        if isinstance(component, dmc.Title)
    ]


def test_the_no_selection_line_is_drawn_once_hidden_and_styled_as_the_pb_cards(
    monkeypatch,
):
    """The page load's call shows it with nothing selected, in place of the lines."""
    components = _layout_components(monkeypatch)
    line = components[IDS.no_scenario]

    assert line.children == "No scenario selected"
    assert line.hidden is True
    assert line.className == latest_run_card.EMPTY_TITLE_CLASS
    assert getattr(components[IDS.num_runs_row], "hidden", None) is None


def test_the_page_registers_the_card_for_its_own_ids():
    """Registration is a call the page makes; without it the card shows nothing."""
    assert _card_registrations(IDS) == _expected_registrations(IDS)


def test_the_run_count_and_the_no_selection_line_are_written_together():
    """One answer, so the card never shows both or neither."""
    (registration,) = [
        entry
        for entry in GLOBAL_CALLBACK_LIST
        if f"{IDS.no_scenario}.hidden" in _output_keys(entry)
    ]

    assert _output_keys(registration) == {
        f"{IDS.num_runs}.children",
        f"{IDS.num_runs_row}.hidden",
        f"{IDS.no_scenario}.hidden",
    }


def test_a_second_page_builds_a_card_that_shares_no_id_with_the_first(monkeypatch):
    first_page_ids = set(_layout_components(monkeypatch)) - {None}

    built = {
        component.id
        for component in _walk_components(
            scenario_stats.scenario_stats_panel(SECOND_PAGE_IDS)
        )
        if getattr(component, "id", None) is not None
    }

    # Every id in the tree came from the ids passed in, and every id passed
    # in is there apart from the ones a page builds itself.
    assert built == set(SECOND_PAGE_IDS) - {
        getattr(SECOND_PAGE_IDS, field) for field in PAGE_BUILT_FIELDS
    }
    assert not built & first_page_ids


def test_a_second_registration_adds_callbacks_for_its_own_ids_only(
    restored_callbacks,
):
    registered_before = list(GLOBAL_CALLBACK_LIST)
    first_page = _card_registrations(IDS)

    scenario_stats.register_scenario_stats(SECOND_PAGE_IDS)

    assert GLOBAL_CALLBACK_LIST[: len(registered_before)] == registered_before
    added = GLOBAL_CALLBACK_LIST[len(registered_before) :]
    assert _card_registrations(SECOND_PAGE_IDS) == _expected_registrations(
        SECOND_PAGE_IDS
    )
    assert len(added) == len(first_page)
    assert {
        key.rpartition(".")[0] for entry in added for key in _output_keys(entry)
    } == {
        "second-category",
        "second-category_row",
        "second-num_runs",
        "second-num_runs_row",
        "second-no_scenario",
        "second-lead",
        "second-recent_readout",
    }
    assert _card_registrations(IDS) == first_page


@pytest.fixture
def grouped_playlists(monkeypatch):
    rank = Rank(name="Gold", color="#ffcc00", threshold=100)
    playlists = {
        code: PlaylistData(
            name=code,
            code=code,
            scenarios=[
                Scenario(name=name, ranks=[rank]) for name in ("Other", "Shared")
            ],
        )
        for code in ("Two", "One", "Ungrouped", "WrongLength")
    }
    playlists["Plain"] = PlaylistData(
        name="Plain", code="Plain", scenarios=[Scenario(name="Shared")]
    )
    group = ScenarioGroup("Control Tracking", None, 0, "Arm", None, 0)
    one = ScenarioGroup("Clicking", None, 0, "", None, 0)
    monkeypatch.setattr(data_service, "playlist_database", playlists)
    monkeypatch.setattr(
        data_service,
        "_bundled_scenario_groups",
        {"Two": (one, group), "One": (group, one), "WrongLength": (group,)},
    )
    return playlists


@pytest.mark.parametrize(
    ("scenario", "code", "expected"),
    [
        ("Shared", "Two", ("Control Tracking · Arm", False)),
        ("Shared", "One", ("Clicking", False)),
        ("Other", "Two", ("Clicking", False)),
        ("Shared", "Ungrouped", ("", True)),
        ("Shared", "Plain", ("", True)),
        ("Absent", "Two", ("", True)),
        ("Shared", "Unknown", ("", True)),
        ("Shared", None, ("", True)),
        (None, "Two", ("", True)),
    ],
)
def test_category_reads_the_selected_benchmarks_own_table_group(
    grouped_playlists, scenario, code, expected
):
    assert scenario_stats.get_scenario_category(None, scenario, code) == expected


def test_category_and_table_omit_misaligned_groups(grouped_playlists):
    assert playlist_scenarios_service.playlist_scenario_groups(
        grouped_playlists["WrongLength"]
    ) == (None, None)
    assert scenario_stats.get_scenario_category(None, "Shared", "WrongLength") == (
        "",
        True,
    )


def test_a_filter_change_alone_rewrites_category(grouped_playlists):
    assert scenario_stats.get_scenario_category(None, "Shared", "Two") == (
        "Control Tracking · Arm",
        False,
    )
    assert scenario_stats.get_scenario_category(None, "Shared", "One") == (
        "Clicking",
        False,
    )
    assert scenario_stats.get_scenario_category(None, "Shared", None) == ("", True)


def test_an_excluded_bundled_benchmark_has_no_category(monkeypatch, tmp_path):
    monkeypatch.setattr(
        data_service, "USER_PLAYLIST_DIRECTORY_PATH", tmp_path / "playlists"
    )
    for name, empty in (
        ("playlist_database", {}),
        ("playlist_startup_warning_queue", []),
        ("_user_root_playlist_codes", set()),
        ("_user_root_playlist_files", {}),
        ("_superseded_user_playlist_files", []),
        ("_bundled_seed_pairs", []),
        ("_bundled_benchmark_ids", {}),
        ("_bundled_scenario_groups", {}),
        ("_bundled_corpus_load_complete", True),
    ):
        monkeypatch.setattr(data_service, name, empty)
    data_service.load_playlists()
    code = next(iter(GROUP_EXCLUDED_PLAYLIST_CODES))
    playlist = data_service.get_playlist_by_code(code)
    assert playlist is not None
    assert data_service.is_benchmark_playlist(playlist)
    assert data_service.get_scenario_groups(code) is None
    assert scenario_stats.get_scenario_category(
        None, playlist.scenarios[0].name, code
    ) == (
        "",
        True,
    )
