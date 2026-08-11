"""The one-time conversion script that stamps the pre-stamp store population.

The script is the deployment story for the release that introduced
``schema_version``: it runs once, against a closed app, on a machine that has
already been updated. What it must never do is as important as what it does, so
the branches that *decline* carry as much weight here as the one that writes.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from source.kovaaks.data_models import PlaylistData, Rank, Scenario

SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent / "scripts" / "stamp_schema_version.py"
)


def _load_script():
    """Import the script by path; ``scripts/`` is not an importable package."""
    spec = importlib.util.spec_from_file_location("stamp_schema_version", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = _load_script()


def _playlist(name="User", code="UserCode") -> PlaylistData:
    return PlaylistData(
        name=name,
        code=code,
        scenarios=[
            Scenario(
                name="Scenario",
                ranks=[Rank(name="Bronze", color="#a97142", threshold=100)],
            )
        ],
    )


@pytest.fixture
def store_root(monkeypatch, tmp_path):
    """Point every store the script converts at a temp tree."""
    data = tmp_path / "data"
    playlists = data / "playlists"
    playlists.mkdir(parents=True)
    monkeypatch.setattr(script, "SETTINGS_FILE_PATH", data / "settings.json")
    monkeypatch.setattr(
        script, "VISIBILITY_FILE_PATH", data / "playlist_visibility.json"
    )
    monkeypatch.setattr(script, "USER_PLAYLIST_DIRECTORY_PATH", playlists)
    return data


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_missing_stores_are_not_an_error(store_root):
    report = script.run()

    assert (report.stamped, report.already_stamped, report.skipped) == ([], [], [])
    assert not (store_root / "settings.json").exists()


def test_every_store_type_is_stamped_in_one_pass(store_root):
    _write(
        store_root / "settings.json",
        json.dumps({"stats_dir": "S:/stats", "kovaaks_username": "MingoDynasty"}),
    )
    _write(
        store_root / "playlist_visibility.json",
        json.dumps({"shown_playlists": ["KovaaKsSomething"]}),
    )
    playlist_file = store_root / "playlists" / "user.json"
    _write(playlist_file, _playlist().model_dump_json(indent=2, exclude_none=True))

    report = script.run()

    assert report.skipped == []
    assert len(report.stamped) == 3
    assert _read(store_root / "settings.json") == {
        "schema_version": 1,
        "stats_dir": "S:/stats",
        "kovaaks_username": "MingoDynasty",
    }
    assert _read(store_root / "playlist_visibility.json") == {
        "schema_version": 1,
        "shown_playlists": ["KovaaKsSomething"],
    }
    stamped_playlist = _read(playlist_file)
    assert stamped_playlist["schema_version"] == 1
    assert PlaylistData.model_validate(stamped_playlist) == _playlist()


def test_a_second_run_changes_nothing(store_root):
    settings_path = store_root / "settings.json"
    _write(settings_path, json.dumps({"kovaaks_username": "MingoDynasty"}))
    script.run()
    after_first = settings_path.read_text(encoding="utf-8")

    report = script.run()

    assert report.stamped == []
    assert report.already_stamped == [settings_path]
    assert settings_path.read_text(encoding="utf-8") == after_first


def test_a_newer_stamped_file_is_never_downgraded(store_root):
    """The whole reason the stamp check is exact rather than "parses as v1".

    Pydantic ignores extra fields, so a v2 playlist would very likely still
    satisfy v1 -- and a re-run years from now would quietly rewrite it.
    """
    playlist_file = store_root / "playlists" / "future.json"
    envelope = json.loads(_playlist().model_dump_json(exclude_none=True))
    original = json.dumps({"schema_version": 2, **envelope, "new_field": "kept"})
    _write(playlist_file, original)

    report = script.run()

    assert report.stamped == []
    assert [path for path, _reason in report.skipped] == [playlist_file]
    assert playlist_file.read_text(encoding="utf-8") == original


@pytest.mark.parametrize(
    "marker",
    [True, "1", 0, -1, None],
    ids=["bool", "string", "zero", "negative", "null"],
)
def test_a_malformed_or_non_positive_stamp_is_preserved_and_reported(
    store_root,
    marker,
):
    visibility_path = store_root / "playlist_visibility.json"
    original = json.dumps({"schema_version": marker, "shown_playlists": []})
    _write(visibility_path, original)

    report = script.run()

    assert [path for path, _reason in report.skipped] == [visibility_path]
    assert visibility_path.read_text(encoding="utf-8") == original


def test_an_unstamped_file_with_an_invalid_payload_is_preserved_and_reported(
    store_root,
):
    settings_path = store_root / "settings.json"
    original = json.dumps({"kovaaks_usernam": "typo"})
    _write(settings_path, original)

    report = script.run()

    assert report.stamped == []
    (path, reason) = report.skipped[0]
    assert path == settings_path
    assert '"kovaaks_usernam"' in reason
    assert settings_path.read_text(encoding="utf-8") == original


def test_a_stamped_file_with_an_invalid_payload_is_preserved_and_reported(store_root):
    settings_path = store_root / "settings.json"
    original = json.dumps({"schema_version": 1, "stats_dir": 5})
    _write(settings_path, original)

    report = script.run()

    assert report.already_stamped == []
    assert [path for path, _reason in report.skipped] == [settings_path]
    assert settings_path.read_text(encoding="utf-8") == original


def test_malformed_json_is_preserved_and_reported(store_root):
    settings_path = store_root / "settings.json"
    _write(settings_path, "not json")

    report = script.run()

    assert [path for path, _reason in report.skipped] == [settings_path]
    assert settings_path.read_text(encoding="utf-8") == "not json"


def test_a_legacy_settings_bom_is_accepted_and_rewritten_without_one(store_root):
    """utf-8-sig is the settings reader's contract, so a BOM is valid input."""
    settings_path = store_root / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_bytes(
        b"\xef\xbb\xbf" + json.dumps({"kovaaks_username": "MingoDynasty"}).encode()
    )

    report = script.run()

    assert report.stamped == [settings_path]
    raw = settings_path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert json.loads(raw.decode("utf-8")) == {
        "schema_version": 1,
        "kovaaks_username": "MingoDynasty",
    }


@pytest.mark.parametrize(
    "store",
    ["playlist_visibility.json", "playlists/user.json"],
    ids=["visibility", "playlist"],
)
def test_a_bom_on_a_machine_written_store_is_preserved_and_reported(store_root, store):
    """Those two are plain UTF-8, where a BOM is corruption rather than legacy."""
    path = store_root / store
    path.parent.mkdir(parents=True, exist_ok=True)
    original = b"\xef\xbb\xbf" + json.dumps({"shown_playlists": []}).encode()
    path.write_bytes(original)

    report = script.run()

    assert report.stamped == []
    assert [skipped for skipped, _reason in report.skipped] == [path]
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "store",
    ["settings.json", "playlist_visibility.json", "playlists/user.json"],
    ids=["settings", "visibility", "playlist"],
)
def test_invalid_utf8_is_preserved_and_reported_for_every_store(store_root, store):
    path = store_root / store
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xfe\x00garbage")

    report = script.run()

    assert report.stamped == []
    assert [skipped for skipped, _reason in report.skipped] == [path]
    assert path.read_bytes() == b"\xff\xfe\x00garbage"


def test_the_exit_code_reports_whether_anything_was_left_alone(store_root, capsys):
    _write(store_root / "settings.json", json.dumps({"kovaaks_username": "Mingo"}))

    assert script.main() == 0
    assert "stamped" in capsys.readouterr().out

    _write(store_root / "playlist_visibility.json", "not json")

    assert script.main() == 1
    assert "NOT converted" in capsys.readouterr().out
