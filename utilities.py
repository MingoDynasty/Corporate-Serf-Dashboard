"""
Utility functions for the Corporate Serf app.
"""


def ordinal(number: int) -> str:
    if 11 <= (number % 100) <= 13:
        suffix = "th"
    else:
        suffix = ["th", "st", "nd", "rd", "th"][min(number % 10, 4)]
    return str(number) + suffix
