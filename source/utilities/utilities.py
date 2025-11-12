"""
Utility functions for the Corporate Serf app.
"""

from decimal import Decimal
from typing import Union


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


def format_decimal(number) -> Union[Decimal, int]:
    """
    Remove trailing zeroes from a float.
    Examples: 10.0 -> 10,  10.5 -> 10.5
    :param number: number to format.
    :return: formatted number.
    """
    decimal = Decimal(str(number))  # Convert to Decimal
    if decimal == decimal.to_integral():
        return int(decimal)
    else:
        return decimal.normalize()
