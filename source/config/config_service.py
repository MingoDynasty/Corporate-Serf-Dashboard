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

# The address the app serves unless `host` in config.toml says otherwise.
# Shared with source.app, which keys the dual-loopback bind on it: the two
# must agree or an unset `host` stops taking the both-faces path.
DEFAULT_HOST = "127.0.0.1"


def config_file_path() -> Path:
    """Return the path to the app's config file inside the state root."""
    return state_dir() / CONFIG_FILE


@dataclass()
class ConfigData:
    """Dataclass models configuration for this app."""

    # ge=1/le=65535: an out-of-range port used to reach sock.bind(), which
    # raises an OverflowError neither bind-path except-clause catches, so the
    # user saw a raw traceback instead of the startup configuration error.
    # Port 0 is refused here even though the socket layer accepts it: the
    # installed launcher probes and opens the configured port, and an
    # OS-chosen one is not a port it can discover.
    port: Annotated[int, Field(ge=1, le=65535)]
    # Loopback by default: the app has no authentication, so serving an
    # address other than this one exposes the run data and the settings to
    # every device that can reach it. Must be an IP literal, not a name --
    # source.app rejects anything else.
    host: str = DEFAULT_HOST
    # gt=0: this feeds a dcc.Interval, so a zero or negative period is
    # nonsense that the browser silently clamps into a request flood rather
    # than failing anywhere the user would look.
    polling_interval: Annotated[int, Field(gt=0)] = 1000
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
