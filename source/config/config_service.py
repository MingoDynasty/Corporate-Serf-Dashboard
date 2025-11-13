"""
Manages the config file for the app, and shares that data to all other modules.
"""

import tomllib

from pydantic.dataclasses import dataclass

CONFIG_FILE = "config.toml"


@dataclass()
class ConfigData:
    """Dataclass models configuration for this app."""

    stats_dir: str
    polling_interval: int
    port: int
    sens_round_decimal_places: int


def load_config() -> ConfigData:
    """Loads the config file for this app."""
    with open(CONFIG_FILE, "rb") as _file:
        config_dict = tomllib.load(_file)
    return ConfigData(**config_dict)


config = load_config()
