import json
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path

import pytest

from source.kovaaks.api_models import (
    LeaderboardAPIResponse,
    RankingPlayer,
    ScenarioRankInfo,
    ScenarioRankStatus,
)
from source.kovaaks import api_service

TEST_CACHE_DIR = Path("tests/fixtures/generated/api_service_cache")


class FakeResponse:
    def __init__(self, data, status_code=200, headers=None):
        self._data = data
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise api_service.requests.HTTPError(response=self)
        return None

    def json(self):
        return self._data


def test_get_with_retry_retries_once_on_429(monkeypatch):
    responses = [
        FakeResponse({"error": "rate limited"}, status_code=429),
        FakeResponse({"ok": True}),
    ]
    calls = []
    sleeps = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(api_service.requests, "get", fake_get)
    monkeypatch.setattr(api_service.time, "sleep", sleeps.append)

    response = api_service._get_with_retry("https://example.test", params={"a": 1})

    assert response.json() == {"ok": True}
    assert len(calls) == 2
    assert calls[0] == calls[1]
    assert sleeps == [api_service.DEFAULT_RETRY_AFTER_SECONDS]


@pytest.mark.parametrize(
    ("headers", "expected_delay"),
    [
        ({"Retry-After": "1.25"}, 1.25),
        ({"Retry-After": "60"}, api_service.MAX_RETRY_AFTER_SECONDS),
        ({"Retry-After": "nonsense"}, api_service.DEFAULT_RETRY_AFTER_SECONDS),
        ({}, api_service.DEFAULT_RETRY_AFTER_SECONDS),
    ],
)
def test_get_with_retry_uses_bounded_retry_after(headers, expected_delay, monkeypatch):
    responses = [
        FakeResponse({"error": "rate limited"}, status_code=429, headers=headers),
        FakeResponse({"ok": True}),
    ]
    sleeps = []

    def fake_get(*_args, **_kwargs):
        return responses.pop(0)

    monkeypatch.setattr(api_service.requests, "get", fake_get)
    monkeypatch.setattr(api_service.time, "sleep", sleeps.append)

    api_service._get_with_retry("https://example.test")

    assert sleeps == [expected_delay]


def test_get_with_retry_caps_http_date_retry_after(monkeypatch):
    retry_after = format_datetime(datetime.now(UTC) + timedelta(minutes=1))
    responses = [
        FakeResponse(
            {"error": "rate limited"},
            status_code=429,
            headers={"Retry-After": retry_after},
        ),
        FakeResponse({"ok": True}),
    ]
    sleeps = []

    def fake_get(*_args, **_kwargs):
        return responses.pop(0)

    monkeypatch.setattr(api_service.requests, "get", fake_get)
    monkeypatch.setattr(api_service.time, "sleep", sleeps.append)

    api_service._get_with_retry("https://example.test")

    assert sleeps == [api_service.MAX_RETRY_AFTER_SECONDS]


def test_get_with_retry_does_not_retry_non_429_http_errors(monkeypatch):
    calls = []

    def fake_get(*_args, **_kwargs):
        calls.append(True)
        return FakeResponse({"error": "not found"}, status_code=404)

    monkeypatch.setattr(api_service.requests, "get", fake_get)

    with pytest.raises(api_service.requests.HTTPError):
        api_service._get_with_retry("https://example.test")

    assert len(calls) == 1


def test_get_with_retry_gives_up_after_second_429(monkeypatch):
    responses = [
        FakeResponse({"error": "rate limited"}, status_code=429),
        FakeResponse({"error": "still rate limited"}, status_code=429),
    ]
    sleeps = []

    def fake_get(*_args, **_kwargs):
        return responses.pop(0)

    monkeypatch.setattr(api_service.requests, "get", fake_get)
    monkeypatch.setattr(api_service.time, "sleep", sleeps.append)

    with pytest.raises(api_service.requests.HTTPError):
        api_service._get_with_retry("https://example.test")

    assert sleeps == [api_service.DEFAULT_RETRY_AFTER_SECONDS]
    assert responses == []


def test_get_with_retry_propagates_non_http_exceptions(monkeypatch):
    calls = []

    def fake_get(*_args, **_kwargs):
        calls.append(True)
        raise api_service.requests.ConnectionError("network unavailable")

    monkeypatch.setattr(api_service.requests, "get", fake_get)

    with pytest.raises(api_service.requests.ConnectionError):
        api_service._get_with_retry("https://example.test")

    assert len(calls) == 1


def test_get_leaderboard_scores_allows_custom_pagination(monkeypatch):
    def fake_get_with_retry(_url, params, timeout):
        assert timeout == api_service.TIMEOUT
        assert params == {
            "page": 2,
            "max": 25,
            "leaderboardId": 98330,
            "usernameSearch": "MingoDynasty",
        }
        return FakeResponse({"page": 2, "max": 25, "total": 18342, "data": []})

    monkeypatch.setattr(api_service, "_get_with_retry", fake_get_with_retry)

    response = api_service.get_leaderboard_scores(
        98330,
        username_search="MingoDynasty",
        page=2,
        max_results=25,
    )

    assert response.total == 18342


def test_get_leaderboard_scores_rejects_invalid_pagination():
    with pytest.raises(ValueError, match="page"):
        api_service.get_leaderboard_scores(98330, page=-1)

    with pytest.raises(ValueError, match="max_results"):
        api_service.get_leaderboard_scores(98330, max_results=0)

    with pytest.raises(ValueError, match="max_results"):
        api_service.get_leaderboard_scores(98330, max_results=101)


@pytest.mark.parametrize(
    ("rank", "total_players", "expected_percentile"),
    [
        (11290, 63892, 82.33),
        (78, 196, 60.46),
        (116, 224, 48.44),
        (1, 10, 95.00),
        (2, 10, 85.00),
        (10, 10, 5.00),
        (1, 1, 50.00),
        (1, 18342, 100.00),
    ],
)
def test_calculate_percentile(rank, total_players, expected_percentile):
    assert round(api_service.calculate_percentile(rank, total_players), 2) == (
        expected_percentile
    )


@pytest.mark.parametrize(
    "rank_info",
    [
        ScenarioRankInfo(
            status=ScenarioRankStatus.UNRANKED,
            leaderboard_id=98330,
            total_players=100,
        ),
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            leaderboard_id=98330,
            rank=None,
            total_players=100,
        ),
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            leaderboard_id=98330,
            rank=10,
            total_players=None,
        ),
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            leaderboard_id=98330,
            rank=10,
            total_players=0,
        ),
    ],
)
def test_with_percentile_omits_incomplete_or_unranked_results(rank_info):
    assert api_service._with_percentile(rank_info).percentile is None


def test_make_cache_creates_leaderboard_mapping_file(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)

    api_service.make_cache()

    mapping_file = (
        TEST_CACHE_DIR
        / "scenario_leaderboards"
        / "scenario_name_to_leaderboard_id.json"
    )
    assert json.loads(mapping_file.read_text(encoding="utf-8")) == {}
    assert (TEST_CACHE_DIR / "benchmarks").is_dir()
    assert (TEST_CACHE_DIR / "user_scenario_total_play").is_dir()
    assert (TEST_CACHE_DIR / "leaderboard" / "user_rank").is_dir()
    assert (TEST_CACHE_DIR / "leaderboard" / "totals").is_dir()
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_save_leaderboard_id_handles_concurrent_upserts(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()

    scenarios = [f"Scenario {index}" for index in range(20)]

    def save_mapping(index_scenario):
        index, scenario_name = index_scenario
        api_service.save_leaderboard_id(scenario_name, index, "test")

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(save_mapping, enumerate(scenarios)))

    mapping_file = (
        TEST_CACHE_DIR
        / "scenario_leaderboards"
        / "scenario_name_to_leaderboard_id.json"
    )
    mappings = json.loads(mapping_file.read_text(encoding="utf-8"))
    assert {
        scenario_name: mappings[scenario_name]["leaderboard_id"]
        for scenario_name in scenarios
    } == {scenario_name: index for index, scenario_name in enumerate(scenarios)}
    assert not list(mapping_file.parent.glob("*.tmp"))
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_user_scenario_total_play_fetches_all_pages_and_caches(
    monkeypatch,
):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()

    responses = [
        {
            "page": 0,
            "max": 1,
            "total": 2,
            "data": [
                {
                    "leaderboardId": "1",
                    "scenarioName": "First",
                    "counts": {"plays": 10},
                    "rank": 12,
                    "score": 100,
                },
            ],
        },
        {
            "page": 1,
            "max": 1,
            "total": 2,
            "data": [
                {
                    "leaderboardId": "2",
                    "scenarioName": "Second",
                    "counts": {"plays": 5},
                    "rank": 34,
                    "score": 200,
                },
            ],
        },
    ]

    def fake_get(_url, params, timeout):
        assert timeout == api_service.TIMEOUT
        return FakeResponse(responses[params["page"]])

    monkeypatch.setattr(api_service.requests, "get", fake_get)

    response = api_service.get_user_scenario_total_play("MingoDynasty")

    assert response.total == 2
    assert [scenario.scenarioName for scenario in response.data] == ["First", "Second"]

    cache_file = TEST_CACHE_DIR / "user_scenario_total_play" / "MingoDynasty.json"
    cached_data = json.loads(cache_file.read_text())
    assert cached_data["total"] == 2
    assert len(cached_data["data"]) == 2

    page_0_file = TEST_CACHE_DIR / "user_scenario_total_play" / "MingoDynasty" / "page_0.json"
    page_1_file = TEST_CACHE_DIR / "user_scenario_total_play" / "MingoDynasty" / "page_1.json"
    assert json.loads(page_0_file.read_text(encoding="utf-8")) == responses[0]
    assert json.loads(page_1_file.read_text(encoding="utf-8")) == responses[1]
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_user_scenario_total_play_continues_after_full_page(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()

    first_page_data = [
        {
            "leaderboardId": str(index),
            "scenarioName": f"Scenario {index}",
            "counts": {"plays": index},
            "rank": index,
            "score": index * 10,
        }
        for index in range(100)
    ]
    second_page_data = [
        {
            "leaderboardId": "100",
            "scenarioName": "Scenario 100",
            "counts": {"plays": 100},
            "rank": 100,
            "score": 1000,
        },
    ]
    responses = [
        {
            "page": 0,
            "max": 100,
            "total": 100,
            "data": first_page_data,
        },
        {
            "page": 1,
            "max": 100,
            "total": 100,
            "data": second_page_data,
        },
    ]
    fetched_pages = []

    def fake_get(_url, params, timeout):
        assert timeout == api_service.TIMEOUT
        fetched_pages.append(params["page"])
        return FakeResponse(responses[params["page"]])

    monkeypatch.setattr(api_service.requests, "get", fake_get)

    response = api_service.get_user_scenario_total_play("MingoDynasty")

    assert fetched_pages == [0, 1]
    assert response.total == 101
    assert len(response.data) == 101

    cache_file = TEST_CACHE_DIR / "user_scenario_total_play" / "MingoDynasty.json"
    cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert cached_data["total"] == 101
    assert len(cached_data["data"]) == 101

    page_0_file = TEST_CACHE_DIR / "user_scenario_total_play" / "MingoDynasty" / "page_0.json"
    page_1_file = TEST_CACHE_DIR / "user_scenario_total_play" / "MingoDynasty" / "page_1.json"
    assert json.loads(page_0_file.read_text(encoding="utf-8")) == responses[0]
    assert json.loads(page_1_file.read_text(encoding="utf-8")) == responses[1]
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_user_scenario_total_play_handles_unknown_username(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()

    fetched_pages = []

    def fake_get(_url, params, timeout):
        assert timeout == api_service.TIMEOUT
        fetched_pages.append(params["page"])
        return FakeResponse(None)

    monkeypatch.setattr(api_service.requests, "get", fake_get)

    with pytest.raises(api_service.UnknownKovaaksUserError):
        api_service.get_user_scenario_total_play("UnknownUser")

    assert fetched_pages == [0]

    cache_file = TEST_CACHE_DIR / "user_scenario_total_play" / "UnknownUser.json"
    cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert cached_data == {
        "page": 0,
        "max": 100,
        "total": 0,
        "data": [],
        "error": "unknown_username",
        "username": "UnknownUser",
    }

    page_0_file = TEST_CACHE_DIR / "user_scenario_total_play" / "UnknownUser" / "page_0.json"
    assert json.loads(page_0_file.read_text(encoding="utf-8")) == {
        "page": 0,
        "max": 100,
        "total": 0,
        "data": [],
        "error": "unknown_username",
        "username": "UnknownUser",
    }
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_hydrate_leaderboard_id_cache_refetches_incomplete_total_play_cache(
    monkeypatch,
):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()

    cache_file = TEST_CACHE_DIR / "user_scenario_total_play" / "MingoDynasty.json"
    api_service._write_json(
        cache_file,
        {
            "page": 0,
            "max": 100,
            "total": 2,
            "data": [
                {
                    "leaderboardId": "1",
                    "scenarioName": "Cached First Page Only",
                    "counts": {"plays": 10},
                    "rank": 12,
                    "score": 100,
                },
            ],
        },
    )

    responses = [
        {
            "page": 0,
            "max": 100,
            "total": 2,
            "data": [
                {
                    "leaderboardId": "10",
                    "scenarioName": "Fresh First",
                    "counts": {"plays": 10},
                    "rank": 12,
                    "score": 100,
                },
            ],
        },
        {
            "page": 1,
            "max": 100,
            "total": 2,
            "data": [
                {
                    "leaderboardId": "20",
                    "scenarioName": "Fresh Second",
                    "counts": {"plays": 5},
                    "rank": 34,
                    "score": 200,
                },
            ],
        },
    ]

    def fake_get(_url, params, timeout):
        assert timeout == api_service.TIMEOUT
        return FakeResponse(responses[params["page"]])

    monkeypatch.setattr(api_service.requests, "get", fake_get)

    api_service.hydrate_leaderboard_id_cache("MingoDynasty")

    cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert cached_data["total"] == 2
    assert [scenario["scenarioName"] for scenario in cached_data["data"]] == [
        "Fresh First",
        "Fresh Second",
    ]
    page_0_file = TEST_CACHE_DIR / "user_scenario_total_play" / "MingoDynasty" / "page_0.json"
    page_1_file = TEST_CACHE_DIR / "user_scenario_total_play" / "MingoDynasty" / "page_1.json"
    assert json.loads(page_0_file.read_text(encoding="utf-8")) == responses[0]
    assert json.loads(page_1_file.read_text(encoding="utf-8")) == responses[1]
    assert api_service.get_cached_leaderboard_id("Fresh First") == 10
    assert api_service.get_cached_leaderboard_id("Fresh Second") == 20
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_user_scenario_total_play_allows_null_rank(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()

    def fake_get(_url, params, timeout):
        assert timeout == api_service.TIMEOUT
        return FakeResponse(
            {
                "page": 0,
                "max": 100,
                "total": 1,
                "data": [
                    {
                        "leaderboardId": "1",
                        "scenarioName": "Unranked Scenario",
                        "counts": {"plays": 10},
                        "rank": None,
                        "score": None,
                    },
                ],
            },
        )

    monkeypatch.setattr(api_service.requests, "get", fake_get)

    response = api_service.get_user_scenario_total_play("MingoDynasty")

    assert response.data[0].rank is None
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_leaderboard_total_reads_fresh_cache(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()
    api_service.save_leaderboard_total(98330, 18342)

    def fail_get_leaderboard_scores(*_args, **_kwargs):
        raise AssertionError("fresh total cache should avoid network calls")

    monkeypatch.setattr(
        api_service,
        "get_leaderboard_scores",
        fail_get_leaderboard_scores,
    )

    assert api_service.get_leaderboard_total(98330, cache_ttl_hours=24) == 18342
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_leaderboard_total_fetches_missing_cache_and_writes_payload(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()

    def fake_get_leaderboard_scores(leaderboard_id, **kwargs):
        assert leaderboard_id == 98330
        assert kwargs["max_results"] == 1
        return LeaderboardAPIResponse(page=0, max=1, total=18342, data=[])

    monkeypatch.setattr(
        api_service,
        "get_leaderboard_scores",
        fake_get_leaderboard_scores,
    )

    assert api_service.get_leaderboard_total(98330, cache_ttl_hours=24) == 18342

    cache_file = TEST_CACHE_DIR / "leaderboard" / "totals" / "98330.json"
    cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert cached_data["leaderboard_id"] == 98330
    assert cached_data["total_players"] == 18342
    assert "fetched_at" in cached_data
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_leaderboard_total_refreshes_stale_cache(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()
    api_service.save_leaderboard_total(98330, 100)
    cache_file = TEST_CACHE_DIR / "leaderboard" / "totals" / "98330.json"
    stale_timestamp = time.time() - (25 * 60 * 60)
    os.utime(cache_file, (stale_timestamp, stale_timestamp))

    def fake_get_leaderboard_scores(leaderboard_id, **kwargs):
        assert leaderboard_id == 98330
        assert kwargs["max_results"] == 1
        return LeaderboardAPIResponse(page=0, max=1, total=18342, data=[])

    monkeypatch.setattr(
        api_service,
        "get_leaderboard_scores",
        fake_get_leaderboard_scores,
    )

    assert api_service.get_leaderboard_total(98330, cache_ttl_hours=24) == 18342
    cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert cached_data["total_players"] == 18342
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_scenario_rank_info_reads_fresh_rank_cache(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()
    api_service.save_leaderboard_id("Cached Scenario", 1, "test")
    api_service.save_scenario_rank(
        1,
        "MingoDynasty",
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=99,
            leaderboard_id=1,
        ),
    )
    api_service.save_leaderboard_total(1, 123)

    def fail_get(*_args, **_kwargs):
        raise AssertionError("fresh cache should avoid network calls")

    monkeypatch.setattr(api_service.requests, "get", fail_get)

    rank_info = api_service.get_scenario_rank_info(
        "Cached Scenario",
        "MingoDynasty",
        rank_cache_ttl_hours=168,
    )
    assert rank_info.status == ScenarioRankStatus.RANKED
    assert rank_info.rank == 99
    assert rank_info.total_players == 123
    assert round(rank_info.percentile, 2) == 19.92
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_scenario_rank_info_adds_scenario_name_to_fresh_rank_cache(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()
    api_service.save_leaderboard_id("VT Pasu Intermediate S5", 98330, "test")

    def fake_get_leaderboard_scores(*_args, **_kwargs):
        return LeaderboardAPIResponse(
            page=0,
            max=50,
            total=1,
            data=[
                RankingPlayer(
                    steamId="right-steam-id",
                    score=863.93,
                    rank=11266,
                    webappUsername="MingoDynasty",
                    steamAccountName="MingoDynasty",
                ),
            ],
        )

    monkeypatch.setattr(
        api_service,
        "get_leaderboard_scores",
        fake_get_leaderboard_scores,
    )

    rank_info = api_service.get_scenario_rank_info(
        "VT Pasu Intermediate S5",
        "MingoDynasty",
        steam_id="right-steam-id",
    )

    assert rank_info.scenario_name == "VT Pasu Intermediate S5"

    cache_file = (
        TEST_CACHE_DIR
        / "leaderboard"
        / "user_rank"
        / "MingoDynasty"
        / "98330.json"
    )
    cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert cached_data["scenario_name"] == "VT Pasu Intermediate S5"
    assert cached_data["matched_steam_id"] == "right-steam-id"
    assert "total_players" not in cached_data
    assert "percentile" not in cached_data
    assert "warning_message" not in cached_data
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


@pytest.mark.parametrize(
    ("status", "expected_rank"),
    [
        (ScenarioRankStatus.RANKED, 11266),
        (ScenarioRankStatus.UNRANKED, None),
    ],
)
def test_get_scenario_rank_info_adds_total_players_for_resolved_result(
    monkeypatch,
    status,
    expected_rank,
):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()
    api_service.save_leaderboard_id("VT Pasu Intermediate S5", 98330, "test")

    def fake_fetch_scenario_rank(*_args, **_kwargs):
        return ScenarioRankInfo(
            status=status,
            rank=expected_rank,
            leaderboard_id=98330,
            matched_steam_id="right-steam-id",
        )

    def fake_get_leaderboard_total(leaderboard_id, cache_ttl_hours):
        assert leaderboard_id == 98330
        assert cache_ttl_hours == 24
        return 18342

    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        fake_fetch_scenario_rank,
    )
    monkeypatch.setattr(
        api_service,
        "get_leaderboard_total",
        fake_get_leaderboard_total,
    )

    rank_info = api_service.get_scenario_rank_info(
        "VT Pasu Intermediate S5",
        "MingoDynasty",
        steam_id="right-steam-id",
        leaderboard_total_cache_ttl_hours=24,
    )

    assert rank_info.status == status
    assert rank_info.rank == expected_rank
    assert rank_info.total_players == 18342
    if status == ScenarioRankStatus.RANKED:
        assert round(rank_info.percentile, 2) == 38.58
    else:
        assert rank_info.percentile is None
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_scenario_rank_info_keeps_rank_when_total_fetch_fails(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()
    api_service.save_leaderboard_id("VT Pasu Intermediate S5", 98330, "test")

    def fake_fetch_scenario_rank(*_args, **_kwargs):
        return ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=11266,
            leaderboard_id=98330,
            matched_steam_id="right-steam-id",
        )

    def fail_get_leaderboard_total(*_args, **_kwargs):
        raise api_service.requests.RequestException("leaderboard total unavailable")

    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        fake_fetch_scenario_rank,
    )
    monkeypatch.setattr(
        api_service,
        "get_leaderboard_total",
        fail_get_leaderboard_total,
    )

    rank_info = api_service.get_scenario_rank_info(
        "VT Pasu Intermediate S5",
        "MingoDynasty",
        steam_id="right-steam-id",
    )

    assert rank_info.status == ScenarioRankStatus.RANKED
    assert rank_info.rank == 11266
    assert rank_info.total_players is None
    assert rank_info.percentile is None
    assert rank_info.error_message is None
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_scenario_rank_info_keeps_rank_when_total_validation_fails(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()
    api_service.save_leaderboard_id("VT Pasu Intermediate S5", 98330, "test")

    def fake_fetch_scenario_rank(*_args, **_kwargs):
        return ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=11266,
            leaderboard_id=98330,
            matched_steam_id="right-steam-id",
        )

    def fail_get_leaderboard_total(*_args, **_kwargs):
        LeaderboardAPIResponse.model_validate({"unexpected": "schema"})

    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        fake_fetch_scenario_rank,
    )
    monkeypatch.setattr(
        api_service,
        "get_leaderboard_total",
        fail_get_leaderboard_total,
    )

    rank_info = api_service.get_scenario_rank_info(
        "VT Pasu Intermediate S5",
        "MingoDynasty",
        steam_id="right-steam-id",
    )

    assert rank_info.status == ScenarioRankStatus.RANKED
    assert rank_info.rank == 11266
    assert rank_info.total_players is None
    assert rank_info.percentile is None
    assert rank_info.error_message is None
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_cache_file_helpers_share_username_sanitization(monkeypatch):
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)

    username = "Mingo Dynasty/Bad:Name"
    safe_username = api_service._safe_cache_key(username)

    assert safe_username == "Mingo_Dynasty_Bad_Name"
    assert api_service._user_scenario_total_play_cache_file(username) == (
        TEST_CACHE_DIR / "user_scenario_total_play" / f"{safe_username}.json"
    )
    assert api_service._user_scenario_total_play_page_cache_file(username, 0) == (
        TEST_CACHE_DIR / "user_scenario_total_play" / safe_username / "page_0.json"
    )
    assert api_service._rank_cache_file(98330, username) == (
        TEST_CACHE_DIR
        / "leaderboard"
        / "user_rank"
        / safe_username
        / "98330.json"
    )
    assert api_service._leaderboard_total_cache_file(98330) == (
        TEST_CACHE_DIR / "leaderboard" / "totals" / "98330.json"
    )


def test_get_scenario_rank_info_returns_unknown_for_unknown_username(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()
    api_service.save_leaderboard_id("VT Pasu Intermediate S5", 98330, "test")

    def fake_get_leaderboard_scores(*_args, **_kwargs):
        return LeaderboardAPIResponse(page=0, max=50, total=0, data=[])

    def fake_get(_url, params, timeout):
        assert timeout == api_service.TIMEOUT
        assert params["username"] == "UnknownUser"
        return FakeResponse(None)

    monkeypatch.setattr(
        api_service,
        "get_leaderboard_scores",
        fake_get_leaderboard_scores,
    )
    monkeypatch.setattr(api_service.requests, "get", fake_get)

    rank_info = api_service.get_scenario_rank_info(
        "VT Pasu Intermediate S5",
        "UnknownUser",
    )

    assert rank_info.status == ScenarioRankStatus.UNKNOWN
    assert rank_info.rank is None
    assert rank_info.error_message == "KovaaK's username 'UnknownUser' was not found."

    rank_cache_file = (
        TEST_CACHE_DIR
        / "leaderboard"
        / "user_rank"
        / "UnknownUser"
        / "98330.json"
    )
    assert not rank_cache_file.exists()
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_scenario_rank_info_returns_unknown_when_scenario_search_fails(
    monkeypatch,
):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()

    def fail_hydrate(*_args, **_kwargs):
        raise api_service.requests.RequestException("total-play unavailable")

    def fail_search(*_args, **_kwargs):
        raise api_service.requests.RequestException("scenario search unavailable")

    monkeypatch.setattr(
        api_service,
        "hydrate_leaderboard_id_cache",
        fail_hydrate,
    )
    monkeypatch.setattr(api_service, "search_scenario_exact", fail_search)

    rank_info = api_service.get_scenario_rank_info(
        "VT Pasu Intermediate S5",
        "MingoDynasty",
    )

    assert rank_info.status == ScenarioRankStatus.UNKNOWN
    assert rank_info.rank is None
    assert (
        rank_info.error_message
        == "Failed to resolve leaderboard for VT Pasu Intermediate S5."
    )
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_scenario_rank_info_returns_unknown_when_rank_fetch_fails(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()
    api_service.save_leaderboard_id("VT Pasu Intermediate S5", 98330, "test")

    def fail_fetch_scenario_rank(*_args, **_kwargs):
        raise api_service.requests.RequestException("leaderboard unavailable")

    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        fail_fetch_scenario_rank,
    )

    rank_info = api_service.get_scenario_rank_info(
        "VT Pasu Intermediate S5",
        "MingoDynasty",
    )

    assert rank_info.status == ScenarioRankStatus.UNKNOWN
    assert rank_info.rank is None
    assert rank_info.leaderboard_id == 98330
    assert (
        rank_info.error_message
        == "Failed to fetch scenario rank for VT Pasu Intermediate S5."
    )

    rank_cache_file = (
        TEST_CACHE_DIR
        / "leaderboard"
        / "user_rank"
        / "MingoDynasty"
        / "98330.json"
    )
    assert not rank_cache_file.exists()
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_scenario_rank_info_keeps_unranked_when_username_validation_fails(
    monkeypatch,
):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()
    api_service.save_leaderboard_id("VT Pasu Intermediate S5", 98330, "test")

    def fake_fetch_scenario_rank(*_args, **_kwargs):
        return ScenarioRankInfo(
            status=ScenarioRankStatus.UNRANKED,
            leaderboard_id=98330,
        )

    def fail_total_play(*_args, **_kwargs):
        raise api_service.requests.RequestException("total-play unavailable")

    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        fake_fetch_scenario_rank,
    )
    monkeypatch.setattr(api_service, "get_user_scenario_total_play", fail_total_play)

    rank_info = api_service.get_scenario_rank_info(
        "VT Pasu Intermediate S5",
        "MingoDynasty",
    )

    assert rank_info.status == ScenarioRankStatus.UNRANKED
    assert rank_info.rank is None
    assert rank_info.leaderboard_id == 98330
    assert rank_info.scenario_name == "VT Pasu Intermediate S5"
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_resolve_leaderboard_id_falls_back_to_search_after_total_play_failure(
    monkeypatch,
):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()

    def fail_hydrate(*_args, **_kwargs):
        raise api_service.requests.RequestException("total-play unavailable")

    searched_scenarios = []

    def fake_search_scenario_exact(scenario_name):
        searched_scenarios.append(scenario_name)
        return 98330

    monkeypatch.setattr(
        api_service,
        "hydrate_leaderboard_id_cache",
        fail_hydrate,
    )
    monkeypatch.setattr(
        api_service,
        "search_scenario_exact",
        fake_search_scenario_exact,
    )

    leaderboard_id = api_service.resolve_leaderboard_id(
        "VT Pasu Intermediate S5",
        "MingoDynasty",
    )

    assert leaderboard_id == 98330
    assert searched_scenarios == ["VT Pasu Intermediate S5"]
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_resolve_leaderboard_id_does_not_hide_unknown_username(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()

    def fail_hydrate(*_args, **_kwargs):
        raise api_service.UnknownKovaaksUserError(
            "KovaaK's username 'UnknownUser' was not found."
        )

    def fail_search(*_args, **_kwargs):
        raise AssertionError("unknown username should stop fallback")

    monkeypatch.setattr(
        api_service,
        "hydrate_leaderboard_id_cache",
        fail_hydrate,
    )
    monkeypatch.setattr(api_service, "search_scenario_exact", fail_search)

    with pytest.raises(api_service.UnknownKovaaksUserError):
        api_service.resolve_leaderboard_id(
            "VT Pasu Intermediate S5",
            "UnknownUser",
        )
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_fetch_scenario_rank_prefers_exact_steam_id(monkeypatch):
    players = [
        RankingPlayer(
            steamId="wrong-steam-id",
            score=100,
            rank=1,
            webappUsername="MingoDynasty",
            steamAccountName="MingoDynasty",
        ),
        RankingPlayer(
            steamId="right-steam-id",
            score=200,
            rank=2,
            webappUsername="SomeoneElse",
            steamAccountName="SomeoneElse",
        ),
    ]

    def fake_get_leaderboard_scores(*_args, **_kwargs):
        return LeaderboardAPIResponse(page=0, max=50, total=2, data=players)

    monkeypatch.setattr(
        api_service,
        "get_leaderboard_scores",
        fake_get_leaderboard_scores,
    )

    rank_info = api_service.fetch_scenario_rank(
        98330,
        "MingoDynasty",
        "right-steam-id",
    )

    assert rank_info.status == ScenarioRankStatus.RANKED
    assert rank_info.rank == 2
    assert rank_info.score == 200
    assert rank_info.matched_steam_id == "right-steam-id"
    assert rank_info.warning_message is None


def test_fetch_scenario_rank_records_matched_steam_id_for_username_fallback(
    monkeypatch,
):
    players = [
        RankingPlayer(
            steamId="actual-steam-id",
            score=200,
            rank=2,
            webappUsername="MingoDynasty",
            steamAccountName="MingoDynasty",
        ),
    ]

    def fake_get_leaderboard_scores(*_args, **_kwargs):
        return LeaderboardAPIResponse(page=0, max=50, total=1, data=players)

    monkeypatch.setattr(
        api_service,
        "get_leaderboard_scores",
        fake_get_leaderboard_scores,
    )

    rank_info = api_service.fetch_scenario_rank(
        98330,
        "MingoDynasty",
        "wrong-steam-id",
    )

    assert rank_info.status == ScenarioRankStatus.RANKED
    assert rank_info.rank == 2
    assert rank_info.score == 200
    assert rank_info.matched_steam_id == "actual-steam-id"
    assert rank_info.warning_message is None


def test_get_scenario_rank_info_derives_warning_from_cached_identity(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()
    api_service.save_leaderboard_id("VT Pasu Intermediate S5", 98330, "test")
    api_service.save_scenario_rank(
        98330,
        "MingoDynasty",
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=11266,
            leaderboard_id=98330,
            matched_steam_id="actual-steam-id",
        ),
    )
    api_service.save_leaderboard_total(98330, 18342)

    def fail_fetch_scenario_rank(*_args, **_kwargs):
        raise AssertionError("fresh rank fetch should not run")

    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        fail_fetch_scenario_rank,
    )

    rank_info = api_service.get_scenario_rank_info(
        "VT Pasu Intermediate S5",
        "MingoDynasty",
        steam_id="wrong-steam-id",
    )

    assert rank_info.status == ScenarioRankStatus.RANKED
    assert rank_info.rank == 11266
    assert rank_info.warning_message == (
        "Configured Steam ID 'wrong-steam-id' does not match "
        "KovaaK's user 'MingoDynasty' (actual Steam ID: actual-steam-id)."
    )

    cache_file = (
        TEST_CACHE_DIR
        / "leaderboard"
        / "user_rank"
        / "MingoDynasty"
        / "98330.json"
    )
    cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert cached_data["matched_steam_id"] == "actual-steam-id"
    assert "warning_message" not in cached_data
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_get_scenario_rank_info_reuses_cache_and_clears_warning_after_steam_id_fix(
    monkeypatch,
):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()
    api_service.save_leaderboard_id("VT Pasu Intermediate S5", 98330, "test")
    api_service.save_scenario_rank(
        98330,
        "MingoDynasty",
        ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=11266,
            leaderboard_id=98330,
            matched_steam_id="actual-steam-id",
        ),
    )
    api_service.save_leaderboard_total(98330, 18342)
    fetched = False

    def fake_fetch_scenario_rank(*_args, **_kwargs):
        nonlocal fetched
        fetched = True
        return ScenarioRankInfo(
            status=ScenarioRankStatus.RANKED,
            rank=11265,
            leaderboard_id=98330,
            matched_steam_id="actual-steam-id",
        )

    monkeypatch.setattr(
        api_service,
        "fetch_scenario_rank",
        fake_fetch_scenario_rank,
    )

    rank_info = api_service.get_scenario_rank_info(
        "VT Pasu Intermediate S5",
        "MingoDynasty",
        steam_id="actual-steam-id",
    )

    assert fetched is False
    assert rank_info.status == ScenarioRankStatus.RANKED
    assert rank_info.rank == 11266
    assert rank_info.warning_message is None

    rank_cache_file = (
        TEST_CACHE_DIR
        / "leaderboard"
        / "user_rank"
        / "MingoDynasty"
        / "98330.json"
    )
    assert rank_cache_file.exists()
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


def test_fetch_scenario_rank_returns_unranked_without_exact_match(monkeypatch):
    players = [
        RankingPlayer(
            steamId="765",
            score=100,
            rank=1,
            webappUsername="Domingo",
            steamAccountName="Domingo",
        ),
    ]

    def fake_get_leaderboard_scores(*_args, **_kwargs):
        return LeaderboardAPIResponse(page=0, max=50, total=1, data=players)

    monkeypatch.setattr(
        api_service,
        "get_leaderboard_scores",
        fake_get_leaderboard_scores,
    )

    rank_info = api_service.fetch_scenario_rank(98330, "MingoDynasty")

    assert rank_info.status == ScenarioRankStatus.UNRANKED
    assert rank_info.rank is None


def test_search_scenario_exact_ignores_fuzzy_matches(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    api_service.make_cache()

    def fake_get(_url, params, timeout):
        assert params["scenarioNameSearch"] == "VT Pasu Intermediate S5"
        assert params["max"] == 100
        assert timeout == api_service.TIMEOUT
        return FakeResponse(
            {
                "page": 0,
                "max": 100,
                "total": 2,
                "data": [
                    {
                        "rank": 1,
                        "leaderboardId": 98330,
                        "scenarioName": "VT Pasu Intermediate S5",
                    },
                    {
                        "rank": 2,
                        "leaderboardId": 106278,
                        "scenarioName": "VT Pasu Intermediate S5 Multi",
                    },
                ],
            },
        )

    monkeypatch.setattr(api_service.requests, "get", fake_get)

    leaderboard_id = api_service.search_scenario_exact("VT Pasu Intermediate S5")

    assert leaderboard_id == 98330
    assert api_service.get_cached_leaderboard_id("VT Pasu Intermediate S5") == 98330
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
