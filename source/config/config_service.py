"""
Manages the config file for the app, and shares that data to all other modules.
"""

import sys
import tomllib

from pydantic import ValidationError
from pydantic.dataclasses import dataclass

CONFIG_FILE = "config.toml"
CONFIG_ERROR_MESSAGE = (
    "Configuration error: copy example.toml to config.toml and set stats_dir."
)


@dataclass()
class ConfigData:
    """Dataclass models configuration for this app."""

    stats_dir: str
    polling_interval: int
    port: int
    sens_round_decimal_places: int
    debug: bool = False
    kovaaks_username: str | None = None
    steam_id: str | None = None
    scenario_metadata_cache_ttl_hours: int = 24
    scenario_rank_cache_ttl_hours: int = 168
    leaderboard_total_cache_ttl_hours: int = 168


def load_config() -> ConfigData:
    """Loads the config file for this app."""
    with open(CONFIG_FILE, "rb") as _file:
        config_dict = tomllib.load(_file)
    return ConfigData(**config_dict)


try:
    config = load_config()
except OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, ValidationError:
    print(CONFIG_ERROR_MESSAGE, file=sys.stderr)
    raise SystemExit(1) from None
