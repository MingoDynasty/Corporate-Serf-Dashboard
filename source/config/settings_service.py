"""App-owned user settings stored in ``data/settings.json``.

One home, one writer: ``config.toml`` is human-owned and app-read-only, while
user-level settings the app itself writes live here and are read
per-operation. The mechanics mirror the playlist visibility store — module
``RLock``, an in-process cache, atomic writes, tolerant reads.

Restart-scoped values are pinned rather than re-read: ``stats_dir`` is pinned
by server startup (see ``resolve_stats_dir``), and the identity pair freezes at
the first read that observes a configured username (see ``get_identity``).
Everything the settings page can change while the app runs is therefore either
applied live or covered by its restart notice (see ``is_restart_pending``).

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
# The identity this process serves, frozen as a (username, Steam ID) pair by
# the first read that saw a configured username; None while reads are still
# live. Mutated in place for the same reason as the two above.
_identity_pin: dict[str, tuple[str | None, str | None] | None] = {"value": None}


def clear_settings_cache() -> None:
    """Forget the cached settings so the next read hits disk (test seam)."""
    with _SETTINGS_LOCK:
        _settings_cache["value"] = None


def clear_stats_dir_pin() -> None:
    """Forget the pinned stats directory (test seam)."""
    with _SETTINGS_LOCK:
        _stats_dir_pin["configured"] = None
        _stats_dir_pin["usable"] = None


def clear_identity_pin() -> None:
    """Forget the pinned identity so reads go live again (test seam)."""
    with _SETTINGS_LOCK:
        _identity_pin["value"] = None


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
    """Get the KovaaK's username this process serves, or None when unset."""
    return get_identity()[0]


def get_steam_id() -> str | None:
    """Get the Steam ID this process serves, or None when unset."""
    return get_identity()[1]


def get_identity() -> tuple[str | None, str | None]:
    """Get the username and Steam ID this process serves, as one pair.

    The pair is always consistent: separate reads could straddle a save and
    pair one settings version's username with another's Steam ID, which rank
    lookups would resolve to one player and then cache under the other's name.

    It is also process-pinned. The first read that observes a configured
    username freezes both values for the life of the process; until then reads
    stay live, which is what lets a first-time identity set apply without a
    restart. A later change is restart-scoped instead -- the warmup worker
    keeps the context it started with, and the caches it fills are scoped to
    one identity per process -- and the settings page's restart notice says so.

    Practical consequence, intended: when identity is already configured at
    boot, the first consumer read -- normally the warmup starter during
    startup, though its ``percentile_warmup_enabled`` guard short-circuits
    ahead of the identity read, leaving the freeze to a Home render or a
    watchdog event -- pins it there. Freeze-on-read only ever matters for the
    unset-to-set flow.
    """
    with _SETTINGS_LOCK:
        pinned = _identity_pin["value"]
        if pinned is not None:
            return pinned
        settings = get_settings()
        identity = (
            settings.get(KOVAAKS_USERNAME_KEY) or None,
            settings.get(STEAM_ID_KEY) or None,
        )
        # Freeze on the username alone: it is what every consumer guards on,
        # so a Steam ID without one has not been consumed by anything yet.
        if identity[0] is not None:
            _identity_pin["value"] = identity
        return identity


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


def decline_identity() -> None:
    """Record that the identity ask was put to the user and declined.

    The store's second runtime write path, and deliberately its narrowest: it
    can only set ``kovaaks_username`` to the empty string -- the shipped
    "unset" value -- and never records anything the user typed. The settings
    page's Save stays the only runtime writer of *values*.

    The read-modify-write happens under the module lock rather than in the
    caller, which makes "alters no other key" an invariant of the operation. A
    page that read the settings to render a card and handed the snapshot back
    would restore that snapshot over whatever the settings page saved in
    between; re-reading here means a newer ``stats_dir`` or ``steam_id``
    survives the decline.

    Absent keys stay absent, so declining an identity never configures a stats
    directory the user has not set -- the startup bootstrap keeps looking for
    one on later boots.
    """
    with _SETTINGS_LOCK:
        settings = get_settings()
        settings[KOVAAKS_USERNAME_KEY] = ""
        _write_settings_to_disk(settings)
        _settings_cache["value"] = settings


def is_stats_dir_change_pending() -> bool:
    """Say whether the stored stats directory differs from this process's pin.

    The stats-directory half of ``is_restart_pending``, split out for consumers
    that speak about the directory alone. A restart repairs whichever setting
    moved and nothing else, so anything phrased about the stats directory has
    to ask this rather than the aggregate: an identity change leaves the
    directory exactly as it was, and a page that answered the aggregate would
    promise a restart that fixes nothing.
    """
    with _SETTINGS_LOCK:
        return _get_setting(STATS_DIR_KEY) != _stats_dir_pin["configured"]


def is_restart_pending() -> bool:
    """Say whether stored settings differ from what this process is running on.

    Derived, never stored: it compares the store against the two pins above, so
    the settings page's notice describes reality for every consumer and
    persists across page visits until the restart actually happens.

    An unfrozen identity pin is not a difference. That is the first-time-set
    path, which applies live -- nothing has consumed the old (unset) value.
    """
    with _SETTINGS_LOCK:
        if is_stats_dir_change_pending():
            return True
        pinned_identity = _identity_pin["value"]
        if pinned_identity is None:
            return False
        settings = get_settings()
        stored_identity = (
            settings.get(KOVAAKS_USERNAME_KEY) or None,
            settings.get(STEAM_ID_KEY) or None,
        )
        return stored_identity != pinned_identity


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
