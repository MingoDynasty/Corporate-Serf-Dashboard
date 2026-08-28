import datetime
import logging
from types import SimpleNamespace

import pytest
from sortedcontainers import SortedList

from source.config import settings_service
from source.kovaaks.data_models import RunData
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
    assert messages[0].previous_high_score == previous_high_score
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
