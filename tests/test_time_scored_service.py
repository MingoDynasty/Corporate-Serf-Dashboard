import logging
import shutil
from datetime import datetime
from pathlib import Path

import pytest
from sortedcontainers import SortedList

from source.kovaaks import data_service, time_scored_service
from source.kovaaks.data_models import RunData
from source.kovaaks.time_scored_service import (
    PaceBasis,
    eligible_pace_constant,
    get_pace_basis,
    index_performance_files,
    note_performance_file,
)
from tests.performance_files import (
    COUNTDOWN_FIXTURE,
    COUNTDOWN_FIXTURE_HASH,
    DEFAULT_HASH,
    FIXED_LENGTH_FIXTURE,
    build_performance_file,
    countdown_events,
)

SCENARIO = "Ground Plaza Sparky V3"
OTHER_HASH = "ffffffffffffffffffffffffffffffff"
OLDEST, OLDER, NEWEST = (
    "2026.08.01-10.00.00",
    "2026.08.02-10.00.00",
    "2026.08.03-10.00.00",
)

COUNTDOWN = build_performance_file(countdown_events(1000.0, 60))
OTHER_VERSION_COUNTDOWN = build_performance_file(
    countdown_events(1000.0, 60), scenario_hash=OTHER_HASH
)
FIXED_LENGTH = build_performance_file([(1.0, 73.0), (2.0, 27.0), (3.0, 53.0)])
UNKNOWN_SCHEMA = build_performance_file(countdown_events(1000.0, 60), schema_version=2)


def _run(
    stamp: str,
    *,
    scenario_hash: str | None = DEFAULT_HASH,
    scenario: str = SCENARIO,
) -> RunData:
    return RunData(
        datetime_object=datetime.strptime(stamp, "%Y.%m.%d-%H.%M.%S"),
        score=900.0,
        sens_scale="cm/360",
        horizontal_sens=40.0,
        scenario=scenario,
        accuracy=0.5,
        scenario_hash=scenario_hash,
        stats_file_name=f"{scenario} - Challenge - {stamp} Stats.csv",
    )


def _performance_file(folder: Path, run: RunData) -> Path:
    assert run.stats_file_name is not None
    return folder / run.stats_file_name.replace(" Stats.csv", " Performance.perf")


@pytest.fixture
def folders(tmp_path) -> tuple[Path, Path]:
    """Lay out a stats folder with a ``performances`` folder beside it."""
    stats_dir = tmp_path / "stats"
    performance_dir = tmp_path / "performances"
    stats_dir.mkdir()
    performance_dir.mkdir()
    return stats_dir, performance_dir


@pytest.fixture
def store(monkeypatch):
    """Load runs through the real CSV loader, so the stores have their real shape."""
    monkeypatch.setattr(data_service, "kovaaks_database", {})
    monkeypatch.setattr(
        data_service,
        "run_database",
        SortedList(key=lambda run: run.datetime_object),
    )

    def load(*runs: RunData) -> None:
        pending = iter(runs)
        monkeypatch.setattr(
            data_service, "extract_data_from_file", lambda _file: next(pending)
        )
        for index in range(len(runs)):
            assert data_service.load_csv_file_into_database(f"run-{index}.csv")

    return load


def _files_read() -> set[str]:
    return set(time_scored_service._readings)


def test_the_newest_runs_file_decides_when_it_can_answer(folders, store):
    stats_dir, performance_dir = folders
    older, newest = _run(OLDER), _run(NEWEST)
    store(older, newest)
    _performance_file(performance_dir, older).write_bytes(FIXED_LENGTH)
    _performance_file(performance_dir, newest).write_bytes(COUNTDOWN)
    index_performance_files(str(stats_dir))

    assert get_pace_basis(SCENARIO) == PaceBasis(1000.0, DEFAULT_HASH)
    assert _files_read() == {_performance_file(performance_dir, newest).name}


def test_a_real_pair_is_recognized_by_its_stats_file_name(folders, store):
    stats_dir, performance_dir = folders
    stamp = COUNTDOWN_FIXTURE.name.split(" - Challenge - ")[1].split(" ")[0]
    run = _run(
        stamp,
        scenario="Air Pure Easier No UFO",
        scenario_hash=COUNTDOWN_FIXTURE_HASH,
    )
    store(run)
    shutil.copy(COUNTDOWN_FIXTURE, performance_dir)
    shutil.copy(FIXED_LENGTH_FIXTURE, performance_dir)
    index_performance_files(str(stats_dir))

    assert get_pace_basis("Air Pure Easier No UFO") == PaceBasis(
        1000.0, COUNTDOWN_FIXTURE_HASH
    )


def test_listing_the_folder_parses_nothing(folders, store):
    stats_dir, performance_dir = folders
    run = _run(NEWEST)
    store(run)
    _performance_file(performance_dir, run).write_bytes(COUNTDOWN)

    index_performance_files(str(stats_dir))

    assert _files_read() == set()


def test_a_newest_run_with_no_file_falls_to_the_next_run_of_its_hash(folders, store):
    stats_dir, performance_dir = folders
    older, newest = _run(OLDER), _run(NEWEST)
    store(older, newest)
    _performance_file(performance_dir, older).write_bytes(COUNTDOWN)
    index_performance_files(str(stats_dir))

    assert get_pace_basis(SCENARIO) == PaceBasis(1000.0, DEFAULT_HASH)


def test_a_newest_file_on_another_schema_leaves_the_scenario_recognized(folders, store):
    """A format change must not turn a recognized scenario back to score math."""
    stats_dir, performance_dir = folders
    older, newest = _run(OLDER), _run(NEWEST)
    store(older, newest)
    _performance_file(performance_dir, older).write_bytes(COUNTDOWN)
    _performance_file(performance_dir, newest).write_bytes(UNKNOWN_SCHEMA)
    index_performance_files(str(stats_dir))

    assert get_pace_basis(SCENARIO) == PaceBasis(1000.0, DEFAULT_HASH)


def test_an_older_file_of_another_hash_is_never_used(folders, store):
    stats_dir, performance_dir = folders
    older, newest = _run(OLDER, scenario_hash=OTHER_HASH), _run(NEWEST)
    store(older, newest)
    _performance_file(performance_dir, older).write_bytes(OTHER_VERSION_COUNTDOWN)
    _performance_file(performance_dir, newest).write_bytes(UNKNOWN_SCHEMA)
    index_performance_files(str(stats_dir))

    assert get_pace_basis(SCENARIO) is None
    assert _files_read() == {_performance_file(performance_dir, newest).name}


def test_a_newest_file_that_answers_not_time_scored_decides(folders, store):
    """Every ordinary scenario stops here, and no older file is read."""
    stats_dir, performance_dir = folders
    older, newest = _run(OLDER), _run(NEWEST)
    store(older, newest)
    _performance_file(performance_dir, older).write_bytes(COUNTDOWN)
    _performance_file(performance_dir, newest).write_bytes(FIXED_LENGTH)
    index_performance_files(str(stats_dir))

    assert get_pace_basis(SCENARIO) is None
    assert _files_read() == {_performance_file(performance_dir, newest).name}


def test_a_stats_folder_with_no_performances_folder_recognizes_nothing(tmp_path, store):
    stats_dir = tmp_path / "stats"
    stats_dir.mkdir()
    store(_run(NEWEST))

    index_performance_files(str(stats_dir))

    assert get_pace_basis(SCENARIO) is None


def test_a_scenario_with_no_runs_is_not_recognized(folders, store):
    stats_dir, performance_dir = folders
    store()
    _performance_file(performance_dir, _run(NEWEST)).write_bytes(COUNTDOWN)
    index_performance_files(str(stats_dir))

    assert get_pace_basis(SCENARIO) is None


def test_a_newest_run_with_no_hash_names_no_version(folders, store):
    stats_dir, performance_dir = folders
    older, newest = _run(OLDER), _run(NEWEST, scenario_hash=None)
    store(older, newest)
    _performance_file(performance_dir, older).write_bytes(COUNTDOWN)
    _performance_file(performance_dir, newest).write_bytes(COUNTDOWN)
    index_performance_files(str(stats_dir))

    assert get_pace_basis(SCENARIO) is None
    assert _files_read() == set()


def test_a_file_that_cannot_be_read_is_not_remembered(folders, store, caplog):
    """The next look tries again, and the older file stands in meanwhile."""
    stats_dir, performance_dir = folders
    older, newest = _run(OLDER), _run(NEWEST)
    store(older, newest)
    _performance_file(performance_dir, older).write_bytes(FIXED_LENGTH)
    newest_file = _performance_file(performance_dir, newest)
    newest_file.write_bytes(COUNTDOWN)
    index_performance_files(str(stats_dir))
    newest_file.unlink()

    with caplog.at_level(logging.WARNING, logger=time_scored_service.logger.name):
        assert get_pace_basis(SCENARIO) is None
    assert newest_file.name not in _files_read()
    assert any(
        message.startswith(f'Failed to read performance file "{newest_file.name}": ')
        for message in caplog.messages
    )

    newest_file.write_bytes(COUNTDOWN)

    assert get_pace_basis(SCENARIO) == PaceBasis(1000.0, DEFAULT_HASH)


def test_an_answer_is_remembered_by_file_name(folders, store):
    """A written file never changes, so each one is read at most once."""
    stats_dir, performance_dir = folders
    older, newest = _run(OLDER), _run(NEWEST)
    store(older, newest)
    older_file = _performance_file(performance_dir, older)
    newest_file = _performance_file(performance_dir, newest)
    older_file.write_bytes(COUNTDOWN)
    newest_file.write_bytes(UNKNOWN_SCHEMA)
    index_performance_files(str(stats_dir))
    assert get_pace_basis(SCENARIO) is not None

    older_file.unlink()
    newest_file.unlink()

    assert get_pace_basis(SCENARIO) == PaceBasis(1000.0, DEFAULT_HASH)
    assert _files_read() == {older_file.name, newest_file.name}


def test_a_file_that_appears_after_startup_joins_the_listing(folders, store):
    stats_dir, performance_dir = folders
    run = _run(NEWEST)
    store(run)
    index_performance_files(str(stats_dir))
    _performance_file(performance_dir, run).write_bytes(COUNTDOWN)
    assert get_pace_basis(SCENARIO) is None

    note_performance_file(run)

    assert get_pace_basis(SCENARIO) == PaceBasis(1000.0, DEFAULT_HASH)


def test_a_folder_the_game_creates_after_startup_is_still_found(tmp_path, store):
    stats_dir = tmp_path / "stats"
    stats_dir.mkdir()
    run = _run(NEWEST)
    store(run)
    index_performance_files(str(stats_dir))
    performance_dir = tmp_path / "performances"
    performance_dir.mkdir()
    _performance_file(performance_dir, run).write_bytes(COUNTDOWN)

    note_performance_file(run)

    assert get_pace_basis(SCENARIO) == PaceBasis(1000.0, DEFAULT_HASH)


def test_a_landed_run_with_no_performance_file_adds_nothing(folders, store):
    stats_dir, _performance_dir = folders
    run = _run(NEWEST)
    store(run)
    index_performance_files(str(stats_dir))

    note_performance_file(run)

    assert time_scored_service._performance_file_names == set()


def test_a_landed_run_is_judged_by_its_own_file_before_it_is_stored(folders, store):
    """The scenario's first run on a current build is what flips it to pace."""
    stats_dir, performance_dir = folders
    store(_run(OLDEST), _run(OLDER))
    index_performance_files(str(stats_dir))
    landed = _run(NEWEST)
    _performance_file(performance_dir, landed).write_bytes(COUNTDOWN)
    note_performance_file(landed)

    assert get_pace_basis(SCENARIO) is None
    assert get_pace_basis(SCENARIO, landed_run=landed) == PaceBasis(
        1000.0, DEFAULT_HASH
    )


def test_a_landed_run_older_than_the_newest_does_not_decide(folders, store):
    """A stats file copied in late keeps its place in the scenario's history."""
    stats_dir, performance_dir = folders
    newest = _run(NEWEST)
    store(newest)
    _performance_file(performance_dir, newest).write_bytes(FIXED_LENGTH)
    index_performance_files(str(stats_dir))
    landed = _run(OLDER)
    _performance_file(performance_dir, landed).write_bytes(COUNTDOWN)
    note_performance_file(landed)

    assert get_pace_basis(SCENARIO, landed_run=landed) is None


def test_a_run_whose_file_name_is_not_a_stats_name_has_no_performance_file(
    folders, store
):
    stats_dir, performance_dir = folders
    run = RunData(
        datetime_object=datetime(2026, 8, 3, 10),
        score=900.0,
        sens_scale="cm/360",
        horizontal_sens=40.0,
        scenario=SCENARIO,
        accuracy=0.5,
        scenario_hash=DEFAULT_HASH,
        stats_file_name="renamed.csv",
    )
    store(run)
    (performance_dir / "renamed.csv").write_bytes(COUNTDOWN)
    (performance_dir / "stray Performance.perf").write_bytes(COUNTDOWN)
    index_performance_files(str(stats_dir))

    note_performance_file(run)

    assert get_pace_basis(SCENARIO) is None
    assert time_scored_service._performance_file_names == {"stray Performance.perf"}


def test_each_parsed_file_logs_its_largest_distance(folders, store, caplog):
    stats_dir, performance_dir = folders
    run = _run(NEWEST)
    store(run)
    performance_file = _performance_file(performance_dir, run)
    performance_file.write_bytes(
        build_performance_file(countdown_events(1000.0, 60, early_by=0.25))
    )
    index_performance_files(str(stats_dir))

    with caplog.at_level(logging.DEBUG, logger=time_scored_service.logger.name):
        get_pace_basis(SCENARIO)

    assert (
        f'Performance file "{performance_file.name}" is time-scored: time limit '
        "1000, 60 score events, largest distance from the countdown 0.2500."
    ) in caplog.messages


def test_a_file_that_cannot_answer_says_so_in_the_log(folders, store, caplog):
    stats_dir, performance_dir = folders
    run = _run(NEWEST)
    store(run)
    performance_file = _performance_file(performance_dir, run)
    performance_file.write_bytes(UNKNOWN_SCHEMA)
    index_performance_files(str(stats_dir))

    with caplog.at_level(logging.DEBUG, logger=time_scored_service.logger.name):
        assert get_pace_basis(SCENARIO) is None

    assert (
        f'Performance file "{performance_file.name}" can\'t answer whether its '
        "scenario is time-scored."
    ) in caplog.messages


def test_the_constant_is_eligible_only_for_runs_of_its_version():
    basis = PaceBasis(1000.0, DEFAULT_HASH)
    current, another = _run(NEWEST), _run(OLDER)
    old_version = _run(OLDEST, scenario_hash=OTHER_HASH)
    no_hash = _run(OLDEST, scenario_hash=None)

    assert eligible_pace_constant(basis) == 1000.0
    assert eligible_pace_constant(basis, current) == 1000.0
    assert eligible_pace_constant(basis, current, another) == 1000.0
    assert eligible_pace_constant(basis, current, old_version) is None
    assert eligible_pace_constant(basis, no_hash) is None
    assert eligible_pace_constant(basis, current, None) is None
    assert eligible_pace_constant(None, current) is None
