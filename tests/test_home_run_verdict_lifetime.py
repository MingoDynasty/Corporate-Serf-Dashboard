"""Regression tests for D5's normative run-verdict replace behaviors.

The contract these pin is about *elapsed time*, not payload contents: at most
one run-verdict toast is on screen once a response has been applied, a later
verdict replaces it, and the replacement gets a full lifetime rather than the
remainder of the old timer.

``FakeNotificationContainer`` is a Python model of the DMC 2.8.0 notification
store, transcribed from the shipped bundle so the assertions can advance a
clock. Four behaviors are modelled, and all four were read out of
``dash_mantine_components.js``:

- ``show`` is a no-op for an id already on screen
  (``e.id && list.some(n => n.id === e.id) ? list : [...list, e]``) -- which is
  why a channel emission mints a fresh instance id every time.
- ``update`` merges into an existing entry and is a no-op for an absent id
  (``list.map(n => n.id === e.id ? {...n, ...e} : n)``). Nothing sends it any
  more, now that both upsert helpers are gone; it stays modelled so this fake
  keeps transcribing the bundle rather than only the subset today's callers
  happen to use.
- ``hideNotifications`` drops the ids it names, and the container declares that
  effect *after* the ``sendNotifications`` one, so one response shows the fresh
  instance before retiring the instance it replaces.
- the auto-close timer is a React effect keyed on the *resolved duration
  alone* (``useEffect(() => (arm(), clear), [resolvedAutoClose])``); a fresh id
  is a fresh entry, so it arms its own timer whatever the outgoing one had
  left.

If a DMC upgrade changes any of those, this model goes stale -- re-read the
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
    CELEBRATION_CHANNEL,
    DEFAULT_AUTO_CLOSE_MS,
    TOAST_CHANNEL_REGISTRY_STORE_ID,
    channel_toast,
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
        if notifications is dash.no_update:
            return
        for payload in notifications:
            action = payload.get("action", "show")
            entry = self._entries.get(payload["id"])
            if action == "show":
                if entry is None:
                    self._entries[payload["id"]] = _Entry(payload, self.now)
            elif entry is not None:
                entry.merge(payload, self.now)

    def hide(self, notification_ids) -> None:
        """Apply the hide effect, which the container runs after the send one."""
        if notification_ids is dash.no_update:
            return
        for notification_id in notification_ids:
            self._entries.pop(notification_id, None)

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


def apply_registry_patch(registry: dict, patch) -> None:
    """Apply a per-key ``dash.Patch`` the way the Dash client applies it."""
    if patch is dash.no_update:
        return
    for operation in patch._operations:
        assert operation["operation"] == "Assign"
        (key,) = operation["location"]
        registry[key] = operation["params"]["value"]


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


def _run_event(score: float) -> dict:
    """One run as the shell's drain stamps it."""
    return {
        "run_id": f"run-{score}.csv",
        "scenario_name": "Scenario A",
        "sensitivity": "34.64 cm/360",
        "nth_score": 2,
        "score": score,
        "scenario_previous_best": 800.0,
        "is_new_sensitivity": False,
        "is_live": True,
    }


class _Client:
    """One browser: the shell's channel registry plus its rendered toasts."""

    def __init__(self) -> None:
        self.container = FakeNotificationContainer()
        self.toast_channels: dict[str, str | None] = {}
        self.last_shown: list[dict] = []
        self.last_hidden: list[str] = []

    @property
    def verdict_instance(self) -> str | None:
        """The instance id the registry says this browser's verdict is under."""
        return self.toast_channels.get(home._RUN_VERDICT_CHANNEL)

    def play(self, *, score: float) -> None:
        payload = {
            "latest": _run_event(score),
            "celebrated_run_id": None,
        }
        _plot, notifications, hidden, registry_patch = home.generate_graph(
            payload,
            "Scenario A",
            5,
            "2026-07-01",
            "score_vs_time",
            False,
            False,
            False,
            False,
            "",
            True,
            True,
            None,
            self.toast_channels,
        )
        self.last_shown = notifications
        self.last_hidden = hidden
        self.container.send(notifications)
        self.container.hide(hidden)
        apply_registry_patch(self.toast_channels, registry_patch)


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
    assert (
        client.container.remaining_lifetime(client.verdict_instance)
        >= DEFAULT_AUTO_CLOSE_MS
    )


def test_each_verdict_shows_a_fresh_instance_and_hides_the_one_it_replaces(plotting):
    """The mechanism itself: show a new id, hide the registered old one."""
    client = _Client()

    client.play(score=812.4)
    first_instance = client.verdict_instance

    assert [payload["id"] for payload in client.last_shown] == [first_instance]
    assert first_instance.startswith(f"{home._RUN_VERDICT_CHANNEL}-")
    # Nothing to replace on the first emission, so nothing is hidden.
    assert client.last_hidden == []

    client.play(score=901.7)
    second_instance = client.verdict_instance

    assert second_instance != first_instance
    assert [payload["id"] for payload in client.last_shown] == [second_instance]
    assert client.last_hidden == [first_instance]


def test_the_celebration_toast_sits_beside_a_run_verdict_and_outlives_it(plotting):
    """The one deliberate exception to replaces-rather-than-stacks.

    The celebration is its own family with its own id and no lifetime, so an
    ordinary run toast lands beside it rather than over it, expires on its own
    schedule, and leaves the celebration up until the user dismisses it.
    """
    client = _Client()
    celebrated = _run_event(901.7)
    celebrated["nth_score"] = 1
    send, hide, patch = channel_toast(
        app_shell._celebration_toast(celebrated), client.toast_channels
    )
    client.container.send(send)
    client.container.hide(hide)
    apply_registry_patch(client.toast_channels, patch)
    celebration_instance = client.toast_channels[CELEBRATION_CHANNEL]

    client.play(score=812.4)

    assert {entry["id"] for entry in client.container.visible} == {
        celebration_instance,
        client.verdict_instance,
    }

    client.container.advance(DEFAULT_AUTO_CLOSE_MS + 1)

    assert [entry["id"] for entry in client.container.visible] == [celebration_instance]


def test_a_verdict_after_navigating_away_and_back_gets_a_full_lifetime(
    plotting, monkeypatch
):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])
    client = _Client()
    client.play(score=812.4)
    client.container.advance(DEFAULT_AUTO_CLOSE_MS - 500)

    # Navigate away and back: Home's layout is rebuilt from scratch, so every
    # store it declares resets to its default. The container and the registry
    # sit outside that layout, so the toast is still up and the registry still
    # knows which instance it is showing.
    assert TOAST_CHANNEL_REGISTRY_STORE_ID not in _component_ids(home.layout())
    assert len(client.container.visible) == 1

    client.play(score=901.7)

    assert len(client.container.visible) == 1
    assert (
        client.container.remaining_lifetime(client.verdict_instance)
        >= DEFAULT_AUTO_CLOSE_MS
    )


def test_a_page_scoped_registry_would_leave_two_verdicts_on_screen(plotting):
    # Why the store belongs in the shell: a page-layout store resets to its
    # default on remount, so the post-navigation emission would have no instance
    # id to hide and its fresh id would stack beside the toast already on
    # screen. This is the failure the test above is guarding against, asserted
    # directly.
    client = _Client()
    client.play(score=812.4)
    client.container.advance(DEFAULT_AUTO_CLOSE_MS - 500)

    client.toast_channels = {}  # what a remounted page-layout store would say
    client.play(score=901.7)

    assert len(client.container.visible) == 2


def test_the_toast_channel_registry_is_hosted_by_the_app_shell(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])

    assert TOAST_CHANNEL_REGISTRY_STORE_ID in _component_ids(app_shell.layout())
    assert TOAST_CHANNEL_REGISTRY_STORE_ID not in _component_ids(home.layout())


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


def test_run_verdict_emissions_carry_the_one_nominal_lifetime(plotting):
    """No more duration alternation: a fresh id is what re-arms the timer."""
    client = _Client()
    durations = []
    instances = []
    for score in (812.4, 901.7, 933.0):
        client.play(score=score)
        durations.append(client.container.visible[0]["autoClose"])
        instances.append(client.verdict_instance)

    assert durations == [DEFAULT_AUTO_CLOSE_MS] * 3
    assert len(set(instances)) == 3
    client.container.advance(DEFAULT_AUTO_CLOSE_MS + 1)
    assert client.container.visible == []
