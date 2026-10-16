"""The Scenario Stats card on the Run History page.

The callbacks live in ``source/components/scenario_stats.py`` and take their
ids from the page that hosts them. These tests hold the run count and the Last
played stores, and the card's registration. The ones that read a layout or a
registration read the page's own. The Position field the card held until the
PB card took it is ``tests/test_pb_card_position.py``.
"""

from datetime import datetime
from types import SimpleNamespace

import dash
import pytest
from dash._callback import (
    GLOBAL_CALLBACK_LIST,
    GLOBAL_CALLBACK_MAP,
    GLOBAL_INLINE_SCRIPTS,
)

from source.components import chart_options, scenario_selection, scenario_stats
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


def test_last_played_initial_state_has_no_tooltip_affordance(monkeypatch):
    monkeypatch.setattr(
        scenario_selection, "get_visible_playlist_selector_options", lambda: []
    )
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])

    components = list(_walk_components(run_history.layout()))
    last_played = next(
        component
        for component in components
        if getattr(component, "id", None) == IDS.last_played
    )
    tooltip = next(
        component
        for component in components
        if getattr(component, "id", None) == IDS.last_played_tooltip
    )
    empty_value = next(
        component
        for component in components
        if getattr(component, "id", None) == IDS.last_played_empty_value
    )

    assert last_played.children == ""
    assert empty_value.data == ""
    assert getattr(last_played, "style", None) is None
    assert getattr(last_played, "className", None) is None
    assert getattr(last_played, "tabIndex", None) is None
    assert tooltip.disabled is True
    assert tooltip.label == ""
    assert tooltip.events == chart_options.TOOLTIP_EVENTS


def test_get_scenario_num_runs_without_selection():
    assert scenario_stats.get_scenario_num_runs(None, None) == (
        0,
        None,
        "—",
        "",
        None,
        None,
        True,
    )


def test_get_scenario_num_runs_without_play_data(monkeypatch):
    monkeypatch.setattr(
        scenario_stats, "is_scenario_in_database", lambda _scenario: False
    )

    assert scenario_stats.get_scenario_num_runs(None, "Unplayed Scenario") == (
        0,
        None,
        "Never",
        "",
        None,
        None,
        True,
    )


def test_get_scenario_num_runs_with_play_data(monkeypatch):
    last_played = datetime(2026, 6, 30, 9, 5, 4)
    played = SimpleNamespace(
        number_of_runs=12,
        date_last_played=last_played,
    )
    monkeypatch.setattr(
        scenario_stats, "is_scenario_in_database", lambda _scenario: True
    )
    monkeypatch.setattr(scenario_stats, "get_scenario_stats", lambda _scenario: played)

    assert scenario_stats.get_scenario_num_runs(None, "Played Scenario") == (
        12,
        last_played.timestamp(),
        "Never",
        "Jun 30, 2026, 9:05 AM",
        "cell-tooltip-affordance",
        0,
        False,
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
    """List what ``register_scenario_stats`` registers for ``ids``, in order."""
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
            None,
            [
                f"{ids.last_played_ts}.data",
                f"{ids.last_played_empty_value}.data",
                f"{ids.relative_time_interval}.n_intervals",
            ],
            [],
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


def test_the_card_holds_last_played_and_the_run_count_and_no_position(monkeypatch):
    """Position moved to the PB card's leaderboard line, ids and all."""
    components = _layout_components(monkeypatch)
    card = next(
        component
        for component in _walk_components(run_history.layout())
        if getattr(component, "className", None) == "scenario-stats-card"
    )
    texts = [
        child
        for component in _walk_components(card)
        for child in [getattr(component, "children", None)]
        if isinstance(child, str) and child
    ]

    assert texts == ["Scenario Stats", "Category: ", "Last played:", "Number of runs: "]
    assert components[IDS.category_row].hidden is True
    assert components[IDS.category_row].children.children[0].fw == 700
    assert components[IDS.category_row].children.size == "sm"
    assert run_history.PB_CARD_IDS.rank in components
    assert run_history.PB_CARD_IDS.rank not in {
        getattr(component, "id", None) for component in _walk_components(card)
    }


def test_the_page_registers_the_card_for_its_own_ids():
    """Registration is a call the page makes; without it the card shows nothing."""
    assert _card_registrations(IDS) == _expected_registrations(IDS)


def test_a_second_page_builds_a_card_that_shares_no_id_with_the_first(monkeypatch):
    first_page_ids = set(_layout_components(monkeypatch)) - {None}

    built = {
        component.id
        for tree in (
            *scenario_stats.scenario_stats_stores(SECOND_PAGE_IDS),
            scenario_stats.scenario_stats_panel(SECOND_PAGE_IDS),
        )
        for component in _walk_components(tree)
        if getattr(component, "id", None) is not None
    }

    # Every id in the two trees came from the ids passed in, and every id
    # passed in is there apart from the ones a page builds itself.
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
        "second-last_played",
        "second-last_played_tooltip",
        "second-last_played_ts",
        "second-last_played_empty_value",
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
        ("Shared", "WrongLength", ("", True)),
        ("Shared", "Unknown", ("", True)),
        ("Shared", None, ("", True)),
        (None, "Two", ("", True)),
    ],
)
def test_category_reads_the_selected_benchmarks_own_table_group(
    grouped_playlists, scenario, code, expected
):
    assert scenario_stats.get_scenario_category(None, scenario, code) == expected
    if code in grouped_playlists:
        groups = playlist_scenarios_service.playlist_scenario_groups(
            grouped_playlists[code]
        )
        if code == "WrongLength":
            assert groups == (None, None)


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


def test_an_excluded_bundled_benchmark_has_no_category(monkeypatch):
    monkeypatch.setattr(data_service, "playlist_database", {})
    monkeypatch.setattr(data_service, "_bundled_scenario_groups", {})
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
