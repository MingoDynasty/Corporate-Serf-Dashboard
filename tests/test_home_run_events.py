import json
from types import SimpleNamespace

import dash
import plotly.graph_objects as go
from dash import no_update
from dash._callback import GLOBAL_CALLBACK_LIST, GLOBAL_CALLBACK_MAP

dash.Dash(__name__, use_pages=True, pages_folder="")

from datetime import datetime  # noqa: E402

from source.app_shell import RunEventBatch, RunEventData  # noqa: E402
from source.components import (  # noqa: E402
    chart_options,
    run_verdict_toast,
    scenario_selection,
    score_threshold,
)
from source.components.run_delivery import RunEventsPayload  # noqa: E402
from source.kovaaks.data_models import RunData  # noqa: E402
from source.kovaaks.time_scored_service import PaceBasis  # noqa: E402
from source.pages import home  # noqa: E402


def _run(
    scenario_name: str = "Scenario A",
    *,
    run_id: str = "run-1.csv",
    nth_score: int = 2,
    score: float = 812.4,
    scenario_previous_best: float | None = 800.0,
    pace_constant: float | None = None,
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
        "pace_constant": pace_constant,
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
) -> RunEventsPayload:
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
    monkeypatch.setattr(
        scenario_selection, "get_visible_playlist_selector_options", lambda: []
    )
    monkeypatch.setattr(scenario_selection, "get_scenario_names", lambda: [])

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
    figure = chart_options.apply_graph_appearance("light", None, "Default", "")

    _assert_placeholder_figure(figure)
    assert figure.layout.template.layout.paper_bgcolor == "#ffffff"


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


def test_the_run_notifications_help_text_names_both_families():
    # The switch's own family, then the one it deliberately does not reach: the
    # celebration has its own setting, and the digest it once mentioned is gone.
    assert chart_options.SETTINGS_HELP_TEXT["run-notification"] == (
        "Controls threshold verdict and placement notifications for your runs. "
        "Personal best celebrations use their own setting."
    )


def test_the_run_notification_switch_is_state_not_input():
    """Flipping the preference must not rebuild the plot.

    Keyed by an output this callback writes, so it survives the dependency
    list growing around it. Anchored at the start, because the Run History
    page's own store id ends the same way.
    """
    (spec,) = [
        spec
        for key, spec in GLOBAL_CALLBACK_MAP.items()
        if key.startswith("..cached-plot.data...")
    ]

    assert "run-notification-switch" not in {dep["id"] for dep in spec["inputs"]}
    assert ("run-notification-switch", "checked") in {
        (dep["id"], dep["property"]) for dep in spec["state"]
    }


def test_generate_graph_returns_empty_state_before_scenario_selection():
    plot_json, notifications, hidden, toast_channels = home.generate_graph(
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
        {},
    )

    plot = json.loads(plot_json)

    assert notifications is no_update
    assert hidden is no_update
    assert toast_channels is no_update
    assert "No scenario selected" in plot["layout"]["annotations"][0]["text"]
    assert plot["layout"]["annotations"][1]["text"] == (
        "Select a scenario to see your score history."
    )
    assert plot["layout"]["dragmode"] is False
    assert plot["layout"]["xaxis"]["visible"] is False
    assert plot["layout"]["yaxis"]["visible"] is False


def test_generate_graph_names_the_missing_control_in_bold():
    # The date field is paraphrased as "the oldest date", a value rather than a
    # control name, so only Top N scores is bold.
    plot_json, *_outputs = home.generate_graph(
        None,
        "Scenario A",
        None,
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
        {},
    )

    plot = json.loads(plot_json)

    assert plot["layout"]["annotations"][1]["text"] == (
        "Set <b>Top N scores</b> and the oldest date to plot this scenario."
    )


def test_generate_graph_returns_empty_state_for_unsupported_x_axis(monkeypatch):
    monkeypatch.setattr(home, "is_scenario_in_database", lambda _scenario: True)

    def fail_if_called(_scenario):
        raise AssertionError("unsupported graph option should return before overlays")

    monkeypatch.setattr(home, "get_high_score", fail_if_called)

    plot_json, notifications, hidden, toast_channels = home.generate_graph(
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
        {},
    )

    plot = json.loads(plot_json)

    assert notifications is no_update
    assert hidden is no_update
    assert toast_channels is no_update
    assert "Unsupported graph option" in plot["layout"]["annotations"][0]["text"]
    assert plot["layout"]["annotations"][1]["text"] == (
        "Choose <b>Score vs Sensitivity</b> or <b>Score vs Time</b>."
    )
    assert plot["layout"]["dragmode"] is False
    assert plot["layout"]["xaxis"]["visible"] is False
    assert plot["layout"]["yaxis"]["visible"] is False


def test_generate_graph_lets_the_empty_canvas_report_an_unplayed_scenario(monkeypatch):
    # Selecting a scenario with no local runs draws the on-canvas empty state
    # and nothing else; the parallel toast was a redundant second copy.
    monkeypatch.setattr(home, "is_scenario_in_database", lambda _scenario: False)

    plot_json, notifications, hidden, toast_channels = home.generate_graph(
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
        {},
    )

    plot = json.loads(plot_json)

    assert notifications is no_update
    assert hidden is no_update
    assert toast_channels is no_update
    assert home._NO_SCENARIO_DATA_PLOT_TITLE in plot["layout"]["annotations"][0]["text"]


def test_generate_graph_control_change_does_not_retoast_stale_payload(monkeypatch):
    monkeypatch.setattr(home, "is_scenario_in_database", lambda _scenario: True)
    monkeypatch.setattr(
        home,
        "get_time_vs_runs",
        lambda *_args: {"2026-07-06": [object()]},
    )
    monkeypatch.setattr(home, "get_new_high_score_runs", lambda _scenario: set())
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

    _plot, notifications, hidden, toast_channels = home.generate_graph(
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
        {},
    )

    assert notifications == []
    assert hidden == []
    assert toast_channels is no_update


def test_generate_graph_skips_threshold_features_when_percentage_is_empty(
    monkeypatch,
):
    monkeypatch.setattr(home, "is_scenario_in_database", lambda _scenario: True)
    monkeypatch.setattr(
        home,
        "get_time_vs_runs",
        lambda *_args: {"2026-07-06": [object()]},
    )
    monkeypatch.setattr(home, "get_new_high_score_runs", lambda _scenario: set())
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

    toast_channels: dict[str, str | None] = {}
    for empty_percentage in (None, ""):
        _plot, notifications, hidden, patch = home.generate_graph(
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
            toast_channels,
        )

        # An unjudged run still placed, so one toast goes out -- one fresh
        # instance shown, and the previous one hidden with it.
        previous_instance = toast_channels.get(run_verdict_toast.RUN_VERDICT_CHANNEL)
        assert [notification["action"] for notification in notifications] == ["show"]
        assert notifications[0]["title"] == "New 2nd-best score"
        assert hidden == ([previous_instance] if previous_instance else [])
        toast_channels.update(
            {
                operation["location"][0]: operation["params"]["value"]
                for operation in patch._operations
            }
        )
        assert (
            toast_channels[run_verdict_toast.RUN_VERDICT_CHANNEL] != previous_instance
        )


def test_generate_graph_sends_no_toast_when_run_notifications_are_off(monkeypatch):
    # The run that would otherwise headline "Threshold passed" updates the plot
    # and nothing else -- no toast, and no registry rotation that would leave
    # the next emission hiding an instance that was never shown.
    monkeypatch.setattr(home, "is_scenario_in_database", lambda _scenario: True)
    monkeypatch.setattr(
        home,
        "get_time_vs_runs",
        lambda *_args: {"2026-07-06": [object()]},
    )
    monkeypatch.setattr(home, "get_new_high_score_runs", lambda _scenario: set())
    monkeypatch.setattr(
        home,
        "generate_time_plot",
        lambda *_args: go.Figure(),
    )
    monkeypatch.setattr(home, "get_high_score", lambda _scenario: 830.0)

    def fail_if_called(*_args):
        raise AssertionError("a silenced run must not reach the toast sender")

    monkeypatch.setattr(home, "channel_toast", fail_if_called)
    monkeypatch.setattr(
        home,
        "ctx",
        SimpleNamespace(triggered=[{"prop_id": "run-events.data"}]),
    )

    _plot, notifications, hidden, toast_channels = home.generate_graph(
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
        {},
    )

    assert notifications == []
    assert hidden == []
    assert toast_channels is no_update


# --- The score threshold line on a time-scored scenario ----------------------

_LINE_HASH = "0123456789abcdef0123456789abcdef"


def _threshold_line_annotation(monkeypatch, *, basis, pb_hash) -> str:
    """Draw Scenario A's threshold line at 95% and return what the chart says."""
    personal_best = RunData(
        datetime_object=datetime(2026, 7, 6, 12),
        score=896.2,
        sens_scale="cm/360",
        horizontal_sens=40.8,
        scenario="Scenario A",
        accuracy=0.5,
        scenario_hash=pb_hash,
    )
    monkeypatch.setattr(home, "is_scenario_in_database", lambda _scenario: True)
    monkeypatch.setattr(
        home, "get_time_vs_runs", lambda *_args: {"2026-07-06": [object()]}
    )
    monkeypatch.setattr(home, "generate_time_plot", lambda *_args: go.Figure())
    monkeypatch.setattr(home, "get_new_high_score_runs", lambda _scenario: set())
    monkeypatch.setattr(home, "get_high_score", lambda _scenario: 896.2)
    monkeypatch.setattr(
        score_threshold, "get_personal_best_run", lambda _scenario: personal_best
    )
    monkeypatch.setattr(score_threshold, "get_pace_basis", lambda _scenario: basis)
    monkeypatch.setattr(
        home,
        "ctx",
        SimpleNamespace(triggered=[{"prop_id": "date-picker.value"}]),
    )

    plot_json, *_outputs = home.generate_graph(
        None,
        "Scenario A",
        5,
        "2026-07-01",
        "score_vs_time",
        False,
        False,
        False,
        True,
        95,
        True,
        True,
        None,
        {},
    )

    plot = json.loads(plot_json)
    (annotation,) = plot["layout"]["annotations"]
    (line,) = plot["layout"]["shapes"]
    # The label is the line's own height, rounded for display.
    assert annotation["text"] == f"Score threshold ({line['y0']:.2f})"
    return annotation["text"]


def test_the_threshold_line_on_a_time_scored_scenario_sits_at_95_percent_of_pb_pace(
    monkeypatch,
):
    # 103.8 s at 95% of the pace is 109.26 s, which is a score of 890.74. The
    # annotation still names a score.
    annotation = _threshold_line_annotation(
        monkeypatch,
        basis=PaceBasis(1000.0, _LINE_HASH),
        pb_hash=_LINE_HASH,
    )

    assert annotation == "Score threshold (890.74)"


def test_the_threshold_line_with_no_constant_sits_at_95_percent_of_the_pb_score(
    monkeypatch,
):
    annotation = _threshold_line_annotation(monkeypatch, basis=None, pb_hash=_LINE_HASH)

    assert annotation == "Score threshold (851.39)"


def test_the_threshold_line_keeps_score_math_for_a_pb_from_another_version(
    monkeypatch,
):
    annotation = _threshold_line_annotation(
        monkeypatch,
        basis=PaceBasis(1000.0, _LINE_HASH),
        pb_hash="ffffffffffffffffffffffffffffffff",
    )

    assert annotation == "Score threshold (851.39)"


def test_the_threshold_line_keeps_score_math_where_pace_is_undefined(monkeypatch):
    # A PB at the constant took no time, so there is no pace to take 95% of.
    personal_best = RunData(
        datetime_object=datetime(2026, 7, 6, 12),
        score=1000.0,
        sens_scale="cm/360",
        horizontal_sens=40.8,
        scenario="Scenario A",
        accuracy=0.5,
        scenario_hash=_LINE_HASH,
    )
    monkeypatch.setattr(
        score_threshold, "get_personal_best_run", lambda _scenario: personal_best
    )
    monkeypatch.setattr(
        score_threshold,
        "get_pace_basis",
        lambda _scenario: PaceBasis(1000.0, _LINE_HASH),
    )

    assert score_threshold.score_threshold_line("Scenario A", 1000.0, 95.0) == 950.0
