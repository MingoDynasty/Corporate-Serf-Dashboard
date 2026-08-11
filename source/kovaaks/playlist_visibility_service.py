"""Per-code show/hide visibility state for playlists.

Visibility is a display preference, not file state: hidden playlists stay
loaded, their routes keep resolving, and rank overlays keep drawing — hiding
only removes them from selector option lists and (by default) the overview.
The store is a plain show-list: a playlist is visible iff its code is in the
persisted ``shown_playlists`` list (see the 2026-07-11 playlist-overview entry
in ``docs/decision_log.md``).

The file carries a ``schema_version`` stamp. A file this build cannot use --
malformed, unstamped, or stamped by a newer build -- reads as the first-run
seed and surfaces a warning on the Playlists page rather than hiding
everything. A user-initiated show/hide owns an unusable file, copying it aside
first; a file from a newer build refuses every write.
"""

import json
import logging
import threading

from source.kovaaks.data_service import (
    get_playlist_selector_options,
    get_user_root_playlist_codes,
)
from source.utilities.atomic_write import atomic_write_text
from source.utilities.paths import state_dir
from source.utilities.store_schema import (
    SHOWN_PLAYLISTS_KEY,
    StoreDocument,
    StoreState,
    UnsupportedSchemaError,
    back_up_unusable_store,
    read_store_document,
    stamped_payload,
    validate_visibility_v1,
)

logger = logging.getLogger(__name__)

VISIBILITY_FILE_PATH = state_dir() / "data" / "playlist_visibility.json"

# First-run visible set: the bundled Voltaic + Viscose benchmarks. A
# hard-coded seed rather than a config.toml option — after first run the UI
# owns visibility, and a config knob would be a second control surface
# fighting it (proposal R4).
DEFAULT_VISIBLE_CODES = frozenset(
    {
        "KovaaKsBobbingSepiaBuff",  # Voltaic Advanced Benchmarks S5
        "KovaaKsBottingShinyDoor",  # Voltaic Intermediate Benchmarks S5
        "KovaaKsBouncingSilverBinding",  # Voltaic Novice Benchmarks S5
        "KovaaKsQuestingMaximumblueNightfall",  # Viscose benchmarks hard
        "KovaaKsPushingMauveWeaponlevel",  # Viscose benchmarks medium
        "KovaaKsRaidingMediumFaction",  # Viscose benchmarks easier
        "KovaaKsDinkingVibrantInfiltration",  # Viscose Entry Benchmarks
        "KovaaKsScreamingPulledEgg",  # Viscose Benchmark S2 - Easier
        "KovaaKsPeakingNarrowImpact",  # Viscose Benchmark S2 - Medium
        "KovaaKsPlunderingOlivegreenClutch",  # Viscose Benchmark S2 - Hard
        "KovaaKsRaidingPeriwinkleWindow",  # Viscose Benchmark S2 - Expert
    }
)

_VISIBILITY_LOCK = threading.RLock()
# The store's last read result under a single key; None means not yet read from
# disk. Mutated in place so no module-global rebinding is needed.
_shown_cache: dict[str, StoreDocument | None] = {"value": None}


def clear_visibility_cache() -> None:
    """Forget the cached shown set so the next read hits disk (test seam)."""
    with _VISIBILITY_LOCK:
        _shown_cache["value"] = None


def _seed_shown_codes() -> set[str]:
    # The seed must never hide anything the user could already see: bundled
    # defaults plus every playlist loaded from the user root (importing was
    # the intent to see it).
    return set(DEFAULT_VISIBLE_CODES) | get_user_root_playlist_codes()


def _visibility_document() -> StoreDocument:
    """Get the store's read result, hitting disk at most once per cache life."""
    with _VISIBILITY_LOCK:
        document = _shown_cache["value"]
        if document is None:
            document = read_store_document(
                VISIBILITY_FILE_PATH,
                encoding="utf-8",
                validate=validate_visibility_v1,
            )
            _shown_cache["value"] = document
        return document


def _write_shown_to_disk(shown: set[str]) -> None:
    payload = json.dumps(
        stamped_payload({SHOWN_PLAYLISTS_KEY: sorted(shown)}), indent=2
    )
    VISIBILITY_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(VISIBILITY_FILE_PATH, payload + "\n", logger=logger)


def _guard_visibility_write() -> None:
    """Refuse a write over a newer schema; preserve an unusable file first."""
    document = _visibility_document()
    if document.state is StoreState.FUTURE:
        raise UnsupportedSchemaError(document.message)
    if document.state is StoreState.ERROR:
        back_up_unusable_store(VISIBILITY_FILE_PATH)


def get_visibility_store_message() -> str:
    """Get the actionable message for an unusable store, or an empty string.

    The Playlists page shows this: a store falling back to the seed looks
    exactly like a first run, so without it the fallback is invisible.
    """
    return _visibility_document().message


def get_shown_playlist_codes() -> set[str]:
    """Get the codes of playlists the user has chosen to see.

    A missing visibility file yields the first-run seed without writing
    anything — the file materializes on the first show/hide. So does a file
    this build cannot use: reading an unusable store as "nothing is shown"
    would empty every selector, which is indistinguishable from data loss,
    whereas the seed is the same inert default a first run gets. What tells
    the two apart is the warning ``get_visibility_store_message`` carries.
    A usable file is authoritative, including an empty list (everything hidden
    on purpose).
    """
    with _VISIBILITY_LOCK:
        document = _visibility_document()
        if document.state is not StoreState.SUPPORTED:
            return _seed_shown_codes()
        return set(document.value)


def is_playlist_shown(playlist_code: str) -> bool:
    """Check whether a playlist is currently visible in option lists."""
    return playlist_code in get_shown_playlist_codes()


def show_playlist(playlist_code: str) -> None:
    """Make a playlist visible and persist the preference."""
    with _VISIBILITY_LOCK:
        shown = get_shown_playlist_codes()
        if playlist_code in shown:
            return
        shown.add(playlist_code)
        _guard_visibility_write()
        _write_shown_to_disk(shown)
        _shown_cache["value"] = StoreDocument(StoreState.SUPPORTED, value=shown)


def hide_playlist(playlist_code: str) -> None:
    """Hide a playlist from option lists and persist the preference."""
    with _VISIBILITY_LOCK:
        shown = get_shown_playlist_codes()
        if playlist_code not in shown:
            return
        shown.discard(playlist_code)
        _guard_visibility_write()
        _write_shown_to_disk(shown)
        _shown_cache["value"] = StoreDocument(StoreState.SUPPORTED, value=shown)


def toggle_playlist_visibility(playlist_code: str) -> bool:
    """Flip a playlist's visibility; return True when it is now shown."""
    with _VISIBILITY_LOCK:
        if is_playlist_shown(playlist_code):
            hide_playlist(playlist_code)
            return False
        show_playlist(playlist_code)
        return True


def get_visible_playlist_selector_options() -> list[dict[str, str]]:
    """Get selector options filtered to visible playlists.

    The single visibility filter for every playlist option list (proposal
    R13): the Home filter, the Aim Training Journey picker, and the overview
    all consume this wrapper, so they can never disagree about what is
    visible.
    """
    shown = get_shown_playlist_codes()
    return [
        option for option in get_playlist_selector_options() if option["value"] in shown
    ]
