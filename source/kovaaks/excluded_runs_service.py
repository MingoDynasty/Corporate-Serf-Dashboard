"""The runs the player excluded, in one file at ``data/excluded_runs.json``.

An excluded run leaves the Run History chart and every typical score's
window, and stays in the run store, the run list, the PB and the stars. It
is the player's own judgment, such as a test run or a run left halfway, so
nothing works it out and nothing can rebuild it. A run is named by its id,
its stats file's name (``run_id``), which survives a rescan of the stats
folder.

The file is a stamped store run through the shared four-state machine in
``store_schema``: missing is no excluded run, and supported is the list. Error
and future both read as no excluded run, so every run counts, and carry the
machine's message for the run viewer to show; a file from a newer build also
refuses every write. The file is read whenever asked and never cached:
excluding is rare and the file is small.

Every write is a player's press and owns the file: the file on disk is
checked immediately before the write, and a broken one is copied aside first.
"""

import json
import logging
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from source.utilities.atomic_write import atomic_write_text
from source.utilities.paths import state_dir
from source.utilities.store_schema import (
    SchemaPayloadError,
    StoreDocument,
    StoreState,
    UnsupportedSchemaError,
    back_up_unusable_store,
    read_store_document,
    stamped_payload,
)

logger = logging.getLogger(__name__)

EXCLUDED_RUNS_PATH = state_dir() / "data" / "excluded_runs.json"

RUNS_KEY = "excluded_runs"
RUN_KEY = "run"
EXCLUDED_AT_KEY = "excluded_at"
_ENTRY_V1_KEYS = (RUN_KEY, EXCLUDED_AT_KEY)

_KIND = "excluded runs file"

# Held for reads too: on Windows, a replace fails while another thread has
# the file open.
_LOCK = threading.RLock()


@dataclass(frozen=True)
class ExcludedRun:
    """One excluded run as the store holds it."""

    run_id: str
    # Aware, in UTC, to the second.
    excluded_at: datetime


def _parse_utc_time(value: Any) -> datetime | None:
    """Parse an ISO 8601 time in UTC, or return None for anything else.

    A time with no offset is refused, not assumed to be UTC.
    """
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.utcoffset() != timedelta(0):
        return None
    return parsed.astimezone(UTC)


def _format_utc_time(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _entry(item: Any) -> ExcludedRun:
    if not isinstance(item, dict):
        msg = f'must hold "{RUNS_KEY}" as a list of objects.'
        raise SchemaPayloadError(msg)
    unknown = sorted(set(item) - set(_ENTRY_V1_KEYS))
    if unknown:
        msg = f'has an excluded run with an unknown key "{unknown[0]}".'
        raise SchemaPayloadError(msg)
    missing = [key for key in _ENTRY_V1_KEYS if key not in item]
    if missing:
        msg = f'has an excluded run missing "{missing[0]}".'
        raise SchemaPayloadError(msg)
    run = item[RUN_KEY]
    if not isinstance(run, str) or not run:
        msg = f'must hold each "{RUN_KEY}" as text.'
        raise SchemaPayloadError(msg)
    excluded_at = _parse_utc_time(item[EXCLUDED_AT_KEY])
    if excluded_at is None:
        msg = f'must hold each "{EXCLUDED_AT_KEY}" as a UTC time.'
        raise SchemaPayloadError(msg)
    return ExcludedRun(run_id=run, excluded_at=excluded_at)


def validate_excluded_runs_v1(payload: Mapping[str, Any]) -> dict[str, ExcludedRun]:
    """Define excluded runs v1: exactly one key, a list of runs and their times.

    Within a version the key sets are fixed, so an unknown key and a missing
    one are both errors, at the top and in each entry. A run listed twice is
    an error too: the file is only ever written with each run once.
    """
    unknown = sorted(set(payload) - {RUNS_KEY})
    if unknown:
        msg = f'has an unknown key "{unknown[0]}".'
        raise SchemaPayloadError(msg)
    if RUNS_KEY not in payload:
        msg = f'is missing "{RUNS_KEY}".'
        raise SchemaPayloadError(msg)
    items = payload[RUNS_KEY]
    if not isinstance(items, list):
        msg = f'must hold "{RUNS_KEY}" as a list.'
        raise SchemaPayloadError(msg)
    entries: dict[str, ExcludedRun] = {}
    for item in items:
        entry = _entry(item)
        if entry.run_id in entries:
            msg = f'lists the run "{entry.run_id}" twice.'
            raise SchemaPayloadError(msg)
        entries[entry.run_id] = entry
    return entries


def _read_document() -> StoreDocument:
    return read_store_document(
        EXCLUDED_RUNS_PATH,
        encoding="utf-8",
        kind=_KIND,
        validate=validate_excluded_runs_v1,
    )


def read_excluded_runs() -> StoreDocument:
    """Read the store from disk, classified into the four store states.

    Supported carries a mapping of run id to ``ExcludedRun``. Error and future
    carry the message the run viewer shows. Reads disk every time and never
    writes.
    """
    with _LOCK:
        return _read_document()


def excluded_run_ids() -> frozenset[str]:
    """Return the ids of the runs the player excluded.

    Empty unless the store is supported: a broken file or one from a newer
    build excludes nothing, so every run counts until it is fixed.
    """
    document = read_excluded_runs()
    if document.state is not StoreState.SUPPORTED:
        return frozenset()
    return frozenset(document.value)


def _guard_destination() -> None:
    """Classify the file on disk immediately before a write.

    One from a newer build refuses the write with ``UnsupportedSchemaError``
    and the file untouched. A broken one is copied aside first, and
    ``back_up_unusable_store`` raises ``OSError`` when it can't be, which
    refuses the write just as firmly.
    """
    document = _read_document()
    if document.state is StoreState.FUTURE:
        raise UnsupportedSchemaError(document.message)
    if document.state is StoreState.ERROR:
        back_up_unusable_store(EXCLUDED_RUNS_PATH)


def set_run_excluded(run_id: str, *, excluded: bool) -> frozenset[str]:
    """Exclude a run, or include it again, and return the ids the store holds.

    Excluding a run already excluded keeps its first time and writes nothing,
    and so does including a run that isn't excluded. Any other press rewrites
    the file whole, and makes its folder on the first one. A file from a newer
    build refuses with ``UnsupportedSchemaError``, and a broken one is copied
    aside and replaced by a file holding this press alone. ``OSError`` means
    the write failed.
    """
    with _LOCK:
        current = _read_document()
        if current.state is StoreState.FUTURE:
            raise UnsupportedSchemaError(current.message)
        entries: dict[str, ExcludedRun] = (
            dict(current.value) if current.state is StoreState.SUPPORTED else {}
        )
        if excluded == (run_id in entries):
            return frozenset(entries)
        if excluded:
            entries[run_id] = ExcludedRun(run_id, datetime.now(UTC))
        else:
            del entries[run_id]
        payload = {
            RUNS_KEY: [
                {
                    RUN_KEY: entry.run_id,
                    EXCLUDED_AT_KEY: _format_utc_time(entry.excluded_at),
                }
                for entry in entries.values()
            ]
        }
        EXCLUDED_RUNS_PATH.parent.mkdir(parents=True, exist_ok=True)
        # ASCII escapes, as the other stores write: a run id is a file name,
        # which can hold any character a stats file's name can.
        atomic_write_text(
            EXCLUDED_RUNS_PATH,
            json.dumps(stamped_payload(payload), indent=2) + "\n",
            logger=logger,
            before_replace=_guard_destination,
        )
        return frozenset(entries)
