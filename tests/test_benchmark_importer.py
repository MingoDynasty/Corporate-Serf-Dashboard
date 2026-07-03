import json
import logging
from pathlib import Path

import pytest
import requests

from scripts.benchmark_importer import script
from scripts.benchmark_importer.models import (
    EvxlDatabaseItem,
    EvxlPlaylist,
    EvxlPlaylistScenario,
)


def _write_evxl_data(path: Path, benchmarks: list[dict]) -> None:
    path.write_text(json.dumps(benchmarks), encoding="utf-8")


def _difficulty(
    sharecode: str,
    benchmark_id: int,
    rank_colors: dict[str, str],
    name: str,
) -> dict:
    return {
        "difficultyName": name,
        "kovaaksBenchmarkId": benchmark_id,
        "sharecode": sharecode,
        "rankColors": rank_colors,
    }


def _benchmark_response(rank_maxes: list[float]) -> dict:
    return {
        "benchmark_progress": 0,
        "overall_rank": 0,
        "categories": {
            "Clicking": {
                "benchmark_progress": 0,
                "category_rank": 0,
                "rank_maxes": rank_maxes,
                "scenarios": {
                    "Test Scenario": {
                        "score": 0,
                        "leaderboard_rank": None,
                        "scenario_rank": 0,
                        "rank_maxes": rank_maxes,
                        "leaderboard_id": 1,
                    }
                },
            }
        },
        "ranks": [],
    }


def test_get_evxl_playlist_uses_retry_policy_and_snake_case_model(monkeypatch):
    calls = []

    class Response:
        @staticmethod
        def json():
            return {
                "playlist": {
                    "playlist_name": "Setsunai Static Benchmark Normal",
                    "playlist_code": "KovaaKsHeadshottingAquamarineCapture",
                    "scenario_list": [{"scenario_name": "Reflex Flick - Easy"}],
                },
                "playlist_b64": "ignored",
            }

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(script, "_get_with_retry", fake_get)

    playlist = script.get_evxl_playlist("KovaaKsHeadshottingAquamarineCapture")

    assert playlist.playlist_name == "Setsunai Static Benchmark Normal"
    assert calls == [
        (
            script.EVXL_PLAYLIST_BY_CODE_URL,
            {
                "params": {"shareCode": "KovaaKsHeadshottingAquamarineCapture"},
                "attempts": 4,
                "backoff_seconds": (2, 4, 8),
            },
        )
    ]


def test_load_evxl_data_dedupes_identical_payload_once(tmp_path, caplog):
    data_path = tmp_path / "benchmarks.json"
    identical = _difficulty(
        "KovaaKsSame",
        10,
        {"Bronze": "#111", "Silver": "#222"},
        "Easy",
    )
    _write_evxl_data(
        data_path,
        [
            {"benchmarkName": "One", "difficulties": [identical]},
            {
                "benchmarkName": "Two",
                "difficulties": [{**identical, "difficultyName": "Normal"}],
            },
        ],
    )
    caplog.set_level(logging.INFO, logger=script.__name__)

    database, conflicts = script.load_evxl_data(data_path)

    assert list(database) == ["KovaaKsSame"]
    assert conflicts == {}
    assert caplog.messages == [
        "Deduplicated 2 identical entries for sharecode KovaaKsSame"
    ]


def test_load_evxl_data_classifies_ordered_rank_conflicts(tmp_path):
    data_path = tmp_path / "benchmarks.json"
    _write_evxl_data(
        data_path,
        [
            {
                "benchmarkName": "Benchmark One",
                "difficulties": [
                    _difficulty(
                        "KovaaKsConflict",
                        10,
                        {"Bronze": "#111", "Silver": "#222"},
                        "Easy",
                    )
                ],
            },
            {
                "benchmarkName": "Benchmark Two",
                "difficulties": [
                    _difficulty(
                        "KovaaKsConflict",
                        10,
                        {"Silver": "#222", "Bronze": "#111"},
                        "Hard",
                    )
                ],
            },
        ],
    )

    database, conflicts = script.load_evxl_data(data_path)

    assert database == {}
    assert [claim.benchmark for claim in conflicts["KovaaKsConflict"]] == [
        "Benchmark One",
        "Benchmark Two",
    ]
    assert conflicts["KovaaKsConflict"][1].difficulty == "Hard"
    assert conflicts["KovaaKsConflict"][1].benchmark_id == 10
    assert conflicts["KovaaKsConflict"][1].rank_ladder == (
        ("Silver", "#222"),
        ("Bronze", "#111"),
    )


@pytest.mark.parametrize(
    ("playlist_name", "sharecode", "expected"),
    [
        ("CON", "KovaaKsOne", "CON_KovaaKsOne"),
        ("nul.txt", "KovaaKsTwo", "nul.txt_KovaaKsTwo"),
        ('<>:"/\\|?* .', "KovaaKsFallback", "KovaaKsFallback"),
        ("Bad\x00Name", "KovaaKsControl", "BadName"),
        ("Valid name. ", "KovaaKsValid", "Valid name"),
    ],
)
def test_sanitize_playlist_name_is_windows_complete(playlist_name, sharecode, expected):
    assert script.sanitize_playlist_name(playlist_name, sharecode) == expected


def test_scan_generated_ownership_is_junk_tolerant(tmp_path, caplog):
    (tmp_path / "manifest.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "code-less.json").write_text(
        json.dumps({"name": "No owner"}),
        encoding="utf-8",
    )
    (tmp_path / "Owned.json").write_text(
        json.dumps({"code": "KovaaKsOwner"}),
        encoding="utf-8",
    )
    caplog.set_level(logging.WARNING, logger=script.__name__)

    ownership, unowned = script.scan_generated_ownership(tmp_path)

    assert ownership == {"owned.json": "KovaaKsOwner"}
    assert unowned == {"broken.json", "code-less.json"}
    assert not any("manifest.json" in message for message in caplog.messages)
    assert any("broken.json" in message for message in caplog.messages)
    assert any("code-less.json" in message for message in caplog.messages)


def test_choose_generated_path_casefolds_ownership_and_suffixes(tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger=script.__name__)

    path = script.choose_generated_path(
        "foo",
        "KovaaKsLater",
        {"Foo.JSON".casefold(): "KovaaKsEarlier"},
        set(),
        tmp_path,
    )

    assert path == tmp_path / "foo_KovaaKsLater.json"
    assert "Filename collision" in caplog.text


def test_choose_generated_path_allows_unowned_overwrite(tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger=script.__name__)

    path = script.choose_generated_path(
        "Corrupt",
        "KovaaKsRepair",
        {},
        {"corrupt.json"},
        tmp_path,
    )

    assert path == tmp_path / "Corrupt.json"
    assert "Overwriting unowned generated file" in caplog.text


def test_generate_playlist_passes_retry_policy_and_writes_playlist(
    tmp_path, monkeypatch
):
    benchmark_calls = []
    playlist = EvxlPlaylist(
        playlist_name="Generated Playlist",
        playlist_code="KovaaKsGenerated",
        scenario_list=[EvxlPlaylistScenario(scenario_name="Test Scenario")],
    )
    monkeypatch.setattr(script, "get_evxl_playlist", lambda _code: playlist)

    def fake_benchmark(*args, **kwargs):
        benchmark_calls.append((args, kwargs))
        return _benchmark_response([100])

    monkeypatch.setattr(script, "get_benchmark_json", fake_benchmark)

    output = script.generate_playlist(
        "KovaaKsGenerated",
        EvxlDatabaseItem(
            kovaaksBenchmarkId=42,
            rankColors={"Bronze": "#111"},
        ),
        {},
        set(),
        tmp_path,
    )

    assert benchmark_calls == [
        (
            (42, None, True),
            {"attempts": 4, "backoff_seconds": (2, 4, 8)},
        )
    ]
    assert output == tmp_path / "Generated Playlist.json"
    generated = json.loads(output.read_text(encoding="utf-8"))
    assert generated["code"] == "KovaaKsGenerated"
    assert generated["scenarios"][0]["ranks"][0]["threshold"] == 100.0


def test_rank_mismatch_is_typed():
    response = script.BenchmarksAPIResponse.model_validate(
        _benchmark_response([100, 200])
    )

    with pytest.raises(
        script.BenchmarkDataMismatchError,
        match="Evxl has 1.*KovaaK's Benchmark API has 2",
    ):
        script.build_scenarios(
            response,
            EvxlDatabaseItem(
                kovaaksBenchmarkId=42,
                rankColors={"Bronze": "#111"},
            ),
        )


def test_run_importer_continues_after_item_failure(tmp_path, monkeypatch):
    calls = []
    sleeps = []
    database = {
        code: EvxlDatabaseItem(kovaaksBenchmarkId=index, rankColors={})
        for index, code in enumerate(["KovaaKsBad", "KovaaKsGoodOne", "KovaaKsGoodTwo"])
    }

    def fake_generate(sharecode, *_args):
        calls.append(sharecode)
        if sharecode == "KovaaKsBad":
            raise script.BenchmarkDataMismatchError("bad ladder")
        return tmp_path / f"{sharecode}.json"

    monkeypatch.setattr(script, "generate_playlist", fake_generate)
    monkeypatch.setattr(script.time, "sleep", sleeps.append)

    summary = script.run_importer(database, {}, generated_dir=tmp_path)

    assert calls == ["KovaaKsBad", "KovaaKsGoodOne", "KovaaKsGoodTwo"]
    assert summary.failed == {"KovaaKsBad": "bad ladder"}
    assert summary.generated == ["KovaaKsGoodOne", "KovaaKsGoodTwo"]
    assert summary.exit_code == 1
    assert sleeps == [0.5, 0.5]


def test_run_importer_stops_at_consecutive_failure_threshold(tmp_path, monkeypatch):
    calls = []
    database = {
        code: EvxlDatabaseItem(kovaaksBenchmarkId=index, rankColors={})
        for index, code in enumerate(["One", "Two", "Three"])
    }

    def fail(sharecode, *_args):
        calls.append(sharecode)
        raise requests.ReadTimeout("offline")

    monkeypatch.setattr(script, "generate_playlist", fail)
    monkeypatch.setattr(script.time, "sleep", lambda _seconds: None)

    summary = script.run_importer(
        database,
        {},
        max_consecutive_failures=2,
        generated_dir=tmp_path,
    )

    assert calls == ["One", "Two"]
    assert list(summary.failed) == ["One", "Two"]
    assert summary.exit_code == 1


def test_run_importer_only_and_limit_apply_to_generated_items(tmp_path, monkeypatch):
    calls = []
    database = {
        code: EvxlDatabaseItem(kovaaksBenchmarkId=index, rankColors={})
        for index, code in enumerate(["One", "Two", "Three"])
    }

    def fake_generate(sharecode, *_args):
        calls.append(sharecode)
        return tmp_path / f"{sharecode}.json"

    monkeypatch.setattr(script, "generate_playlist", fake_generate)
    monkeypatch.setattr(script.time, "sleep", lambda _seconds: None)

    summary = script.run_importer(
        database,
        {"Conflict": []},
        only=["Two", "Three"],
        limit=1,
        generated_dir=tmp_path,
    )

    assert calls == ["Two"]
    assert summary.generated == ["Two"]
    assert summary.conflicts == {}
    assert summary.exit_code == 0


def test_identical_duplicate_generates_once(tmp_path, monkeypatch):
    data_path = tmp_path / "benchmarks.json"
    duplicate = _difficulty(
        "KovaaKsDuplicate",
        10,
        {"Bronze": "#111"},
        "Easy",
    )
    _write_evxl_data(
        data_path,
        [
            {"benchmarkName": "One", "difficulties": [duplicate]},
            {"benchmarkName": "Two", "difficulties": [duplicate]},
        ],
    )
    database, conflicts = script.load_evxl_data(data_path)
    generated = []

    def fake_generate(sharecode, *_args):
        generated.append(sharecode)
        return tmp_path / f"{sharecode}.json"

    monkeypatch.setattr(script, "generate_playlist", fake_generate)

    summary = script.run_importer(database, conflicts, generated_dir=tmp_path)

    assert generated == ["KovaaKsDuplicate"]
    assert summary.generated == ["KovaaKsDuplicate"]
    assert summary.exit_code == 0


def test_conflicting_duplicate_generates_nothing(tmp_path, monkeypatch):
    data_path = tmp_path / "benchmarks.json"
    _write_evxl_data(
        data_path,
        [
            {
                "benchmarkName": "One",
                "difficulties": [
                    _difficulty(
                        "KovaaKsConflict",
                        10,
                        {"Bronze": "#111"},
                        "Easy",
                    )
                ],
            },
            {
                "benchmarkName": "Two",
                "difficulties": [
                    _difficulty(
                        "KovaaKsConflict",
                        20,
                        {"Silver": "#222"},
                        "Hard",
                    )
                ],
            },
        ],
    )
    database, conflicts = script.load_evxl_data(data_path)

    monkeypatch.setattr(
        script,
        "generate_playlist",
        lambda *_args: pytest.fail("conflicts must not generate"),
    )

    summary = script.run_importer(database, conflicts, generated_dir=tmp_path)

    assert summary.generated == []
    assert list(summary.conflicts) == ["KovaaKsConflict"]
    assert summary.exit_code == 1


def test_conflict_summary_lists_claimants_and_exits_nonzero(caplog):
    claimants = [
        script.DuplicateClaimant(
            benchmark="Benchmark",
            difficulty="Advanced",
            benchmark_id=99,
            rank_ladder=(("Master", "#abc"),),
        )
    ]
    summary = script.RunSummary(conflicts={"KovaaKsConflict": claimants})
    caplog.set_level(logging.INFO, logger=script.__name__)

    script.log_summary(summary)

    assert summary.exit_code == 1
    assert "conflicts=1" in caplog.text
    assert "benchmark='Benchmark' difficulty='Advanced' benchmark_id=99" in caplog.text


def test_parse_args_supports_repeated_only_and_positive_limits():
    args = script.parse_args(
        [
            "--only",
            "One",
            "--only",
            "Two",
            "--limit",
            "5",
            "--max-consecutive-failures",
            "4",
        ]
    )

    assert args.only == ["One", "Two"]
    assert args.limit == 5
    assert args.max_consecutive_failures == 4

    with pytest.raises(SystemExit):
        script.parse_args(["--limit", "0"])
