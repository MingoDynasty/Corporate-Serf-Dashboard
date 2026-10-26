"""Prove the scan-to-watchdog handoff with real CSVs and an actual observer."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

STARTUP_PROBE = """
import json
import threading
from pathlib import Path

import requests
import source.app as app
from source.kovaaks import data_service
from source.my_queue.message_queue import message_queue
from source.my_watchdog.file_watchdog import run_import_failure_queue

arrival = {arrival!r}
stats = Path({stats_dir!r})
names = {{
    phase: f"Startup probe - Challenge - 2026.10.23-12.00.{{second:02d}} Stats.csv"
    for phase, second in (("before", 0), ("gap", 1), ("live", 2))
}}
live_finished = threading.Event()
writes = []

def write_run(phase):
    (stats / names[phase]).write_text(
        "\\n".join([
            "Score:,100",
            "Sens Scale:,Overwatch",
            "Horiz Sens:,2",
            "Scenario:,Startup probe",
            data_service.POSSIBLE_SUB_CSV_HEADERS[0],
            "Rifle,10,5,50,100",
            "",
        ]),
        encoding="utf-8",
    )

def forbid_network(*args, **kwargs):
    raise AssertionError("The startup probe must stay offline")

requests.sessions.Session.request = forbid_network
write_run("before")
# An old unreadable CSV remains startup log information, with no live toast.
(stats / "Unreadable - Challenge - 2026.10.23-12.00.03 Stats.csv").write_text("Score:", encoding="utf-8")
original_load = data_service.load_csv_file_into_database

def record_load(path):
    loaded = original_load(path)
    if loaded:
        writes.append((Path(path).name, threading.current_thread().name))
    return loaded

data_service.load_csv_file_into_database = record_load
# The ingestion worker holds its own imported reference to the same loader.
import source.my_watchdog.file_watchdog as file_watchdog
file_watchdog.load_csv_file_into_database = record_load
OriginalObserver = app.Observer

class Observer(OriginalObserver):
    def start(self):
        if arrival == "before_observer_start":
            write_run("gap")
        super().start()
        if arrival == "after_observer_start":
            write_run("gap")

original_import = file_watchdog.import_run_file

def record_import(path):
    imported = original_import(path)
    if imported and len(message_queue) == 2:
        live_finished.set()
    return imported

file_watchdog.import_run_file = record_import
app.Observer = Observer
app.bind_server_socket = lambda *args, **kwargs: []

def serve(*args, **kwargs):
    write_run("live")
    assert live_finished.wait(15), "Startup and live imports did not converge"
    # Drain observer dispatch as well as waiting for worker publication.
    observer = next(t for t in threading.enumerate() if isinstance(t, Observer))
    observer.event_queue.join()
    runs = data_service.get_all_runs()
    assert sorted(r.stats_file_name for r in runs) == sorted(names.values()), runs
    assert data_service.get_scenario_stats("Startup probe").number_of_runs == 3
    assert sorted(m.run_id for m in message_queue) == sorted([names["gap"], names["live"]])
    assert not run_import_failure_queue
    assert [name for name, thread in writes if thread == "MainThread"] == [names["before"]]
    assert {{thread for name, thread in writes if name != names["before"]}} == {{"run-import"}}
    assert len(writes) == 3, writes
    print("STARTUP_RESULT=" + json.dumps({{"runs": len(runs), "messages": len(message_queue)}}))

app.serve = serve
app.main()
"""


@pytest.mark.parametrize(
    "arrival",
    ["before_observer_start", "after_observer_start"],
)
def test_startup_imports_an_arrival_once_across_the_watchdog_handoff(
    tmp_path: Path,
    arrival: str,
) -> None:
    state_root = tmp_path / "state"
    stats_dir = state_root / "stats"
    stats_dir.mkdir(parents=True)
    (state_root / "config.toml").write_text("port = 8050\n", encoding="utf-8")
    (state_root / "data").mkdir()
    (state_root / "data" / "settings.json").write_text(
        json.dumps({"schema_version": 1, "stats_dir": str(stats_dir)}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            STARTUP_PROBE.format(arrival=arrival, stats_dir=str(stats_dir)),
        ],
        cwd=state_root,
        env={
            **os.environ,
            "PYTHONPATH": str(REPO_ROOT),
            "CSD_STATE_DIR": str(state_root),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'STARTUP_RESULT={"runs": 3, "messages": 2}' in result.stdout
