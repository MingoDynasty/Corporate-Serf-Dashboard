"""The app shell's drain: the one consumer of the run-event queue.

Facts travel and only this callback decides. Every assertion below is about
that invariant: the drain stamps liveness, names at most one celebrated run,
and publishes both so the pages never re-derive either.
"""

from collections import deque
from datetime import datetime, timedelta

import dash
import pytest
from dash import no_update
from dash._callback import GLOBAL_CALLBACK_LIST

dash.Dash(__name__, use_pages=True, pages_folder="")

from source import app_shell  # noqa: E402
from source.my_queue.message_queue import NewFileMessage  # noqa: E402
from source.pages import home  # noqa: E402
from source.utilities.notifications import (  # noqa: E402
    CELEBRATION_CHANNEL,
    TOAST_CHANNEL_REGISTRY_STORE_ID,
)

_NOW = datetime(2026, 8, 29, 12, 0, 0)


def _message(
    scenario_name: str = "Scenario A",
    *,
    run_id: str = "run-1.csv",
    score: float = 812.4,
    scenario_previous_best: float | None = 800.0,
    is_new_sensitivity: bool = False,
    nth_score: int = 2,
    age_seconds: float = 0.0,
) -> NewFileMessage:
    return NewFileMessage(
        datetime_created=_NOW - timedelta(seconds=age_seconds),
        is_new_sensitivity=is_new_sensitivity,
        nth_score=nth_score,
        run_id=run_id,
        scenario_name=scenario_name,
        scenario_previous_best=scenario_previous_best,
        score=score,
        sensitivity="34.64 cm/360",
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


def _drain_emission(monkeypatch, *messages, previous_batch=None, toast_channels=None):
    """Run one drain and return all four outputs, registry patch included."""
    monkeypatch.setattr(app_shell, "message_queue", deque(messages))
    return app_shell.publish_run_events(1, previous_batch, toast_channels or {})


def _drain(monkeypatch, *messages, previous_batch=None):
    """Run one drain over a queue holding exactly these messages.

    Returns the batch and the toasts to show. The hide list and the registry
    patch are the celebration channel's business, asserted through
    ``_drain_emission`` in the channel tests below.
    """
    batch, send, _hide, _patch = _drain_emission(
        monkeypatch, *messages, previous_batch=previous_batch
    )
    return batch, send


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
    assert notifications is no_update


def test_a_scenarios_first_run_only_sets_the_baseline(monkeypatch, frozen_clock):
    batch, notifications = _drain(
        monkeypatch,
        _message(
            score=800.0,
            scenario_previous_best=None,
            is_new_sensitivity=True,
            nth_score=1,
        ),
    )

    assert batch["celebrated_run_id"] is None
    assert notifications is no_update


def test_a_new_sensitivity_run_can_still_win_the_celebration(monkeypatch, frozen_clock):
    # Scenario-wide, like the watchdog's own flag: the first run at a new
    # sensitivity beats the scenario best often enough to matter.
    batch, _notifications = _drain(
        monkeypatch,
        _message(
            run_id="new-sens.csv", score=900.0, is_new_sensitivity=True, nth_score=1
        ),
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
    _batch, silent = _drain(monkeypatch, _message(score=700.0))
    assert silent is no_update

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
    assert CELEBRATION_CHANNEL != home._RUN_VERDICT_CHANNEL


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


def test_the_shell_writes_only_the_celebration_channel(monkeypatch, frozen_clock):
    """The two toast families stay in separate lanes.

    The shell declares the registry and hide outputs it needs for its own
    channel, and its emission assigns exactly one key. A whole-dict write here
    would let the shell clobber the page's run-verdict entry.
    """
    (spec,) = [
        spec
        for spec in GLOBAL_CALLBACK_LIST
        if "run-events-batch.data" in str(spec["output"])
    ]

    assert TOAST_CHANNEL_REGISTRY_STORE_ID in str(spec["output"])
    assert "hideNotifications" in str(spec["output"])
    assert spec["prevent_initial_call"] is True

    _batch, _send, _hide, patch = _drain_emission(
        monkeypatch, _message(score=830.0), toast_channels={"run-verdict": "verdict-1"}
    )

    assert set(_registry_writes(patch)) == {CELEBRATION_CHANNEL}


def test_a_quiet_drain_touches_neither_the_hide_list_nor_the_registry(
    monkeypatch, frozen_clock
):
    _batch, send, hide, patch = _drain_emission(monkeypatch, _message(score=700.0))

    assert (send, hide, patch) == (no_update, no_update, no_update)


def test_the_shell_hosts_the_drain_interval_and_the_batch_store(monkeypatch):
    ids = _component_ids(app_shell.layout())
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])

    assert app_shell.PB_CELEBRATION_INTERVAL_ID in ids
    assert app_shell.RUN_EVENTS_BATCH_STORE_ID in ids
    assert app_shell.RUN_EVENTS_BATCH_STORE_ID not in _component_ids(home.layout())


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
    # Chromium slows a hidden tab's interval to about one tick per minute, and
    # the tab is occluded during play, so ~60 s is the ordinary case rather
    # than the edge.
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

    `polling_interval` is an unconstrained config key, so a deliberately slow
    poll can make every run a whole period old by the time the drain sees it.
    A fixed cap below that period would then mark all of them stale and
    silently retire every toast liveness gates -- the celebration and the
    page's ordinary run toasts alike -- while the plot kept updating.
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

    batch, *_emission = app_shell.publish_run_events(1, None, {})

    assert [run["run_id"] for run in batch["runs"]] == ["early.csv", "late.csv"]
    assert not app_shell.message_queue


# --- the toast body ----------------------------------------------------


def _celebration_message(score: float, previous_best: float) -> str:
    return app_shell._celebration_toast(
        {
            "run_id": "run-1.csv",
            "scenario_name": "Scenario A",
            "sensitivity": "34.64 cm/360",
            "nth_score": 1,
            "score": score,
            "scenario_previous_best": previous_best,
            "is_new_sensitivity": False,
            "is_live": True,
        }
    )["message"]


def test_the_celebration_message_reports_the_gain_over_the_previous_best():
    assert _celebration_message(830.0, 800.0) == (
        "Scenario A: 830.00. Up 3.8% on your previous best of 800.00."
    )


@pytest.mark.parametrize("previous_best", [0.0, -5.0])
def test_a_nonpositive_previous_best_drops_the_percentage(previous_best):
    # No percentage to give at zero, and a negative one would read backwards --
    # the same division the threshold verdict declines, for the same reason.
    assert _celebration_message(830.0, previous_best) == (
        f"Scenario A: 830.00. Your previous best was {previous_best:.2f}."
    )


def test_a_mixed_batch_toasts_the_celebration_and_the_live_ordinary_run(
    monkeypatch, frozen_clock
):
    """Up to two toasts per batch, one per run, and never a digest.

    A personal best in one scenario beside an ordinary live run in the selected
    one: each toast reports its own run exactly once. The contract is per run,
    not per batch, which is why two toasts here is correct.
    """
    batch, celebration = _drain(
        monkeypatch,
        _message(
            "Scenario B",
            run_id="pb.csv",
            score=900.0,
            scenario_previous_best=700.0,
        ),
        # Below its own previous best, so the batch has exactly one
        # personal best and the newest-qualifying rule cannot pick this one.
        _message("Scenario A", run_id="ordinary.csv", score=780.0),
    )
    _target, payload = home._summarize_run_events(batch, "Scenario A", False)
    verdict = home._build_run_event_notification(
        payload,
        "Scenario A",
        5,
        95.0,
        True,
        True,
    )

    assert batch["celebrated_run_id"] == "pb.csv"
    assert celebration[0]["id"].startswith(f"{CELEBRATION_CHANNEL}-")
    assert celebration[0]["message"].startswith("Scenario B: 900.00.")
    assert verdict["id"] == home._RUN_VERDICT_CHANNEL
    assert verdict["message"].startswith("Scenario A — 780.00")
