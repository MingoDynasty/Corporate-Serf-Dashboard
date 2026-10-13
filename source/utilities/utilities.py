"""
Utility functions for the Corporate Serf app.
"""

import math
from datetime import date, datetime
from decimal import Decimal

# Abbreviated English month names, hardcoded so the absolute-timestamp format is
# locale-independent (``%b``/``calendar.month_abbr`` follow the process locale).
_MONTH_ABBREVIATIONS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def ordinal(number: int) -> str:
    """
    Get the English ordinal number of the given number.
    Example: ordinal(10) => "10th"
    :param number: number to get ordinal number.
    :return: ordinal number.
    """
    if 11 <= (number % 100) <= 13:
        suffix = "th"
    else:
        suffix = ["th", "st", "nd", "rd", "th"][min(number % 10, 4)]
    return str(number) + suffix


def format_decimal(number) -> Decimal | int:
    """
    Remove trailing zeroes from a float.
    Examples: 10.0 -> 10,  10.5 -> 10.5
    :param number: number to format.
    :return: formatted number.
    """
    decimal = Decimal(str(number))  # Convert to Decimal
    if decimal == decimal.to_integral():
        return int(decimal)
    return decimal.normalize()


def format_approximate_duration(seconds: float) -> str:
    """Format a duration estimate without false precision.

    Examples: 45 -> "<1 min", 254 -> "5 min", 5940 -> "1 hr 39 min".
    Meant for estimates (ETAs), not measurements — precision below one
    minute is deliberately discarded.
    """
    if seconds < 60:
        return "<1 min"
    minutes = math.ceil(seconds / 60)
    if minutes < 60:
        return f"{minutes} min"
    hours, remainder = divmod(minutes, 60)
    if not remainder:
        return f"{hours} hr"
    return f"{hours} hr {remainder} min"


def format_absolute_timestamp(dt: datetime, *, include_seconds: bool = False) -> str:
    """
    Format a datetime as a humanized, GitHub-shaped absolute timestamp.

    Examples: ``Apr 9, 2026, 7:04 PM`` (default),
    ``Apr 9, 2026, 7:04:22 PM`` (``include_seconds=True``).

    The month is a hardcoded English abbreviation, the day and hour are
    unpadded, and minutes/seconds are zero-padded. The hour is 12-hour with
    ``0`` mapped to ``12`` so midnight is ``12:xx AM`` and noon ``12:xx PM``.
    Hand-rolled rather than ``strftime``-ed for locale independence (see the
    month array) and the unpadded hour (no cross-platform strftime code exists:
    ``%-I`` is POSIX-only, ``%#I`` Windows-only).

    The no-seconds variant is mirrored by ``dagfuncs.absoluteTime`` in
    ``assets/dashAgGridFunctions.js``; keep the two in sync by hand.

    :param dt: datetime to format (rendered in its own naive/local time).
    :param include_seconds: whether to append zero-padded seconds.
    :return: formatted timestamp string.
    """
    month = _MONTH_ABBREVIATIONS[dt.month - 1]
    meridiem = "AM" if dt.hour < 12 else "PM"
    hour = dt.hour % 12 or 12
    time_part = f"{hour}:{dt.minute:02d}"
    if include_seconds:
        time_part += f":{dt.second:02d}"
    return f"{month} {dt.day}, {dt.year}, {time_part} {meridiem}"


def format_short_date(day: date, today: date) -> str:
    """Format a date as ``Oct 12``, or ``Jan 1, 2027`` in another year than today's.

    For a date shown beside others of the same year, where the year on each
    would be noise. The month is the hardcoded English abbreviation and the
    day is unpadded, as in ``format_absolute_timestamp``.
    """
    short = f"{_MONTH_ABBREVIATIONS[day.month - 1]} {day.day}"
    if day.year == today.year:
        return short
    return f"{short}, {day.year}"


def format_time_of_day(dt: datetime) -> str:
    """Format a time of day as ``10:50 PM``, with no date and no seconds.

    The hour is 12-hour and unpadded, as in ``format_absolute_timestamp``.
    For a time shown under something that already gives its date.
    """
    meridiem = "AM" if dt.hour < 12 else "PM"
    return f"{dt.hour % 12 or 12}:{dt.minute:02d} {meridiem}"


def format_short_timestamp(dt: datetime, today: date) -> str:
    """Format a moment as ``Oct 4, 9:45 PM``, or ``Dec 30, 2025, 9:45 PM``.

    The absolute timestamp's shape with the year left out while it is
    today's year, which is ``format_short_date`` followed by the time of day.
    """
    return f"{format_short_date(dt.date(), today)}, {format_time_of_day(dt)}"


def format_score(value: float) -> str:
    """Format a score with thousands separators and at most two decimals.

    Trailing zeros are dropped: ``3324.0`` reads ``3,324`` and ``896.2``
    reads ``896.2``. Every table that shows a score formats it here, so one
    run never reads two ways on two pages.
    """
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def format_whole_percent(fraction: float) -> str:
    """Format a fraction as a whole percentage, a half rounding up: 0.545 -> "55%".

    Not ``round``, which sends a half to the even number: 54.5 would read
    54% and 55.5 would read 56%.
    """
    return f"{math.floor(fraction * 100 + 0.5)}%"


def format_elapsed_duration(seconds: float) -> str:
    """Format a measured length of time in the form the estimates use.

    Examples: 45 -> "<1 min", 599 -> "9 min", 3970 -> "1 hr 6 min". A
    measurement counts the whole minutes gone by, as a clock does, where
    ``format_approximate_duration`` rounds an estimate up to the next one.
    """
    minutes = int(seconds // 60)
    if minutes < 1:
        return "<1 min"
    hours, remainder = divmod(minutes, 60)
    if not hours:
        return f"{minutes} min"
    if not remainder:
        return f"{hours} hr"
    return f"{hours} hr {remainder} min"
