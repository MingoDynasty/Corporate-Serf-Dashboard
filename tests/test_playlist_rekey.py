import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from source.kovaaks import data_service
from source.kovaaks.data_models import PlaylistData, Rank, Scenario

REPO_ROOT = Path(__file__).resolve().parent.parent


def _playlist(
    name: str,
    code: str,
    scenario_name: str = "Scenario",
    *,
    with_ranks: bool = True,
) -> PlaylistData:
    ranks = (
        [Rank(name="Bronze", color="#a97142", threshold=100)] if with_ranks else None
    )
    return PlaylistData(
        name=name,
        code=code,
        scenarios=[Scenario(name=scenario_name, ranks=ranks)],
    )


def _write_playlist(path: Path, playlist: PlaylistData) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        playlist.model_dump_json(indent=2, exclude_none=True) + "\n",
        encoding="utf-8",
    )


def _write_raw_playlist(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _configure_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path]:
    bundled_root = tmp_path / "resources" / "playlists"
    user_root = tmp_path / "data" / "playlists"
    bundled_root.mkdir(parents=True)
    monkeypatch.setattr(
        data_service,
        "BUNDLED_PLAYLIST_DIRECTORY_PATH",
        bundled_root.resolve(),
    )
    monkeypatch.setattr(
        data_service,
        "USER_PLAYLIST_DIRECTORY_PATH",
        user_root.resolve(),
    )
    monkeypatch.setattr(data_service, "playlist_database", {})
    data_service.playlist_startup_warning_queue.clear()
    return bundled_root, user_root


def test_playlist_data_strips_codes_and_rejects_blank_codes():
    playlist = _playlist("Test", "  KovaaKsCode  ")

    assert playlist.code == "KovaaKsCode"
    with pytest.raises(ValueError, match="add a `code` field"):
        _playlist("Blank", "   ")


def test_load_playlists_keys_by_code_and_disambiguates_duplicate_names(
    monkeypatch,
    tmp_path,
):
    bundled_root, _user_root = _configure_roots(monkeypatch, tmp_path)
    first = _playlist("Same Name", "CodeA", "First")
    second = _playlist("Same Name", "CodeB", "Second")
    _write_playlist(bundled_root / "b.json", second)
    _write_playlist(bundled_root / "a.json", first)

    data_service.load_playlists()

    assert data_service.playlist_database == {"CodeA": first, "CodeB": second}
    assert data_service.get_playlist_by_code("CodeA") == first
    assert data_service.get_scenarios_from_playlist_code("CodeB") == ["Second"]
    assert data_service.get_playlist_selector_options() == [
        {"label": "Same Name (CodeA)", "value": "CodeA"},
        {"label": "Same Name (CodeB)", "value": "CodeB"},
    ]
    assert data_service.get_playlist_display_label("CodeA") == "Same Name (CodeA)"
    assert data_service.drain_startup_playlist_warnings() == []


def test_load_playlists_treats_missing_user_root_as_empty(monkeypatch, tmp_path):
    bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    playlist = _playlist("Bundled", "BundledCode")
    _write_playlist(bundled_root / "bundled.json", playlist)

    data_service.load_playlists()

    assert not user_root.exists()
    assert data_service.playlist_database == {"BundledCode": playlist}
    assert data_service.drain_startup_playlist_warnings() == []


def test_duplicate_code_in_one_root_uses_total_filename_order_and_warns(
    monkeypatch,
    tmp_path,
):
    bundled_root, _user_root = _configure_roots(monkeypatch, tmp_path)
    winner = _playlist("Winner", "SharedCode")
    skipped = _playlist("Skipped", "SharedCode")
    _write_playlist(bundled_root / "A.json", winner)
    _write_playlist(bundled_root / "b.json", skipped)

    data_service.load_playlists()

    assert data_service.playlist_database == {"SharedCode": winner}
    assert data_service.drain_startup_playlist_warnings() == [
        "Skipping playlist file "
        f"{bundled_root.resolve() / 'b.json'}: playlist code SharedCode "
        f"already loaded from {bundled_root.resolve() / 'A.json'}."
    ]
    assert sorted(
        [Path("a.json"), Path("A.json")],
        key=data_service._playlist_file_sort_key,
    ) == [Path("A.json"), Path("a.json")]


def test_bundled_root_wins_over_user_root_and_user_file_is_not_deleted(
    monkeypatch,
    tmp_path,
):
    bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    bundled = _playlist("Bundled Benchmark", "SharedCode", "Bundled Scenario")
    user = _playlist("User Import", "SharedCode", "User Scenario", with_ranks=False)
    user_only = _playlist("User Only", "UserCode", "User Only Scenario")
    _write_playlist(bundled_root / "benchmark.json", bundled)
    _write_playlist(user_root / "import.json", user)
    _write_playlist(user_root / "user-only.json", user_only)

    data_service.load_playlists()

    assert data_service.playlist_database == {
        "SharedCode": bundled,
        "UserCode": user_only,
    }
    assert (user_root / "import.json").exists()
    assert data_service.drain_startup_playlist_warnings() == [
        "Skipping playlist file "
        f"{user_root.resolve() / 'import.json'}: playlist code SharedCode "
        f"already loaded from {bundled_root.resolve() / 'benchmark.json'}."
    ]


def test_load_playlists_skips_missing_empty_and_blank_codes_with_actionable_warning(
    monkeypatch,
    tmp_path,
):
    bundled_root, _user_root = _configure_roots(monkeypatch, tmp_path)
    valid = _playlist("Valid", "ValidCode")
    _write_raw_playlist(
        bundled_root / "missing.json",
        '{"name": "Missing", "scenarios": [{"name": "Scenario"}]}',
    )
    _write_raw_playlist(
        bundled_root / "empty.json",
        '{"name": "Empty", "code": "", "scenarios": [{"name": "Scenario"}]}',
    )
    _write_raw_playlist(
        bundled_root / "blank.json",
        '{"name": "Blank", "code": "   ", "scenarios": [{"name": "Scenario"}]}',
    )
    _write_playlist(bundled_root / "valid.json", valid)

    data_service.load_playlists()

    assert data_service.playlist_database == {"ValidCode": valid}
    warnings = data_service.drain_startup_playlist_warnings()
    assert len(warnings) == 3
    assert all("add a `code` field" in warning for warning in warnings)


def test_import_refuses_duplicate_code_but_allows_duplicate_name(
    monkeypatch,
    tmp_path,
):
    bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    existing = _playlist("Same Name", "ExistingCode")
    _write_playlist(bundled_root / "existing.json", existing)
    data_service.load_playlists()

    api_response = SimpleNamespace(
        data=[
            SimpleNamespace(
                playlistName="Upstream Rename",
                playlistCode="ExistingCode",
                scenarioList=[SimpleNamespace(scenarioName="Imported Scenario")],
            )
        ]
    )
    monkeypatch.setattr(data_service, "get_playlist_data", lambda _code: api_response)

    message = data_service.load_playlist_from_code("ExistingCode")

    assert message == (
        "Playlist code already exists: ExistingCode is already imported as "
        "Same Name (ExistingCode)."
    )
    assert not user_root.exists()
    assert data_service.playlist_database == {"ExistingCode": existing}

    api_response.data[0].playlistName = "Same Name"
    api_response.data[0].playlistCode = "NewCode"

    assert data_service.load_playlist_from_code("NewCode") is None
    assert set(data_service.playlist_database) == {"ExistingCode", "NewCode"}
    imported_file = user_root / "Same Name [NewCode].json"
    assert imported_file.exists()
    imported = PlaylistData.model_validate_json(
        imported_file.read_text(encoding="utf-8")
    )
    assert imported.name == "Same Name"
    assert imported.code == "NewCode"


def test_write_playlist_data_to_file_retries_transient_replace_errors(
    monkeypatch,
    tmp_path,
):
    _bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    playlist = _playlist("Retry Me", "RetryCode")
    replacements = []
    original_replace = data_service.os.replace

    def flaky_replace(source, destination):
        replacements.append((Path(source), Path(destination)))
        if len(replacements) == 1:
            raise PermissionError("transient lock")
        original_replace(source, destination)

    monkeypatch.setattr(data_service.os, "replace", flaky_replace)
    monkeypatch.setattr(data_service.time, "sleep", lambda _delay: None)

    data_service.write_playlist_data_to_file(playlist)

    assert len(replacements) == 2
    assert (user_root / "Retry Me [RetryCode].json").exists()
    assert not list(user_root.glob(".*.tmp"))


def test_write_playlist_data_to_file_leaves_existing_file_intact_on_failure(
    monkeypatch,
    tmp_path,
):
    _bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    playlist = _playlist("Atomic", "AtomicCode")
    destination = user_root / "Atomic [AtomicCode].json"
    destination.parent.mkdir(parents=True)
    destination.write_text("previous content", encoding="utf-8")

    def failing_replace(_source, _destination):
        raise RuntimeError("boom")

    monkeypatch.setattr(data_service.os, "replace", failing_replace)

    with pytest.raises(RuntimeError, match="boom"):
        data_service.write_playlist_data_to_file(playlist)

    assert destination.read_text(encoding="utf-8") == "previous content"
    assert not list(user_root.glob(".*.tmp"))


def test_committed_bundled_playlists_all_carry_rank_data():
    result = subprocess.run(
        ["git", "ls-files", "resources/playlists"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    playlist_paths = [
        REPO_ROOT / path
        for path in result.stdout.splitlines()
        if path.endswith(".json")
    ]

    assert playlist_paths
    missing_rank_data = []
    for playlist_path in playlist_paths:
        playlist = PlaylistData.model_validate_json(
            playlist_path.read_text(encoding="utf-8")
        )
        if not playlist.scenarios or any(
            not scenario.ranks for scenario in playlist.scenarios
        ):
            missing_rank_data.append(playlist_path.relative_to(REPO_ROOT).as_posix())

    assert not missing_rank_data
