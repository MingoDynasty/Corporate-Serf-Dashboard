import tomllib
from dataclasses import asdict, dataclass

import tomli_w

CONFIG_FILE = "config.toml"


@dataclass()
class ConfigData:
    scenario_to_monitor: str
    stats_dir: str
    within_n_days: int
    top_n_scores: int
    polling_interval: int
    port: int


def load_config() -> ConfigData:
    with open(CONFIG_FILE, "rb") as _file:
        config_dict = tomllib.load(_file)
    return ConfigData(**config_dict)


def update_config(config_data: ConfigData) -> None:
    """Write the current config file to disk."""
    with open(CONFIG_FILE, "wb") as file:
        tomli_w.dump(asdict(config_data), file)
