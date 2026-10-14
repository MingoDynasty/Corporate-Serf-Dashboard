"""The summary a page's batch consumer makes of the shell's run-event batch.

``summarize_run_events`` picks the scenario the page should show and the one
run its summary names. The callbacks that forward the summary are each page's
own, and are tested with their page.
"""

import json

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


def _payload(scenario_name: str = "Scenario A", **run_fields) -> RunEventsPayload:
    return {"latest": _run(scenario_name, **run_fields)}


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


def test_the_summary_names_the_run_and_carries_no_decision():
    # The shell sends both run toasts itself, so no page needs to know which
    # run the batch celebrated. The batch still says, for the animation.
    _target, payload = run_delivery.summarize_run_events(
        _batch(
            _run("Scenario B", run_id="pb.csv", score=900.0),
            _run("Scenario A", run_id="ordinary.csv"),
            celebrated_run_id="pb.csv",
        ),
        "Scenario A",
        False,
    )

    assert payload == {"latest": _run("Scenario A", run_id="ordinary.csv")}
