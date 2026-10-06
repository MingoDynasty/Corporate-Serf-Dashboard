import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from source.kovaaks import evxl_snapshot
from source.kovaaks.evxl_links import evxl_benchmark_url

STEAM_ID = "76561198000000000"

SNAPSHOT = [
    {
        "benchmarkName": "Viscose Benchmarks S2",
        # Fields the lookup does not read must not stop it loading.
        "rankCalculation": "basic",
        "difficulties": [
            {
                "difficultyName": "Medium",
                "kovaaksBenchmarkId": 2336,
                "sharecode": "KovaaKsPeakingNarrowImpact",
            },
            {"difficultyName": "Hard", "sharecode": "KovaaKsPlunderingOliveClutch"},
        ],
    },
    {
        "benchmarkName": "Sparky (Voltaic) S1",
        "difficulties": [{"difficultyName": "All", "sharecode": "KovaaKsParensCode"}],
    },
    {
        "benchmarkName": "773TS Main β3.0",
        "difficulties": [{"difficultyName": "Normal", "sharecode": "KovaaKsBetaCode"}],
    },
    {
        "benchmarkName": "xyz Comps",
        "difficulties": [
            {"difficultyName": "#1 Clicking", "sharecode": "KovaaKsHashCode"}
        ],
    },
    {
        "benchmarkName": "NRS 360 / Macro Benchmarks",
        "difficulties": [{"difficultyName": "Easy", "sharecode": "KovaaKsSlashCode"}],
    },
    {
        "benchmarkName": "Aimerz+ S1",
        "difficulties": [{"difficultyName": "Easy", "sharecode": "KovaaKsPlusCode"}],
    },
    {
        "benchmarkName": "m0narcS & hizku Tracking",
        "difficulties": [{"difficultyName": "Easy", "sharecode": "KovaaKsAmpCode"}],
    },
    {
        "benchmarkName": "SCP: Roleplay Benchmark",
        "difficulties": [{"difficultyName": "All", "sharecode": "KovaaKsColonCode"}],
    },
    {
        "benchmarkName": "Revosect S4",
        "difficulties": [
            {"difficultyName": "Easy", "sharecode": "KovaaKsExitFraggingWideCamp"}
        ],
    },
    {
        "benchmarkName": "Listed Again",
        "difficulties": [
            {"difficultyName": "Later", "sharecode": "KovaaKsPeakingNarrowImpact"}
        ],
    },
]


@pytest.fixture(autouse=True)
def fresh_snapshot_memo() -> Iterator[None]:
    """Keep one test's snapshot from answering for the next."""
    evxl_snapshot.evxl_entries_by_code.cache_clear()
    yield
    evxl_snapshot.evxl_entries_by_code.cache_clear()


@pytest.fixture
def snapshot_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the lookup at a snapshot file holding ``SNAPSHOT``."""
    path = tmp_path / "benchmarks.json"
    path.write_text(json.dumps(SNAPSHOT), encoding="utf-8")
    monkeypatch.setattr(evxl_snapshot, "EVXL_BENCHMARKS_SNAPSHOT_PATH", path)
    return path


def test_a_steam_id_links_the_players_sheet_for_the_difficulty(snapshot_path):
    assert evxl_benchmark_url("KovaaKsPeakingNarrowImpact", STEAM_ID) == (
        f"https://evxl.app/u/{STEAM_ID}/Viscose%20Benchmarks%20S2/Medium"
    )
    assert evxl_benchmark_url("KovaaKsPlunderingOliveClutch", STEAM_ID) == (
        f"https://evxl.app/u/{STEAM_ID}/Viscose%20Benchmarks%20S2/Hard"
    )


@pytest.mark.parametrize("steam_id", [None, ""])
def test_no_steam_id_links_the_page_that_asks_for_a_profile(snapshot_path, steam_id):
    assert evxl_benchmark_url("KovaaKsPeakingNarrowImpact", steam_id) == (
        "https://evxl.app/benchmarks/Viscose%20Benchmarks%20S2"
    )


@pytest.mark.parametrize(
    ("playlist_code", "expected_path"),
    [
        ("KovaaKsParensCode", "Sparky%20%28Voltaic%29%20S1/All"),
        ("KovaaKsBetaCode", "773TS%20Main%20%CE%B23.0/Normal"),
        ("KovaaKsHashCode", "xyz%20Comps/%231%20Clicking"),
        # A bare slash would split the name into two path segments.
        ("KovaaKsSlashCode", "NRS%20360%20%2F%20Macro%20Benchmarks/Easy"),
        ("KovaaKsPlusCode", "Aimerz%2B%20S1/Easy"),
        ("KovaaKsAmpCode", "m0narcS%20%26%20hizku%20Tracking/Easy"),
        ("KovaaKsColonCode", "SCP%3A%20Roleplay%20Benchmark/All"),
    ],
)
def test_the_sheet_address_encodes_each_name_as_one_segment(
    snapshot_path, playlist_code, expected_path
):
    assert evxl_benchmark_url(playlist_code, STEAM_ID) == (
        f"https://evxl.app/u/{STEAM_ID}/{expected_path}"
    )


@pytest.mark.parametrize(
    ("playlist_code", "expected_url"),
    [
        (
            "KovaaKsParensCode",
            "https://evxl.app/benchmarks/Sparky%20%28Voltaic%29%20S1",
        ),
        ("KovaaKsBetaCode", "https://evxl.app/benchmarks/773TS%20Main%20%CE%B23.0"),
        # Only the benchmark name is in this address, so the difficulty's
        # ``#`` does not matter.
        ("KovaaKsHashCode", "https://evxl.app/benchmarks/xyz%20Comps"),
    ],
)
def test_the_profile_less_page_takes_names_evxl_can_match(
    snapshot_path, playlist_code, expected_url
):
    assert evxl_benchmark_url(playlist_code, None) == expected_url


@pytest.mark.parametrize(
    "playlist_code",
    ["KovaaKsSlashCode", "KovaaKsPlusCode", "KovaaKsAmpCode", "KovaaKsColonCode"],
)
def test_no_steam_id_gives_no_link_for_a_name_evxl_would_404(
    snapshot_path, playlist_code
):
    assert evxl_benchmark_url(playlist_code, None) is None


def test_a_code_evxl_does_not_list_has_no_page(snapshot_path):
    assert evxl_benchmark_url("KovaaKsNotABenchmark", STEAM_ID) is None
    assert evxl_benchmark_url("KovaaKsNotABenchmark", None) is None


def test_a_code_matches_whatever_its_letter_case(snapshot_path):
    # The bundled file's code and the snapshot's have differed by case.
    assert evxl_benchmark_url("KovaaKsExitfraggingWideCamp", STEAM_ID) == (
        f"https://evxl.app/u/{STEAM_ID}/Revosect%20S4/Easy"
    )


def test_a_code_listed_twice_keeps_its_first_listing(snapshot_path):
    url = evxl_benchmark_url("KovaaKsPeakingNarrowImpact", STEAM_ID)

    assert url is not None
    assert "Listed%20Again" not in url


def test_a_missing_snapshot_gives_no_links_and_says_so_once(
    monkeypatch, tmp_path, caplog
):
    path = tmp_path / "absent.json"
    monkeypatch.setattr(evxl_snapshot, "EVXL_BENCHMARKS_SNAPSHOT_PATH", path)

    with caplog.at_level(logging.WARNING, logger=evxl_snapshot.__name__):
        assert evxl_benchmark_url("KovaaKsPeakingNarrowImpact", STEAM_ID) is None
        assert evxl_benchmark_url("KovaaKsPeakingNarrowImpact", None) is None

    (record,) = caplog.records
    assert f'Failed to read the Evxl benchmark snapshot "{path}"' in record.message
    assert "no Evxl link and no categories" in record.message


@pytest.mark.parametrize(
    "content",
    [
        "{ not json",
        json.dumps({"benchmarkName": "Not a list"}),
        json.dumps([{"benchmarkName": "No difficulties"}]),
        json.dumps(
            [{"benchmarkName": "No code", "difficulties": [{"difficultyName": "Easy"}]}]
        ),
    ],
)
def test_a_snapshot_in_another_shape_gives_no_links_and_says_so(
    snapshot_path, caplog, content
):
    snapshot_path.write_text(content, encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger=evxl_snapshot.__name__):
        assert evxl_benchmark_url("KovaaKsPeakingNarrowImpact", STEAM_ID) is None

    (record,) = caplog.records
    assert "is not in the expected format" in record.message
    assert record.exc_info is not None


def test_an_entry_with_an_unusable_layout_keeps_its_link(snapshot_path, caplog):
    # ``SNAPSHOT`` holds no layouts at all, which is one unusable shape.
    with caplog.at_level(logging.WARNING, logger=evxl_snapshot.__name__):
        entry = evxl_snapshot.evxl_entries_by_code()["kovaaksparenscode"]

    assert entry.layout is None
    assert evxl_benchmark_url("KovaaKsParensCode", STEAM_ID) is not None
    assert (
        "categories for KovaaKsParensCode are not in the expected format" in caplog.text
    )


def test_the_committed_snapshot_loads_in_the_shape_the_lookup_reads():
    entries_by_code = evxl_snapshot.evxl_entries_by_code()

    assert entries_by_code
    assert all(
        entry.benchmark_name and entry.difficulty_name and entry.layout is not None
        for entry in entries_by_code.values()
    )
