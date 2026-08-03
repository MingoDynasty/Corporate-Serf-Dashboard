import pytest
from flask import Flask

from source import health
from source.health import LAUNCH_TOKEN_ENV_VAR, register_health_endpoint
from source.utilities.build_info import BuildInfo


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    """Serve /health on a bare Flask app with a known build identity."""
    monkeypatch.setattr(
        health,
        "get_build_info",
        lambda: BuildInfo(
            sha="a" * 40,
            commit_date="2026-07-18",
            tag="v2026.07.18",
            source="manifest",
        ),
    )
    server = Flask(__name__)
    register_health_endpoint(server)
    return server.test_client()


def test_health_reports_the_build_identity(client, monkeypatch) -> None:
    monkeypatch.delenv(LAUNCH_TOKEN_ENV_VAR, raising=False)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "tag": "v2026.07.18",
        "sha": "a" * 40,
        "commit_date": "2026-07-18",
        "source": "manifest",
        "launch_token": None,
    }


def test_health_echoes_the_launch_token(client, monkeypatch) -> None:
    monkeypatch.setenv(LAUNCH_TOKEN_ENV_VAR, "token-123")

    assert client.get("/health").get_json()["launch_token"] == "token-123"
