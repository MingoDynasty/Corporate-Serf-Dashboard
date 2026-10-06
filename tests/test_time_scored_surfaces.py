"""A time-scored scenario, from real files on disk to every surface.

Each test lays out a stats folder with a ``performances`` folder beside it,
loads the stats files through the real loader, and lands a run through the
real watchdog handler. Nothing between the files and the surface is faked, so
these are the tests that would notice the table, the chart, and the watchdog
disagreeing about one scenario.
"""

import logging
from pathlib import Path
from types import SimpleNamespace

import dash
import pytest
from sortedcontainers import SortedList

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.app_shell import _run_event_data  # noqa: E402
from source.kovaaks import data_service, playlist_scenarios_service  # noqa: E402
from source.kovaaks.api_models import (  # noqa: E402
    ScenarioRankInfo,
    ScenarioRankStatus,
)
from source.kovaaks.data_models import Rank  # noqa: E402
from source.kovaaks.time_scored_service import (  # noqa: E402
    index_performance_files,
)
from source.my_watchdog import file_watchdog  # noqa: E402
from source.pages import home  # noqa: E402
from tests.performance_files import (  # noqa: E402
    DEFAULT_HASH,
    build_performance_file,
    countdown_events,
)

SCENARIO = "Ground Plaza Sparky V3"
OLD_VERSION_HASH = "ffffffffffffffffffffffffffffffff"
LADDER = [
    Rank(name="Cerulean", color="#ffffff", threshold=892.5),
    Rank(name="Lavender", color="#ffffff", threshold=899),
]
COUNTDOWN = build_performance_file(countdown_events(1000.0, 60))
FIXED_LENGTH = build_performance_file([(1.0, 73.0), (2.0, 27.0), (3.0, 53.0)])
UNKNOWN_SCHEMA = build_performance_file(countdown_events(1000.0, 60), schema_version=2)

FIRST, SECOND, THIRD = (
    "2026.08.01-10.00.00",
    "2026.08.02-10.00.00",
    "2026.08.03-10.00.00",
)


class _Folders:
    """A stats folder and the ``performances`` folder beside it."""

    def __init__(self, root: Path):
        self.stats = root / "stats"
        self.performances = root / "performances"
        self.stats.mkdir()
        self.performances.mkdir()

    def stats_file(
        self,
        stamp: str,
        score: float,
        *,
        scenario_hash: str | None = DEFAULT_HASH,
    ) -> Path:
        """Write one stats file the real parser reads, and return its path."""
        lines = [
            f"Score:,{score}",
            "Sens Scale:,cm/360",
            "Horiz Sens:,40.8",
            "Vert Sens:,40.8",
            f"Scenario:,{SCENARIO}",
        ]
        if scenario_hash is not None:
            lines.append(f"Hash:,{scenario_hash}")
        lines += [
            data_service.POSSIBLE_SUB_CSV_HEADERS[0],
            "Rifle,100,50,75,100,,cm/360,40.8,40.8,103,0,0,0,0,0,0,0,0",
            "",
        ]
        path = self.stats / f"{SCENARIO} - Challenge - {stamp} Stats.csv"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def performance_file(self, stamp: str, data: bytes = COUNTDOWN) -> Path:
        path = self.performances / f"{SCENARIO} - Challenge - {stamp} Performance.perf"
        path.write_bytes(data)
        return path

    def start(self) -> None:
        """Load every stats file and list the performance files, as startup does."""
        data_service.initialize_kovaaks_data(str(self.stats))
        index_performance_files(str(self.stats))


@pytest.fixture
def folders(tmp_path, monkeypatch) -> _Folders:
    monkeypatch.setattr(data_service, "kovaaks_database", {})
    monkeypatch.setattr(
        data_service,
        "run_database",
        SortedList(key=lambda run: run.datetime_object),
    )
    return _Folders(tmp_path)


def _land(monkeypatch, stats_file: Path):
    """Land one stats file through the watchdog and return its queued message."""
    messages = []
    monkeypatch.setattr(file_watchdog.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        file_watchdog, "message_queue", SimpleNamespace(append=messages.append)
    )
    monkeypatch.setattr(
        file_watchdog, "schedule_rank_freshness_refresh", lambda *_args: None
    )
    file_watchdog.run_import_failure_queue.clear()

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(is_directory=False, src_path=str(stats_file))
    )

    assert file_watchdog.drain_run_import_failures() == []
    (message,) = messages
    return message


def _next_rank() -> str:
    """Build the scenario's benchmark row as the table does, and read its cell."""
    row = playlist_scenarios_service._build_row(
        SCENARIO,
        0,
        ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN),
        "generation-1",
        "KovaaKsTestCode",
        ladder=LADDER,
        group=None,
        mark_unresolved_pending=False,
    )
    return row["next_tier_display"]


def _threshold_line() -> float:
    """Return the score the chart draws the 95% threshold line at."""
    return round(
        home._score_threshold_line(
            SCENARIO, data_service.get_high_score(SCENARIO), 95.0
        ),
        2,
    )


def test_a_recognized_scenario_reads_pace_on_the_table_and_the_chart(folders):
    folders.stats_file(FIRST, 884.41)
    folders.stats_file(SECOND, 896.2)
    folders.performance_file(SECOND)
    folders.start()

    assert _next_rank() == "+2.8% faster to Lavender"
    assert _threshold_line() == 890.74


def test_a_scenario_with_no_performance_file_keeps_score_on_every_surface(
    folders, monkeypatch
):
    folders.stats_file(FIRST, 884.41)
    folders.stats_file(SECOND, 896.2)
    folders.start()

    message = _land(monkeypatch, folders.stats_file(THIRD, 883.02))

    assert message.pace_constant is None
    assert _next_rank() == "+0.4% to Lavender"
    assert _threshold_line() == 851.39


def test_a_landed_runs_message_carries_the_constant_from_its_own_file(
    folders, monkeypatch
):
    folders.stats_file(FIRST, 884.41)
    folders.stats_file(SECOND, 896.2)
    folders.performance_file(SECOND)
    folders.start()
    folders.performance_file(
        THIRD, build_performance_file(countdown_events(1200.0, 60), time_limit=1200.0)
    )

    message = _land(monkeypatch, folders.stats_file(THIRD, 883.02))

    # 1,200 is the landed run's own file. The older file says 1,000.
    assert message.pace_constant == 1200.0
    assert message.scenario_previous_best == 896.2


def test_a_file_that_appears_after_startup_is_seen_by_every_surface_alike(
    folders, monkeypatch
):
    """A scenario's first run on a current build flips it to pace, everywhere.

    Startup found stats files only, so the table and the chart read score. The
    landed pair must reach all three without a restart: the watchdog judges
    the run by its file, and the table and the chart find the same file on
    their next rebuild.
    """
    folders.stats_file(FIRST, 884.41)
    folders.stats_file(SECOND, 896.2)
    folders.start()
    assert _next_rank() == "+0.4% to Lavender"
    assert _threshold_line() == 851.39

    folders.performance_file(THIRD)
    message = _land(monkeypatch, folders.stats_file(THIRD, 883.02))

    assert message.pace_constant == 1000.0
    assert _next_rank() == "+2.8% faster to Lavender"
    assert _threshold_line() == 890.74


def test_a_first_run_of_a_scenario_carries_no_constant_and_lists_its_file(
    folders, monkeypatch
):
    """Nothing judges a first run, and the next surface still finds its file."""
    folders.start()
    folders.performance_file(FIRST)

    message = _land(monkeypatch, folders.stats_file(FIRST, 896.2))

    assert message.scenario_previous_best is None
    assert message.pace_constant is None
    assert _next_rank() == "+2.8% faster to Lavender"


def test_a_previous_best_from_another_version_keeps_score_everywhere(
    folders, monkeypatch
):
    """The constant was read from the current version, and the PB is not of it."""
    folders.stats_file(FIRST, 896.2, scenario_hash=OLD_VERSION_HASH)
    folders.stats_file(SECOND, 884.41)
    folders.performance_file(SECOND)
    folders.start()
    assert _next_rank() == "+0.4% to Lavender"
    assert _threshold_line() == 851.39

    folders.performance_file(THIRD)
    message = _land(monkeypatch, folders.stats_file(THIRD, 883.02))

    assert message.pace_constant is None


def test_a_landed_run_from_another_version_carries_no_constant(folders, monkeypatch):
    folders.stats_file(FIRST, 884.41)
    folders.stats_file(SECOND, 896.2)
    folders.performance_file(SECOND)
    folders.start()

    message = _land(
        monkeypatch,
        folders.stats_file(THIRD, 883.02, scenario_hash=OLD_VERSION_HASH),
    )

    assert message.pace_constant is None


def test_a_current_version_run_that_beats_an_old_pb_turns_the_scenario_to_pace(
    folders, monkeypatch
):
    folders.stats_file(FIRST, 890.0, scenario_hash=OLD_VERSION_HASH)
    folders.stats_file(SECOND, 884.41)
    folders.performance_file(SECOND)
    folders.start()
    assert _next_rank() == "+0.3% to Cerulean"

    folders.performance_file(THIRD)
    message = _land(monkeypatch, folders.stats_file(THIRD, 896.2))

    # The run that beat it was judged against the old version's PB, by score.
    assert message.pace_constant is None
    assert _next_rank() == "+2.8% faster to Lavender"
    assert _threshold_line() == 890.74


def test_a_landed_file_on_another_schema_leaves_the_scenario_on_pace(
    folders, monkeypatch
):
    folders.stats_file(FIRST, 884.41)
    folders.stats_file(SECOND, 896.2)
    folders.performance_file(SECOND)
    folders.start()
    folders.performance_file(THIRD, UNKNOWN_SCHEMA)

    message = _land(monkeypatch, folders.stats_file(THIRD, 883.02))

    assert message.pace_constant == 1000.0
    assert _next_rank() == "+2.8% faster to Lavender"


def test_a_landed_file_that_shows_no_countdown_turns_the_scenario_back(
    folders, monkeypatch
):
    folders.stats_file(FIRST, 884.41)
    folders.stats_file(SECOND, 896.2)
    folders.performance_file(SECOND)
    folders.start()
    assert _next_rank() == "+2.8% faster to Lavender"
    folders.performance_file(THIRD, FIXED_LENGTH)

    message = _land(monkeypatch, folders.stats_file(THIRD, 883.02))

    assert message.pace_constant is None
    assert _next_rank() == "+0.4% to Lavender"
    assert _threshold_line() == 851.39


def test_the_landed_run_reaches_the_toast_as_a_percentage_of_pb_pace(
    folders, monkeypatch
):
    folders.stats_file(FIRST, 884.41)
    folders.stats_file(SECOND, 896.17)
    folders.performance_file(SECOND)
    folders.start()
    folders.performance_file(THIRD)

    message = _land(monkeypatch, folders.stats_file(THIRD, 883.02))
    notification = home._build_run_event_notification(
        {
            # Projected the way the app shell's drain does.
            "latest": _run_event_data(message, message.datetime_created, 120.0),
            "celebrated_run_id": None,
        },
        SCENARIO,
        5,
        95.0,
        True,
        True,
    )

    assert notification["title"] == "Below threshold"
    assert notification["message"] == (
        f"{SCENARIO}: 883.02, 88.8% of PB pace (need 95.0%). "
        "Still your 3rd-best at 40.8 cm/360."
    )


def _session_log(caplog) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == file_watchdog.logger.name
    ]


def test_the_session_log_judges_a_time_scored_run_by_pace(folders, monkeypatch, caplog):
    """883.02 is 98.5% of 896.17 by score, and 88.8% of its pace."""
    folders.stats_file(FIRST, 884.41)
    folders.stats_file(SECOND, 896.17)
    folders.performance_file(SECOND)
    folders.start()
    folders.performance_file(THIRD)

    with caplog.at_level(logging.DEBUG, logger=file_watchdog.logger.name):
        _land(monkeypatch, folders.stats_file(THIRD, 883.02))

    log = _session_log(caplog)
    assert (
        "Current score (883.02) is -11.24% from high score (896.17) by pace "
        "with score threshold (890.71)"
    ) in log
    assert "Failed to meet the score threshold. Keep grinding..." in log
    assert not any(line.startswith("Successfully passed") for line in log)


def test_the_session_log_keeps_score_for_a_run_with_no_constant(
    folders, monkeypatch, caplog
):
    folders.stats_file(FIRST, 884.41)
    folders.stats_file(SECOND, 896.17)
    folders.start()

    with caplog.at_level(logging.DEBUG, logger=file_watchdog.logger.name):
        _land(monkeypatch, folders.stats_file(THIRD, 883.02))

    log = _session_log(caplog)
    assert (
        "Current score (883.02) is -1.47% from high score (896.17) "
        "with score threshold (851.36)"
    ) in log
    assert any(line.startswith("Successfully passed") for line in log)


def test_the_session_log_moves_the_pace_threshold_on_a_new_high_score(
    folders, monkeypatch, caplog
):
    folders.stats_file(FIRST, 870.0)
    folders.stats_file(SECOND, 884.41)
    folders.performance_file(SECOND)
    folders.start()
    folders.performance_file(THIRD)

    with caplog.at_level(logging.DEBUG, logger=file_watchdog.logger.name):
        _land(monkeypatch, folders.stats_file(THIRD, 896.17))

    log = _session_log(caplog)
    assert (
        "Current score (896.17) is +11.33% from high score (884.41) by pace "
        "with score threshold (878.33)"
    ) in log
    assert "Score threshold increased from (878.33) to (890.71)" in log
    assert any(line.startswith("Successfully passed") for line in log)


def test_a_failed_pace_lookup_costs_the_constant_and_never_the_run(
    folders, monkeypatch, caplog
):
    folders.stats_file(FIRST, 884.41)
    folders.stats_file(SECOND, 896.2)
    folders.performance_file(SECOND)
    folders.start()

    def fail(*_args, **_kwargs):
        raise RuntimeError("the run list changed size during iteration")

    monkeypatch.setattr(file_watchdog, "get_pace_basis", fail)

    with caplog.at_level(logging.WARNING, logger=file_watchdog.logger.name):
        message = _land(monkeypatch, folders.stats_file(THIRD, 883.02))

    assert message.pace_constant is None
    assert data_service.get_scenario_stats(SCENARIO).number_of_runs == 3
    failures = [
        record
        for record in caplog.records
        if record.getMessage() == f'Failed to tell whether "{SCENARIO}" is time-scored'
    ]
    assert len(failures) == 1
    assert failures[0].exc_info is not None


def test_no_performances_folder_reads_score_and_logs_no_failure(
    folders, monkeypatch, caplog
):
    folders.performances.rmdir()
    folders.stats_file(FIRST, 884.41)
    folders.stats_file(SECOND, 896.2)

    with caplog.at_level(logging.WARNING):
        folders.start()
        message = _land(monkeypatch, folders.stats_file(THIRD, 883.02))

    assert message.pace_constant is None
    assert _next_rank() == "+0.4% to Lavender"
    assert _threshold_line() == 851.39
    assert [
        record for record in caplog.records if record.levelno >= logging.WARNING
    ] == []
