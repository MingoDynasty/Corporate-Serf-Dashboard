"""Addresses of a benchmark's pages on Evxl.

Evxl addresses a benchmark by its own benchmark and difficulty names, matched
exactly and case-sensitively, and a bundled playlist file carries neither. The
names come from the Evxl benchmark snapshot, which ships with the code.
Evidence for the address rules is in ``docs/kovaaks_api_notes.md``.
"""

from urllib.parse import quote

from source.kovaaks.evxl_snapshot import evxl_entries_by_code

EVXL_SITE_URL = "https://evxl.app"

# Evxl's page that takes no profile answers 404 for a benchmark name holding
# one of these, percent-encoded or not. Measured 2026-10-04 for ``+ / & :``,
# the ones benchmark names held that day. The rest are listed because the set
# JavaScript's ``decodeURI`` leaves encoded fits every name tried, which makes
# it the likely cause. The address with a Steam ID took every name tried.
_PROFILELESS_UNMATCHED_CHARACTERS = frozenset(";/?:@&=+$,#")


def evxl_benchmark_url(playlist_code: str, steam_id: str | None) -> str | None:
    """Build the address of a benchmark's page on Evxl, or None when it has none.

    With a Steam ID the address is that player's sheet for the benchmark's
    difficulty. Without one it is the benchmark's page that asks for a profile
    and a difficulty, which Evxl serves only for some benchmark names.

    Neither address carries a ``tab`` query: Evxl appends its own from the
    visitor's remembered tab, and a link that set one would override it.
    """
    entry = evxl_entries_by_code().get(playlist_code.casefold())
    if entry is None:
        return None
    benchmark_name, difficulty_name = entry.benchmark_name, entry.difficulty_name
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
