import json
import shutil
from pathlib import Path

from source.kovaaks import api_service

TEST_CACHE_DIR = Path("tests/fixtures/generated/api_service_cache")


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


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


def test_get_user_scenario_rank_reads_fresh_cache(monkeypatch):
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
    monkeypatch.setattr(api_service, "CACHE_DIR", TEST_CACHE_DIR)
    cache_dir = TEST_CACHE_DIR / "user_scenario_total_play"
    cache_dir.mkdir(parents=True)
    cache_file = cache_dir / "MingoDynasty.json"
    cache_file.write_text(
        json.dumps(
            {
                "page": 0,
                "max": 100,
                "total": 1,
                "data": [
                    {
                        "leaderboardId": "1",
                        "scenarioName": "Cached Scenario",
                        "counts": {"plays": 10},
                        "rank": 99,
                        "score": 100,
                    },
                ],
            },
        ),
    )

    def fail_get(*_args, **_kwargs):
        raise AssertionError("fresh cache should avoid network calls")

    monkeypatch.setattr(api_service.requests, "get", fail_get)

    assert (
        api_service.get_user_scenario_rank(
            "MingoDynasty",
            "Cached Scenario",
        )
        == 99
    )
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)
