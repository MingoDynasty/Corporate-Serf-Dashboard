from decimal import Decimal

from source.utilities.utilities import format_decimal, ordinal


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
