"""The playlist filter and the scenario dropdown on the Scenario Performance page.

The callbacks live in ``source/components/scenario_selection.py`` and take
their ids from the page that hosts them. These tests hold what a deep link
selects, what the two dropdowns list, and the link from the filter to its
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


ALPHA = {"label": "Alpha", "value": "KovaaKsAlpha"}
BETA = {"label": "Beta", "value": "KovaaKsBeta"}
DELTA = {"label": "Delta", "value": "KovaaKsDelta"}
GAMMA = {"label": "Gamma", "value": "KovaaKsGamma"}
VISIBLE_PLAYLISTS = [ALPHA, GAMMA]


@pytest.fixture
def playlist_lists(monkeypatch):
    """Load four playlists, two of them hidden, without touching the stores.

    The hidden two sort between the visible two, so a held one that is merely
    appended to the visible list shows up as a wrong order.
    """
    monkeypatch.setattr(
        scenario_selection,
        "get_visible_playlist_selector_options",
        lambda: list(VISIBLE_PLAYLISTS),
    )
    monkeypatch.setattr(
        scenario_selection,
        "get_playlist_selector_options",
        lambda: [ALPHA, BETA, DELTA, GAMMA],
    )
    monkeypatch.setattr(
        scenario_selection,
        "get_playlist_by_code",
        lambda code: object() if code in {"KovaaKsAlpha", "KovaaKsBeta"} else None,
    )
    monkeypatch.setattr(
        scenario_selection,
        "get_scenarios_from_playlist_code",
        lambda code: [f"{code} Scenario"],
    )
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: ["All"])


def _playlist_filter(page):
    return next(
        component
        for component in _walk_components(page)
        if getattr(component, "id", None) == "playlist-dropdown-selection"
    )


@pytest.mark.parametrize("held_playlist", [None, "", "KovaaKsAlpha"])
def test_the_filter_lists_the_visible_playlists(playlist_lists, held_playlist):
    """Nothing held, or a visible playlist held: the visible list as it is."""
    assert (
        scenario_selection.playlist_filter_options(held_playlist) == VISIBLE_PLAYLISTS
    )


def test_the_filter_lists_the_hidden_playlist_it_holds(playlist_lists):
    """A hidden playlist still loads and its scenario table links here.

    Without an option for it the filter shows no name, or the previous
    playlist's, while the rest of the page follows the hidden one. Only the
    held playlist joins the list: the other hidden one stays out.
    """
    assert scenario_selection.playlist_filter_options("KovaaKsBeta") == [
        ALPHA,
        BETA,
        GAMMA,
    ]


def test_the_filter_lists_nothing_for_a_code_no_playlist_has(playlist_lists):
    assert (
        scenario_selection.playlist_filter_options("KovaaKsGoneCode")
        == VISIBLE_PLAYLISTS
    )


def test_select_playlist_keeps_a_hidden_selection_and_lists_it(playlist_lists):
    """The list written to the filter has to hold what the filter holds.

    The Select drops a value its new options lack, so writing the visible
    list alone would clear a hidden selection.
    """
    scenarios, link, options = scenario_selection.select_playlist("KovaaKsBeta", None)

    assert scenarios == ["KovaaKsBeta Scenario"]
    (anchor,) = [
        component
        for component in _walk_components(link)
        if isinstance(component, dmc.Anchor)
    ]
    assert anchor.href == "/playlists/KovaaKsBeta"
    assert options == [ALPHA, BETA, GAMMA]


@pytest.mark.parametrize("selected_playlist", [None, "KovaaKsAlpha", "KovaaKsGoneCode"])
def test_select_playlist_writes_only_the_visible_list_otherwise(
    playlist_lists, selected_playlist
):
    """A code no playlist has gets no option, which is what empties the filter."""
    _scenarios, _link, options = scenario_selection.select_playlist(
        selected_playlist, None
    )

    assert options == VISIBLE_PLAYLISTS


def test_home_layout_lists_a_hidden_playlist_the_url_names(playlist_lists):
    """The first paint can already name a linked playlist, with no round trip."""
    playlist_filter = _playlist_filter(home.layout(playlist_code="KovaaKsBeta"))

    assert playlist_filter.data == [ALPHA, BETA, GAMMA]
    # Still never the query parameter: see the comment on the Select.
    assert playlist_filter.value is None


@pytest.mark.parametrize("playlist_code", [None, "KovaaKsAlpha", "KovaaKsGoneCode"])
def test_home_layout_lists_the_visible_playlists_otherwise(
    playlist_lists, playlist_code
):
    playlist_filter = _playlist_filter(home.layout(playlist_code=playlist_code))

    assert playlist_filter.data == VISIBLE_PLAYLISTS


def test_home_layout_initializes_from_playlist_scenario_query(monkeypatch):
    monkeypatch.setattr(
        scenario_selection,
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


def test_home_select_playlist_ignores_stale_persisted_names(playlist_lists):
    # The second argument is the deep-link store: a scheduling Input the
    # callback never reads. See select_playlist.
    assert scenario_selection.select_playlist("Old Playlist Name", None) == (
        ["All"],
        None,
        VISIBLE_PLAYLISTS,
    )
    scenarios, _link, _options = scenario_selection.select_playlist(
        "KovaaKsAlpha", None
    )
    assert scenarios == ["KovaaKsAlpha Scenario"]


def test_select_playlist_links_the_selection_to_its_scenario_table(playlist_lists):
    """The way back from a scenario to the table it was opened from."""
    _scenarios, link, _options = scenario_selection.select_playlist(
        "KovaaKsAlpha", None
    )

    (anchor,) = [
        component
        for component in _walk_components(link)
        if isinstance(component, dmc.Anchor)
    ]
    assert anchor.children == "Open scenario table"
    # The bare route: no ``?sort=``, so the table opens in playlist order.
    assert anchor.href == "/playlists/KovaaKsAlpha"
    # In-app navigation, as every other internal link on the page.
    assert anchor.refresh is False


@pytest.mark.parametrize("selected_playlist", [None, "", "KovaaKsGoneCode"])
def test_select_playlist_shows_no_link_without_a_loaded_playlist(
    playlist_lists, selected_playlist
):
    """A cleared filter and a remembered code that no longer resolves both
    list every local scenario, so neither has a table to link."""
    scenarios, link, _options = scenario_selection.select_playlist(
        selected_playlist, None
    )

    assert scenarios == ["All"]
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
        "playlist-dropdown-selection.data",
    }


def test_select_playlist_lists_nothing_without_a_usable_directory(
    monkeypatch, playlist_lists
):
    settings_service.save_settings({})
    settings_service.resolve_stats_dir()
    monkeypatch.setattr(
        scenario_selection,
        "get_scenario_names",
        lambda: pytest.fail("listed scenarios without a usable stats directory"),
    )

    scenarios, link, _options = scenario_selection.select_playlist(None, None)

    assert (scenarios, link) == ([], None)


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

    monkeypatch.setattr(
        scenario_selection, "get_visible_playlist_selector_options", lambda: []
    )
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
        "second-playlist_filter.data",
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


# --- A scenario the playlist filter does not list --------------------------------
#
# ``reach_scenario`` is the Run History page's rule: a link or a followed run
# that names such a scenario clears the filter and selects the scenario. The
# Scenario Performance page keeps ``apply_deep_link``, which the tests above
# hold: the filter stays and the scenario is dropped.

ALPHA_CODE, BETA_CODE = "KovaaKsAlpha", "KovaaKsBeta"
LISTED = "KovaaKsAlpha Scenario"
OUTSIDE = "Outside Scenario"
NEVER_PLAYED = "Never Played"


@pytest.fixture
def played(monkeypatch, playlist_lists):
    """Two loaded playlists that each list one scenario, and two scenarios with runs.

    ``LISTED`` is in the first playlist and has runs. ``OUTSIDE`` has runs
    and is in neither. ``NEVER_PLAYED`` is in neither and has none.
    """
    monkeypatch.setattr(
        scenario_selection,
        "is_scenario_in_database",
        lambda name: name in {LISTED, OUTSIDE},
    )


def _landed_on(scenario_name: str) -> dict:
    """Build a page's run summary whose latest run is on a scenario."""
    return {"latest": {"scenario_name": scenario_name}, "celebrated_run_id": None}


@pytest.mark.parametrize(
    ("selection", "held_filter", "expected"),
    [
        # No parameters: nothing is written, whatever the browser restored.
        ({}, ALPHA_CODE, (no_update, no_update)),
        (None, ALPHA_CODE, (no_update, no_update)),
        # ?scenario= alone, against the filter the browser restored.
        ({"scenario": LISTED}, ALPHA_CODE, (no_update, LISTED)),
        ({"scenario": OUTSIDE}, ALPHA_CODE, (None, OUTSIDE)),
        ({"scenario": OUTSIDE}, None, (no_update, OUTSIDE)),
        ({"scenario": OUTSIDE}, "", (no_update, OUTSIDE)),
        # A remembered code no playlist has filters nothing, and the scenario
        # list callback drops it.
        ({"scenario": OUTSIDE}, "KovaaKsGoneCode", (no_update, OUTSIDE)),
        # Clearing the filter would not put a scenario with no runs on the
        # list, so the filter stays.
        ({"scenario": NEVER_PLAYED}, ALPHA_CODE, (no_update, NEVER_PLAYED)),
        ({"scenario": None}, ALPHA_CODE, (no_update, None)),
        # ?playlist_code= alone names no scenario, so nothing is cleared.
        ({"playlist": ALPHA_CODE}, BETA_CODE, (ALPHA_CODE, no_update)),
        ({"playlist": None}, ALPHA_CODE, (None, no_update)),
        # Both: the filter the link itself names is the one that counts.
        ({"playlist": ALPHA_CODE, "scenario": LISTED}, BETA_CODE, (ALPHA_CODE, LISTED)),
        ({"playlist": ALPHA_CODE, "scenario": OUTSIDE}, None, (None, OUTSIDE)),
        ({"playlist": ALPHA_CODE, "scenario": OUTSIDE}, ALPHA_CODE, (None, OUTSIDE)),
        (
            {"playlist": ALPHA_CODE, "scenario": NEVER_PLAYED},
            None,
            (ALPHA_CODE, NEVER_PLAYED),
        ),
        ({"playlist": ALPHA_CODE, "scenario": None}, BETA_CODE, (ALPHA_CODE, None)),
        # An unknown code arrives as no playlist, which clears the filter as
        # it always did.
        ({"playlist": None, "scenario": OUTSIDE}, ALPHA_CODE, (None, OUTSIDE)),
    ],
)
def test_a_link_to_a_scenario_the_filter_does_not_list_clears_the_filter(
    played, selection, held_filter, expected
):
    """Each combination of the two parameters, on a visit with no run landed."""
    assert (
        scenario_selection.reach_scenario(
            selection, None, True, held_filter, "Remembered Scenario"
        )
        == expected
    )


@pytest.mark.parametrize("follow_newly_played", [True, False])
def test_a_link_is_applied_whatever_the_follow_switch_says(played, follow_newly_played):
    assert scenario_selection.reach_scenario(
        {"scenario": OUTSIDE}, None, follow_newly_played, ALPHA_CODE, LISTED
    ) == (None, OUTSIDE)


@pytest.mark.parametrize(
    ("played_on", "held_filter", "selected", "expected"),
    [
        # The filter does not list the scenario just played: it is cleared.
        (OUTSIDE, ALPHA_CODE, LISTED, (None, OUTSIDE)),
        # It lists it, or there is no filter: only the scenario moves.
        (LISTED, ALPHA_CODE, OUTSIDE, (no_update, LISTED)),
        (OUTSIDE, None, LISTED, (no_update, OUTSIDE)),
        (OUTSIDE, "KovaaKsGoneCode", LISTED, (no_update, OUTSIDE)),
        (OUTSIDE, ALPHA_CODE, None, (None, OUTSIDE)),
        # Still on the scenario being played: nothing to write.
        (LISTED, ALPHA_CODE, LISTED, (no_update, no_update)),
        (OUTSIDE, None, OUTSIDE, (no_update, no_update)),
    ],
)
def test_follow_selects_the_scenario_just_played_and_clears_a_filter_in_its_way(
    played, played_on, held_filter, selected, expected
):
    assert (
        scenario_selection.reach_scenario(
            {}, _landed_on(played_on), True, held_filter, selected
        )
        == expected
    )


@pytest.mark.parametrize("played_on", [LISTED, OUTSIDE])
def test_with_follow_off_a_landed_run_moves_nothing(played, played_on):
    """The summary is then for the selected scenario, and the switch is read anyway.

    A selection the user changes while a batch is on its way must not be put
    back by the summary of the scenario they left.
    """
    assert scenario_selection.reach_scenario(
        {}, _landed_on(played_on), False, ALPHA_CODE, LISTED
    ) == (no_update, no_update)


def test_a_landed_run_is_not_answered_by_applying_the_link_again(played):
    """The visit's parameters are applied once, when the page is drawn.

    The deep-link store still holds them when a run lands, and the selection
    the user has since made must not be put back.
    """
    opened_with = {"playlist": ALPHA_CODE, "scenario": LISTED}

    assert scenario_selection.reach_scenario(
        opened_with, _landed_on(OUTSIDE), True, BETA_CODE, OUTSIDE
    ) == (no_update, no_update)
    assert scenario_selection.reach_scenario(
        opened_with, _landed_on(OUTSIDE), True, ALPHA_CODE, LISTED
    ) == (None, OUTSIDE)


def test_the_clearing_registration_adds_callbacks_for_its_own_ids_only(
    restored_callbacks,
):
    registered_before = list(GLOBAL_CALLBACK_LIST)

    scenario_selection.register_scenario_selection_clearing_filter(
        SECOND_PAGE_IDS,
        run_events="second-run_events",
        follow_switch="second-follow_switch",
    )

    assert GLOBAL_CALLBACK_LIST[: len(registered_before)] == registered_before
    select_playlist, reach_scenario = GLOBAL_CALLBACK_LIST[len(registered_before) :]
    assert _answering(select_playlist) == "select_playlist"
    assert _answering(reach_scenario) == "reach_scenario"
    # Plain outputs, both: a callback is held back for a plain output and not
    # for a duplicate one, and the scenario list must wait for the filter.
    assert reach_scenario["output"] == (
        "..second-playlist_filter.value...second-scenario_dropdown.value.."
    )
    assert _input_keys(reach_scenario) == {
        "second-deep_link.data",
        "second-run_events.data",
    }
    assert [f"{dep['id']}.{dep['property']}" for dep in reach_scenario["state"]] == [
        "second-follow_switch.checked",
        "second-playlist_filter.value",
        "second-scenario_dropdown.value",
    ]
    assert reach_scenario["prevent_initial_call"] is False
    # The scenario list keeps the Input nothing writes, for the same reason
    # as on the other page.
    assert not _input_keys(select_playlist) <= _output_keys(reach_scenario)
    # It also takes the run summary, so a scenario whose first run has just
    # landed joins the list. The filter's value is ``reach_scenario``'s plain
    # output, which is what makes Dash hold the list for the selection.
    assert _input_keys(select_playlist) == {
        "second-playlist_filter.value",
        "second-deep_link.data",
        "second-run_events.data",
    }


def test_a_run_summary_has_the_local_list_read_again(monkeypatch, playlist_lists):
    """The first run of a scenario adds it to the list a page drew before it.

    With no filter to clear, nothing else writes the list, and the dropdown
    would go on showing the old name for a scenario it cannot name.
    """
    drawn_with = scenario_selection.select_playlist(None, None)
    monkeypatch.setattr(
        scenario_selection, "get_scenario_names", lambda: ["All", "Just Played"]
    )

    scenarios, link, options = scenario_selection.select_playlist(
        None, None, _landed_on("Just Played")
    )

    assert drawn_with[0] == ["All"]
    assert scenarios == ["All", "Just Played"]
    assert (link, options) == (None, VISIBLE_PLAYLISTS)


def test_a_run_summary_leaves_a_playlists_list_as_it_is(playlist_lists):
    """A filter that stays lists its playlist's scenarios, run or no run."""
    assert scenario_selection.select_playlist(
        "KovaaKsAlpha", None, _landed_on("KovaaKsAlpha Scenario")
    )[0] == ["KovaaKsAlpha Scenario"]


def test_the_old_pages_scenario_list_takes_no_run_summary():
    """Its Follow never clears a filter, and its served callbacks must not change."""
    (registration,) = [
        entry
        for entry in GLOBAL_CALLBACK_LIST
        if "scenario-dropdown-selection.data" in entry["output"]
    ]

    assert _input_keys(registration) == {
        "playlist-dropdown-selection.value",
        f"{home.SCENARIO_SELECTION_IDS.deep_link}.data",
    }


def test_the_old_page_keeps_the_rule_that_drops_the_scenario():
    """R7 is the new page's alone until it replaces this one."""
    answering = {
        _answering(entry)
        for entry in GLOBAL_CALLBACK_LIST
        if home.SCENARIO_SELECTION_IDS.deep_link
        in {dep["id"] for dep in entry["inputs"]}
    }

    assert answering == {"select_playlist", "apply_deep_link"}
