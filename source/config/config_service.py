"""
Manages the config file for the app, and shares that data to all other modules.
"""

import dataclasses
import logging
import tomllib
from collections.abc import Mapping
from functools import cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field
from pydantic.dataclasses import dataclass

from source.utilities.paths import state_dir

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.toml"


def config_file_path() -> Path:
    """Return the path to the app's config file inside the state root."""
    return state_dir() / CONFIG_FILE


@dataclass()
class ConfigData:
    """Dataclass models configuration for this app."""

    port: int
    polling_interval: int = 1000
    sens_round_decimal_places: int = 1
    debug: bool = False
    scenario_metadata_cache_ttl_hours: int = 24
    scenario_rank_cache_ttl_hours: int = 168
    leaderboard_total_cache_ttl_hours: int = 168
    percentile_warmup_enabled: bool = True
    # gt=0: requests raises an unhandled ValueError on timeout<=0, so reject it
    # at config validation where the startup error message is actionable.
    kovaaks_api_timeout_seconds: Annotated[int, Field(gt=0)] = 30
    # Off by default: the marker only helps an operator running several
    # instances at once, and every other user would just see it as noise.
    show_version_in_title: bool = False


def _warn_unknown_keys(config_dict: Mapping[str, Any]) -> None:
    """Name every unrecognized config key once, then let startup proceed.

    Tolerating unknown keys is permanent design, not a transition shim: it is
    what keeps every update and rollback boundary safe, since a config
    carrying keys a release has retired (or does not have yet) still loads on
    both. The warning replaces silent acceptance with visible, non-fatal
    feedback about typos and leftovers.
    """
    known = {field.name for field in dataclasses.fields(ConfigData)}
    unknown = sorted(set(config_dict) - known)
    if unknown:
        logger.warning(
            "Ignoring unknown key(s) in %s: %s. Remove them when convenient.",
            config_file_path(),
            ", ".join(unknown),
        )


def load_config() -> ConfigData:
    """Loads the config file for this app."""
    with open(config_file_path(), "rb") as _file:
        config_dict = tomllib.load(_file)
    _warn_unknown_keys(config_dict)
    return ConfigData(**config_dict)


@cache
def get_config() -> ConfigData:
    """Load and cache the application config."""
    return load_config()
