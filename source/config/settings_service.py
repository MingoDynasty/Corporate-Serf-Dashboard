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

Unset semantics are deliberately flat: a missing key and an empty value both
mean *not configured*, and so does a file the app cannot use. The store carries
a ``schema_version`` stamp, so "cannot use" now splits three ways: a missing
file is first run, a file that is unreadable/malformed/unstamped/invalid is an
error state that reads as no keys and says so on the settings page, and a file
stamped by a newer build reads as no keys and refuses every write. Only a
user-initiated save may overwrite an error-state file, and it copies the
incumbent aside first.

Hand-editing the file while the app is stopped is a legitimate escape hatch;
edits made while it runs are not picked up, because reads are cached
in-process. A hand edit must keep the stamp and use only the three known keys:
within a version the key set is fixed, so an unknown key is reported rather
than ignored.
"""

import json
import logging
import threading
from collections.abc import Mapping
from pathlib import Path

from source.utilities.atomic_write import atomic_write_text
from source.utilities.paths import state_dir
from source.utilities.store_schema import (
    KOVAAKS_USERNAME_KEY,
    STATS_DIR_KEY,
    STEAM_ID_KEY,
    StoreDocument,
    StoreState,
    UnsupportedSchemaError,
    back_up_unusable_store,
    read_store_document,
    stamped_payload,
    validate_settings_v1,
)

logger = logging.getLogger(__name__)

SETTINGS_FILE_PATH = state_dir() / "data" / "settings.json"

# KOVAAKS_USERNAME_KEY / STATS_DIR_KEY / STEAM_ID_KEY are defined in
# ``store_schema``, beside the v1 key set they make up, so the schema definition
# and the runtime constants cannot drift. They stay importable from here, which
# is where the rest of the app has always read them.

_SETTINGS_LOCK = threading.RLock()
# The store's last read result under a single key; None means not yet read from
# disk. Mutated in place so no module-global rebinding is needed.
_settings_cache: dict[str, StoreDocument | None] = {"value": None}
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


def _read_settings_document() -> StoreDocument:
    """Classify the settings file through the shared four-state machine."""
    # utf-8-sig, not utf-8: this file is the documented hand-edit escape hatch,
    # and Windows editors write a UTF-8 BOM that json.loads rejects outright —
    # which would read as "every setting unset" instead of as the identity the
    # user just typed. Transparent when no BOM is present. The visibility and
    # playlist stores are machine-written and stay plain UTF-8, where a BOM is
    # invalid.
    return read_store_document(
        SETTINGS_FILE_PATH,
        encoding="utf-8-sig",
        validate=validate_settings_v1,
    )


def _settings_document() -> StoreDocument:
    """Get the store's read result, hitting disk at most once per cache life."""
    with _SETTINGS_LOCK:
        document = _settings_cache["value"]
        if document is None:
            document = _read_settings_document()
            _settings_cache["value"] = document
        return document


def get_settings() -> dict[str, str]:
    """Get every stored setting; anything but a usable file yields no keys.

    The ``schema_version`` stamp is a storage detail and never leaks out: what
    callers get is the domain mapping alone.
    """
    document = _settings_document()
    if document.state is not StoreState.SUPPORTED:
        return {}
    return dict(document.value)


def get_settings_store_state() -> StoreState:
    """Say which of the four read states the settings file is in."""
    return _settings_document().state


def get_settings_store_message() -> str:
    """Get the actionable message for an unusable store, or an empty string.

    The settings page shows this, because a store read as "no keys" is
    otherwise indistinguishable from a first run with an empty form.
    """
    return _settings_document().message


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
    """Replace the stored settings with ``values`` and refresh the cache.

    A user-initiated save owns the file: an unusable incumbent is copied aside
    first (so self-service recovery from a bad hand edit stays possible) and
    then replaced whole. A file stamped by a newer build is never overwritten;
    that raises ``UnsupportedSchemaError``, which every caller reports.
    """
    settings = dict(values)
    with _SETTINGS_LOCK:
        _guard_settings_write()
        _write_settings_to_disk(settings)
        _settings_cache["value"] = StoreDocument(StoreState.SUPPORTED, value=settings)


def _guard_settings_write() -> None:
    """Refuse a write over a newer schema; preserve an unusable file first.

    Reads the store when nothing has yet, so the guard holds for a writer that
    runs before any prior read (a save on a freshly started process).
    """
    document = _settings_document()
    if document.state is StoreState.FUTURE:
        raise UnsupportedSchemaError(document.message)
    if document.state is StoreState.ERROR:
        # Raises OSError when the copy cannot be made, which refuses the write:
        # nothing is overwritten until its bytes are safely beside it.
        back_up_unusable_store(SETTINGS_FILE_PATH)


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
    # Written plain UTF-8 even though it is read as utf-8-sig: the app never
    # authors a BOM, it only tolerates one a Windows editor left behind.
    payload = json.dumps(stamped_payload(settings), indent=2, sort_keys=True)
    SETTINGS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(SETTINGS_FILE_PATH, payload + "\n", logger=logger)
