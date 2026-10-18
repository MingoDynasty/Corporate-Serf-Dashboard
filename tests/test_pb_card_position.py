"""The PB card's leaderboard line on the Run History page: the Position field, moved.

The callbacks live in ``source/components/pb_card.py`` and take their ids
from the page that hosts them. These tests hold the line's value with its
hints and its hover, the Steam ID mismatch toast, each answer a click on
Refresh can give, and the card's registration. The ones that read a layout or
a registration read the page's own. What the rest of the card shows is
``tests/test_pb_card.py``.
"""

import os
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import dash
import dash_mantine_components as dmc
import pytest
import requests
from dash import dcc, html, no_update
from dash._callback import (
    GLOBAL_CALLBACK_LIST,
    GLOBAL_CALLBACK_MAP,
    GLOBAL_INLINE_SCRIPTS,
)

from source.components import chart_options, pb_card, scenario_selection
from source.config import settings_service
from source.kovaaks import api_service
from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import run_history  # noqa: E402

IDS = run_history.PB_CARD_IDS

format_scenario_rank = pb_card.format_scenario_rank
PositionShown = pb_card.PositionShown


@pytest.fixture(autouse=True)
def _forget_rank_hints():
    """Keep the cross-tick hint memo from leaking between tests."""
    pb_card._last_rank_hints.clear()
    yield
    pb_card._last_rank_hints.clear()


@pytest.fixture(autouse=True)
def _forget_session_notices():
    """Give each test a fresh app session's worth of once-per-session toasts."""
    pb_card._session_notices_sent.clear()
    yield
    pb_card._session_notices_sent.clear()


@pytest.fixture(autouse=True)
def _every_scenario_has_local_runs(monkeypatch):
    """Give the line a local PB to sit under, as every test here but one needs."""
    monkeypatch.setattr(pb_card, "is_scenario_in_database", lambda _scenario: True)


def _render(*args, **kwargs):
    """Render the line, as (value, when it was stored, the toasts it earned)."""
    outputs, notifications = pb_card._render_scenario_rank(*args, **kwargs)
    return outputs.value, outputs.updated_ts, notifications


def _rendered_rank(*args, **kwargs):
    """Render the line's value, discarding any toast the render earned."""
    return _render(*args, **kwargs)[0]


class _RefreshClient:
    """One browser clicking Refresh, carrying the shell's channel registry."""

    def __init__(self) -> None:
        self.toast_channels: dict[str, str | None] = {}
        self.clicks = 0
        self.updated_ts = None
        self.label_hidden = None
        self.of_total = None

    def click(self, scenario: str | None):
        """Return this click's (display, shown payloads, hidden ids)."""
        self.clicks += 1
        (
            display,
            self.label_hidden,
            self.updated_ts,
            self.of_total,
            shown,
            hidden,
            patch,
        ) = pb_card.refresh_rank(self.clicks, scenario, self.toast_channels)
        self.toast_channels.update(_registry_writes(patch))
        return display, shown, hidden


def _registry_writes(patch) -> dict[str, str | None]:
    """Read a per-key ``dash.Patch`` as the assignments it will apply."""
    if patch is no_update:
        return {}
    return {
        operation["location"][0]: operation["params"]["value"]
        for operation in patch._operations
    }


def _rank_text(rendered) -> str:
    """Flatten a rendered Position value into the text a reader would see."""
    if isinstance(rendered, str):
        return rendered
    return "".join(
        component
        for child in rendered
        for component in _walk_components(child)
        if isinstance(component, str)
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


def test_rank_refresh_button_has_tooltip(monkeypatch):
    monkeypatch.setattr(
        scenario_selection, "get_visible_playlist_selector_options", lambda: []
    )
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])

    tooltips = [
        component
        for component in _walk_components(run_history.layout())
        if isinstance(component, dmc.Tooltip)
        and any(
            getattr(child, "id", None) == IDS.rank_refresh_button
            for child in _walk_components(component.children)
        )
    ]

    assert len(tooltips) == 1
    assert tooltips[0].label == pb_card.RANK_REFRESH_TOOLTIP
    assert tooltips[0].events == chart_options.TOOLTIP_EVENTS
    assert tooltips[0].withArrow is True
    assert tooltips[0].multiline is True


def test_the_percentile_leads_the_line_and_the_position_moves_to_its_hover():
    rank_info = ScenarioRankInfo(
        status=ScenarioRankStatus.RANKED,
        rank=11266,
        total_players=18342,
        percentile=38.58,
    )

    assert format_scenario_rank(rank_info) == PositionShown(
        "38.58% percentile", "Position 11,266 of 18,342"
    )


@pytest.mark.parametrize(
    ("rank_info", "value"),
    [
        pytest.param(
            ScenarioRankInfo(
                status=ScenarioRankStatus.RANKED, rank=11266, total_players=18342
            ),
            "11,266 of 18,342",
            id="a-total-and-no-percentile",
        ),
        pytest.param(
            ScenarioRankInfo(status=ScenarioRankStatus.RANKED, rank=11266),
            "11,266",
            id="no-total",
        ),
        pytest.param(
            ScenarioRankInfo(status=ScenarioRankStatus.UNRANKED, total_players=63870),
            "Unranked (63,870 players)",
            id="unranked-with-a-total",
        ),
        pytest.param(
            ScenarioRankInfo(status=ScenarioRankStatus.UNRANKED),
            "Unranked",
            id="unranked",
        ),
        pytest.param(
            ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN), "N/A", id="unknown"
        ),
        pytest.param(
            ScenarioRankInfo(status=ScenarioRankStatus.RANKED), "N/A", id="no-rank"
        ),
    ],
)
def test_without_a_percentile_the_line_reads_as_the_position_field_did(
    rank_info, value
):
    """After the ``Position:`` label, which shows wherever there is no hover line."""
    assert format_scenario_rank(rank_info) == PositionShown(value, None)


def test_a_rank_past_a_stale_total_shows_both_numbers_without_a_percentile():
    rank_info = api_service._with_percentile(
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            leaderboard_id=98330,
            scenario_name="Some Scenario",
            rank=900,
            total_players=500,
        )
    )

    assert format_scenario_rank(rank_info) == PositionShown("900 of 500", None)


@pytest.mark.parametrize(
    ("rank_info", "label_hidden", "of_total"),
    [
        pytest.param(
            ScenarioRankInfo(
                status=ScenarioRankStatus.RANKED,
                rank=5400,
                total_players=28614,
                percentile=81.13,
            ),
            True,
            "Position 5,400 of 28,614",
            id="a-percentile",
        ),
        pytest.param(
            ScenarioRankInfo(status=ScenarioRankStatus.UNRANKED, total_players=12345),
            False,
            None,
            id="unranked",
        ),
    ],
)
def test_the_label_shows_wherever_the_percentile_does_not_lead(
    monkeypatch, rank_info, label_hidden, of_total
):
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    monkeypatch.setattr(pb_card, "get_scenario_rank_info", lambda *_a, **_k: rank_info)

    outputs, _notifications = pb_card._render_scenario_rank("Scenario", True)

    assert (outputs.label_hidden, outputs.of_total) == (label_hidden, of_total)


def test_a_scenario_with_no_local_runs_is_never_looked_up(monkeypatch):
    """The card shows no leaderboard line without a local PB, so nothing asks.

    Until the line moved into the PB card, the Position field looked a
    scenario with no local runs up as well.
    """
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    monkeypatch.setattr(pb_card, "is_scenario_in_database", lambda _scenario: False)
    monkeypatch.setattr(
        pb_card,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: pytest.fail("no local PB, so no lookup"),
    )
    monkeypatch.setattr(
        pb_card, "ctx", SimpleNamespace(triggered=[{"prop_id": "x.value"}])
    )

    for allow_network in (True, False):
        assert _render("Unplayed Scenario", allow_network) == ("N/A", None, [])
    assert pb_card.get_scenario_rank(None, "Unplayed Scenario", 0) == (
        "N/A",
        False,
        None,
        None,
        no_update,
    )
    assert pb_card.refresh_rank(1, "Unplayed Scenario", {}) == (
        "N/A",
        False,
        None,
        None,
        no_update,
        no_update,
        no_update,
    )


def test_rank_trigger_classification_preserves_initial_and_cofired_network_reads():
    interval = {"prop_id": f"{IDS.polling_interval}.n_intervals"}
    new_runs = {"prop_id": f"{IDS.run_events}.data"}

    assert pb_card._rank_allows_network([{"prop_id": "."}]) is True
    assert pb_card._rank_allows_network([interval]) is False
    assert pb_card._rank_allows_network([new_runs]) is True
    assert (
        pb_card._rank_allows_network(
            [
                interval,
                {"prop_id": f"{IDS.scenario_dropdown}.value"},
            ]
        )
        is True
    )


def test_rank_render_records_only_interactive_activity(monkeypatch, tmp_path):
    scenario_name = "Cached Scenario"
    leaderboard_id = 98330
    username = "MingoDynasty"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    settings_service.save_settings({"kovaaks_username": username})
    api_service.make_cache()
    api_service.save_leaderboard_id(scenario_name, leaderboard_id, "test")
    api_service.save_scenario_rank(
        leaderboard_id,
        username,
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=10,
            leaderboard_id=leaderboard_id,
            scenario_name=scenario_name,
            score=100.0,
        ),
    )
    api_service.save_leaderboard_total(leaderboard_id, 100)
    monkeypatch.setattr(api_service, "_last_interactive_activity", 10.0)

    assert _rendered_rank(scenario_name, allow_network=False) == "90.50% percentile"
    interval_activity, _network_success = api_service.get_api_activity_timestamps()
    assert interval_activity == 10.0

    assert _rendered_rank(scenario_name, allow_network=True) == "90.50% percentile"
    interactive_activity, _network_success = api_service.get_api_activity_timestamps()
    assert interactive_activity > interval_activity


@pytest.mark.parametrize(
    ("total_state", "expected"),
    [
        ("missing", "10"),
        ("expired", "90.50% percentile"),
    ],
)
def test_interval_rank_render_is_ttl_independent_and_never_fetches(
    monkeypatch,
    tmp_path,
    total_state,
    expected,
):
    scenario_name = "Cached Scenario"
    leaderboard_id = 98330
    username = "MingoDynasty"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    settings_service.save_settings({"kovaaks_username": username})
    api_service.make_cache()
    api_service.save_leaderboard_id(scenario_name, leaderboard_id, "test")
    api_service.save_scenario_rank(
        leaderboard_id,
        username,
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=10,
            leaderboard_id=leaderboard_id,
            scenario_name=scenario_name,
            score=100.0,
        ),
    )
    rank_cache_file = api_service._rank_cache_file(leaderboard_id, username)
    os.utime(rank_cache_file, (1, 1))

    if total_state == "expired":
        api_service.save_leaderboard_total(leaderboard_id, 100)
        total_cache_file = api_service._leaderboard_total_cache_file(leaderboard_id)
        os.utime(total_cache_file, (1, 1))

    def fail_network(*_args, **_kwargs):
        raise AssertionError("interval rank reads must not use the network")

    monkeypatch.setattr(api_service, "_session_get", fail_network)

    assert _rendered_rank(scenario_name, allow_network=False) == expected


def test_interval_rank_render_does_not_fetch_or_cache_unresolved_scenario(
    monkeypatch,
    tmp_path,
):
    scenario_name = "Local Custom Scenario"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    api_service.make_cache()

    def fail_network(*_args, **_kwargs):
        raise AssertionError("unresolved interval rank reads must not use the network")

    monkeypatch.setattr(api_service, "_session_get", fail_network)

    rendered = _rendered_rank(scenario_name, allow_network=False)
    assert _rank_text(rendered) == "N/A · lookup failed"
    assert api_service.get_cached_leaderboard_id(scenario_name) is None


def test_allow_network_false_short_circuits_resolution_and_rank_fetch(monkeypatch):
    cached_lookups = []

    def get_cached(scenario_name):
        cached_lookups.append(scenario_name)

    def fail_network_path(*_args, **_kwargs):
        raise AssertionError("cache-only lookup reached a network path")

    monkeypatch.setattr(api_service, "get_cached_leaderboard_id", get_cached)
    monkeypatch.setattr(
        api_service,
        "hydrate_leaderboard_id_cache",
        fail_network_path,
    )
    monkeypatch.setattr(api_service, "search_scenario_exact", fail_network_path)
    monkeypatch.setattr(api_service, "fetch_scenario_rank", fail_network_path)

    rank_info = api_service.get_scenario_rank_info(
        "Unresolved Scenario",
        "MingoDynasty",
        allow_network=False,
    )

    assert rank_info.status == ScenarioRankStatus.UNKNOWN
    assert cached_lookups == ["Unresolved Scenario"]


def _seed_mismatched_rank_cache(monkeypatch, tmp_path) -> str:
    """Cache a ranked position that matched a different Steam account."""
    scenario_name = "Cached Scenario"
    leaderboard_id = 98330
    username = "MingoDynasty"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    settings_service.save_settings(
        {"kovaaks_username": username, "steam_id": "configured-steam-id"}
    )
    api_service.make_cache()
    api_service.save_leaderboard_id(scenario_name, leaderboard_id, "test")
    api_service.save_scenario_rank(
        leaderboard_id,
        username,
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=10,
            leaderboard_id=leaderboard_id,
            scenario_name=scenario_name,
            score=100.0,
            matched_steam_id="different-steam-id",
        ),
    )
    api_service.save_leaderboard_total(leaderboard_id, 100)
    return scenario_name


def test_passive_rank_render_reports_a_steam_id_mismatch_once_per_session(
    monkeypatch,
    tmp_path,
):
    # The mismatch is the one persistent condition with no in-place home, so
    # it toasts -- but once for the session, not once per scenario switch.
    scenario_name = _seed_mismatched_rank_cache(monkeypatch, tmp_path)

    display, _updated_ts, notifications = _render(
        scenario_name,
        allow_network=True,
    )

    assert display == "90.50% percentile"
    assert len(notifications) == 1
    assert notifications[0]["title"] == "Steam ID mismatch"
    assert notifications[0]["color"] == "yellow"
    assert notifications[0]["id"] == "steam-id-mismatch"
    assert "different-steam-id" in notifications[0]["message"]

    for allow_network in (False, True):
        assert _render(
            scenario_name,
            allow_network=allow_network,
        ) == (display, None, [])


def test_steam_id_mismatch_toast_persists_until_dismissed(monkeypatch, tmp_path):
    # It can fire while nobody is looking at the page, so it must not expire.
    scenario_name = _seed_mismatched_rank_cache(monkeypatch, tmp_path)

    _display, _updated_ts, notifications = _render(
        scenario_name,
        allow_network=True,
    )

    assert notifications[0]["autoClose"] is False


def test_matching_steam_id_never_toasts(monkeypatch, tmp_path):
    scenario_name = _seed_mismatched_rank_cache(monkeypatch, tmp_path)
    settings_service.save_settings(
        {"kovaaks_username": "MingoDynasty", "steam_id": "different-steam-id"}
    )

    _display, _updated_ts, notifications = _render(
        scenario_name,
        allow_network=True,
    )

    assert notifications == []


def test_a_rank_render_nobody_triggered_keeps_the_sessions_mismatch_toast(
    monkeypatch,
    tmp_path,
):
    # Under DashProxy an allow_duplicate callback can fire once on page load
    # with an empty trigger list. The value still renders, but the session's
    # one mismatch toast must survive for a render the user actually caused.
    scenario_name = _seed_mismatched_rank_cache(monkeypatch, tmp_path)
    monkeypatch.setattr(pb_card, "ctx", SimpleNamespace(triggered=[]))

    display, _label_hidden, _updated_ts, _of_total, notifications = (
        pb_card.get_scenario_rank(None, scenario_name, 0)
    )

    assert display == "90.50% percentile"
    assert notifications is no_update

    monkeypatch.setattr(
        pb_card,
        "ctx",
        SimpleNamespace(triggered=[{"prop_id": f"{IDS.scenario_dropdown}.value"}]),
    )
    _display, _label_hidden, _updated_ts, _of_total, notifications = (
        pb_card.get_scenario_rank(None, scenario_name, 0)
    )

    assert [notification["id"] for notification in notifications] == [
        "steam-id-mismatch"
    ]


def test_rank_render_without_notifications_reports_no_update(monkeypatch, tmp_path):
    scenario_name = _seed_mismatched_rank_cache(monkeypatch, tmp_path)
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    monkeypatch.setattr(
        pb_card,
        "ctx",
        SimpleNamespace(triggered=[{"prop_id": f"{IDS.scenario_dropdown}.value"}]),
    )

    _display, _label_hidden, _updated_ts, _of_total, notifications = (
        pb_card.get_scenario_rank(None, scenario_name, 0)
    )

    assert notifications is no_update


def test_passive_rank_render_points_an_unset_username_at_settings():
    # The fixture store leaves identity unset -- the fresh-install default.
    rendered, _updated_ts, notifications = _render(
        "Scenario",
        allow_network=True,
    )

    assert _rank_text(rendered) == "N/A · set your KovaaK's username in Settings"
    anchors = [
        component
        for child in rendered
        for component in _walk_components(child)
        if isinstance(component, dmc.Anchor)
    ]
    assert [anchor.href for anchor in anchors] == ["/settings"]
    assert notifications == []


def test_passive_rank_render_offers_refresh_when_the_lookup_failed(monkeypatch):
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    monkeypatch.setattr(
        pb_card,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            error_message="Failed to fetch leaderboard position for Scenario.",
        ),
    )

    rendered, _updated_ts, notifications = _render(
        "Scenario",
        allow_network=True,
    )

    assert _rank_text(rendered) == "N/A · lookup failed"
    assert notifications == []


def test_passive_rank_render_marks_a_stale_cached_position(monkeypatch):
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    monkeypatch.setattr(
        pb_card,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=1240,
            served_stale=True,
            warning_message="Couldn't refresh from KovaaK's; showing the last "
            "cached position for Scenario.",
        ),
    )

    rendered, _updated_ts, notifications = _render(
        "Scenario",
        allow_network=True,
    )

    assert _rank_text(rendered) == "1,240 · from cache"
    assert notifications == []


def test_stale_affordance_survives_the_cache_only_interval_tick(monkeypatch):
    # The interval re-reads the same rank from cache, where the served-stale
    # marker is gone; the hint must not blink off a tick after it appears.
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})

    def rank_for(*_args, **kwargs):
        return ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=1240,
            served_stale=True if kwargs["allow_network"] else None,
        )

    monkeypatch.setattr(pb_card, "get_scenario_rank_info", rank_for)

    assert (
        _rank_text(_rendered_rank("Scenario", allow_network=True))
        == "1,240 · from cache"
    )
    assert (
        _rank_text(_rendered_rank("Scenario", allow_network=False))
        == "1,240 · from cache"
    )


@pytest.mark.parametrize(
    ("hint", "stale_value"),
    [
        (pb_card._RANK_HINT_SERVED_STALE, "1,240"),
        (pb_card._RANK_HINT_LOOKUP_FAILED, "N/A"),
    ],
)
def test_a_background_cache_write_retires_the_memoized_hint(
    monkeypatch,
    hint,
    stale_value,
):
    # The warmup worker and the score-aware refresh Timer both write the rank
    # cache off a background thread. Once the interval reads a value the last
    # network verdict was never about, that verdict must not keep claiming the
    # lookup failed over a position that has since arrived.
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    pb_card._last_rank_hints["Scenario"] = (PositionShown(stale_value, None), hint)
    monkeypatch.setattr(
        pb_card,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=1180,
        ),
    )

    assert _rendered_rank("Scenario", allow_network=False) == "1,180"
    assert "Scenario" not in pb_card._last_rank_hints


def test_a_background_write_that_moves_only_the_hover_retires_the_hint(monkeypatch):
    """The line can show the same percentile over another position and total.

    The memo is tied to the hover's first line too, so a position that moved
    under an unchanged percentile still retires the verdict.
    """
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    pb_card._last_rank_hints["Scenario"] = (
        PositionShown("81.13% percentile", "Position 5,400 of 28,614"),
        pb_card._RANK_HINT_SERVED_STALE,
    )
    monkeypatch.setattr(
        pb_card,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=5401,
            total_players=28619,
            percentile=81.13,
        ),
    )

    assert _rendered_rank("Scenario", allow_network=False) == "81.13% percentile"
    assert "Scenario" not in pb_card._last_rank_hints


def test_a_successful_manual_refresh_retires_the_stale_affordance(monkeypatch):
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    pb_card._last_rank_hints["Scenario"] = (
        PositionShown("1,240", None),
        pb_card._RANK_HINT_SERVED_STALE,
    )
    monkeypatch.setattr(
        pb_card,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=1240,
        ),
    )

    _RefreshClient().click("Scenario")

    assert pb_card._last_rank_hints["Scenario"] == (PositionShown("1,240", None), None)
    assert _rendered_rank("Scenario", allow_network=False) == "1,240"


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        (
            ScenarioRankInfo(
                status=ScenarioRankStatus.RANKED,
                rank=25,
                leaderboard_id=98330,
                score=100.0,
            ),
            "25",
        ),
        (
            ScenarioRankInfo(
                status=ScenarioRankStatus.UNRANKED,
                leaderboard_id=98330,
            ),
            "Unranked",
        ),
    ],
)
def test_manual_rank_refresh_is_one_shot_and_authoritative(
    monkeypatch,
    tmp_path,
    candidate,
    expected,
):
    scenario_name = "Reset Scenario"
    leaderboard_id = 98330
    username = "MingoDynasty"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    settings_service.save_settings({"kovaaks_username": username})
    api_service.make_cache()
    api_service.save_leaderboard_id(scenario_name, leaderboard_id, "test")
    api_service.save_scenario_rank(
        leaderboard_id,
        username,
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=5,
            leaderboard_id=leaderboard_id,
            scenario_name=scenario_name,
            score=110.0,
        ),
    )

    fetched = []

    def fetch_once(*_args):
        fetched.append(True)
        return candidate

    monkeypatch.setattr(api_service, "fetch_scenario_rank", fetch_once)
    monkeypatch.setattr(
        api_service,
        "get_user_scenario_total_play",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        api_service,
        "_with_leaderboard_total",
        lambda rank_info, _ttl=168, force_refresh=False: rank_info,
    )

    rank_text, notifications, _hidden = _RefreshClient().click(scenario_name)
    assert rank_text == expected
    # Any completed refresh — ranked or unranked — confirms with a green
    # toast, on a channel keyed to the scenario it refreshed.
    assert notifications[0]["color"] == "green"
    assert notifications[0]["title"] == "Position refreshed"
    assert scenario_name in notifications[0]["message"]
    assert notifications[0]["id"].startswith(f"rank-refresh-success-{scenario_name}-")
    assert fetched == [True]
    stored = api_service._cached_rank(leaderboard_id, username)
    assert stored is not None
    assert stored.status == candidate.status
    assert stored.score == candidate.score


def _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id):
    """Cache one resolved, ranked scenario for a Refresh click to act on."""
    username = "MingoDynasty"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    settings_service.save_settings({"kovaaks_username": username})
    api_service.make_cache()
    api_service.save_leaderboard_id(scenario, leaderboard_id, "test")
    api_service.save_scenario_rank(
        leaderboard_id,
        username,
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=40,
            leaderboard_id=leaderboard_id,
            scenario_name=scenario,
            score=110.0,
        ),
    )
    monkeypatch.setattr(
        api_service,
        "get_user_scenario_total_play",
        lambda *_args: None,
    )


def _refreshed_rank(leaderboard_id, rank=25):
    """Return the board-authoritative result a click's rank fetch would give."""
    return ScenarioRankInfo(
        status=ScenarioRankStatus.RANKED,
        rank=rank,
        leaderboard_id=leaderboard_id,
    )


def test_manual_rank_refresh_re_reads_the_total_behind_the_percentile(
    monkeypatch,
    tmp_path,
):
    """A fresh totals cache does not spare the click its total lookup.

    The denominator is refreshed with the numerator: a live position over a
    week-old count is two moments presented as one fact, and on a growing
    board it understates the percentile.
    """
    scenario = "Reset Scenario"
    leaderboard_id = 98330
    _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id)
    api_service.save_leaderboard_total(leaderboard_id, 500)

    totals = []

    def fetch_total(_leaderboard_id):
        totals.append(True)
        return 1000

    monkeypatch.setattr(api_service, "fetch_leaderboard_total", fetch_total)
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: _refreshed_rank(leaderboard_id),
    )

    client = _RefreshClient()
    display, notifications, _hidden = client.click(scenario)

    assert totals == [True]
    # 95.10% is what the cached 500 would have printed.
    assert _rank_text(display) == "97.55% percentile"
    # The percentile leads, so the label goes, and the position and the new
    # total are the hover's first line.
    assert client.label_hidden is True
    assert client.of_total == "Position 25 of 1,000"
    assert notifications[0]["color"] == "green"


def test_a_passive_render_still_honors_the_leaderboard_total_ttl(
    monkeypatch,
    tmp_path,
):
    """Only the click is board-authoritative; bulk and interval paths keep the TTL."""
    scenario = "Reset Scenario"
    leaderboard_id = 98330
    _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id)
    api_service.save_leaderboard_total(leaderboard_id, 500)

    monkeypatch.setattr(
        api_service,
        "fetch_leaderboard_total",
        lambda *_args: pytest.fail("a passive render must not refetch the total"),
    )
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: pytest.fail("a passive render must not refetch the rank"),
    )

    assert _rank_text(_rendered_rank(scenario, True)) == "92.10% percentile"


def test_a_failed_total_refresh_toasts_orange_and_keeps_the_cached_percentile(
    monkeypatch,
    tmp_path,
):
    """Orange is partial success: the position committed, the total did not.

    Green would assert a freshness the readout does not have, and the
    served-stale yellow would claim the position came from cache when it is
    the one part that did refresh.
    """
    scenario = "Reset Scenario"
    leaderboard_id = 98330
    _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id)
    api_service.save_leaderboard_total(leaderboard_id, 500)

    def fetch_total(_leaderboard_id):
        raise requests.RequestException("leaderboard unreachable")

    monkeypatch.setattr(api_service, "fetch_leaderboard_total", fetch_total)
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: _refreshed_rank(leaderboard_id),
    )

    display, notifications, _hidden = _RefreshClient().click(scenario)

    assert _rank_text(display) == "95.10% percentile"
    assert notifications[0]["color"] == "orange"
    assert notifications[0]["title"] == "Position refreshed but total from cache"
    assert scenario in notifications[0]["message"]
    # The percentile moved under the user's eyes this click (92.10 to 95.10),
    # so the copy names the total, which is the part that came from cache.
    assert "the total shown is from cache" in notifications[0]["message"]
    assert notifications[0]["id"].startswith(f"rank-refresh-success-{scenario}-")


def test_a_failed_total_refresh_with_nothing_cached_toasts_orange_without_a_total(
    monkeypatch,
    tmp_path,
):
    """No count was ever cached, so the position stands alone and says so."""
    scenario = "Reset Scenario"
    leaderboard_id = 98330
    _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id)

    def fetch_total(_leaderboard_id):
        raise requests.RequestException("leaderboard unreachable")

    monkeypatch.setattr(api_service, "fetch_leaderboard_total", fetch_total)
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: _refreshed_rank(leaderboard_id),
    )

    display, notifications, _hidden = _RefreshClient().click(scenario)

    assert _rank_text(display) == "25"
    assert notifications[0]["color"] == "orange"
    assert notifications[0]["title"] == "Position refreshed but no total"
    assert "no total is shown" in notifications[0]["message"]


def test_a_failed_total_refresh_on_an_unranked_result_stays_true(
    monkeypatch,
    tmp_path,
):
    """An unranked readout has no percentile, so the copy must not claim one.

    ``format_scenario_rank`` renders UNRANKED as ``Unranked (N players)``. The
    total is the only thing the failed re-read touched, and naming it is what
    keeps one string true for both statuses.
    """
    scenario = "Reset Scenario"
    leaderboard_id = 98330
    _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id)
    api_service.save_leaderboard_total(leaderboard_id, 500)

    def fetch_total(_leaderboard_id):
        raise requests.RequestException("leaderboard unreachable")

    monkeypatch.setattr(api_service, "fetch_leaderboard_total", fetch_total)
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: ScenarioRankInfo(
            status=ScenarioRankStatus.UNRANKED,
            leaderboard_id=leaderboard_id,
        ),
    )

    display, notifications, _hidden = _RefreshClient().click(scenario)

    assert _rank_text(display) == "Unranked (500 players)"
    assert notifications[0]["color"] == "orange"
    assert notifications[0]["title"] == "Position refreshed but total from cache"
    assert "the total shown is from cache" in notifications[0]["message"]
    assert "percentile" not in notifications[0]["message"]


def test_a_served_stale_refresh_names_the_total_it_shows(monkeypatch, tmp_path):
    """A cached total beside the cached position is named as cached too.

    A failed position request asks for no total, so the total on screen
    predates the click. Naming only the position would read as though the
    total had refreshed.
    """
    scenario = "Reset Scenario"
    leaderboard_id = 98330
    _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id)
    api_service.save_leaderboard_total(leaderboard_id, 500)

    def fetch_rank(*_args):
        raise requests.RequestException("leaderboard unreachable")

    monkeypatch.setattr(api_service, "fetch_scenario_rank", fetch_rank)

    client = _RefreshClient()
    display, notifications, _hidden = client.click(scenario)

    assert _rank_text(display) == "92.10% percentile · from cache"
    assert client.of_total == "Position 40 of 500"
    assert notifications[0]["color"] == "yellow"
    assert notifications[0]["title"] == "Refresh failed · data from cache"
    assert (
        notifications[0]["message"]
        == "Couldn't refresh. The position and total shown are from cache."
    )


def test_a_failed_rank_refresh_asks_for_no_total(monkeypatch, tmp_path):
    """A host that just failed the rank is not asked for the count as well."""
    scenario = "Reset Scenario"
    leaderboard_id = 98330
    _prepare_refresh_scenario(monkeypatch, tmp_path, scenario, leaderboard_id)
    api_service.save_leaderboard_total(leaderboard_id, 500)

    monkeypatch.setattr(
        api_service,
        "fetch_leaderboard_total",
        lambda *_args: pytest.fail("a failed rank fetch must not ask for the total"),
    )

    def fetch_rank(*_args):
        raise requests.RequestException("leaderboard unreachable")

    monkeypatch.setattr(api_service, "fetch_scenario_rank", fetch_rank)

    display, notifications, _hidden = _RefreshClient().click(scenario)

    # The cached position carries the served-stale hint; its count comes from
    # the TTL-free read in the fallback, not from a second request.
    assert _rank_text(display) == "92.10% percentile · from cache"
    assert notifications[0]["color"] == "yellow"


def test_manual_rank_refresh_failure_toasts_red_and_leaves_the_value_alone(
    monkeypatch,
):
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    calls = []

    def get_rank(*_args, **kwargs):
        calls.append(kwargs)
        return ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            error_message="Rank lookup failed.",
        )

    monkeypatch.setattr(pb_card, "get_scenario_rank_info", get_rank)

    rank_display, notifications, _hidden = _RefreshClient().click("Scenario")

    # no_update, not "N/A": whatever the field showed -- usually the cached
    # position -- stays put, which is what the toast copy promises.
    assert rank_display is no_update
    assert calls == [{"force_refresh": True}]
    assert [notification["color"] for notification in notifications] == ["red"]
    assert notifications[0]["title"] == "Position refresh failed"
    assert (
        notifications[0]["message"]
        == "Couldn't refresh. The position shown is unchanged."
    )


def test_manual_rank_refresh_crash_toasts_red_and_leaves_the_value_alone(monkeypatch):
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})

    def explode(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(pb_card, "get_scenario_rank_info", explode)

    rank_display, notifications, _hidden = _RefreshClient().click("Scenario")

    assert rank_display is no_update
    assert [notification["color"] for notification in notifications] == ["red"]
    assert notifications[0]["title"] == "Position refresh failed"


def test_manual_rank_refresh_served_stale_toasts_yellow_and_marks_the_value(
    monkeypatch,
):
    # A failed fetch served from cache is neither a failure the user must act
    # on nor a refresh worth confirming: yellow, and the value says so too.
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})

    def get_rank(*_args, **_kwargs):
        return ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=50,
            leaderboard_id=1,
            scenario_name="Scenario",
            served_stale=True,
            warning_message="Couldn't refresh from KovaaK's; showing the last "
            "cached position for Scenario.",
        )

    monkeypatch.setattr(pb_card, "get_scenario_rank_info", get_rank)

    rank_display, notifications, _hidden = _RefreshClient().click("Scenario")

    assert _rank_text(rank_display) == "50 · from cache"
    assert [notification["color"] for notification in notifications] == ["yellow"]
    assert notifications[0]["title"] == "Refresh failed · data from cache"
    # No total on screen, so the message must not claim one.
    assert (
        notifications[0]["message"]
        == "Couldn't refresh. The position shown is from cache."
    )


def test_manual_rank_refresh_reports_a_steam_mismatch_as_a_clean_refresh(monkeypatch):
    # The fetch succeeded; the mismatch is the passive path's once-per-session
    # toast, not a per-click complaint about a refresh that worked.
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})

    def get_rank(*_args, **_kwargs):
        return ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=50,
            leaderboard_id=1,
            scenario_name="Scenario",
            matched_steam_id="different-steam-id",
            warning_message="Configured Steam ID 'x' does not match.",
        )

    monkeypatch.setattr(pb_card, "get_scenario_rank_info", get_rank)

    rank_display, notifications, _hidden = _RefreshClient().click("Scenario")

    assert rank_display == "50"
    assert [notification["color"] for notification in notifications] == ["green"]


def test_back_to_back_manual_refreshes_each_render_their_result(monkeypatch):
    # ``show`` swallows a repeated id while the first toast is still up, so
    # each deliberate click shows a fresh instance and hides the one before it.
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    monkeypatch.setattr(
        pb_card,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=50,
            leaderboard_id=1,
            scenario_name="Scenario",
        ),
    )

    client = _RefreshClient()
    _first_display, first, first_hidden = client.click("Scenario")
    _second_display, second, second_hidden = client.click("Scenario")

    assert first[0]["color"] == second[0]["color"] == "green"
    assert first[0]["id"] != second[0]["id"]
    assert first[0]["id"].startswith("rank-refresh-success-Scenario-")
    assert second[0]["id"].startswith("rank-refresh-success-Scenario-")
    # The replacement: the second click retires the first click's instance.
    assert first_hidden == []
    assert second_hidden == [first[0]["id"]]


def test_manual_rank_refresh_without_a_username_names_the_condition(monkeypatch):
    # Nothing failed: with no username the lookup would never touch the
    # network, so the click is answered with the verdict rather than the
    # generic red failure -- and the field's own hint is left alone.
    monkeypatch.setattr(
        pb_card,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: pytest.fail(
            "an unset username must not reach the rank service"
        ),
    )

    rank_display, notifications, _hidden = _RefreshClient().click("Scenario")

    assert rank_display is no_update
    assert [notification["color"] for notification in notifications] == ["blue"]
    assert notifications[0]["title"] == "KovaaK's username not set"
    assert notifications[0]["message"] == (
        "Set your KovaaK's username in Settings to see your leaderboard position."
    )


def test_back_to_back_unset_username_refreshes_each_answer(monkeypatch):
    # Same reason the green confirmation re-pops: a stable id would be
    # swallowed while the first toast is still on screen.
    monkeypatch.setattr(
        pb_card,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: pytest.fail(
            "an unset username must not reach the rank service"
        ),
    )

    client = _RefreshClient()
    _first_display, first, first_hidden = client.click("Scenario")
    _second_display, second, second_hidden = client.click("Scenario")

    assert first[0]["id"] != second[0]["id"]
    assert first[0]["id"].startswith("rank-refresh-username-unset-")
    assert second[0]["id"].startswith("rank-refresh-username-unset-")
    assert first_hidden == []
    assert second_hidden == [first[0]["id"]]


def test_the_two_refresh_problems_share_one_channel(monkeypatch):
    """A hard failure and a served-stale retry are verdicts on one attempt.

    Under the separate ids they used to carry, a stale retry after a hard
    failure left both toasts on screen contradicting each other about the same
    click. One channel makes each attempt's verdict replace the last.
    """
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    outcomes = [
        ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            error_message="Rank lookup failed.",
        ),
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=50,
            leaderboard_id=1,
            scenario_name="Scenario",
            served_stale=True,
            warning_message="Showing the last cached position.",
        ),
    ]
    monkeypatch.setattr(
        pb_card, "get_scenario_rank_info", lambda *_a, **_k: outcomes.pop(0)
    )

    client = _RefreshClient()
    _display, failed, failed_hidden = client.click("Scenario")
    _display, stale, stale_hidden = client.click("Scenario")

    assert failed[0]["color"] == "red"
    assert stale[0]["color"] == "yellow"
    assert failed[0]["id"].startswith(f"{pb_card._RANK_REFRESH_PROBLEM_CHANNEL}-")
    assert stale[0]["id"].startswith(f"{pb_card._RANK_REFRESH_PROBLEM_CHANNEL}-")
    assert failed_hidden == []
    assert stale_hidden == [failed[0]["id"]]


def test_refreshes_of_two_scenarios_keep_separate_success_channels(monkeypatch):
    """Different scenarios are different facts, so their confirmations stack."""
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    monkeypatch.setattr(
        pb_card,
        "get_scenario_rank_info",
        lambda scenario, *_a, **_k: ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=50,
            leaderboard_id=1,
            scenario_name=scenario,
        ),
    )

    client = _RefreshClient()
    _display, first, first_hidden = client.click("Scenario A")
    _display, second, second_hidden = client.click("Scenario B")

    assert first_hidden == second_hidden == []
    assert client.toast_channels["rank-refresh-success-Scenario A"] == first[0]["id"]
    assert client.toast_channels["rank-refresh-success-Scenario B"] == second[0]["id"]


def test_a_successful_refresh_clears_the_problem_and_username_channels(monkeypatch):
    """The success falsifies both standing claims about the same scenario."""
    outcomes = [
        ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            error_message="Rank lookup failed.",
        ),
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=50,
            leaderboard_id=1,
            scenario_name="Scenario",
        ),
    ]
    monkeypatch.setattr(
        pb_card, "get_scenario_rank_info", lambda *_a, **_k: outcomes.pop(0)
    )

    # No username first: the blue notice stands, and nothing reached the
    # service. Then the username is set and the refresh fails, then succeeds.
    client = _RefreshClient()
    _display, unset, _hidden = client.click("Scenario")
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    _display, failed, _hidden = client.click("Scenario")
    _display, success, success_hidden = client.click("Scenario")

    assert success[0]["color"] == "green"
    assert set(success_hidden) == {failed[0]["id"], unset[0]["id"]}
    assert client.toast_channels[pb_card._RANK_REFRESH_PROBLEM_CHANNEL] is None
    assert client.toast_channels[pb_card._RANK_REFRESH_USERNAME_UNSET_CHANNEL] is None


def test_manual_rank_refresh_ignores_initial_load_fire(monkeypatch):
    # Under DashProxy an allow_duplicate callback can fire once on page load
    # with n_clicks=None; that must not force a network refresh or toast.
    monkeypatch.setattr(
        pb_card,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: pytest.fail(
            "an initial-load fire must not hit the network"
        ),
    )

    assert pb_card.refresh_rank(None, "Scenario", {}) == (no_update,) * 7


def test_manual_rank_refresh_without_scenario_skips_fetch_and_toast(monkeypatch):
    monkeypatch.setattr(
        pb_card,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: pytest.fail(
            "a refresh without a scenario must not hit the network"
        ),
    )

    assert pb_card.refresh_rank(1, None, {}) == (
        "N/A",
        False,
        None,
        None,
        no_update,
        no_update,
        no_update,
    )


def test_scenario_rank_loading_is_delayed_and_not_shown_initially(monkeypatch):
    monkeypatch.setattr(
        scenario_selection, "get_visible_playlist_selector_options", lambda: []
    )
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])

    page = run_history.layout()
    rank_loading = next(
        (
            component
            for component in _walk_components(page)
            if isinstance(component, dcc.Loading)
            and any(
                getattr(child, "id", None) == IDS.rank
                for child in _walk_components(component.children)
            )
        ),
        None,
    )

    assert rank_loading is not None
    assert rank_loading.delay_show == pb_card.SCENARIO_RANK_LOADING_DELAY_MS == 250
    assert rank_loading.show_initially is False

    refresh_button = next(
        component
        for component in _walk_components(page)
        if getattr(component, "id", None) == IDS.rank_refresh_button
    )
    assert refresh_button.children == "Refresh"


STORED_AT = datetime(2026, 10, 1, 6, 24, 30, tzinfo=UTC)


def test_position_hover_starts_disabled_around_the_value(monkeypatch):
    """Until a render dates a position there is nothing to hover for."""
    components = _layout_components(monkeypatch)
    tooltip = components[IDS.rank_updated_tooltip]
    value = tooltip.children

    assert value.id == IDS.rank
    assert tooltip.disabled is True
    assert tooltip.label == ""
    assert tooltip.events == chart_options.TOOLTIP_EVENTS
    assert getattr(value, "className", None) is None
    assert getattr(value, "tabIndex", None) is None
    assert getattr(components[IDS.rank_updated_ts], "data", None) is None


@pytest.mark.parametrize(
    ("rank_info", "expected"),
    [
        (
            ScenarioRankInfo(
                status=ScenarioRankStatus.RANKED, rank=10, fetched_at=STORED_AT
            ),
            STORED_AT.timestamp(),
        ),
        (
            ScenarioRankInfo(status=ScenarioRankStatus.UNRANKED, fetched_at=STORED_AT),
            STORED_AT.timestamp(),
        ),
        # The field reads N/A for both of these, so there is nothing to date,
        # whatever the entry carries.
        (
            ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN, fetched_at=STORED_AT),
            None,
        ),
        (
            ScenarioRankInfo(status=ScenarioRankStatus.RANKED, fetched_at=STORED_AT),
            None,
        ),
        # A cache entry written without a time.
        (ScenarioRankInfo(status=ScenarioRankStatus.RANKED, rank=10), None),
    ],
)
def test_rank_updated_ts_dates_only_a_displayed_position(rank_info, expected):
    assert pb_card._rank_updated_ts(rank_info) == expected


def _seed_dated_rank_cache(monkeypatch, tmp_path) -> str:
    """Cache a ranked position that records when it was stored."""
    scenario_name = "Cached Scenario"
    leaderboard_id = 98330
    username = "MingoDynasty"
    monkeypatch.setattr(api_service, "CACHE_DIR", tmp_path / "cache")
    settings_service.save_settings({"kovaaks_username": username})
    api_service.make_cache()
    api_service.save_leaderboard_id(scenario_name, leaderboard_id, "test")
    api_service.save_scenario_rank(
        leaderboard_id,
        username,
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=10,
            leaderboard_id=leaderboard_id,
            scenario_name=scenario_name,
            score=100.0,
            fetched_at=STORED_AT,
        ),
    )
    api_service.save_leaderboard_total(leaderboard_id, 100)
    monkeypatch.setattr(
        api_service,
        "get_user_scenario_total_play",
        lambda *_args: None,
    )
    return scenario_name


def test_both_render_paths_date_the_position_from_its_cache_entry(
    monkeypatch,
    tmp_path,
):
    """The hover dates the stored read, so a cache hit must not restart its age."""
    scenario_name = _seed_dated_rank_cache(monkeypatch, tmp_path)

    for allow_network in (True, False):
        display, updated_ts, _notifications = _render(
            scenario_name,
            allow_network=allow_network,
        )

        assert display == "90.50% percentile"
        assert updated_ts == STORED_AT.timestamp()


def test_a_render_with_no_position_dates_nothing(monkeypatch):
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    monkeypatch.setattr(
        pb_card,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            error_message="Failed to fetch leaderboard position for Scenario.",
        ),
    )

    rendered, updated_ts, _notifications = _render(
        "Scenario",
        allow_network=True,
    )

    assert _rank_text(rendered) == "N/A · lookup failed"
    assert updated_ts is None
    assert _render(None, allow_network=True) == (
        "N/A",
        None,
        [],
    )


def test_a_refresh_restarts_the_stored_time(monkeypatch, tmp_path):
    """The fetch's own time replaces the one the field was showing."""
    scenario_name = _seed_dated_rank_cache(monkeypatch, tmp_path)
    refreshed_at = datetime(2026, 10, 4, 11, 0, tzinfo=UTC)
    monkeypatch.setattr(api_service, "fetch_leaderboard_total", lambda *_args: 1000)
    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        lambda *_args: ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=25,
            leaderboard_id=98330,
            score=100.0,
            fetched_at=refreshed_at,
        ),
    )

    client = _RefreshClient()
    display, notifications, _hidden = client.click(scenario_name)

    assert _rank_text(display) == "97.55% percentile"
    assert notifications[0]["color"] == "green"
    assert client.updated_ts == refreshed_at.timestamp()


def test_a_served_stale_refresh_keeps_the_stored_time(monkeypatch, tmp_path):
    """A failed fetch re-serves the cached position, so its age must not restart.

    This is the case "Last updated" is worded for: the app tried again just
    now, and the position on screen is still the one stored earlier.
    """
    scenario_name = _seed_dated_rank_cache(monkeypatch, tmp_path)

    def fetch_rank(*_args):
        raise requests.RequestException("leaderboard unreachable")

    monkeypatch.setattr(api_service, "fetch_scenario_rank", fetch_rank)

    client = _RefreshClient()
    display, notifications, _hidden = client.click(scenario_name)

    assert _rank_text(display) == "90.50% percentile · from cache"
    assert notifications[0]["color"] == "yellow"
    assert client.updated_ts == STORED_AT.timestamp()


def test_a_failed_refresh_leaves_the_stored_time_alone(monkeypatch):
    """The value stays on screen untouched, and so does the time that dates it."""
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    monkeypatch.setattr(
        pb_card,
        "get_scenario_rank_info",
        lambda *_args, **_kwargs: ScenarioRankInfo(
            status=ScenarioRankStatus.UNKNOWN,
            error_message="Rank lookup failed.",
        ),
    )

    client = _RefreshClient()
    display, notifications, _hidden = client.click("Scenario")

    assert display is no_update
    assert notifications[0]["color"] == "red"
    assert client.updated_ts is no_update
    # The label and the hover's first line stay with the value they described.
    assert client.label_hidden is no_update
    assert client.of_total is no_update


def test_every_writer_of_the_position_value_also_writes_its_label_and_hover():
    """A value written alone would sit beside a label or under a hover of another.

    The passive render and the Refresh click both replace the value, and the
    label and the hover read what came with it, so each writes all four.
    """
    value_writers = [
        _output_keys(spec)
        for spec in GLOBAL_CALLBACK_LIST
        if f"{IDS.rank}.children" in _output_keys(spec)
    ]

    assert len(value_writers) == 2
    for outputs in value_writers:
        assert {
            f"{IDS.rank_label}.hidden",
            f"{IDS.rank_updated_ts}.data",
            f"{IDS.rank_of_total}.data",
        } <= outputs


def test_position_hover_is_worded_in_the_browser_from_the_stored_time():
    """The age is recomputed on the 30s tick, so a parked page stays current.

    Where the percentile leads, the position and the total are the hover's
    first line, over the age.
    """
    (spec,) = [
        spec
        for spec in GLOBAL_CALLBACK_LIST
        if f"{IDS.rank_updated_tooltip}.label" in _output_keys(spec)
    ]

    assert spec["clientside_function"] is not None
    assert _output_keys(spec) == {
        f"{IDS.rank_updated_tooltip}.label",
        f"{IDS.rank_updated_tooltip}.disabled",
        f"{IDS.rank}.className",
        f"{IDS.rank}.tabIndex",
    }
    assert spec["inputs"] == [
        {"id": IDS.rank_updated_ts, "property": "data"},
        {"id": IDS.rank_of_total, "property": "data"},
        {"id": IDS.relative_time_interval, "property": "n_intervals"},
    ]
    source = next(
        script
        for script in GLOBAL_INLINE_SCRIPTS
        if spec["clientside_function"]["function_name"] in script
    )
    # The copy, and the shared helpers that word the age and the timestamp the
    # same way the Last played hover does.
    assert '"Last updated "' in source
    assert '" · "' in source
    assert "relativeTime(seconds" in source
    assert "absoluteTime(seconds" in source
    assert "cell-tooltip-affordance" in source
    # The position's line first, then the age's, one line each.
    assert "lines.push(ofTotal)" in source
    assert 'lines.join("\\n")' in source


def test_the_hover_keeps_its_line_break():
    """dmc's tooltip does not break a line, so the stylesheet lets it."""
    target = next(
        component
        for component in _walk_components(pb_card.pb_card(IDS))
        if getattr(component, "id", None) == IDS.rank_updated_tooltip
    )
    css = (Path(__file__).resolve().parents[1] / "assets" / "stylesheet.css").read_text(
        encoding="utf-8"
    )

    assert target.classNames == {"tooltip": "pb-card-position-tooltip"}
    assert (
        ".mantine-Tooltip-tooltip.pb-card-position-tooltip {\n"
        "    white-space: pre-line;"
    ) in css


def test_the_line_is_the_label_and_the_value_in_one_run_of_text_then_refresh(
    monkeypatch,
):
    """A hint too long for the line wraps as a sentence, and Refresh follows it.

    The line starts hidden: the card shows it once there is a local PB.
    """
    components = _layout_components(monkeypatch)
    line = components[IDS.leaderboard]
    loading, refresh = line.children
    text = loading.children
    label, tooltip = text.children

    assert line.hidden is True
    assert line.className == "run-history-card-result pb-card-leaderboard"
    assert isinstance(loading, dcc.Loading)
    assert isinstance(text, html.Span)
    assert (label.id, label.children, label.className) == (
        IDS.rank_label,
        "Position: ",
        "pb-card-position-label",
    )
    assert tooltip.id == IDS.rank_updated_tooltip
    # dmc wraps a tooltip's target in a block box: inline here, flex round
    # the button, so neither adds a line of its own.
    assert tooltip.boxWrapperProps == {"className": "run-history-card-time-target"}
    assert tooltip.children.inherit is True
    assert refresh.children.id == IDS.rank_refresh_button
    assert refresh.boxWrapperProps == {"className": "pb-card-flex-target"}


# A second page's ids, none of which the Run History page uses.
SECOND_PAGE_IDS = pb_card.PbCardIds(
    *(f"second-{field}" for field in pb_card.PbCardIds._fields)
)
# The ids of what a page builds itself and the card only reads.
PAGE_BUILT_FIELDS = (
    "run_events",
    "scenario_dropdown",
    "playlist_filter",
    "polling_interval",
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
    """List what ``register_pb_card`` registers for ``ids``, in order."""
    return [
        (
            pb_card.show_pb,
            [
                f"{ids.run_events}.data",
                f"{ids.scenario_dropdown}.value",
                f"{ids.playlist_filter}.value",
            ],
            [],
        ),
        (
            None,
            [f"{ids.set_at}.data", f"{ids.relative_time_interval}.n_intervals"],
            [],
        ),
        (
            pb_card.get_scenario_rank,
            [
                f"{ids.run_events}.data",
                f"{ids.scenario_dropdown}.value",
                f"{ids.polling_interval}.n_intervals",
            ],
            [],
        ),
        (
            None,
            [
                f"{ids.rank_updated_ts}.data",
                f"{ids.rank_of_total}.data",
                f"{ids.relative_time_interval}.n_intervals",
            ],
            [],
        ),
        (
            pb_card.refresh_rank,
            [f"{ids.rank_refresh_button}.n_clicks"],
            [f"{ids.scenario_dropdown}.value", "toast-channel-registry.data"],
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


def test_the_page_registers_the_card_for_its_own_ids():
    """Registration is a call the page makes; without it the card shows nothing."""
    assert _card_registrations(IDS) == _expected_registrations(IDS)


def test_a_second_page_builds_a_card_that_shares_no_id_with_the_first(monkeypatch):
    first_page_ids = set(_layout_components(monkeypatch)) - {None}

    built = {
        component.id
        for component in _walk_components(pb_card.pb_card(SECOND_PAGE_IDS))
        if getattr(component, "id", None) is not None
    }

    # Every id in the card came from the ids passed in, and every id passed in
    # is there apart from the ones a page builds itself.
    assert built == set(SECOND_PAGE_IDS) - {
        getattr(SECOND_PAGE_IDS, field) for field in PAGE_BUILT_FIELDS
    }
    assert not built & first_page_ids


def test_a_second_registration_adds_callbacks_for_its_own_ids_only(
    restored_callbacks,
):
    registered_before = list(GLOBAL_CALLBACK_LIST)
    first_page = _card_registrations(IDS)

    pb_card.register_pb_card(SECOND_PAGE_IDS)

    assert GLOBAL_CALLBACK_LIST[: len(registered_before)] == registered_before
    added = GLOBAL_CALLBACK_LIST[len(registered_before) :]
    # The same functions answer for both pages, so both read and write the
    # module's one memory of what the leaderboard line last concluded.
    assert _card_registrations(SECOND_PAGE_IDS) == _expected_registrations(
        SECOND_PAGE_IDS
    )
    assert len(added) == len(first_page)
    # Nothing it writes belongs to the first page. The notification container
    # and the channel registry are the shell's, which both pages share.
    assert {
        key.rpartition(".")[0] for entry in added for key in _output_keys(entry)
    } == {
        "second-set_at",
        "second-body",
        "second-leaderboard",
        "second-faded",
        "second-label",
        "second-time",
        "second-time_tooltip",
        "second-rank",
        "second-rank_label",
        "second-rank_updated_ts",
        "second-rank_of_total",
        "second-rank_updated_tooltip",
        "notification-container",
        "toast-channel-registry",
    }
    # The spinner that swallows repeat clicks is on the second page's button.
    assert added[-1]["running"] == {
        "running": {"second-rank_refresh_button.loading": True},
        "runningOff": {"second-rank_refresh_button.loading": False},
    }
    assert _card_registrations(IDS) == first_page


def test_a_second_pages_polling_tick_alone_reads_caches_only(monkeypatch):
    """Each page has an interval of its own, so the rule cannot name one id."""
    tick = {"prop_id": f"{SECOND_PAGE_IDS.polling_interval}.n_intervals"}
    chosen = {"prop_id": f"{SECOND_PAGE_IDS.scenario_dropdown}.value"}
    new_runs = {"prop_id": f"{SECOND_PAGE_IDS.run_events}.data"}

    assert pb_card._rank_allows_network([tick]) is False
    assert pb_card._rank_allows_network([new_runs]) is True
    assert pb_card._rank_allows_network([tick, chosen]) is True

    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    allowed = []

    def rank_for(*_args, **kwargs):
        allowed.append(kwargs["allow_network"])
        return ScenarioRankInfo(status=ScenarioRankStatus.UNRANKED)

    monkeypatch.setattr(pb_card, "get_scenario_rank_info", rank_for)
    for triggered in ([tick], [tick, chosen]):
        monkeypatch.setattr(pb_card, "ctx", SimpleNamespace(triggered=triggered))
        pb_card.get_scenario_rank(None, "Scenario", 1)

    assert allowed == [False, True]
