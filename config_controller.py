import tomllib
from dataclasses import dataclass

import tomli_w

CONFIG_FILE = "config.toml"


@dataclass(frozen=True)
class ConfigData:
    scenario_to_monitor: str
    stats_dir: str
    within_n_days: int
    top_n_scores: int
    polling_interval: int
    port: int


def load_config() -> dict:
    with open(CONFIG_FILE, "rb") as _file:
        config = tomllib.load(_file)
    return config


def update_config(config) -> None:
    """Write the current config file to disk."""
    with open(CONFIG_FILE, "wb") as file:
        tomli_w.dump(config, file)
