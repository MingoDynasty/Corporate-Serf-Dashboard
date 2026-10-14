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
            f"{run_history.LATEST_RUN_CARD_IDS.scenario_button}.n_clicks",
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


BUTTON_CLICKED = "page-scenario-button.n_clicks"


@pytest.mark.parametrize(
    ("asked", "held_filter", "selected", "expected"),
    [
        # The filter does not list the scenario asked for: it is cleared.
        (OUTSIDE, ALPHA_CODE, LISTED, (None, OUTSIDE)),
        # It lists it, or there is no filter: only the scenario moves.
        (LISTED, ALPHA_CODE, OUTSIDE, (no_update, LISTED)),
        (OUTSIDE, None, LISTED, (no_update, OUTSIDE)),
        (OUTSIDE, "KovaaKsGoneCode", LISTED, (no_update, OUTSIDE)),
        (OUTSIDE, ALPHA_CODE, None, (None, OUTSIDE)),
        # Already selected, or the button names nothing: nothing to write.
        (LISTED, ALPHA_CODE, LISTED, (no_update, no_update)),
        (None, ALPHA_CODE, LISTED, (no_update, no_update)),
        ("", ALPHA_CODE, LISTED, (no_update, no_update)),
    ],
)
def test_the_scenario_button_selects_its_scenario_and_clears_a_filter_in_its_way(
    monkeypatch, played, asked, held_filter, selected, expected
):
    _called_by(monkeypatch, BUTTON_CLICKED)

    assert (
        scenario_selection.reach_scenario_or_the_one_asked_for(
            {}, None, 1, True, held_filter, selected, asked
        )
        == expected
    )


@pytest.mark.parametrize("follow_newly_played", [True, False])
def test_a_click_is_answered_and_not_the_run_summary_still_in_its_store(
    monkeypatch, played, follow_newly_played
):
    """The summary store replays its last batch to every later call.

    Read from the values, a click made after a run landed would be taken for
    that run: with Follow on the page would go back to the scenario last
    played, and with Follow off the click would do nothing.
    """
    _called_by(monkeypatch, BUTTON_CLICKED)

    assert scenario_selection.reach_scenario_or_the_one_asked_for(
        {"scenario": LISTED},
        _landed_on(LISTED),
        1,
        follow_newly_played,
        ALPHA_CODE,
        LISTED,
        OUTSIDE,
    ) == (None, OUTSIDE)


def test_a_run_that_lands_after_a_click_is_followed_as_before(monkeypatch, played):
    """The button's count stays above zero, and is not what called."""
    _called_by(monkeypatch, "page-run-events.data")

    assert scenario_selection.reach_scenario_or_the_one_asked_for(
        {}, _landed_on(OUTSIDE), 3, True, ALPHA_CODE, LISTED, NEVER_PLAYED
    ) == (None, OUTSIDE)
    assert scenario_selection.reach_scenario_or_the_one_asked_for(
        {}, _landed_on(OUTSIDE), 3, False, ALPHA_CODE, LISTED, NEVER_PLAYED
    ) == (no_update, no_update)


def test_the_page_load_applies_the_link_and_not_a_button_nobody_clicked(
    monkeypatch, played
):
    _called_by(monkeypatch)

    assert scenario_selection.reach_scenario_or_the_one_asked_for(
        {"scenario": OUTSIDE}, None, 0, True, ALPHA_CODE, LISTED, NEVER_PLAYED
    ) == (None, OUTSIDE)
    assert scenario_selection.reach_scenario_or_the_one_asked_for(
        {}, None, 0, True, ALPHA_CODE, LISTED, NEVER_PLAYED
    ) == (no_update, no_update)


def test_a_button_that_reports_no_clicks_is_not_a_click(monkeypatch, played):
    """A button just drawn calls with a count of nothing."""
    _called_by(monkeypatch, BUTTON_CLICKED, value=0)

    assert scenario_selection.reach_scenario_or_the_one_asked_for(
        {}, None, 0, True, ALPHA_CODE, LISTED, OUTSIDE
    ) == (no_update, no_update)


def test_the_clearing_registration_adds_callbacks_for_its_own_ids_only(
    restored_callbacks,
):
    registered_before = list(GLOBAL_CALLBACK_LIST)

    scenario_selection.register_scenario_selection_clearing_filter(
        SECOND_PAGE_IDS,
        run_events="second-run_events",
        follow_switch="second-follow_switch",
        run_landed="second-run_landed",
        scenario_button="second-scenario_button",
    )

    assert GLOBAL_CALLBACK_LIST[: len(registered_before)] == registered_before
    select_playlist, reach_scenario = GLOBAL_CALLBACK_LIST[len(registered_before) :]
    assert _answering(select_playlist) == "select_playlist"
    assert _answering(reach_scenario) == "reach_scenario_or_the_one_asked_for"
    # Plain outputs, both: a callback is held back for a plain output and not
    # for a duplicate one, and the scenario list must wait for the filter.
    assert reach_scenario["output"] == (
        "..second-playlist_filter.value...second-scenario_dropdown.value.."
    )
    assert _input_keys(reach_scenario) == {
        "second-deep_link.data",
        "second-run_events.data",
        "second-scenario_button.n_clicks",
    }
    assert [f"{dep['id']}.{dep['property']}" for dep in reach_scenario["state"]] == [
        "second-follow_switch.checked",
        "second-playlist_filter.value",
        "second-scenario_dropdown.value",
        "second-scenario_button.value",
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
