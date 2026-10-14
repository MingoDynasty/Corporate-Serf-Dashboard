"""Regression tests for the run toast's replace-in-place behaviors.

The contract these pin is about *elapsed time*, not payload contents: at most
one run toast is on screen once a response has been applied, a later run's
toast replaces it, and the replacement gets a full lifetime rather than the
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

The run toast is sent by the app shell's drain, on every page, which is what
each test drives.
"""

from collections import deque
from datetime import datetime
from urllib.parse import parse_qs, urlsplit

import dash
import pytest
from dash import dcc

dash.Dash(__name__, use_pages=True, pages_folder="")

from source import app_shell  # noqa: E402
from source.components import scenario_selection  # noqa: E402
from source.my_queue.message_queue import NewFileMessage  # noqa: E402
from source.pages import run_history  # noqa: E402
from source.utilities.notifications import (  # noqa: E402
    CELEBRATION_CHANNEL,
    DEFAULT_AUTO_CLOSE_MS,
    RUN_VERDICT_CHANNEL,
    TOAST_CHANNEL_REGISTRY_STORE_ID,
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


@pytest.fixture(autouse=True)
def run_queue(monkeypatch):
    """Give each test a queue of its own for the drain to empty."""
    monkeypatch.setattr(app_shell, "message_queue", deque())


def _message(run_id: str, score: float) -> NewFileMessage:
    """One run as the watchdog queues it, against a previous best of 800."""
    return NewFileMessage(
        datetime_created=datetime.now(),
        is_new_sensitivity=False,
        run_id=run_id,
        scenario_name="Scenario A",
        scenario_previous_best=800.0,
        score=score,
        sensitivity="34.64 cm/360",
        pace_constant=None,
    )


def _named_run(run_toast: dict) -> str:
    """The id of the run a run toast is about, read from its link."""
    (link,) = [part for part in run_toast["message"] if isinstance(part, dcc.Link)]
    (run_id,) = parse_qs(urlsplit(link.href).query)["run"]
    return run_id


class _Client:
    """One browser: the shell's channel registry plus its rendered toasts."""

    def __init__(self) -> None:
        self.container = FakeNotificationContainer()
        self.toast_channels: dict[str, str | None] = {}
        self.last_shown: list[dict] = []
        self.last_hidden: list[str] = []

    @property
    def run_toast_instance(self) -> str | None:
        """The instance id the registry says this browser's run toast is under."""
        return self.toast_channels.get(RUN_VERDICT_CHANNEL)

    def play(self, *runs: tuple[str, float]) -> None:
        """Land a batch of runs and apply the drain's answer as a browser does.

        Each run is its id and its score. A score above 800 sets a new PB.
        """
        app_shell.message_queue.extend(_message(*run) for run in runs)
        _batch, notifications, hidden, registry_patch = app_shell.publish_run_events(
            1,
            None,
            self.toast_channels,
            app_shell.CELEBRATION_STYLE_CONFETTI,
            app_shell.RUN_NOTIFICATIONS_ON,
        )
        self.last_shown = notifications
        self.last_hidden = hidden
        self.container.send(notifications)
        self.container.hide(hidden)
        apply_registry_patch(self.toast_channels, registry_patch)


def test_a_second_run_replaces_the_visible_toast_with_a_full_lifetime():
    client = _Client()
    client.play(("first.csv", 780.0))
    client.container.advance(DEFAULT_AUTO_CLOSE_MS - 500)

    client.play(("second.csv", 790.0))

    visible = client.container.visible
    assert len(visible) == 1
    assert _named_run(visible[0]) == "second.csv"
    # The point of the test: 500 ms short of expiry, the replacement starts its
    # own timer rather than flashing for what was left of the old one.
    assert (
        client.container.remaining_lifetime(client.run_toast_instance)
        >= DEFAULT_AUTO_CLOSE_MS
    )


def test_each_run_toast_shows_a_fresh_instance_and_hides_the_one_it_replaces():
    """The mechanism itself: show a new id, hide the registered old one.

    A fresh id is also what makes the replacement play its entry animation, so
    a second run is seen to arrive although the two toasts may read the same.
    """
    client = _Client()

    client.play(("first.csv", 780.0))
    first_instance = client.run_toast_instance

    assert [payload["id"] for payload in client.last_shown] == [first_instance]
    assert first_instance.startswith(f"{RUN_VERDICT_CHANNEL}-")
    # Nothing to replace on the first emission, so nothing is hidden.
    assert client.last_hidden == []

    client.play(("second.csv", 790.0))
    second_instance = client.run_toast_instance

    assert second_instance != first_instance
    assert [payload["id"] for payload in client.last_shown] == [second_instance]
    assert client.last_hidden == [first_instance]


def test_the_celebration_toast_sits_beside_a_run_toast_and_outlives_it():
    """The one deliberate exception to replaces-rather-than-stacks.

    The celebration is its own family with its own id and no lifetime, so an
    ordinary run toast lands beside it rather than over it, expires on its own
    schedule, and leaves the celebration up until the user dismisses it.
    """
    client = _Client()
    client.play(("pb.csv", 901.7))
    celebration_instance = client.toast_channels[CELEBRATION_CHANNEL]
    assert [entry["id"] for entry in client.container.visible] == [celebration_instance]

    client.play(("ordinary.csv", 780.0))

    assert {entry["id"] for entry in client.container.visible} == {
        celebration_instance,
        client.run_toast_instance,
    }

    client.container.advance(DEFAULT_AUTO_CLOSE_MS + 1)

    assert [entry["id"] for entry in client.container.visible] == [celebration_instance]


def test_a_batch_that_sends_both_toasts_replaces_each_on_its_own_channel():
    """Two toasts in one response, twice: two on screen, never four."""
    client = _Client()
    client.play(("pb-1.csv", 901.7), ("ordinary-1.csv", 780.0))
    first = dict(client.toast_channels)
    assert len(client.container.visible) == 2

    client.play(("pb-2.csv", 950.0), ("ordinary-2.csv", 780.0))

    assert {entry["id"] for entry in client.container.visible} == {
        client.toast_channels[CELEBRATION_CHANNEL],
        client.run_toast_instance,
    }
    assert sorted(client.last_hidden) == sorted(first.values())
    assert client.toast_channels.keys() == {CELEBRATION_CHANNEL, RUN_VERDICT_CHANNEL}


def test_a_run_toast_after_navigating_away_and_back_gets_a_full_lifetime(monkeypatch):
    monkeypatch.setattr(
        scenario_selection, "get_visible_playlist_selector_options", lambda: []
    )
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])
    client = _Client()
    client.play(("first.csv", 780.0))
    client.container.advance(DEFAULT_AUTO_CLOSE_MS - 500)

    # Navigate away and back: a page's layout is rebuilt from scratch, so
    # every store it declares resets to its default. The container and the
    # registry sit outside every page's layout, so the toast is still up and
    # the registry still knows which instance it is showing.
    assert TOAST_CHANNEL_REGISTRY_STORE_ID not in _component_ids(run_history.layout())
    assert len(client.container.visible) == 1

    client.play(("second.csv", 790.0))

    assert len(client.container.visible) == 1
    assert (
        client.container.remaining_lifetime(client.run_toast_instance)
        >= DEFAULT_AUTO_CLOSE_MS
    )


def test_a_page_scoped_registry_would_leave_two_run_toasts_on_screen():
    # Why the store belongs in the shell: a page-layout store resets to its
    # default on remount, so the post-navigation emission would have no instance
    # id to hide and its fresh id would stack beside the toast already on
    # screen. This is the failure the test above is guarding against, asserted
    # directly.
    client = _Client()
    client.play(("first.csv", 780.0))
    client.container.advance(DEFAULT_AUTO_CLOSE_MS - 500)

    client.toast_channels = {}  # what a remounted page-layout store would say
    client.play(("second.csv", 790.0))

    assert len(client.container.visible) == 2


def test_the_toast_channel_registry_is_hosted_by_the_app_shell(monkeypatch):
    monkeypatch.setattr(
        scenario_selection, "get_visible_playlist_selector_options", lambda: []
    )
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])

    assert TOAST_CHANNEL_REGISTRY_STORE_ID in _component_ids(app_shell.layout())
    assert TOAST_CHANNEL_REGISTRY_STORE_ID not in _component_ids(run_history.layout())


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


def test_run_toast_emissions_carry_the_one_nominal_lifetime():
    """No more duration alternation: a fresh id is what re-arms the timer."""
    client = _Client()
    durations = []
    instances = []
    for run_id in ("first.csv", "second.csv", "third.csv"):
        client.play((run_id, 780.0))
        durations.append(client.container.visible[0]["autoClose"])
        instances.append(client.run_toast_instance)

    assert durations == [DEFAULT_AUTO_CLOSE_MS] * 3
    assert len(set(instances)) == 3
    client.container.advance(DEFAULT_AUTO_CLOSE_MS + 1)
    assert client.container.visible == []
