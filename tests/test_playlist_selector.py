"""The props every playlist dropdown shares: how it sizes in a row that wraps.

The Run History playlist filter and the Aim Training Journey picker both sit
in rows that wrap, and both take their sizing from
``source/pages/playlist_selector.py``. These tests hold the rule that makes a
dropdown narrow before its row wraps, and that the preset splatted into the
dropdown books no width of its own.
"""

import re

from source.pages.playlist_selector import (
    PLAYLIST_SELECTOR_PRESET,
    PLAYLIST_SELECTOR_SIZING,
)

_FLEX_SHORTHAND = re.compile(r"^(?P<grow>\d+) (?P<shrink>\d+) (?P<basis>\d+)px$")
_PX_CLAMP = re.compile(r"^min\((?P<px>\d+)px, 100%\)$")


def _px(clamp, label):
    match = _PX_CLAMP.match(clamp)
    assert match, f"unrecognized {label}: {clamp!r}"
    return int(match["px"])


def _sizing(flex, floor, cap):
    """Reduce one control's sizing props to (grow, hypothetical size, target).

    A flex item is collected onto a line at its *hypothetical main size* --
    flex-basis clamped by min/max width -- so that, not flex-shrink, is what
    decides whether the row wraps.
    """
    shorthand = _FLEX_SHORTHAND.match(flex)
    assert shorthand, f"unrecognized flex shorthand: {flex!r}"
    target = _px(cap, "max width")
    hypothetical = min(max(int(shorthand["basis"]), _px(floor, "min width")), target)
    return int(shorthand["grow"]), hypothetical, target


def test_playlist_sizing_carries_the_shrink_rule():
    """Both playlist dropdowns sit in wrapping rows, so one shared rule owns this.

    A control booking its full target width wraps instead of narrowing:
    line-breaking reads the hypothetical main size, so a basis or floor at
    the 400px target reserves 400px of the row before flex-shrink ever runs.
    Breaking small is only half of it. A row with room must still fill it.
    """
    grow, hypothetical, target = _sizing(
        PLAYLIST_SELECTOR_SIZING["flex"],
        PLAYLIST_SELECTOR_SIZING["miw"],
        PLAYLIST_SELECTOR_SIZING["maw"],
    )

    assert hypothetical < target
    assert grow >= 1


def test_playlist_preset_books_no_width_of_its_own():
    """The preset is splatted into a dropdown that may sit inside the flex
    item, where a second box booking a width fights the first over the break."""
    assert not set(PLAYLIST_SELECTOR_PRESET) & set(PLAYLIST_SELECTOR_SIZING)
