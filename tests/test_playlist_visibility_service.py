import json

import pytest

from source.kovaaks import playlist_visibility_service as visibility
from source.utilities import store_schema


def _use_tmp_visibility(monkeypatch, tmp_path, user_root_codes=frozenset()):
    visibility_path = tmp_path / "data" / "playlist_visibility.json"
    monkeypatch.setattr(visibility, "VISIBILITY_FILE_PATH", visibility_path)
    monkeypatch.setattr(
        visibility,
        "get_user_root_playlist_codes",
        lambda: set(user_root_codes),
    )
    visibility.clear_visibility_cache()
    return visibility_path


def _write_visibility(path, payload):
    """Write a well-formed v1 store: the stamp plus the given payload."""
    _write_raw_visibility(path, json.dumps({"schema_version": 1, **payload}))


def _write_raw_visibility(path, text):
    """Write whatever text the test wants, stamp included or not."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_missing_file_seeds_defaults_plus_user_root_without_writing(
    monkeypatch,
    tmp_path,
):
    visibility_path = _use_tmp_visibility(
        monkeypatch,
        tmp_path,
        user_root_codes={"UserCode"},
    )

    shown = visibility.get_shown_playlist_codes()

    assert shown == set(visibility.DEFAULT_VISIBLE_CODES) | {"UserCode"}
    # Reads never materialize the file; it appears on the first show/hide.
    assert not visibility_path.exists()


def test_hide_persists_across_cache_reset(monkeypatch, tmp_path):
    visibility_path = _use_tmp_visibility(monkeypatch, tmp_path)
    hidden_code = sorted(visibility.DEFAULT_VISIBLE_CODES)[0]

    visibility.hide_playlist(hidden_code)

    assert visibility_path.exists()
    visibility.clear_visibility_cache()
    assert not visibility.is_playlist_shown(hidden_code)
    assert visibility.get_shown_playlist_codes() == (
        set(visibility.DEFAULT_VISIBLE_CODES) - {hidden_code}
    )


def test_toggle_round_trips_and_reports_new_state(monkeypatch, tmp_path):
    _use_tmp_visibility(monkeypatch, tmp_path)
    code = sorted(visibility.DEFAULT_VISIBLE_CODES)[0]

    assert visibility.toggle_playlist_visibility(code) is False
    assert not visibility.is_playlist_shown(code)
    assert visibility.toggle_playlist_visibility(code) is True
    assert visibility.is_playlist_shown(code)


def test_empty_shown_list_is_authoritative_not_reseeded(monkeypatch, tmp_path):
    visibility_path = _use_tmp_visibility(
        monkeypatch,
        tmp_path,
        user_root_codes={"UserCode"},
    )
    _write_visibility(visibility_path, {"shown_playlists": []})

    assert visibility.get_shown_playlist_codes() == set()


def test_corrupt_file_falls_back_to_seed_and_recovers_on_write(
    monkeypatch,
    tmp_path,
):
    visibility_path = _use_tmp_visibility(monkeypatch, tmp_path)
    _write_raw_visibility(visibility_path, "not json")

    assert visibility.get_shown_playlist_codes() == set(
        visibility.DEFAULT_VISIBLE_CODES
    )

    code = sorted(visibility.DEFAULT_VISIBLE_CODES)[0]
    visibility.hide_playlist(code)
    payload = json.loads(visibility_path.read_text(encoding="utf-8"))

    assert payload["shown_playlists"] == sorted(
        set(visibility.DEFAULT_VISIBLE_CODES) - {code}
    )


def test_invalid_utf8_file_falls_back_to_seed(monkeypatch, tmp_path):
    visibility_path = _use_tmp_visibility(monkeypatch, tmp_path)
    visibility_path.parent.mkdir(parents=True, exist_ok=True)
    visibility_path.write_bytes(b"\xff\xfe\x00garbage")

    assert visibility.get_shown_playlist_codes() == set(
        visibility.DEFAULT_VISIBLE_CODES
    )


def test_non_list_shown_value_falls_back_to_seed(monkeypatch, tmp_path):
    visibility_path = _use_tmp_visibility(monkeypatch, tmp_path)
    _write_visibility(visibility_path, {"shown_playlists": "not-a-list"})

    assert visibility.get_shown_playlist_codes() == set(
        visibility.DEFAULT_VISIBLE_CODES
    )


def test_a_failed_write_propagates_and_leaves_the_cached_set_intact(
    monkeypatch,
    tmp_path,
):
    """The write-before-cache ordering is what makes a later retry correct.

    An antivirus lock exhausts the atomic replace's retries and re-raises. The
    service deliberately propagates that (its callers decide what to report),
    but it must not have already moved the in-memory set — otherwise the retry
    would see the new value, early-return, and never write.
    """
    _use_tmp_visibility(monkeypatch, tmp_path, user_root_codes={"UserCode"})
    before = visibility.get_shown_playlist_codes()

    def refuse_to_write(_shown):
        raise PermissionError("locked by another process")

    monkeypatch.setattr(visibility, "_write_shown_to_disk", refuse_to_write)

    with pytest.raises(PermissionError):
        visibility.show_playlist("NewCode")

    assert visibility.get_shown_playlist_codes() == before
    assert not visibility.is_playlist_shown("NewCode")


def test_visible_selector_options_filter_hidden_codes(monkeypatch):
    monkeypatch.setattr(
        visibility,
        "get_playlist_selector_options",
        lambda: [
            {"label": "Shown", "value": "ShownCode"},
            {"label": "Hidden", "value": "HiddenCode"},
        ],
    )
    monkeypatch.setattr(
        visibility,
        "get_shown_playlist_codes",
        lambda: {"ShownCode"},
    )

    assert visibility.get_visible_playlist_selector_options() == [
        {"label": "Shown", "value": "ShownCode"}
    ]


# --- schema_version: the four read states, and what writes may do in each ---


def _seed(user_root_codes=()):
    return set(visibility.DEFAULT_VISIBLE_CODES) | set(user_root_codes)


def test_a_stamped_write_round_trips(monkeypatch, tmp_path):
    visibility_path = _use_tmp_visibility(monkeypatch, tmp_path)
    hidden_code = sorted(visibility.DEFAULT_VISIBLE_CODES)[0]

    visibility.hide_playlist(hidden_code)

    payload = json.loads(visibility_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["shown_playlists"] == sorted(_seed() - {hidden_code})
    assert visibility.get_visibility_store_message() == ""


def test_an_unstamped_file_falls_back_to_the_seed_and_reports_it(
    monkeypatch,
    tmp_path,
):
    """No grandfather rule, and the fallback must not look like a first run."""
    visibility_path = _use_tmp_visibility(monkeypatch, tmp_path)
    _write_raw_visibility(
        visibility_path, json.dumps({"shown_playlists": ["KovaaKsSomething"]})
    )

    assert visibility.get_shown_playlist_codes() == _seed()
    assert '"schema_version": 1' in visibility.get_visibility_store_message()


@pytest.mark.parametrize(
    "marker",
    [True, "1", 0, -1],
    ids=["bool", "string", "zero", "negative"],
)
def test_a_marker_that_is_not_a_positive_integer_falls_back_to_the_seed(
    monkeypatch,
    tmp_path,
    marker,
):
    visibility_path = _use_tmp_visibility(monkeypatch, tmp_path)
    _write_raw_visibility(
        visibility_path, json.dumps({"schema_version": marker, "shown_playlists": []})
    )

    assert visibility.get_shown_playlist_codes() == _seed()
    # Not the future state: a show/hide must still be able to own the file.
    visibility.hide_playlist(sorted(visibility.DEFAULT_VISIBLE_CODES)[0])
    assert visibility.get_visibility_store_message() == ""


def test_a_newer_stamp_falls_back_to_the_seed_and_refuses_writes(
    monkeypatch,
    tmp_path,
):
    visibility_path = _use_tmp_visibility(monkeypatch, tmp_path)
    _write_raw_visibility(
        visibility_path, json.dumps({"schema_version": 2, "shown_playlists": []})
    )

    assert visibility.get_shown_playlist_codes() == _seed()
    assert "newer version of this app" in visibility.get_visibility_store_message()

    with pytest.raises(store_schema.UnsupportedSchemaError):
        visibility.hide_playlist(sorted(visibility.DEFAULT_VISIBLE_CODES)[0])
    with pytest.raises(store_schema.UnsupportedSchemaError):
        visibility.show_playlist("KovaaKsBrandNewCode")

    assert json.loads(visibility_path.read_text(encoding="utf-8")) == {
        "schema_version": 2,
        "shown_playlists": [],
    }


def test_an_unknown_key_under_a_supported_stamp_names_the_key(monkeypatch, tmp_path):
    visibility_path = _use_tmp_visibility(monkeypatch, tmp_path)
    _write_visibility(visibility_path, {"shown_playlists": [], "shown_playlist": []})

    assert visibility.get_shown_playlist_codes() == _seed()
    assert '"shown_playlist"' in visibility.get_visibility_store_message()


def test_an_error_state_read_never_touches_the_file(monkeypatch, tmp_path):
    visibility_path = _use_tmp_visibility(monkeypatch, tmp_path)
    _write_raw_visibility(visibility_path, "not json")

    assert visibility.get_shown_playlist_codes() == _seed()

    assert visibility_path.read_text(encoding="utf-8") == "not json"
    assert [path.name for path in visibility_path.parent.iterdir()] == [
        visibility_path.name
    ]


def test_a_show_over_an_error_state_file_backs_it_up_then_owns_it(
    monkeypatch,
    tmp_path,
):
    visibility_path = _use_tmp_visibility(monkeypatch, tmp_path)
    _write_raw_visibility(visibility_path, "not json")

    visibility.show_playlist("KovaaKsBrandNewCode")

    backup = visibility_path.parent / "playlist_visibility.json.corrupt-1.bak"
    assert backup.read_text(encoding="utf-8") == "not json"
    assert visibility.is_playlist_shown("KovaaKsBrandNewCode")
