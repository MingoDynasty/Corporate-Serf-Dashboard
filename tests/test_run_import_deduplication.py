"""Run-file identity stays idempotent across startup and live ingestion."""

import os
from collections import deque
from pathlib import Path

import pytest
from sortedcontainers import SortedList
from watchdog.events import FileCreatedEvent

from source.kovaaks import data_service
from source.my_watchdog import file_watchdog

SCENARIO = "Synthetic deduplication"
FILENAME = f"{SCENARIO} - Challenge - 2026.10.23-12.00.00 Stats.csv"
CONTENT = (
    "Score:,100\nSens Scale:,cm/360\nHoriz Sens:,40\n"
    f"Scenario:,{SCENARIO}\n"
    + data_service.POSSIBLE_SUB_CSV_HEADERS[0]
    + "\nRifle,100,90,0,0\n"
)


@pytest.fixture(autouse=True)
def isolated_ingestion(monkeypatch):
    monkeypatch.setattr(data_service, "kovaaks_database", {})
    monkeypatch.setattr(
        data_service, "run_database", SortedList(key=lambda run: run.datetime_object)
    )
    monkeypatch.setattr(file_watchdog, "message_queue", deque())
    monkeypatch.setattr(file_watchdog, "run_import_failure_queue", deque())
    sleeps = []
    monkeypatch.setattr(file_watchdog.time, "sleep", sleeps.append)
    return sleeps


def _create(path: Path) -> None:
    path.write_text(CONTENT, encoding="utf-8")


def _deliver(path: Path) -> None:
    file_watchdog.NewFileHandler().dispatch(FileCreatedEvent(str(path)))


def _assert_one_run() -> None:
    assert len(data_service.run_database) == 1
    assert data_service.get_scenario_stats(SCENARIO).number_of_runs == 1
    assert len(data_service.get_runs_newest_first(SCENARIO)) == 1
    assert len(data_service.get_sensitivities_vs_runs(SCENARIO)["40.0 cm/360"]) == 1


@pytest.mark.parametrize("initial_import", ["watchdog", "startup"])
@pytest.mark.parametrize(
    "repeat",
    [
        "same_path",
        "recreated",
        "relative_path",
        pytest.param(
            "case_variant",
            marks=pytest.mark.skipif(os.name != "nt", reason="Windows path casing"),
        ),
    ],
)
def test_duplicate_create_keeps_one_run_and_no_extra_message(
    tmp_path, monkeypatch, isolated_ingestion, initial_import, repeat
):
    path = tmp_path / FILENAME
    _create(path)
    if initial_import == "startup":
        data_service.initialize_kovaaks_data(str(tmp_path))
    else:
        _deliver(path)
    _assert_one_run()
    messages = list(file_watchdog.message_queue)
    sleeps = list(isolated_ingestion)

    if repeat == "recreated":
        path.unlink()
        _create(path)
    elif repeat == "relative_path":
        monkeypatch.chdir(tmp_path)
        path = Path(FILENAME)
    elif repeat == "case_variant":
        path = path.with_name(path.stem.swapcase() + path.suffix)
    _deliver(path)

    _assert_one_run()
    assert list(file_watchdog.message_queue) == messages
    assert file_watchdog.drain_run_import_failures() == []
    assert isolated_ingestion == sleeps


@pytest.mark.parametrize("remove_file", [False, True])
def test_loading_an_imported_file_is_successful_without_adding_it_again(
    tmp_path, remove_file
):
    path = tmp_path / FILENAME
    _create(path)
    assert data_service.load_csv_file_into_database(str(path)) is True
    if remove_file:
        path.unlink()

    assert data_service.load_csv_file_into_database(str(path)) is True
    _assert_one_run()


@pytest.mark.parametrize(
    "second_name",
    [
        FILENAME.replace("Challenge", "Free Play"),
        FILENAME.replace("12.00.00", "12.01.00"),
    ],
)
def test_distinct_files_with_identical_run_values_are_both_imported(
    tmp_path, second_name
):
    for name in [FILENAME, second_name]:
        path = tmp_path / name
        _create(path)
        _deliver(path)

    assert len(data_service.run_database) == 2
    assert data_service.get_scenario_stats(SCENARIO).number_of_runs == 2
    assert len(file_watchdog.message_queue) == 2
    assert len({message.run_id for message in file_watchdog.message_queue}) == 2
    assert file_watchdog.drain_run_import_failures() == []


@pytest.mark.parametrize("failure", ["initial_parse", "store_reread"])
def test_failed_import_can_succeed_on_a_later_create(tmp_path, monkeypatch, failure):
    path = tmp_path / FILENAME
    _create(path)
    if failure == "initial_parse":
        path.write_text("Score:\n", encoding="utf-8")
    else:
        parse = data_service.extract_data_from_file
        reads = 0

        def fail_first_store_read(file):
            nonlocal reads
            reads += 1
            return None if reads == 1 else parse(file)

        monkeypatch.setattr(
            data_service, "extract_data_from_file", fail_first_store_read
        )
    _deliver(path)
    assert list(data_service.run_database) == []
    assert list(file_watchdog.message_queue) == []
    assert file_watchdog.drain_run_import_failures() == [
        file_watchdog.RUN_IMPORT_FAILURE_MESSAGE
    ]

    _create(path)
    _deliver(path)

    _assert_one_run()
    assert len(file_watchdog.message_queue) == 1
    assert file_watchdog.drain_run_import_failures() == []
