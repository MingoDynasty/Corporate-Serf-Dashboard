import json
from collections import deque
from datetime import datetime
from types import SimpleNamespace

import dash
import plotly.graph_objects as go
from dash import no_update
from dash._callback import GLOBAL_CALLBACK_MAP

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.my_queue.message_queue import NewFileMessage  # noqa: E402
from source.pages import home  # noqa: E402


def _message(
    scenario_name: str,
    *,
    nth_score: int = 2,
    score: float = 812.4,
    scenario_previous_best: float | None = 800.0,
    is_new_sensitivity: bool = False,
) -> NewFileMessage:
    return NewFileMessage(
        datetime_created=datetime(2026, 7, 6, 12),
        is_new_sensitivity=is_new_sensitivity,
        nth_score=nth_score,
        run_id=f"{scenario_name} {score}.csv",
        scenario_name=scenario_name,
        scenario_previous_best=scenario_previous_best,
        score=score,
        sensitivity="34.64 cm/360",
    )


def _payload(
    scenario_name: str = "Scenario A",
    *,
    count: int = 1,
    nth_score: int = 2,
    score: float = 812.4,
    scenario_previous_best: float | None = 800.0,
    is_new_sensitivity: bool = False,
) -> home.RunEventsPayload:
    return {
        "count": count,
        "latest": {
            "scenario_name": scenario_name,
            "sensitivity": "34.64 cm/360",
            "nth_score": nth_score,
            "score": score,
            "scenario_previous_best": scenario_previous_best,
            "is_new_sensitivity": is_new_sensitivity,
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


def _assert_placeholder_figure(figure) -> None:
    placeholder = go.Figure(figure)

    assert not placeholder.layout.annotations
    assert placeholder.layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert placeholder.layout.plot_bgcolor == "rgba(0,0,0,0)"
    assert placeholder.layout.dragmode is False
    assert placeholder.layout.xaxis.visible is False
    assert placeholder.layout.yaxis.visible is False


def test_home_layout_initial_graph_has_placeholder(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
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

    _assert_placeholder_figure(figure)
    _assert_placeholder_figure(cached_plot_data)


def test_graph_theme_callback_falls_back_to_initial_placeholder():
    figure = home.apply_graph_appearance("light", None, "Default", "")

    _assert_placeholder_figure(figure)
    assert figure.layout.template.layout.paper_bgcolor == "#ffffff"


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


def _notification(
    payload: home.RunEventsPayload,
    *,
    top_n_scores: int = 5,
    score_threshold_percentage: float | str | None = 100.0,
    score_threshold_notification_switch: bool = True,
    run_notification_switch: bool = True,
) -> dict[str, object] | None:
    return home._build_run_event_notification(
        payload,
        "Scenario A",
        top_n_scores,
        score_threshold_percentage,
        score_threshold_notification_switch,
        run_notification_switch,
    )


def test_every_run_verdict_shares_one_replaceable_id():
    # One run, one toast: the placement toast, the threshold verdict, and the
    # catch-up digest all land under the same id, so the newest one replaces
    # whatever is on screen instead of stacking beside it.
    ids = {
        _notification(_payload(is_new_sensitivity=True))["id"],
        _notification(_payload(score=830.0))["id"],
        _notification(_payload(score=780.0, scenario_previous_best=800.0))["id"],
        _notification(_payload(count=3))["id"],
    }

    assert ids == {"run-verdict"}


def test_top_n_placement_alone_leads_with_the_scenario():
    # No previous high score means no threshold verdict; the placement is the
    # whole story and the title carries it.
    notification = _notification(_payload(is_new_sensitivity=True))

    assert notification["title"] == "New 2nd-best score"
    assert notification["message"] == "Scenario A — 812.40 at 34.64 cm/360."
    assert notification["color"] == "green"


def test_a_first_place_run_is_titled_new_best_score():
    # Deliberately not "New personal best!": the recorded decision is that a PB
    # gets no toast of its own, and a retitle would create one by the back door.
    notification = _notification(_payload(nth_score=1, is_new_sensitivity=True))

    assert notification["title"] == "New best score"
    assert notification["message"] == "Scenario A — 812.40 at 34.64 cm/360."


def test_threshold_pass_headlines_over_the_placement_it_also_earned():
    notification = _notification(
        _payload(score=830.0, scenario_previous_best=800.0),
        score_threshold_percentage=102.5,
    )

    assert notification["title"] == "Threshold passed"
    assert notification["color"] == "green"
    assert notification["message"] == (
        "Scenario A — 830.00, 103.8% of PB. Also your 2nd-best at 34.64 cm/360."
    )


def test_threshold_pass_without_a_placement_points_at_the_next_scenario():
    notification = _notification(
        _payload(score=830.0, scenario_previous_best=800.0, nth_score=9),
        score_threshold_percentage=102.5,
    )

    assert notification["title"] == "Threshold passed"
    assert notification["message"] == (
        "Scenario A — 830.00, 103.8% of PB. Ready to move on."
    )


def test_threshold_passes_at_exactly_the_goal():
    notification = _notification(
        _payload(score=820.0, scenario_previous_best=800.0),
        score_threshold_percentage=102.5,
    )

    assert notification["title"] == "Threshold passed"
    assert notification["message"].startswith("Scenario A — 820.00, 102.5% of PB.")


def test_threshold_fail_names_the_target_it_missed():
    notification = _notification(
        _payload(score=780.0, scenario_previous_best=800.0),
        score_threshold_percentage=98.75,
    )

    assert notification["title"] == "Below threshold"
    assert notification["color"] == "yellow"
    assert notification["message"] == (
        "Scenario A — 780.00, 97.5% of PB — need 98.8%. "
        "Still your 2nd-best at 34.64 cm/360. Keep grinding..."
    )


def test_a_new_pb_short_of_a_stretch_goal_still_reads_as_below_threshold():
    # Reachable whenever the goal exceeds 100%: the run beat the old PB and
    # still missed the bar. The verdict is the title, so it stays "Below
    # threshold" rather than being retitled for the PB.
    notification = _notification(
        _payload(score=820.0, scenario_previous_best=800.0, nth_score=1),
        score_threshold_percentage=105.0,
    )

    assert notification["title"] == "Below threshold"
    assert notification["message"] == (
        "Scenario A — 820.00, 102.5% of PB — need 105.0%. "
        "Still your best at 34.64 cm/360. Keep grinding..."
    )


def test_threshold_fail_without_a_placement_drops_the_placement_clause():
    notification = _notification(
        _payload(score=780.0, scenario_previous_best=800.0, nth_score=9),
        score_threshold_percentage=98.75,
    )

    assert notification["message"] == (
        "Scenario A — 780.00, 97.5% of PB — need 98.8%. Keep grinding..."
    )


def test_an_empty_threshold_percentage_leaves_the_run_unjudged():
    for empty_percentage in (None, ""):
        notification = _notification(
            _payload(score=780.0, scenario_previous_best=800.0),
            score_threshold_percentage=empty_percentage,
        )

        assert notification["title"] == "New 2nd-best score"


def test_a_run_qualifying_for_neither_verdict_says_nothing():
    assert _notification(_payload(nth_score=9, is_new_sensitivity=True)) is None


def test_backlog_summary_reports_the_count_and_the_latest_verdict():
    notification = _notification(
        _payload(count=3, score=780.0, scenario_previous_best=800.0),
        score_threshold_percentage=98.75,
    )

    assert notification["title"] == "While you were away"
    assert notification["color"] == "yellow"
    assert notification["message"] == (
        "3 new Scenario A runs. Latest: 780.00 — 97.5% of PB, below the "
        "98.8% threshold."
    )


def test_backlog_summary_without_a_verdict_stays_neutral():
    for empty_percentage in (None, ""):
        notification = _notification(
            _payload(count=3, score=780.0, scenario_previous_best=800.0),
            score_threshold_percentage=empty_percentage,
        )

        assert notification["title"] == "While you were away"
        assert notification["color"] == "blue"
        assert notification["message"] == (
            "3 new Scenario A runs. Latest: 780.00 at 34.64 cm/360."
        )


def test_backlog_summary_passes_at_exactly_the_goal():
    notification = _notification(
        _payload(count=3, score=820.0, scenario_previous_best=800.0),
        score_threshold_percentage=102.5,
    )

    assert notification["color"] == "green"
    assert notification["message"] == (
        "3 new Scenario A runs. Latest: 820.00 — 102.5% of PB, passed threshold."
    )


def test_backlog_summary_passes_a_new_pb_above_a_stretch_goal():
    notification = _notification(
        _payload(count=3, score=850.0, scenario_previous_best=800.0),
        score_threshold_percentage=105.0,
    )

    assert notification["color"] == "green"
    assert notification["message"] == (
        "3 new Scenario A runs. Latest: 850.00 — 106.2% of PB, passed threshold."
    )


def test_notifications_ignore_payload_for_another_scenario():
    assert (
        home._build_run_event_notification(
            _payload("Scenario B"),
            "Scenario A",
            5,
            100.0,
            True,
            True,
        )
        is None
    )


def test_the_master_switch_silences_the_whole_run_toast_family():
    # One guard, three shapes. Each payload earns a toast with the switch on,
    # so the off assertions cannot pass vacuously.
    shapes = (
        _payload(score=830.0, scenario_previous_best=800.0),  # threshold verdict
        _payload(is_new_sensitivity=True),  # top-N placement
        _payload(count=3),  # "While you were away" digest
    )

    for payload in shapes:
        assert _notification(payload) is not None
        assert _notification(payload, run_notification_switch=False) is None


def test_the_run_notification_switch_is_state_not_input():
    """Flipping the preference must not rebuild the plot.

    Keyed by an output this callback writes, so it survives the dependency
    list growing around it.
    """
    spec = next(
        spec for key, spec in GLOBAL_CALLBACK_MAP.items() if "cached-plot.data" in key
    )

    assert "run-notification-switch" not in {dep["id"] for dep in spec["inputs"]}
    assert ("run-notification-switch", "checked") in {
        (dep["id"], dep["property"]) for dep in spec["state"]
    }


def test_generate_graph_returns_empty_state_before_scenario_selection():
    plot_json, notifications, lifetime_sequence = home.generate_graph(
        None,
        None,
        5,
        "2026-07-01",
        "score_vs_time",
        False,
        False,
        False,
        False,
        95,
        True,
        True,
        None,
        0,
    )

    plot = json.loads(plot_json)

    assert notifications is no_update
    assert lifetime_sequence is no_update
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

    plot_json, notifications, lifetime_sequence = home.generate_graph(
        None,
        "Scenario A",
        5,
        "2026-07-01",
        "unsupported",
        False,
        False,
        True,
        True,
        95,
        True,
        True,
        None,
        0,
    )

    plot = json.loads(plot_json)

    assert notifications is no_update
    assert lifetime_sequence is no_update
    assert "Unsupported graph option" in plot["layout"]["annotations"][0]["text"]
    assert plot["layout"]["annotations"][1]["text"] == (
        "Choose Score vs Sensitivity or Score vs Time."
    )
    assert plot["layout"]["dragmode"] is False
    assert plot["layout"]["xaxis"]["visible"] is False
    assert plot["layout"]["yaxis"]["visible"] is False


def test_generate_graph_lets_the_empty_canvas_report_an_unplayed_scenario(monkeypatch):
    # Selecting a scenario with no local runs draws the on-canvas empty state
    # and nothing else; the parallel toast was a redundant second copy.
    monkeypatch.setattr(home, "is_scenario_in_database", lambda _scenario: False)

    plot_json, notifications, lifetime_sequence = home.generate_graph(
        None,
        "Unplayed Scenario",
        5,
        "2026-07-01",
        "score_vs_time",
        False,
        False,
        True,
        True,
        95,
        True,
        True,
        None,
        0,
    )

    plot = json.loads(plot_json)

    assert notifications is no_update
    assert lifetime_sequence is no_update
    assert home._NO_SCENARIO_DATA_PLOT_TITLE in plot["layout"]["annotations"][0]["text"]


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

    _plot, notifications, lifetime_sequence = home.generate_graph(
        _payload(),
        "Scenario A",
        5,
        "2026-07-01",
        "score_vs_time",
        False,
        False,
        False,
        False,
        95,
        True,
        True,
        None,
        0,
    )

    assert notifications == []
    assert lifetime_sequence is no_update


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

    for sequence, empty_percentage in enumerate((None, "")):
        _plot, notifications, lifetime_sequence = home.generate_graph(
            _payload(score=780.0, scenario_previous_best=800.0),
            "Scenario A",
            5,
            "2026-07-01",
            "score_vs_time",
            False,
            False,
            False,
            True,
            empty_percentage,
            True,
            True,
            None,
            sequence,
        )

        # An unjudged run still placed, so one toast goes out -- as the paired
        # update+show that lets it replace whatever is on screen.
        assert [notification["action"] for notification in notifications] == [
            "update",
            "show",
        ]
        assert notifications[0]["title"] == "New 2nd-best score"
        assert lifetime_sequence == sequence + 1


def test_generate_graph_sends_no_toast_when_run_notifications_are_off(monkeypatch):
    # The run that would otherwise headline "Threshold passed" updates the plot
    # and nothing else -- no toast, and no bump of the lifetime counter that
    # would let a later toast replace one that was never shown.
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

    def fail_if_called(*_args):
        raise AssertionError("a silenced run must not reach the toast sender")

    monkeypatch.setattr(home, "upsert_toast", fail_if_called)
    monkeypatch.setattr(
        home,
        "ctx",
        SimpleNamespace(triggered=[{"prop_id": "run-events.data"}]),
    )

    _plot, notifications, lifetime_sequence = home.generate_graph(
        _payload(score=830.0, scenario_previous_best=800.0),
        "Scenario A",
        5,
        "2026-07-01",
        "score_vs_time",
        False,
        False,
        False,
        False,
        95,
        True,
        False,
        None,
        0,
    )

    assert notifications == []
    assert lifetime_sequence is no_update
