"""Build KovaaK's performance files for tests, and name the real ones kept as fixtures.

The builder writes the same protobuf wire format the game does, but only the
fields the app reads. The two real files carry everything else a run records,
which is what proves the reader skips it.
"""

import struct
from collections.abc import Sequence
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "performances"

# A countdown: Air Pure Easier No UFO, time limit 1000, 60 score events.
COUNTDOWN_FIXTURE = (
    FIXTURE_DIR
    / "Air Pure Easier No UFO - Challenge - 2026.08.07-20.17.03 Performance.perf"
)
COUNTDOWN_FIXTURE_HASH = "b084b3c448c9417a770afac883f6a1a2"
# A fixed-length run: VT Controlsphere Intermediate S5, time limit 60, whose
# 60 score events are points gained.
FIXED_LENGTH_FIXTURE = (
    FIXTURE_DIR
    / "VT Controlsphere Intermediate S5 - Challenge - 2026.08.06-23.21.32 Performance.perf"
)

DEFAULT_HASH = "0123456789abcdef0123456789abcdef"

_VARINT = 0
_LENGTH_DELIMITED = 2
_FIXED32 = 5


def _varint(value: int) -> bytes:
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            encoded.append(byte | 0x80)
        else:
            encoded.append(byte)
            return bytes(encoded)


def _key(number: int, wire_type: int) -> bytes:
    return _varint(number << 3 | wire_type)


def _message_field(number: int, payload: bytes) -> bytes:
    return _key(number, _LENGTH_DELIMITED) + _varint(len(payload)) + payload


def _float_field(number: int, value: float) -> bytes:
    return _key(number, _FIXED32) + struct.pack("<f", value)


def _varint_field(number: int, value: int) -> bytes:
    return _key(number, _VARINT) + _varint(value)


def score_event(timestamp: float, delta: float) -> bytes:
    """Encode one score event: a timestamp and the points it adds."""
    return _message_field(
        2,
        _float_field(1, timestamp) + _message_field(7, _float_field(1, delta)),
    )


def build_performance_file(
    score_events: Sequence[tuple[float, float]] = (),
    *,
    time_limit: float | None = 1000.0,
    timescale: float | None = 1.0,
    scenario_hash: str | None = DEFAULT_HASH,
    schema_version: int | None = 1,
    with_header: bool = True,
) -> bytes:
    """Encode a performance file from ``(timestamp, delta)`` score events.

    ``None`` leaves a header field off the wire, as ``proto3`` does for a
    field at its default.
    """
    data = b""
    if with_header:
        profile = b""
        if time_limit is not None:
            profile += _float_field(1, time_limit)
        if timescale is not None:
            profile += _float_field(10, timescale)
        header = _message_field(1, b"Test Scenario")
        if scenario_hash is not None:
            header += _message_field(2, scenario_hash.encode())
        if schema_version is not None:
            header += _varint_field(4, schema_version)
        header += _message_field(5, profile)
        data += _message_field(1, header)
    for timestamp, delta in score_events:
        data += score_event(timestamp, delta)
    return data


def countdown_events(
    time_limit: float = 1000.0,
    count: int = 60,
    *,
    points_per_second: float = 1.0,
    early_by: float = 0.0,
) -> list[tuple[float, float]]:
    """Build the score events of a countdown, one a second.

    The running score after second ``k`` is
    ``time_limit - points_per_second * k``: the first event grants the limit
    less the time gone, and each later one takes a second's points away.
    ``early_by`` stamps every event that much before its second.
    """
    events = []
    for second in range(1, count + 1):
        delta = time_limit - points_per_second if second == 1 else -points_per_second
        events.append((second - early_by, delta))
    return events
