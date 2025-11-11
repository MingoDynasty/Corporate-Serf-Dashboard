"""
Utility functions for the Corporate Serf app.
"""


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
