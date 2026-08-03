from datetime import datetime
from decimal import Decimal

import pytest

from source.utilities.utilities import (
    format_absolute_timestamp,
    format_approximate_duration,
    format_decimal,
    ordinal,
)


def test_ordinal_special_cases() -> None:
    assert ordinal(1) == "1st"
    assert ordinal(2) == "2nd"
    assert ordinal(3) == "3rd"
    assert ordinal(4) == "4th"
    assert ordinal(11) == "11th"
    assert ordinal(12) == "12th"
    assert ordinal(13) == "13th"
    assert ordinal(21) == "21st"


def test_format_decimal_integral_and_fractional() -> None:
    assert format_decimal(10.0) == 10
    assert format_decimal(10.5) == Decimal("10.5")
    assert format_decimal("100.000") == 100


def test_format_absolute_timestamp_single_digit_day_and_hour() -> None:
    assert (
        format_absolute_timestamp(datetime(2026, 4, 9, 7, 4)) == "Apr 9, 2026, 7:04 AM"
    )


def test_format_absolute_timestamp_midnight() -> None:
    assert (
        format_absolute_timestamp(datetime(2026, 4, 9, 0, 7)) == "Apr 9, 2026, 12:07 AM"
    )


def test_format_absolute_timestamp_noon() -> None:
    assert (
        format_absolute_timestamp(datetime(2026, 4, 9, 12, 0))
        == "Apr 9, 2026, 12:00 PM"
    )


def test_format_absolute_timestamp_afternoon_pm() -> None:
    assert (
        format_absolute_timestamp(datetime(2026, 11, 23, 15, 30))
        == "Nov 23, 2026, 3:30 PM"
    )


def test_format_absolute_timestamp_include_seconds() -> None:
    assert (
        format_absolute_timestamp(datetime(2026, 4, 9, 19, 4, 22), include_seconds=True)
        == "Apr 9, 2026, 7:04:22 PM"
    )


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "<1 min"),
        (59.9, "<1 min"),
        (60, "1 min"),
        (61, "2 min"),
        (254, "5 min"),
        (3600, "1 hr"),
        (5940, "1 hr 39 min"),
        (98765, "27 hr 27 min"),
    ],
)
def test_format_approximate_duration(seconds: float, expected: str) -> None:
    assert format_approximate_duration(seconds) == expected
