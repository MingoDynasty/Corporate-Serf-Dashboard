"""The app shell's drain: the one consumer of the run-event queue.

Facts travel and only this callback decides. Every assertion below is about
that invariant: the drain stamps liveness, names at most one celebrated run,
and publishes both so the pages never re-derive either. It also sends both
run toasts, the celebration and the plain one, and the section "which run
earns which toast" holds the table that says which run gets which.
"""

from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import dash
import pytest
from dash import dcc, html, no_update
from dash._callback import GLOBAL_CALLBACK_LIST

dash.Dash(__name__, use_pages=True, pages_folder="")

from source import app_shell  # noqa: E402
from source.app_shell import (  # noqa: E402
    CELEBRATION_STYLE_CONFETTI,
    CELEBRATION_STYLE_OFF,
    RUN_NOTIFICATIONS_OFF,
    RUN_NOTIFICATIONS_ON,
)
from source.components import scenario_selection  # noqa: E402
from source.my_queue.message_queue import NewFileMessage  # noqa: E402
from source.pages import run_history  # noqa: E402
from source.utilities.notifications import (  # noqa: E402
    CELEBRATION_CHANNEL,
    DEFAULT_AUTO_CLOSE_MS,
    RUN_VERDICT_CHANNEL,
    TOAST_CHANNEL_REGISTRY_STORE_ID,
)

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "source"
_NOW = datetime(2026, 8, 29, 12, 0, 0)


def _message(
    scenario_name: str = "Scenario A",
    *,
    run_id: str = "run-1.csv",
    score: float = 812.4,
    scenario_previous_best: float | None = 800.0,
    is_new_sensitivity: bool = False,
    age_seconds: float = 0.0,
    pace_constant: float | None = None,
) -> NewFileMessage:
    return NewFileMessage(
        datetime_created=_NOW - timedelta(seconds=age_seconds),
        is_new_sensitivity=is_new_sensitivity,
        run_id=run_id,
        scenario_name=scenario_name,
        scenario_previous_best=scenario_previous_best,
        score=score,
        sensitivity="34.64 cm/360",
        pace_constant=pace_constant,
    )


@pytest.fixture
def frozen_clock(monkeypatch):
    """Pin the drain's wall clock so message ages are exact."""

    class _Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return _NOW

    monkeypatch.setattr(app_shell, "datetime", _Clock)


def _window() -> float:
    """The freshness window this environment's config resolves to."""
    return app_shell._run_event_freshness_seconds()


def _drain_emission(
    monkeypatch,
    *messages,
    previous_batch=None,
    toast_channels=None,
    celebration_style=CELEBRATION_STYLE_CONFETTI,
    run_notifications=RUN_NOTIFICATIONS_ON,
):
    """Run one drain and return all four outputs, registry patch included."""
    monkeypatch.setattr(app_shell, "message_queue", deque(messages))
    return app_shell.publish_run_events(
        1,
        previous_batch,
        toast_channels or {},
        celebration_style,
        run_notifications,
    )


def _drain(
    monkeypatch,
    *messages,
    previous_batch=None,
    celebration_style=CELEBRATION_STYLE_CONFETTI,
    run_notifications=RUN_NOTIFICATIONS_ON,
):
    """Run one drain over a queue holding exactly these messages.

    Returns the batch and the toasts to show. The hide list and the registry
    patch are the channels' business, asserted through ``_drain_emission`` in
    the channel tests below.
    """
    batch, send, _hide, _patch = _drain_emission(
        monkeypatch,
        *messages,
        previous_batch=previous_batch,
        celebration_style=celebration_style,
        run_notifications=run_notifications,
    )
    return batch, send


def _on_channel(send, channel: str) -> list[dict]:
    """Pick one channel's toasts out of what a drain sent."""
    if send is no_update:
        return []
    return [toast for toast in send if toast["id"].startswith(f"{channel}-")]


def _celebrations(send) -> list[dict]:
    return _on_channel(send, CELEBRATION_CHANNEL)


def _run_toasts(send) -> list[dict]:
    return _on_channel(send, RUN_VERDICT_CHANNEL)


def _link(run_toast: dict) -> dcc.Link:
    """The one link in a run toast's message."""
    (link,) = [part for part in run_toast["message"] if isinstance(part, dcc.Link)]
    return link


def _named_run(run_toast: dict) -> str:
    """The id of the run a run toast is about, read from its link."""
    (run_id,) = parse_qs(urlsplit(_link(run_toast).href).query)["run"]
    return run_id


def _registry_writes(patch) -> dict[str, str | None]:
    """Read a per-key ``dash.Patch`` as the assignments it will apply."""
    if patch is no_update:
        return {}
    return {
        operation["location"][0]: operation["params"]["value"]
        for operation in patch._operations
    }


def test_an_empty_queue_publishes_nothing(monkeypatch, frozen_clock):
    batch, notifications = _drain(monkeypatch)

    assert batch is no_update
    assert notifications is no_update


def test_a_batch_carries_its_runs_in_order_with_the_stamped_decision(
    monkeypatch, frozen_clock
):
    batch, _notifications = _drain(
        monkeypatch,
        _message(run_id="first.csv", score=780.0),
        _message(run_id="second.csv", score=830.0),
    )

    assert [run["run_id"] for run in batch["runs"]] == ["first.csv", "second.csv"]
    assert batch["celebrated_run_id"] == "second.csv"
    assert batch["animation_sequence"] == 1
    assert all(run["is_live"] for run in batch["runs"])


def test_every_run_in_the_payload_carries_a_liveness_stamp(monkeypatch, frozen_clock):
    batch, _notifications = _drain(
        monkeypatch,
        _message(run_id="stale.csv", age_seconds=300.0),
        _message(run_id="fresh.csv", score=700.0),
    )

    assert [(run["run_id"], run["is_live"]) for run in batch["runs"]] == [
        ("stale.csv", False),
        ("fresh.csv", True),
    ]


def test_the_decision_names_the_newest_qualifying_run(monkeypatch, frozen_clock):
    # Two personal bests in one batch: one drain decides one celebration,
    # because one response drives one animation. The older one is plot-only.
    batch, _notifications = _drain(
        monkeypatch,
        _message(run_id="older-pb.csv", score=810.0),
        _message(
            "Scenario B",
            run_id="unrelated.csv",
            score=100.0,
            scenario_previous_best=500.0,
        ),
        _message(run_id="newer-pb.csv", score=830.0),
    )

    assert batch["celebrated_run_id"] == "newer-pb.csv"


def test_a_tie_with_the_previous_best_is_never_celebrated(monkeypatch, frozen_clock):
    batch, notifications = _drain(
        monkeypatch,
        _message(score=800.0, scenario_previous_best=800.0),
    )

    assert batch["celebrated_run_id"] is None
    assert _celebrations(notifications) == []


def test_a_scenarios_first_run_only_sets_the_baseline(monkeypatch, frozen_clock):
    batch, notifications = _drain(
        monkeypatch,
        _message(
            score=800.0,
            scenario_previous_best=None,
            is_new_sensitivity=True,
        ),
    )

    assert batch["celebrated_run_id"] is None
    assert _celebrations(notifications) == []


def test_a_new_sensitivity_run_can_still_win_the_celebration(monkeypatch, frozen_clock):
    # Scenario-wide, like the watchdog's own flag: the first run at a new
    # sensitivity beats the scenario best often enough to matter.
    batch, _notifications = _drain(
        monkeypatch,
        _message(run_id="new-sens.csv", score=900.0, is_new_sensitivity=True),
    )

    assert batch["celebrated_run_id"] == "new-sens.csv"


def test_the_animation_sequence_advances_only_on_a_celebration(
    monkeypatch, frozen_clock
):
    celebrated, _n = _drain(monkeypatch, _message(score=830.0))
    assert celebrated["animation_sequence"] == 1

    quiet, _n = _drain(
        monkeypatch,
        _message(score=700.0),
        previous_batch=celebrated,
    )
    assert quiet["animation_sequence"] == 1

    again, _n = _drain(monkeypatch, _message(score=830.0), previous_batch=quiet)
    # Same score twice over: a monotonic bump is what lets the second one play.
    assert again["animation_sequence"] == 2


def test_the_celebration_toast_is_emitted_exactly_when_a_run_is_named(
    monkeypatch, frozen_clock
):
    _batch, uncelebrated = _drain(monkeypatch, _message(score=700.0))
    assert _celebrations(uncelebrated) == []

    _batch, notifications = _drain(monkeypatch, _message(score=830.0))
    assert [payload["action"] for payload in notifications] == ["show"]
    assert notifications[0]["title"] == "New personal best"


def test_the_celebration_toast_stays_until_dismissed(monkeypatch, frozen_clock):
    # The builder passes ``auto_close=False`` explicitly, because
    # ``channel_toast`` carries the payload's lifetime through untouched rather
    # than stamping one. This is the one channel with no timer at all.
    _batch, notifications = _drain(monkeypatch, _message(score=830.0))

    assert [payload["autoClose"] for payload in notifications] == [False]


def test_the_celebration_toast_has_its_own_channel(monkeypatch, frozen_clock):
    # A dedicated lane is what lets the celebration survive the next ordinary
    # run toast instead of being replaced by it. Only a later celebration
    # replaces a celebration.
    _batch, notifications, _hide, patch = _drain_emission(
        monkeypatch, _message(score=830.0)
    )

    assert notifications[0]["id"].startswith(f"{CELEBRATION_CHANNEL}-")
    assert set(_registry_writes(patch)) == {CELEBRATION_CHANNEL}
    assert CELEBRATION_CHANNEL != RUN_VERDICT_CHANNEL


def test_a_later_celebration_replaces_the_one_on_screen(monkeypatch, frozen_clock):
    """The PR #261 family, reconciled onto the standing policy.

    Two personal bests inside one session used to be an ``update``-plus-``show``
    pair on a stable id. Now each shows a fresh instance and hides the one it
    replaces, which is what makes the second one visibly arrive -- while the
    contract it was ratified with holds: still its own lane, still no lifetime.
    """
    _batch, first, first_hide, first_patch = _drain_emission(
        monkeypatch, _message(run_id="pb-1.csv", score=830.0)
    )
    registry = _registry_writes(first_patch)

    _batch, second, second_hide, second_patch = _drain_emission(
        monkeypatch,
        _message(run_id="pb-2.csv", score=900.0),
        toast_channels=registry,
    )

    assert first_hide == []
    assert second[0]["id"] != first[0]["id"]
    assert second_hide == [first[0]["id"]]
    assert _registry_writes(second_patch) == {CELEBRATION_CHANNEL: second[0]["id"]}
    assert second[0]["autoClose"] is False


def test_a_celebration_alone_writes_only_its_own_channel(monkeypatch, frozen_clock):
    """The two toast families stay in separate lanes.

    The shell declares the registry and hide outputs both of its channels
    need, and an emission assigns only the keys it emits on. A whole-dict
    write here would carry a stale run-toast entry back over a newer one.
    """
    (spec,) = [
        spec
        for spec in GLOBAL_CALLBACK_LIST
        if "run-events-batch.data" in str(spec["output"])
    ]

    assert TOAST_CHANNEL_REGISTRY_STORE_ID in str(spec["output"])
    assert "hideNotifications" in str(spec["output"])
    assert spec["prevent_initial_call"] is True

    _batch, _send, hide, patch = _drain_emission(
        monkeypatch,
        _message(score=830.0),
        toast_channels={RUN_VERDICT_CHANNEL: "run-verdict-1"},
    )

    assert set(_registry_writes(patch)) == {CELEBRATION_CHANNEL}
    # The run toast on screen is about another run, and it stays.
    assert hide == []


def test_a_drain_that_toasts_nothing_touches_neither_the_hide_list_nor_the_registry(
    monkeypatch, frozen_clock
):
    _batch, send, hide, patch = _drain_emission(
        monkeypatch, _message(score=700.0), run_notifications=RUN_NOTIFICATIONS_OFF
    )

    assert (send, hide, patch) == (no_update, no_update, no_update)


# --- the setting -------------------------------------------------------


def test_off_publishes_the_batch_but_stamps_no_celebration(monkeypatch, frozen_clock):
    """Off silences the family, not the delivery.

    The batch still carries every run and its liveness stamp, because the page
    is every run's record whatever the setting says. The run is then an
    ordinary one, which the table's second row holds.
    """
    batch, notifications, _hide, patch = _drain_emission(
        monkeypatch,
        _message(score=830.0),
        celebration_style=CELEBRATION_STYLE_OFF,
    )

    assert [run["run_id"] for run in batch["runs"]] == ["run-1.csv"]
    assert batch["runs"][0]["is_live"] is True
    assert batch["celebrated_run_id"] is None
    assert _celebrations(notifications) == []
    assert CELEBRATION_CHANNEL not in _registry_writes(patch)


def test_off_holds_the_animation_sequence_where_it_was(monkeypatch, frozen_clock):
    celebrated, _n = _drain(monkeypatch, _message(score=830.0))

    quiet, _n = _drain(
        monkeypatch,
        _message(score=900.0),
        previous_batch=celebrated,
        celebration_style=CELEBRATION_STYLE_OFF,
    )

    assert quiet["animation_sequence"] == celebrated["animation_sequence"]


def test_an_unknown_stored_style_still_celebrates(monkeypatch, frozen_clock):
    # Only the exact off value silences the family. A style a later build
    # wrote, or a browser that lost its site data, has to fail towards the
    # celebration rather than into silence.
    batch, notifications = _drain(
        monkeypatch, _message(score=830.0), celebration_style="fireworks"
    )

    assert batch["celebrated_run_id"] == "run-1.csv"
    assert len(_celebrations(notifications)) == 1


def test_the_style_store_is_browser_local_and_defaults_to_confetti():
    store = _component(app_shell.layout(), app_shell.PB_CELEBRATION_STYLE_STORE_ID)

    assert store.storage_type == "local"
    assert store.data == CELEBRATION_STYLE_CONFETTI


def test_the_drain_reads_the_style_store_as_state():
    """State, not Input: flipping the setting must not replay a drained batch."""
    (spec,) = [
        spec
        for spec in GLOBAL_CALLBACK_LIST
        if "run-events-batch.data" in str(spec["output"])
    ]

    assert app_shell.PB_CELEBRATION_STYLE_STORE_ID not in {
        dep["id"] for dep in spec["inputs"]
    }
    assert (app_shell.PB_CELEBRATION_STYLE_STORE_ID, "data") in {
        (dep["id"], dep["property"]) for dep in spec["state"]
    }


def test_the_run_notifications_store_is_browser_local_and_starts_on():
    """The id and the off value are what a browser holds.

    Changing either turns run toasts back on for everyone who turned them
    off, so both are spelled out here and not read from the constants.
    """
    store = _component(app_shell.layout(), "run-notifications")

    assert app_shell.RUN_NOTIFICATIONS_STORE_ID == "run-notifications"
    assert RUN_NOTIFICATIONS_OFF == "off"
    assert store.storage_type == "local"
    assert store.data == RUN_NOTIFICATIONS_ON == "on"


def test_the_drain_reads_the_run_notifications_store_as_state():
    """State, not Input: flipping the setting must not toast a drained batch."""
    (spec,) = [
        spec
        for spec in GLOBAL_CALLBACK_LIST
        if "run-events-batch.data" in str(spec["output"])
    ]

    assert [(dep["id"], dep["property"]) for dep in spec["inputs"]] == [
        (app_shell.PB_CELEBRATION_INTERVAL_ID, "n_intervals")
    ]
    assert (app_shell.RUN_NOTIFICATIONS_STORE_ID, "data") in {
        (dep["id"], dep["property"]) for dep in spec["state"]
    }


def test_the_animation_is_driven_clientside_from_the_batch():
    """No server round trip for the burst, and no replay on a setting change."""
    (spec,) = [
        spec
        for spec in GLOBAL_CALLBACK_LIST
        if app_shell.PB_CELEBRATION_SIGNAL_STORE_ID in str(spec["output"])
    ]

    assert spec["clientside_function"] is not None
    assert [(dep["id"], dep["property"]) for dep in spec["inputs"]] == [
        (app_shell.RUN_EVENTS_BATCH_STORE_ID, "data")
    ]
    assert [(dep["id"], dep["property"]) for dep in spec["state"]] == [
        (app_shell.PB_CELEBRATION_STYLE_STORE_ID, "data")
    ]


def test_the_shell_hosts_the_drain_interval_and_the_batch_store(monkeypatch):
    ids = _component_ids(app_shell.layout())
    monkeypatch.setattr(
        scenario_selection, "get_visible_playlist_selector_options", lambda: []
    )
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])

    assert app_shell.PB_CELEBRATION_INTERVAL_ID in ids
    assert app_shell.RUN_EVENTS_BATCH_STORE_ID in ids
    # The page that listens to the store holds no copy of it.
    assert app_shell.RUN_EVENTS_BATCH_STORE_ID not in _component_ids(
        run_history.layout()
    )


def _component(root, component_id):
    """Find one component in a built layout by its id."""
    stack = [root]
    while stack:
        current = stack.pop()
        if getattr(current, "id", None) == component_id:
            return current
        children = getattr(current, "children", None)
        if children is None:
            continue
        stack.extend(children if isinstance(children, list) else [children])
    raise AssertionError(f"{component_id} is not in the layout")


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


# --- freshness ---------------------------------------------------------


def test_a_throttled_tick_old_run_is_still_live(monkeypatch, frozen_clock):
    # Chromium slows an interval in a tab hidden over five minutes to one tick
    # per minute (https://developer.chrome.com/blog/timer-throttling-in-chrome-88),
    # and a tab can stay hidden through a whole session, so ~60 s is an ordinary
    # case rather than the edge.
    batch, notifications = _drain(
        monkeypatch,
        _message(score=830.0, age_seconds=60.0),
    )

    assert batch["runs"][0]["is_live"] is True
    assert notifications is not no_update


def test_a_run_older_than_the_window_is_not_live(monkeypatch, frozen_clock):
    batch, notifications = _drain(
        monkeypatch,
        _message(score=830.0, age_seconds=_window() + 1),
    )

    assert batch["runs"][0]["is_live"] is False
    assert batch["celebrated_run_id"] is None
    assert notifications is no_update


def test_a_run_at_exactly_the_window_is_still_live(monkeypatch, frozen_clock):
    batch, _notifications = _drain(
        monkeypatch,
        _message(score=830.0, age_seconds=_window()),
    )

    assert batch["runs"][0]["is_live"] is True


def test_the_window_is_never_shorter_than_one_poll_period(monkeypatch, frozen_clock):
    """A slow poll must not stamp every run stale.

    `polling_interval` carries no product cap -- only the browser timer
    ceiling -- so a deliberately slow poll can make every run a whole period
    old by the time the drain sees it.
    A fixed cap below that period would then mark all of them stale and
    silently retire every toast liveness gates -- the celebration and the
    plain run toast alike -- while the plot kept updating.
    """
    monkeypatch.setattr(app_shell, "_drain_interval_ms", lambda: 300_000)

    batch, notifications = _drain(
        monkeypatch,
        _message(score=830.0, age_seconds=290.0),
    )

    assert app_shell._run_event_freshness_seconds() == 420.0
    assert batch["runs"][0]["is_live"] is True
    assert batch["celebrated_run_id"] == "run-1.csv"
    assert notifications is not no_update


def test_the_default_poll_period_leaves_the_ratified_cap_intact(monkeypatch):
    # 121 s rather than 120 s: the one poll period the cadence itself costs,
    # which no viewer can tell apart from the ratified figure.
    monkeypatch.setattr(app_shell, "_drain_interval_ms", lambda: 1000)

    assert app_shell._run_event_freshness_seconds() == 121.0


def test_a_recent_no_tab_backlog_still_celebrates(monkeypatch, frozen_clock):
    # Bounded replay, accepted deliberately: a player who reopens the tab
    # within the cap of the run wants the celebration, and the timestamp cannot
    # tell that case from a throttled hidden tab's, which must land.
    batch, notifications = _drain(
        monkeypatch,
        _message(run_id="a.csv", score=805.0, age_seconds=100.0),
        _message(run_id="b.csv", score=830.0, age_seconds=90.0),
    )

    assert batch["celebrated_run_id"] == "b.csv"
    assert notifications is not no_update


def test_an_old_no_tab_backlog_is_never_replayed(monkeypatch, frozen_clock):
    batch, notifications = _drain(
        monkeypatch,
        _message(run_id="a.csv", score=830.0, age_seconds=600.0),
        _message(run_id="b.csv", score=900.0, age_seconds=400.0),
    )

    assert batch["celebrated_run_id"] is None
    assert notifications is no_update
    # Still delivered, because the plot is every run's record.
    assert [run["run_id"] for run in batch["runs"]] == ["a.csv", "b.csv"]


def test_a_message_appended_mid_drain_is_seen_exactly_once(monkeypatch, frozen_clock):
    """Freshness needs no drain bookkeeping, and this is why.

    Every drain empties the queue, so a message a drain finds was never seen by
    an earlier one. A message appended while a drain is popping is caught by
    that drain or the next, exactly once either way.
    """

    class _RacingQueue(deque):
        def __init__(self, *args):
            super().__init__(*args)
            self._appended = False

        def popleft(self):
            item = super().popleft()
            if not self._appended:
                self._appended = True
                self.append(_message(run_id="late.csv", score=850.0))
            return item

    monkeypatch.setattr(
        app_shell,
        "message_queue",
        _RacingQueue([_message(run_id="early.csv", score=805.0)]),
    )

    batch, *_emission = app_shell.publish_run_events(
        1, None, {}, CELEBRATION_STYLE_CONFETTI, RUN_NOTIFICATIONS_ON
    )

    assert [run["run_id"] for run in batch["runs"]] == ["early.csv", "late.csv"]
    assert not app_shell.message_queue


# --- the toast body ----------------------------------------------------


def _celebration_message(
    score: float,
    previous_best: float,
    pace_constant: float | None = None,
) -> str:
    return app_shell._celebration_toast(
        {
            "run_id": "run-1.csv",
            "scenario_name": "Scenario A",
            "sensitivity": "34.64 cm/360",
            "score": score,
            "scenario_previous_best": previous_best,
            "pace_constant": pace_constant,
            "is_new_sensitivity": False,
            "is_live": True,
        }
    )["message"]


def test_the_celebration_message_reports_the_gain_over_the_previous_best():
    assert _celebration_message(830.0, 800.0) == (
        "Scenario A: 830.00. Up 3.8% on your previous best of 800.00."
    )


def test_a_time_scored_celebration_reports_how_much_faster_the_run_finished():
    # 115.59 s down to 103.83 s. As a share of the score it would read 1.3%.
    assert _celebration_message(896.17, 884.41, 1000.0) == (
        "Scenario A: 896.17. Finished 11.3% faster than your previous best of 884.41."
    )
    assert _celebration_message(896.17, 884.41) == (
        "Scenario A: 896.17. Up 1.3% on your previous best of 884.41."
    )


@pytest.mark.parametrize("previous_best", [0.0, -5.0])
def test_a_time_scored_celebration_needs_no_positive_previous_best(previous_best):
    # Pace needs positive times only, so the percentage this toast drops for a
    # score has a meaning here.
    assert _celebration_message(10.0, previous_best, 1000.0) == (
        f"Scenario A: 10.00. Finished {((1000 - previous_best) / 990 - 1) * 100:.1f}% "
        f"faster than your previous best of {previous_best:.2f}."
    )


def test_a_celebration_with_an_undefined_pace_reports_the_score_gain():
    # A score at the constant took no time at all, so there is no pace.
    assert _celebration_message(1000.0, 800.0, 1000.0) == (
        "Scenario A: 1000.00. Up 25.0% on your previous best of 800.00."
    )


def test_the_drain_carries_the_pace_constant_into_the_batch(monkeypatch, frozen_clock):
    batch, _celebration = _drain(
        monkeypatch,
        _message(run_id="timed.csv", pace_constant=1000.0),
        _message(run_id="ordinary.csv"),
    )

    assert [run["pace_constant"] for run in batch["runs"]] == [1000.0, None]


def test_a_drained_time_scored_personal_best_toasts_by_pace(monkeypatch, frozen_clock):
    _batch, (celebration,) = _drain(
        monkeypatch,
        _message(score=896.17, scenario_previous_best=884.41, pace_constant=1000.0),
    )

    assert celebration["title"] == "New personal best"
    assert celebration["message"] == (
        "Scenario A: 896.17. Finished 11.3% faster than your previous best of 884.41."
    )


@pytest.mark.parametrize("previous_best", [0.0, -5.0])
def test_a_nonpositive_previous_best_drops_the_percentage(previous_best):
    # No percentage to give at zero, and a negative one would read backwards --
    # the same division the threshold verdict declines, for the same reason.
    assert _celebration_message(830.0, previous_best) == (
        f"Scenario A: 830.00. Your previous best was {previous_best:.2f}."
    )


# --- which run earns which toast -----------------------------------------
#
# The six rows of the table under "A new personal best" in the Run toasts
# decision, one test per row, each named for its row. A row is the batch's
# newest live run, the celebration setting, the Run notifications setting, and
# what is on screen. ``_message``'s default previous best is 800.0, so a score
# of 830.0 sets a new PB and 780.0 does not.

_BOTH_STYLES = [CELEBRATION_STYLE_CONFETTI, CELEBRATION_STYLE_OFF]
_BOTH_NOTIFICATION_VALUES = [RUN_NOTIFICATIONS_ON, RUN_NOTIFICATIONS_OFF]


@pytest.mark.parametrize("run_notifications", _BOTH_NOTIFICATION_VALUES)
def test_row_1_a_new_pb_with_the_celebration_on_shows_the_celebration_alone(
    monkeypatch, frozen_clock, run_notifications
):
    """A run the celebration announces keeps the celebration as its one toast."""
    batch, send, _hide, patch = _drain_emission(
        monkeypatch,
        _message(run_id="pb.csv", score=830.0),
        run_notifications=run_notifications,
    )

    assert batch["celebrated_run_id"] == "pb.csv"
    assert [toast["title"] for toast in send] == ["New personal best"]
    assert _run_toasts(send) == []
    assert set(_registry_writes(patch)) == {CELEBRATION_CHANNEL}


def test_row_2_a_new_pb_with_the_celebration_off_shows_the_plain_toast(
    monkeypatch, frozen_clock
):
    batch, send, _hide, patch = _drain_emission(
        monkeypatch,
        _message(run_id="pb.csv", score=830.0),
        celebration_style=CELEBRATION_STYLE_OFF,
    )

    assert batch["celebrated_run_id"] is None
    assert [toast["title"] for toast in send] == ["New run detected"]
    assert _named_run(send[0]) == "pb.csv"
    assert set(_registry_writes(patch)) == {RUN_VERDICT_CHANNEL}


def test_row_3_an_earlier_pb_in_the_batch_shows_both_toasts_about_different_runs(
    monkeypatch, frozen_clock
):
    """Two toasts in one response, and one registry patch that assigns both keys.

    An output takes one value and two patches cannot be joined, so the one
    patch has to carry both channels' assignments. Each is still a per-key
    write: the registry is never sent back whole.
    """
    batch, send, hide, patch = _drain_emission(
        monkeypatch,
        _message(
            "Scenario B",
            run_id="pb.csv",
            score=900.0,
            scenario_previous_best=700.0,
        ),
        # Below its own previous best, so the batch has exactly one personal
        # best and the newest-qualifying rule cannot pick this one.
        _message("Scenario A", run_id="ordinary.csv", score=780.0),
        toast_channels={
            CELEBRATION_CHANNEL: "pb-celebration-old",
            RUN_VERDICT_CHANNEL: "run-verdict-old",
            "unrelated": "unrelated-1",
        },
    )

    (celebration,) = _celebrations(send)
    (run_toast,) = _run_toasts(send)
    assert len(send) == 2
    assert batch["celebrated_run_id"] == "pb.csv"
    assert celebration["message"].startswith("Scenario B: 900.00.")
    assert _named_run(run_toast) == "ordinary.csv"
    assert [operation["operation"] for operation in patch._operations] == [
        "Assign",
        "Assign",
    ]
    assert _registry_writes(patch) == {
        CELEBRATION_CHANNEL: celebration["id"],
        RUN_VERDICT_CHANNEL: run_toast["id"],
    }
    # Each replaces its own channel's instance, and nothing else is hidden.
    assert sorted(hide) == ["pb-celebration-old", "run-verdict-old"]


def test_row_3_holds_when_both_runs_are_on_one_scenario(monkeypatch, frozen_clock):
    """The shell picks the batch's newest run, whatever its scenario."""
    _batch, send = _drain(
        monkeypatch,
        _message(run_id="pb.csv", score=830.0),
        _message(run_id="after-it.csv", score=780.0, scenario_previous_best=830.0),
    )

    assert [toast["title"] for toast in send] == [
        "New personal best",
        "New run detected",
    ]
    assert _named_run(send[1]) == "after-it.csv"


@pytest.mark.parametrize("celebration_style", _BOTH_STYLES)
def test_row_4_a_run_that_set_no_pb_shows_the_plain_toast(
    monkeypatch, frozen_clock, celebration_style
):
    batch, send, hide, patch = _drain_emission(
        monkeypatch,
        _message(run_id="ordinary.csv", score=780.0),
        celebration_style=celebration_style,
    )

    assert batch["celebrated_run_id"] is None
    assert [toast["title"] for toast in send] == ["New run detected"]
    assert _named_run(send[0]) == "ordinary.csv"
    assert hide == []
    assert set(_registry_writes(patch)) == {RUN_VERDICT_CHANNEL}


@pytest.mark.parametrize(
    ("scores", "celebration_style", "titles"),
    [
        ([780.0], CELEBRATION_STYLE_CONFETTI, []),
        ([780.0], CELEBRATION_STYLE_OFF, []),
        ([830.0], CELEBRATION_STYLE_CONFETTI, ["New personal best"]),
        ([830.0], CELEBRATION_STYLE_OFF, []),
        # An earlier run set the PB: with the plain toast off, row 3's pair is
        # the celebration alone.
        ([830.0, 780.0], CELEBRATION_STYLE_CONFETTI, ["New personal best"]),
    ],
)
def test_row_5_run_notifications_off_sends_no_plain_toast_and_the_celebration_follows_its_own_setting(  # noqa: E501
    monkeypatch, frozen_clock, scores, celebration_style, titles
):
    batch, send, _hide, patch = _drain_emission(
        monkeypatch,
        *[
            _message(run_id=f"run-{index}.csv", score=score)
            for index, score in enumerate(scores)
        ],
        celebration_style=celebration_style,
        run_notifications=RUN_NOTIFICATIONS_OFF,
    )

    assert len(batch["runs"]) == len(scores)
    assert _run_toasts(send) == []
    assert [toast["title"] for toast in _celebrations(send)] == titles
    assert RUN_VERDICT_CHANNEL not in _registry_writes(patch)


@pytest.mark.parametrize("celebration_style", _BOTH_STYLES)
@pytest.mark.parametrize("run_notifications", _BOTH_NOTIFICATION_VALUES)
def test_row_6_a_batch_with_no_live_run_shows_nothing(
    monkeypatch, frozen_clock, celebration_style, run_notifications
):
    """Still published, because the page is every run's record."""
    batch, send, hide, patch = _drain_emission(
        monkeypatch,
        _message(run_id="a.csv", score=830.0, age_seconds=_window() + 60),
        _message(run_id="b.csv", score=780.0, age_seconds=_window() + 1),
        celebration_style=celebration_style,
        run_notifications=run_notifications,
    )

    assert [(run["run_id"], run["is_live"]) for run in batch["runs"]] == [
        ("a.csv", False),
        ("b.csv", False),
    ]
    assert (send, hide, patch) == (no_update, no_update, no_update)


# --- the plain toast -------------------------------------------------------


def test_a_batch_of_several_runs_gets_one_toast_for_its_newest_run(
    monkeypatch, frozen_clock
):
    """The other runs earn none, and the title does not count them."""
    _batch, send = _drain(
        monkeypatch,
        _message("Scenario A", run_id="a.csv", score=700.0),
        _message("Scenario B", run_id="b.csv", score=760.0),
        _message("Scenario C", run_id="c.csv", score=780.0),
    )

    (run_toast,) = send
    assert run_toast["title"] == "New run detected"
    assert _named_run(run_toast) == "c.csv"
    assert run_toast["message"][0].children == "Scenario C"


def test_the_runs_before_a_celebrated_newest_run_earn_no_toast(
    monkeypatch, frozen_clock
):
    _batch, send = _drain(
        monkeypatch,
        _message("Scenario B", run_id="ordinary.csv", score=780.0),
        _message("Scenario A", run_id="pb.csv", score=830.0),
    )

    assert [toast["title"] for toast in send] == ["New personal best"]


def test_the_run_toast_is_blue_and_holds_the_scenario_and_a_link_and_nothing_else(
    monkeypatch, frozen_clock
):
    """No score, percentage, sensitivity, or goal: the page holds the verdict."""
    _batch, send = _drain(
        monkeypatch,
        _message("Scenario A", score=780.0, pace_constant=1000.0),
    )

    (run_toast,) = send
    assert run_toast["action"] == "show"
    assert run_toast["title"] == "New run detected"
    assert run_toast["color"] == "blue"
    assert run_toast["autoClose"] == DEFAULT_AUTO_CLOSE_MS
    assert "fontisto-line-chart.svg" in str(run_toast["icon"].to_plotly_json())

    scenario_line, link = run_toast["message"]
    # A line of its own: a block, so the link starts on the line below.
    assert isinstance(scenario_line, html.Div)
    assert scenario_line.children == "Scenario A"
    assert link.children == "Open in Run History"
    assert link.className == app_shell.RUN_TOAST_LINK_CLASS


def test_the_link_is_a_dcc_link_to_run_history_with_the_encoded_name_and_the_run(
    monkeypatch, frozen_clock
):
    """A ``dmc.Anchor`` would decode the name, and an ``html.A`` reload the app."""
    name = "Whisphere Small & Slow 70% +#? x/y"
    run_id = f"{name} - Challenge - 2026.10.13-18.00.00 Stats.csv"

    _batch, send = _drain(monkeypatch, _message(name, run_id=run_id, score=780.0))
    link = _link(send[0])

    assert type(link) is dcc.Link
    # Unset is dcc.Link's own default: the page changes with no reload.
    assert getattr(link, "refresh", False) is False
    address = urlsplit(link.href)
    assert address.path == "/run-history"
    assert parse_qs(address.query) == {"scenario": [name], "run": [run_id]}
    for encoded in ("%26", "%25", "%2B", "%23"):
        assert encoded in link.href
    # The one function that builds a scenario's address built it, and it
    # carries no playlist: the shell does not know the page's filter.
    assert link.href == app_shell.scenario_run_history_href(name, run_id=run_id)
    assert "playlist_code" not in link.href


def test_two_runs_of_one_scenario_link_to_two_addresses(monkeypatch, frozen_clock):
    """A link to the address the page already holds would do nothing."""
    _batch, first = _drain(monkeypatch, _message(run_id="first.csv", score=780.0))
    _batch, second = _drain(monkeypatch, _message(run_id="second.csv", score=780.0))

    assert _link(first[0]).href != _link(second[0]).href
    assert (
        parse_qs(urlsplit(_link(first[0]).href).query)["scenario"]
        == parse_qs(urlsplit(_link(second[0]).href).query)["scenario"]
        == ["Scenario A"]
    )


@pytest.mark.parametrize("stored", [None, "", "quiet", "OFF", True, False, 0])
def test_only_the_exact_off_value_silences_the_run_toast(
    monkeypatch, frozen_clock, stored
):
    """A value this build does not know, or a store the browser lost, shows it."""
    _batch, send = _drain(monkeypatch, _message(score=780.0), run_notifications=stored)

    assert [toast["title"] for toast in send] == ["New run detected"]


def test_a_run_toast_replaces_the_one_on_screen_and_leaves_a_celebration_up(
    monkeypatch, frozen_clock
):
    _batch, send, hide, patch = _drain_emission(
        monkeypatch,
        _message(score=780.0),
        toast_channels={
            CELEBRATION_CHANNEL: "pb-celebration-1",
            RUN_VERDICT_CHANNEL: "run-verdict-1",
        },
    )

    assert hide == ["run-verdict-1"]
    assert _registry_writes(patch) == {RUN_VERDICT_CHANNEL: send[0]["id"]}
    assert send[0]["id"] != "run-verdict-1"


def test_the_shell_is_the_only_code_that_names_the_run_toasts_channel():
    """Each channel has exactly one producing callback, and this one's is the drain.

    Replace-in-place relies on it: a second producer would read a registry the
    first had not yet written, and leave two run toasts on screen.
    """
    naming = sorted(
        path.relative_to(SOURCE_ROOT).as_posix()
        for path in SOURCE_ROOT.rglob("*.py")
        if "RUN_VERDICT_CHANNEL" in (text := path.read_text(encoding="utf-8"))
        or '"run-verdict"' in text
    )

    assert naming == ["app_shell.py", "utilities/notifications.py"]
