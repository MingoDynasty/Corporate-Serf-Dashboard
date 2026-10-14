import dataclasses
import datetime
import logging
from types import SimpleNamespace

import pytest
from sortedcontainers import SortedList

from source.components.score_threshold import (
    ThresholdVerdict,
    judge_run,
    shown_percentage,
)
from source.config import settings_service
from source.kovaaks import data_service
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

    assert 'Detected new file: "notes.txt"' in caplog.messages


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
        "pace_constant",
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


# --- Normalized sensitivity groups, from a real stats file -----------------
#
# These go through the real parser, where the tests above stand it in: what
# they hold is that a run recorded on a game's own scale joins the group its
# converted value lands in.

NORMALIZED_SCENARIO = "Normalized Scenario"
NORMALIZED_KEY = "40.8 cm/360"


def _stats_file(tmp_path, name, *, sens_scale, horizontal_sens, score):
    """Write one real stats file the parser will read, and return its path."""
    file_path = tmp_path / f"{name} - Challenge - 2025.03.04-21.30.00 Stats.csv"
    file_path.write_text(
        "\n".join(
            [
                f"Score:,{score}",
                f"Sens Scale:,{sens_scale}",
                # 0.2 Valorant and 40.8 cm/360 are the same physical
                # sensitivity at 1600 DPI, so both files record this increment.
                "Sens Increment:,0.199886",
                f"Horiz Sens:,{horizontal_sens}",
                f"Vert Sens:,{horizontal_sens}",
                "DPI:,1600",
                f"Scenario:,{NORMALIZED_SCENARIO}",
                data_service.POSSIBLE_SUB_CSV_HEADERS[0],
                "Rifle,100,50,75,100,,Valorant,0.2,0.2,103,0,0,0,0,0,0,0,0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return file_path


def _normalized_group(*scores):
    """The score-ascending SortedKeyList the production stores hold."""
    return SortedList(
        [
            RunData(
                datetime_object=datetime.datetime(2025, 3, 1, 12)
                + datetime.timedelta(minutes=index),
                score=score,
                sens_scale="cm/360",
                horizontal_sens=40.8,
                scenario=NORMALIZED_SCENARIO,
                accuracy=0.5,
            )
            for index, score in enumerate(scores)
        ],
        key=lambda item: item.score,
    )


def _import_real_file(monkeypatch, file_path, *, group_scores, high_score):
    """Import one real file and return the message the app would receive."""
    messages = []
    monkeypatch.setattr(file_watchdog.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        file_watchdog, "message_queue", SimpleNamespace(append=messages.append)
    )
    monkeypatch.setattr(
        file_watchdog, "load_csv_file_into_database", lambda _file: True
    )
    monkeypatch.setattr(
        file_watchdog, "schedule_rank_freshness_refresh", lambda *_args: None
    )
    monkeypatch.setattr(file_watchdog, "is_scenario_in_database", lambda _name: True)
    monkeypatch.setattr(file_watchdog, "get_high_score", lambda _name: high_score)
    monkeypatch.setattr(
        file_watchdog,
        "get_sensitivities_vs_runs",
        lambda _name: {NORMALIZED_KEY: _normalized_group(*group_scores)},
    )

    file_watchdog.NewFileHandler().on_created(
        SimpleNamespace(is_directory=False, src_path=str(file_path))
    )

    (message,) = messages
    return message


def test_a_converted_run_is_placed_against_the_group_it_normalizes_into(
    monkeypatch,
    tmp_path,
):
    # The converted run joins a group that already holds native runs, so it is
    # not the first at its sensitivity, and its place is counted against the
    # merged history. Against the converted runs alone it would have been the
    # best. Here it is sixth.
    message = _import_real_file(
        monkeypatch,
        _stats_file(
            tmp_path,
            "converted-into-native-group",
            sens_scale="Valorant",
            horizontal_sens="0.2",
            score=95,
        ),
        group_scores=(90, 100, 101, 102, 103, 104),
        high_score=104,
    )

    assert message.sensitivity == NORMALIZED_KEY
    assert message.is_new_sensitivity is False
    assert message.nth_score == 6


def test_a_native_run_at_a_converted_groups_value_is_not_a_new_sensitivity(
    monkeypatch,
    tmp_path,
):
    # The group exists only because converted runs landed on it, so this native
    # run is not the scenario's first at 40.8 cm/360. It is therefore judged
    # against the score threshold, where a first run at a sensitivity is not.
    message = _import_real_file(
        monkeypatch,
        _stats_file(
            tmp_path,
            "native-into-converted-group",
            sens_scale="cm/360",
            horizontal_sens="40.8",
            score=85,
        ),
        group_scores=(80, 85, 90),
        high_score=90,
    )

    assert message.sensitivity == NORMALIZED_KEY
    assert message.is_new_sensitivity is False
    assert message.scenario_previous_best == 90

    verdict = judge_run(
        message.score,
        message.scenario_previous_best,
        message.is_new_sensitivity,
        message.pace_constant,
        95.0,
    )

    assert isinstance(verdict, ThresholdVerdict)
    assert verdict.passed is False
    assert f"{shown_percentage(verdict):.1f}" == "94.4"
