import json

from source.kovaaks import playlist_visibility_service as visibility


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
    visibility_path.parent.mkdir(parents=True, exist_ok=True)
    visibility_path.write_text(
        json.dumps({"shown_playlists": []}),
        encoding="utf-8",
    )

    assert visibility.get_shown_playlist_codes() == set()


def test_corrupt_file_falls_back_to_seed_and_recovers_on_write(
    monkeypatch,
    tmp_path,
):
    visibility_path = _use_tmp_visibility(monkeypatch, tmp_path)
    visibility_path.parent.mkdir(parents=True, exist_ok=True)
    visibility_path.write_text("not json", encoding="utf-8")

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
    visibility_path.parent.mkdir(parents=True, exist_ok=True)
    visibility_path.write_text(
        json.dumps({"shown_playlists": "not-a-list"}),
        encoding="utf-8",
    )

    assert visibility.get_shown_playlist_codes() == set(
        visibility.DEFAULT_VISIBLE_CODES
    )


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
