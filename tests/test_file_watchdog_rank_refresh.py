import datetime
from types import SimpleNamespace

import pytest

from source.kovaaks.data_models import RunData
from source.my_watchdog import file_watchdog

SCENARIO_NAME = "VT Pasu Intermediate S5"
SENSITIVITY_KEY = "2.0 Overwatch"


def _capture_log(messages):
    def capture(message, *args):
        messages.append(message % args if args else message)

    return capture


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
        loads.append,
    )
    monkeypatch.setattr(
        file_watchdog,
        "schedule_rank_freshness_refresh",
        lambda *args: schedules.append(args),
    )
    monkeypatch.setattr(file_watchdog.config, "kovaaks_username", "MingoDynasty")
    monkeypatch.setattr(file_watchdog.config, "steam_id", "steam-id")
    monkeypatch.setattr(
        file_watchdog.config,
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
        sensitivities = {} if path_kind == "new_sensitivity" else {SENSITIVITY_KEY: []}
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
    stats_dir = (tmp_path / "stats").resolve()
    source_path = (tmp_path / "outside-stats" / "run.csv").resolve()
    parsed_paths = []

    monkeypatch.setattr(file_watchdog.config, "stats_dir", str(stats_dir))
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
        lambda _scenario: {SENSITIVITY_KEY: []},
    )

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(is_directory=False, src_path="run.csv")
    )

    assert len(messages) == 1
    assert loads == ["run.csv"]
    assert schedules == []


def test_scheduling_failure_does_not_block_ingestion(monkeypatch):
    run_data = _run_data()
    messages, loads, _schedules = _patch_common(monkeypatch, run_data)
    notifications = []
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
    monkeypatch.setattr(
        file_watchdog.dash_logger,
        "error",
        _capture_log(notifications),
    )

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(is_directory=False, src_path="run.csv")
    )

    assert len(messages) == 1
    assert loads == ["run.csv"]
    assert notifications == [f"Could not start position update for {SCENARIO_NAME}."]
