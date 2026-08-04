"""Regression tests for D5's normative run-verdict replace behaviors.

The contract these pin is about *elapsed time*, not payload contents: at most
one run-verdict toast is visible, a later verdict replaces it, and the
replacement gets a full lifetime rather than the remainder of the old timer.

``FakeNotificationContainer`` is a Python model of the DMC 2.8.0 notification
store, transcribed from the shipped bundle so the assertions can advance a
clock. Three behaviors are modelled, and all three were read out of
``dash_mantine_components.js``:

- ``show`` is a no-op for an id already on screen
  (``e.id && list.some(n => n.id === e.id) ? list : [...list, e]``).
- ``update`` merges into an existing entry and is a no-op for an absent id
  (``list.map(n => n.id === e.id ? {...n, ...e} : n)``).
- the auto-close timer is a React effect keyed on the *resolved duration
  alone* (``useEffect(() => (arm(), clear), [resolvedAutoClose])``), so a
  replacement carrying the same duration leaves the running timer untouched.

If a DMC upgrade changes any of those, this model goes stale — re-read the
bundle before trusting a green run here.
"""

from types import SimpleNamespace

import dash
import plotly.graph_objects as go
import pytest

dash.Dash(__name__, use_pages=True, pages_folder="")

from source import app_shell  # noqa: E402
from source.pages import home  # noqa: E402
from source.utilities.notifications import (  # noqa: E402
    DEFAULT_AUTO_CLOSE_MS,
    TOAST_LIFETIME_STORE_ID,
)

# What dmc.NotificationContainer resolves autoClose to when a payload omits it.
_CONTAINER_DEFAULT_AUTO_CLOSE_MS = 4000


class _Entry:
    def __init__(self, payload: dict, now: int) -> None:
        self.payload = dict(payload)
        self.armed_duration: int | bool = _CONTAINER_DEFAULT_AUTO_CLOSE_MS
        self.expires_at: int | None = None
        self._arm(now)

    def _arm(self, now: int) -> None:
        duration = self.payload.get("autoClose", _CONTAINER_DEFAULT_AUTO_CLOSE_MS)
        self.armed_duration = duration
        self.expires_at = now + duration if duration is not False else None

    def merge(self, payload: dict, now: int) -> None:
        self.payload.update(payload)
        duration = self.payload.get("autoClose", _CONTAINER_DEFAULT_AUTO_CLOSE_MS)
        # The timer effect only re-runs when its key -- the resolved duration --
        # changes. An identical duration leaves the original timeout running.
        if duration != self.armed_duration:
            self._arm(now)


class FakeNotificationContainer:
    """A clock-driven stand-in for the Mantine notifications store."""

    def __init__(self) -> None:
        self.now = 0
        self._entries: dict[str, _Entry] = {}

    def send(self, notifications) -> None:
        for payload in notifications:
            action = payload.get("action", "show")
            entry = self._entries.get(payload["id"])
            if action == "show":
                if entry is None:
                    self._entries[payload["id"]] = _Entry(payload, self.now)
            elif entry is not None:
                entry.merge(payload, self.now)

    def advance(self, milliseconds: int) -> None:
        self.now += milliseconds
        self._entries = {
            key: entry
            for key, entry in self._entries.items()
            if entry.expires_at is None or entry.expires_at > self.now
        }

    @property
    def visible(self) -> list[dict]:
        self.advance(0)
        return [entry.payload for entry in self._entries.values()]

    def remaining_lifetime(self, notification_id: str) -> int:
        self.advance(0)
        return self._entries[notification_id].expires_at - self.now


@pytest.fixture
def plotting(monkeypatch):
    """Stub out everything generate_graph needs that is not the toast."""
    monkeypatch.setattr(home, "is_scenario_in_database", lambda _scenario: True)
    monkeypatch.setattr(
        home, "get_time_vs_runs", lambda *_a: {"2026-07-06": [object()]}
    )
    monkeypatch.setattr(home, "generate_time_plot", lambda *_a: go.Figure())
    monkeypatch.setattr(home, "get_high_score", lambda _scenario: 830.0)
    monkeypatch.setattr(
        home,
        "ctx",
        SimpleNamespace(triggered=[{"prop_id": "run-events.data"}]),
    )


class _Client:
    """One browser: the shell's lifetime store plus its rendered toasts."""

    def __init__(self) -> None:
        self.container = FakeNotificationContainer()
        self.lifetime_sequence = 0

    def play(self, *, score: float, count: int = 1) -> None:
        payload = {
            "count": count,
            "latest": {
                "scenario_name": "Scenario A",
                "sensitivity": "34.64 cm/360",
                "nth_score": 2,
                "score": score,
                "previous_high_score": 800.0,
            },
        }
        _plot, notifications, next_sequence = home.generate_graph(
            payload,
            "Scenario A",
            5,
            "2026-07-01",
            "score_vs_time",
            False,
            False,
            False,
            "",
            True,
            None,
            self.lifetime_sequence,
        )
        self.container.send(notifications)
        if next_sequence is not dash.no_update:
            self.lifetime_sequence = next_sequence


def test_a_second_run_replaces_the_visible_toast_with_a_full_lifetime(plotting):
    client = _Client()
    client.play(score=812.4)
    client.container.advance(DEFAULT_AUTO_CLOSE_MS - 500)

    client.play(score=901.7)

    visible = client.container.visible
    assert len(visible) == 1
    assert "901.70" in visible[0]["message"]
    # The point of the test: 500 ms short of expiry, the replacement starts its
    # own timer rather than flashing for what was left of the old one.
    assert client.container.remaining_lifetime("run-verdict") >= DEFAULT_AUTO_CLOSE_MS


def test_a_live_run_replaces_the_backlog_digest_with_a_full_lifetime(plotting):
    client = _Client()
    client.play(score=780.0, count=6)
    assert client.container.visible[0]["title"] == "While you were away"

    client.container.advance(DEFAULT_AUTO_CLOSE_MS - 500)
    client.play(score=901.7)

    visible = client.container.visible
    assert len(visible) == 1
    assert visible[0]["title"] == "New 2nd-best score"
    assert client.container.remaining_lifetime("run-verdict") >= DEFAULT_AUTO_CLOSE_MS


def test_a_verdict_after_navigating_away_and_back_gets_a_full_lifetime(
    plotting, monkeypatch
):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])
    client = _Client()
    client.play(score=812.4)
    client.container.advance(DEFAULT_AUTO_CLOSE_MS - 500)

    # Navigate away and back: Home's layout is rebuilt from scratch, so every
    # store it declares resets to its default. The container and the lifetime
    # store sit outside that layout, so the toast is still up and the sequence
    # still knows which duration it is displaying.
    assert TOAST_LIFETIME_STORE_ID not in _component_ids(home.layout())
    assert len(client.container.visible) == 1

    client.play(score=901.7)

    assert len(client.container.visible) == 1
    assert client.container.remaining_lifetime("run-verdict") >= DEFAULT_AUTO_CLOSE_MS


def test_a_page_scoped_sequence_would_not_re_arm_the_timer(plotting):
    # Why the store belongs in the shell: a page-layout store resets to its
    # default on remount, so the post-navigation emission would hand the
    # visible toast the duration it is already displaying and the timer -- keyed
    # on that duration alone -- would never re-arm. This is the failure the
    # test above is guarding against, asserted directly.
    client = _Client()
    client.play(score=812.4)
    client.container.advance(DEFAULT_AUTO_CLOSE_MS - 500)

    client.lifetime_sequence = 0  # what a remounted page-layout store would say
    client.play(score=901.7)

    assert client.container.remaining_lifetime("run-verdict") == 500


def test_the_toast_lifetime_store_is_hosted_by_the_app_shell(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])

    assert TOAST_LIFETIME_STORE_ID in _component_ids(app_shell.layout())
    assert TOAST_LIFETIME_STORE_ID not in _component_ids(home.layout())


def _component_ids(component) -> set[str]:
    found = set()
    stack = [component]
    while stack:
        current = stack.pop()
        component_id = getattr(current, "id", None)
        if isinstance(component_id, str):
            found.add(component_id)
        children = getattr(current, "children", None)
        if children is None:
            continue
        stack.extend(children if isinstance(children, list) else [children])
    return found


def test_run_verdict_emissions_alternate_between_indistinguishable_durations(plotting):
    client = _Client()
    durations = []
    for score in (812.4, 901.7, 933.0):
        client.play(score=score)
        durations.append(client.container.visible[0]["autoClose"])

    assert durations == [
        DEFAULT_AUTO_CLOSE_MS,
        DEFAULT_AUTO_CLOSE_MS + 1,
        DEFAULT_AUTO_CLOSE_MS,
    ]
    # Advancing past the nominal lifetime retires the toast either way, so the
    # 1 ms is invisible to the user and only exists to re-key the timer effect.
    client.container.advance(DEFAULT_AUTO_CLOSE_MS + 1)
    assert client.container.visible == []
