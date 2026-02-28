"""Pytest configuration for repository tests."""

from pathlib import Path


def pytest_sessionstart(session):
    """Create a minimal config.toml expected by import-time config loading."""
    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / "config.toml"
    if config_path.exists():
        return

    stats_dir = repo_root / "tests" / "fixtures" / "stats"
    stats_dir.mkdir(parents=True, exist_ok=True)

    config_path.write_text(
        "\n".join(
            [
                f'stats_dir = "{stats_dir.as_posix()}"',
                "polling_interval = 1000",
                "port = 8080",
                "sens_round_decimal_places = 2",
                "",
            ]
        ),
        encoding="utf-8",
    )
