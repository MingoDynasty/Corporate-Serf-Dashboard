"""Read the Evxl benchmark snapshot that ships with the code.

The benchmark importer generates the bundled library from this file, and the
app reads two things from it that a bundled playlist file doesn't carry: the
names Evxl addresses a benchmark by, and the layout of categories and
subcategories its scenarios are sorted into.
"""

import logging
from functools import cache
from typing import Any, NamedTuple

from pydantic import BaseModel, TypeAdapter, ValidationError

from source.utilities.paths import package_root

logger = logging.getLogger(__name__)

EVXL_BENCHMARKS_SNAPSHOT_PATH = (
    package_root() / "resources" / "evxl" / "benchmarks.json"
)


class EvxlSubcategory(BaseModel):
    """One subcategory of a layout, and how many scenarios it holds."""

    subcategoryName: str
    color: str
    scenarioCount: int


class EvxlCategory(BaseModel):
    """One category of a layout, with its subcategories in order."""

    categoryName: str
    color: str
    subcategories: list[EvxlSubcategory]


class _EvxlDifficulty(BaseModel):
    difficultyName: str
    sharecode: str
    # Left unvalidated here and checked per entry, so one entry's bad layout
    # costs that benchmark its groups and no benchmark its Evxl link.
    categories: Any = None


class _EvxlBenchmark(BaseModel):
    benchmarkName: str
    difficulties: list[_EvxlDifficulty]


_SNAPSHOT_ADAPTER = TypeAdapter(list[_EvxlBenchmark])
_LAYOUT_ADAPTER = TypeAdapter(tuple[EvxlCategory, ...])


class EvxlSnapshotEntry(NamedTuple):
    """What the app reads from one difficulty's entry in the snapshot.

    ``layout`` is the entry's categories in order, or ``None`` when they are
    not in the expected shape.
    """

    benchmark_name: str
    difficulty_name: str
    layout: tuple[EvxlCategory, ...] | None


@cache
def evxl_entries_by_code() -> dict[str, EvxlSnapshotEntry]:
    """Map each case-folded playlist code to its entry in the snapshot.

    Read once per process. A snapshot that is missing or not in the expected
    shape yields no entries, so benchmarks lose their Evxl link and their
    categories and nothing else.
    """
    try:
        benchmarks = _SNAPSHOT_ADAPTER.validate_json(
            EVXL_BENCHMARKS_SNAPSHOT_PATH.read_bytes()
        )
    except OSError as exc:
        logger.warning(
            'Failed to read the Evxl benchmark snapshot "%s"; benchmarks get no '
            "Evxl link and no categories: %s",
            EVXL_BENCHMARKS_SNAPSHOT_PATH,
            exc,
        )
        return {}
    except ValidationError:
        logger.warning(
            'The Evxl benchmark snapshot "%s" is not in the expected format; '
            "benchmarks get no Evxl link and no categories.",
            EVXL_BENCHMARKS_SNAPSHOT_PATH,
            exc_info=True,
        )
        return {}

    entries_by_code: dict[str, EvxlSnapshotEntry] = {}
    for benchmark in benchmarks:
        for difficulty in benchmark.difficulties:
            # Case-folded because the snapshot has carried a code in different
            # letter case from the one the bundled file was generated under.
            # A code listed twice keeps its first listing, the one the
            # importer generates that file from.
            code = difficulty.sharecode.casefold()
            if code in entries_by_code:
                continue
            try:
                layout = _LAYOUT_ADAPTER.validate_python(difficulty.categories)
            except ValidationError:
                logger.warning(
                    "The Evxl benchmark snapshot's categories for %s are not in "
                    "the expected format; that benchmark gets no categories.",
                    difficulty.sharecode,
                    exc_info=True,
                )
                layout = None
            entries_by_code[code] = EvxlSnapshotEntry(
                benchmark.benchmarkName, difficulty.difficultyName, layout
            )
    return entries_by_code
