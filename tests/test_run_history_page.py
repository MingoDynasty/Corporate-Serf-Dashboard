"""The Run History page: where it is served, what its layout holds, and its callbacks.

The page is built beside the Scenario Performance page and hidden until it
replaces it, so these tests also hold what keeps the two apart: an address
with no link to it, and an id of its own for everything it draws. What the
chart plots is ``tests/test_run_history_chart.py``, and the rule for a
scenario the playlist filter does not list is ``tests/test_scenario_selection.py``.
"""

import json
import re
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import dash
import dash_mantine_components as dmc
import plotly.graph_objects as go
import pytest
from dash import dcc, no_update
from dash._callback import GLOBAL_CALLBACK_LIST, GLOBAL_CALLBACK_MAP

dash.Dash(__name__, use_pages=True, pages_folder="")

from source import app_shell  # noqa: E402
from source.components import (  # noqa: E402
    chart_options,
    run_history_chart,
    scenario_selection,
    setup_surfaces,
)
from source.config import settings_service  # noqa: E402
from source.pages import home, run_history  # noqa: E402
from source.utilities.notifications import TOAST_CHANNEL_REGISTRY_STORE_ID  # noqa: E402
from tests.rendered_text import rendered_text  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
STYLESHEET = REPO_ROOT / "assets" / "stylesheet.css"
SOURCE_ROOT = REPO_ROOT / "source"
SCENARIO = "Scenario A"
STATS_DIR_KEY = settings_service.STATS_DIR_KEY
USERNAME_KEY = settings_service.KOVAAKS_USERNAME_KEY


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


def _by_id(page, component_id):
    return next(
        (
            component
            for component in _walk_components(page)
            if getattr(component, "id", None) == component_id
        ),
        None,
    )


def _by_class(page, class_name):
    return next(
        component
        for component in _walk_components(page)
        if getattr(component, "className", None) == class_name
    )


def _ids(page) -> set[str]:
    return {
        component.id
        for component in _walk_components(page)
        if isinstance(getattr(component, "id", None), str)
    }


@pytest.fixture(autouse=True)
def quiet_lists(monkeypatch):
    """Keep the playlist and scenario stores out of the way of the layout."""
    monkeypatch.setattr(
        scenario_selection, "get_visible_playlist_selector_options", lambda: []
    )
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: ["All"])


# --- Where the page is, and that nothing leads to it ---------------------------


def test_the_page_is_registered_at_its_final_address_under_its_name():
    page = dash.page_registry["source.pages.run_history"]

    assert page["path"] == "/run-history"
    assert page["name"] == "Run History"


def test_the_hidden_page_has_no_navbar_entry():
    links = [
        (component.label, component.href)
        for component in _walk_components(app_shell.layout())
        if isinstance(component, dmc.NavLink)
    ]

    assert "/run-history" not in [href for _label, href in links]
    assert "Run History" not in [label for label, _href in links]


def test_nothing_in_the_app_links_to_the_hidden_page():
    """Its address appears in one place: the line that registers it."""
    mentions = {
        path.relative_to(SOURCE_ROOT).as_posix(): path.read_text(
            encoding="utf-8"
        ).count("/run-history")
        for path in sorted(SOURCE_ROOT.rglob("*.py"))
        if "/run-history" in path.read_text(encoding="utf-8")
    }

    assert mentions == {"pages/run_history.py": 1}


def test_the_old_page_still_owns_the_landing_address():
    page = dash.page_registry["source.pages.home"]

    assert (page["path"], page["name"]) == ("/", "Scenario Performance")


def test_the_page_never_imports_the_old_pages_module():
    """Dash Pages loads a page file as ``pages.<name>``.

    A second import path would make a second copy of the module, with its own
    state and its own callback registrations.
    """
    source = (SOURCE_ROOT / "pages" / "run_history.py").read_text(encoding="utf-8")

    assert not re.search(r"^\s*(from|import)\s+source\.pages\.home\b", source, re.M)
    assert not re.search(
        r"^\s*from\s+source\.pages\s+import\s+.*\bhome\b", source, re.M
    )


# --- Ids -----------------------------------------------------------------------


def test_every_id_the_page_draws_is_its_own():
    """Two pages cannot share part of a callback, so they share no id."""
    shared = _ids(run_history.layout()) & _ids(home.layout())

    assert shared == set()


def test_the_layout_builds_every_id_the_blocks_are_registered_for():
    mounted = _ids(run_history.layout())

    assert set(run_history.SCENARIO_SELECTION_IDS) <= mounted
    assert set(run_history.CHART_OPTIONS_IDS) <= mounted
    assert set(run_history.SCENARIO_STATS_IDS) <= mounted
    assert {
        run_history.RUN_EVENTS_STORE_ID,
        run_history.POLLING_INTERVAL_ID,
        run_history.RELATIVE_TIME_INTERVAL_ID,
        run_history.STARTUP_PLAYLIST_WARNING_INTERVAL_ID,
        run_history.TODAY_STORE_ID,
        run_history.FOLLOW_SWITCH_ID,
        run_history.CHART_MODE_ID,
        run_history.RUN_RANGE_ID,
        run_history.DAY_RANGE_ID,
        run_history.RUN_RANGE_FIELD_ID,
        run_history.DAY_RANGE_FIELD_ID,
        run_history.SETUP_CARD_ID,
        run_history.RUN_LANDED_STORE_ID,
        run_history.SESSION_IN_PROGRESS_STORE_ID,
    } <= mounted
    # The Columns menu's own id is part of its checkboxes' ids and is no
    # component's id by itself.
    list_ids = run_history.RUN_LIST_IDS._asdict()
    menu_id = list_ids.pop("columns_menu")
    assert set(list_ids.values()) <= mounted
    assert {f"{menu_id}-button", f"{menu_id}-sink"} <= mounted


def test_the_ids_are_the_ones_browsers_store_values_under():
    """A remembered value is stored under its control's id.

    Renaming one resets it for every user, so each is spelled out here.
    """
    assert run_history.SCENARIO_SELECTION_IDS._asdict() == {
        "playlist_filter": "run-history-playlist-filter",
        "scenario_dropdown": "run-history-scenario",
        "deep_link": "run-history-deep-link",
        "playlist_table_link": "run-history-playlist-table-link",
    }
    assert (
        run_history.FOLLOW_SWITCH_ID,
        run_history.CHART_MODE_ID,
        run_history.RUN_RANGE_ID,
        run_history.DAY_RANGE_ID,
    ) == (
        "run-history-follow-switch",
        "run-history-chart-mode",
        "run-history-run-range",
        "run-history-day-range",
    )
    options = run_history.CHART_OPTIONS_IDS
    assert (
        options.rank_overlay,
        options.show_all_ranks,
        options.high_score_overlay,
        options.point_size,
        options.point_color,
        options.score_threshold_overlay,
        options.score_threshold_percentage,
        options.score_threshold_notification,
        options.run_notification,
    ) == (
        "run-history-rank-overlay-switch",
        "run-history-show-all-ranks-switch",
        "run-history-high-score-overlay-switch",
        "run-history-point-size",
        "run-history-point-color",
        "run-history-score-threshold-overlay-switch",
        "run-history-score-threshold-percentage",
        "run-history-score-threshold-notification-switch",
        "run-history-run-notification-switch",
    )


# --- The layout ----------------------------------------------------------------


def test_the_layout_takes_a_query_parameter_it_does_not_name():
    """A link may carry one only to make its address differ from the last."""
    page = run_history.layout(scenario=SCENARIO, run="2026.10.12-10.50.00")

    assert _by_id(page, run_history.SCENARIO_SELECTION_IDS.deep_link).data == {
        "scenario": SCENARIO
    }


def test_the_top_row_holds_the_dropdowns_the_stats_and_the_cards_slot():
    row = _by_class(run_history.layout(), "run-history-top-row")

    assert [getattr(child, "className", None) for child in row.children] == [
        "run-history-playlist-field",
        "run-history-scenario-field",
        None,
        "run-history-card-slot",
    ]
    playlist_field, scenario_field, stats, card_slot = row.children
    assert [getattr(child, "id", None) for child in playlist_field.children] == [
        run_history.SCENARIO_SELECTION_IDS.playlist_filter,
        run_history.SCENARIO_SELECTION_IDS.playlist_table_link,
    ]
    assert [getattr(child, "id", None) for child in scenario_field.children] == [
        run_history.SCENARIO_SELECTION_IDS.scenario_dropdown,
        run_history.FOLLOW_SWITCH_ID,
    ]
    assert run_history.SCENARIO_STATS_IDS.rank in _ids(stats)
    # Reserved for the latest-run card, and empty until it ships.
    assert getattr(card_slot, "children", None) is None


def test_the_chart_sits_left_of_the_run_list():
    columns = _by_class(run_history.layout(), "run-history-columns")

    chart_column, list_column = columns.children
    assert chart_column.className == "run-history-chart-column"
    assert list_column.className == "run-history-list-column"
    assert list_column.children.id == run_history.RUN_LIST_IDS.panel


def test_the_charts_header_holds_the_mode_both_ranges_and_the_options_button():
    header = _by_class(run_history.layout(), "run-history-chart-header")

    assert [getattr(child, "id", None) for child in header.children] == [
        run_history.CHART_MODE_ID,
        run_history.RUN_RANGE_FIELD_ID,
        run_history.DAY_RANGE_FIELD_ID,
        run_history.CHART_OPTIONS_IDS.toggle,
    ]


def test_chart_options_opens_between_the_chart_and_the_list():
    """The panel is the graph's neighbor in the chart's own row."""
    area = _by_class(run_history.layout(), "run-history-chart-area")

    row = area.children
    assert row.className == "home-chart-row"
    assert [getattr(child, "id", None) for child in row.children] == [
        run_history.CHART_OPTIONS_IDS.graph,
        run_history.CHART_OPTIONS_IDS.panel,
    ]
    assert chart_options.CHART_OPTIONS_PANEL_HIDDEN_CLASS in row.children[1].className


def test_the_graph_carries_the_class_both_graph_scripts_find_it_by():
    graph = _by_id(run_history.layout(), run_history.CHART_OPTIONS_IDS.graph)

    assert isinstance(graph, dcc.Graph)
    assert graph.className == "home-graph"
    assert graph.responsive is True
    for script in ("homeGraphResize.js", "homeGraphZoomFit.js"):
        assert ".home-graph" in (REPO_ROOT / "assets" / script).read_text(
            encoding="utf-8"
        )


def test_the_chart_starts_as_the_neutral_placeholder():
    page = run_history.layout()

    cached = json.loads(_by_id(page, run_history.CHART_OPTIONS_IDS.cached_plot).data)
    assert cached["layout"]["xaxis"]["visible"] is False
    assert "annotations" not in cached["layout"]


def test_the_page_has_no_top_n_control_and_no_date_picker():
    components = list(_walk_components(run_history.layout()))

    assert not [c for c in components if isinstance(c, dmc.DatePickerInput)]
    number_inputs = [c for c in components if isinstance(c, dmc.NumberInput)]
    assert [c.id for c in number_inputs] == [
        run_history.CHART_OPTIONS_IDS.score_threshold_percentage
    ]
    assert "Top N scores" not in rendered_text(run_history.layout())
    assert "Oldest date to consider" not in rendered_text(run_history.layout())


# --- Remembered controls --------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [{}, {"scenario": SCENARIO, "playlist_code": "KovaaKsTestCode"}],
    ids=["plain", "deep_linked"],
)
def test_a_remembered_controls_layout_default_never_varies(query):
    """Dash discards a stored value when a later visit draws another default.

    So the query parameters never reach a control's layout value. They reach
    the deep-link store, and a callback applies them.
    """
    page = run_history.layout(**query)

    defaults = {
        run_history.SCENARIO_SELECTION_IDS.playlist_filter: ("value", None),
        run_history.SCENARIO_SELECTION_IDS.scenario_dropdown: ("value", None),
        run_history.FOLLOW_SWITCH_ID: ("checked", True),
        run_history.CHART_MODE_ID: ("value", "score_vs_run"),
        run_history.RUN_RANGE_ID: ("value", "100"),
        run_history.DAY_RANGE_ID: ("value", "90"),
        run_history.CHART_OPTIONS_IDS.score_threshold_percentage: ("value", 95),
        run_history.CHART_OPTIONS_IDS.run_notification: ("checked", True),
    }
    for component_id, (prop, default) in defaults.items():
        component = _by_id(page, component_id)
        assert getattr(component, prop) == default, component_id
        assert component.persistence is True, component_id


def test_both_range_selects_are_always_in_the_layout_and_one_is_hidden():
    """Hidden, never removed: a control out of the layout is no callback input."""
    page = run_history.layout()

    run_field = _by_id(page, run_history.RUN_RANGE_FIELD_ID)
    day_field = _by_id(page, run_history.DAY_RANGE_FIELD_ID)
    assert run_field.children.id == run_history.RUN_RANGE_ID
    assert day_field.children.id == run_history.DAY_RANGE_ID
    # The chart opens on Score vs Run, whose range is in runs.
    assert run_field.className == "run-history-range-field"
    assert day_field.className == (
        "run-history-range-field run-history-range-field-hidden"
    )
    css = STYLESHEET.read_text(encoding="utf-8")
    assert re.search(r"\.run-history-range-field-hidden \{\s*display: none;\s*\}", css)


def test_the_mode_decides_which_range_select_shows():
    (registration,) = [
        entry
        for entry in GLOBAL_CALLBACK_LIST
        if f"{run_history.RUN_RANGE_FIELD_ID}.className" in entry["output"]
    ]

    assert {f"{dep['id']}.{dep['property']}" for dep in registration["inputs"]} == {
        f"{run_history.CHART_MODE_ID}.value"
    }
    assert f"{run_history.DAY_RANGE_FIELD_ID}.className" in registration["output"]
    script = run_history._SHOW_RANGE_FOR_MODE_SCRIPT
    assert 'mode === "score_vs_run"' in script
    assert '"run-history-range-field run-history-range-field-hidden"' in script


# --- Copy ------------------------------------------------------------------------


def test_the_mode_and_ranges_take_their_names_from_aria_labels():
    page = run_history.layout()

    def aria_label(component_id):
        return _by_id(page, component_id).to_plotly_json()["props"]["aria-label"]

    assert aria_label(run_history.CHART_MODE_ID) == "Chart mode"
    assert aria_label(run_history.RUN_RANGE_ID) == "Range"
    assert aria_label(run_history.DAY_RANGE_ID) == "Range"
    assert _by_id(page, run_history.CHART_MODE_ID).data == (
        run_history_chart.CHART_MODE_OPTIONS
    )


def test_the_follow_help_says_a_filter_in_the_way_is_cleared():
    switch = _by_id(run_history.layout(), run_history.FOLLOW_SWITCH_ID)

    (tooltip,) = [
        component
        for component in _walk_components(switch.label)
        if isinstance(component, dmc.Tooltip)
    ]
    assert rendered_text(switch.label).startswith("Follow newly played scenario")
    # The Copy block's sentence, with its marker for the bold control name.
    assert rendered_text(tooltip.label) == (
        "Automatically selects the scenario you just played when a new run is "
        "detected. If the **Playlist filter** doesn't list that scenario, the "
        "filter is cleared."
    )


def test_the_percentage_help_says_a_run_is_judged_whatever_judges_it():
    """On this page a toast is no longer the only thing that judges a run."""
    field = _by_id(
        run_history.layout(), run_history.CHART_OPTIONS_IDS.score_threshold_percentage
    )

    (tooltip,) = [
        component
        for component in _walk_components(field.label)
        if isinstance(component, dmc.Tooltip)
    ]
    assert tooltip.label.endswith(
        "The overlay line tracks your current personal best. A run is judged "
        "against the personal best you had before the run."
    )
    assert "Notifications judge" not in tooltip.label


def test_the_old_page_keeps_its_own_two_help_texts():
    page = home.layout()

    follow = _by_id(page, "automatically-change-scenario-switch")
    percentage = _by_id(page, home.CHART_OPTIONS_IDS.score_threshold_percentage)
    assert "filter is cleared" not in rendered_text(follow.label)
    (tooltip,) = [
        component
        for component in _walk_components(percentage.label)
        if isinstance(component, dmc.Tooltip)
    ]
    assert tooltip.label.endswith(
        "Notifications judge a run against the personal best you had before the run."
    )


# --- The setup surfaces ------------------------------------------------------------


def _store(**values):
    """Save exactly these keys and pin the directory the way startup would."""
    settings_service.save_settings(values)
    settings_service.resolve_stats_dir()


def _card(page):
    container = _by_id(page, run_history.SETUP_CARD_ID)
    assert container is not None, "the card's container is always in the layout"
    return container.children[0] if container.children else None


def _card_texts(card) -> list[str]:
    return [
        child.children
        for child in _walk_components(card)
        if isinstance(child, dmc.Text)
    ]


def test_with_no_stats_folder_ever_set_the_page_says_to_finish_setting_up():
    _store()

    card = _card(run_history.layout())

    assert _card_texts(card) == [
        setup_surfaces.SETUP_CARD_STATS_DIR_TITLE,
        setup_surfaces.SETUP_CARD_STATS_DIR_BODY,
    ]
    assert card.className == setup_surfaces.SETUP_CARD_CAUTION_CLASS


def test_with_a_settings_file_it_cannot_read_the_page_says_so():
    settings_service.SETTINGS_FILE_PATH.write_text(
        json.dumps({"kovaaks_username": "MingoDynasty"}), encoding="utf-8"
    )
    settings_service.clear_settings_cache()
    settings_service.resolve_stats_dir()

    card = _card(run_history.layout())

    assert _card_texts(card) == [
        setup_surfaces.SETUP_CARD_STORE_TITLE,
        setup_surfaces.SETUP_CARD_STORE_BODY,
    ]
    assert card.className == setup_surfaces.SETUP_CARD_CAUTION_CLASS


def test_the_page_never_offers_the_account_or_skip():
    """The blue offer is the landing page's: it explains nothing about an empty chart."""
    _store(
        **{STATS_DIR_KEY: str(Path(__file__).resolve().parent / "fixtures" / "stats")}
    )

    page = run_history.layout()

    assert _card(page) is None
    # The same state draws the offer on the page the launcher opens.
    home_card = _by_id(home.layout(), home.SETUP_CARD_ID).children
    assert setup_surfaces.SETUP_CARD_IDENTITY_TITLE in _card_texts(home_card[0])


@pytest.mark.parametrize(
    "arrange",
    [
        _store,
        lambda: _store(**{STATS_DIR_KEY: ""}),
        lambda: _store(**{STATS_DIR_KEY: "no-such-stats-dir", USERNAME_KEY: ""}),
    ],
    ids=["nothing_asked", "folder_emptied", "folder_vanished"],
)
def test_no_state_of_the_page_draws_a_skip_button(arrange):
    arrange()

    page = run_history.layout()

    assert _by_id(page, setup_surfaces.SETUP_CARD_SKIP_ID) is None
    assert not [
        component
        for component in _walk_components(_by_id(page, run_history.SETUP_CARD_ID))
        if isinstance(component, dmc.Button)
    ]


@pytest.mark.parametrize("stored", ["", "no-such-stats-dir"])
def test_a_stats_folder_that_is_set_and_unusable_gets_the_hint(stored):
    _store(**{STATS_DIR_KEY: stored, USERNAME_KEY: ""})

    page = run_history.layout()

    hint = _by_id(page, run_history.STATS_DIR_HINT_ID)
    assert hint is not None
    assert hint.className == setup_surfaces.STATS_DIR_HINT_CLASS
    assert rendered_text(hint) == "No stats folder configured. Set it in Settings."
    assert _card(page) is None
    # The hint and the card sit above the top row, hint first.
    order = [id(component) for component in _walk_components(page)]
    top_row = _by_class(page, "run-history-top-row")
    assert order.index(id(hint)) < order.index(id(top_row))


def test_a_saved_folder_awaiting_a_restart_gets_the_restart_hint_alone(tmp_path):
    _store()
    settings_service.save_settings({STATS_DIR_KEY: str(tmp_path)})

    page = run_history.layout()

    hint = _by_id(page, run_history.STATS_DIR_HINT_ID)
    assert rendered_text(hint) == "Restart the app to apply your saved settings."
    assert _card(page) is None


def test_a_configured_install_draws_neither_surface():
    page = run_history.layout()

    assert _by_id(page, run_history.STATS_DIR_HINT_ID) is None
    assert _card(page) is None


def test_the_hint_has_this_pages_id_and_never_the_old_pages():
    _store(**{STATS_DIR_KEY: ""})

    assert _by_id(run_history.layout(), home.STATS_DIR_HINT_ID) is None
    assert _by_id(home.layout(), run_history.STATS_DIR_HINT_ID) is None
    assert _by_id(home.layout(), home.STATS_DIR_HINT_ID) is not None


# --- Run delivery --------------------------------------------------------------------


def _run(scenario_name: str = SCENARIO, **fields):
    return {
        "run_id": "run-1.csv",
        "scenario_name": scenario_name,
        "sensitivity": "34.64 cm/360",
        "nth_score": 2,
        "score": 812.4,
        "scenario_previous_best": 800.0,
        "pace_constant": None,
        "is_new_sensitivity": False,
        "is_live": True,
        **fields,
    }


def _batch(*runs, celebrated_run_id=None):
    return {
        "runs": list(runs),
        "celebrated_run_id": celebrated_run_id,
        "animation_sequence": 0,
    }


def _payload(scenario_name: str = SCENARIO, **fields):
    return {"latest": _run(scenario_name, **fields), "celebrated_run_id": None}


def _registration(output_fragment: str) -> dict:
    (registration,) = [
        entry for entry in GLOBAL_CALLBACK_LIST if output_fragment in entry["output"]
    ]
    return registration


def _keys(dependencies) -> list[str]:
    return [f"{dep['id']}.{dep['property']}" for dep in dependencies]


def test_run_delivery_takes_the_shells_batch_and_writes_its_two_stores():
    """It writes neither dropdown: the selection callback moves them.

    The controls are State, and prevent_initial_call stays on, because the
    shell's store replays its last batch to a page that mounts.

    The summary and the newest run's id leave in one answer. Dash holds a
    callback back only for a writer that is already queued, so the run list,
    which is queued for the id, waits for the selection callback only when
    that one was queued for the summary at the same moment.
    """
    registration = _registration(f"{run_history.RUN_EVENTS_STORE_ID}.data")

    assert registration["output"] == (
        f"..{run_history.RUN_EVENTS_STORE_ID}.data"
        f"...{run_history.RUN_LANDED_STORE_ID}.data.."
    )
    assert _keys(registration["inputs"]) == ["run-events-batch.data"]
    assert set(_keys(registration["state"])) == {
        f"{run_history.FOLLOW_SWITCH_ID}.checked",
        f"{run_history.SCENARIO_SELECTION_IDS.scenario_dropdown}.value",
    }
    assert registration["prevent_initial_call"] is True


def test_run_delivery_forwards_nothing_without_a_batch():
    nothing = (no_update, no_update)

    assert run_history.forward_run_events(None, True, SCENARIO) == nothing
    assert run_history.forward_run_events(_batch(), True, SCENARIO) == nothing


def test_with_follow_on_the_summary_is_for_the_scenario_just_played():
    summary, run_landed = run_history.forward_run_events(
        _batch(_run(SCENARIO, run_id="a.csv"), _run("Scenario B", run_id="b.csv")),
        True,
        SCENARIO,
    )

    assert summary == {
        "latest": _run("Scenario B", run_id="b.csv"),
        "celebrated_run_id": None,
    }
    assert run_landed == "b.csv"


def test_with_follow_off_a_run_on_another_scenario_forwards_no_summary():
    """So the chart is not rebuilt for a run it does not plot.

    The run's id is still written. A session row counts every scenario's
    runs, so the run list is rebuilt for a run on any of them.
    """
    assert run_history.forward_run_events(
        _batch(_run("Scenario B", run_id="b.csv")), False, SCENARIO
    ) == (no_update, "b.csv")
    assert run_history.forward_run_events(
        _batch(_run(SCENARIO, run_id="a.csv"), _run("Scenario B", run_id="b.csv")),
        False,
        SCENARIO,
    ) == (
        {"latest": _run(SCENARIO, run_id="a.csv"), "celebrated_run_id": None},
        # The batch's newest run, whatever scenario the summary is for.
        "b.csv",
    )


def test_the_page_never_pops_the_run_event_queue():
    assert not hasattr(run_history, "message_queue")


# --- The selection, and the rule that keeps the first calls from starving --------------


def _selection_registration() -> dict:
    """Find the callback that writes both dropdowns' values for this page."""
    return _registration(f"{run_history.SCENARIO_SELECTION_IDS.playlist_filter}.value")


def _output_keys(registration: dict) -> set[str]:
    return {
        output.split("@")[0]
        for output in registration["output"].strip(".").split("...")
    }


def test_one_callback_writes_both_dropdowns_and_neither_write_is_a_duplicate():
    """Dash holds a callback back for a plain output and not for a duplicate one.

    With a duplicate writer the scenario list could be built for the filter
    as it was, land after the scenario was selected, and drop it.
    """
    registration = _selection_registration()
    ids = run_history.SCENARIO_SELECTION_IDS

    assert GLOBAL_CALLBACK_MAP[registration["output"]]["callback"].__name__ == (
        "reach_scenario"
    )
    assert registration["output"] == (
        f"..{ids.playlist_filter}.value...{ids.scenario_dropdown}.value.."
    )
    assert "@" not in registration["output"]
    assert _keys(registration["inputs"]) == [
        f"{ids.deep_link}.data",
        f"{run_history.RUN_EVENTS_STORE_ID}.data",
    ]
    assert _keys(registration["state"]) == [
        f"{run_history.FOLLOW_SWITCH_ID}.checked",
        f"{ids.playlist_filter}.value",
        f"{ids.scenario_dropdown}.value",
    ]
    # It applies this visit's query parameters, so the page load runs it.
    assert registration["prevent_initial_call"] is False
    writers = [
        entry["output"]
        for entry in GLOBAL_CALLBACK_LIST
        if f"{ids.scenario_dropdown}.value" in _output_keys(entry)
        or f"{ids.playlist_filter}.value" in _output_keys(entry)
    ]
    assert writers == [registration["output"]]


def test_no_callback_depends_only_on_what_the_selection_callback_conditionally_writes():
    """The structural test of the 2026-09-19 entry, carried to this page.

    ``reach_scenario`` returns ``no_update`` for both dropdowns on a visit
    with no query parameters. dash-renderer drops a ready callback when none
    of its Inputs was written and every one of them is a declared output of
    a group member that already ran, so a callback whose Inputs are all
    among these two outputs would never make its first call on such a visit.
    """
    selection = _selection_registration()
    written = _output_keys(selection)

    starved = [
        entry["output"]
        for entry in GLOBAL_CALLBACK_LIST
        if entry is not selection
        and entry["inputs"]
        and {f"{dep['id']}.{dep['property']}" for dep in entry["inputs"]} <= written
    ]

    assert starved == [], (
        "these callbacks would not make their initial call on a visit with no "
        f"query parameters: {starved}"
    )


def test_the_scenario_list_callback_keeps_the_input_nothing_writes():
    ids = run_history.SCENARIO_SELECTION_IDS
    registration = _registration(f"{ids.scenario_dropdown}.data")

    assert set(_keys(registration["inputs"])) == {
        f"{ids.playlist_filter}.value",
        f"{ids.deep_link}.data",
        f"{run_history.RUN_EVENTS_STORE_ID}.data",
    }
    assert _output_keys(registration) == {
        f"{ids.scenario_dropdown}.data",
        f"{ids.playlist_table_link}.children",
        f"{ids.playlist_filter}.data",
    }


def test_the_scenario_list_is_read_again_when_a_run_lands_and_waits_for_the_selection():
    """Follow can land on a scenario that had no runs when the page was drawn.

    The list has to gain it, or the dropdown names the old scenario while the
    chart and the stats show the new one. The run summary is what calls the
    list, and it calls ``reach_scenario`` too. The list also takes the
    filter's value, a plain output of that callback, so Dash holds the list
    until the selection has moved.
    """
    ids = run_history.SCENARIO_SELECTION_IDS
    scenario_list = _registration(f"{ids.scenario_dropdown}.data")
    selection = _selection_registration()
    summary = f"{run_history.RUN_EVENTS_STORE_ID}.data"

    assert summary in _keys(scenario_list["inputs"])
    assert summary in _keys(selection["inputs"])
    assert f"{ids.playlist_filter}.value" in _keys(scenario_list["inputs"])
    assert f"{ids.playlist_filter}.value" in _output_keys(selection)
    assert "@" not in selection["output"]


def test_the_page_registers_every_block_for_its_own_ids():
    def answering(output_fragment):
        registration = _registration(output_fragment)
        return GLOBAL_CALLBACK_MAP[registration["output"]]["callback"].__name__

    stats, options = run_history.SCENARIO_STATS_IDS, run_history.CHART_OPTIONS_IDS
    assert answering(f"{stats.num_runs}.children") == "get_scenario_num_runs"
    assert answering(f"{options.graph}.figure") == "apply_graph_appearance"
    assert answering(f"{options.panel}.className") == "toggle_chart_options"
    flushes = {
        entry["inputs"][0]["id"]: GLOBAL_CALLBACK_MAP[entry["output"]][
            "callback"
        ].__name__
        for entry in GLOBAL_CALLBACK_LIST
        if len(entry["inputs"]) == 1
        and entry["inputs"][0]["id"]
        in {
            run_history.POLLING_INTERVAL_ID,
            run_history.STARTUP_PLAYLIST_WARNING_INTERVAL_ID,
        }
        and "sendNotifications" in entry["output"]
    }
    assert flushes == {
        run_history.POLLING_INTERVAL_ID: "flush_run_import_failures",
        run_history.STARTUP_PLAYLIST_WARNING_INTERVAL_ID: "flush_startup_playlist_warnings",
    }


# --- The chart callback ------------------------------------------------------------------


def _chart_registration() -> dict:
    return _registration(f"{run_history.CHART_OPTIONS_IDS.cached_plot}.data")


def test_the_chart_rebuilds_on_the_mode_both_ranges_the_date_and_the_playlist_filter():
    """The filter is an Input, so the rank lines follow it at once.

    The date is one too: a range of days counts back from today, and nothing
    else changes at midnight on a page that is left open.
    """
    registration = _chart_registration()
    ids, options = run_history.SCENARIO_SELECTION_IDS, run_history.CHART_OPTIONS_IDS

    assert _keys(registration["inputs"]) == [
        f"{run_history.RUN_EVENTS_STORE_ID}.data",
        f"{ids.scenario_dropdown}.value",
        f"{ids.playlist_filter}.value",
        f"{run_history.CHART_MODE_ID}.value",
        f"{run_history.RUN_RANGE_ID}.value",
        f"{run_history.DAY_RANGE_ID}.value",
        f"{run_history.TODAY_STORE_ID}.data",
        f"{options.rank_overlay}.checked",
        f"{options.show_all_ranks}.checked",
        f"{options.high_score_overlay}.checked",
        f"{options.score_threshold_overlay}.checked",
        f"{options.score_threshold_percentage}.value",
        f"{options.score_threshold_notification}.checked",
    ]
    # Flipping the master switch must not rebuild the plot.
    assert _keys(registration["state"]) == [
        f"{options.run_notification}.checked",
        f"{TOAST_CHANNEL_REGISTRY_STORE_ID}.data",
    ]


def test_the_chart_shares_the_shells_toast_outputs_as_duplicates_and_still_loads():
    """The old page's chart callback is the plain writer of the same three."""
    registration = _chart_registration()
    outputs = registration["output"].strip(".").split("...")

    assert outputs[0] == f"{run_history.CHART_OPTIONS_IDS.cached_plot}.data"
    assert [output.split("@")[0] for output in outputs[1:]] == [
        "notification-container.sendNotifications",
        "notification-container.hideNotifications",
        f"{TOAST_CHANNEL_REGISTRY_STORE_ID}.data",
    ]
    assert all("@" in output for output in outputs[1:])
    # What Dash stores for "initial_duplicate": the page load still draws it.
    assert registration["prevent_initial_call"] is False


def _graph(
    monkeypatch,
    *,
    run_events=None,
    scenario=SCENARIO,
    playlist=None,
    mode="score_vs_run",
    run_range="100",
    day_range="90",
    high_score_overlay=False,
    threshold_overlay=False,
    percentage=95,
    verdict_switch=True,
    run_notifications=True,
    triggered=None,
    supports_overlays=True,
):
    """Call the chart callback with the data layer stood in for."""
    built = []

    def build(*args):
        built.append(args)
        return go.Figure(layout={"title": "built"}), supports_overlays

    monkeypatch.setattr(run_history, "is_scenario_in_database", lambda _name: True)
    monkeypatch.setattr(run_history, "build_run_history_figure", build)
    monkeypatch.setattr(run_history, "get_high_score", lambda _name: 830.0)
    monkeypatch.setattr(
        run_history,
        "ctx",
        SimpleNamespace(
            triggered=[
                {"prop_id": triggered or f"{run_history.RUN_EVENTS_STORE_ID}.data"}
            ]
        ),
    )
    result = run_history.generate_graph(
        run_events,
        scenario,
        playlist,
        mode,
        run_range,
        day_range,
        "2026-10-12",
        True,
        False,
        high_score_overlay,
        threshold_overlay,
        percentage,
        verdict_switch,
        run_notifications,
        {},
    )
    return result, built


def _annotations(plot_json: str) -> list[str]:
    return [
        annotation["text"]
        for annotation in json.loads(plot_json)["layout"].get("annotations", [])
    ]


def test_with_no_scenario_selected_the_chart_says_so():
    plot, notifications, hidden, channels = run_history.generate_graph(
        None, None, None, "score_vs_run", "100", "90", "2026-10-12", True, False,
        True, True, 95, True, True, {},
    )  # fmt: skip

    assert _annotations(plot) == [
        "<b>No scenario selected</b>",
        "Select a scenario to see your score history.",
    ]
    assert (notifications, hidden, channels) == (no_update, no_update, no_update)


def test_a_scenario_with_no_local_runs_says_so(monkeypatch):
    monkeypatch.setattr(run_history, "is_scenario_in_database", lambda _name: False)

    plot, notifications, _hidden, _channels = run_history.generate_graph(
        None, "Never Played", None, "score_vs_run", "100", "90", "2026-10-12",
        True, False, True, True, 95, True, True, {},
    )  # fmt: skip

    assert _annotations(plot) == [
        "<b>No local runs found</b>",
        "Play this scenario once and the graph will fill in.",
    ]
    assert notifications is no_update


def test_the_chart_asks_for_the_figure_with_every_control_and_todays_date(monkeypatch):
    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 12, 23, 59, 59)

    monkeypatch.setattr(run_history, "datetime", _FrozenDatetime)

    (plot, *_rest), built = _graph(
        monkeypatch,
        playlist="KovaaKsTestCode",
        mode="score_vs_time",
        run_range="50",
        day_range="30",
        triggered=f"{run_history.DAY_RANGE_ID}.value",
    )

    assert built == [
        (
            "score_vs_time",
            SCENARIO,
            "50",
            "30",
            True,
            False,
            "KovaaKsTestCode",
            date(2026, 10, 12),
        )
    ]
    assert json.loads(plot)["layout"]["title"]["text"] == "built"


def test_the_pb_score_and_score_threshold_lines_are_drawn_on_the_figure(monkeypatch):
    monkeypatch.setattr(run_history, "score_threshold_line", lambda *_args: 788.5)

    (plot, *_rest), _built = _graph(
        monkeypatch, high_score_overlay=True, threshold_overlay=True
    )

    assert _annotations(plot) == ["PB score (830.00)", "Score threshold (788.50)"]


def test_an_empty_percentage_draws_no_threshold_line(monkeypatch):
    monkeypatch.setattr(
        run_history,
        "score_threshold_line",
        lambda *_args: pytest.fail("placed a threshold line with no percentage"),
    )

    (plot, *_rest), _built = _graph(
        monkeypatch, high_score_overlay=True, threshold_overlay=True, percentage=""
    )

    assert _annotations(plot) == ["PB score (830.00)"]


def test_an_empty_range_takes_no_overlay_and_sends_no_toast(monkeypatch):
    (plot, notifications, hidden, channels), _built = _graph(
        monkeypatch,
        run_events=_payload(score=830.0),
        high_score_overlay=True,
        supports_overlays=False,
    )

    assert _annotations(plot) == []
    assert (notifications, hidden, channels) == (no_update, no_update, no_update)


def test_a_run_that_just_landed_gets_todays_toast(monkeypatch):
    """The page builds today's run toast until the plain run toast replaces it."""
    (_plot, notifications, hidden, channels), _built = _graph(
        monkeypatch, run_events=_payload(score=830.0)
    )

    (toast,) = notifications
    assert toast["title"] == "Threshold passed"
    assert toast["message"] == (
        f"{SCENARIO}: 830.00, 103.8% of PB. Also your 2nd-best at 34.64 cm/360."
    )
    assert hidden == []
    assert channels is not no_update


@pytest.mark.parametrize(("nth_score", "placed"), [(5, True), (6, False)])
def test_the_toast_places_a_run_against_a_top_n_fixed_at_five(
    monkeypatch, nth_score, placed
):
    """The page has no Top N scores control, so the old control's default stands."""
    (_plot, notifications, _hidden, _channels), _built = _graph(
        monkeypatch,
        run_events=_payload(nth_score=nth_score, is_new_sensitivity=True),
    )

    assert run_history.RUN_TOAST_TOP_N_SCORES == 5
    assert [toast["title"] for toast in notifications] == (
        ["New 5th-best score"] if placed else []
    )


def test_a_control_change_does_not_repeat_the_last_runs_toast(monkeypatch):
    """The store replays its summary to every later call."""
    (_plot, notifications, hidden, channels), _built = _graph(
        monkeypatch,
        run_events=_payload(score=830.0),
        triggered=f"{run_history.CHART_MODE_ID}.value",
    )

    assert (notifications, hidden) == ([], [])
    assert channels is no_update


def test_run_notifications_off_sends_no_toast(monkeypatch):
    (_plot, notifications, _hidden, channels), _built = _graph(
        monkeypatch, run_events=_payload(score=830.0), run_notifications=False
    )

    assert notifications == []
    assert channels is no_update


def test_the_verdict_switch_off_leaves_only_a_placement_to_report(monkeypatch):
    (_plot, notifications, _hidden, _channels), _built = _graph(
        monkeypatch, run_events=_payload(score=830.0), verdict_switch=False
    )

    assert [toast["title"] for toast in notifications] == ["New 2nd-best score"]


# --- The date the ranges of days count back from ---------------------------------------


def _clock_at(*moment):
    """Return a ``datetime`` whose ``now`` is always the moment given."""

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(*moment)

    return _FrozenDatetime


def test_the_layout_holds_the_date_the_page_is_drawn_on(monkeypatch):
    """So the first tick finds the date held, and rebuilds no chart just drawn."""
    monkeypatch.setattr(run_history, "datetime", _clock_at(2026, 10, 12, 9, 0))

    store = _by_id(run_history.layout(), run_history.TODAY_STORE_ID)

    assert run_history.TODAY_STORE_ID == "run-history-today"
    assert isinstance(store, dcc.Store)
    assert store.data == "2026-10-12"


def test_the_date_is_checked_on_the_slow_tick_and_never_on_load():
    """A call on load would hold the first chart for an answer that writes nothing."""
    registration = _registration(f"{run_history.TODAY_STORE_ID}.data")

    assert registration["output"] == f"{run_history.TODAY_STORE_ID}.data"
    assert _keys(registration["inputs"]) == [
        f"{run_history.RELATIVE_TIME_INTERVAL_ID}.n_intervals"
    ]
    assert _keys(registration["state"]) == [f"{run_history.TODAY_STORE_ID}.data"]
    assert registration["prevent_initial_call"] is True


def test_a_tick_inside_the_same_date_writes_nothing(monkeypatch):
    """The store is the chart's input, so no write means no rebuild."""
    monkeypatch.setattr(run_history, "datetime", _clock_at(2026, 10, 12, 23, 59, 59))

    assert run_history.advance_today(1, "2026-10-12") is no_update
    assert run_history.advance_today(2, "2026-10-12") is no_update


def test_the_first_tick_past_midnight_writes_the_new_date_and_the_next_does_not(
    monkeypatch,
):
    """One write a day, so the date moving on rebuilds the chart once."""
    monkeypatch.setattr(run_history, "datetime", _clock_at(2026, 10, 13, 0, 0, 0))

    written = run_history.advance_today(3, "2026-10-12")

    assert written == "2026-10-13"
    assert run_history.advance_today(4, written) is no_update


@pytest.mark.parametrize("held", [None, "", "not a date"])
def test_a_page_holding_no_date_is_given_todays(monkeypatch, held):
    monkeypatch.setattr(run_history, "datetime", _clock_at(2026, 10, 12, 9, 0))

    assert run_history.advance_today(1, held) == "2026-10-12"


def test_a_chart_left_open_past_midnight_is_rebuilt_for_the_new_date(monkeypatch):
    """The date's write calls the chart, which reads the clock for itself.

    The last run's summary is still in its store on that call, and it earns
    no second toast.
    """
    monkeypatch.setattr(run_history, "datetime", _clock_at(2026, 10, 13, 0, 0, 20))

    (_plot, notifications, hidden, channels), built = _graph(
        monkeypatch,
        run_events=_payload(score=830.0),
        mode="score_vs_time",
        day_range="7",
        triggered=f"{run_history.TODAY_STORE_ID}.data",
    )

    assert [arguments[-1] for arguments in built] == [date(2026, 10, 13)]
    assert (notifications, hidden) == ([], [])
    assert channels is no_update


# --- The stylesheet --------------------------------------------------------------------


def _css_block(css, selector):
    match = re.search(rf"(?m)^{re.escape(selector)} \{{(.*?)^\}}", css, re.DOTALL)
    assert match, f"no {selector} rule in the stylesheet"
    return match.group(1)


def test_the_list_takes_a_column_of_500px_beside_the_chart():
    columns = _css_block(STYLESHEET.read_text(encoding="utf-8"), ".run-history-columns")

    assert "grid-template-columns: minmax(0, 1fr) 500px;" in columns
    assert "flex: 1 1 0;" in columns


def test_chart_options_stacks_on_the_charts_own_area_at_48em():
    """A container of its own: the old page's 62em is pinned to its own name."""
    css = STYLESHEET.read_text(encoding="utf-8")
    area = _css_block(css, ".run-history-chart-area")

    assert "container: run-history-chart-area / inline-size;" in area
    assert "min-height: 20rem;" in area
    assert re.findall(
        r"@container run-history-chart-area \(max-width: ([^)]+)\)", css
    ) == ["48em"]
    assert re.findall(r"@container home-chart-area \(max-width: ([^)]+)\)", css) == [
        "62em"
    ]


def test_the_columns_stack_when_the_page_itself_is_900px_or_narrower():
    """Measured on the page, never the window: the navbar takes 225px of it."""
    css = STYLESHEET.read_text(encoding="utf-8")

    assert "container: run-history-page / inline-size;" in _css_block(
        css, ".run-history-page"
    )
    assert re.findall(r"@container run-history-page \(max-width: ([^)]+)\)", css) == [
        "900px"
    ]


def test_the_cards_slot_is_reserved_at_one_height():
    slot = _css_block(STYLESHEET.read_text(encoding="utf-8"), ".run-history-card-slot")

    assert "min-height: 132px;" in slot
    assert "min-width: min(380px, 100%);" in slot
