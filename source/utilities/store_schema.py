"""Schema stamps for the durable JSON stores the app owns and rewrites.

Every file the app writes under ``data/`` carries a top-level integer
``"schema_version"``. The stamp exists so a future release can tell the format
it understands from one it does not, and so a file written by a newer build is
recognized as *newer* rather than parsed as garbage.

Three stores are covered: ``data/settings.json``,
``data/playlist_visibility.json``, and each user playlist under
``data/playlists/``. The bundled benchmark corpus is exempt (it ships with the
code and carries its own provenance contract), and cache files under
``data/cache/`` are deliberately unstamped.

Reads run a four-state machine, per store:

1. **Missing** -- no file. First-run defaults, exactly as before stamps existed.
2. **Error** -- unreadable, not JSON, not an object, no stamp, a malformed or
   non-positive stamp, or a supported stamp whose payload fails that version's
   definition. The bytes are preserved untouched, the store reads as its
   first-run default, and an actionable message is reported.
3. **Supported** -- a stamp this build knows, with a payload that validates.
4. **Future** -- a stamp above the highest this build supports. Nothing is
   read, and every write to that store is refused.

An unstamped but otherwise well-formed file is deliberately *not* treated as
version 1: there is no grandfather rule. The one-time conversion script in
``scripts/stamp_schema_version.py`` retires the pre-stamp population, so no
future reader has to carry a missing-means-v1 special case.

A stamp routes a payload to a validator; it never vouches for the payload.
"""

import json
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA_VERSION_KEY = "schema_version"
CURRENT_SCHEMA_VERSION = 1
# Every version this build can read. Retiring a version removes it from here,
# which turns files carrying it into the error state rather than the future one.
SUPPORTED_SCHEMA_VERSIONS = frozenset({1})
_HIGHEST_SUPPORTED_SCHEMA_VERSION = max(SUPPORTED_SCHEMA_VERSIONS)

# The v1 settings key set. Owned here rather than in ``settings_service`` so the
# schema definition and the runtime constants can never drift apart; the service
# re-exports these names, which is where the rest of the app reads them from.
STATS_DIR_KEY = "stats_dir"
KOVAAKS_USERNAME_KEY = "kovaaks_username"
STEAM_ID_KEY = "steam_id"
SETTINGS_V1_KEYS = frozenset({STATS_DIR_KEY, KOVAAKS_USERNAME_KEY, STEAM_ID_KEY})

SHOWN_PLAYLISTS_KEY = "shown_playlists"

# A backup name that can never collide with a real store file or with an
# earlier backup: the counter advances until an exclusive create succeeds.
_BACKUP_NAME_TEMPLATE = "{name}.corrupt-{counter}.bak"
_MAX_BACKUP_ATTEMPTS = 1000


class StoreState(Enum):
    """Which of the four read states a durable store is in."""

    MISSING = auto()
    ERROR = auto()
    SUPPORTED = auto()
    FUTURE = auto()


class SchemaPayloadError(ValueError):
    """A payload that does not match its stamped version's definition.

    The message is a predicate about the file (``has an unknown setting "x".``)
    so the caller can compose it after the path.
    """


class UnsupportedSchemaError(RuntimeError):
    """A write was refused: the file on disk was written by a newer build.

    Deliberately not an ``OSError``. Callers already treat ``OSError`` as "the
    write failed, try again"; this one is "the write must not happen", and
    every caller reports it differently.
    """


@dataclass(frozen=True)
class StoreDocument:
    """One store's read result: its state, its payload, and what to say."""

    state: StoreState
    # The validated payload, and only in the supported state. Its type is the
    # store's own domain type (a settings mapping, a shown-code set, a
    # PlaylistData), which is why this is deliberately untyped here.
    value: Any = None
    # Actionable, user-facing text for the error and future states; empty
    # otherwise. Surfaced in the UI, not only in the log.
    message: str = ""


def has_schema_marker(payload: Mapping[str, Any]) -> bool:
    """Say whether a parsed object carries a stamp at all (of any shape)."""
    return SCHEMA_VERSION_KEY in payload


def is_current_schema_marker(value: Any) -> bool:
    """Say whether a stamp value is exactly this build's version.

    ``type(...) is int`` on purpose: ``True`` is an ``int`` to ``isinstance``,
    and a JSON ``true`` is not a schema version.
    """
    return type(value) is int and value == CURRENT_SCHEMA_VERSION


def strip_schema_marker(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the payload without its stamp, which never reaches domain code."""
    return {key: value for key, value in payload.items() if key != SCHEMA_VERSION_KEY}


def stamped_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return ``payload`` with this build's stamp first and authoritative."""
    return {
        SCHEMA_VERSION_KEY: CURRENT_SCHEMA_VERSION,
        **strip_schema_marker(payload),
    }


def _unstamped_message(path: Path) -> str:
    return (
        f'{path} has no "{SCHEMA_VERSION_KEY}" line. Add '
        f'"{SCHEMA_VERSION_KEY}": {CURRENT_SCHEMA_VERSION} to it, or delete the '
        "file to start over."
    )


def _bad_marker_message(path: Path, value: Any) -> str:
    return (
        f'{path} has an invalid "{SCHEMA_VERSION_KEY}" value ({value!r}). It '
        f"must be the whole number {CURRENT_SCHEMA_VERSION}."
    )


def _future_message(path: Path, value: int) -> str:
    return (
        f"{path} was written by a newer version of this app "
        f"({SCHEMA_VERSION_KEY} {value}). The file is intact. Update the app to "
        "use it."
    )


def _parse_stamped_object(text: str, path: Path) -> dict[str, Any] | StoreDocument:
    """Parse the text into a stamped JSON object, or say why it is not one."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return _error(f"{path} is not valid JSON.")
    if not isinstance(payload, dict):
        return _error(f"{path} must hold a JSON object.")
    if not has_schema_marker(payload):
        return _error(_unstamped_message(path))
    return payload


def decode_store_document(text: str, *, path: Path, validate) -> StoreDocument:
    """Run the four-state machine over one store file's text.

    ``validate`` receives the payload with the stamp already removed and either
    returns the domain value or raises ``SchemaPayloadError``. It is the single
    definition of what that store's version 1 means, shared by the runtime
    readers and the conversion script.
    """
    payload = _parse_stamped_object(text, path)
    if isinstance(payload, StoreDocument):
        return payload

    version = payload[SCHEMA_VERSION_KEY]
    # A non-positive stamp is garbage, not the future: refusing every write on
    # the strength of ``"schema_version": 0`` would strand the store forever.
    if type(version) is not int or version < 1:
        return _error(_bad_marker_message(path, version))
    if version > _HIGHEST_SUPPORTED_SCHEMA_VERSION:
        message = _future_message(path, version)
        logger.warning(message)
        return StoreDocument(StoreState.FUTURE, message=message)
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        # A retired version inside the supported range: unreadable, not newer.
        return _error(_bad_marker_message(path, version))

    try:
        value = validate(strip_schema_marker(payload))
    except SchemaPayloadError as exc:
        return _error(f"{path} {exc}")
    return StoreDocument(StoreState.SUPPORTED, value=value)


def read_store_document(path: Path, *, encoding: str, validate) -> StoreDocument:
    """Read one store file from disk and classify it. Never mutates the file."""
    try:
        text = path.read_text(encoding=encoding)
    except FileNotFoundError:
        return StoreDocument(StoreState.MISSING)
    except OSError, UnicodeDecodeError:
        logger.warning("Failed to read %s.", path, exc_info=True)
        return _error(f"{path} could not be read. See data/logs/debug.log.")
    return decode_store_document(text, path=path, validate=validate)


def _error(message: str) -> StoreDocument:
    logger.warning(message)
    return StoreDocument(StoreState.ERROR, message=message)


def back_up_unusable_store(path: Path) -> Path:
    """Copy an unusable store file aside before a write replaces it.

    A copy, never a move, to a name that cannot already exist: the incumbent
    stays exactly where it is until the atomic replace lands, so a failure
    anywhere in the write leaves the original in place *and* a backup beside it.
    Raises ``OSError`` when the copy cannot be made, which refuses the write.
    """
    data = path.read_bytes()
    for counter in range(1, _MAX_BACKUP_ATTEMPTS + 1):
        backup = path.with_name(
            _BACKUP_NAME_TEMPLATE.format(name=path.name, counter=counter)
        )
        try:
            # Exclusive create: a backup never replaces an earlier backup.
            with open(backup, "xb") as file:
                file.write(data)
                file.flush()
                os.fsync(file.fileno())
        except FileExistsError:
            continue
        logger.warning("Copied the unusable file %s aside to %s.", path, backup)
        return backup
    msg = f"No free backup name beside {path} after {_MAX_BACKUP_ATTEMPTS} tries."
    raise OSError(msg)


def validate_settings_v1(payload: Mapping[str, Any]) -> dict[str, str]:
    """Define settings v1: a flat object of known keys with text values.

    Unknown keys are invalid rather than ignored. Within a version the key set
    is fixed -- adding a key means bumping the version -- so a stray key under
    stamp 1 is a hand-edit mistake worth surfacing, not tolerating. Missing keys
    still mean unset.
    """
    unknown = sorted(set(payload) - SETTINGS_V1_KEYS)
    if unknown:
        msg = f'has an unknown setting "{unknown[0]}".'
        raise SchemaPayloadError(msg)
    if not all(isinstance(value, str) for value in payload.values()):
        msg = "must hold text values for every setting."
        raise SchemaPayloadError(msg)
    return dict(payload)


def validate_visibility_v1(payload: Mapping[str, Any]) -> set[str]:
    """Define visibility v1: exactly one key, a list of playlist codes."""
    unknown = sorted(set(payload) - {SHOWN_PLAYLISTS_KEY})
    if unknown:
        msg = f'has an unknown key "{unknown[0]}".'
        raise SchemaPayloadError(msg)
    if SHOWN_PLAYLISTS_KEY not in payload:
        msg = f'is missing "{SHOWN_PLAYLISTS_KEY}".'
        raise SchemaPayloadError(msg)
    shown = payload[SHOWN_PLAYLISTS_KEY]
    if not isinstance(shown, list) or not all(isinstance(code, str) for code in shown):
        msg = f'must hold "{SHOWN_PLAYLISTS_KEY}" as a list of text codes.'
        raise SchemaPayloadError(msg)
    return set(shown)
