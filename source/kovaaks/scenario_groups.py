"""Sort a bundled benchmark's scenarios into its categories and subcategories.

A bundled playlist file lists scenarios and carries no grouping. The Evxl
benchmark snapshot lists each benchmark's categories in order, each with its
subcategories and how many scenarios each holds, and no scenario names. The
join is therefore positional: it walks the counts down the file's scenario
list. The premise, and the importer comparison that checks it against
KovaaK's own categories, are in ``docs/decision_log.md``.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from source.kovaaks.evxl_snapshot import EvxlCategory, evxl_entries_by_code

# Bundled benchmarks that get no groups although their counts add up, by
# playlist code. On each, a group the walk would draw crosses a boundary
# between two of KovaaK's categories, so some row would be mislabeled. Kept by
# hand: a failure of the importer's comparison needs a look, and usually a
# report upstream, before it belongs here.
GROUP_EXCLUDED_PLAYLIST_CODES = frozenset(
    {
        # IRIS Mixed Benchmarks Easy. Evxl's counts put IRIS Smoothbot Easy
        # under Tracking / PRECISE, and KovaaK's holds it in Clicking
        # (compared 2026-10-05).
        "KovaaKsDeathballingFlyJump",
    }
)

_SHORT_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3}")
_LONG_HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


@dataclass(frozen=True)
class ScenarioGroup:
    """One scenario's category and subcategory, as the table draws them.

    A benchmark with one level of grouping has an empty ``subcategory``. A
    color is six-digit hex, or ``None`` when the snapshot's value is not a
    hex color. A run numbers a series of neighboring scenarios that share a
    group, counted from 0 down the benchmark: two scenarios are drawn as one
    group exactly when their runs are equal.
    """

    category: str
    category_color: str | None
    category_run: int
    subcategory: str
    subcategory_color: str | None
    subcategory_run: int


def _hex_color(value: str) -> str | None:
    color = value.strip()
    if _LONG_HEX_COLOR.fullmatch(color):
        return color
    if _SHORT_HEX_COLOR.fullmatch(color):
        return "#" + "".join(digit * 2 for digit in color[1:])
    return None


def assign_scenario_groups(
    layout: Sequence[EvxlCategory],
    scenario_count: int,
) -> tuple[ScenarioGroup, ...] | None:
    """Walk a layout's counts down a scenario list, one group per scenario.

    ``None`` when the benchmark gets no groups: the layout's counts don't add
    up to ``scenario_count``, or it names nothing. Names are trimmed. When no
    category is named, the subcategories become the categories, so a benchmark
    with one level always has categories.
    """
    promote = not any(category.categoryName.strip() for category in layout)
    # (category, category color, subcategory, subcategory color) per scenario.
    slots: list[tuple[str, str | None, str, str | None]] = []
    for category in layout:
        for subcategory in category.subcategories:
            if subcategory.scenarioCount < 0:
                return None
            name = subcategory.subcategoryName.strip()
            color = _hex_color(subcategory.color)
            slot = (
                (name, color, "", None)
                if promote
                else (
                    category.categoryName.strip(),
                    _hex_color(category.color),
                    name,
                    color,
                )
            )
            slots.extend([slot] * subcategory.scenarioCount)
    if len(slots) != scenario_count:
        return None
    if not any(slot[0] or slot[2] for slot in slots):
        return None

    groups: list[ScenarioGroup] = []
    category_run = subcategory_run = -1
    previous: tuple[str, str] | None = None
    for category_name, category_color, subcategory_name, subcategory_color in slots:
        # Runs go by name alone, as the drawn labels do: neighbors under one
        # name read as one group whatever their colors.
        if previous is None or category_name != previous[0]:
            category_run += 1
            subcategory_run += 1
        elif subcategory_name != previous[1]:
            subcategory_run += 1
        previous = (category_name, subcategory_name)
        groups.append(
            ScenarioGroup(
                category=category_name,
                category_color=category_color,
                category_run=category_run,
                subcategory=subcategory_name,
                subcategory_color=subcategory_color,
                subcategory_run=subcategory_run,
            )
        )
    return tuple(groups)


def join_scenario_groups(
    playlist_code: str,
    scenario_count: int,
) -> tuple[ScenarioGroup, ...] | None:
    """Join a bundled benchmark to its snapshot layout, by playlist code.

    ``None`` when the benchmark gets no groups: its code is on the exclusion
    list, the snapshot has no entry or no usable layout for it, or the walk
    yields none. Only a bundled benchmark may be joined: a playlist the user
    imported has its own scenario order, which the counts don't describe.
    """
    if playlist_code in GROUP_EXCLUDED_PLAYLIST_CODES:
        return None
    entry = evxl_entries_by_code().get(playlist_code.casefold())
    if entry is None or entry.layout is None:
        return None
    return assign_scenario_groups(entry.layout, scenario_count)
