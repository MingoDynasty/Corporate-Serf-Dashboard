"""Finding the KovaaK's stats directory, and seeding it at startup.

No test reads the real registry: the registry layer is one function
(``_registry_value``) and every test replaces either it or the roots it
produces. Libraries are real temp directories, so the probe itself is the real
one.
"""

import json
import logging
from pathlib import Path

import pytest

from source.config import settings_service
from source.config import stats_dir_detection as detection

STATS_SUBPATH = Path("steamapps/common/FPSAimTrainer/FPSAimTrainer/stats")


def _library(path: Path, *, with_game: bool = True) -> Path:
    """Create a Steam library directory, optionally with KovaaK's installed."""
    path.mkdir(parents=True, exist_ok=True)
    if with_game:
        (path / STATS_SUBPATH).mkdir(parents=True, exist_ok=True)
    return path


def _write_structured_vdf(root: Path, libraries: list[Path]) -> None:
    """Write the per-library-object format Steam writes today."""
    blocks = "\n".join(
        f"""\t"{index}"
\t{{
\t\t"path"\t\t"{str(library).replace("\\", "\\\\")}"
\t\t"label"\t\t""
\t\t"apps"
\t\t{{
\t\t\t"720000"\t\t"12345"
\t\t}}
\t}}"""
        for index, library in enumerate(libraries)
    )
    vdf_path = root / "steamapps" / "libraryfolders.vdf"
    vdf_path.parent.mkdir(parents=True, exist_ok=True)
    vdf_path.write_text(f'"libraryfolders"\n{{\n{blocks}\n}}\n', encoding="utf-8")


@pytest.fixture
def roots(monkeypatch):
    """Let a test declare the Steam roots the registry would have reported."""

    def set_roots(*paths: Path) -> None:
        monkeypatch.setattr(detection, "_steam_roots", lambda: [str(p) for p in paths])

    return set_roots


def test_the_steam_root_itself_is_a_library(roots, tmp_path):
    """The common case: KovaaK's installed under the Steam install itself."""
    root = _library(tmp_path / "Steam")
    roots(root)

    assert detection.detect_stats_dir() == str(root / STATS_SUBPATH)


def test_a_second_library_named_by_the_vdf_is_found(roots, tmp_path):
    root = _library(tmp_path / "Steam", with_game=False)
    library = _library(tmp_path / "D" / "SteamLibrary")
    _write_structured_vdf(root, [root, library])
    roots(root)

    assert detection.detect_stats_dir() == str(library / STATS_SUBPATH)


def test_escaped_backslashes_in_the_vdf_are_unescaped(roots, tmp_path):
    """A path left escaped would not resolve to anything on disk."""
    root = _library(tmp_path / "Steam", with_game=False)
    library = _library(tmp_path / "D" / "SteamLibrary")
    vdf_path = root / "steamapps" / "libraryfolders.vdf"
    vdf_path.parent.mkdir(parents=True, exist_ok=True)
    escaped = str(library).replace("\\", "\\\\")
    vdf_path.write_text(f'\t"path"\t\t"{escaped}"\n', encoding="utf-8")
    assert "\\\\" in escaped  # the fixture is worthless if nothing was escaped
    roots(root)

    assert detection.detect_stats_dir() == str(library / STATS_SUBPATH)


def test_the_first_library_holding_the_game_wins(roots, tmp_path):
    """Roots first, then vdf order: a stale second copy must not shadow it."""
    root = _library(tmp_path / "Steam")
    stale = _library(tmp_path / "D" / "SteamLibrary")
    _write_structured_vdf(root, [stale])
    roots(root)

    assert detection.detect_stats_dir() == str(root / STATS_SUBPATH)


def test_a_library_reached_several_ways_is_probed_once(roots, tmp_path, monkeypatch):
    """One directory: two registry spellings, its own vdf, and a trailing slash."""
    root = _library(tmp_path / "Steam")
    _write_structured_vdf(root, [root, Path(f"{root}\\")])
    roots(root, Path(str(root).replace("\\", "/")))
    probed = []
    real_is_dir = Path.is_dir

    def counting_is_dir(self):
        probed.append(self)
        return real_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", counting_is_dir)

    assert detection.detect_stats_dir() == str(root / STATS_SUBPATH)
    assert len(probed) == 1


def test_no_steam_at_all_detects_nothing(roots):
    roots()

    assert detection.detect_stats_dir() is None


def test_steam_without_the_game_detects_nothing(roots, tmp_path):
    root = _library(tmp_path / "Steam", with_game=False)
    _write_structured_vdf(root, [_library(tmp_path / "Other", with_game=False)])
    roots(root)

    assert detection.detect_stats_dir() is None


def test_a_root_without_a_vdf_is_still_probed(roots, tmp_path):
    """A missing vdf is ordinary, not a failure worth logging."""
    root = _library(tmp_path / "Steam")
    roots(root)

    assert detection.detect_stats_dir() == str(root / STATS_SUBPATH)


def test_a_malformed_vdf_is_tolerated_and_warned(roots, tmp_path, caplog):
    root = _library(tmp_path / "Steam")
    # A directory where the file belongs: read_text raises an OSError subclass,
    # standing in for any unreadable vdf.
    (root / "steamapps" / "libraryfolders.vdf").mkdir(parents=True)
    roots(root)

    with caplog.at_level(logging.WARNING):
        assert detection.detect_stats_dir() == str(root / STATS_SUBPATH)

    assert "Could not read" in caplog.text


def test_a_vdf_holding_no_paths_contributes_no_libraries(roots, tmp_path):
    """Steam's pre-2021 numeric format has no ``path`` keys to harvest.

    The installer's regex behaved identically; the roots are still probed, so
    the practical loss is a secondary library on a Steam that has not written
    its library file since the format changed.
    """
    root = _library(tmp_path / "Steam", with_game=False)
    library = _library(tmp_path / "D" / "SteamLibrary")
    vdf_path = root / "steamapps" / "libraryfolders.vdf"
    vdf_path.parent.mkdir(parents=True, exist_ok=True)
    vdf_path.write_text(
        '"LibraryFolders"\n{\n\t"1"\t\t"%s"\n}\n' % str(library).replace("\\", "\\\\"),
        encoding="utf-8",
    )
    roots(root)

    assert detection.detect_stats_dir() is None


def test_every_library_holding_the_game_becomes_a_candidate(roots, tmp_path):
    """The settings page offers all of them; the order is the detector's."""
    root = _library(tmp_path / "Steam")
    stale = _library(tmp_path / "D" / "SteamLibrary")
    empty = _library(tmp_path / "E" / "SteamLibrary", with_game=False)
    _write_structured_vdf(root, [empty, stale])
    roots(root)

    assert detection.detect_stats_dir_candidates() == [
        str(root / STATS_SUBPATH),
        str(stale / STATS_SUBPATH),
    ]


def test_the_first_candidate_is_what_startup_detects(roots, tmp_path):
    """The contract the bootstrap and the pin depend on, pinned against drift."""
    root = _library(tmp_path / "Steam")
    _library(tmp_path / "D" / "SteamLibrary")
    _write_structured_vdf(root, [tmp_path / "D" / "SteamLibrary"])
    roots(root)

    assert detection.detect_stats_dir() == str(root / STATS_SUBPATH)
    assert detection.detect_stats_dir() == detection.detect_stats_dir_candidates()[0]


def test_one_library_reached_several_ways_is_one_candidate(roots, tmp_path):
    """Two registry spellings plus its own vdf must not triple the suggestions."""
    root = _library(tmp_path / "Steam")
    _write_structured_vdf(root, [root, Path(f"{root}\\")])
    roots(root, Path(str(root).replace("\\", "/")))

    assert detection.detect_stats_dir_candidates() == [str(root / STATS_SUBPATH)]


def test_a_single_library_yields_a_single_candidate(roots, tmp_path):
    root = _library(tmp_path / "Steam")
    roots(root)

    assert detection.detect_stats_dir_candidates() == [str(root / STATS_SUBPATH)]


def test_no_steam_at_all_yields_no_candidates(roots):
    roots()

    assert detection.detect_stats_dir_candidates() == []


def test_steam_without_the_game_yields_no_candidates(roots, tmp_path):
    root = _library(tmp_path / "Steam", with_game=False)
    _write_structured_vdf(root, [_library(tmp_path / "Other", with_game=False)])
    roots(root)

    assert detection.detect_stats_dir_candidates() == []


def test_every_registry_hit_becomes_a_root(monkeypatch):
    """Both HKLM views can name different installs; all of them are candidates."""
    found = {
        (r"Software\Valve\Steam", "SteamPath"): "C:/Steam",
        (r"SOFTWARE\Valve\Steam", "InstallPath"): "D:/Steam",
    }
    monkeypatch.setattr(
        detection,
        "_registry_value",
        lambda _hive, subkey, name: found.get((subkey, name)),
    )

    assert detection._steam_roots() == ["C:/Steam", "D:/Steam"]


def test_a_machine_without_steam_registry_keys_has_no_roots(monkeypatch):
    monkeypatch.setattr(
        detection,
        "_registry_value",
        lambda _hive, _subkey, _name: None,
    )

    assert detection._steam_roots() == []


@pytest.fixture
def detected(monkeypatch):
    """Let a test declare what detection finds, without any real detection."""

    def set_detected(path: Path | None) -> list[bool]:
        calls: list[bool] = []

        def detect():
            calls.append(True)
            return None if path is None else str(path)

        monkeypatch.setattr(detection, "detect_stats_dir", detect)
        return calls

    return set_detected


def test_an_absent_key_is_detected_and_stored(detected, tmp_path, caplog):
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})
    stats_dir = _library(tmp_path / "Steam") / STATS_SUBPATH
    detected(stats_dir)

    with caplog.at_level(logging.INFO):
        detection.bootstrap_stats_dir()

    # Merged, not replaced: the stored identity survives the bootstrap write.
    assert settings_service.get_settings() == {
        "kovaaks_username": "MingoDynasty",
        "stats_dir": str(stats_dir),
    }
    assert str(stats_dir) in caplog.text


def test_a_missing_settings_file_counts_as_an_absent_key(detected, tmp_path):
    stats_dir = _library(tmp_path / "Steam") / STATS_SUBPATH
    detected(stats_dir)
    settings_service.SETTINGS_FILE_PATH.unlink(missing_ok=True)
    settings_service.clear_settings_cache()

    detection.bootstrap_stats_dir()

    assert settings_service.get_settings() == {"stats_dir": str(stats_dir)}


def test_a_cleared_value_is_never_overridden(detected, tmp_path):
    """An empty value is the user saying "run without run data" on the page."""
    settings_service.save_settings({"stats_dir": ""})
    calls = detected(_library(tmp_path / "Steam") / STATS_SUBPATH)

    detection.bootstrap_stats_dir()

    assert settings_service.get_settings() == {"stats_dir": ""}
    assert calls == []


def test_a_configured_value_is_never_overridden(detected, tmp_path):
    configured = _library(tmp_path / "Configured")
    settings_service.save_settings({"stats_dir": str(configured)})
    calls = detected(_library(tmp_path / "Steam") / STATS_SUBPATH)

    detection.bootstrap_stats_dir()

    assert settings_service.get_settings() == {"stats_dir": str(configured)}
    assert calls == []


def test_detecting_nothing_writes_nothing(detected):
    settings_service.save_settings({})
    detected(None)

    detection.bootstrap_stats_dir()

    # No key: the next startup detects again, so KovaaK's installed later still
    # self-configures.
    assert settings_service.get_settings() == {}


def test_a_failed_write_leaves_the_store_alone(detected, monkeypatch, tmp_path, caplog):
    """An unwritable store must not stop the app from serving."""
    settings_service.save_settings({})
    detected(_library(tmp_path / "Steam") / STATS_SUBPATH)

    def refuse_to_write(_values):
        raise PermissionError("locked by another process")

    monkeypatch.setattr(detection, "save_settings", refuse_to_write)

    with caplog.at_level(logging.WARNING):
        detection.bootstrap_stats_dir()

    assert settings_service.get_settings() == {}
    assert "Could not store the detected stats directory" in caplog.text


def test_the_bootstrap_write_is_visible_to_the_boot_pin(detected, tmp_path):
    """Startup bootstraps before it pins, so a first detection serves this boot."""
    stats_dir = _library(tmp_path / "Steam") / STATS_SUBPATH
    detected(stats_dir)
    settings_service.save_settings({})
    settings_service.clear_stats_dir_pin()

    detection.bootstrap_stats_dir()
    settings_service.resolve_stats_dir()

    assert settings_service.get_usable_stats_dir() == str(stats_dir)
    assert json.loads(
        settings_service.SETTINGS_FILE_PATH.read_text(encoding="utf-8")
    ) == {"schema_version": 1, "stats_dir": str(stats_dir)}
