"""The Home page: its name and addresses, and what its layout holds.

Home is the page the app opens on. It shows the stats-folder hint and the
setup card when they apply, then one line that says how many runs the app
found. These tests hold the registration, the two intervals the queued
notices are delivered on, the stats line in each state, and that the page has
no control and reads no query parameter. The card is
``tests/test_home_setup_card.py`` and the hint is
``tests/test_home_stats_dir_hint.py``.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import dash
import dash_mantine_components as dmc
import pytest
from dash import dcc
from dash._callback import GLOBAL_CALLBACK_LIST, GLOBAL_CALLBACK_MAP
from plotly.utils import PlotlyJSONEncoder

from source.components import setup_surfaces
from source.config import settings_service
from source.kovaaks.data_models import ScenarioStats
from source.utilities.paths import STATE_DIR_ENV_VAR

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
STATS_DIR_KEY = settings_service.STATS_DIR_KEY
USERNAME_KEY = settings_service.KOVAAKS_USERNAME_KEY
# Some of the ids of the page that was served at this address before Home:
# its dropdowns, its switches and inputs, its graph, and its stores.
REPLACED_PAGE_IDS = {
    "playlist-dropdown-selection",
    "scenario-dropdown-selection",
    "automatically-change-scenario-switch",
    "top_n_scores",
    "date-picker",
    "x-axis-radiogroup",
    "graph-content",
    "cached-plot",
    "chart-options-panel",
    "chart-options-toggle",
    "scenario_num_runs",
    "scenario_rank",
    "run-events",
    "home-deep-link",
    "interval-component",
    "startup-playlist-warning-interval",
    "relative-time-interval",
}
# The kinds of component Home holds none of: a graph, a store, a modal, and
# an input of any kind.
ABSENT_COMPONENT_TYPES = (
    dcc.Graph,
    dcc.Store,
    dmc.Modal,
    dmc.Select,
    dmc.Switch,
    dmc.NumberInput,
    dmc.DatePickerInput,
    dmc.RadioGroup,
    dmc.SegmentedControl,
    dmc.ColorInput,
)


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


def _ids(page) -> set[str]:
    return {
        component.id
        for component in _walk_components(page)
        if isinstance(getattr(component, "id", None), str)
    }


def _store(**values):
    """Save exactly these keys and pin the directory the way startup would."""
    settings_service.save_settings(values)
    settings_service.resolve_stats_dir()


def _configured(stats_dir: Path):
    """Store a usable stats folder and an account, so neither surface shows."""
    _store(**{STATS_DIR_KEY: str(stats_dir), USERNAME_KEY: "MingoDynasty"})


def _found(monkeypatch, *runs_per_scenario: int) -> None:
    """Fill the run store's stats with one scenario per count given."""
    stats = {
        f"Scenario {index}": ScenarioStats(
            date_last_played=datetime(2026, 10, 12, 22, 50),
            number_of_runs=runs,
            high_score=100.0,
        )
        for index, runs in enumerate(runs_per_scenario)
    }
    monkeypatch.setattr(home, "get_scenario_stats_snapshot", lambda: stats)


@pytest.fixture
def stats_dir():
    """The fixture stats folder, the same one a real startup would pin."""
    return Path(__file__).resolve().parent / "fixtures" / "stats"


# --- The registration --------------------------------------------------------


def test_the_page_is_named_home_and_owns_the_landing_address():
    page = dash.page_registry["source.pages.home"]

    assert page["path"] == "/"
    assert page["name"] == "Home"
    # Registered as a callable so the optional build-label prefix can be read
    # per request; unprefixed here because the flag defaults off.
    assert page["title"]() == "Home"


# Run in a child process. Dash keeps nothing under ``redirect_from`` in the
# page registry: it adds the redirects as URL rules to whichever app is
# current when the page module is first imported, and in a test run that is
# the app of whichever test module imported the page first.
REDIRECTS_SNIPPET = """
import json

import dash

app = dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home

answers = {}
for address in ("/home", "/index"):
    with app.server.test_request_context(address):
        response = app.server.view_functions[address]()
    answers[address] = [response.status_code, response.headers["Location"]]
print(json.dumps(answers))
"""


def test_the_two_old_addresses_of_the_landing_page_redirect_to_it(tmp_path):
    """``/home`` and ``/index`` have always led to ``/``, and still do."""
    environment = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    environment.pop(STATE_DIR_ENV_VAR, None)

    child = subprocess.run(
        [sys.executable, "-c", REDIRECTS_SNIPPET],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    assert child.returncode == 0, child.stderr
    answers = json.loads(child.stdout.splitlines()[-1])
    assert set(answers) == {"/home", "/index"}
    for status, location in answers.values():
        assert 300 <= status < 400
        assert location == "/"


# --- The layout ---------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        {"scenario": "Scenario A"},
        {"playlist_code": "KovaaKsTestCode"},
        {"scenario": "Scenario A", "playlist_code": "KovaaKsTestCode"},
        {"run": "2026.10.12-22.50.00"},
    ],
    ids=["scenario", "playlist_code", "both", "unknown"],
)
def test_the_layout_takes_every_query_parameter_and_reads_none(monkeypatch, query):
    """A link written for the page once served here draws Home, and selects nothing.

    Dash refuses a query parameter a layout does not take, so an old
    ``/?scenario=`` link would otherwise fail to draw anything.
    """
    _found(monkeypatch, 3, 1)

    def drawn(**parameters) -> str:
        return json.dumps(
            home.layout(**parameters), cls=PlotlyJSONEncoder, sort_keys=True
        )

    assert drawn(**query) == drawn()


def test_home_holds_no_control_and_none_of_the_replaced_pages_ids(monkeypatch):
    _found(monkeypatch, 3, 1)

    page = home.layout()

    assert not _ids(page) & REPLACED_PAGE_IDS
    assert not [
        component
        for component in _walk_components(page)
        if isinstance(component, ABSENT_COMPONENT_TYPES)
    ]


def test_home_never_pops_the_run_event_queue():
    # One consumer, in the shell. A second drain here is the race the design
    # closed by construction.
    assert not hasattr(home, "message_queue")


# --- The intervals the queued notices are delivered on -------------------------


def test_home_ticks_once_shortly_after_it_mounts_and_then_at_the_polling_rate():
    page = home.layout()

    once = _by_id(page, home.STARTUP_PLAYLIST_WARNING_INTERVAL_ID)
    polling = _by_id(page, home.POLLING_INTERVAL_ID)
    assert (home.STARTUP_PLAYLIST_WARNING_INTERVAL_ID, home.POLLING_INTERVAL_ID) == (
        "home-startup-playlist-warning-interval",
        "home-polling-interval",
    )
    assert isinstance(once, dcc.Interval)
    assert (once.interval, once.max_intervals, once.n_intervals) == (250, 1, 0)
    assert isinstance(polling, dcc.Interval)
    # The polling interval the test configuration sets.
    assert (polling.interval, polling.n_intervals) == (1000, 0)
    assert getattr(polling, "max_intervals", None) is None


def test_nothing_but_the_two_queued_notice_flushes_reads_homes_intervals():
    """Home polls for nothing of its own: each interval delivers one queue."""

    def readers(interval_id: str) -> list[str | None]:
        return [
            getattr(
                GLOBAL_CALLBACK_MAP[entry["output"]].get("callback"), "__name__", None
            )
            for entry in GLOBAL_CALLBACK_LIST
            if interval_id in {dep["id"] for dep in entry["inputs"] + entry["state"]}
        ]

    assert readers(home.POLLING_INTERVAL_ID) == ["flush_run_import_failures"]
    assert readers(home.STARTUP_PLAYLIST_WARNING_INTERVAL_ID) == [
        "flush_startup_playlist_warnings"
    ]


# --- The stats line ------------------------------------------------------------


@pytest.mark.parametrize(
    ("runs_per_scenario", "line"),
    [
        ([10] * 1000, "Found 10,000 runs across 1,000 scenarios in your stats folder."),
        ([1], "Found 1 run across 1 scenario in your stats folder."),
        ([7], "Found 7 runs across 1 scenario in your stats folder."),
        ([1, 1], "Found 2 runs across 2 scenarios in your stats folder."),
    ],
    ids=["many", "one_run", "one_scenario", "one_run_each"],
)
def test_the_stats_line_counts_the_runs_and_the_scenarios_the_app_found(
    monkeypatch, runs_per_scenario, line
):
    _found(monkeypatch, *runs_per_scenario)

    stats_line = _by_id(home.layout(), home.STATS_LINE_ID)

    assert isinstance(stats_line, dmc.Text)
    assert stats_line.children == line


def test_a_stats_folder_with_no_runs_in_it_says_what_to_do(monkeypatch):
    _found(monkeypatch)

    stats_line = _by_id(home.layout(), home.STATS_LINE_ID)

    assert home.NO_RUNS_FOUND_MESSAGE == (
        "No runs found in your stats folder yet. Play a scenario in KovaaK's and "
        "your runs will appear in Run History."
    )
    assert isinstance(stats_line, dmc.Text)
    assert stats_line.children == home.NO_RUNS_FOUND_MESSAGE


@pytest.mark.parametrize(
    "stored",
    [{}, {STATS_DIR_KEY: ""}, {STATS_DIR_KEY: "no-such-stats-dir"}],
    ids=["never_set", "emptied", "vanished"],
)
def test_there_is_no_stats_line_without_a_usable_stats_folder(monkeypatch, stored):
    """The hint and the card already say why the app has no runs.

    A count beside them would read as a second problem, so none is drawn
    even when the run store holds runs.
    """
    _store(**stored)
    _found(monkeypatch, 3, 1)

    page = home.layout()

    assert _by_id(page, home.STATS_LINE_ID) is None
    assert home.stats_line() == []


def _shown_in_order(page) -> list[str]:
    """List the hint, the card's container and the stats line as the page stacks them."""
    surfaces = {home.STATS_DIR_HINT_ID, home.SETUP_CARD_ID, home.STATS_LINE_ID}
    return [
        child.id for child in page.children if getattr(child, "id", None) in surfaces
    ]


def test_the_page_stacks_the_hint_then_the_card_then_the_stats_line(
    monkeypatch, stats_dir
):
    """The hint and the stats line never show together, so two states hold the order.

    The hint speaks only without a usable stats folder, and the line only
    with one. The card's container is in the layout in both.
    """
    _found(monkeypatch, 3, 1)

    _store(**{STATS_DIR_KEY: "no-such-stats-dir"})
    without_a_folder = home.layout()
    _store(**{STATS_DIR_KEY: str(stats_dir)})
    with_a_folder = home.layout()

    assert _shown_in_order(without_a_folder) == [
        home.STATS_DIR_HINT_ID,
        home.SETUP_CARD_ID,
    ]
    assert _shown_in_order(with_a_folder) == [home.SETUP_CARD_ID, home.STATS_LINE_ID]
    # The account offer is drawn in both, so the card is not an empty box
    # the order is read past.
    for page in (without_a_folder, with_a_folder):
        assert _by_id(page, home.SETUP_CARD_ID).children != []


# --- Links ---------------------------------------------------------------------


def _hrefs(page) -> set[str]:
    return {
        component.href
        for component in _walk_components(page)
        if getattr(component, "href", None) is not None
    }


@pytest.mark.parametrize(
    "stored",
    [
        {},
        {STATS_DIR_KEY: ""},
        {STATS_DIR_KEY: "no-such-stats-dir"},
        {STATS_DIR_KEY: "no-such-stats-dir", USERNAME_KEY: ""},
    ],
    ids=["never_set", "emptied", "vanished", "vanished_and_account_declined"],
)
def test_every_link_on_home_leads_to_settings(stored):
    """Home forwards nowhere: the navbar is the way to every other page."""
    _store(**stored)

    assert _hrefs(home.layout()) == {"/settings"}


def test_the_account_offer_links_to_settings_and_nowhere_else(monkeypatch, stats_dir):
    _store(**{STATS_DIR_KEY: str(stats_dir)})
    _found(monkeypatch, 3, 1)

    page = home.layout()

    card = _by_id(page, home.SETUP_CARD_ID).children[0]
    assert setup_surfaces.SETUP_CARD_IDENTITY_TITLE in [
        component.children
        for component in _walk_components(card)
        if isinstance(component, dmc.Text)
    ]
    assert _hrefs(page) == {"/settings"}


@pytest.mark.parametrize("runs_per_scenario", [(), (3, 1)], ids=["no_runs", "runs"])
def test_a_configured_install_draws_no_link_at_all(
    monkeypatch, stats_dir, runs_per_scenario
):
    """The line that names Run History names it in plain text."""
    _configured(stats_dir)
    _found(monkeypatch, *runs_per_scenario)

    page = home.layout()

    assert _by_id(page, home.STATS_LINE_ID) is not None
    assert _hrefs(page) == set()
