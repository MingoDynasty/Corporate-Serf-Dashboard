"""The summary a page's batch consumer makes of the shell's run-event batch.

``summarize_run_events`` picks the scenario the page should show and the one
run it narrates. The callbacks that forward the summary are each page's own,
and are tested with their page.
"""

import json

from dash._callback_context import falsy_triggered

from source.app_shell import RunEventBatch, RunEventData
from source.components import run_delivery
from source.components.run_delivery import RunEventsPayload


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


def test_summarize_run_events_coalesces_a_single_scenario_backlog():
    target, payload = run_delivery.summarize_run_events(
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
    target, payload = run_delivery.summarize_run_events(
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
    target, payload = run_delivery.summarize_run_events(
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

    assert run_delivery.summarize_run_events(batch, "Scenario A", False) == (
        "Scenario A",
        None,
    )


def test_the_decision_travels_even_when_it_names_another_scenarios_run():
    # The celebration is app-wide, so the run it names need not be one this
    # page is showing. Forwarding it unconditionally is what lets the page
    # recognize the celebrated run when it *is* the one being narrated.
    _target, payload = run_delivery.summarize_run_events(
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


def test_run_events_were_triggered_reads_the_trigger_and_not_the_value():
    """The store replays its last summary, so only the trigger says a run landed."""
    prop = "page-run-events.data"

    assert run_delivery.run_events_were_triggered([{"prop_id": prop}], prop)
    assert run_delivery.run_events_were_triggered(
        [{"prop_id": "page-scenario.value"}, {"prop_id": prop}], prop
    )
    assert not run_delivery.run_events_were_triggered(
        [{"prop_id": "page-scenario.value"}], prop
    )
    # Another page's store is not this page's.
    assert not run_delivery.run_events_were_triggered(
        [{"prop_id": "run-events.data"}], prop
    )


def test_a_call_nothing_triggered_is_not_a_landed_run():
    """Dash hands an untriggered call a falsy list that still holds one item."""
    assert not run_delivery.run_events_were_triggered(
        falsy_triggered, "page-run-events.data"
    )
