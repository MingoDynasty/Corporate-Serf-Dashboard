"""The player's scenario notes, one file per scenario under ``data/scenario_notes/``.

A note belongs to the scenario's name as the app holds it: the stats file's
``Scenario:`` field with its outer spaces stripped, case and inner spaces kept.
Every caller already holds that name, so this module never normalizes it, and
every version of a scenario shares one note. The file name is that name through
``safe_file_key``, so names that differ only by case, which Windows file names
fold together, still get a file each.

Each file is a stamped store of its own, run through the shared four-state
machine in ``store_schema``: missing is no note, supported is the note, and
error and future carry the machine's message for the scenario's card. A note is
read when asked and never cached; the path comes from the name, so nothing ever
scans the folder.

Every write is a user's save and owns its file: the file on disk is checked
immediately before the write, a broken one is copied aside first, and one from
a newer build refuses the save. Saving empty text deletes the note after the
same check. The last save wins across tabs.
"""

import json
import logging
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

from source.utilities.atomic_write import atomic_write_text
from source.utilities.file_keys import safe_file_key
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

SCENARIO_NOTES_DIR = state_dir() / "data" / "scenario_notes"

# Counted in Python characters. The editor's text box counts UTF-16 units,
# which are never fewer, so any text it lets through is within this limit.
MAX_NOTE_CHARACTERS = 2000

SCENARIO_KEY = "scenario"
TEXT_KEY = "text"
EDITED_AT_KEY = "edited_at"
# In the order a missing key is reported.
_NOTE_V1_KEYS = (SCENARIO_KEY, TEXT_KEY, EDITED_AT_KEY)

_KIND = "scenario note file"

_NOTES_LOCK = threading.RLock()


@dataclass(frozen=True)
class ScenarioNote:
    """One scenario's note as the store holds it."""

    text: str
    # Aware, in UTC, to the second. Moves only when a save changes the text.
    edited_at: datetime


def scenario_note_path(scenario: str) -> Path:
    """Return where ``scenario``'s note lives, whether or not it exists."""
    return SCENARIO_NOTES_DIR / f"{safe_file_key(scenario)}.json"


def _parse_utc_time(value: Any) -> datetime | None:
    """Parse an ISO 8601 time in UTC, or return None for anything else.

    A time with no offset is refused, not assumed to be UTC: the file says it
    is UTC or it is wrong.
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


def _is_empty_note(text: str) -> bool:
    return not text or text.isspace()


def validate_scenario_note_v1(
    payload: Mapping[str, Any], *, scenario: str
) -> ScenarioNote:
    """Define scenario note v1: exactly the scenario, the text, and its edit time.

    Within a version the key set is fixed, so an unknown key and a missing one
    are both errors. ``scenario`` is the name the caller asked for: a file at
    this path holding another scenario's note is in the error state, which is
    what lets a save copy it aside rather than lose either note.
    """
    unknown = sorted(set(payload) - set(_NOTE_V1_KEYS))
    if unknown:
        msg = f'has an unknown key "{unknown[0]}".'
        raise SchemaPayloadError(msg)
    missing = [key for key in _NOTE_V1_KEYS if key not in payload]
    if missing:
        msg = f'is missing "{missing[0]}".'
        raise SchemaPayloadError(msg)
    for key in (SCENARIO_KEY, TEXT_KEY):
        if not isinstance(payload[key], str):
            msg = f'must hold "{key}" as text.'
            raise SchemaPayloadError(msg)
    if payload[SCENARIO_KEY] != scenario:
        msg = "is for another scenario."
        raise SchemaPayloadError(msg)
    text = payload[TEXT_KEY]
    if _is_empty_note(text):
        msg = "holds an empty note."
        raise SchemaPayloadError(msg)
    if len(text) > MAX_NOTE_CHARACTERS:
        msg = f"holds more than {MAX_NOTE_CHARACTERS:,} characters."
        raise SchemaPayloadError(msg)
    edited_at = _parse_utc_time(payload[EDITED_AT_KEY])
    if edited_at is None:
        msg = f'must hold "{EDITED_AT_KEY}" as a UTC time.'
        raise SchemaPayloadError(msg)
    return ScenarioNote(text=text, edited_at=edited_at)


def _read_note_document(scenario: str) -> StoreDocument:
    return read_store_document(
        scenario_note_path(scenario),
        encoding="utf-8",
        kind=_KIND,
        validate=partial(validate_scenario_note_v1, scenario=scenario),
    )


def read_scenario_note(scenario: str) -> StoreDocument:
    """Read ``scenario``'s note from disk, classified into the four store states.

    Supported carries a ``ScenarioNote``; missing means the scenario has no
    note. Error and future carry the message the card shows in place of the
    text. Reads disk every time and never writes.
    """
    # Held for reads too: on Windows, a replace or a delete fails while
    # another thread has the file open.
    with _NOTES_LOCK:
        return _read_note_document(scenario)


def _guard_note_destination(scenario: str) -> None:
    """Classify whatever sits at the note's path, immediately before a write.

    Reads disk rather than what the card showed, which may be minutes old. A
    file from a newer build refuses the write with ``UnsupportedSchemaError``
    and the destination untouched. A broken file is copied aside first, and
    ``back_up_unusable_store`` raises ``OSError`` when it can't be, which
    refuses the write just as firmly.

    Unlike the playlist writer's guard, a healthy file is never a refusal: one
    holding another scenario's note reads as broken, so it is copied aside and
    neither note is lost.
    """
    document = _read_note_document(scenario)
    if document.state is StoreState.FUTURE:
        raise UnsupportedSchemaError(document.message)
    if document.state is StoreState.ERROR:
        back_up_unusable_store(scenario_note_path(scenario))


def save_scenario_note(scenario: str, text: str) -> ScenarioNote | None:
    """Save ``text`` as ``scenario``'s note and return the note the store holds.

    - Empty or whitespace-only text deletes the note and returns None.
    - Text equal to the readable note on disk writes nothing and keeps its edit
      time, so ``edited_at`` moves only when the text changes.
    - Any other text replaces the file whole, stamped with the current UTC
      time, and the folder is made on the first save.

    A write and a delete are both guarded by the file on disk: one from a newer
    build refuses with ``UnsupportedSchemaError``, and a broken one is copied
    aside first. ``OSError`` means the write or the delete failed. Text over
    ``MAX_NOTE_CHARACTERS`` raises ``SchemaPayloadError`` with nothing written,
    since the store never writes a file it would read as broken.
    """
    with _NOTES_LOCK:
        path = scenario_note_path(scenario)
        if _is_empty_note(text):
            _guard_note_destination(scenario)
            path.unlink(missing_ok=True)
            return None
        payload = {
            SCENARIO_KEY: scenario,
            TEXT_KEY: text,
            EDITED_AT_KEY: _format_utc_time(datetime.now(UTC)),
        }
        note = validate_scenario_note_v1(payload, scenario=scenario)
        current = _read_note_document(scenario)
        if current.state is StoreState.SUPPORTED and current.value.text == text:
            return current.value
        path.parent.mkdir(parents=True, exist_ok=True)
        # ASCII escapes, as the other stores write: a JavaScript string, and so
        # the text a page sends, can hold a lone surrogate, which a plain UTF-8
        # write would refuse.
        atomic_write_text(
            path,
            json.dumps(stamped_payload(payload), indent=2) + "\n",
            logger=logger,
            before_replace=partial(_guard_note_destination, scenario),
        )
        return note
