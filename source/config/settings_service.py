"""App-owned user settings stored in ``data/settings.json``.

One home, one writer: ``config.toml`` is human-owned and app-read-only, while
user-level settings the app itself writes live here and are read
per-operation. The mechanics mirror the playlist visibility store — module
``RLock``, an in-process cache, atomic writes, tolerant reads.

Unset semantics are deliberately flat: a missing key, an empty value, and a
missing/unreadable/malformed file all mean *not configured*. A malformed file
is warned about once and treated as holding no keys; the next save rewrites it
whole.

Hand-editing the file while the app is stopped is a legitimate escape hatch;
edits made while it runs are not picked up, because reads are cached
in-process.
"""

import json
import logging
import os
import threading
from collections.abc import Mapping

from source.utilities.atomic_write import replace_with_retry
from source.utilities.paths import state_dir

logger = logging.getLogger(__name__)

SETTINGS_FILE_PATH = state_dir() / "data" / "settings.json"

KOVAAKS_USERNAME_KEY = "kovaaks_username"
STEAM_ID_KEY = "steam_id"

_SETTINGS_LOCK = threading.RLock()
# Cached settings mapping under a single key; None means not yet read from
# disk. Mutated in place so no module-global rebinding is needed.
_settings_cache: dict[str, dict[str, str] | None] = {"value": None}


def clear_settings_cache() -> None:
    """Forget the cached settings so the next read hits disk (test seam)."""
    with _SETTINGS_LOCK:
        _settings_cache["value"] = None


def _read_settings_from_disk() -> dict[str, str]:
    """Read the persisted settings; anything unusable yields no keys."""
    try:
        raw = SETTINGS_FILE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError, UnicodeDecodeError:
        logger.warning(
            "Failed to read %s; treating every setting as unset.",
            SETTINGS_FILE_PATH,
            exc_info=True,
        )
        return {}
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in payload.items()
        ):
            raise TypeError("settings must be a flat object of string values")
    except json.JSONDecodeError, TypeError:
        logger.warning(
            "Invalid settings file %s; treating every setting as unset. "
            "The file is rewritten on the next save.",
            SETTINGS_FILE_PATH,
            exc_info=True,
        )
        return {}
    return payload


def get_settings() -> dict[str, str]:
    """Get every stored setting, reading disk at most once per cache lifetime."""
    with _SETTINGS_LOCK:
        cached = _settings_cache["value"]
        if cached is None:
            cached = _read_settings_from_disk()
            _settings_cache["value"] = cached
        return dict(cached)


def _get_setting(key: str) -> str | None:
    """Get one setting, collapsing absent and empty to the same "unset"."""
    return get_settings().get(key) or None


def get_kovaaks_username() -> str | None:
    """Get the configured KovaaK's username, or None when unset."""
    return _get_setting(KOVAAKS_USERNAME_KEY)


def get_steam_id() -> str | None:
    """Get the configured Steam ID, or None when unset."""
    return _get_setting(STEAM_ID_KEY)


def save_settings(values: Mapping[str, str]) -> None:
    """Replace the stored settings with ``values`` and refresh the cache."""
    settings = dict(values)
    with _SETTINGS_LOCK:
        _write_settings_to_disk(settings)
        _settings_cache["value"] = settings


def _write_settings_to_disk(settings: Mapping[str, str]) -> None:
    payload = json.dumps(dict(settings), indent=2, sort_keys=True)
    SETTINGS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_file = SETTINGS_FILE_PATH.with_name(
        f".{SETTINGS_FILE_PATH.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        with open(temp_file, "w", encoding="utf-8") as file:
            file.write(payload)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        replace_with_retry(temp_file, SETTINGS_FILE_PATH, logger=logger)
    finally:
        temp_file.unlink(missing_ok=True)
