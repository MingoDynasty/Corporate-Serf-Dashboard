"""Pytest configuration for repository tests."""

from pathlib import Path
from typing import Any

_CONFIG_BACKUP: bytes | None = None
_CONFIG_PATH: Path | None = None


def pytest_sessionstart(session: Any) -> None:
    """Install a deterministic config.toml for the test session."""
    del session
    global _CONFIG_BACKUP, _CONFIG_PATH

    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / "config.toml"
    stats_dir = repo_root / "tests" / "fixtures" / "stats"
    stats_dir.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        _CONFIG_BACKUP = config_path.read_bytes()

    config_path.write_text(
        "\n".join(
            [
                f'stats_dir = "{stats_dir.as_posix()}"',
                "polling_interval = 1000",
                "port = 8080",
                "sens_round_decimal_places = 2",
                "debug = false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _CONFIG_PATH = config_path


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    """Restore the user's config.toml after tests complete."""
    del session, exitstatus
    if _CONFIG_PATH is None:
        return
    if _CONFIG_BACKUP is None:
        _CONFIG_PATH.unlink(missing_ok=True)
        return
    _CONFIG_PATH.write_bytes(_CONFIG_BACKUP)
