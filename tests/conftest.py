"""Pytest configuration for repository tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from source.config import config_service, settings_service
from source.config.config_service import ConfigData, get_config


@pytest.fixture(autouse=True)
def test_config(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Provide deterministic config without touching the user's config file."""
    config = ConfigData(
        polling_interval=1000,
        port=8050,
        sens_round_decimal_places=2,
        debug=False,
    )
    monkeypatch.setattr(config_service, "load_config", lambda: config)
    get_config.cache_clear()
    yield
    get_config.cache_clear()


@pytest.fixture(autouse=True)
def test_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[None]:
    """Keep the settings store off the developer's real one.

    Identity stays unset, and the stats directory is pinned the way a real
    startup pins it -- at the fixture stats folder, so tests that render Home
    or scan runs see the same directory they always have.
    """
    # Its own subdirectory: tests that drive the store directly point it at
    # ``tmp_path/data`` and expect to find nothing there but their own writes.
    monkeypatch.setattr(
        settings_service,
        "SETTINGS_FILE_PATH",
        tmp_path / "settings-store" / "settings.json",
    )
    settings_service.clear_settings_cache()
    stats_dir = Path(__file__).resolve().parent / "fixtures" / "stats"
    stats_dir.mkdir(parents=True, exist_ok=True)
    settings_service.save_settings({settings_service.STATS_DIR_KEY: str(stats_dir)})
    settings_service.resolve_stats_dir()
    yield
    settings_service.clear_settings_cache()
    settings_service.clear_stats_dir_pin()
