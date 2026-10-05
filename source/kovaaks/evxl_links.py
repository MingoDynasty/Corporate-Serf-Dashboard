"""Addresses of a benchmark's pages on Evxl.

Evxl addresses a benchmark by its own benchmark and difficulty names, matched
exactly and case-sensitively, and a bundled playlist file carries neither. The
names come from the Evxl benchmark snapshot the importer generates the bundled
library from, which ships with the code. Evidence for the address rules is in
``docs/kovaaks_api_notes.md``.
"""

import logging
from functools import cache
from urllib.parse import quote

from pydantic import BaseModel, TypeAdapter, ValidationError

from source.utilities.paths import package_root

logger = logging.getLogger(__name__)

EVXL_SITE_URL = "https://evxl.app"
EVXL_BENCHMARKS_SNAPSHOT_PATH = (
    package_root() / "resources" / "evxl" / "benchmarks.json"
)

# Evxl's page that takes no profile answers 404 for a benchmark name holding
# one of these, percent-encoded or not. Measured 2026-10-04 for ``+ / & :``,
# the ones benchmark names held that day. The rest are listed because the set
# JavaScript's ``decodeURI`` leaves encoded fits every name tried, which makes
# it the likely cause. The address with a Steam ID took every name tried.
_PROFILELESS_UNMATCHED_CHARACTERS = frozenset(";/?:@&=+$,#")


class _EvxlDifficulty(BaseModel):
    difficultyName: str
    sharecode: str


class _EvxlBenchmark(BaseModel):
    benchmarkName: str
    difficulties: list[_EvxlDifficulty]


_SNAPSHOT_ADAPTER = TypeAdapter(list[_EvxlBenchmark])


@cache
def _evxl_names_by_code() -> dict[str, tuple[str, str]]:
    """Map each case-folded playlist code to Evxl's benchmark and difficulty names.

    Read once per process. A snapshot that is missing or not in the expected
    shape yields no names, so benchmarks lose their Evxl link and nothing else.
    """
    try:
        benchmarks = _SNAPSHOT_ADAPTER.validate_json(
            EVXL_BENCHMARKS_SNAPSHOT_PATH.read_bytes()
        )
    except OSError as exc:
        logger.warning(
            'Failed to read the Evxl benchmark snapshot "%s"; benchmarks get no '
            "Evxl link: %s",
            EVXL_BENCHMARKS_SNAPSHOT_PATH,
            exc,
        )
        return {}
    except ValidationError:
        logger.warning(
            'The Evxl benchmark snapshot "%s" is not in the expected format; '
            "benchmarks get no Evxl link.",
            EVXL_BENCHMARKS_SNAPSHOT_PATH,
            exc_info=True,
        )
        return {}

    names_by_code: dict[str, tuple[str, str]] = {}
    for benchmark in benchmarks:
        for difficulty in benchmark.difficulties:
            # Case-folded because the snapshot has carried a code in different
            # letter case from the one the bundled file was generated under.
            # A code listed twice keeps its first listing, the one the
            # importer generates that file from.
            names_by_code.setdefault(
                difficulty.sharecode.casefold(),
                (benchmark.benchmarkName, difficulty.difficultyName),
            )
    return names_by_code


def evxl_benchmark_url(playlist_code: str, steam_id: str | None) -> str | None:
    """Build the address of a benchmark's page on Evxl, or None when it has none.

    With a Steam ID the address is that player's sheet for the benchmark's
    difficulty. Without one it is the benchmark's page that asks for a profile
    and a difficulty, which Evxl serves only for some benchmark names.

    Neither address carries a ``tab`` query: Evxl appends its own from the
    visitor's remembered tab, and a link that set one would override it.
    """
    names = _evxl_names_by_code().get(playlist_code.casefold())
    if names is None:
        return None
    benchmark_name, difficulty_name = names
    segments: tuple[str, ...]
    if steam_id:
        segments = ("u", steam_id, benchmark_name, difficulty_name)
    elif _PROFILELESS_UNMATCHED_CHARACTERS.isdisjoint(benchmark_name):
        segments = ("benchmarks", benchmark_name)
    else:
        return None
    # ``safe=""`` because the default leaves ``/`` unescaped, and a name
    # holding one would then read as two path segments.
    encoded = (quote(segment, safe="") for segment in segments)
    return "/".join((EVXL_SITE_URL, *encoded))
