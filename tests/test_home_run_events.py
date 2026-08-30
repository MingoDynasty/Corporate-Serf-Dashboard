import json
from types import SimpleNamespace

import dash
import plotly.graph_objects as go
from dash import no_update
from dash._callback import GLOBAL_CALLBACK_LIST, GLOBAL_CALLBACK_MAP

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.app_shell import RunEventBatch, RunEventData  # noqa: E402
from source.pages import home  # noqa: E402


def _run(
    scenario_name: str = "Scenario A",
    *,
    run_id: str = "run-1.csv",
    nth_score: int = 2,
    score: float = 812.4,
    scenario_previous_best: float | None = 800.0,
    is_new_sensitivity: bool = False,
    is_live: bool = True,
) -> RunEventData:
    """One run as the shell stamped it: facts plus the drain's liveness."""
    return {
        "run_id": run_id,
        "scenario_name": scenario_name,
        "sensitivity": "34.64 cm/360",
        "nth_score": nth_score,
        "score": score,
        "scenario_previous_best": scenario_previous_best,
        "is_new_sensitivity": is_new_sensitivity,
        "is_live": is_live,
    }


def _batch(
    *runs: RunEventData,
    celebrated_run_id: str | None = None,
) -> RunEventBatch:
    return {
        "runs": list(runs),
        "celebrated_run_id": celebrated_run_id,
        "animation_sequence": 1 if celebrated_run_id else 0,
    }


def _payload(
    scenario_name: str = "Scenario A",
    *,
    celebrated_run_id: str | None = None,
    **run_fields,
) -> home.RunEventsPayload:
    return {
        "latest": _run(scenario_name, **run_fields),
        "celebrated_run_id": celebrated_run_id,
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


def test_summarize_run_events_coalesces_a_single_scenario_backlog():
    target, payload = home._summarize_run_events(
        _batch(
            _run(run_id="a.csv"),
            _run(run_id="b.csv", score=830.1),
        ),
        "Scenario A",
        False,
    )

    assert target == "Scenario A"
    assert payload == _payload(run_id="b.csv", score=830.1)
    json.dumps(payload)


def test_summarize_run_events_auto_change_lands_on_latest_scenario():
    target, payload = home._summarize_run_events(
        _batch(
            _run("Scenario B", run_id="a.csv", score=700.0),
            _run("Scenario A", run_id="b.csv", score=800.0),
            _run("Scenario B", run_id="c.csv", score=830.1),
        ),
        "Scenario A",
        True,
    )

    assert target == "Scenario B"
    assert payload == _payload("Scenario B", run_id="c.csv", score=830.1)


def test_summarize_run_events_without_auto_change_discards_other_scenarios():
    target, payload = home._summarize_run_events(
        _batch(
            _run("Scenario B", run_id="a.csv"),
            _run("Scenario A", run_id="b.csv", score=820.0),
            _run("Scenario B", run_id="c.csv", score=830.1),
        ),
        "Scenario A",
        False,
    )

    assert target == "Scenario A"
    assert payload == _payload(run_id="b.csv", score=820.0)


def test_summarize_run_events_returns_no_payload_when_nothing_relevant():
    batch = _batch(_run("Scenario B"))

    assert home._summarize_run_events(batch, "Scenario A", False) == (
        "Scenario A",
        None,
    )


def test_the_decision_travels_even_when_it_names_another_scenarios_run():
    # The celebration is app-wide, so the run it names need not be one this
    # page is showing. Forwarding it unconditionally is what lets the page
    # recognize the celebrated run when it *is* the one being narrated.
    _target, payload = home._summarize_run_events(
        _batch(
            _run("Scenario B", run_id="pb.csv", score=900.0),
            _run("Scenario A", run_id="ordinary.csv"),
            celebrated_run_id="pb.csv",
        ),
        "Scenario A",
        False,
    )

    assert payload["celebrated_run_id"] == "pb.csv"
    assert payload["latest"]["run_id"] == "ordinary.csv"


def test_check_for_new_data_updates_store_once_and_dropdown_at_most_once():
    payload, target = home.check_for_new_data(
        _batch(_run("Scenario A", run_id="a.csv"), _run("Scenario B", run_id="b.csv")),
        True,
        "Scenario A",
    )
    second_payload, second_target = home.check_for_new_data(
        _batch(_run("Scenario B", run_id="b.csv")),
        True,
        "Scenario B",
    )

    assert payload == _payload("Scenario B", run_id="b.csv")
    assert target == "Scenario B"
    assert second_payload == _payload("Scenario B", run_id="b.csv")
    assert second_target is no_update


def test_check_for_new_data_forwards_nothing_without_a_batch():
    assert home.check_for_new_data(None, True, "Scenario A") == (no_update, no_update)


def test_check_for_new_data_consumes_the_batch_store_as_its_only_input():
    """The controls are State, and the store is the sole trigger.

    A queue pop was destructive, so a control-triggered rerun used to find
    nothing. A Store replays its last value instead, so an auto-switch flip or
    a dropdown change must not re-forward a batch already processed -- and
    prevent_initial_call keeps a remount from replaying the retained value,
    the initial-load duplicate-callback hazard this repo has already paid for.
    """
    key = "..run-events.data...scenario-dropdown-selection.value.."
    spec = GLOBAL_CALLBACK_MAP[key]
    (registration,) = [
        entry for entry in GLOBAL_CALLBACK_LIST if str(entry["output"]) == key
    ]

    assert [(dep["id"], dep["property"]) for dep in spec["inputs"]] == [
        ("run-events-batch", "data")
    ]
    assert {(dep["id"], dep["property"]) for dep in spec["state"]} == {
        ("automatically-change-scenario-switch", "checked"),
        ("scenario-dropdown-selection", "value"),
    }
    assert registration["prevent_initial_call"] is True


def test_the_page_never_pops_the_run_event_queue():
    # One consumer, in the shell. A second drain here is the race the design
    # closed by construction.
    assert not hasattr(home, "message_queue")


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
    # One run, one toast: the placement toast and both threshold verdicts land
    # under the same id, so the newest one replaces whatever is on screen
    # instead of stacking beside it.
    ids = {
        _notification(_payload(is_new_sensitivity=True))["id"],
        _notification(_payload(score=830.0))["id"],
        _notification(_payload(score=780.0))["id"],
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


def test_a_multi_run_batch_narrates_only_its_latest_matching_run():
    """No digest: the plot is every other run's record.

    A batch of several runs rebuilds the graph once, auto-switches once, and
    toasts about the latest matching run exactly as a single run would.
    """
    _target, payload = home._summarize_run_events(
        _batch(
            _run(run_id="a.csv", score=700.0),
            _run(run_id="b.csv", score=760.0),
            _run(run_id="c.csv", score=780.0),
        ),
        "Scenario A",
        False,
    )
    notification = _notification(payload, score_threshold_percentage=98.75)

    assert notification["title"] == "Below threshold"
    assert "runs" not in notification["message"]
    assert not hasattr(home, "_build_backlog_notification")


def test_an_older_qualifying_personal_best_in_the_batch_is_plot_only():
    # Two personal bests in one batch. The drain names the newer one, the page
    # narrates the newer one and yields it to the celebration, and the older
    # one earns nothing -- exactly as such coalesced runs already do today.
    _target, payload = home._summarize_run_events(
        _batch(
            _run(run_id="older-pb.csv", score=810.0),
            _run(run_id="newer-pb.csv", score=830.0),
            celebrated_run_id="newer-pb.csv",
        ),
        "Scenario A",
        False,
    )

    assert payload["latest"]["run_id"] == "newer-pb.csv"
    assert _notification(payload) is None


def test_a_celebrated_run_yields_its_toast_to_the_celebration():
    # The celebration toast is that run's one notification, whatever verdict
    # the run would otherwise have earned -- including a stretch goal it
    # missed, which would have read "Below threshold" under the confetti.
    for goal in (95.0, 105.0):
        assert (
            _notification(
                _payload(score=830.0, celebrated_run_id="run-1.csv"),
                score_threshold_percentage=goal,
            )
            is None
        )


def test_a_celebrated_first_run_at_a_new_sensitivity_yields_too():
    # Case 2: unjudged, first at its sensitivity, and still the scenario's
    # best. The old schema could not tell this run from one with no history.
    assert (
        _notification(
            _payload(
                nth_score=1,
                score=900.0,
                is_new_sensitivity=True,
                celebrated_run_id="run-1.csv",
            )
        )
        is None
    )


def test_the_page_reads_the_stamp_and_never_re_derives_the_celebration():
    """Facts travel; only the drain decides.

    A run whose raw fields beat its previous best still narrates when the
    decision does not name it, and a run whose fields did not still yields when
    it does. Re-deriving here is what the single-drain design removed.
    """
    beat_its_best = _payload(score=830.0, celebrated_run_id=None)
    did_not = _payload(score=780.0, celebrated_run_id="run-1.csv")

    assert _notification(beat_its_best) is not None
    assert _notification(did_not) is None


def test_a_stale_run_narrates_nothing():
    # Past the freshness cap the run still reaches the plot; only the
    # interruption is withheld.
    assert _notification(_payload(score=830.0, is_live=False)) is None
    assert _notification(_payload(score=830.0, is_live=True)) is not None


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
    # One guard, both shapes. Each payload earns a toast with the switch on,
    # so the off assertions cannot pass vacuously.
    shapes = (
        _payload(score=830.0),  # threshold verdict
        _payload(is_new_sensitivity=True),  # top-N placement
    )

    for payload in shapes:
        assert _notification(payload) is not None
        assert _notification(payload, run_notification_switch=False) is None


def test_the_master_switch_guard_precedes_the_celebration_yield():
    # The two settings are independent families, and the order says which one
    # answers first: with run notifications off the page is silent whether or
    # not the drain celebrated the run.
    celebrated = _payload(score=830.0, celebrated_run_id="run-1.csv")
    ordinary = _payload(score=830.0)

    assert _notification(celebrated, run_notification_switch=False) is None
    assert _notification(ordinary, run_notification_switch=False) is None


def test_the_run_notifications_help_text_drops_the_retired_digest():
    assert home.SETTINGS_HELP_TEXT["run-notification"] == (
        "Controls threshold verdict and placement notifications for your runs."
    )


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
