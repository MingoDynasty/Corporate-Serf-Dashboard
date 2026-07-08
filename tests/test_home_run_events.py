import json
from collections import deque
from datetime import datetime
from types import SimpleNamespace

import dash
import plotly.graph_objects as go
from dash import no_update

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.my_queue.message_queue import NewFileMessage  # noqa: E402
from source.pages import home  # noqa: E402


def _message(
    scenario_name: str,
    *,
    nth_score: int = 2,
    score: float = 812.4,
    previous_high_score: float | None = 800.0,
) -> NewFileMessage:
    return NewFileMessage(
        datetime_created=datetime(2026, 7, 6, 12),
        nth_score=nth_score,
        previous_high_score=previous_high_score,
        scenario_name=scenario_name,
        score=score,
        sensitivity="34.64 cm/360",
    )


def _payload(
    scenario_name: str = "Scenario A",
    *,
    count: int = 1,
    nth_score: int = 2,
    score: float = 812.4,
    previous_high_score: float | None = 800.0,
) -> home.RunEventsPayload:
    return {
        "count": count,
        "latest": {
            "scenario_name": scenario_name,
            "sensitivity": "34.64 cm/360",
            "nth_score": nth_score,
            "score": score,
            "previous_high_score": previous_high_score,
        },
    }


def _walk_component_tree(component):
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if not isinstance(children, list):
        children = [children]
    for child in children:
        yield from _walk_component_tree(child)


def test_home_layout_initial_graph_has_empty_state(monkeypatch):
    monkeypatch.setattr(home, "get_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])

    page = home.layout()
    graph = next(
        component
        for component in _walk_component_tree(page)
        if getattr(component, "id", None) == "graph-content"
    )
    cached_plot = next(
        component
        for component in _walk_component_tree(page)
        if getattr(component, "id", None) == "cached-plot"
    )

    figure = graph.figure
    cached_plot_data = json.loads(cached_plot.data)

    assert "No scenario selected" in figure["layout"]["annotations"][0]["text"]
    assert figure["layout"]["annotations"][1]["text"] == (
        "Select a scenario to see your score history."
    )
    assert figure["layout"]["dragmode"] is False
    assert figure["layout"]["xaxis"]["visible"] is False
    assert figure["layout"]["yaxis"]["visible"] is False
    assert (
        "No scenario selected" in cached_plot_data["layout"]["annotations"][0]["text"]
    )
    assert cached_plot_data["layout"]["annotations"][1]["text"] == (
        "Select a scenario to see your score history."
    )
    assert cached_plot_data["layout"]["dragmode"] is False


def test_graph_theme_callback_falls_back_to_initial_empty_state():
    figure = home.apply_light_dark_theme_to_graph("light", None)

    assert "No scenario selected" in figure.layout.annotations[0].text
    assert figure.layout.annotations[1].text == (
        "Select a scenario to see your score history."
    )
    assert figure.layout.dragmode is False
    assert figure.layout.xaxis.visible is False
    assert figure.layout.yaxis.visible is False


def test_drain_run_events_summarizes_single_scenario_backlog(monkeypatch):
    queue = deque([_message("Scenario A"), _message("Scenario A", score=830.1)])
    monkeypatch.setattr(home, "message_queue", queue)

    target, payload = home._drain_run_events("Scenario A", False)

    assert target == "Scenario A"
    assert payload == _payload(
        count=2,
        score=830.1,
    )
    assert not queue
    json.dumps(payload)


def test_drain_run_events_auto_change_lands_on_latest_scenario(monkeypatch):
    queue = deque(
        [
            _message("Scenario B", score=700.0),
            _message("Scenario A", score=800.0),
            _message("Scenario B", score=830.1),
        ]
    )
    monkeypatch.setattr(home, "message_queue", queue)

    target, payload = home._drain_run_events("Scenario A", True)

    assert target == "Scenario B"
    assert payload == _payload(
        "Scenario B",
        count=2,
        score=830.1,
    )
    assert not queue


def test_drain_run_events_without_auto_change_discards_other_scenarios(monkeypatch):
    queue = deque(
        [
            _message("Scenario B"),
            _message("Scenario A", score=820.0),
            _message("Scenario B", score=830.1),
        ]
    )
    monkeypatch.setattr(home, "message_queue", queue)

    target, payload = home._drain_run_events("Scenario A", False)

    assert target == "Scenario A"
    assert payload == _payload(score=820.0)
    assert not queue


def test_drain_run_events_returns_no_payload_when_nothing_relevant(monkeypatch):
    queue = deque([_message("Scenario B")])
    monkeypatch.setattr(home, "message_queue", queue)

    assert home._drain_run_events("Scenario A", False) == ("Scenario A", None)
    assert not queue


def test_check_for_new_data_updates_store_once_and_dropdown_at_most_once(monkeypatch):
    queue = deque([_message("Scenario A"), _message("Scenario B")])
    monkeypatch.setattr(home, "message_queue", queue)

    payload, target = home.check_for_new_data(1, True, "Scenario A")
    second_payload, second_target = home.check_for_new_data(1, True, "Scenario B")

    assert payload == _payload("Scenario B")
    assert target == "Scenario B"
    assert second_payload is no_update
    assert second_target is no_update


def test_drain_run_events_tolerates_popleft_race(monkeypatch):
    class RacingQueue:
        def __init__(self):
            self.calls = 0

        def popleft(self):
            self.calls += 1
            if self.calls == 1:
                return _message("Scenario A")
            raise IndexError

    monkeypatch.setattr(home, "message_queue", RacingQueue())

    target, payload = home._drain_run_events("Scenario A", False)

    assert target == "Scenario A"
    assert payload == _payload()


def test_single_run_notifications_preserve_top_n_and_fallback_toasts():
    notifications = home._build_run_event_notifications(
        _payload(previous_high_score=None),
        "Scenario A",
        top_n_scores=5,
        score_threshold_percentage=100.0,
        score_threshold_notification_switch=True,
    )

    assert [notification["id"] for notification in notifications] == [
        "new-top-n-score-notification",
        "graph-updated-notification",
    ]
    assert notifications[0]["message"] == (
        "34.64 cm/360 has a new 2nd place score: 812.40"
    )
    assert notifications[1]["message"] == "Graph updated!"


def test_single_run_threshold_notification_uses_previous_high_score():
    notifications = home._build_run_event_notifications(
        _payload(score=830.0, previous_high_score=800.0),
        "Scenario A",
        top_n_scores=5,
        score_threshold_percentage=102.5,
        score_threshold_notification_switch=True,
    )

    assert [notification["id"] for notification in notifications] == [
        "new-top-n-score-notification",
        "score-threshold-notification",
    ]
    assert notifications[1]["message"] == (
        "Current score percentage (103.8%) successfully passed the score "
        "threshold! Ready to move onto the next scenario."
    )


def test_single_run_threshold_notification_passes_at_exact_threshold():
    notifications = home._build_run_event_notifications(
        _payload(score=820.0, previous_high_score=800.0),
        "Scenario A",
        top_n_scores=5,
        score_threshold_percentage=102.5,
        score_threshold_notification_switch=True,
    )

    assert notifications[1]["color"] == "green"
    assert notifications[1]["message"] == (
        "Current score percentage (102.5%) successfully passed the score "
        "threshold! Ready to move onto the next scenario."
    )


def test_single_run_threshold_notification_passes_new_pb_above_100_percent_goal():
    notifications = home._build_run_event_notifications(
        _payload(score=850.0, previous_high_score=800.0),
        "Scenario A",
        top_n_scores=5,
        score_threshold_percentage=105.0,
        score_threshold_notification_switch=True,
    )

    assert notifications[1]["color"] == "green"
    assert notifications[1]["message"] == (
        "Current score percentage (106.2%) successfully passed the score "
        "threshold! Ready to move onto the next scenario."
    )


def test_single_run_threshold_notification_fails_new_pb_short_of_100_plus_goal():
    notifications = home._build_run_event_notifications(
        _payload(score=820.0, previous_high_score=800.0),
        "Scenario A",
        top_n_scores=5,
        score_threshold_percentage=105.0,
        score_threshold_notification_switch=True,
    )

    assert notifications[1]["color"] == "yellow"
    assert notifications[1]["message"] == (
        "Current score percentage (102.5%) failed to meet the score threshold. "
        "Keep grinding..."
    )


def test_single_run_threshold_failure_preserves_legacy_toast():
    notifications = home._build_run_event_notifications(
        _payload(score=780.0, previous_high_score=800.0),
        "Scenario A",
        top_n_scores=5,
        score_threshold_percentage=98.75,
        score_threshold_notification_switch=True,
    )

    assert [notification["id"] for notification in notifications] == [
        "new-top-n-score-notification",
        "score-threshold-notification",
    ]
    assert notifications[1]["message"] == (
        "Current score percentage (97.5%) failed to meet the score threshold. "
        "Keep grinding..."
    )


def test_single_run_threshold_notification_ignores_empty_percentage():
    for empty_percentage in (None, ""):
        notifications = home._build_run_event_notifications(
            _payload(score=780.0, previous_high_score=800.0),
            "Scenario A",
            top_n_scores=5,
            score_threshold_percentage=empty_percentage,
            score_threshold_notification_switch=True,
        )

        assert [notification["id"] for notification in notifications] == [
            "new-top-n-score-notification",
            "graph-updated-notification",
        ]


def test_backlog_notification_is_one_scenario_named_summary():
    notifications = home._build_run_event_notifications(
        _payload(count=3, score=780.0, previous_high_score=800.0),
        "Scenario A",
        top_n_scores=5,
        score_threshold_percentage=98.75,
        score_threshold_notification_switch=True,
    )

    assert len(notifications) == 1
    assert notifications[0]["id"] == "run-summary-notification"
    assert notifications[0]["color"] == "yellow"
    assert notifications[0]["message"] == (
        "3 new Scenario A runs while you were away. Latest: 34.64 cm/360 has "
        "a new 2nd place score: 780.00. Current score percentage (97.5%) "
        "failed to meet the score threshold. Keep grinding..."
    )


def test_backlog_threshold_summary_ignores_empty_percentage():
    for empty_percentage in (None, ""):
        notifications = home._build_run_event_notifications(
            _payload(count=3, score=780.0, previous_high_score=800.0),
            "Scenario A",
            top_n_scores=5,
            score_threshold_percentage=empty_percentage,
            score_threshold_notification_switch=True,
        )

        assert len(notifications) == 1
        assert notifications[0]["color"] == "blue"
        assert notifications[0]["message"] == (
            "3 new Scenario A runs while you were away. Latest: 34.64 cm/360 has "
            "a new 2nd place score: 780.00."
        )


def test_backlog_threshold_summary_passes_at_exact_threshold():
    notifications = home._build_run_event_notifications(
        _payload(count=3, score=820.0, previous_high_score=800.0),
        "Scenario A",
        top_n_scores=5,
        score_threshold_percentage=102.5,
        score_threshold_notification_switch=True,
    )

    assert len(notifications) == 1
    assert notifications[0]["color"] == "green"
    assert notifications[0]["message"] == (
        "3 new Scenario A runs while you were away. Latest: 34.64 cm/360 has "
        "a new 2nd place score: 820.00. Current score percentage (102.5%) "
        "successfully passed the score threshold! Ready to move onto the next "
        "scenario."
    )


def test_backlog_threshold_summary_passes_new_pb_above_100_percent_goal():
    notifications = home._build_run_event_notifications(
        _payload(count=3, score=850.0, previous_high_score=800.0),
        "Scenario A",
        top_n_scores=5,
        score_threshold_percentage=105.0,
        score_threshold_notification_switch=True,
    )

    assert len(notifications) == 1
    assert notifications[0]["color"] == "green"
    assert notifications[0]["message"] == (
        "3 new Scenario A runs while you were away. Latest: 34.64 cm/360 has "
        "a new 2nd place score: 850.00. Current score percentage (106.2%) "
        "successfully passed the score threshold! Ready to move onto the next "
        "scenario."
    )


def test_notifications_ignore_payload_for_another_scenario():
    assert (
        home._build_run_event_notifications(
            _payload("Scenario B"),
            "Scenario A",
            top_n_scores=5,
            score_threshold_percentage=100.0,
            score_threshold_notification_switch=True,
        )
        == []
    )


def test_generate_graph_returns_empty_state_before_scenario_selection():
    plot_json, notifications = home.generate_graph(
        None,
        None,
        5,
        "2026-07-01",
        "score_vs_time",
        False,
        False,
        False,
        95,
        True,
        None,
    )

    plot = json.loads(plot_json)

    assert notifications is no_update
    assert "No scenario selected" in plot["layout"]["annotations"][0]["text"]
    assert plot["layout"]["annotations"][1]["text"] == (
        "Select a scenario to see your score history."
    )
    assert plot["layout"]["dragmode"] is False
    assert plot["layout"]["xaxis"]["visible"] is False
    assert plot["layout"]["yaxis"]["visible"] is False


def test_generate_graph_returns_empty_state_for_unsupported_x_axis(monkeypatch):
    monkeypatch.setattr(home, "is_scenario_in_database", lambda _scenario: True)

    def fail_if_called(_scenario):
        raise AssertionError("unsupported graph option should return before overlays")

    monkeypatch.setattr(home, "get_high_score", fail_if_called)

    plot_json, notifications = home.generate_graph(
        None,
        "Scenario A",
        5,
        "2026-07-01",
        "unsupported",
        False,
        True,
        True,
        95,
        True,
        None,
    )

    plot = json.loads(plot_json)

    assert notifications is no_update
    assert "Unsupported graph option" in plot["layout"]["annotations"][0]["text"]
    assert plot["layout"]["annotations"][1]["text"] == (
        "Choose Score vs Sensitivity or Score vs Time."
    )
    assert plot["layout"]["dragmode"] is False
    assert plot["layout"]["xaxis"]["visible"] is False
    assert plot["layout"]["yaxis"]["visible"] is False


def test_generate_graph_control_change_does_not_retoast_stale_payload(monkeypatch):
    monkeypatch.setattr(home, "is_scenario_in_database", lambda _scenario: True)
    monkeypatch.setattr(
        home,
        "get_time_vs_runs",
        lambda *_args: {"2026-07-06": [object()]},
    )
    monkeypatch.setattr(
        home,
        "generate_time_plot",
        lambda *_args: go.Figure(),
    )
    monkeypatch.setattr(home, "get_high_score", lambda _scenario: 830.0)
    monkeypatch.setattr(
        home,
        "ctx",
        SimpleNamespace(triggered=[{"prop_id": "date-picker.value"}]),
    )

    _plot, notifications = home.generate_graph(
        _payload(),
        "Scenario A",
        5,
        "2026-07-01",
        "score_vs_time",
        False,
        False,
        False,
        95,
        True,
        None,
    )

    assert notifications == []


def test_generate_graph_skips_threshold_features_when_percentage_is_empty(
    monkeypatch,
):
    monkeypatch.setattr(home, "is_scenario_in_database", lambda _scenario: True)
    monkeypatch.setattr(
        home,
        "get_time_vs_runs",
        lambda *_args: {"2026-07-06": [object()]},
    )
    monkeypatch.setattr(
        home,
        "generate_time_plot",
        lambda *_args: go.Figure(),
    )
    monkeypatch.setattr(home, "get_high_score", lambda _scenario: 830.0)

    def fail_if_called(_plot, _score_threshold):
        raise AssertionError("empty threshold percentage should skip overlay")

    monkeypatch.setattr(home, "add_score_threshold_overlay", fail_if_called)
    monkeypatch.setattr(
        home,
        "ctx",
        SimpleNamespace(triggered=[{"prop_id": "run-events.data"}]),
    )

    for empty_percentage in (None, ""):
        _plot, notifications = home.generate_graph(
            _payload(score=780.0, previous_high_score=800.0),
            "Scenario A",
            5,
            "2026-07-01",
            "score_vs_time",
            False,
            False,
            True,
            empty_percentage,
            True,
            None,
        )

        assert [notification["id"] for notification in notifications] == [
            "new-top-n-score-notification",
            "graph-updated-notification",
        ]
