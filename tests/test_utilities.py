from datetime import date, datetime
from decimal import Decimal

import pytest

from source.utilities.stopwatch import Stopwatch
from source.utilities.utilities import (
    format_absolute_timestamp,
    format_approximate_duration,
    format_decimal,
    format_elapsed_duration,
    format_score,
    format_short_date,
    format_short_timestamp,
    format_time_of_day,
    format_whole_percent,
)


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


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 10, 12), "Oct 12"),
        # Unpadded, as the absolute timestamp writes its day.
        (date(2026, 1, 4), "Jan 4"),
        (date(2025, 12, 30), "Dec 30, 2025"),
        (date(2027, 1, 1), "Jan 1, 2027"),
    ],
)
def test_format_short_date_leaves_out_this_years_year(day: date, expected: str) -> None:
    assert format_short_date(day, date(2026, 10, 12)) == expected


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "<1 min"),
        (15, "<1 min"),
        (29.9, "<1 min"),
        # A half rounds up, here and at every later half.
        (30, "1 min"),
        (45, "1 min"),
        # A run of 60 seconds, as the app measures it: its start is written
        # to the millisecond and its end is a whole second.
        (59.9, "1 min"),
        (60, "1 min"),
        # The estimate reads this one "2 min".
        (61, "1 min"),
        (89.9, "1 min"),
        (90, "2 min"),
        (149.9, "2 min"),
        (150, "3 min"),
        (599, "10 min"),
        (3570, "1 hr"),
        (3600, "1 hr"),
        # A session of 1 hr 6 min 1 s is not rounded up to the next minute.
        (3961, "1 hr 6 min"),
        (3970, "1 hr 6 min"),
        (3990, "1 hr 7 min"),
        (98765, "27 hr 26 min"),
        # A clock change can put a session's end before its start.
        (-120, "<1 min"),
    ],
)
def test_format_elapsed_duration_rounds_to_the_nearest_minute(
    seconds: float, expected: str
) -> None:
    assert format_elapsed_duration(seconds) == expected


@pytest.mark.parametrize(
    ("fraction", "expected"),
    [
        (0.0, "0%"),
        (0.544, "54%"),
        # A half rounds up, where ``round`` would send these two to 54 and 56.
        (0.545, "55%"),
        (0.555, "56%"),
        (0.999, "100%"),
        (1.0, "100%"),
    ],
)
def test_format_whole_percent_rounds_a_half_up(fraction: float, expected: str) -> None:
    assert format_whole_percent(fraction) == expected


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (datetime(2026, 10, 4, 22, 50, 59), "10:50 PM"),
        (datetime(2026, 10, 4, 7, 4), "7:04 AM"),
        (datetime(2026, 10, 4, 0, 7), "12:07 AM"),
        (datetime(2026, 10, 4, 12, 0), "12:00 PM"),
    ],
)
def test_format_time_of_day_has_no_date_and_no_seconds(
    moment: datetime, expected: str
) -> None:
    assert format_time_of_day(moment) == expected


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (datetime(2026, 10, 4, 21, 45), "Oct 4, 9:45 PM"),
        (datetime(2025, 12, 30, 21, 45), "Dec 30, 2025, 9:45 PM"),
    ],
)
def test_format_short_timestamp_leaves_out_this_years_year(
    moment: datetime, expected: str
) -> None:
    assert format_short_timestamp(moment, date(2026, 10, 12)) == expected


def test_a_short_timestamp_of_another_year_is_the_absolute_timestamp() -> None:
    moment = datetime(2025, 12, 30, 21, 45)

    assert format_short_timestamp(
        moment, date(2026, 10, 12)
    ) == format_absolute_timestamp(moment)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (3324.0, "3,324"),
        (896.2, "896.2"),
        (12345.678, "12,345.68"),
        (0.0, "0"),
        (-3.5, "-3.5"),
        (100.004, "100"),
    ],
)
def test_format_score_drops_trailing_zeros(score: float, expected: str) -> None:
    assert format_score(score) == expected


def test_stopwatch_elapsed_after_start_and_stop() -> None:
    stopwatch = Stopwatch()
    stopwatch.start()
    stopwatch.stop()
    assert stopwatch.elapsed() >= 0.0


def test_stopwatch_elapsed_before_stop_raises() -> None:
    stopwatch = Stopwatch()
    with pytest.raises(RuntimeError, match=r"start\(\) and stop\(\)"):
        stopwatch.elapsed()
    stopwatch.start()
    with pytest.raises(RuntimeError, match=r"start\(\) and stop\(\)"):
        stopwatch.elapsed()
