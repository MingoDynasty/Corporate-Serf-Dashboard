"""Pytest configuration for repository tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from source.config import config_service
from source.config.config_service import ConfigData, get_config


@pytest.fixture(autouse=True)
def test_config(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Provide deterministic config without touching the user's config file."""
    repo_root = Path(__file__).resolve().parents[1]
    stats_dir = repo_root / "tests" / "fixtures" / "stats"
    stats_dir.mkdir(parents=True, exist_ok=True)
    config = ConfigData(
        stats_dir=str(stats_dir),
        polling_interval=1000,
        port=8080,
        sens_round_decimal_places=2,
        debug=False,
    )
    monkeypatch.setattr(config_service, "load_config", lambda: config)
    get_config.cache_clear()
    yield
    get_config.cache_clear()
