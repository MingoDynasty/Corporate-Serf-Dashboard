import json
import logging
from pathlib import Path

import pytest
import requests
from pydantic import ValidationError

from scripts.benchmark_importer import script
from scripts.benchmark_importer.models import (
    EvxlDatabaseItem,
    EvxlPlaylist,
    EvxlPlaylistScenario,
    ManifestEntry,
)
from source.utilities import atomic_write


def _write_evxl_data(path: Path, benchmarks: list[dict]) -> None:
    complete_benchmarks = []
    for benchmark in benchmarks:
        complete_benchmarks.append(
            {
                "rankCalculation": "basic",
                "abbreviation": "TEST",
                "color": "#000",
                "spreadsheetURL": "https://example.com",
                "dateAdded": "2026-07-03",
                **benchmark,
            }
        )
    path.write_text(json.dumps(complete_benchmarks), encoding="utf-8")


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
        "categories": [
            {
                "categoryName": "Clicking",
                "color": "#111",
                "subcategories": [
                    {
                        "subcategoryName": "Static",
                        "color": "#222",
                        "scenarioCount": 1,
                    }
                ],
            }
        ],
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


def _manifest_entry(
    *,
    file: str = "Generated Playlist.json",
    playlist_name: str = "Generated Playlist",
    benchmark_id: int = 42,
    rank_colors: list[tuple[str, str]] | None = None,
) -> ManifestEntry:
    return ManifestEntry(
        file=file,
        playlist_name=playlist_name,
        kovaaks_benchmark_id=benchmark_id,
        rank_colors=rank_colors or [("Bronze", "#111"), ("Silver", "#222")],
        generated_at="2026-07-03T12:00:00+00:00",
    )


def _write_generated_file(
    path: Path,
    sharecode: str,
    entry: ManifestEntry,
    *,
    provenance_sharecode: str | None = None,
) -> None:
    path.write_text(
        json.dumps(
            {
                "name": entry.playlist_name,
                "code": sharecode,
                "scenarios": [],
                "generated_from": {
                    "sharecode": provenance_sharecode or sharecode,
                    "kovaaks_benchmark_id": entry.kovaaks_benchmark_id,
                    "rank_colors": [list(pair) for pair in entry.rank_colors],
                    "generated_at": entry.generated_at,
                    "generator": "benchmark_importer",
                },
            }
        ),
        encoding="utf-8",
    )


def _evxl_payload(*difficulties: dict) -> list[dict]:
    return [
        {
            "benchmarkName": "Test Benchmark",
            "rankCalculation": "basic",
            "abbreviation": "TEST",
            "color": "#000",
            "spreadsheetURL": "https://example.com",
            "dateAdded": "2026-07-03",
            "difficulties": list(difficulties),
        }
    ]


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
        ("nul.txt", "KovaaKsTwo", "nul_KovaaKsTwo.txt"),
        (
            "COM1.profile.backup",
            "KovaaKsThree",
            "COM1_KovaaKsThree.profile.backup",
        ),
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


def test_build_scenarios_strips_padded_scenario_names():
    # KovaaK's occasionally returns padded scenario keys; CSV run import strips
    # the `Scenario:` value, so unstripped playlist names never match lookups.
    payload = _benchmark_response([100])
    payload["categories"]["Clicking"]["scenarios"] = {
        " 6 Sphere Hipfire 150% Size ": {
            "score": 0,
            "leaderboard_rank": None,
            "scenario_rank": 0,
            "rank_maxes": [100],
            "leaderboard_id": 1,
        }
    }
    response = script.BenchmarksAPIResponse.model_validate(payload)

    scenarios = script.build_scenarios(
        response,
        EvxlDatabaseItem(kovaaksBenchmarkId=42, rankColors={"Bronze": "#111"}),
    )

    assert [scenario.name for scenario in scenarios] == ["6 Sphere Hipfire 150% Size"]


def test_run_importer_continues_after_item_failure(tmp_path, monkeypatch):
    calls = []
    sleeps = []
    database = {
        code: EvxlDatabaseItem(kovaaksBenchmarkId=index, rankColors={})
        for index, code in enumerate(["KovaaKsBad", "KovaaKsGoodOne", "KovaaKsGoodTwo"])
    }

    def fake_generate(sharecode, *_args, **_kwargs):
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

    def fail(sharecode, *_args, **_kwargs):
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

    def fake_generate(sharecode, *_args, **_kwargs):
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


def test_run_importer_missing_only_sharecodes_are_failures(tmp_path, monkeypatch):
    database = {
        "Present": EvxlDatabaseItem(kovaaksBenchmarkId=1, rankColors={}),
    }
    generated = []

    def fake_generate(sharecode, *_args, **_kwargs):
        generated.append(sharecode)
        return tmp_path / f"{sharecode}.json"

    monkeypatch.setattr(script, "generate_playlist", fake_generate)

    summary = script.run_importer(
        database,
        {},
        only=["Missing", "Present"],
        generated_dir=tmp_path,
    )

    assert generated == ["Present"]
    assert summary.generated == ["Present"]
    assert summary.failed == {
        "Missing": "Requested sharecode was not found in Evxl data"
    }
    assert summary.exit_code == 1


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

    def fake_generate(sharecode, *_args, **_kwargs):
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


def test_manifest_skip_requires_matching_ordered_provenance_and_playlist(tmp_path):
    sharecode = "KovaaKsGenerated"
    item = EvxlDatabaseItem(
        kovaaksBenchmarkId=42,
        rankColors={"Bronze": "#111", "Silver": "#222"},
    )
    entry = _manifest_entry()
    _write_generated_file(tmp_path / entry.file, sharecode, entry)

    assert script.should_skip_generation(sharecode, item, entry, tmp_path)
    assert not script.should_skip_generation(
        sharecode,
        EvxlDatabaseItem(
            kovaaksBenchmarkId=43,
            rankColors={"Bronze": "#111", "Silver": "#222"},
        ),
        entry,
        tmp_path,
    )
    assert not script.should_skip_generation(
        sharecode,
        EvxlDatabaseItem(
            kovaaksBenchmarkId=42,
            rankColors={"Silver": "#222", "Bronze": "#111"},
        ),
        entry,
        tmp_path,
    )
    assert not script.should_skip_generation(
        sharecode,
        item,
        entry,
        tmp_path,
        force=True,
    )


@pytest.mark.parametrize("failure", ["missing", "malformed", "wrong_provenance"])
def test_manifest_skip_regenerates_for_broken_output(tmp_path, failure):
    sharecode = "KovaaKsGenerated"
    item = EvxlDatabaseItem(kovaaksBenchmarkId=42, rankColors={"Bronze": "#111"})
    entry = _manifest_entry(rank_colors=[("Bronze", "#111")])
    path = tmp_path / entry.file
    if failure == "malformed":
        path.write_text("{broken", encoding="utf-8")
    elif failure == "wrong_provenance":
        _write_generated_file(
            path,
            sharecode,
            entry,
            provenance_sharecode="KovaaKsSomeoneElse",
        )

    assert not script.should_skip_generation(sharecode, item, entry, tmp_path)


def test_manifest_path_outside_generated_is_never_read_or_deleted(
    tmp_path, monkeypatch
):
    generated_dir = tmp_path / "generated"
    generated_dir.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("do not touch", encoding="utf-8")
    entry = _manifest_entry(file="../outside.json")
    item = EvxlDatabaseItem(kovaaksBenchmarkId=42, rankColors={"Bronze": "#111"})

    assert not script.should_skip_generation(
        "KovaaKsGenerated", item, entry, generated_dir
    )

    playlist = EvxlPlaylist(
        playlist_name="Renamed",
        playlist_code="KovaaKsGenerated",
        scenario_list=[],
    )
    monkeypatch.setattr(script, "get_evxl_playlist", lambda _code: playlist)
    monkeypatch.setattr(
        script,
        "get_benchmark_json",
        lambda *_args, **_kwargs: _benchmark_response([100]),
    )
    manifest = {"KovaaKsGenerated": entry}
    script.generate_playlist(
        "KovaaKsGenerated",
        item,
        {},
        set(),
        generated_dir,
        manifest=manifest,
    )

    assert outside.read_text(encoding="utf-8") == "do not touch"


def test_generation_writes_output_before_manifest_and_deletes_renamed_file(
    tmp_path, monkeypatch
):
    old_path = tmp_path / "Old Name.json"
    old_path.write_text("old", encoding="utf-8")
    old_entry = _manifest_entry(
        file=old_path.name,
        playlist_name="Old Name",
        rank_colors=[("Bronze", "#111")],
    )
    manifest = {"KovaaKsGenerated": old_entry}
    playlist = EvxlPlaylist(
        playlist_name="New Name",
        playlist_code="KovaaKsGenerated",
        scenario_list=[],
    )
    monkeypatch.setattr(script, "get_evxl_playlist", lambda _code: playlist)
    monkeypatch.setattr(
        script,
        "get_benchmark_json",
        lambda *_args, **_kwargs: _benchmark_response([100]),
    )
    writes = []
    original_atomic_write = script._atomic_write_json

    def record_write(path, payload):
        writes.append(path.name)
        original_atomic_write(path, payload)

    monkeypatch.setattr(script, "_atomic_write_json", record_write)

    output = script.generate_playlist(
        "KovaaKsGenerated",
        EvxlDatabaseItem(kovaaksBenchmarkId=42, rankColors={"Bronze": "#111"}),
        {"old name.json": "KovaaKsGenerated"},
        set(),
        tmp_path,
        manifest=manifest,
    )

    assert writes == ["New Name.json", "manifest.json"]
    assert output.exists()
    assert not old_path.exists()
    assert manifest["KovaaKsGenerated"].file == "New Name.json"
    raw_output = json.loads(output.read_text(encoding="utf-8"))
    assert raw_output["generated_from"]["rank_colors"] == [["Bronze", "#111"]]


def test_manifest_write_uses_atomic_replace(tmp_path, monkeypatch):
    path = tmp_path / "manifest.json"
    replacements = []
    original_replace = atomic_write.os.replace

    def record_replace(source, destination):
        replacements.append((Path(source), Path(destination)))
        original_replace(source, destination)

    monkeypatch.setattr(atomic_write.os, "replace", record_replace)
    script.write_manifest({"KovaaKsGenerated": _manifest_entry()}, path)

    assert len(replacements) == 1
    assert replacements[0][1] == path
    assert replacements[0][0].parent == path.parent
    assert script.load_manifest(path)["KovaaKsGenerated"].rank_colors == [
        ("Bronze", "#111"),
        ("Silver", "#222"),
    ]


def test_atomic_write_retries_replace_on_transient_permission_error(
    tmp_path, monkeypatch, caplog
):
    caplog.set_level(logging.WARNING, logger=script.__name__)
    path = tmp_path / "out.json"
    original_replace = atomic_write.os.replace
    attempts = {"count": 0}

    def flaky_replace(source, destination):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise PermissionError("antivirus is holding the destination open")
        original_replace(source, destination)

    monkeypatch.setattr(atomic_write.os, "replace", flaky_replace)
    monkeypatch.setattr(atomic_write.time, "sleep", lambda _seconds: None)

    script._atomic_write_json(path, {"ok": True})

    assert attempts["count"] == 2
    assert json.loads(path.read_text(encoding="utf-8")) == {"ok": True}
    assert any("Retrying replace" in message for message in caplog.messages)


def test_atomic_write_reraises_and_cleans_up_after_exhausting_retries(
    tmp_path, monkeypatch
):
    path = tmp_path / "out.json"

    def always_locked(source, destination):
        raise PermissionError("destination stays locked")

    monkeypatch.setattr(atomic_write.os, "replace", always_locked)
    monkeypatch.setattr(atomic_write.time, "sleep", lambda _seconds: None)

    with pytest.raises(PermissionError):
        script._atomic_write_json(path, {"ok": True})

    assert not path.exists()
    assert list(tmp_path.glob(f".{path.name}.*.tmp")) == []


def test_load_manifest_treats_missing_and_malformed_as_empty(tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger=script.__name__)
    path = tmp_path / "manifest.json"

    assert script.load_manifest(path) == {}
    path.write_text("{broken", encoding="utf-8")
    assert script.load_manifest(path) == {}
    assert sum("missing or malformed" in message for message in caplog.messages) == 2


def test_run_importer_skips_intact_manifest_entry(tmp_path, monkeypatch):
    sharecode = "KovaaKsGenerated"
    entry = _manifest_entry(rank_colors=[("Bronze", "#111")])
    _write_generated_file(tmp_path / entry.file, sharecode, entry)
    script.write_manifest({sharecode: entry}, tmp_path / "manifest.json")
    monkeypatch.setattr(
        script,
        "generate_playlist",
        lambda *_args, **_kwargs: pytest.fail("intact output must be skipped"),
    )

    summary = script.run_importer(
        {
            sharecode: EvxlDatabaseItem(
                kovaaksBenchmarkId=42,
                rankColors={"Bronze": "#111"},
            )
        },
        {},
        generated_dir=tmp_path,
    )

    assert summary.skipped == [sharecode]
    assert summary.generated == []


def test_force_bypasses_manifest_and_benchmark_cache(tmp_path, monkeypatch):
    captured = {}

    def fake_generate(sharecode, *_args, **kwargs):
        captured[sharecode] = kwargs
        return tmp_path / f"{sharecode}.json"

    monkeypatch.setattr(script, "generate_playlist", fake_generate)

    summary = script.run_importer(
        {
            "KovaaKsGenerated": EvxlDatabaseItem(
                kovaaksBenchmarkId=42,
                rankColors={},
            )
        },
        {},
        generated_dir=tmp_path,
        force=True,
    )

    assert summary.generated == ["KovaaKsGenerated"]
    assert captured["KovaaKsGenerated"]["use_cache"] is False


def test_live_evxl_mixed_candidate_is_rejected_in_full(tmp_path, monkeypatch):
    path = tmp_path / "benchmarks.json"
    current = _evxl_payload(
        _difficulty("Keep", 1, {"Bronze": "#111"}, "Easy"),
        _difficulty("Remove", 2, {"Bronze": "#111"}, "Hard"),
    )
    candidate = _evxl_payload(
        _difficulty("Keep", 1, {"Bronze": "#111"}, "Easy"),
        _difficulty("Add", 3, {"Bronze": "#111"}, "Normal"),
    )
    _write_evxl_data(path, current)

    class Response:
        @staticmethod
        def json():
            return candidate

    monkeypatch.setattr(script, "_get_with_retry", lambda *_args, **_kwargs: Response())

    assert not script.refresh_evxl_snapshot(path)
    assert json.loads(path.read_text(encoding="utf-8")) == current


def test_live_evxl_accept_removals_replaces_whole_candidate_atomically(
    tmp_path, monkeypatch
):
    path = tmp_path / "benchmarks.json"
    current = _evxl_payload(
        _difficulty("Keep", 1, {"Bronze": "#111"}, "Easy"),
        _difficulty("Remove", 2, {"Bronze": "#111"}, "Hard"),
    )
    candidate = _evxl_payload(
        _difficulty("Keep", 1, {"Bronze": "#111"}, "Easy"),
        _difficulty("Add", 3, {"Bronze": "#111"}, "Normal"),
    )
    _write_evxl_data(path, current)

    class Response:
        @staticmethod
        def json():
            return candidate

    monkeypatch.setattr(script, "_get_with_retry", lambda *_args, **_kwargs: Response())
    replacements = []
    original_replace = atomic_write.os.replace

    def record_replace(source, destination):
        replacements.append((Path(source), Path(destination)))
        original_replace(source, destination)

    monkeypatch.setattr(atomic_write.os, "replace", record_replace)

    assert script.refresh_evxl_snapshot(path, accept_removals=True)
    assert json.loads(path.read_text(encoding="utf-8")) == candidate
    assert len(replacements) == 1
    assert replacements[0][1] == path


@pytest.mark.parametrize("candidate", [{}, {"error": "upstream"}])
def test_invalid_live_evxl_data_preserves_snapshot(tmp_path, monkeypatch, candidate):
    path = tmp_path / "benchmarks.json"
    current = _evxl_payload(
        _difficulty("Keep", 1, {"Bronze": "#111"}, "Easy"),
    )
    _write_evxl_data(path, current)

    class Response:
        @staticmethod
        def json():
            return candidate

    monkeypatch.setattr(script, "_get_with_retry", lambda *_args, **_kwargs: Response())

    assert not script.refresh_evxl_snapshot(path)
    assert json.loads(path.read_text(encoding="utf-8")) == current


def test_partial_live_evxl_entry_preserves_snapshot(tmp_path, monkeypatch):
    path = tmp_path / "benchmarks.json"
    current = _evxl_payload(
        _difficulty("Keep", 1, {"Bronze": "#111"}, "Easy"),
    )
    candidate = json.loads(json.dumps(current))
    del candidate[0]["difficulties"][0]["categories"]
    _write_evxl_data(path, current)

    class Response:
        @staticmethod
        def json():
            return candidate

    monkeypatch.setattr(script, "_get_with_retry", lambda *_args, **_kwargs: Response())

    assert not script.refresh_evxl_snapshot(path)
    assert json.loads(path.read_text(encoding="utf-8")) == current


def test_live_rank_color_reorder_refreshes_and_invalidates_manifest(
    tmp_path, monkeypatch
):
    snapshot = tmp_path / "benchmarks.json"
    current = _evxl_payload(
        _difficulty(
            "KovaaKsGenerated",
            42,
            {"Bronze": "#111", "Silver": "#222"},
            "Easy",
        )
    )
    candidate = _evxl_payload(
        _difficulty(
            "KovaaKsGenerated",
            42,
            {"Silver": "#222", "Bronze": "#111"},
            "Easy",
        )
    )
    _write_evxl_data(snapshot, current)

    class Response:
        @staticmethod
        def json():
            return candidate

    monkeypatch.setattr(script, "_get_with_retry", lambda *_args, **_kwargs: Response())
    assert script.refresh_evxl_snapshot(snapshot)

    entry = _manifest_entry()
    _write_generated_file(
        tmp_path / entry.file,
        "KovaaKsGenerated",
        entry,
    )
    script.write_manifest({"KovaaKsGenerated": entry}, tmp_path / "manifest.json")
    database, conflicts = script.load_evxl_data(snapshot)
    generated = []

    def fake_generate(sharecode, *_args, **_kwargs):
        generated.append(sharecode)
        return tmp_path / f"{sharecode}.json"

    monkeypatch.setattr(script, "generate_playlist", fake_generate)
    summary = script.run_importer(database, conflicts, generated_dir=tmp_path)

    assert generated == ["KovaaKsGenerated"]
    assert summary.generated == ["KovaaKsGenerated"]


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
            "--offline",
            "--force",
            "--accept-removals",
        ]
    )

    assert args.only == ["One", "Two"]
    assert args.limit == 5
    assert args.max_consecutive_failures == 4
    assert args.offline
    assert args.force
    assert args.accept_removals

    with pytest.raises(SystemExit):
        script.parse_args(["--limit", "0"])


def _http_error(status_code: int) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status_code
    return requests.HTTPError(f"{status_code} error", response=response)


def _validation_error() -> ValidationError:
    try:
        ManifestEntry.model_validate({})
    except ValidationError as exc:
        return exc
    raise AssertionError("expected a ValidationError")


def _read_ledger(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "failures.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "exc",
    [
        script.BenchmarkDataMismatchError("bad ladder"),
        _validation_error(),
        _http_error(400),
        _http_error(404),
    ],
)
def test_deterministic_failures_are_classified(exc):
    assert script._is_deterministic_failure(exc)


@pytest.mark.parametrize(
    "exc",
    [
        _http_error(429),
        _http_error(503),
        requests.ConnectionError("no route"),
        requests.ReadTimeout("too slow"),
        requests.HTTPError("no response attached"),
    ],
)
def test_transient_failures_are_classified(exc):
    assert not script._is_deterministic_failure(exc)


def test_consecutive_deterministic_failures_do_not_abort_the_sweep(
    tmp_path, monkeypatch
):
    calls = []
    database = {
        code: EvxlDatabaseItem(kovaaksBenchmarkId=index, rankColors={})
        for index, code in enumerate(["One", "Two", "Three", "Four"])
    }

    def fake_generate(sharecode, *_args, **_kwargs):
        calls.append(sharecode)
        if sharecode == "Four":
            return tmp_path / "Four.json"
        raise script.BenchmarkDataMismatchError(f"bad ladder for {sharecode}")

    monkeypatch.setattr(script, "generate_playlist", fake_generate)
    monkeypatch.setattr(script.time, "sleep", lambda _seconds: None)

    summary = script.run_importer(
        database,
        {},
        max_consecutive_failures=3,
        generated_dir=tmp_path,
    )

    assert calls == ["One", "Two", "Three", "Four"]
    assert list(summary.failed) == ["One", "Two", "Three"]
    assert summary.generated == ["Four"]
    # Fresh failures report as failures, not as known-bad skips.
    assert summary.known_bad == {}
    assert sorted(_read_ledger(tmp_path)) == ["One", "Three", "Two"]
    assert _read_ledger(tmp_path)["One"]["error"] == "bad ladder for One"


def test_second_run_skips_ledger_codes_without_touching_the_network(
    tmp_path, monkeypatch
):
    database = {"Bad": EvxlDatabaseItem(kovaaksBenchmarkId=1, rankColors={})}

    def fail(_sharecode, *_args, **_kwargs):
        raise script.BenchmarkDataMismatchError("bad ladder")

    monkeypatch.setattr(script, "generate_playlist", fail)
    monkeypatch.setattr(script.time, "sleep", lambda _seconds: None)
    first = script.run_importer(database, {}, generated_dir=tmp_path)

    assert list(first.failed) == ["Bad"]

    monkeypatch.setattr(
        script,
        "generate_playlist",
        lambda *_args, **_kwargs: pytest.fail("known-bad codes must not be fetched"),
    )
    second = script.run_importer(database, {}, generated_dir=tmp_path)

    assert second.known_bad == {"Bad": "bad ladder"}
    assert second.failed == {}
    assert second.generated == []
    # Known-bad skips stay informational.
    assert second.exit_code == 0


def test_only_retries_a_ledger_code_and_success_clears_the_entry(tmp_path, monkeypatch):
    database = {"Bad": EvxlDatabaseItem(kovaaksBenchmarkId=1, rankColors={})}
    script.write_failure_ledger(
        {
            "Bad": script.FailureEntry(
                error="bad ladder",
                recorded_at="2026-07-03T12:00:00+00:00",
            )
        },
        tmp_path / "failures.json",
    )
    calls = []

    def fake_generate(sharecode, *_args, **_kwargs):
        calls.append(sharecode)
        return tmp_path / f"{sharecode}.json"

    monkeypatch.setattr(script, "generate_playlist", fake_generate)
    monkeypatch.setattr(script.time, "sleep", lambda _seconds: None)

    summary = script.run_importer(
        database,
        {},
        only=["Bad"],
        generated_dir=tmp_path,
    )

    assert calls == ["Bad"]
    assert summary.generated == ["Bad"]
    assert summary.known_bad == {}
    assert _read_ledger(tmp_path) == {}


def test_repeat_deterministic_failure_refreshes_the_ledger_entry(tmp_path, monkeypatch):
    database = {"Bad": EvxlDatabaseItem(kovaaksBenchmarkId=1, rankColors={})}
    script.write_failure_ledger(
        {
            "Bad": script.FailureEntry(
                error="stale reason",
                recorded_at="2026-07-03T12:00:00+00:00",
            )
        },
        tmp_path / "failures.json",
    )

    def fail(_sharecode, *_args, **_kwargs):
        raise script.BenchmarkDataMismatchError("fresh reason")

    monkeypatch.setattr(script, "generate_playlist", fail)
    monkeypatch.setattr(script.time, "sleep", lambda _seconds: None)

    summary = script.run_importer(
        database,
        {},
        only=["Bad"],
        generated_dir=tmp_path,
    )

    assert summary.failed == {"Bad": "fresh reason"}
    entry = _read_ledger(tmp_path)["Bad"]
    assert entry["error"] == "fresh reason"
    assert entry["recorded_at"] != "2026-07-03T12:00:00+00:00"


def test_force_attempts_ledger_codes(tmp_path, monkeypatch):
    database = {"Bad": EvxlDatabaseItem(kovaaksBenchmarkId=1, rankColors={})}
    script.write_failure_ledger(
        {
            "Bad": script.FailureEntry(
                error="bad ladder",
                recorded_at="2026-07-03T12:00:00+00:00",
            )
        },
        tmp_path / "failures.json",
    )
    calls = []

    def fake_generate(sharecode, *_args, **_kwargs):
        calls.append(sharecode)
        return tmp_path / f"{sharecode}.json"

    monkeypatch.setattr(script, "generate_playlist", fake_generate)
    monkeypatch.setattr(script.time, "sleep", lambda _seconds: None)

    summary = script.run_importer(database, {}, generated_dir=tmp_path, force=True)

    assert calls == ["Bad"]
    assert summary.generated == ["Bad"]
    assert _read_ledger(tmp_path) == {}


def test_transient_failures_are_not_recorded(tmp_path, monkeypatch):
    database = {
        code: EvxlDatabaseItem(kovaaksBenchmarkId=index, rankColors={})
        for index, code in enumerate(["One", "Two"])
    }

    def fail(_sharecode, *_args, **_kwargs):
        raise requests.ReadTimeout("offline")

    monkeypatch.setattr(script, "generate_playlist", fail)
    monkeypatch.setattr(script.time, "sleep", lambda _seconds: None)

    summary = script.run_importer(
        database,
        {},
        max_consecutive_failures=3,
        generated_dir=tmp_path,
    )

    assert list(summary.failed) == ["One", "Two"]
    assert not (tmp_path / "failures.json").exists()


def test_load_failure_ledger_treats_missing_and_malformed_as_empty(tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger=script.__name__)
    path = tmp_path / "failures.json"

    assert script.load_failure_ledger(path) == {}
    path.write_text("{broken", encoding="utf-8")
    assert script.load_failure_ledger(path) == {}
    path.write_text(json.dumps({"Bad": {"error": "no timestamp"}}), encoding="utf-8")
    assert script.load_failure_ledger(path) == {}
    assert sum("missing or malformed" in message for message in caplog.messages) == 3


def test_importer_state_files_are_not_scanned_as_playlists(tmp_path, caplog):
    caplog.set_level(logging.WARNING, logger=script.__name__)
    script.write_manifest({"Code": _manifest_entry()}, tmp_path / "manifest.json")
    script.write_failure_ledger(
        {
            "Code": script.FailureEntry(
                error="bad ladder",
                recorded_at="2026-07-03T12:00:00+00:00",
            )
        },
        tmp_path / "failures.json",
    )

    ownership, unowned = script.scan_generated_ownership(tmp_path)

    assert ownership == {}
    assert unowned == set()
    assert caplog.messages == []


@pytest.mark.parametrize("reserved", ["manifest", "failures"])
def test_playlist_named_after_importer_state_does_not_overwrite_it(reserved, tmp_path):
    path = script.choose_generated_path(reserved, "KovaaKsCode", {}, set(), tmp_path)

    assert path == tmp_path / f"{reserved}_KovaaKsCode.json"


def test_ledger_survives_a_sweep_that_scans_the_generated_directory(
    tmp_path, monkeypatch
):
    database = {"Bad": EvxlDatabaseItem(kovaaksBenchmarkId=1, rankColors={})}

    def fail(_sharecode, *_args, **_kwargs):
        raise script.BenchmarkDataMismatchError("bad ladder")

    monkeypatch.setattr(script, "generate_playlist", fail)
    monkeypatch.setattr(script.time, "sleep", lambda _seconds: None)
    script.run_importer(database, {}, generated_dir=tmp_path)

    # A later sweep must still read the ledger it wrote.
    second = script.run_importer(database, {}, generated_dir=tmp_path)

    assert second.known_bad == {"Bad": "bad ladder"}


def _record_known_bad(tmp_path, item, monkeypatch, error="bad ladder"):
    """Record a real deterministic failure so the ledger carries its signature."""

    def fail(_sharecode, *_args, **_kwargs):
        raise script.BenchmarkDataMismatchError(error)

    monkeypatch.setattr(script, "generate_playlist", fail)
    monkeypatch.setattr(script.time, "sleep", lambda _seconds: None)
    script.run_importer({"Bad": item}, {}, generated_dir=tmp_path)


def test_ledger_records_the_evxl_signature_it_failed_against(tmp_path, monkeypatch):
    item = EvxlDatabaseItem(kovaaksBenchmarkId=2412, rankColors={"Bronze": "#111"})
    _record_known_bad(tmp_path, item, monkeypatch)

    entry = _read_ledger(tmp_path)["Bad"]

    assert entry["kovaaks_benchmark_id"] == 2412
    assert entry["rank_colors"] == [["Bronze", "#111"]]


@pytest.mark.parametrize(
    "repaired",
    [
        EvxlDatabaseItem(
            kovaaksBenchmarkId=2412,
            rankColors={"Bronze": "#111", "Silver": "#222"},
        ),
        EvxlDatabaseItem(kovaaksBenchmarkId=9999, rankColors={"Bronze": "#111"}),
    ],
    ids=["rank-ladder-changed", "benchmark-id-changed"],
)
def test_upstream_metadata_change_retries_a_known_bad_code(
    repaired, tmp_path, monkeypatch
):
    item = EvxlDatabaseItem(kovaaksBenchmarkId=2412, rankColors={"Bronze": "#111"})
    _record_known_bad(tmp_path, item, monkeypatch)
    calls = []

    def fake_generate(sharecode, *_args, **_kwargs):
        calls.append(sharecode)
        return tmp_path / f"{sharecode}.json"

    monkeypatch.setattr(script, "generate_playlist", fake_generate)

    summary = script.run_importer({"Bad": repaired}, {}, generated_dir=tmp_path)

    assert calls == ["Bad"]
    assert summary.generated == ["Bad"]
    assert summary.known_bad == {}
    assert _read_ledger(tmp_path) == {}


def test_unchanged_metadata_still_skips_a_known_bad_code(tmp_path, monkeypatch):
    item = EvxlDatabaseItem(kovaaksBenchmarkId=2412, rankColors={"Bronze": "#111"})
    _record_known_bad(tmp_path, item, monkeypatch)
    monkeypatch.setattr(
        script,
        "generate_playlist",
        lambda *_args, **_kwargs: pytest.fail("unchanged metadata must be skipped"),
    )

    summary = script.run_importer({"Bad": item}, {}, generated_dir=tmp_path)

    assert summary.known_bad == {"Bad": "bad ladder"}


def test_ledger_entry_without_a_signature_is_retried(tmp_path, monkeypatch):
    # Entries written before the signature existed must not skip forever.
    (tmp_path / "failures.json").write_text(
        json.dumps(
            {"Bad": {"error": "bad ladder", "recorded_at": "2026-07-03T12:00:00+00:00"}}
        ),
        encoding="utf-8",
    )
    calls = []

    def fake_generate(sharecode, *_args, **_kwargs):
        calls.append(sharecode)
        return tmp_path / f"{sharecode}.json"

    monkeypatch.setattr(script, "generate_playlist", fake_generate)
    monkeypatch.setattr(script.time, "sleep", lambda _seconds: None)

    summary = script.run_importer(
        {"Bad": EvxlDatabaseItem(kovaaksBenchmarkId=1, rankColors={})},
        {},
        generated_dir=tmp_path,
    )

    assert calls == ["Bad"]
    assert summary.generated == ["Bad"]
