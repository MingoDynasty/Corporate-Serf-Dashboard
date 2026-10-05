"""Read a KovaaK's performance file and tell whether its scenario is time-scored.

KovaaK's writes one performance file per run, beside the run's stats file,
and publishes the format at https://wiki.kovaaks.com/performance.proto
(protobuf, ``proto3``). This module reads the few fields the countdown check
needs and skips the rest. It is pure: bytes in, one of three answers out, with
no file access, no logging, and no dependency on a protobuf library.
"""

import math
import struct
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum

SUPPORTED_SCHEMA_VERSION = 1
MIN_SCORE_EVENTS = 2
# How far the running score may sit from the countdown line, in points. It
# absorbs a start lag, not noise: on the maintainer's 84 countdown files
# (2026-10-04) the distance is set at the first score event, at most 0.0174,
# and the nearest other file is 42 away. Every one of those runs was played
# above 400 FPS, so the margin is for machines that lag more.
COUNTDOWN_TOLERANCE = 0.5

_VARINT = 0
_FIXED64 = 1
_LENGTH_DELIMITED = 2
_FIXED32 = 5
# A 64-bit varint never takes more than ten bytes.
_MAX_VARINT_BYTES = 10

_FILE_HEADER = 1
_FILE_EVENT = 2
_HEADER_SCENARIO_HASH = 2
_HEADER_SCHEMA_VERSION = 4
_HEADER_CHALLENGE_PROFILE = 5
_PROFILE_TIME_LIMIT = 1
_PROFILE_TIMESCALE = 10
_EVENT_TIMESTAMP = 1
_EVENT_SCORE = 7
_SCORE_DELTA = 1


class Scoring(Enum):
    """How a performance file answers whether its scenario is time-scored."""

    TIME_SCORED = "time-scored"
    NOT_TIME_SCORED = "not time-scored"
    CANNOT_ANSWER = "can't answer"


@dataclass(frozen=True)
class PerformanceReading:
    """One performance file's answer, with the facts the answer rests on.

    ``time_limit`` and ``scenario_hash`` are set whenever the file can answer.
    On a time-scored answer the time limit is the constant the score counts
    down from, and the hash is the scenario version it was read from.
    ``largest_distance`` is the farthest the running score sat from the
    countdown line, and is ``None`` when the file has no score events.
    """

    scoring: Scoring
    time_limit: float | None = None
    scenario_hash: str | None = None
    score_events: int = 0
    largest_distance: float | None = None


class _MalformedError(ValueError):
    """The bytes are not a well-formed protobuf message of the known shape."""


@dataclass
class _Header:
    schema_version: int = 0
    scenario_hash: str = ""
    time_limit: float = 0.0
    timescale: float = 0.0


def _read_varint(data: bytes, position: int) -> tuple[int, int]:
    value = 0
    for index in range(_MAX_VARINT_BYTES):
        if position >= len(data):
            raise _MalformedError
        byte = data[position]
        position += 1
        value |= (byte & 0x7F) << (7 * index)
        if not byte & 0x80:
            return value, position
    raise _MalformedError


def _fields(data: bytes) -> Iterator[tuple[int, int, int | bytes]]:
    """Yield each field of one message as its number, wire type, and value."""
    position = 0
    while position < len(data):
        key, position = _read_varint(data, position)
        number, wire_type = key >> 3, key & 7
        if wire_type == _VARINT:
            value, position = _read_varint(data, position)
            yield number, wire_type, value
            continue
        if wire_type == _LENGTH_DELIMITED:
            length, position = _read_varint(data, position)
        elif wire_type == _FIXED64:
            length = 8
        elif wire_type == _FIXED32:
            length = 4
        else:
            raise _MalformedError
        end = position + length
        # A slice past the end returns what is left instead of raising, which
        # would read a truncated file as a shorter, well-formed one.
        if end > len(data):
            raise _MalformedError
        yield number, wire_type, data[position:end]
        position = end


def _message(wire_type: int, value: int | bytes) -> bytes:
    if wire_type != _LENGTH_DELIMITED or not isinstance(value, bytes):
        raise _MalformedError
    return value


def _float(wire_type: int, value: int | bytes) -> float:
    if wire_type != _FIXED32 or not isinstance(value, bytes):
        raise _MalformedError
    return struct.unpack("<f", value)[0]


def _unsigned(wire_type: int, value: int | bytes) -> int:
    if wire_type != _VARINT or not isinstance(value, int):
        raise _MalformedError
    return value


def _parse_header(data: bytes) -> _Header:
    header = _Header()
    for number, wire_type, value in _fields(data):
        if number == _HEADER_SCENARIO_HASH:
            # A hash that does not decode can never equal a stats file's, so
            # replacing the bad bytes is enough to keep it from matching.
            header.scenario_hash = _message(wire_type, value).decode(
                "utf-8", errors="replace"
            )
        elif number == _HEADER_SCHEMA_VERSION:
            header.schema_version = _unsigned(wire_type, value)
        elif number == _HEADER_CHALLENGE_PROFILE:
            for profile_number, profile_type, profile_value in _fields(
                _message(wire_type, value)
            ):
                if profile_number == _PROFILE_TIME_LIMIT:
                    header.time_limit = _float(profile_type, profile_value)
                elif profile_number == _PROFILE_TIMESCALE:
                    header.timescale = _float(profile_type, profile_value)
    return header


def _parse_score_event(data: bytes) -> tuple[float, float] | None:
    """Return one event's timestamp and score delta, or None for another kind.

    ``proto3`` leaves a field at its default off the wire, so a missing
    timestamp or delta reads as 0.0.
    """
    timestamp = 0.0
    delta = None
    for number, wire_type, value in _fields(data):
        if number == _EVENT_TIMESTAMP:
            timestamp = _float(wire_type, value)
        elif number == _EVENT_SCORE:
            delta = 0.0
            for score_number, score_type, score_value in _fields(
                _message(wire_type, value)
            ):
                if score_number == _SCORE_DELTA:
                    delta = _float(score_type, score_value)
    if delta is None:
        return None
    return timestamp, delta


def _parse(data: bytes) -> tuple[_Header | None, list[tuple[float, float]]]:
    header = None
    score_events = []
    for number, wire_type, value in _fields(data):
        if number == _FILE_HEADER:
            header = _parse_header(_message(wire_type, value))
        elif number == _FILE_EVENT:
            score_event = _parse_score_event(_message(wire_type, value))
            if score_event is not None:
                score_events.append(score_event)
    return header, score_events


def _is_positive(value: float) -> bool:
    return math.isfinite(value) and value > 0


def read_performance_file(data: bytes) -> PerformanceReading:
    """Answer whether a performance file's scenario is time-scored.

    A time-scored scenario scores the time left on a clock that counts down
    from the file's time limit, so its running score follows
    ``time_limit - timescale * timestamp``. The file answers time-scored when
    it has at least two score events and the running score is within
    ``COUNTDOWN_TOLERANCE`` of that line after every one of them, and not
    time-scored otherwise.

    A file can't answer when its bytes do not parse, when its schema version
    is not the supported one, or when its header lacks a scenario hash, a
    positive time limit, or a positive timescale. Never raises.
    """
    try:
        header, score_events = _parse(data)
    except _MalformedError:
        return PerformanceReading(Scoring.CANNOT_ANSWER)
    if (
        header is None
        or header.schema_version != SUPPORTED_SCHEMA_VERSION
        or not header.scenario_hash
        or not _is_positive(header.time_limit)
        or not _is_positive(header.timescale)
    ):
        return PerformanceReading(Scoring.CANNOT_ANSWER)

    running_score = 0.0
    largest_distance = None
    for timestamp, delta in score_events:
        running_score += delta
        distance = abs(
            running_score - (header.time_limit - header.timescale * timestamp)
        )
        # NaN compares false against everything, so a garbage event would
        # otherwise pass as a distance that is never over the tolerance.
        if math.isnan(distance):
            distance = math.inf
        if largest_distance is None or distance > largest_distance:
            largest_distance = distance

    is_countdown = (
        len(score_events) >= MIN_SCORE_EVENTS
        and largest_distance is not None
        and largest_distance <= COUNTDOWN_TOLERANCE
    )
    return PerformanceReading(
        scoring=Scoring.TIME_SCORED if is_countdown else Scoring.NOT_TIME_SCORED,
        time_limit=header.time_limit,
        scenario_hash=header.scenario_hash,
        score_events=len(score_events),
        largest_distance=largest_distance,
    )
