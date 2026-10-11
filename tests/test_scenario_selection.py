"""The playlist filter and the scenario dropdown on the Scenario Performance page.

The callbacks live in ``source/components/scenario_selection.py`` and take
their ids from the page that hosts them. These tests hold what a deep link
selects, what the scenario dropdown lists, and the link from the filter to its
scenario table. Two of them read the page's real registrations, for the rule
that keeps the scenario list from going unwritten on a visit with no query
parameters.
"""

import dash
import dash_mantine_components as dmc
import pytest
from dash import no_update
from dash._callback import GLOBAL_CALLBACK_LIST, GLOBAL_CALLBACK_MAP

from source.components import scenario_selection
from source.config import settings_service

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402


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


def test_home_layout_initializes_from_playlist_scenario_query(monkeypatch):
    monkeypatch.setattr(
        home,
        "get_visible_playlist_selector_options",
        lambda: [{"label": "Voltaic Benchmarks", "value": "KovaaKsTestCode"}],
    )
    monkeypatch.setattr(
        scenario_selection,
        "get_playlist_by_code",
        lambda code: object() if code == "KovaaKsTestCode" else None,
    )
    monkeypatch.setattr(
        scenario_selection,
        "get_scenarios_from_playlist_code",
        lambda code: [f"{code} Scenario"],
    )
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: ["All"])

    page = home.layout(
        scenario="KovaaKsTestCode Scenario",
        playlist_code="KovaaKsTestCode",
    )
    components = list(_walk_components(page))
    playlist_filter = next(
        component
        for component in components
        if getattr(component, "id", None) == "playlist-dropdown-selection"
    )
    scenario_dropdown = next(
        component
        for component in components
        if getattr(component, "id", None) == "scenario-dropdown-selection"
    )
    deep_link_store = next(
        component
        for component in components
        if getattr(component, "id", None) == home.SCENARIO_SELECTION_IDS.deep_link
    )

    # The query parameters reach the dropdowns through the store, never as
    # the layout value: a persisted control's default has to be the same on
    # every visit or Dash discards the stored edit instead of restoring it.
    assert deep_link_store.data == {
        "playlist": "KovaaKsTestCode",
        "scenario": "KovaaKsTestCode Scenario",
    }
    assert playlist_filter.value is None
    assert playlist_filter.persistence is True
    assert scenario_dropdown.value is None
    assert scenario_dropdown.persistence is True
    # Still resolved in the layout, so the first paint already lists the
    # deep-linked playlist's scenarios.
    assert scenario_dropdown.data == ["KovaaKsTestCode Scenario"]


def _known_playlist(monkeypatch):
    monkeypatch.setattr(
        scenario_selection,
        "get_playlist_by_code",
        lambda code: object() if code == "KovaaKsTestCode" else None,
    )


def test_home_deep_link_records_only_the_parameters_the_url_carried(monkeypatch):
    """An absent parameter leaves its control on the restored value."""
    _known_playlist(monkeypatch)

    assert scenario_selection.deep_link_selection(None, None) == {}
    assert scenario_selection.deep_link_selection("Scenario A", None) == {
        "scenario": "Scenario A"
    }
    assert scenario_selection.deep_link_selection(None, "KovaaKsTestCode") == {
        "playlist": "KovaaKsTestCode"
    }


def test_home_deep_link_clears_the_filter_for_an_unknown_playlist_code(monkeypatch):
    """The URL's selection is applied as given: no playlist means no filter."""
    _known_playlist(monkeypatch)

    assert scenario_selection.deep_link_selection(None, "KovaaKsGoneCode") == {
        "playlist": None
    }


def test_home_deep_link_treats_an_empty_scenario_as_no_scenario(monkeypatch):
    _known_playlist(monkeypatch)

    assert scenario_selection.deep_link_selection("", "KovaaKsTestCode") == {
        "playlist": "KovaaKsTestCode",
        "scenario": None,
    }


def test_apply_deep_link_writes_only_the_controls_the_url_named():
    assert scenario_selection.apply_deep_link({}) == (no_update, no_update)
    assert scenario_selection.apply_deep_link(None) == (no_update, no_update)
    assert scenario_selection.apply_deep_link({"scenario": "Scenario A"}) == (
        no_update,
        "Scenario A",
    )
    assert scenario_selection.apply_deep_link({"playlist": None}) == (None, no_update)
    assert scenario_selection.apply_deep_link(
        {"playlist": "KovaaKsTestCode", "scenario": "Scenario A"}
    ) == ("KovaaKsTestCode", "Scenario A")


def test_apply_deep_link_is_a_second_writer_of_the_scenario_value():
    """It shares the scenario value with the run-event consumer.

    ``initial_duplicate`` rather than ``True``: applying the deep link is the
    mount's whole job, and Dash refuses an ``allow_duplicate`` output without
    one of the ``prevent_initial_call`` forms.
    """
    registration = _deep_link_registration()
    playlist_output, scenario_output = registration["output"].strip(".").split("...")

    assert playlist_output == "playlist-dropdown-selection.value"
    # The suffix Dash appends to an allow_duplicate output. The scenario value
    # already has a writer in check_for_new_data; the playlist filter does not.
    assert scenario_output.startswith("scenario-dropdown-selection.value@")
    # What Dash stores for "initial_duplicate": the mount still runs it.
    assert registration["prevent_initial_call"] is False


def _deep_link_registration() -> dict:
    """Find apply_deep_link's registration. The store has more than one reader."""
    (registration,) = [
        entry
        for entry in GLOBAL_CALLBACK_LIST
        if any(
            dep["id"] == home.SCENARIO_SELECTION_IDS.deep_link
            for dep in entry["inputs"]
        )
        and "playlist-dropdown-selection.value" in entry["output"]
    ]
    return registration


def _output_keys(registration: dict) -> set[str]:
    """Read a registration's outputs as ``id.prop``, without duplicate hashes."""
    return {
        output.split("@")[0]
        for output in registration["output"].strip(".").split("...")
    }


def test_no_callback_depends_only_on_what_apply_deep_link_conditionally_writes():
    """Guard the regression that shipped once: a starved single-Input dependent.

    ``apply_deep_link`` returns ``no_update`` for a control the URL did not
    name, which is every control on an ordinary visit. dash-renderer drops a
    ready callback when none of its Inputs was written and every one of them
    is a declared output of a group member that already ran, so a callback
    whose Inputs are all written by ``apply_deep_link`` never makes its
    initial call on those visits. ``select_playlist`` was exactly that, and
    the scenario dropdown kept the full local list while the filter named a
    playlist. Its second Input is what this test protects.
    """
    deep_link = _deep_link_registration()
    written = _output_keys(deep_link)

    starved = [
        entry["output"]
        for entry in GLOBAL_CALLBACK_LIST
        if entry is not deep_link
        and entry["inputs"]
        and {f"{dep['id']}.{dep['property']}" for dep in entry["inputs"]} <= written
    ]

    assert starved == [], (
        "these callbacks would not make their initial call on a visit with no "
        f"query parameters: {starved}"
    )


def test_home_select_playlist_ignores_stale_persisted_names(monkeypatch):
    monkeypatch.setattr(
        scenario_selection,
        "get_playlist_by_code",
        lambda code: object() if code == "ValidCode" else None,
    )
    monkeypatch.setattr(
        scenario_selection,
        "get_scenarios_from_playlist_code",
        lambda code: [f"{code} Scenario"],
    )
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: ["All"])

    # The second argument is the deep-link store: a scheduling Input the
    # callback never reads. See select_playlist.
    assert scenario_selection.select_playlist("Old Playlist Name", None) == (
        ["All"],
        None,
    )
    scenarios, _link = scenario_selection.select_playlist("ValidCode", None)
    assert scenarios == ["ValidCode Scenario"]


def test_select_playlist_links_the_selection_to_its_scenario_table(monkeypatch):
    """The way back from a scenario to the table it was opened from."""
    _known_playlist(monkeypatch)
    monkeypatch.setattr(
        scenario_selection, "get_scenarios_from_playlist_code", lambda _code: []
    )

    _scenarios, link = scenario_selection.select_playlist("KovaaKsTestCode", None)

    (anchor,) = [
        component
        for component in _walk_components(link)
        if isinstance(component, dmc.Anchor)
    ]
    assert anchor.children == "Open scenario table"
    # The bare route: no ``?sort=``, so the table opens in playlist order.
    assert anchor.href == "/playlists/KovaaKsTestCode"
    # In-app navigation, as every other internal link on the page.
    assert anchor.refresh is False


@pytest.mark.parametrize("selected_playlist", [None, "", "KovaaKsGoneCode"])
def test_select_playlist_shows_no_link_without_a_loaded_playlist(
    monkeypatch, selected_playlist
):
    """A cleared filter and a remembered code that no longer resolves both
    list every local scenario, so neither has a table to link."""
    _known_playlist(monkeypatch)
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])

    _scenarios, link = scenario_selection.select_playlist(selected_playlist, None)

    assert link is None


def test_select_playlist_writes_the_link_holder_the_layout_carries():
    (registration,) = [
        entry
        for entry in GLOBAL_CALLBACK_LIST
        if "scenario-dropdown-selection.data" in entry["output"]
    ]

    assert _output_keys(registration) == {
        "scenario-dropdown-selection.data",
        f"{home.SCENARIO_SELECTION_IDS.playlist_table_link}.children",
    }


def test_select_playlist_lists_nothing_without_a_usable_directory(monkeypatch):
    settings_service.save_settings({})
    settings_service.resolve_stats_dir()
    monkeypatch.setattr(
        scenario_selection,
        "get_scenario_names",
        lambda: pytest.fail("listed scenarios without a usable stats directory"),
    )

    assert scenario_selection.select_playlist(None, None) == ([], None)


# A second page's ids, none of which the Scenario Performance page uses.
SECOND_PAGE_IDS = scenario_selection.ScenarioSelectionIds(
    *(f"second-{field}" for field in scenario_selection.ScenarioSelectionIds._fields)
)


def _input_keys(registration: dict) -> set[str]:
    """Read a registration's Inputs as ``id.prop``."""
    return {f"{dep['id']}.{dep['property']}" for dep in registration["inputs"]}


def _answering(registration: dict) -> str:
    """Name the function a registration runs."""
    return GLOBAL_CALLBACK_MAP[registration["output"]]["callback"].__name__


@pytest.fixture
def restored_callbacks():
    """Take a test's registrations back out of Dash's process-wide registry."""
    saved_list = list(GLOBAL_CALLBACK_LIST)
    saved_map = dict(GLOBAL_CALLBACK_MAP)
    yield
    GLOBAL_CALLBACK_LIST[:] = saved_list
    GLOBAL_CALLBACK_MAP.clear()
    GLOBAL_CALLBACK_MAP.update(saved_map)


def test_the_page_gives_the_block_the_ids_its_layout_builds(monkeypatch):
    # The ids are data the page passes in, so a typo there resets every
    # user's stored selection, or leaves a callback writing to nothing.
    assert home.SCENARIO_SELECTION_IDS._asdict() == {
        "playlist_filter": "playlist-dropdown-selection",
        "scenario_dropdown": "scenario-dropdown-selection",
        "deep_link": "home-deep-link",
        "playlist_table_link": "playlist-table-link",
    }

    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])
    mounted = {
        getattr(component, "id", None) for component in _walk_components(home.layout())
    }
    # The layout spells the two dropdowns' ids itself, so nothing but this
    # ties them to the ids the callbacks were registered for.
    assert set(home.SCENARIO_SELECTION_IDS) <= mounted


def test_the_page_registers_the_block_for_its_own_ids():
    """Registration is a call the page makes; without it both go quiet."""
    registered = {
        _answering(entry): _input_keys(entry)
        for entry in GLOBAL_CALLBACK_LIST
        if home.SCENARIO_SELECTION_IDS.deep_link
        in {dep["id"] for dep in entry["inputs"]}
    }

    assert registered == {
        "select_playlist": {"playlist-dropdown-selection.value", "home-deep-link.data"},
        "apply_deep_link": {"home-deep-link.data"},
    }


def test_a_second_registration_adds_callbacks_for_its_own_ids_only(
    restored_callbacks,
):
    registered_before = list(GLOBAL_CALLBACK_LIST)

    scenario_selection.register_scenario_selection(SECOND_PAGE_IDS)

    assert GLOBAL_CALLBACK_LIST[: len(registered_before)] == registered_before
    select_playlist, apply_deep_link = GLOBAL_CALLBACK_LIST[len(registered_before) :]
    assert _answering(select_playlist) == "select_playlist"
    assert _output_keys(select_playlist) == {
        "second-scenario_dropdown.data",
        "second-playlist_table_link.children",
    }
    assert _answering(apply_deep_link) == "apply_deep_link"
    assert _output_keys(apply_deep_link) == {
        "second-playlist_filter.value",
        "second-scenario_dropdown.value",
    }
    assert _input_keys(apply_deep_link) == {"second-deep_link.data"}
    assert select_playlist["state"] == apply_deep_link["state"] == []
    # The second page gets the Input that keeps its scenario list from going
    # unwritten too: without the store, every Input of ``select_playlist``
    # would be something ``apply_deep_link`` conditionally writes.
    assert _input_keys(select_playlist) == {
        "second-playlist_filter.value",
        "second-deep_link.data",
    }
    assert not _input_keys(select_playlist) <= _output_keys(apply_deep_link)
