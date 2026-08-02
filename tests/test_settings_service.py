import json
import logging

import pytest

from source.config import settings_service as settings


@pytest.fixture
def settings_path(monkeypatch, tmp_path):
    """Point the store at a temp file and start from a cold cache and pin."""
    path = tmp_path / "data" / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_FILE_PATH", path)
    settings.clear_settings_cache()
    settings.clear_stats_dir_pin()
    settings.clear_identity_pin()
    return path


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_missing_file_leaves_every_setting_unset(settings_path):
    assert settings.get_settings() == {}
    assert settings.get_kovaaks_username() is None
    assert settings.get_steam_id() is None
    # Reads never materialize the file; it appears on the first save.
    assert not settings_path.exists()


def test_stored_identity_is_returned(settings_path):
    _write(
        settings_path,
        {"kovaaks_username": "MingoDynasty", "steam_id": "76561197986713986"},
    )

    assert settings.get_kovaaks_username() == "MingoDynasty"
    assert settings.get_steam_id() == "76561197986713986"


def test_empty_values_read_the_same_as_absent_keys(settings_path):
    _write(settings_path, {"kovaaks_username": "", "steam_id": ""})

    assert settings.get_kovaaks_username() is None
    assert settings.get_steam_id() is None


def test_empty_file_is_tolerated_and_warned(settings_path, caplog):
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text("", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        assert settings.get_kovaaks_username() is None

    assert "Invalid settings file" in caplog.text


def test_malformed_json_is_tolerated_and_warned(settings_path, caplog):
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text("not json", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        assert settings.get_settings() == {}

    assert "Invalid settings file" in caplog.text


def test_non_object_payload_is_tolerated(settings_path):
    _write(settings_path, ["kovaaks_username"])

    assert settings.get_settings() == {}


def test_non_string_value_is_tolerated(settings_path):
    _write(settings_path, {"kovaaks_username": "MingoDynasty", "steam_id": 12345})

    assert settings.get_settings() == {}
    assert settings.get_kovaaks_username() is None


def test_hand_written_file_with_a_utf8_bom_is_read(settings_path):
    """Windows editors write a BOM; json.loads rejects one outright."""
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_bytes(
        b"\xef\xbb\xbf" + json.dumps({"kovaaks_username": "MingoDynasty"}).encode()
    )

    assert settings.get_kovaaks_username() == "MingoDynasty"


def test_invalid_utf8_file_is_tolerated_and_warned(settings_path, caplog):
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_bytes(b"\xff\xfe\x00garbage")

    with caplog.at_level(logging.WARNING):
        assert settings.get_settings() == {}

    assert "Failed to read" in caplog.text


def test_unreadable_path_is_tolerated_and_warned(settings_path, caplog):
    # A directory where the file belongs: read_text raises an OSError subclass
    # on every platform, standing in for any unreadable file.
    settings_path.mkdir(parents=True, exist_ok=True)

    with caplog.at_level(logging.WARNING):
        assert settings.get_settings() == {}

    assert "Failed to read" in caplog.text


def test_save_round_trips_across_a_cache_reset(settings_path):
    settings.save_settings({"kovaaks_username": "MingoDynasty", "steam_id": ""})

    # The stored view, not the pinned accessors: this is about the file and the
    # cache, and a pinned identity would answer without reading either.
    assert settings.get_settings()["kovaaks_username"] == "MingoDynasty"
    settings.clear_settings_cache()
    assert settings.get_settings()["kovaaks_username"] == "MingoDynasty"
    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "kovaaks_username": "MingoDynasty",
        "steam_id": "",
    }


def test_save_replaces_the_file_whole_and_leaves_no_temp_files(settings_path):
    _write(settings_path, {"kovaaks_username": "Old", "retired_key": "value"})
    settings.clear_settings_cache()

    settings.save_settings({"kovaaks_username": "New"})

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "kovaaks_username": "New"
    }
    assert [path.name for path in settings_path.parent.iterdir()] == [
        settings_path.name
    ]


def test_save_recovers_from_a_malformed_file(settings_path):
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text("not json", encoding="utf-8")
    settings.clear_settings_cache()

    settings.save_settings({"steam_id": "76561197986713986"})

    assert settings.get_steam_id() == "76561197986713986"


def test_reads_are_cached_until_the_cache_is_cleared(settings_path):
    _write(settings_path, {"kovaaks_username": "First"})

    # Through the stored view, so the identity pin cannot mask the cache.
    assert settings.get_settings()["kovaaks_username"] == "First"
    _write(settings_path, {"kovaaks_username": "Second"})
    assert settings.get_settings()["kovaaks_username"] == "First"

    settings.clear_settings_cache()
    assert settings.get_settings()["kovaaks_username"] == "Second"


def test_get_identity_pairs_both_fields_from_one_read(settings_path):
    _write(settings_path, {"kovaaks_username": "MingoDynasty", "steam_id": "765611"})

    assert settings.get_identity() == ("MingoDynasty", "765611")


def test_get_identity_collapses_empty_values_like_the_single_getters(settings_path):
    _write(settings_path, {"kovaaks_username": "MingoDynasty", "steam_id": ""})

    assert settings.get_identity() == ("MingoDynasty", None)
    assert settings.get_identity() == (
        settings.get_kovaaks_username(),
        settings.get_steam_id(),
    )


def test_get_identity_cannot_straddle_a_concurrent_save(settings_path, monkeypatch):
    """Both fields must come from one settings version, never a mix of two."""
    settings.save_settings({"kovaaks_username": "First", "steam_id": "111"})
    real_get_settings = settings.get_settings
    reads = []

    def get_settings_then_save():
        """Stand in for a save landing between two separate getter calls."""
        result = real_get_settings()
        reads.append(result)
        settings.save_settings({"kovaaks_username": "Second", "steam_id": "222"})
        return result

    monkeypatch.setattr(settings, "get_settings", get_settings_then_save)

    assert settings.get_identity() == ("First", "111")
    assert len(reads) == 1


def test_callers_cannot_mutate_the_cache_through_get_settings(settings_path):
    _write(settings_path, {"kovaaks_username": "MingoDynasty"})

    settings.get_settings()["kovaaks_username"] = "Tampered"

    assert settings.get_kovaaks_username() == "MingoDynasty"


def test_unresolved_pin_reads_as_no_stats_directory(settings_path, tmp_path):
    """A startup that never pinned one (tests, imports) reads as unconfigured."""
    _write(settings_path, {"stats_dir": str(tmp_path)})

    assert settings.get_usable_stats_dir() is None


def test_resolved_pin_returns_the_stored_directory(settings_path, tmp_path):
    _write(settings_path, {"stats_dir": str(tmp_path)})

    assert settings.resolve_stats_dir() == str(tmp_path)
    assert settings.get_usable_stats_dir() == str(tmp_path)


@pytest.mark.parametrize(
    "stored",
    [None, "", "no-such-directory"],
    ids=["absent", "empty", "missing-directory"],
)
def test_unusable_values_all_read_as_no_stats_directory(settings_path, stored):
    _write(settings_path, {} if stored is None else {"stats_dir": stored})

    settings.resolve_stats_dir()

    assert settings.get_usable_stats_dir() is None


def test_a_missing_directory_is_still_pinned_for_the_startup_message(settings_path):
    """The log line names what was configured, so the raw value must survive."""
    _write(settings_path, {"stats_dir": "no-such-directory"})

    assert settings.resolve_stats_dir() == "no-such-directory"
    assert settings.get_usable_stats_dir() is None


def test_a_directory_appearing_after_resolution_stays_unusable(
    settings_path,
    tmp_path,
):
    """Startup already skipped the scan and the watchdog for this directory."""
    late = tmp_path / "late"
    _write(settings_path, {"stats_dir": str(late)})
    settings.resolve_stats_dir()

    late.mkdir()

    assert settings.get_usable_stats_dir() is None


def test_a_save_after_resolution_does_not_move_the_pin(settings_path, tmp_path):
    """Consumers read the boot pin, never the store: the value is restart-scoped."""
    booted = tmp_path / "booted"
    booted.mkdir()
    _write(settings_path, {"stats_dir": str(booted)})
    settings.resolve_stats_dir()

    moved = tmp_path / "moved"
    moved.mkdir()
    settings.save_settings({"stats_dir": str(moved)})

    assert settings.get_usable_stats_dir() == str(booted)


def test_identity_reads_stay_live_while_no_username_is_configured(settings_path):
    """Unset stays live: that is what makes the first-time set apply at once."""
    _write(settings_path, {"steam_id": "111"})

    assert settings.get_identity() == (None, "111")

    settings.save_settings({"kovaaks_username": "MingoDynasty", "steam_id": "222"})

    assert settings.get_identity() == ("MingoDynasty", "222")


def test_the_first_configured_read_freezes_both_values_together(settings_path):
    settings.save_settings({"kovaaks_username": "First", "steam_id": "111"})

    assert settings.get_identity() == ("First", "111")

    settings.save_settings({"kovaaks_username": "Second", "steam_id": "222"})

    assert settings.get_identity() == ("First", "111")
    assert settings.get_kovaaks_username() == "First"
    assert settings.get_steam_id() == "111"


def test_a_single_getter_freezes_the_pair_as_a_whole(settings_path):
    """Any accessor is a read: the Steam ID cannot be pinned on its own."""
    settings.save_settings({"kovaaks_username": "First", "steam_id": "111"})

    assert settings.get_steam_id() == "111"

    settings.save_settings({"kovaaks_username": "Second", "steam_id": "222"})

    assert settings.get_kovaaks_username() == "First"


def test_clearing_the_identity_pin_makes_reads_live_again(settings_path):
    settings.save_settings({"kovaaks_username": "First", "steam_id": "111"})
    assert settings.get_identity() == ("First", "111")
    settings.save_settings({"kovaaks_username": "Second", "steam_id": "222"})

    settings.clear_identity_pin()

    assert settings.get_identity() == ("Second", "222")


@pytest.mark.parametrize(
    "stored",
    [{}, {"kovaaks_username": "", "steam_id": ""}],
    ids=["absent", "empty"],
)
def test_absent_and_empty_identity_both_read_as_unset(settings_path, stored):
    _write(settings_path, stored)

    assert settings.get_identity() == (None, None)
    assert settings.get_kovaaks_username() is None
    assert settings.get_steam_id() is None


def test_nothing_is_pending_while_the_store_matches_both_pins(settings_path, tmp_path):
    booted = tmp_path / "booted"
    booted.mkdir()
    settings.save_settings(
        {"stats_dir": str(booted), "kovaaks_username": "First", "steam_id": "111"}
    )
    settings.resolve_stats_dir()
    settings.get_identity()

    assert settings.is_restart_pending() is False


def test_a_stats_directory_change_is_pending(settings_path, tmp_path):
    booted = tmp_path / "booted"
    booted.mkdir()
    settings.save_settings({"stats_dir": str(booted)})
    settings.resolve_stats_dir()

    moved = tmp_path / "moved"
    moved.mkdir()
    settings.save_settings({"stats_dir": str(moved)})

    assert settings.is_restart_pending() is True


def test_clearing_the_stats_directory_is_pending(settings_path, tmp_path):
    """Cleared is a change like any other: the pin still points at the old one."""
    booted = tmp_path / "booted"
    booted.mkdir()
    settings.save_settings({"stats_dir": str(booted)})
    settings.resolve_stats_dir()

    settings.save_settings({"stats_dir": ""})

    assert settings.is_restart_pending() is True


@pytest.mark.parametrize(
    "saved",
    [
        {"kovaaks_username": "Second", "steam_id": "111"},
        {"kovaaks_username": "First", "steam_id": "222"},
        {"kovaaks_username": "", "steam_id": ""},
    ],
    ids=["username", "steam-id", "cleared"],
)
def test_changing_a_frozen_identity_is_pending(settings_path, saved):
    settings.save_settings({"kovaaks_username": "First", "steam_id": "111"})
    settings.get_identity()

    settings.save_settings(saved)

    assert settings.is_restart_pending() is True


def test_a_first_time_identity_set_is_not_pending(settings_path):
    """The live-apply path: nothing has consumed the old, unset identity."""
    settings.save_settings({})
    settings.resolve_stats_dir()
    settings.get_identity()

    settings.save_settings({"kovaaks_username": "First", "steam_id": "111"})

    assert settings.is_restart_pending() is False
