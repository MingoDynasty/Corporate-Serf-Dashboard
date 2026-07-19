"""Per-code show/hide visibility preferences for playlists.

Visibility is a display preference, not file state: hidden playlists stay
loaded, their routes keep resolving, and rank overlays keep drawing — hiding
only removes them from selector option lists and (by default) the overview.
The store is a plain show-list: a playlist is visible iff its code is in the
persisted ``shown_playlists`` list (see the 2026-07-11 playlist-overview entry
in ``docs/decision_log.md``).
"""

import json
import logging
import os
import threading

from source.kovaaks.data_service import (
    get_playlist_selector_options,
    get_user_root_playlist_codes,
)
from source.utilities.atomic_write import replace_with_retry
from source.utilities.paths import state_dir

logger = logging.getLogger(__name__)

PREFERENCES_FILE_PATH = state_dir() / "data" / "preferences.json"
_SHOWN_PLAYLISTS_KEY = "shown_playlists"

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

_PREFERENCES_LOCK = threading.RLock()
# Cached shown set under a single key; None means not yet read from disk.
# Mutated in place so no module-global rebinding is needed.
_shown_cache: dict[str, set[str] | None] = {"value": None}


def clear_preferences_cache() -> None:
    """Forget the cached shown set so the next read hits disk (test seam)."""
    with _PREFERENCES_LOCK:
        _shown_cache["value"] = None


def _seed_shown_codes() -> set[str]:
    # The seed must never hide anything the user could already see: bundled
    # defaults plus every playlist loaded from the user root (importing was
    # the intent to see it).
    return set(DEFAULT_VISIBLE_CODES) | get_user_root_playlist_codes()


def _read_shown_from_disk() -> set[str] | None:
    """Read the persisted shown set; None means absent or unusable."""
    try:
        raw = PREFERENCES_FILE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError, UnicodeDecodeError:
        logger.warning(
            "Failed to read %s; falling back to the first-run visibility seed.",
            PREFERENCES_FILE_PATH,
            exc_info=True,
        )
        return None
    try:
        payload = json.loads(raw)
        shown = payload[_SHOWN_PLAYLISTS_KEY]
        if not isinstance(shown, list) or not all(
            isinstance(code, str) for code in shown
        ):
            raise TypeError(f"{_SHOWN_PLAYLISTS_KEY} must be a list of strings")
    except json.JSONDecodeError, KeyError, TypeError:
        logger.warning(
            "Invalid preferences file %s; falling back to the first-run "
            "visibility seed. The file is rewritten on the next show/hide.",
            PREFERENCES_FILE_PATH,
            exc_info=True,
        )
        return None
    return set(shown)


def _write_shown_to_disk(shown: set[str]) -> None:
    payload = json.dumps({_SHOWN_PLAYLISTS_KEY: sorted(shown)}, indent=2)
    PREFERENCES_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_file = PREFERENCES_FILE_PATH.with_name(
        f".{PREFERENCES_FILE_PATH.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        with open(temp_file, "w", encoding="utf-8") as file:
            file.write(payload)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        replace_with_retry(temp_file, PREFERENCES_FILE_PATH, logger=logger)
    finally:
        temp_file.unlink(missing_ok=True)


def get_shown_playlist_codes() -> set[str]:
    """Get the codes of playlists the user has chosen to see.

    A missing (or unusable) preferences file yields the first-run seed
    without writing anything — the file materializes on the first show/hide.
    An existing file is authoritative, including an empty list (everything
    hidden on purpose).
    """
    with _PREFERENCES_LOCK:
        if _shown_cache["value"] is None:
            _shown_cache["value"] = _read_shown_from_disk()
        shown = _shown_cache["value"]
        return set(shown) if shown is not None else _seed_shown_codes()


def is_playlist_shown(playlist_code: str) -> bool:
    """Check whether a playlist is currently visible in option lists."""
    return playlist_code in get_shown_playlist_codes()


def show_playlist(playlist_code: str) -> None:
    """Make a playlist visible and persist the preference."""
    with _PREFERENCES_LOCK:
        shown = get_shown_playlist_codes()
        if playlist_code in shown:
            return
        shown.add(playlist_code)
        _write_shown_to_disk(shown)
        _shown_cache["value"] = shown


def hide_playlist(playlist_code: str) -> None:
    """Hide a playlist from option lists and persist the preference."""
    with _PREFERENCES_LOCK:
        shown = get_shown_playlist_codes()
        if playlist_code not in shown:
            return
        shown.discard(playlist_code)
        _write_shown_to_disk(shown)
        _shown_cache["value"] = shown


def toggle_playlist_visibility(playlist_code: str) -> bool:
    """Flip a playlist's visibility; return True when it is now shown."""
    with _PREFERENCES_LOCK:
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
