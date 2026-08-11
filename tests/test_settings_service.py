import json
import logging

import pytest

from source.config import settings_service as settings
from source.utilities import atomic_write, store_schema


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
    """Write a well-formed v1 store: the stamp plus the given settings."""
    _write_raw(path, json.dumps({"schema_version": 1, **payload}))


def _write_raw(path, text):
    """Write whatever text the test wants, stamp included or not."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    _write_raw(settings_path, "")

    with caplog.at_level(logging.WARNING):
        assert settings.get_kovaaks_username() is None

    assert "is not valid JSON" in caplog.text


def test_malformed_json_is_tolerated_and_warned(settings_path, caplog):
    _write_raw(settings_path, "not json")

    with caplog.at_level(logging.WARNING):
        assert settings.get_settings() == {}

    assert "is not valid JSON" in caplog.text


def test_non_object_payload_is_tolerated(settings_path):
    _write_raw(settings_path, json.dumps(["kovaaks_username"]))

    assert settings.get_settings() == {}


def test_non_string_value_is_tolerated(settings_path):
    _write(settings_path, {"kovaaks_username": "MingoDynasty", "steam_id": 12345})

    assert settings.get_settings() == {}
    assert settings.get_kovaaks_username() is None


def test_hand_written_file_with_a_utf8_bom_is_read(settings_path):
    """Windows editors write a BOM; json.loads rejects one outright."""
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_bytes(
        b"\xef\xbb\xbf"
        + json.dumps({"schema_version": 1, "kovaaks_username": "MingoDynasty"}).encode()
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
        "schema_version": 1,
        "kovaaks_username": "MingoDynasty",
        "steam_id": "",
    }


def test_save_replaces_the_file_whole_and_leaves_no_temp_files(settings_path):
    _write(settings_path, {"kovaaks_username": "Old"})
    settings.clear_settings_cache()

    settings.save_settings({"kovaaks_username": "New"})

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "kovaaks_username": "New",
    }
    assert [path.name for path in settings_path.parent.iterdir()] == [
        settings_path.name
    ]


def test_save_recovers_from_a_malformed_file(settings_path):
    _write_raw(settings_path, "not json")
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


def test_only_a_stats_directory_change_is_a_stats_directory_change(
    settings_path,
    tmp_path,
):
    """The narrow helper must ignore the identity half of the aggregate."""
    booted = tmp_path / "booted"
    booted.mkdir()
    settings.save_settings({"stats_dir": str(booted), "kovaaks_username": "First"})
    settings.resolve_stats_dir()
    settings.get_identity()

    settings.save_settings({"stats_dir": str(booted), "kovaaks_username": "Second"})

    assert settings.is_restart_pending() is True
    assert settings.is_stats_dir_change_pending() is False

    moved = tmp_path / "moved"
    moved.mkdir()
    settings.save_settings({"stats_dir": str(moved), "kovaaks_username": "Second"})

    assert settings.is_stats_dir_change_pending() is True


def test_a_first_time_identity_set_is_not_pending(settings_path):
    """The live-apply path: nothing has consumed the old, unset identity."""
    settings.save_settings({})
    settings.resolve_stats_dir()
    settings.get_identity()

    settings.save_settings({"kovaaks_username": "First", "steam_id": "111"})

    assert settings.is_restart_pending() is False


# --- schema_version: the four read states, and what writes may do in each ---


def test_a_supported_stamp_never_leaks_into_the_domain_values(settings_path):
    """The stamp is storage, not a setting: nothing downstream should see it."""
    _write(settings_path, {"kovaaks_username": "MingoDynasty"})

    assert settings.get_settings() == {"kovaaks_username": "MingoDynasty"}
    assert settings.get_settings_store_state() is store_schema.StoreState.SUPPORTED
    assert settings.get_settings_store_message() == ""


def test_the_stamp_is_written_first_and_the_rest_stays_sorted(settings_path):
    """Every durable store leads with its format marker, this one included.

    ``sort_keys=True`` would sort the marker into the middle of the settings
    (``kovaaks_username`` precedes it alphabetically), so the keys are sorted
    before the stamp is added rather than by the serializer.
    """
    settings.save_settings(
        {
            "steam_id": "76561197986713986",
            "kovaaks_username": "MingoDynasty",
            "stats_dir": "S:/stats",
        }
    )

    written = json.loads(settings_path.read_text(encoding="utf-8"))

    assert list(written) == [
        "schema_version",
        "kovaaks_username",
        "stats_dir",
        "steam_id",
    ]


def test_a_missing_file_is_its_own_state_not_an_error(settings_path):
    assert settings.get_settings_store_state() is store_schema.StoreState.MISSING
    assert settings.get_settings_store_message() == ""


def test_an_unstamped_file_is_an_error_state_naming_the_fix(settings_path):
    """No grandfather rule: a well-formed legacy file is not implicitly v1."""
    _write_raw(settings_path, json.dumps({"kovaaks_username": "MingoDynasty"}))

    assert settings.get_settings() == {}
    assert settings.get_settings_store_state() is store_schema.StoreState.ERROR
    assert '"schema_version": 1' in settings.get_settings_store_message()


@pytest.mark.parametrize(
    "marker",
    [True, "1", 1.0, None, 0, -1],
    ids=["bool", "string", "float", "null", "zero", "negative"],
)
def test_a_marker_that_is_not_a_positive_integer_is_an_error_state(
    settings_path,
    marker,
):
    """Including 0 and negatives: garbage is not the future, or writes strand."""
    _write_raw(
        settings_path,
        json.dumps({"schema_version": marker, "kovaaks_username": "MingoDynasty"}),
    )

    assert settings.get_settings() == {}
    assert settings.get_settings_store_state() is store_schema.StoreState.ERROR


def test_a_newer_stamp_is_the_future_state(settings_path):
    _write_raw(
        settings_path,
        json.dumps({"schema_version": 2, "kovaaks_username": "MingoDynasty"}),
    )

    assert settings.get_settings() == {}
    assert settings.get_settings_store_state() is store_schema.StoreState.FUTURE
    assert "newer version of this app" in settings.get_settings_store_message()


def test_a_supported_stamp_does_not_vouch_for_the_payload(settings_path):
    _write(settings_path, {"kovaaks_username": 12345})

    assert settings.get_settings() == {}
    assert settings.get_settings_store_state() is store_schema.StoreState.ERROR


def test_an_unknown_key_under_a_supported_stamp_is_an_error_naming_the_key(
    settings_path,
):
    """Within a version the key set is fixed, so a stray key is a hand-edit typo."""
    _write(settings_path, {"kovaaks_username": "MingoDynasty", "kovaaks_usernam": "x"})

    assert settings.get_settings() == {}
    assert '"kovaaks_usernam"' in settings.get_settings_store_message()


def test_an_error_state_read_never_touches_the_file(settings_path):
    _write_raw(settings_path, "not json")

    assert settings.get_settings() == {}

    assert settings_path.read_text(encoding="utf-8") == "not json"
    assert [path.name for path in settings_path.parent.iterdir()] == [
        settings_path.name
    ]


def test_a_save_over_an_error_state_file_backs_it_up_then_owns_it(settings_path):
    """Self-service recovery: the settings page can always rewrite the store."""
    _write_raw(settings_path, "not json")

    settings.save_settings({"kovaaks_username": "MingoDynasty"})

    assert settings.get_settings() == {"kovaaks_username": "MingoDynasty"}
    backups = sorted(settings_path.parent.glob("*.bak"))
    assert [path.name for path in backups] == ["settings.json.corrupt-1.bak"]
    assert backups[0].read_text(encoding="utf-8") == "not json"


def test_a_save_before_any_read_still_backs_up_an_error_state_file(settings_path):
    """The guard has to read for itself; a writer may be the first caller."""
    _write_raw(settings_path, "not json")
    settings.clear_settings_cache()

    settings.save_settings({"steam_id": "76561197986713986"})

    assert (settings_path.parent / "settings.json.corrupt-1.bak").exists()


def test_a_backup_never_replaces_an_earlier_backup(settings_path):
    _write_raw(settings_path, "first corruption")
    settings.save_settings({"kovaaks_username": "First"})
    _write_raw(settings_path, "second corruption")
    settings.clear_settings_cache()

    settings.save_settings({"kovaaks_username": "Second"})

    directory = settings_path.parent
    assert (directory / "settings.json.corrupt-1.bak").read_text(
        encoding="utf-8"
    ) == "first corruption"
    assert (directory / "settings.json.corrupt-2.bak").read_text(
        encoding="utf-8"
    ) == "second corruption"


def test_a_failed_replace_after_a_backup_leaves_the_original_in_place(
    settings_path,
    monkeypatch,
):
    """A copy, not a move: the incumbent survives a write that never lands."""
    _write_raw(settings_path, "not json")

    def failing_replace(_source, _destination):
        raise PermissionError("locked by another process")

    monkeypatch.setattr(atomic_write.os, "replace", failing_replace)
    monkeypatch.setattr(atomic_write.time, "sleep", lambda _delay: None)

    with pytest.raises(PermissionError):
        settings.save_settings({"kovaaks_username": "MingoDynasty"})

    assert settings_path.read_text(encoding="utf-8") == "not json"
    assert (settings_path.parent / "settings.json.corrupt-1.bak").exists()
    assert not list(settings_path.parent.glob(".*.tmp"))


def test_a_write_is_refused_when_the_incumbent_cannot_be_copied_aside(
    settings_path,
    monkeypatch,
):
    _write_raw(settings_path, "not json")

    def refuse_to_copy(_path):
        raise PermissionError("cannot read the incumbent")

    monkeypatch.setattr(settings, "back_up_unusable_store", refuse_to_copy)

    with pytest.raises(PermissionError):
        settings.save_settings({"kovaaks_username": "MingoDynasty"})

    assert settings_path.read_text(encoding="utf-8") == "not json"


def test_a_future_state_file_refuses_every_save(settings_path):
    _write_raw(
        settings_path,
        json.dumps({"schema_version": 2, "kovaaks_username": "FromTheFuture"}),
    )

    with pytest.raises(store_schema.UnsupportedSchemaError):
        settings.save_settings({"kovaaks_username": "MingoDynasty"})

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 2,
        "kovaaks_username": "FromTheFuture",
    }
    assert not list(settings_path.parent.glob("*.bak"))


def test_a_save_before_any_read_still_refuses_a_future_state_file(settings_path):
    _write_raw(settings_path, json.dumps({"schema_version": 2}))
    settings.clear_settings_cache()

    with pytest.raises(store_schema.UnsupportedSchemaError):
        settings.save_settings({"kovaaks_username": "MingoDynasty"})


def test_declining_identity_records_an_empty_username(settings_path):
    settings.save_settings({})

    settings.decline_identity()

    assert settings.get_settings() == {"kovaaks_username": ""}
    assert settings.get_kovaaks_username() is None
    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "kovaaks_username": "",
    }


def test_declining_identity_leaves_an_absent_stats_directory_absent(settings_path):
    """The bootstrap has to keep looking on later boots, so it stays unwritten."""
    settings.save_settings({"steam_id": "111"})

    settings.decline_identity()

    assert settings.get_settings() == {"kovaaks_username": "", "steam_id": "111"}


def test_declining_identity_preserves_a_save_made_since_the_page_rendered(
    settings_path,
    tmp_path,
):
    """The decline re-reads under the lock instead of trusting a stale view."""
    settings.save_settings({"stats_dir": "old-directory"})
    # What a card render read, moments before the user clicked Skip.
    stale = settings.get_settings()
    settings.save_settings(
        {"stats_dir": str(tmp_path), "steam_id": "111", "kovaaks_username": ""}
    )

    settings.decline_identity()

    assert settings.get_settings() == {
        "stats_dir": str(tmp_path),
        "steam_id": "111",
        "kovaaks_username": "",
    }
    assert stale["stats_dir"] == "old-directory"


@pytest.mark.parametrize("saved", ["MingoDynasty", ""])
def test_declining_identity_never_overwrites_an_answered_question(
    settings_path,
    saved,
):
    """A stale tab's Skip must not discard a username saved from another one."""
    settings.save_settings({"stats_dir": "somewhere"})
    # What the card render read, before the other tab saved.
    settings.get_settings()
    settings.save_settings({"stats_dir": "somewhere", "kovaaks_username": saved})

    settings.decline_identity()

    assert settings.get_settings() == {
        "stats_dir": "somewhere",
        "kovaaks_username": saved,
    }


def test_declining_identity_does_not_disturb_the_replace_all_save(settings_path):
    """Save keeps its contract: the next one still writes the file whole."""
    settings.save_settings({"stats_dir": "somewhere", "steam_id": "111"})
    settings.decline_identity()

    settings.save_settings({"kovaaks_username": "First"})

    assert settings.get_settings() == {"kovaaks_username": "First"}


def test_declining_identity_takes_the_same_write_guard_as_a_save(settings_path):
    """The decline is user-initiated, so it owns an unusable file too."""
    _write_raw(settings_path, "not json")

    settings.decline_identity()

    backup = settings_path.parent / "settings.json.corrupt-1.bak"
    assert backup.read_text(encoding="utf-8") == "not json"
    assert settings.get_settings() == {"kovaaks_username": ""}


def test_a_newer_store_refuses_the_decline_and_keeps_its_bytes(settings_path):
    """A second writer must not be a hole in the newer-schema refusal."""
    stored = json.dumps({"schema_version": 2, "kovaaks_username": "FromTheFuture"})
    _write_raw(settings_path, stored)

    with pytest.raises(store_schema.UnsupportedSchemaError):
        settings.decline_identity()

    assert settings_path.read_text(encoding="utf-8") == stored
    assert not list(settings_path.parent.glob("*.bak"))
