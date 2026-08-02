import json
import logging

import pytest

from source.config import settings_service as settings


@pytest.fixture
def settings_path(monkeypatch, tmp_path):
    """Point the store at a temp file and start from a cold cache."""
    path = tmp_path / "data" / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_FILE_PATH", path)
    settings.clear_settings_cache()
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

    assert settings.get_kovaaks_username() == "MingoDynasty"
    settings.clear_settings_cache()
    assert settings.get_kovaaks_username() == "MingoDynasty"
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

    assert settings.get_kovaaks_username() == "First"
    _write(settings_path, {"kovaaks_username": "Second"})
    assert settings.get_kovaaks_username() == "First"

    settings.clear_settings_cache()
    assert settings.get_kovaaks_username() == "Second"


def test_callers_cannot_mutate_the_cache_through_get_settings(settings_path):
    _write(settings_path, {"kovaaks_username": "MingoDynasty"})

    settings.get_settings()["kovaaks_username"] = "Tampered"

    assert settings.get_kovaaks_username() == "MingoDynasty"
