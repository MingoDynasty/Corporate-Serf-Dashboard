import dataclasses
import datetime
import logging
from types import SimpleNamespace

import pytest
from sortedcontainers import SortedList

from source.config import settings_service
from source.kovaaks.data_models import RunData
from source.my_queue.message_queue import NewFileMessage
from source.my_watchdog import file_watchdog

SCENARIO_NAME = "VT Pasu Intermediate S5"
SENSITIVITY_KEY = "2.0 Overwatch"


def _sorted_runs(*scores: float) -> SortedList:
    """Build the score-ascending SortedKeyList the production stores hold."""
    return SortedList(
        [_run_data(score) for score in scores],
        key=lambda item: item.score,
    )


def _run_data(score: float = 100.0) -> RunData:
    return RunData(
        datetime_object=datetime.datetime.now(),
        score=score,
        sens_scale="Overwatch",
        horizontal_sens=2.0,
        scenario=SCENARIO_NAME,
        accuracy=0.9,
    )


def _patch_common(monkeypatch, run_data):
    messages = []
    loads = []
    schedules = []

    def load(file):
        loads.append(file)
        return True

    monkeypatch.setattr(file_watchdog.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        file_watchdog,
        "extract_data_from_file",
        lambda _path: run_data,
    )
    monkeypatch.setattr(
        file_watchdog, "message_queue", SimpleNamespace(append=messages.append)
    )
    monkeypatch.setattr(
        file_watchdog,
        "load_csv_file_into_database",
        load,
    )
    monkeypatch.setattr(
        file_watchdog,
        "schedule_rank_freshness_refresh",
        lambda *args: schedules.append(args),
    )
    settings_service.save_settings(
        {"kovaaks_username": "MingoDynasty", "steam_id": "steam-id"}
    )
    monkeypatch.setattr(
        file_watchdog.get_config(),
        "scenario_metadata_cache_ttl_hours",
        24,
    )
    return messages, loads, schedules


@pytest.mark.parametrize("path_kind", ["new_scenario", "new_sensitivity", "existing"])
def test_on_created_schedules_score_aware_refresh_for_all_pb_paths(
    monkeypatch,
    path_kind,
):
    run_data = _run_data()
    messages, loads, schedules = _patch_common(monkeypatch, run_data)

    if path_kind == "new_scenario":
        monkeypatch.setattr(
            file_watchdog,
            "is_scenario_in_database",
            lambda _scenario: False,
        )
    else:
        monkeypatch.setattr(
            file_watchdog,
            "is_scenario_in_database",
            lambda _scenario: True,
        )
        monkeypatch.setattr(
            file_watchdog,
            "get_high_score",
            lambda _scenario: 90.0,
        )
        sensitivities = (
            {} if path_kind == "new_sensitivity" else {SENSITIVITY_KEY: _sorted_runs()}
        )
        monkeypatch.setattr(
            file_watchdog,
            "get_sensitivities_vs_runs",
            lambda _scenario: sensitivities,
        )

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(is_directory=False, src_path="run.csv")
    )

    assert len(messages) == 1
    assert loads == ["run.csv"]
    assert schedules == [
        (
            SCENARIO_NAME,
            "MingoDynasty",
            "steam-id",
            run_data.score,
            24,
        )
    ]


def test_on_created_parses_absolute_source_path_outside_stats_dir(
    tmp_path,
    monkeypatch,
):
    run_data = _run_data()
    messages, loads, _schedules = _patch_common(monkeypatch, run_data)
    source_path = (tmp_path / "outside-stats" / "run.csv").resolve()
    parsed_paths = []

    monkeypatch.setattr(
        file_watchdog,
        "extract_data_from_file",
        lambda path: parsed_paths.append(path) or run_data,
    )
    monkeypatch.setattr(
        file_watchdog,
        "is_scenario_in_database",
        lambda _scenario: False,
    )

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(is_directory=False, src_path=str(source_path))
    )

    assert parsed_paths == [str(source_path)]
    assert len(messages) == 1
    assert loads == [str(source_path)]


def test_on_created_does_not_schedule_refresh_for_non_pb(monkeypatch):
    run_data = _run_data(score=80.0)
    messages, loads, schedules = _patch_common(monkeypatch, run_data)
    monkeypatch.setattr(
        file_watchdog,
        "is_scenario_in_database",
        lambda _scenario: True,
    )
    monkeypatch.setattr(
        file_watchdog,
        "get_high_score",
        lambda _scenario: 90.0,
    )
    monkeypatch.setattr(
        file_watchdog,
        "get_sensitivities_vs_runs",
        lambda _scenario: {SENSITIVITY_KEY: _sorted_runs()},
    )

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(is_directory=False, src_path="run.csv")
    )

    assert len(messages) == 1
    assert loads == ["run.csv"]
    assert schedules == []


@pytest.mark.parametrize(
    ("new_score", "expected_nth"),
    [
        (115.0, 2),  # slots between 110 and 120
        (120.0, 1),  # ties the top score; ties are not counted as higher
        (90.0, 4),  # below every existing run
    ],
)
def test_on_created_computes_nth_place_via_bisect(
    monkeypatch,
    new_score,
    expected_nth,
):
    run_data = _run_data(score=new_score)
    messages, _loads, _schedules = _patch_common(monkeypatch, run_data)
    monkeypatch.setattr(
        file_watchdog,
        "is_scenario_in_database",
        lambda _scenario: True,
    )
    monkeypatch.setattr(file_watchdog, "get_high_score", lambda _scenario: 120.0)
    monkeypatch.setattr(
        file_watchdog,
        "get_sensitivities_vs_runs",
        lambda _scenario: {SENSITIVITY_KEY: _sorted_runs(100.0, 110.0, 120.0)},
    )

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(is_directory=False, src_path="run.csv")
    )

    assert len(messages) == 1
    assert messages[0].nth_score == expected_nth


def test_on_created_preserves_detection_log_for_non_csv(caplog):
    with caplog.at_level(logging.DEBUG, logger=file_watchdog.logger.name):
        file_watchdog.NewFileHandler().on_created(
            SimpleNamespace(is_directory=False, src_path="notes.txt")
        )

    assert "Detected new file: notes.txt" in caplog.messages


def test_scheduling_failure_does_not_block_ingestion(monkeypatch, caplog):
    run_data = _run_data()
    messages, loads, _schedules = _patch_common(monkeypatch, run_data)
    monkeypatch.setattr(
        file_watchdog,
        "is_scenario_in_database",
        lambda _scenario: False,
    )

    def fail_schedule(*_args):
        raise RuntimeError("thread limit")

    monkeypatch.setattr(
        file_watchdog,
        "schedule_rank_freshness_refresh",
        fail_schedule,
    )

    with caplog.at_level(logging.ERROR, logger=file_watchdog.logger.name):
        file_watchdog.NewFileHandler().on_created(
            SimpleNamespace(is_directory=False, src_path="run.csv")
        )

    assert len(messages) == 1
    assert loads == ["run.csv"]
    matching_records = [
        record
        for record in caplog.records
        if "Failed to schedule rank refresh" in record.getMessage()
    ]
    assert len(matching_records) == 1
    assert matching_records[0].exc_info is not None


def test_on_created_loads_before_enqueuing(monkeypatch):
    run_data = _run_data()
    events = []
    monkeypatch.setattr(file_watchdog.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        file_watchdog,
        "extract_data_from_file",
        lambda _path: run_data,
    )
    monkeypatch.setattr(
        file_watchdog,
        "is_scenario_in_database",
        lambda _scenario: False,
    )
    monkeypatch.setattr(
        file_watchdog,
        "load_csv_file_into_database",
        lambda _path: events.append("load") or True,
    )
    monkeypatch.setattr(
        file_watchdog,
        "message_queue",
        SimpleNamespace(append=lambda _message: events.append("enqueue")),
    )
    # No stored identity, so ingestion must still complete without a refresh.
    settings_service.save_settings({})

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(is_directory=False, src_path="run.csv")
    )

    assert events == ["load", "enqueue"]


def test_on_created_does_not_enqueue_or_refresh_when_load_fails(monkeypatch):
    run_data = _run_data()
    messages, loads, schedules = _patch_common(monkeypatch, run_data)
    file_watchdog.run_import_failure_queue.clear()
    monkeypatch.setattr(
        file_watchdog,
        "is_scenario_in_database",
        lambda _scenario: False,
    )

    def fail_load(file):
        loads.append(file)
        return False

    monkeypatch.setattr(file_watchdog, "load_csv_file_into_database", fail_load)

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(is_directory=False, src_path="run.csv")
    )

    assert loads == ["run.csv"]
    assert messages == []
    assert schedules == []
    # The store's own re-read failed, so the run never landed -- the user hears
    # about it here rather than only in debug.log.
    assert file_watchdog.drain_run_import_failures() == [
        file_watchdog.RUN_IMPORT_FAILURE_MESSAGE
    ]


@pytest.mark.parametrize("previous_high_score", [0.0, -5.0])
def test_on_created_ingests_run_when_high_score_has_no_usable_denominator(
    monkeypatch,
    previous_high_score,
):
    """A high score of 0 must not divide a perfectly good run out of ingestion.

    KovaaK's scores are unconstrained floats and a run can score exactly 0, so
    a scenario whose stored runs all scored 0 leaves no usable denominator for
    the debug log's percent-from-high-score figure. The negative case pins that
    the guard left the path that already worked alone.
    """
    file_watchdog.run_import_failure_queue.clear()
    run_data = _run_data(score=100.0)
    messages, loads, schedules = _patch_common(monkeypatch, run_data)
    monkeypatch.setattr(
        file_watchdog,
        "is_scenario_in_database",
        lambda _scenario: True,
    )
    monkeypatch.setattr(
        file_watchdog,
        "get_high_score",
        lambda _scenario: previous_high_score,
    )
    monkeypatch.setattr(
        file_watchdog,
        "get_sensitivities_vs_runs",
        lambda _scenario: {SENSITIVITY_KEY: _sorted_runs(previous_high_score)},
    )

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(is_directory=False, src_path="run.csv")
    )

    assert loads == ["run.csv"]
    assert len(messages) == 1
    assert messages[0].scenario_previous_best == previous_high_score
    assert schedules == [
        (
            SCENARIO_NAME,
            "MingoDynasty",
            "steam-id",
            run_data.score,
            24,
        )
    ]
    assert file_watchdog.drain_run_import_failures() == []


def _patch_scenario_path(monkeypatch, path_kind, high_score=90.0):
    """Steer on_created down one of its three message-building branches."""
    monkeypatch.setattr(
        file_watchdog,
        "is_scenario_in_database",
        lambda _scenario: path_kind != "new_scenario",
    )
    if path_kind == "new_scenario":
        return
    monkeypatch.setattr(file_watchdog, "get_high_score", lambda _scenario: high_score)
    sensitivities = (
        {} if path_kind == "new_sensitivity" else {SENSITIVITY_KEY: _sorted_runs()}
    )
    monkeypatch.setattr(
        file_watchdog,
        "get_sensitivities_vs_runs",
        lambda _scenario: sensitivities,
    )


@pytest.mark.parametrize(
    ("path_kind", "expected_previous_best", "expected_new_sensitivity"),
    [
        ("new_scenario", None, True),
        ("new_sensitivity", 90.0, True),
        ("existing", 90.0, False),
    ],
)
def test_on_created_publishes_facts_from_every_branch(
    monkeypatch,
    path_kind,
    expected_previous_best,
    expected_new_sensitivity,
):
    """Each branch reports the same two facts, so consumers can derive verdicts.

    ``scenario_previous_best`` is the scenario-wide best before this run and is
    None only when the scenario had no prior run at all. ``is_new_sensitivity``
    carries the "nothing to judge this against" half that the one nullable
    field used to mean as well -- which is why a new-sensitivity run now
    reports the scenario best it may well have beaten.
    """
    run_data = _run_data()
    messages, _loads, _schedules = _patch_common(monkeypatch, run_data)
    _patch_scenario_path(monkeypatch, path_kind)

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(
            is_directory=False,
            src_path="S:/stats/VT Pasu Intermediate S5 - Challenge - 2026.08.29 Stats.csv",
        )
    )

    (message,) = messages
    assert message.scenario_previous_best == expected_previous_best
    assert message.is_new_sensitivity is expected_new_sensitivity
    assert message.run_id == (
        "VT Pasu Intermediate S5 - Challenge - 2026.08.29 Stats.csv"
    )


def test_the_run_message_carries_no_decision_field():
    """Facts travel; only the drain decides.

    A decision on the message would let two consumers disagree about one run,
    or let one of them read a verdict the other set. The watchdog keeps its
    ``is_new_high_score`` as a local for the rank refresh and the debug log.
    """
    assert {field.name for field in dataclasses.fields(NewFileMessage)} == {
        "datetime_created",
        "is_new_sensitivity",
        "nth_score",
        "run_id",
        "scenario_name",
        "scenario_previous_best",
        "score",
        "sensitivity",
    }


def test_a_new_sensitivity_run_that_is_a_personal_best_reports_both_facts(monkeypatch):
    """The case the old schema could not express.

    A first run at a new sensitivity can still beat the scenario's best. The
    old field was None here, which hid the scenario best from anything that
    wanted it and was the shape behind two review-round bugs.
    """
    run_data = _run_data(score=120.0)
    messages, _loads, _schedules = _patch_common(monkeypatch, run_data)
    _patch_scenario_path(monkeypatch, "new_sensitivity", high_score=90.0)

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(is_directory=False, src_path="run.csv")
    )

    (message,) = messages
    assert message.is_new_sensitivity is True
    assert message.scenario_previous_best == 90.0
