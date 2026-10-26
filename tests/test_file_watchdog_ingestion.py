"""Exercise scheduled ingestion through real CSVs and filesystem events."""

import datetime
import os
import threading
import time
from collections import deque
from pathlib import Path

import pytest
from sortedcontainers import SortedList
from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileMovedEvent
from watchdog.observers import Observer

from source.kovaaks import data_service
from source.my_watchdog import file_watchdog


@pytest.fixture
def stores(monkeypatch):
    monkeypatch.setattr(data_service, "kovaaks_database", {})
    monkeypatch.setattr(
        data_service, "run_database", SortedList(key=lambda run: run.datetime_object)
    )
    monkeypatch.setattr(file_watchdog, "message_queue", [])
    monkeypatch.setattr(file_watchdog, "run_import_failure_queue", deque())


@pytest.fixture
def fast_worker(monkeypatch, stores):
    monkeypatch.setattr(file_watchdog, "FILE_GRACE_SECONDS", 0.01)
    monkeypatch.setattr(file_watchdog, "IMPORT_RETRY_DELAYS", (0.02, 0.04))
    monkeypatch.setattr(file_watchdog, "FAILED_FILE_RECHECK_SECONDS", 0.05)
    handler = file_watchdog.NewFileHandler()
    handler.start()
    yield handler
    handler.stop()
    handler.join(2)
    assert not handler._thread.is_alive()


def _csv(index=0):
    scenario = f"Synthetic scenario {index % 3}"
    stamp = datetime.datetime(2026, 10, 23, 12) + datetime.timedelta(seconds=index)
    name = f"{scenario} - Challenge - {stamp:%Y.%m.%d-%H.%M.%S} Stats.csv"
    body = "\n".join(
        [
            f"Score:,{100 + index}",
            "Sens Scale:,cm/360",
            "Horiz Sens:,40.8",
            f"Scenario:,{scenario}",
            data_service.POSSIBLE_SUB_CSV_HEADERS[0],
            "Rifle,100,50,75,100,,cm/360,40.8,40.8,103,0,0,0,0,0,0,0,0",
            "",
        ]
    )
    return name, body


def _write(folder, index=0):
    name, body = _csv(index)
    path = folder / name
    path.write_text(body, encoding="utf-8")
    return path


def _wait_for(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < deadline, "Ingestion did not converge"
        threading.Event().wait(0.005)


def test_native_observer_drains_a_thousand_file_burst_in_one_grace_period(
    tmp_path, monkeypatch, stores
):
    loaded = threading.Event()
    writers = set()
    real_load = file_watchdog.load_csv_file_into_database

    def load(path):
        writers.add(threading.get_ident())
        result = real_load(path)
        if len(data_service.run_database) == 1000:
            loaded.set()
        return result

    monkeypatch.setattr(file_watchdog, "load_csv_file_into_database", load)
    handler = file_watchdog.NewFileHandler()
    observer = Observer()
    observer.schedule(handler, str(tmp_path), recursive=False)
    handler.start()
    observer.start()
    start = time.monotonic()
    try:
        for index in range(1000):
            _write(tmp_path, index)
        assert loaded.wait(6), f"Only {len(data_service.run_database)} of 1000 imported"
        _wait_for(lambda: len(file_watchdog.message_queue) == 1000)
        elapsed = time.monotonic() - start
        print(f"native_burst: 1000 imported and published in {elapsed:.3f}s")
        assert elapsed < 6
        assert len(writers) == 1
        assert threading.get_ident() not in writers
        assert len({run.stats_file_name for run in data_service.run_database}) == 1000
        assert len({message.run_id for message in file_watchdog.message_queue}) == 1000
        assert file_watchdog.drain_run_import_failures() == []
    finally:
        observer.stop()
        observer.join()
        handler.stop()
        handler.join(2)
    assert not handler._thread.is_alive()


def test_duplicate_events_and_recreation_import_one_run(tmp_path, fast_worker):
    path = _write(tmp_path)
    event = FileCreatedEvent(str(path))
    for _ in range(200):
        fast_worker.on_created(event)
    _wait_for(lambda: len(file_watchdog.message_queue) == 1)
    path.unlink()
    _write(tmp_path)
    fast_worker.on_created(event)
    fast_worker.on_modified(FileModifiedEvent(str(path)))
    _wait_for(lambda: not fast_worker._pending)
    assert len(data_service.run_database) == 1
    assert len(file_watchdog.message_queue) == 1


def test_startup_imports_seed_the_successful_identity_set(
    tmp_path, monkeypatch, stores
):
    path = _write(tmp_path)
    assert data_service.load_csv_file_into_database(str(path))
    handler = file_watchdog.NewFileHandler()
    handler.on_created(FileCreatedEvent(str(path)))
    assert handler._pending == {}
    assert file_watchdog.message_queue == []


def test_incomplete_file_retries_without_holding_up_a_ready_file(
    tmp_path, monkeypatch, fast_worker
):
    name, body = _csv()
    incomplete = tmp_path / name
    incomplete.write_text("", encoding="utf-8")
    ready = _write(tmp_path, 1)
    attempts = []
    real_extract = file_watchdog.extract_data_from_file

    def extract(path):
        attempts.append(Path(path).name)
        return real_extract(path)

    monkeypatch.setattr(file_watchdog, "extract_data_from_file", extract)
    fast_worker.on_created(FileCreatedEvent(str(incomplete)))
    fast_worker.on_created(FileCreatedEvent(str(ready)))
    _wait_for(lambda: len(file_watchdog.message_queue) == 1)
    assert file_watchdog.message_queue[0].run_id == ready.name
    assert attempts[:2] == [incomplete.name, ready.name]
    # No modify notification: the scheduled retry alone must recover it.
    incomplete.write_text(body, encoding="utf-8")
    _wait_for(lambda: len(file_watchdog.message_queue) == 2)
    assert len(data_service.run_database) == 2
    assert file_watchdog.drain_run_import_failures() == []


def test_exhausted_retries_report_once_and_recheck_until_recovered(
    tmp_path, monkeypatch, fast_worker
):
    attempts = []
    real_extract = file_watchdog.extract_data_from_file

    def extract(path):
        attempts.append(path)
        return real_extract(path)

    monkeypatch.setattr(file_watchdog, "extract_data_from_file", extract)
    name, body = _csv()
    path = tmp_path / name
    path.write_text("", encoding="utf-8")
    fast_worker.on_created(FileCreatedEvent(str(path)))
    _wait_for(lambda: bool(file_watchdog.run_import_failure_queue))
    assert file_watchdog.drain_run_import_failures() == [
        file_watchdog.RUN_IMPORT_FAILURE_MESSAGE
    ]
    key = os.path.normcase(os.path.abspath(path))
    pending = fast_worker._pending[key]
    assert pending.attempts == len(file_watchdog.IMPORT_RETRY_DELAYS)
    _wait_for(lambda: len(attempts) >= len(file_watchdog.IMPORT_RETRY_DELAYS) + 3)
    assert file_watchdog.drain_run_import_failures() == []
    path.write_text(body, encoding="utf-8")
    _wait_for(lambda: len(file_watchdog.message_queue) == 1)
    assert len(data_service.run_database) == 1
    assert file_watchdog.drain_run_import_failures() == []


def test_handler_survives_a_read_exception_and_imports_the_next_file(
    tmp_path, monkeypatch, fast_worker
):
    blocked = _write(tmp_path)
    ready = _write(tmp_path, 1)
    real_extract = file_watchdog.extract_data_from_file
    release = threading.Event()

    def extract(path):
        if Path(path).name == blocked.name and not release.is_set():
            raise PermissionError("still locked")
        return real_extract(path)

    monkeypatch.setattr(file_watchdog, "extract_data_from_file", extract)
    fast_worker.on_created(FileCreatedEvent(str(blocked)))
    fast_worker.on_created(FileCreatedEvent(str(ready)))
    _wait_for(lambda: len(file_watchdog.message_queue) == 1)
    assert file_watchdog.message_queue[0].run_id == ready.name
    release.set()
    _wait_for(lambda: len(file_watchdog.message_queue) == 2)


def test_rename_to_final_and_modified_only_arrivals_are_imported(tmp_path, fast_worker):
    moved = _write(tmp_path)
    modified = _write(tmp_path, 1)
    fast_worker.on_moved(FileMovedEvent(str(tmp_path / "unfinished.tmp"), str(moved)))
    fast_worker.on_modified(FileModifiedEvent(str(modified)))
    _wait_for(lambda: len(file_watchdog.message_queue) == 2)
    assert len(data_service.run_database) == 2


def test_stop_wakes_a_worker_waiting_on_a_file_deadline(tmp_path, monkeypatch, stores):
    monkeypatch.setattr(file_watchdog, "FILE_GRACE_SECONDS", 60)
    handler = file_watchdog.NewFileHandler()
    handler.on_created(FileCreatedEvent(str(_write(tmp_path))))
    handler.start()
    handler.stop()
    handler.join(0.5)
    assert not handler._thread.is_alive()
    assert len(data_service.run_database) == 0


def test_stop_allows_an_active_import_to_finish(tmp_path, monkeypatch, fast_worker):
    entered = threading.Event()
    release = threading.Event()
    real_load = file_watchdog.load_csv_file_into_database

    def load(path):
        entered.set()
        assert release.wait(2)
        return real_load(path)

    monkeypatch.setattr(file_watchdog, "load_csv_file_into_database", load)
    fast_worker.on_created(FileCreatedEvent(str(_write(tmp_path))))
    assert entered.wait(2)
    fast_worker.stop()
    release.set()
    fast_worker.join(2)
    assert len(data_service.run_database) == len(file_watchdog.message_queue) == 1


def test_modify_refreshes_only_its_own_initial_deadline(tmp_path, monkeypatch, stores):
    monkeypatch.setattr(file_watchdog, "FILE_GRACE_SECONDS", 1)
    handler = file_watchdog.NewFileHandler()
    first = _write(tmp_path)
    second = _write(tmp_path, 1)
    monkeypatch.setattr(file_watchdog.time, "monotonic", lambda: 100.0)
    handler.on_created(FileCreatedEvent(str(first)))
    handler.on_created(FileCreatedEvent(str(second)))
    monkeypatch.setattr(file_watchdog.time, "monotonic", lambda: 100.5)
    handler.on_created(FileCreatedEvent(str(first)))
    handler.on_modified(FileModifiedEvent(str(second)))
    first_key = os.path.normcase(os.path.abspath(first))
    second_key = os.path.normcase(os.path.abspath(second))
    assert handler._pending[first_key].ready_at == 101
    assert handler._pending[second_key].ready_at == 101.5


def test_performance_file_can_arrive_during_the_grace_period(
    tmp_path, monkeypatch, stores
):
    stats = tmp_path / "stats"
    stats.mkdir()
    path = _write(stats)
    companion = tmp_path / "performances" / "companion.perf"
    observed = []
    monkeypatch.setattr(file_watchdog, "FILE_GRACE_SECONDS", 0.1)
    monkeypatch.setattr(
        file_watchdog,
        "note_performance_file",
        lambda _run: observed.append(companion.exists()),
    )
    handler = file_watchdog.NewFileHandler()
    handler.start()
    try:
        handler.on_created(FileCreatedEvent(str(path)))
        assert file_watchdog.message_queue == []
        companion.parent.mkdir()
        companion.write_bytes(b"performance")
        _wait_for(lambda: len(file_watchdog.message_queue) == 1)
        assert observed == [True]
    finally:
        handler.stop()
        handler.join(2)


@pytest.mark.skipif(os.name != "nt", reason="Windows filesystem identity")
def test_windows_case_alias_events_preserve_the_original_run_name(
    tmp_path, fast_worker
):
    path = _write(tmp_path)
    fast_worker.on_created(FileCreatedEvent(str(path)))
    fast_worker.on_created(FileCreatedEvent(str(path).upper()))
    _wait_for(lambda: len(file_watchdog.message_queue) == 1)
    assert file_watchdog.message_queue[0].run_id == path.name
    assert data_service.run_database[0].stats_file_name == path.name
    assert len(data_service.run_database) == 1


def test_pending_run_loaded_before_worker_start_is_not_announced_again(
    tmp_path, monkeypatch, stores
):
    monkeypatch.setattr(file_watchdog, "FILE_GRACE_SECONDS", 0.01)
    path = _write(tmp_path)
    handler = file_watchdog.NewFileHandler()
    handler.on_created(FileCreatedEvent(str(path)))
    assert data_service.load_csv_file_into_database(str(path))

    def unexpected_parse(_path):
        raise AssertionError("An imported file must be skipped before parsing")

    monkeypatch.setattr(file_watchdog, "extract_data_from_file", unexpected_parse)
    handler.start()
    try:
        _wait_for(lambda: not handler._pending)
        assert len(data_service.run_database) == 1
        assert file_watchdog.message_queue == []
        assert file_watchdog.drain_run_import_failures() == []
    finally:
        handler.stop()
        handler.join(2)
