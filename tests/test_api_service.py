import json
import shutil
from pathlib import Path

from source.kovaaks.api_models import (
    LeaderboardAPIResponse,
    RankingPlayer,
    ScenarioRankInfo,
    ScenarioRankStatus,
)
from source.kovaaks import api_service

TEST_CACHE_DIR = Path("tests/fixtures/generated/api_service_cache")


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


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


def test_get_user_scenario_rank_reads_fresh_rank_cache(monkeypatch):
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

    def fail_get(*_args, **_kwargs):
        raise AssertionError("fresh cache should avoid network calls")

    monkeypatch.setattr(api_service.requests, "get", fail_get)

    assert (
        api_service.get_user_scenario_rank(
            "MingoDynasty",
            "Cached Scenario",
            cache_ttl_hours=168,
        )
        == 99
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
