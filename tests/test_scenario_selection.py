"""The playlist filter and the scenario dropdown on the Run History page.

The callbacks live in ``source/components/scenario_selection.py`` and take
their ids from the page that hosts them. These tests hold what a deep link
selects, what the two dropdowns list, the link from the filter to its
scenario table, and the rule for a scenario the filter does not list. What
keeps the scenario list from going unwritten on a visit with no query
parameters is read off the page's registrations in
``tests/test_run_history_page.py``.
"""

from types import SimpleNamespace

import dash
import dash_mantine_components as dmc
import pytest
from dash import no_update
from dash._callback import GLOBAL_CALLBACK_LIST, GLOBAL_CALLBACK_MAP

from source.components import scenario_selection
from source.config import settings_service

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import run_history  # noqa: E402

IDS = run_history.SCENARIO_SELECTION_IDS


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
        if getattr(component, "id", None) == IDS.playlist_filter
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
    scenarios, link, options = scenario_selection.select_playlist(
        "KovaaKsBeta", None, None
    )

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
        selected_playlist, None, None
    )

    assert options == VISIBLE_PLAYLISTS


def test_the_layout_lists_a_hidden_playlist_the_url_names(playlist_lists):
    """The first paint can already name a linked playlist, with no round trip."""
    playlist_filter = _playlist_filter(run_history.layout(playlist_code="KovaaKsBeta"))

    assert playlist_filter.data == [ALPHA, BETA, GAMMA]
    # Still never the query parameter: see the comment on the Select.
    assert playlist_filter.value is None


@pytest.mark.parametrize("playlist_code", [None, "KovaaKsAlpha", "KovaaKsGoneCode"])
def test_the_layout_lists_the_visible_playlists_otherwise(
    playlist_lists, playlist_code
):
    playlist_filter = _playlist_filter(run_history.layout(playlist_code=playlist_code))

    assert playlist_filter.data == VISIBLE_PLAYLISTS


def test_the_layout_initializes_from_playlist_scenario_query(monkeypatch):
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

    page = run_history.layout(
        scenario="KovaaKsTestCode Scenario",
        playlist_code="KovaaKsTestCode",
    )
    components = list(_walk_components(page))
    playlist_filter = next(
        component
        for component in components
        if getattr(component, "id", None) == IDS.playlist_filter
    )
    scenario_dropdown = next(
        component
        for component in components
        if getattr(component, "id", None) == IDS.scenario_dropdown
    )
    deep_link_store = next(
        component
        for component in components
        if getattr(component, "id", None) == IDS.deep_link
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


def test_a_deep_link_records_only_the_parameters_the_url_carried(monkeypatch):
    """An absent parameter leaves its control on the restored value."""
    _known_playlist(monkeypatch)

    assert scenario_selection.deep_link_selection(None, None) == {}
    assert scenario_selection.deep_link_selection("Scenario A", None) == {
        "scenario": "Scenario A"
    }
    assert scenario_selection.deep_link_selection(None, "KovaaKsTestCode") == {
        "playlist": "KovaaKsTestCode"
    }


def test_a_deep_link_clears_the_filter_for_an_unknown_playlist_code(monkeypatch):
    """The URL's selection is applied as given: no playlist means no filter."""
    _known_playlist(monkeypatch)

    assert scenario_selection.deep_link_selection(None, "KovaaKsGoneCode") == {
        "playlist": None
    }


def test_a_deep_link_treats_an_empty_scenario_as_no_scenario(monkeypatch):
    _known_playlist(monkeypatch)

    assert scenario_selection.deep_link_selection("", "KovaaKsTestCode") == {
        "playlist": "KovaaKsTestCode",
        "scenario": None,
    }


def _output_keys(registration: dict) -> set[str]:
    """Read a registration's outputs as ``id.prop``, without duplicate hashes."""
    return {
        output.split("@")[0]
        for output in registration["output"].strip(".").split("...")
    }


def test_select_playlist_ignores_stale_persisted_names(playlist_lists):
    # The second argument is the deep-link store, and the third the store
    # written for every batch of runs: two Inputs the callback never reads.
    # See select_playlist.
    assert scenario_selection.select_playlist("Old Playlist Name", None, None) == (
        ["All"],
        None,
        VISIBLE_PLAYLISTS,
    )
    scenarios, _link, _options = scenario_selection.select_playlist(
        "KovaaKsAlpha", None, None
    )
    assert scenarios == ["KovaaKsAlpha Scenario"]


def test_select_playlist_links_the_selection_to_its_scenario_table(playlist_lists):
    """The way back from a scenario to the table it was opened from."""
    _scenarios, link, _options = scenario_selection.select_playlist(
        "KovaaKsAlpha", None, None
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
        selected_playlist, None, None
    )

    assert scenarios == ["All"]
    assert link is None


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

    scenarios, link, _options = scenario_selection.select_playlist(None, None, None)

    assert (scenarios, link) == ([], None)


def _scenario_dropdown(page):
    return next(
        component
        for component in _walk_components(page)
        if getattr(component, "id", None) == IDS.scenario_dropdown
    )


def test_the_layout_lists_the_local_scenarios_with_a_usable_directory(playlist_lists):
    """The autouse fixtures pin the fixture stats folder, as startup would."""
    assert _scenario_dropdown(run_history.layout()).data == ["All"]


@pytest.mark.parametrize(
    "stored",
    [
        {},
        {settings_service.STATS_DIR_KEY: ""},
        {settings_service.STATS_DIR_KEY: "no-such-stats-dir"},
    ],
    ids=["never_set", "emptied", "vanished"],
)
def test_the_layout_lists_no_scenario_without_a_usable_directory(
    monkeypatch, playlist_lists, stored
):
    """The first paint is as empty as the list the callback then writes."""
    settings_service.save_settings(stored)
    settings_service.resolve_stats_dir()
    monkeypatch.setattr(
        scenario_selection,
        "get_scenario_names",
        lambda: pytest.fail("listed scenarios without a usable stats directory"),
    )

    assert _scenario_dropdown(run_history.layout()).data == []


def test_the_layout_lists_no_scenario_from_a_folder_saved_since_startup(
    monkeypatch, playlist_lists, tmp_path
):
    """A saved folder is not in use until the app restarts."""
    settings_service.save_settings({})
    settings_service.resolve_stats_dir()
    settings_service.save_settings({settings_service.STATS_DIR_KEY: str(tmp_path)})
    monkeypatch.setattr(
        scenario_selection,
        "get_scenario_names",
        lambda: pytest.fail("listed scenarios without a usable stats directory"),
    )

    assert _scenario_dropdown(run_history.layout()).data == []


# A second page's ids, none of which the Run History page uses.
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


def test_the_page_registers_the_block_for_its_own_ids():
    """Registration is a call the page makes; without it both go quiet."""
    registered = {
        _answering(entry): _input_keys(entry)
        for entry in GLOBAL_CALLBACK_LIST
        if IDS.deep_link in {dep["id"] for dep in entry["inputs"]}
    }

    assert registered == {
        "select_playlist": {
            f"{IDS.playlist_filter}.value",
            f"{IDS.deep_link}.data",
            f"{run_history.RUN_LANDED_STORE_ID}.data",
        },
        "reach_scenario_or_the_one_asked_for": {
            f"{IDS.deep_link}.data",
            f"{run_history.RUN_EVENTS_STORE_ID}.data",
            f"{run_history.RUN_LIST_IDS.scenario_asked}.data",
            f"{run_history.NOTE_CARD_IDS.go}.data",
            f"{run_history.FOLLOW_SWITCH_ID}.checked",
        },
    }


# --- A scenario the playlist filter does not list --------------------------------
#
# ``reach_scenario`` holds the rule: a link or a followed run that names such
# a scenario clears the filter and selects the scenario.

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
    return {"latest": {"scenario_name": scenario_name}}


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


def _called_by(monkeypatch, *prop_ids: str, value=1) -> None:
    """Say which inputs triggered the call, as Dash reports them."""
    triggered = [{"prop_id": prop_id, "value": value} for prop_id in prop_ids]
    monkeypatch.setattr(
        scenario_selection,
        "ctx",
        # A call nothing triggered reports one item that names no input.
        SimpleNamespace(triggered=triggered or [{"prop_id": ".", "value": None}]),
    )


LIST_ASKED = "page-list-asked.data"


RUN_EVENTS = "page-run-events.data"
GO = "page-go.data"
FOLLOW = "page-follow.checked"
DEEP_LINK = "page-deep-link.data"
PROPS = scenario_selection.SelectionProps(
    list_asked=LIST_ASKED,
    run_events=RUN_EVENTS,
    go=GO,
    follow=FOLLOW,
    deep_link=DEEP_LINK,
)
# An editor opened on LISTED's note, and a text that differs from it.
EDITING_LISTED = {"scenario": LISTED, "opened": "aim lower"}
UNSAVED = "aim lower, and slower"


def _reach_all(  # noqa: PLR0913
    selection,
    run_events,
    follow_newly_played,
    held_filter,
    selected,
    list_scenario=None,
    *,
    request=None,
    editor=None,
    draft=None,
    waiting=None,
):
    """Call the selection callback as Dash would, with what ``_called_by`` set.

    Returns all four outputs: the filter, the scenario, the wait, and a name
    held for the note card.
    """
    return scenario_selection.reach_the_scenario_asked_for(
        scenario_selection.ctx.triggered,
        PROPS,
        selection,
        run_events,
        list_scenario,
        request,
        follow_newly_played,
        held_filter,
        selected,
        editor,
        draft,
        waiting,
    )


def _reach(*args, **kwargs):
    """Call it with no note open, and return the two dropdowns' values.

    With no note open the wait and the held store are never written.
    """
    result = _reach_all(*args, **kwargs)
    assert result[2:] == (no_update, no_update)
    return result[:2]


def test_a_run_that_lands_after_a_press_is_followed_as_before(monkeypatch, played):
    """The list's store replays the last name pressed, and is not what called."""
    _called_by(monkeypatch, RUN_EVENTS)

    assert _reach({}, _landed_on(OUTSIDE), True, ALPHA_CODE, LISTED, NEVER_PLAYED) == (
        None,
        OUTSIDE,
    )
    assert _reach({}, _landed_on(OUTSIDE), False, ALPHA_CODE, LISTED, NEVER_PLAYED) == (
        no_update,
        no_update,
    )


def test_the_page_load_applies_the_link_and_not_a_name_nobody_pressed(
    monkeypatch, played
):
    _called_by(monkeypatch)

    assert _reach(
        {"scenario": OUTSIDE}, None, True, ALPHA_CODE, LISTED, NEVER_PLAYED
    ) == (None, OUTSIDE)
    assert _reach({}, None, True, ALPHA_CODE, LISTED, NEVER_PLAYED) == (
        no_update,
        no_update,
    )


def test_a_page_load_that_names_every_input_still_applies_the_link(monkeypatch, played):
    """A Pages mount can report every input as a trigger, each with what it holds."""
    triggered = [
        {"prop_id": DEEP_LINK, "value": {"scenario": OUTSIDE}},
        {"prop_id": RUN_EVENTS, "value": None},
        {"prop_id": LIST_ASKED, "value": None},
        {"prop_id": GO, "value": None},
        {"prop_id": FOLLOW, "value": True},
    ]
    monkeypatch.setattr(scenario_selection, "ctx", SimpleNamespace(triggered=triggered))

    assert _reach({"scenario": OUTSIDE}, None, True, ALPHA_CODE, LISTED) == (
        None,
        OUTSIDE,
    )


@pytest.mark.parametrize(
    ("asked", "held_filter", "selected", "expected"),
    [
        # The filter does not list the scenario pressed: it is cleared.
        (OUTSIDE, ALPHA_CODE, LISTED, (None, OUTSIDE)),
        # It lists it, or there is no filter: only the scenario moves.
        (LISTED, ALPHA_CODE, OUTSIDE, (no_update, LISTED)),
        (OUTSIDE, None, LISTED, (no_update, OUTSIDE)),
        (OUTSIDE, "KovaaKsGoneCode", LISTED, (no_update, OUTSIDE)),
        (OUTSIDE, ALPHA_CODE, None, (None, OUTSIDE)),
        # A press on the selected scenario's own name changes nothing.
        (LISTED, ALPHA_CODE, LISTED, (no_update, no_update)),
    ],
)
def test_a_name_pressed_in_the_list_selects_it_and_clears_a_filter_in_its_way(
    monkeypatch, played, asked, held_filter, selected, expected
):
    """The third way in to the rule a link and a run follow."""
    _called_by(monkeypatch, LIST_ASKED)

    assert _reach({}, None, True, held_filter, selected, asked) == expected


def test_a_list_store_that_holds_no_name_is_not_a_press(monkeypatch, played):
    """The store is in the layout from the start, with no value."""
    _called_by(monkeypatch, LIST_ASKED, value=None)

    assert _reach({}, None, True, ALPHA_CODE, LISTED, None) == (
        no_update,
        no_update,
    )


@pytest.mark.parametrize("follow_newly_played", [True, False])
def test_a_press_is_answered_and_not_the_run_summary_still_in_its_store(
    monkeypatch, played, follow_newly_played
):
    """The summary store replays its last batch to every later call.

    Read from the values, a press made after a run landed would be taken for
    that run: with Follow on the page would go back to the scenario last
    played, and with Follow off the press would do nothing.
    """
    _called_by(monkeypatch, LIST_ASKED)

    assert _reach(
        {"scenario": LISTED},
        _landed_on(LISTED),
        follow_newly_played,
        ALPHA_CODE,
        LISTED,
        OUTSIDE,
    ) == (None, OUTSIDE)


# --- While the scenario note has unsaved changes ----------------------------------


def test_unsaved_changes_are_a_text_other_than_the_one_the_editor_opened_with():
    has = scenario_selection.has_unsaved_changes

    assert has(EDITING_LISTED, UNSAVED)
    assert not has(EDITING_LISTED, "aim lower")
    assert not has(None, UNSAVED)
    assert not has(EDITING_LISTED, None)


def test_a_run_with_unsaved_changes_waits_and_moves_nothing(monkeypatch, played):
    """The run's scenario is the one the page will move to."""
    _called_by(monkeypatch, RUN_EVENTS)

    assert _reach_all(
        {},
        _landed_on(OUTSIDE),
        True,
        ALPHA_CODE,
        LISTED,
        editor=EDITING_LISTED,
        draft=UNSAVED,
    ) == (no_update, no_update, OUTSIDE, no_update)


def test_a_newer_run_replaces_the_one_that_waits(monkeypatch, played):
    _called_by(monkeypatch, RUN_EVENTS)

    assert _reach_all(
        {},
        _landed_on(NEVER_PLAYED),
        True,
        ALPHA_CODE,
        LISTED,
        editor=EDITING_LISTED,
        draft=UNSAVED,
        waiting=OUTSIDE,
    ) == (no_update, no_update, NEVER_PLAYED, no_update)
    # The same scenario again writes nothing.
    assert _reach_all(
        {},
        _landed_on(OUTSIDE),
        True,
        ALPHA_CODE,
        LISTED,
        editor=EDITING_LISTED,
        draft=UNSAVED,
        waiting=OUTSIDE,
    ) == (no_update, no_update, no_update, no_update)


def test_a_run_on_the_edited_scenario_ends_the_wait(monkeypatch, played):
    """Against the edited scenario, which a pick held behind the dialog has left."""
    _called_by(monkeypatch, RUN_EVENTS)

    assert _reach_all(
        {},
        _landed_on(LISTED),
        True,
        ALPHA_CODE,
        OUTSIDE,
        editor=EDITING_LISTED,
        draft=UNSAVED,
        waiting=OUTSIDE,
    ) == (no_update, no_update, None, no_update)


def test_with_follow_off_a_run_with_unsaved_changes_asks_for_nothing(
    monkeypatch, played
):
    _called_by(monkeypatch, RUN_EVENTS)

    assert _reach_all(
        {},
        _landed_on(OUTSIDE),
        False,
        ALPHA_CODE,
        LISTED,
        editor=EDITING_LISTED,
        draft=UNSAVED,
    ) == (no_update, no_update, no_update, no_update)


def test_a_run_with_no_unsaved_changes_moves_the_page_as_before(monkeypatch, played):
    """An editor open on its own text is no reason to wait."""
    _called_by(monkeypatch, RUN_EVENTS)

    assert _reach_all(
        {},
        _landed_on(OUTSIDE),
        True,
        ALPHA_CODE,
        LISTED,
        editor=EDITING_LISTED,
        draft="aim lower",
    ) == (None, OUTSIDE, no_update, no_update)
    # A wait left over from a moment ago ends with the move.
    assert _reach_all(
        {},
        _landed_on(OUTSIDE),
        True,
        ALPHA_CODE,
        LISTED,
        editor=EDITING_LISTED,
        draft="aim lower",
        waiting=NEVER_PLAYED,
    ) == (None, OUTSIDE, None, no_update)


def test_turning_follow_off_ends_the_wait_and_turning_it_on_brings_none_back(
    monkeypatch, played
):
    """A flip of the switch never follows the summary the store still holds."""
    _called_by(monkeypatch, FOLLOW)

    assert _reach_all(
        {},
        _landed_on(OUTSIDE),
        False,
        ALPHA_CODE,
        LISTED,
        editor=EDITING_LISTED,
        draft=UNSAVED,
        waiting=OUTSIDE,
    ) == (no_update, no_update, None, no_update)
    assert _reach_all(
        {},
        _landed_on(OUTSIDE),
        True,
        ALPHA_CODE,
        LISTED,
        editor=EDITING_LISTED,
        draft=UNSAVED,
    ) == (no_update, no_update, no_update, no_update)
    # With nothing waiting, off writes nothing either.
    assert _reach_all({}, _landed_on(OUTSIDE), False, ALPHA_CODE, LISTED) == (
        no_update,
        no_update,
        no_update,
        no_update,
    )


def test_a_press_with_unsaved_changes_is_held_for_the_note_card(monkeypatch, played):
    _called_by(monkeypatch, LIST_ASKED)

    assert _reach_all(
        {},
        None,
        True,
        ALPHA_CODE,
        LISTED,
        OUTSIDE,
        editor=EDITING_LISTED,
        draft=UNSAVED,
    ) == (no_update, no_update, no_update, {"to": OUTSIDE})
    # A press on the edited scenario's own name is no change, as before.
    assert _reach_all(
        {},
        None,
        True,
        ALPHA_CODE,
        LISTED,
        LISTED,
        editor=EDITING_LISTED,
        draft=UNSAVED,
    ) == (no_update, no_update, no_update, no_update)


@pytest.mark.parametrize("answer", ["Save", "Cancel", "undoing every change"])
def test_each_answer_that_ends_the_wait_releases_it_once(monkeypatch, played, answer):
    """Save, Cancel and undoing each send ``release``, and a second finds nothing.

    The run's scenario is selected as Follow would have, clearing a filter
    that doesn't list it, and the wait ends.
    """
    _called_by(monkeypatch, GO)

    assert _reach_all(
        {},
        _landed_on(OUTSIDE),
        True,
        ALPHA_CODE,
        LISTED,
        request={"release": True},
        waiting=OUTSIDE,
    ) == (None, OUTSIDE, None, no_update)
    assert _reach_all(
        {},
        _landed_on(OUTSIDE),
        True,
        None,
        OUTSIDE,
        request={"release": True},
    ) == (no_update, no_update, no_update, no_update)


def test_a_release_moves_although_the_editor_store_still_holds_the_text(
    monkeypatch, played
):
    """The card sends a request only once its answer is final.

    It writes the request and closes the editor in one step, so the editor
    store can still hold the text when the request arrives.
    """
    _called_by(monkeypatch, GO)

    assert _reach_all(
        {},
        None,
        True,
        ALPHA_CODE,
        LISTED,
        request={"release": True},
        waiting=OUTSIDE,
        editor=EDITING_LISTED,
        draft=UNSAVED,
    ) == (None, OUTSIDE, None, no_update)


def test_a_dialog_answer_selects_where_the_player_asked_and_drops_the_wait(
    monkeypatch, played
):
    """Discard or Save after a name in the list or a toast's link."""
    _called_by(monkeypatch, GO)

    assert _reach_all(
        {},
        None,
        True,
        ALPHA_CODE,
        LISTED,
        request={"select": OUTSIDE},
        waiting=NEVER_PLAYED,
    ) == (None, OUTSIDE, None, no_update)
    assert _reach_all(
        {}, None, True, ALPHA_CODE, OUTSIDE, request={"select": LISTED}
    ) == (
        no_update,
        LISTED,
        no_update,
        no_update,
    )


def test_keep_editing_puts_the_old_values_back_and_the_run_keeps_waiting(
    monkeypatch, played
):
    """After a pick, or a filter change that dropped the edited scenario."""
    _called_by(monkeypatch, GO)
    restore = {"restore": {"scenario": LISTED, "playlist": ALPHA_CODE}}

    assert _reach_all(
        {},
        None,
        True,
        ALPHA_CODE,
        OUTSIDE,
        request=restore,
        waiting=NEVER_PLAYED,
    ) == (no_update, LISTED, no_update, no_update)
    assert _reach_all({}, None, True, BETA_CODE, None, request=restore) == (
        ALPHA_CODE,
        LISTED,
        no_update,
        no_update,
    )


def test_a_dialog_answer_after_a_pick_only_drops_the_wait(monkeypatch, played):
    """The dropdown already holds where the player asked to go."""
    _called_by(monkeypatch, GO)

    assert _reach_all(
        {},
        None,
        True,
        ALPHA_CODE,
        OUTSIDE,
        request={"drop": True},
        waiting=NEVER_PLAYED,
    ) == (no_update, no_update, None, no_update)


def test_a_run_while_the_dialog_is_open_leaves_its_destination(monkeypatch, played):
    """The dialog's destination is the card's to keep: a run only waits.

    A pick of OUTSIDE is held behind the dialog, so the dropdown holds
    OUTSIDE while the note is LISTED's. A run on NEVER_PLAYED waits, and
    neither dropdown moves.
    """
    _called_by(monkeypatch, RUN_EVENTS)

    assert _reach_all(
        {},
        _landed_on(NEVER_PLAYED),
        True,
        ALPHA_CODE,
        OUTSIDE,
        editor=EDITING_LISTED,
        draft=UNSAVED,
    ) == (no_update, no_update, NEVER_PLAYED, no_update)


def test_the_clearing_registration_adds_callbacks_for_its_own_ids_only(
    restored_callbacks,
):
    registered_before = list(GLOBAL_CALLBACK_LIST)

    scenario_selection.register_scenario_selection_clearing_filter(
        SECOND_PAGE_IDS,
        run_events="second-run_events",
        follow_switch="second-follow_switch",
        run_landed="second-run_landed",
        scenario_asked="second-scenario_asked",
        note=scenario_selection.NoteSelectionIds(
            go="second-note_go",
            editor="second-note_editor",
            draft="second-note_draft",
            waiting="second-note_waiting",
            held="second-note_held",
        ),
    )

    assert GLOBAL_CALLBACK_LIST[: len(registered_before)] == registered_before
    select_playlist, reach_scenario = GLOBAL_CALLBACK_LIST[len(registered_before) :]
    assert _answering(select_playlist) == "select_playlist"
    assert _answering(reach_scenario) == "reach_scenario_or_the_one_asked_for"
    # Plain outputs, all: a callback is held back for a plain output and not
    # for a duplicate one, and the scenario list must wait for the filter.
    # The wait and the held name are this callback's alone.
    assert reach_scenario["output"] == (
        "..second-playlist_filter.value...second-scenario_dropdown.value"
        "...second-note_waiting.data...second-note_held.data.."
    )
    assert _input_keys(reach_scenario) == {
        "second-deep_link.data",
        "second-run_events.data",
        "second-scenario_asked.data",
        "second-note_go.data",
        "second-follow_switch.checked",
    }
    assert [f"{dep['id']}.{dep['property']}" for dep in reach_scenario["state"]] == [
        "second-playlist_filter.value",
        "second-scenario_dropdown.value",
        "second-note_editor.data",
        "second-note_draft.value",
        "second-note_waiting.data",
    ]
    assert reach_scenario["prevent_initial_call"] is False
    # The scenario list keeps the Input nothing writes. Without the store,
    # every Input of ``select_playlist`` would be something ``reach_scenario``
    # writes only on some visits, and the list would go unwritten on the rest.
    assert not _input_keys(select_playlist) <= _output_keys(reach_scenario)
    # It also takes the store written for every batch, so a scenario whose
    # first run has just landed joins the list. Not the summary, which is
    # written only for a batch the page shows: with Follow off the scenario
    # would stay out of the list. The filter's value is ``reach_scenario``'s
    # plain output, which is what makes Dash hold the list for the selection.
    assert _input_keys(select_playlist) == {
        "second-playlist_filter.value",
        "second-deep_link.data",
        "second-run_landed.data",
    }


def test_a_landed_run_has_the_local_list_read_again(monkeypatch, playlist_lists):
    """The first run of a scenario adds it to the list a page drew before it.

    With no filter to clear, nothing else writes the list, and the dropdown
    would go on showing the old name for a scenario it cannot name.
    """
    drawn_with = scenario_selection.select_playlist(None, None, None)
    monkeypatch.setattr(
        scenario_selection, "get_scenario_names", lambda: ["All", "Just Played"]
    )

    scenarios, link, options = scenario_selection.select_playlist(
        None, None, "just-played.csv"
    )

    assert drawn_with[0] == ["All"]
    assert scenarios == ["All", "Just Played"]
    assert (link, options) == (None, VISIBLE_PLAYLISTS)


def test_a_landed_run_leaves_a_playlists_list_as_it_is(playlist_lists):
    """A filter that stays lists its playlist's scenarios, run or no run."""
    assert scenario_selection.select_playlist("KovaaKsAlpha", None, "landed.csv")[
        0
    ] == ["KovaaKsAlpha Scenario"]
