"""App-owned user settings stored in ``data/settings.json``.

One home, one writer: ``config.toml`` is human-owned and app-read-only, while
user-level settings the app itself writes live here and are read
per-operation. The mechanics mirror the playlist visibility store — module
``RLock``, an in-process cache, atomic writes, tolerant reads.

``stats_dir`` is the one exception to per-operation reads: server startup pins
it for the life of the process and every consumer reads that pin (see
``resolve_stats_dir``).

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
from pathlib import Path

from source.utilities.atomic_write import replace_with_retry
from source.utilities.paths import state_dir

logger = logging.getLogger(__name__)

SETTINGS_FILE_PATH = state_dir() / "data" / "settings.json"

KOVAAKS_USERNAME_KEY = "kovaaks_username"
STATS_DIR_KEY = "stats_dir"
STEAM_ID_KEY = "steam_id"

_SETTINGS_LOCK = threading.RLock()
# Cached settings mapping under a single key; None means not yet read from
# disk. Mutated in place so no module-global rebinding is needed.
_settings_cache: dict[str, dict[str, str] | None] = {"value": None}
# The stats directory this process booted with: what was configured, and the
# same value once it has been judged usable (None when it was not). Both are
# None until startup resolves them, and stay None for a startup that never did
# (tests, imports). Mutated in place for the same reason as the cache above.
_stats_dir_pin: dict[str, str | None] = {"configured": None, "usable": None}


def clear_settings_cache() -> None:
    """Forget the cached settings so the next read hits disk (test seam)."""
    with _SETTINGS_LOCK:
        _settings_cache["value"] = None


def clear_stats_dir_pin() -> None:
    """Forget the pinned stats directory (test seam)."""
    with _SETTINGS_LOCK:
        _stats_dir_pin["configured"] = None
        _stats_dir_pin["usable"] = None


def _read_settings_from_disk() -> dict[str, str]:
    """Read the persisted settings; anything unusable yields no keys."""
    try:
        # utf-8-sig, not utf-8: this file is the documented hand-edit escape
        # hatch, and Windows editors write a UTF-8 BOM that json.loads rejects
        # outright — which would read as "every setting unset" instead of as
        # the identity the user just typed. Transparent when no BOM is present.
        raw = SETTINGS_FILE_PATH.read_text(encoding="utf-8-sig")
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


def get_identity() -> tuple[str | None, str | None]:
    """Get the username and Steam ID from a single consistent read.

    Every caller that needs both must use this rather than the two getters
    in sequence: separate reads can straddle a save and pair one settings
    version's username with another's Steam ID, which rank lookups would
    resolve to one player and then cache under the other's name.
    """
    settings = get_settings()
    return (
        settings.get(KOVAAKS_USERNAME_KEY) or None,
        settings.get(STEAM_ID_KEY) or None,
    )


def resolve_stats_dir() -> str | None:
    """Pin the stats directory for this process and return what was pinned.

    Called once from server startup; every consumer reads the pin instead of
    the store. A per-operation read would let a save made while the app runs
    move half the app to a new directory while the watchdog and the runs
    already in memory stayed on the old one — so the value is restart-scoped,
    and the settings page's restart notice describes reality for every
    consumer.
    """
    with _SETTINGS_LOCK:
        configured = _get_setting(STATS_DIR_KEY)
        _stats_dir_pin["configured"] = configured
        _stats_dir_pin["usable"] = (
            configured if configured and Path(configured).is_dir() else None
        )
        return configured


def get_usable_stats_dir() -> str | None:
    """Get the stats directory this process can actually scan and watch.

    Unset, unresolved (a startup that never pinned one), and set-but-missing
    all collapse to None: none of the three can be scanned or watched, and the
    app serves without run data in all of them.

    The existence check is part of the pin rather than repeated per call. A
    directory that appears mid-run -- a network library coming online -- would
    otherwise start reading as usable to whichever consumer asked next, even
    though startup already skipped the scan and never began watching it: pages
    would list scenarios whose runs are not loaded, with the hint that explains
    the emptiness gone.
    """
    with _SETTINGS_LOCK:
        return _stats_dir_pin["usable"]


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
