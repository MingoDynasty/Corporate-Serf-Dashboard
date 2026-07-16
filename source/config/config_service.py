"""
Manages the config file for the app, and shares that data to all other modules.
"""

import tomllib
from functools import cache
from typing import Annotated

from pydantic import Field
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
    # gt=0: requests raises an unhandled ValueError on timeout<=0, so reject it
    # at config validation where the startup error message is actionable.
    kovaaks_api_timeout_seconds: Annotated[int, Field(gt=0)] = 30


def load_config() -> ConfigData:
    """Loads the config file for this app."""
    with open(CONFIG_FILE, "rb") as _file:
        config_dict = tomllib.load(_file)
    return ConfigData(**config_dict)


@cache
def get_config() -> ConfigData:
    """Load and cache the application config."""
    return load_config()
