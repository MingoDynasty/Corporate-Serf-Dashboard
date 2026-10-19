"""The Run History page: where it is served, what its layout holds, and its callbacks.

The page has its own address and its own navbar entry, beside the Home page
at ``/``. These tests also hold what keeps the two pages apart: the places
the address is written in, and an id of its own for everything the page
draws. What the chart plots is ``tests/test_run_history_chart.py``, and the
rule for a scenario the playlist filter does not list is
``tests/test_scenario_selection.py``.
"""

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import dash
import dash_mantine_components as dmc
import plotly.graph_objects as go
import pytest
from dash import dcc, html, no_update
from dash._callback import GLOBAL_CALLBACK_LIST, GLOBAL_CALLBACK_MAP

dash.Dash(__name__, use_pages=True, pages_folder="")

from source import app_shell  # noqa: E402
from source.components import (  # noqa: E402
    chart_options,
    latest_run_card,
    pb_card,
    run_history_chart,
    run_history_list,
    scenario_selection,
    setup_surfaces,
)
from source.components.columns_menu import choice_checkbox_id  # noqa: E402
from source.config import settings_service  # noqa: E402
from source.kovaaks.data_models import RunData  # noqa: E402
from source.pages import home, run_history  # noqa: E402
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


# --- Where the page is, and what leads to it -----------------------------------


def test_the_page_is_registered_at_its_final_address_under_its_name():
    page = dash.page_registry["source.pages.run_history"]

    assert page["path"] == "/run-history"
    assert page["name"] == "Run History"


def test_the_page_has_its_navbar_entry_second_after_home():
    links = [
        (component.label, component.href)
        for component in _walk_components(app_shell.layout())
        if isinstance(component, dmc.NavLink)
    ]

    assert links[:2] == [("Home", "/"), ("Run History", "/run-history")]
    # One entry: the page is listed once, and under no other name.
    assert [href for _label, href in links].count("/run-history") == 1


def test_the_pages_address_is_written_in_three_places_and_no_other():
    """The line that registers it, the navbar, and the one link builder.

    Counted per file, so a new hard-coded copy of the address fails here. A
    link to a scenario on the page is built by the link builder, which is
    what keeps the address and its two parameters in one place.
    """
    mentions = {
        path.relative_to(SOURCE_ROOT).as_posix(): path.read_text(
            encoding="utf-8"
        ).count("/run-history")
        for path in sorted(SOURCE_ROOT.rglob("*.py"))
        if "/run-history" in path.read_text(encoding="utf-8")
    }

    assert mentions == {
        "pages/run_history.py": 1,
        "app_shell.py": 1,
        "kovaaks/playlist_scenarios_service.py": 1,
    }


def test_home_owns_the_landing_address():
    page = dash.page_registry["source.pages.home"]

    assert (page["path"], page["name"]) == ("/", "Home")


def test_the_page_never_imports_another_pages_module():
    """Dash Pages loads a page file as ``pages.<name>``.

    A second import path would make a second copy of the module, with its own
    state and its own callback registrations. Home is the page it shares the
    setup surfaces and the queued notices with, and both live under
    ``source/components/`` so that neither page imports the other.
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
    assert set(run_history.LATEST_RUN_CARD_IDS) <= mounted
    assert set(run_history.PB_CARD_IDS) <= mounted
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
        run_history.RUN_LIST_IDS.view,
    ) == (
        "run-history-follow-switch",
        "run-history-chart-mode",
        "run-history-run-range",
        "run-history-day-range",
        "run-history-list-view",
    )
    assert choice_checkbox_id(run_history.RUN_LIST_IDS.columns_menu, "median_best") == {
        "type": "run-history-list-columns-choice",
        "choice": "median_best",
    }
    options = run_history.CHART_OPTIONS_IDS
    assert (
        options.rank_overlay,
        options.show_all_ranks,
        options.high_score_overlay,
        options.point_size,
        options.point_color,
        options.score_threshold_overlay,
        options.score_threshold_percentage,
    ) == (
        "run-history-rank-overlay-switch",
        "run-history-show-all-ranks-switch",
        "run-history-high-score-overlay-switch",
        "run-history-point-size",
        "run-history-point-color",
        "run-history-score-threshold-overlay-switch",
        "run-history-score-threshold-percentage",
    )


# --- The layout ----------------------------------------------------------------


def test_the_layout_takes_a_query_parameter_it_does_not_name():
    """A link may carry one only to make its address differ from the last."""
    page = run_history.layout(scenario=SCENARIO, run="2026.10.12-10.50.00")

    assert _by_id(page, run_history.SCENARIO_SELECTION_IDS.deep_link).data == {
        "scenario": SCENARIO
    }


def test_the_top_row_holds_the_dropdowns_stats_note_and_pb_then_the_latest_run_card():
    """Two columns: the first holds the dropdowns, Scenario Stats, the note and PB.

    The latest-run card is the second column on its own, so it sits over
    the run list, and the PB card is last in the first, beside it. The
    scenario note card is in the room between the stats card and the PB card.
    """
    row = _by_class(run_history.layout(), "run-history-top-row")

    left, card = row.children
    assert left.className == "run-history-top-row-left"
    assert card.className == latest_run_card.CARD_CLASS
    assert _ids(card) == set(run_history.LATEST_RUN_CARD_IDS)
    dropdowns, stats, note, pb = left.children
    assert dropdowns.className == "run-history-dropdown-column"
    assert stats.className == "scenario-stats-card"
    assert note.id == run_history.NOTE_CARD_IDS.card
    # Position is the PB card's now.
    assert run_history.PB_CARD_IDS.rank in _ids(pb)
    assert run_history.PB_CARD_IDS.rank not in _ids(stats)
    assert pb.className == pb_card.CARD_CLASS
    page_owned = {"run_events", "scenario_dropdown", "playlist_filter"}
    page_owned |= {"polling_interval", "relative_time_interval"}
    assert _ids(pb) == {
        component_id
        for field, component_id in run_history.PB_CARD_IDS._asdict().items()
        if field not in page_owned
    }
    playlist_field, scenario_field = dropdowns.children
    assert playlist_field.className == "run-history-playlist-field"
    assert scenario_field.className == "run-history-scenario-field"
    assert [getattr(child, "id", None) for child in playlist_field.children] == [
        run_history.SCENARIO_SELECTION_IDS.playlist_filter,
        run_history.SCENARIO_SELECTION_IDS.playlist_table_link,
    ]
    assert [getattr(child, "id", None) for child in scenario_field.children] == [
        run_history.SCENARIO_SELECTION_IDS.scenario_dropdown,
        run_history.FOLLOW_SWITCH_ID,
    ]


def test_the_link_and_the_switch_follow_their_dropdowns_and_are_never_in_a_label():
    """A label names its input, so anything in it would join the dropdown's name.

    Each Select's label is its plain name, and the link and the switch are
    the Select's siblings, after it. The stylesheet places the link on the
    label's line and the switch under the dropdown.
    """
    page = run_history.layout()
    playlist_field = _by_class(page, "run-history-playlist-field")
    scenario_field = _by_class(page, "run-history-scenario-field")

    playlist_filter, link_holder = playlist_field.children
    scenario, follow = scenario_field.children
    assert playlist_filter.label == "Playlist filter"
    assert scenario.label == "Selected scenario"
    assert link_holder.className == "run-history-playlist-table-link"
    assert follow.className == "run-history-follow-switch"


def test_the_playlist_filters_scrollbar_is_always_visible():
    """A long list of playlists should read as one that scrolls."""
    playlist_filter = _by_id(
        run_history.layout(), run_history.SCENARIO_SELECTION_IDS.playlist_filter
    )

    assert playlist_filter.scrollAreaProps == {"type": "always"}


def test_the_playlist_link_holder_starts_empty_and_takes_no_room():
    """The holder is a callback's output, so it is in the layout on every visit.

    It starts empty because the layout cannot know the remembered selection,
    and an empty holder must take no room beside the filter's label.
    """
    field = _by_class(run_history.layout(), "run-history-playlist-field")
    holder = field.children[1]

    assert holder.id == run_history.SCENARIO_SELECTION_IDS.playlist_table_link
    assert getattr(holder, "children", None) is None
    # A Stack's gap or a margin on the holder would be paid while there is no
    # link to space. The link brings its own.
    assert isinstance(field, dmc.Box)
    assert getattr(holder, "mt", None) is None


def test_section_titles_keep_visual_size_with_accessible_heading_order():
    titles = {
        component.children: component
        for component in _walk_components(run_history.layout())
        if isinstance(component, dmc.Title)
    }

    # The panel's groups, drawn small.
    for group in ("Overlays", "Run Data Points", "Score Threshold"):
        assert titles[group].order == 3
        assert titles[group].size == "h6"


def test_the_three_cards_first_lines_are_plain_text_and_not_headings():
    """Scenario Stats' first line reads as the PB card's and the latest-run card's do."""
    page = run_history.layout()
    titles = [
        component.children
        for component in _walk_components(page)
        if isinstance(component, dmc.Title)
    ]
    first_line = _by_class(page, "scenario-stats-heading")

    assert "Scenario Stats" not in titles
    assert "Scenario stats" not in titles
    assert isinstance(first_line, html.Div)
    assert first_line.children == "Scenario stats"


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
    """Each script is pinned by the selector in its text, as no test runs it.

    Opening and collapsing the Chart options panel resizes the graph's
    container without a window resize, which is the one case
    ``homeGraphResize.js`` exists for: ``responsive=True`` alone only redraws
    on a window resize.
    """
    graph = _by_id(run_history.layout(), run_history.CHART_OPTIONS_IDS.graph)

    assert isinstance(graph, dcc.Graph)
    assert graph.className == "home-graph"
    assert graph.responsive is True
    for script in ("homeGraphResize.js", "homeGraphZoomFit.js"):
        assert ".home-graph" in (REPO_ROOT / "assets" / script).read_text(
            encoding="utf-8"
        )


def test_the_chart_starts_as_the_neutral_placeholder():
    """Both the graph and the store it is restyled from, so neither flashes an axis."""
    page = run_history.layout()

    graph = _by_id(page, run_history.CHART_OPTIONS_IDS.graph)
    cached = json.loads(_by_id(page, run_history.CHART_OPTIONS_IDS.cached_plot).data)
    for drawn in (graph.figure, cached):
        placeholder = go.Figure(drawn)
        assert not placeholder.layout.annotations
        assert placeholder.layout.paper_bgcolor == "rgba(0,0,0,0)"
        assert placeholder.layout.plot_bgcolor == "rgba(0,0,0,0)"
        assert placeholder.layout.dragmode is False
        assert placeholder.layout.xaxis.visible is False
        assert placeholder.layout.yaxis.visible is False


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

    defaults = [
        (run_history.SCENARIO_SELECTION_IDS.playlist_filter, "value", None),
        (run_history.SCENARIO_SELECTION_IDS.scenario_dropdown, "value", None),
        (run_history.FOLLOW_SWITCH_ID, "checked", True),
        (run_history.CHART_MODE_ID, "value", "score_vs_run"),
        (run_history.RUN_RANGE_ID, "value", "100"),
        (run_history.DAY_RANGE_ID, "value", "90"),
        (run_history.CHART_OPTIONS_IDS.score_threshold_percentage, "value", 95),
        (run_history.CHART_OPTIONS_IDS.score_threshold_overlay, "checked", True),
        (run_history.RUN_LIST_IDS.view, "value", "scenario"),
        (
            choice_checkbox_id(run_history.RUN_LIST_IDS.columns_menu, "median_best"),
            "checked",
            False,
        ),
    ]
    for component_id, prop, default in defaults:
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


def test_the_follow_help_says_a_filter_in_the_way_is_cleared_and_a_note_waits():
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
        "filter is cleared. It waits while a scenario note has unsaved changes."
    )


def test_the_percentage_help_says_a_run_is_judged_whatever_judges_it():
    """The sentence names no surface: the check and the card judge a run."""
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


def test_each_help_text_has_one_wording():
    """One key a help text, and no second key for a control's help.

    A second key would hold a wording no control shows, and the two would
    drift apart with nothing on screen to show it.
    """
    help_text = chart_options.SETTINGS_HELP_TEXT

    assert set(help_text) == {
        "automatically-change-scenario",
        "rank-overlay",
        "show-all-ranks",
        "high-score-overlay",
        "score-threshold-overlay",
        "score-threshold-percentage",
    }
    assert rendered_text(help_text["automatically-change-scenario"]).endswith(
        "If the **Playlist filter** doesn't list that scenario, the filter is "
        "cleared. It waits while a scenario note has unsaved changes."
    )
    assert help_text["score-threshold-percentage"].endswith(
        "A run is judged against the personal best you had before the run."
    )
    # What the control draws is the text under its own key.
    page = run_history.layout()
    shown = {
        run_history.FOLLOW_SWITCH_ID: "automatically-change-scenario",
        run_history.CHART_OPTIONS_IDS.score_threshold_percentage: (
            "score-threshold-percentage"
        ),
    }
    for component_id, key in shown.items():
        (tooltip,) = [
            component
            for component in _walk_components(_by_id(page, component_id).label)
            if isinstance(component, dmc.Tooltip)
        ]
        assert tooltip.label == help_text[key]


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


def test_the_hint_has_this_pages_id_and_never_homes():
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
    return {"latest": _run(scenario_name, **fields)}


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

    assert summary == {"latest": _run("Scenario B", run_id="b.csv")}
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
        {"latest": _run(SCENARIO, run_id="a.csv")},
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

    asked_by_the_list = run_history.RUN_LIST_IDS.scenario_asked

    assert GLOBAL_CALLBACK_MAP[registration["output"]]["callback"].__name__ == (
        "reach_scenario_or_the_one_asked_for"
    )
    note = run_history.NOTE_CARD_IDS
    assert registration["output"] == (
        f"..{ids.playlist_filter}.value...{ids.scenario_dropdown}.value"
        f"...{note.waiting}.data...{note.held}.data.."
    )
    assert "@" not in registration["output"]
    # A name pressed in the run list's tree is the third thing that reaches a
    # scenario, and the note card's answer the fourth. Each comes here and
    # writes neither dropdown itself. The latest-run card follows the
    # selection and has no input here.
    assert _keys(registration["inputs"]) == [
        f"{ids.deep_link}.data",
        f"{run_history.RUN_EVENTS_STORE_ID}.data",
        f"{asked_by_the_list}.data",
        f"{note.go}.data",
        f"{run_history.FOLLOW_SWITCH_ID}.checked",
    ]
    assert _keys(registration["state"]) == [
        f"{ids.playlist_filter}.value",
        f"{ids.scenario_dropdown}.value",
        f"{note.editor}.data",
        f"{note.draft}.value",
        f"{note.waiting}.data",
    ]
    card_ids = set(run_history.LATEST_RUN_CARD_IDS)
    assert not card_ids & {
        dep["id"] for dep in registration["inputs"] + registration["state"]
    }
    # It applies this visit's query parameters, so the page load runs it.
    assert registration["prevent_initial_call"] is False
    writers = [
        entry["output"]
        for entry in GLOBAL_CALLBACK_LIST
        if f"{ids.scenario_dropdown}.value" in _output_keys(entry)
        or f"{ids.playlist_filter}.value" in _output_keys(entry)
    ]
    assert writers == [registration["output"]]


_SELECTION_PROPS = scenario_selection.SelectionProps(
    list_asked=f"{run_history.RUN_LIST_IDS.scenario_asked}.data",
    run_events=f"{run_history.RUN_EVENTS_STORE_ID}.data",
    go=f"{run_history.NOTE_CARD_IDS.go}.data",
    follow=f"{run_history.FOLLOW_SWITCH_ID}.checked",
    deep_link=f"{run_history.SCENARIO_SELECTION_IDS.deep_link}.data",
)


def _press(triggered: list[dict], run_events, follow, list_scenario):
    """Call the selection callback as Dash would, for a selected scenario of A.

    With no note open, so it writes only the dropdowns, and returns those.
    """
    *dropdowns, waiting, held = scenario_selection.reach_the_scenario_asked_for(
        triggered,
        _SELECTION_PROPS,
        {},
        run_events,
        list_scenario,
        None,
        follow,
        None,
        "Scenario A",
        None,
        None,
        None,
    )
    assert (waiting, held) == (no_update, no_update)
    return tuple(dropdowns)


@pytest.mark.parametrize(
    ("follow", "written"),
    [(True, (no_update, "Scenario C")), (False, (no_update, no_update))],
)
def test_a_run_that_lands_after_a_name_was_pressed_is_answered_and_not_the_name(
    follow, written
):
    """The list's store replays the name pressed into every later call.

    Read from the values, a run that lands would select that name again.
    """
    landed = {"latest": {"scenario_name": "Scenario C"}}
    triggered = [
        {"prop_id": f"{run_history.RUN_EVENTS_STORE_ID}.data", "value": landed}
    ]

    assert _press(triggered, landed, follow, "Scenario B") == written


def test_a_name_pressed_after_a_run_landed_selects_the_name():
    """The summary store replays its last batch into the press's call."""
    landed = {"latest": {"scenario_name": "Scenario C"}}
    triggered = [
        {
            "prop_id": f"{run_history.RUN_LIST_IDS.scenario_asked}.data",
            "value": "Scenario B",
        }
    ]

    assert _press(triggered, landed, True, "Scenario B") == (no_update, "Scenario B")


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
        f"{run_history.RUN_LANDED_STORE_ID}.data",
    }
    assert _output_keys(registration) == {
        f"{ids.scenario_dropdown}.data",
        f"{ids.playlist_table_link}.children",
        f"{ids.playlist_filter}.data",
    }


def test_the_scenario_list_is_read_again_when_a_run_lands_and_waits_for_the_selection():
    """Follow can land on a scenario that had no runs when the page was drawn.

    The list has to gain it, or the dropdown names the old scenario while the
    chart and the stats show the new one. The store written for every batch
    is what calls the list, and the summary, written in the same answer,
    calls ``reach_scenario``. The list also takes the filter's value, a plain
    output of that callback, so Dash holds the list until the selection has
    moved.

    It is the store for every batch and not the summary, so that a scenario
    whose first run lands while Follow is off joins the list too: no summary
    is written for a run the page does not show.
    """
    ids = run_history.SCENARIO_SELECTION_IDS
    scenario_list = _registration(f"{ids.scenario_dropdown}.data")
    selection = _selection_registration()
    summary = f"{run_history.RUN_EVENTS_STORE_ID}.data"
    run_landed = f"{run_history.RUN_LANDED_STORE_ID}.data"
    delivery = _registration(summary)

    assert run_landed in _keys(scenario_list["inputs"])
    assert summary not in _keys(scenario_list["inputs"])
    assert summary in delivery["output"]
    assert run_landed in delivery["output"]
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
    assert answering(f"{options.graph}.figure") == "ring_latest_run_on_graph"
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
    ]
    # It reads no notification setting and no toast registry: the shell sends
    # the run toast.
    assert registration["state"] == []


def test_the_chart_writes_its_figure_and_nothing_else_and_the_page_load_draws_it():
    """The run toast's channel has one producer, the shell's drain.

    With the figure as its one plain output the callback needs none of the
    ``prevent_initial_call`` forms, so the page load runs it, which is what
    draws the first chart.
    """
    registration = _chart_registration()

    assert registration["output"] == f"{run_history.CHART_OPTIONS_IDS.cached_plot}.data"
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
    plot = run_history.generate_graph(
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
    )
    return plot, built


def _annotations(plot_json: str) -> list[str]:
    return [
        annotation["text"]
        for annotation in json.loads(plot_json)["layout"].get("annotations", [])
    ]


def test_with_no_scenario_selected_the_chart_says_so():
    plot = run_history.generate_graph(
        None, None, None, "score_vs_run", "100", "90", "2026-10-12", True, False,
        True, True, 95,
    )  # fmt: skip

    assert _annotations(plot) == [
        "<b>No scenario selected</b>",
        "Select a scenario to see your score history.",
    ]


def test_a_scenario_with_no_local_runs_says_so(monkeypatch):
    monkeypatch.setattr(run_history, "is_scenario_in_database", lambda _name: False)

    plot = run_history.generate_graph(
        None, "Never Played", None, "score_vs_run", "100", "90", "2026-10-12",
        True, False, True, True, 95,
    )  # fmt: skip

    assert _annotations(plot) == [
        "<b>No local runs found</b>",
        "Play this scenario once and the graph will fill in.",
    ]


def test_the_chart_asks_for_the_figure_with_every_control_and_todays_date(monkeypatch):
    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 12, 23, 59, 59)

    monkeypatch.setattr(run_history, "datetime", _FrozenDatetime)

    plot, built = _graph(
        monkeypatch,
        playlist="KovaaKsTestCode",
        mode="score_vs_time",
        run_range="50",
        day_range="30",
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

    plot, _built = _graph(monkeypatch, high_score_overlay=True, threshold_overlay=True)

    assert _annotations(plot) == ["PB score (830.00)", "Score threshold (788.50)"]


@pytest.mark.parametrize("empty_percentage", [None, ""])
def test_an_empty_percentage_draws_no_threshold_line(monkeypatch, empty_percentage):
    """A cleared field sends an empty string, and one never set sends nothing."""
    monkeypatch.setattr(
        run_history,
        "score_threshold_line",
        lambda *_args: pytest.fail("placed a threshold line with no percentage"),
    )

    plot, _built = _graph(
        monkeypatch,
        high_score_overlay=True,
        threshold_overlay=True,
        percentage=empty_percentage,
    )

    assert _annotations(plot) == ["PB score (830.00)"]


def test_an_empty_range_takes_no_overlay(monkeypatch):
    plot, _built = _graph(
        monkeypatch,
        run_events=_payload(score=830.0),
        high_score_overlay=True,
        supports_overlays=False,
    )

    assert _annotations(plot) == []


def test_a_run_that_lands_redraws_the_chart_and_the_page_sends_no_toast(monkeypatch):
    """The answer is the figure alone. The shell's drain sends the run's toast."""
    plot, built = _graph(monkeypatch, run_events=_payload(score=830.0))

    assert isinstance(plot, str)
    assert json.loads(plot)["layout"]["title"]["text"] == "built"
    assert len(built) == 1


def test_the_page_builds_no_toast_of_its_own():
    """Each toast channel keeps one producer, and the run toast's is the shell."""
    source = (SOURCE_ROOT / "pages" / "run_history.py").read_text(encoding="utf-8")

    assert "channel_toast" not in source
    assert "sendNotifications" not in source
    assert not (SOURCE_ROOT / "components" / "run_verdict_toast.py").exists()


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
    """The date's write calls the chart, which reads the clock for itself."""
    monkeypatch.setattr(run_history, "datetime", _clock_at(2026, 10, 13, 0, 0, 20))

    _plot, built = _graph(
        monkeypatch,
        run_events=_payload(score=830.0),
        mode="score_vs_time",
        day_range="7",
    )

    assert [arguments[-1] for arguments in built] == [date(2026, 10, 13)]


# --- The stylesheet --------------------------------------------------------------------


def _css_block(css, selector):
    """Return the body of the top-level rule for ``selector`` alone.

    A selector list's later lines are not a rule of their own, so a line
    after one ending in a comma never matches.
    """
    match = re.search(
        rf"(?m)(?<!,\n)^{re.escape(selector)} \{{(.*?)^\}}", css, re.DOTALL
    )
    assert match, f"no {selector} rule in the stylesheet"
    return match.group(1)


def _container_block(css, query):
    """Return the body of the ``@container`` rule for ``query``."""
    match = re.search(
        rf"(?m)^@container {re.escape(query)} \{{(.*?)^\}}", css, re.DOTALL
    )
    assert match, f"no @container {query} rule in the stylesheet"
    return match.group(1)


def test_the_list_takes_a_column_of_500px_beside_the_chart():
    css = STYLESHEET.read_text(encoding="utf-8")
    columns = _css_block(css, ".run-history-columns")

    assert "--run-history-list-width: 500px;" in _css_block(css, ".run-history-page")
    assert (
        "grid-template-columns: minmax(0, 1fr) var(--run-history-list-width);"
        in columns
    )
    assert "flex: 1 1 0;" in columns


def test_the_top_row_takes_the_columns_and_the_gap_of_the_chart_and_the_list():
    """So the latest-run card's edges are the run list's at every zoom level.

    One value sets the list's width for both, and the row stretches each
    column, and every card in it, to its own height.
    """
    css = STYLESHEET.read_text(encoding="utf-8")
    row = _css_block(css, ".run-history-top-row")
    columns = _css_block(css, ".run-history-columns")

    for rule in (row, columns):
        assert (
            "grid-template-columns: minmax(0, 1fr) var(--run-history-list-width);"
            in rule
        )
        assert "    gap: var(--mantine-spacing-md);" in rule
    assert "display: grid;" in row
    assert "align-items" not in row
    assert "500px" not in row
    assert css.count("--run-history-list-width: ") == 1


def test_the_first_column_wraps_its_pieces_on_its_own_width():
    left = _css_block(
        STYLESHEET.read_text(encoding="utf-8"), ".run-history-top-row-left"
    )

    assert "flex-wrap: wrap;" in left
    assert "min-width: 0;" in left
    assert "align-items" not in left


def test_the_dropdowns_column_grows_from_260px_to_420px():
    column = _css_block(
        STYLESHEET.read_text(encoding="utf-8"), ".run-history-dropdown-column"
    )

    assert "flex: 1 1 260px;" in column
    assert "max-width: 420px;" in column
    assert "min-width: min(260px, 100%);" in column
    assert "flex-direction: column;" in column


def test_the_link_is_placed_on_the_labels_line():
    """The Select's own box lays out nothing, so its label is the field's item."""
    css = STYLESHEET.read_text(encoding="utf-8")
    fields = (".run-history-playlist-field", ".run-history-scenario-field")

    assert "display: grid;" in _css_block(
        css, ".run-history-playlist-field,\n.run-history-scenario-field"
    )
    roots = ",\n".join(f"{field} > .mantine-Select-root" for field in fields)
    assert "display: contents;" in _css_block(css, roots)
    labels = _css_block(css, ",\n".join(f"{f} .mantine-Select-label" for f in fields))
    assert "grid-row: 1;" in labels
    inputs = _css_block(css, ",\n".join(f"{f} .mantine-Select-wrapper" for f in fields))
    assert "grid-row: 2;" in inputs
    link = _css_block(css, ".run-history-playlist-table-link")
    assert "grid-column: 2;" in link
    assert "grid-row: 1;" in link


def test_the_follow_switch_sits_under_the_scenario_dropdown_on_a_16px_line():
    """The maintainer's choice on PR #380: under the dropdown, and small.

    On the label's line it sat between the two dropdowns. Under the dropdown
    at its full size it made the top row 148px; small, with its text at the
    dropdown labels' 14px and a 16px help icon, the row is 141px.
    """
    css = STYLESHEET.read_text(encoding="utf-8")
    page = run_history.layout()
    follow = _by_id(page, run_history.FOLLOW_SWITCH_ID)
    _text, tooltip = follow.label.children

    below = _css_block(css, ".run-history-follow-switch")
    assert "grid-column: 1 / -1;" in below
    assert "grid-row: 3;" in below
    assert "@container run-history-dropdown-column" not in css
    assert follow.size == "xs"
    assert tooltip.children.size == 16
    assert "font-size: var(--mantine-font-size-sm);" in _css_block(
        css, ".run-history-follow-switch .mantine-Switch-label"
    )
    # dmc's box round the help icon, a block whose line would be 3px taller.
    assert tooltip.boxWrapperProps == {"className": "settings-help-target"}
    assert "display: flex;" in _css_block(
        css, ".run-history-follow-switch .settings-help-target"
    )


def test_chart_options_stacks_on_the_charts_own_area_at_48em():
    """Measured on the chart's own area, never the window.

    The navbar and the run list take their room first, so the window's width
    says little about the room the chart has.
    """
    css = STYLESHEET.read_text(encoding="utf-8")
    area = _css_block(css, ".run-history-chart-area")

    assert "container: run-history-chart-area / inline-size;" in area
    assert "min-height: 20rem;" in area
    assert re.findall(
        r"@container run-history-chart-area \(max-width: ([^)]+)\)", css
    ) == ["48em"]
    # The one threshold the panel stacks at: no other container has a say.
    assert "home-chart-area" not in css


def test_the_columns_stack_when_the_page_itself_is_900px_or_narrower():
    """Measured on the page, never the window: the navbar takes 225px of it."""
    css = STYLESHEET.read_text(encoding="utf-8")

    assert "container: run-history-page / inline-size;" in _css_block(
        css, ".run-history-page"
    )
    assert re.findall(r"@container run-history-page \(max-width: ([^)]+)\)", css) == [
        "900px"
    ]


def test_the_top_row_is_one_wrapping_line_where_the_columns_stack():
    """The dropdowns, Scenario Stats, PB, then the latest-run card, in the page's order.

    With the list above the chart there is nothing for the card to line up
    with, so the first column's pieces and the card share one line, packed
    from its start: the PB card no longer keeps to the column's right end.
    """
    narrow = _container_block(
        STYLESHEET.read_text(encoding="utf-8"), "run-history-page (max-width: 900px)"
    )

    row = re.search(r"\.run-history-top-row \{(.*?)\}", narrow, re.DOTALL)
    left = re.search(r"\.run-history-top-row-left \{(.*?)\}", narrow, re.DOTALL)
    pb = re.search(r"\.pb-card \{(.*?)\}", narrow, re.DOTALL)
    card = re.search(r"\.run-history-card \{(.*?)\}", narrow, re.DOTALL)
    assert row and "display: flex;" in row.group(1)
    assert "flex-wrap: wrap;" in row.group(1)
    assert left and "display: contents;" in left.group(1)
    assert pb and "margin-left: 0;" in pb.group(1)
    assert card and "flex: 1 1 380px;" in card.group(1)


def test_every_card_in_the_row_has_the_same_frame():
    frame = _css_block(
        STYLESHEET.read_text(encoding="utf-8"),
        ".run-history-card,\n.scenario-stats-card,\n.pb-card",
    )

    assert "border: 1px solid var(--mantine-color-default-border);" in frame
    assert "border-radius: var(--mantine-radius-sm);" in frame


def test_the_card_is_as_tall_as_the_row_and_never_under_135px():
    """135px holds the card's tallest state, so its height never follows a run.

    The tallest state is the second line on two lines in a narrow card, over
    the third and fourth lines, measured at 135px in Edge and Firefox. A
    minimum and not a height: the card is as tall as the row, which the PB
    card makes taller in its setup state, with no KovaaK's username.
    """
    css = STYLESHEET.read_text(encoding="utf-8")
    card = _css_block(css, ".run-history-card")

    assert "min-height: 135px;" in card
    assert re.search(r"(?m)^    height:", card) is None
    assert "min-width: 0;" in card
    assert "overflow: hidden;" in card
    assert "justify-content: center;" in card


def test_the_stats_card_is_270px_and_adds_only_its_border_to_the_height():
    """Category fits beside the PB card without padding raising the row."""
    css = STYLESHEET.read_text(encoding="utf-8")
    card = _css_block(css, ".scenario-stats-card")

    assert "width: 270px;" in card
    assert "padding: 0 var(--mantine-spacing-sm);" in card
    assert "flex: 0 0 auto;" in card
    assert "justify-content: center;" in card
    heading = _css_block(css, ".scenario-stats-card > .scenario-stats-heading")
    assert "font-size: 12px;" in heading
    assert "line-height: 18px;" in heading
    assert "color: var(--mantine-color-dimmed);" in heading


def test_the_pb_card_is_300px_at_the_first_columns_right_end():
    """Beside the latest-run card, after the scenario note card.

    Its frame adds only its border to its height, so the row stays the height
    the dropdowns' column sets in every state that changes between runs.
    """
    css = STYLESHEET.read_text(encoding="utf-8")
    card = _css_block(css, ".pb-card")

    assert "flex: 0 0 300px;" in card
    assert "margin-left: auto;" in card
    assert "padding: 0 var(--mantine-spacing-sm);" in card
    assert "justify-content: center;" in card
    assert "max-width: 100%;" in card
    # The age stays in its line: not a flex container, which drops spaces.
    assert "display" not in _css_block(css, ".pb-card-heading")
    # dmc's boxes round the score and Refresh add no line of their own.
    assert "display: flex;" in _css_block(css, ".pb-card-flex-target")
    # The score's last space reaches a screen reader and takes no room, its
    # line height included: the score's 33px would otherwise make the row
    # 12px taller, measured in Edge and Firefox.
    word_end = _css_block(css, ".pb-card-word-end")
    assert "font-size: 0;" in word_end
    assert "line-height: 0;" in word_end
    assert "white-space: pre;" in word_end


def test_the_pb_cards_quiet_lines_and_its_badge_use_the_themes_tokens():
    """The rank colors from the benchmark files are the only fixed colors."""
    css = STYLESHEET.read_text(encoding="utf-8")
    badge = _css_block(css, ".pb-card .pb-card-rank-badge")

    assert "color: var(--mantine-color-text);" in badge
    assert "border: 1px solid var(--pb-card-rank-color);" in badge
    assert (
        "background: color-mix(in srgb, var(--pb-card-rank-color) 20%, transparent);"
        in badge
    )
    assert "background: var(--pb-card-rank-color);" in _css_block(
        css, ".pb-card-rank-dot"
    )
    for quiet in (".pb-card-heading", ".pb-card-faded"):
        assert "color: var(--mantine-color-dimmed);" in _css_block(css, quiet)
    # With no PB the faded line is empty and out of the card.
    assert "display: none;" in _css_block(css, ".pb-card-faded:empty")
    # Its hidden attribute takes the leaderboard line out with no local PB,
    # which the line's own display would otherwise undo.
    assert "display: flex;" in _css_block(css, ".pb-card-leaderboard")
    assert "display: none;" in _css_block(css, ".pb-card-leaderboard[hidden]")


def test_the_cards_heading_is_one_line_and_cuts_a_long_scenario_name_short():
    css = STYLESHEET.read_text(encoding="utf-8")
    label = _css_block(css, ".run-history-card-label")
    scenario = _css_block(css, ".run-history-card-scenario")

    assert "display: flex;" in _css_block(css, ".run-history-card-heading")
    # The label is kept whole, with the space it ends on.
    assert "flex: 0 0 auto;" in label
    assert "white-space: pre;" in label
    # The run's age stays in the label's line, though dmc wraps it in a box.
    assert "display: inline;" in _css_block(css, ".run-history-card-time-target")
    assert "min-width: 0;" in scenario
    assert "text-overflow: ellipsis;" in scenario
    assert "white-space: nowrap;" in scenario


# --- The latest-run card ---------------------------------------------------------------


def _card_registration() -> dict:
    return _registration(f"{run_history.LATEST_RUN_CARD_IDS.body}.children")


def test_the_card_is_written_by_these_five_inputs_and_on_load():
    """The date among them: an older session's name leaves its year out only while it is this year's.

    The browser words the run's age, so the date is not read for that.
    """
    registration = _card_registration()
    card = run_history.LATEST_RUN_CARD_IDS

    assert registration["output"] == (
        f"..{card.played_at}.data...{card.heading}.children"
        f"...{card.body}.children...{run_history.LATEST_RUN_STORE_ID}.data.."
    )
    assert _keys(registration["inputs"]) == [
        f"{run_history.RUN_LANDED_STORE_ID}.data",
        f"{run_history.SCENARIO_SELECTION_IDS.scenario_dropdown}.value",
        f"{run_history.CHART_OPTIONS_IDS.score_threshold_percentage}.value",
        f"{run_history.SESSION_IN_PROGRESS_STORE_ID}.data",
        f"{run_history.TODAY_STORE_ID}.data",
    ]
    assert _keys(registration["state"]) == [f"{run_history.LATEST_RUN_STORE_ID}.data"]
    # The page load runs it, so the card is right with no new run.
    assert registration["prevent_initial_call"] is False


def test_the_cards_age_is_reworded_in_the_browser_on_the_30_second_tick():
    """As Last played is, so the age stays current on a page left open.

    The script words the run's end as an age, gives the hover the exact time
    in the shared format, and hides the first line's words with no run. It
    runs on the page load too, when the card's store is first written.
    """
    card = run_history.LATEST_RUN_CARD_IDS
    registration = _registration(f"{card.time}.children")
    interval = _by_id(run_history.layout(), run_history.RELATIVE_TIME_INTERVAL_ID)

    assert registration["clientside_function"] is not None
    assert registration["output"] == (
        f"..{card.label}.hidden...{card.time}.children...{card.time_tooltip}.label.."
    )
    assert _keys(registration["inputs"]) == [
        f"{card.played_at}.data",
        f"{run_history.RELATIVE_TIME_INTERVAL_ID}.n_intervals",
    ]
    assert registration["prevent_initial_call"] is False
    assert interval.interval == 30_000
    script = latest_run_card.AGE_SCRIPT
    assert "seconds === null || seconds === undefined" in script
    assert 'return [true, "", ""];' in script
    assert 'dagfuncs.relativeTime(seconds, "")' in script
    assert 'dagfuncs.absoluteTime(seconds, "")' in script


def test_the_card_is_not_written_by_the_charts_summary_store():
    """It is written for a run on any scenario, and the summary names only one."""
    inputs = _keys(_card_registration()["inputs"])

    assert f"{run_history.RUN_EVENTS_STORE_ID}.data" not in inputs
    assert "run-events-batch.data" not in inputs


def test_the_card_waits_for_the_selection_and_for_the_session_to_be_judged():
    """As the run list does, so the card is written once per batch.

    A batch writes the summary and the run's id in one answer. The selection
    callback is queued for the first and the session callback for the second,
    and the card takes an output of each as an input.
    """
    card_inputs = set(_keys(_card_registration()["inputs"]))
    delivery = _registration(f"{run_history.RUN_EVENTS_STORE_ID}.data")
    selection = _selection_registration()
    session = _registration(f"{run_history.SESSION_IN_PROGRESS_STORE_ID}.data")

    assert f"{run_history.RUN_LANDED_STORE_ID}.data" in delivery["output"]
    assert f"{run_history.RUN_EVENTS_STORE_ID}.data" in _keys(selection["inputs"])
    assert f"{run_history.RUN_LANDED_STORE_ID}.data" in _keys(session["inputs"])
    for writer in (selection, session):
        assert "@" not in writer["output"]
    assert {
        f"{run_history.SCENARIO_SELECTION_IDS.scenario_dropdown}.value",
        f"{run_history.SESSION_IN_PROGRESS_STORE_ID}.data",
    } <= card_inputs


def test_the_card_is_worked_out_from_the_run_store_for_the_selection(monkeypatch):
    asked = []
    shown = latest_run_card.LatestRun(
        run_id="selected.csv",
        scenario=SCENARIO,
        played_at=datetime(2026, 10, 12, 22, 49),
        score="812.4",
        badge=None,
        result="Accuracy 55.00%",
        session="Run 1 this session",
        time_on_scenario="4 min on this scenario",
    )

    def from_store(*arguments):
        asked.append(arguments)
        return latest_run_card.StoreRuns(shown, "landed.csv")

    monkeypatch.setattr(run_history, "latest_run_from_store", from_store)
    monkeypatch.setattr(run_history, "datetime", _clock_at(2026, 10, 12, 22, 50))

    answer = run_history.show_latest_run(
        "landed.csv", SCENARIO, 95, True, "2026-10-12", "held.csv"
    )

    # The batch only calls it: nothing of the run is read from the store that
    # names it.
    assert asked == [(SCENARIO, 95, datetime(2026, 10, 12, 22, 50))]
    played_at, heading, body, latest_run_id = answer
    assert played_at == datetime(2026, 10, 12, 22, 49).timestamp()
    assert rendered_text(heading) == SCENARIO
    assert [rendered_text(line) for line in body] == [
        "812.4",
        "Accuracy 55.00%",
        "Run 1 this session",
        "4 min on this scenario",
    ]
    # The ring's store names the newest run on any scenario, not the card's.
    assert latest_run_id == "landed.csv"
    # One value per output, in the outputs' order.
    assert len(answer) == len(_card_registration()["output"].split("..."))


@pytest.mark.parametrize(
    ("selected", "newest_run_id", "said"),
    [
        (
            None,
            None,
            [
                "No runs yet",
                "Play a scenario in KovaaK's. Select it to see its latest run.",
            ],
        ),
        (None, "a.csv", ["No scenario selected"]),
        (
            SCENARIO,
            "a.csv",
            [
                "No runs yet",
                "Play this scenario in KovaaK's and your latest run will show here.",
            ],
        ),
        (
            SCENARIO,
            None,
            [
                "No runs yet",
                "Play this scenario in KovaaK's and your latest run will show here.",
            ],
        ),
    ],
)
def test_with_no_run_to_report_the_card_says_why(
    monkeypatch, selected, newest_run_id, said
):
    """The selection decides first, then whether the store holds any run."""
    monkeypatch.setattr(
        run_history,
        "latest_run_from_store",
        lambda *_arguments: latest_run_card.StoreRuns(None, newest_run_id),
    )

    played_at, heading, body, _latest_run_id = run_history.show_latest_run(
        None, selected, 95, False, "2026-10-12", None
    )

    assert played_at is None
    assert heading is None
    assert [rendered_text(line) for line in body] == said


# --- The latest-run card, against a run store ------------------------------------------


def _record(scenario: str, ended: datetime, score: float = 100.0) -> RunData:
    """Build one stored run of 60 seconds that ended at ``ended``."""
    return RunData(
        datetime_object=ended,
        score=score,
        sens_scale="cm/360",
        horizontal_sens=40.8,
        scenario=scenario,
        accuracy=0.5,
        stats_file_name=f"{scenario} - Challenge - {ended:%Y.%m.%d-%H.%M.%S} Stats.csv",
        run_start=ended - timedelta(seconds=60),
        run_length=timedelta(seconds=60),
    )


class _Store:
    """The run store the card reads, which a test adds runs to."""

    def __init__(self, monkeypatch, *runs: RunData):
        self.runs = list(runs)
        monkeypatch.setattr(latest_run_card, "get_all_runs", lambda: list(self.runs))
        monkeypatch.setattr(
            latest_run_card, "get_version_pace_basis", lambda _scenario, _version: None
        )


def _card_at(monkeypatch, moment: datetime, selected, held_latest_run=None):
    """Call the card's callback as the page does at ``moment``.

    Returns what a reader sees in the card, the first line's scenario then
    every line under it, and the ring store's write.
    """
    monkeypatch.setattr(run_history, "datetime", _clock_at(*moment.timetuple()[:6]))
    _played_at, heading, body, latest_run_id = run_history.show_latest_run(
        None, selected, 95, True, moment.date().isoformat(), held_latest_run
    )
    return rendered_text(heading), [rendered_text(line) for line in body], latest_run_id


B_SCENARIO = "Scenario B"
EVENING = datetime(2026, 10, 12, 21, 0)


def test_a_change_of_scenario_rewrites_the_card_for_the_new_one(monkeypatch):
    _Store(
        monkeypatch,
        _record(SCENARIO, EVENING, score=80.0),
        _record(B_SCENARIO, EVENING + timedelta(minutes=5), score=612.5),
    )
    now = EVENING + timedelta(minutes=6)

    on_a = _card_at(monkeypatch, now, SCENARIO)
    on_b = _card_at(monkeypatch, now, B_SCENARIO)

    assert on_a[:2] == (
        SCENARIO,
        ["80", "Accuracy 50.00%", "Run 1 this session", "1 min on this scenario"],
    )
    assert on_b[0] == B_SCENARIO
    assert on_b[1][0] == "612.5"


def test_with_follow_off_a_run_on_another_scenario_moves_the_ring_and_not_the_card(
    monkeypatch,
):
    """The selection stays on A, so the card keeps A's run, and the ring leaves it."""
    store = _Store(monkeypatch, _record(SCENARIO, EVENING, score=80.0))
    before = _card_at(monkeypatch, EVENING + timedelta(minutes=1), SCENARIO)
    landed = _record(B_SCENARIO, EVENING + timedelta(minutes=5), score=612.5)
    store.runs.append(landed)

    after = _card_at(
        monkeypatch,
        EVENING + timedelta(minutes=6),
        SCENARIO,
        held_latest_run=before[2],
    )

    assert after[:2] == before[:2]
    assert after[2] == run_history_list.run_id(landed)
    assert before[2] == run_history_list.run_id(store.runs[0])


def test_a_run_that_starts_a_new_session_names_the_old_one(monkeypatch):
    """With Follow off, a run on another scenario can change the third line's words."""
    a_run = _record(SCENARIO, EVENING, score=80.0)
    store = _Store(monkeypatch, a_run)
    an_hour_on = EVENING + timedelta(hours=1)

    ended = _card_at(monkeypatch, an_hour_on, SCENARIO)
    store.runs.append(_record(B_SCENARIO, an_hour_on))
    named = _card_at(monkeypatch, an_hour_on + timedelta(minutes=1), SCENARIO)

    assert ended[1][2] == "Run 1 last session"
    assert named[1][2] == "Run 1 (Oct 12, 8:59 PM session)"


def test_the_date_moving_into_a_new_year_puts_the_year_in_an_older_sessions_name(
    monkeypatch,
):
    """With no run landing: the date store's write is what calls the card."""
    _Store(
        monkeypatch,
        _record(SCENARIO, datetime(2026, 12, 30, 21, 1)),
        _record(B_SCENARIO, datetime(2026, 12, 31, 9, 0)),
    )

    before = _card_at(monkeypatch, datetime(2026, 12, 31, 23, 59), SCENARIO)
    after = _card_at(monkeypatch, datetime(2027, 1, 1, 0, 0), SCENARIO)

    assert before[1][2] == "Run 1 (Dec 30, 9:00 PM session)"
    assert after[1][2] == "Run 1 (Dec 30, 2026, 9:00 PM session)"
    assert f"{run_history.TODAY_STORE_ID}.data" in _keys(_card_registration()["inputs"])


PLAYLIST_CODE = "KovaaKsPlaylistCode"


def _first_run_lands(monkeypatch, follow: bool, selected: str | None):
    """Land a first run, on B, in a store with no runs, as the page's callbacks do.

    A playlist filter lists A alone, which has never been played. The run is
    delivered, the selection callback runs if a summary was written, and the
    card is written for the scenario the page ends up on. Returns the card
    before and after, and the selection after.
    """
    monkeypatch.setattr(
        scenario_selection, "get_playlist_by_code", lambda code: object()
    )
    monkeypatch.setattr(
        scenario_selection, "get_scenarios_from_playlist_code", lambda code: [SCENARIO]
    )
    monkeypatch.setattr(
        scenario_selection, "is_scenario_in_database", lambda name: name == B_SCENARIO
    )
    store = _Store(monkeypatch)
    before = _card_at(monkeypatch, EVENING, selected)

    landed = _record(B_SCENARIO, EVENING + timedelta(minutes=1), score=612.5)
    store.runs.append(landed)
    summary, _landed_id = run_history.forward_run_events(
        _batch(_run(B_SCENARIO, run_id=run_history_list.run_id(landed))),
        follow,
        selected,
    )
    if summary is not no_update:
        _filter, moved_to, _waiting, _held = (
            scenario_selection.reach_the_scenario_asked_for(
                [
                    {
                        "prop_id": f"{run_history.RUN_EVENTS_STORE_ID}.data",
                        "value": summary,
                    }
                ],
                _SELECTION_PROPS,
                {},
                summary,
                None,
                None,
                follow,
                PLAYLIST_CODE if selected else None,
                selected,
                None,
                None,
                None,
            )
        )
        if moved_to is not no_update:
            selected = moved_to
    after = _card_at(monkeypatch, EVENING + timedelta(minutes=2), selected)
    return before, after, selected


@pytest.mark.parametrize("selected", [None, SCENARIO])
def test_with_follow_on_a_first_run_into_an_empty_store_shows_in_the_card(
    monkeypatch, selected
):
    """Its scenario is selected as it lands, so the card reports it."""
    before, after, now_selected = _first_run_lands(monkeypatch, True, selected)

    assert before[1][0] == "No runs yet"
    assert now_selected == B_SCENARIO
    assert after[0] == B_SCENARIO
    assert after[1][0] == "612.5"


@pytest.mark.parametrize(
    ("selected", "before_message", "after_lines"),
    [
        # Nothing selected: the sentence said to select the scenario played,
        # and the card now says no scenario is selected.
        (
            None,
            "Play a scenario in KovaaK's. Select it to see its latest run.",
            ["No scenario selected"],
        ),
        # A playlist's unplayed scenario selected: it is still unplayed.
        (
            SCENARIO,
            "Play this scenario in KovaaK's and your latest run will show here.",
            [
                "No runs yet",
                "Play this scenario in KovaaK's and your latest run will show here.",
            ],
        ),
    ],
)
def test_with_follow_off_a_first_run_into_an_empty_store_leaves_the_selection(
    monkeypatch, selected, before_message, after_lines
):
    before, after, now_selected = _first_run_lands(monkeypatch, False, selected)

    assert before[1] == ["No runs yet", before_message]
    assert now_selected == selected
    assert after[1] == after_lines
    # The ring's store still moves to the run.
    assert after[2] is not None


def test_the_card_starts_empty_and_the_page_load_fills_it():
    """Drawn empty: the layout knows neither the selection nor the percentage."""
    page = run_history.layout()
    card = run_history.LATEST_RUN_CARD_IDS

    assert _by_id(page, card.heading).children is None
    assert _by_id(page, card.body).children is None
    assert _by_id(page, card.body).children is None


def test_the_page_holds_no_scenario_button_and_no_script_to_hand_focus_on():
    """The card follows the selection, so it has no scenario of its own to offer.

    The button's keyboard focus script and the store it wrote went with it.
    """
    page = run_history.layout()

    assert not hasattr(run_history, "CARD_FOCUS_SINK_ID")
    assert not hasattr(run_history, "_HAND_FOCUS_TO_SCENARIO_SCRIPT")
    assert "run-history-card-focus-sink" not in _ids(page)
    assert "run-history-card-scenario-button" not in _ids(page)
    assert not [
        entry
        for entry in GLOBAL_CALLBACK_LIST
        if "run-history-card-scenario-button"
        in {dep["id"] for dep in entry["inputs"] + entry["state"]}
    ]


# --- The latest run's id, and the ring ------------------------------------------------


@pytest.mark.parametrize(
    ("held", "newest", "written"),
    [
        # Another run than the one held: on load, and when a run lands.
        (None, "a.csv", "a.csv"),
        ("a.csv", "b.csv", "b.csv"),
        # The same run: a change of scenario, of the percentage, of the
        # session's state, of the date.
        ("a.csv", "a.csv", no_update),
    ],
)
@pytest.mark.parametrize("selected", [SCENARIO, None])
def test_the_newest_runs_id_is_written_only_when_it_is_another_run(
    monkeypatch, held, newest, written, selected
):
    """The graph takes the store, so the same id again would restyle the chart.

    It is the newest run on any scenario, whatever the card reports, so it is
    written with no scenario selected too.
    """
    monkeypatch.setattr(
        run_history,
        "latest_run_from_store",
        lambda *_arguments: latest_run_card.StoreRuns(None, newest),
    )

    *_card, latest_run_id = run_history.show_latest_run(
        None, selected, 95, True, "2026-10-12", held
    )

    assert latest_run_id == written or latest_run_id is written


def test_a_run_store_emptied_of_runs_takes_the_held_id_away(monkeypatch):
    monkeypatch.setattr(
        run_history,
        "latest_run_from_store",
        lambda *_arguments: latest_run_card.StoreRuns(None, None),
    )

    *_card, latest_run_id = run_history.show_latest_run(
        None, SCENARIO, 95, False, "2026-10-12", "a.csv"
    )

    assert latest_run_id is None


def test_the_latest_run_store_starts_empty_and_the_page_load_fills_it():
    store = _by_id(run_history.layout(), run_history.LATEST_RUN_STORE_ID)

    assert run_history.LATEST_RUN_STORE_ID == "run-history-latest-run"
    assert isinstance(store, dcc.Store)
    assert getattr(store, "data", None) is None


def test_the_graph_takes_the_latest_run_and_waits_for_both_of_its_writers():
    """One writer of the figure, held for the chart and for the latest run.

    A run on the chart's own scenario writes a new figure and a new latest
    run. Dash holds a callback back for a queued writer of one of its
    inputs, so the graph is written once, after both. A run on another
    scenario writes only the latest run, which is what takes the ring off
    with no new figure.
    """
    options = run_history.CHART_OPTIONS_IDS
    graph = _registration(f"{options.graph}.figure")
    chart = _chart_registration()
    card = _card_registration()

    assert graph["output"] == f"{options.graph}.figure"
    assert _keys(graph["inputs"]) == [
        "color-scheme-switch.computedColorScheme",
        f"{options.cached_plot}.data",
        f"{options.point_size}.value",
        f"{options.point_color}.value",
        f"{run_history.LATEST_RUN_STORE_ID}.data",
    ]
    assert graph["state"] == []
    assert chart["output"] == f"{options.cached_plot}.data"
    assert card["output"].endswith(f"...{run_history.LATEST_RUN_STORE_ID}.data..")
    # Neither write is a duplicate one, which Dash would not hold the graph
    # back for.
    assert f"{options.cached_plot}.data@" not in chart["output"]
    assert "@" not in card["output"]
    # The chart is still not rebuilt for a run on another scenario.
    assert f"{run_history.LATEST_RUN_STORE_ID}.data" not in _keys(chart["inputs"])
    assert f"{run_history.RUN_LANDED_STORE_ID}.data" not in _keys(chart["inputs"])


def test_the_graphs_figure_has_exactly_one_writer_which_takes_the_latest_run():
    """One callback, and not one for the figure and one for the ring.

    Dash holds a callback back for a queued writer of one of its inputs, so
    a run on the chart's own scenario writes the graph once, after both the
    new figure and the new latest run are in. Two writers would write it
    twice.
    """
    options = run_history.CHART_OPTIONS_IDS
    writers = [key for key in GLOBAL_CALLBACK_MAP if f"{options.graph}.figure" in key]

    assert writers == [f"{options.graph}.figure"]
    (graph,) = (GLOBAL_CALLBACK_MAP[key] for key in writers)
    assert graph["callback"].__name__ == "ring_latest_run_on_graph"
    assert run_history.LATEST_RUN_STORE_ID in [entry["id"] for entry in graph["inputs"]]
    # No graph anywhere is styled by a callback that never hears of the
    # latest run.
    assert "apply_graph_appearance" not in {
        getattr(spec.get("callback"), "__name__", None)
        for spec in GLOBAL_CALLBACK_MAP.values()
    }
