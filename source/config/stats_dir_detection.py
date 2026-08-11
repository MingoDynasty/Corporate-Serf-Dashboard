"""Find the KovaaK's stats directory on this machine.

A Python port of the installer's ``Find-KovaaksStatsDir``, deleted when installs
became non-interactive: Steam's roots come from the registry, each root's
``libraryfolders.vdf`` names the other libraries, and every library holding
``steamapps/common/FPSAimTrainer/FPSAimTrainer/stats`` is a hit.

The walk has two readers with different needs. Startup wants one answer and
takes the first hit; the settings page wants all of them, because a machine
carrying a stale second copy is exactly the case where the first hit is the
wrong one and the user has to pick.

The vdf is read with a flat ``"path"`` regex rather than a real parser -- the
same expression the installer used, and no new dependency for a file this app
reads exactly once. It matches the structured format Steam has written for
years; a pre-structured file simply yields no extra libraries, and the Steam
roots themselves are still probed. Every step is best-effort: a missing
registry key, an unreadable vdf, or a machine with no Steam at all is an
ordinary miss, never an error.

The bootstrap below is the only writer of a detected value, and it writes only
when the key has never been set -- a cleared value is the user saying "run
without run data" on the settings page, and re-detecting over it would undo the
one thing that page can say about it.
"""

import logging
import os
import re
import winreg
from pathlib import Path

from source.config.settings_service import (
    STATS_DIR_KEY,
    get_settings,
    get_settings_store_message,
    get_settings_store_state,
    save_settings,
)
from source.utilities.store_schema import StoreState, UnsupportedSchemaError

logger = logging.getLogger(__name__)

# Every place Steam records an install root, in the installer's order. All hits
# are collected rather than the first one taken: a machine can carry both a
# 32-bit and a 64-bit key, pointing at different installs.
_STEAM_ROOT_REGISTRY_VALUES = (
    (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
)

_LIBRARY_VDF_SUBPATH = Path("steamapps/libraryfolders.vdf")
_STATS_SUBPATH = Path("steamapps/common/FPSAimTrainer/FPSAimTrainer/stats")

_LIBRARY_PATH_PATTERN = re.compile(r'"path"\s*"([^"]*)"')


def _registry_value(hive: int, subkey: str, name: str) -> str | None:
    """Read one registry string, treating every absence as an ordinary miss."""
    try:
        with winreg.OpenKey(hive, subkey) as key:
            value, _value_type = winreg.QueryValueEx(key, name)
    except OSError:
        # No Steam, or only one of the two HKLM views: nothing to report.
        return None
    return value if isinstance(value, str) and value else None


def _steam_roots() -> list[str]:
    """Collect every Steam install root the registry knows about."""
    roots = []
    for hive, subkey, name in _STEAM_ROOT_REGISTRY_VALUES:
        root = _registry_value(hive, subkey, name)
        if root is not None:
            roots.append(root)
    return roots


def _libraries_in_vdf(root: str) -> list[str]:
    """Read one root's ``libraryfolders.vdf``, or nothing at all."""
    vdf_path = Path(root) / _LIBRARY_VDF_SUBPATH
    try:
        text = vdf_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        # A root with no vdf is normal -- the root itself is still a library.
        return []
    except OSError, UnicodeDecodeError:
        logger.warning("Could not read %s; skipping it.", vdf_path, exc_info=True)
        return []
    # The vdf escapes backslashes; the installer's regex unescaped them the
    # same way, and an unescaped path would not resolve.
    return [
        match.group(1).replace("\\\\", "\\")
        for match in _LIBRARY_PATH_PATTERN.finditer(text)
    ]


def _steam_libraries() -> list[str]:
    """List every Steam library on this machine, roots included.

    The roots come first and in registry order, so the probe below reaches the
    primary install before any secondary library -- a stale copy in a second
    library is the one case this detection can get wrong.
    """
    roots = _steam_roots()
    libraries = list(roots)
    for root in roots:
        libraries.extend(_libraries_in_vdf(root))
    return libraries


def detect_stats_dir_candidates() -> list[str]:
    """List every KovaaK's stats directory on this machine, likeliest first.

    Registry order, then each root's vdf order -- the same order the first-hit
    detector walks, so the head of this list is what startup would have chosen.
    """
    candidates = []
    seen = set()
    for library in _steam_libraries():
        # A root reached through the registry and again through its own vdf is
        # the same directory spelled two ways (slashes, case), so compare the
        # normalized form and probe each library once.
        key = os.path.normcase(os.path.normpath(library))
        if key in seen:
            continue
        seen.add(key)
        stats_dir = Path(library) / _STATS_SUBPATH
        if stats_dir.is_dir():
            candidates.append(str(stats_dir))
    return candidates


def detect_stats_dir() -> str | None:
    """Find the KovaaK's stats directory, or None when there is nothing to find."""
    candidates = detect_stats_dir_candidates()
    return candidates[0] if candidates else None


def bootstrap_stats_dir() -> None:
    """Detect and store the stats directory when it has never been configured.

    Called from server startup before the directory is pinned, so a first
    detection serves the boot that made it rather than the next one. A miss
    writes nothing and is retried on the next start: a dashboard installed
    before KovaaK's configures itself once KovaaK's appears.

    This is an automatic writer, so it never touches a settings file the app
    cannot use: an unusable or newer-stamped store reads as holding no keys,
    and writing over it would silently destroy an identity the user really did
    configure. It declines out loud and the boot continues without run data.
    """
    store_state = get_settings_store_state()
    if store_state in (StoreState.ERROR, StoreState.FUTURE):
        logger.warning(
            "Not detecting the KovaaK's stats directory, and not writing to the "
            "settings file: %s",
            get_settings_store_message(),
        )
        return
    settings = get_settings()
    if STATS_DIR_KEY in settings:
        return
    detected = detect_stats_dir()
    if detected is None:
        logger.info(
            "No KovaaK's stats directory found on this machine; set it on the "
            "settings page. Detection runs again on the next start."
        )
        return
    logger.info("Detected the KovaaK's stats directory: %s", detected)
    try:
        # Merged, never replaced: an identity may already be stored.
        save_settings({**settings, STATS_DIR_KEY: detected})
    except OSError:
        # The store is untouched (temp file plus atomic replace), so this boot
        # serves without run data and the next start detects again.
        logger.warning(
            "Could not store the detected stats directory; serving without it.",
            exc_info=True,
        )
    except UnsupportedSchemaError as exc:
        # Reachable despite the state check above: the check and the save take
        # the settings lock separately, so another writer can land between them.
        logger.warning(
            "Refused to store the detected stats directory; serving without it: %s",
            exc,
        )
