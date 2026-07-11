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


def test_load_playlists_tracks_user_root_codes_for_visibility_seed(
    monkeypatch,
    tmp_path,
):
    bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    _write_playlist(bundled_root / "bundled.json", _playlist("Bundled", "BundledCode"))
    _write_playlist(user_root / "user.json", _playlist("User", "UserCode"))
    # A user copy shadowed by a bundled duplicate never wins, so it must not
    # count as a user-root code either.
    _write_playlist(user_root / "shadowed.json", _playlist("Shadow", "BundledCode"))

    data_service.load_playlists()

    assert data_service.get_user_root_playlist_codes() == {"UserCode"}


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

    message, imported_code = data_service.load_playlist_from_code("ExistingCode")

    assert message == (
        "Playlist code already exists: ExistingCode is already imported as "
        "Same Name (ExistingCode)."
    )
    # Duplicate refusal now carries the conflicting existing (canonical) code,
    # so the page layer can check whether that playlist is hidden.
    assert imported_code == "ExistingCode"
    assert not user_root.exists()
    assert data_service.playlist_database == {"ExistingCode": existing}

    api_response.data[0].playlistName = "Same Name"
    api_response.data[0].playlistCode = "NewCode"

    # The canonical stored code is returned even when the pasted input
    # differs (case normalization, non-exact search matches).
    assert data_service.load_playlist_from_code("newcode") == (None, "NewCode")
    assert set(data_service.playlist_database) == {"ExistingCode", "NewCode"}
    imported_file = user_root / "Same Name [NewCode].json"
    assert imported_file.exists()
    imported = PlaylistData.model_validate_json(
        imported_file.read_text(encoding="utf-8")
    )
    assert imported.name == "Same Name"
    assert imported.code == "NewCode"


def test_import_reports_write_failures_without_updating_database(
    monkeypatch,
    tmp_path,
):
    _bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    api_response = SimpleNamespace(
        data=[
            SimpleNamespace(
                playlistName="Locked Playlist",
                playlistCode="LockedCode",
                scenarioList=[SimpleNamespace(scenarioName="Imported Scenario")],
            )
        ]
    )
    monkeypatch.setattr(data_service, "get_playlist_data", lambda _code: api_response)

    def fail_write(_playlist):
        raise PermissionError("playlist file is locked")

    monkeypatch.setattr(data_service, "write_playlist_data_to_file", fail_write)

    message, imported_code = data_service.load_playlist_from_code("LockedCode")

    assert message == "Failed to save playlist data: Locked Playlist (LockedCode)"
    assert imported_code is None
    assert data_service.playlist_database == {}
    assert not user_root.exists()


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


def test_load_playlists_records_user_root_file_paths(monkeypatch, tmp_path):
    _bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    # A hand-dropped file whose name get_playlist_file_path would never
    # reconstruct: delete must still find it via the recorded path.
    hand_named = user_root / "arbitrary-name.json"
    _write_playlist(hand_named, _playlist("Hand Named", "HandCode"))

    data_service.load_playlists()

    recorded = data_service._user_root_playlist_files
    assert recorded == {"HandCode": [user_root.resolve() / "arbitrary-name.json"]}
    # The import-written path the naive reconstruction would produce does not
    # match the hand-dropped filename — that is exactly why we record paths.
    reconstructed = data_service.get_playlist_file_path("Hand Named", "HandCode")
    assert reconstructed.name == "Hand Named [HandCode].json"
    assert reconstructed not in recorded["HandCode"]


def test_load_playlists_records_superseded_user_files_only_for_bundled_winners(
    monkeypatch,
    tmp_path,
):
    bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    _write_playlist(bundled_root / "bundled.json", _playlist("Bundled", "BundledCode"))
    # A user copy of a bundled code: a dead pre-#90 copy-to-activate leftover.
    superseded = user_root / "old-copy.json"
    _write_playlist(superseded, _playlist("Old Copy", "BundledCode"))
    # A user file shadowed by another *user* file is a plain duplicate, not
    # "superseded by bundled", so it must stay out of the cleanup list.
    _write_playlist(user_root / "a-dup.json", _playlist("Dup", "DupCode"))
    _write_playlist(user_root / "z-dup.json", _playlist("Dup Two", "DupCode"))

    data_service.load_playlists()

    assert data_service.get_superseded_user_playlist_files() == [
        (user_root.resolve() / "old-copy.json", "BundledCode")
    ]


def test_delete_user_playlist_removes_file_store_and_tracking(monkeypatch, tmp_path):
    _bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    user_file = user_root / "user.json"
    _write_playlist(user_file, _playlist("User", "UserCode"))
    data_service.load_playlists()
    assert user_file.exists()

    result = data_service.delete_user_playlist("UserCode")

    assert result is None
    assert not user_file.exists()
    assert "UserCode" not in data_service.playlist_database
    assert data_service.get_user_root_playlist_codes() == set()
    assert "UserCode" not in data_service._user_root_playlist_files


def test_delete_user_playlist_removes_all_same_code_duplicates(monkeypatch, tmp_path):
    # Two user files sharing one code: the loser is skipped at load, but a
    # leftover copy would resurrect the playlist on restart. Delete must remove
    # every copy (regression for PR #98 review).
    _bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    _write_playlist(user_root / "a.json", _playlist("Dup A", "DupCode"))
    _write_playlist(user_root / "b.json", _playlist("Dup B", "DupCode"))
    data_service.load_playlists()
    assert (user_root / "a.json").exists()
    assert (user_root / "b.json").exists()
    assert len(data_service._user_root_playlist_files["DupCode"]) == 2

    result = data_service.delete_user_playlist("DupCode")

    assert result is None
    assert not (user_root / "a.json").exists()
    assert not (user_root / "b.json").exists()
    assert "DupCode" not in data_service.playlist_database

    # Simulate a restart: reloading must not resurrect the deleted playlist.
    data_service.load_playlists()
    assert "DupCode" not in data_service.playlist_database


def test_delete_user_playlist_keeps_served_winner_when_a_duplicate_is_locked(
    monkeypatch,
    tmp_path,
):
    # A locked non-winning duplicate must not leave the store serving the
    # winner's data after its file is deleted (which would silently swap in the
    # survivor on restart). Winner-last deletion keeps store == disk on failure.
    _bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    _write_playlist(user_root / "a.json", _playlist("Winner", "DupCode", "Win Scen"))
    _write_playlist(user_root / "b.json", _playlist("Survivor", "DupCode", "Surv Scen"))
    data_service.load_playlists()
    # a.json wins on filename order; its data is what the store serves.
    assert data_service.playlist_database["DupCode"].name == "Winner"

    real_unlink = data_service.Path.unlink

    def locked_b_unlink(self):
        if self.name == "b.json":
            raise PermissionError("b.json is locked")
        real_unlink(self)

    monkeypatch.setattr(data_service.Path, "unlink", locked_b_unlink)

    result = data_service.delete_user_playlist("DupCode")

    assert result is not None
    assert "Failed to delete playlist file" in result
    # The served (winning) file survives — the store is not serving a deleted
    # file — and the store still holds the winner's data.
    assert (user_root / "a.json").exists()
    assert (user_root / "b.json").exists()
    assert data_service.playlist_database["DupCode"].name == "Winner"

    # Simulated restart: still the winner, no silent swap to the survivor.
    monkeypatch.setattr(data_service.Path, "unlink", real_unlink)
    data_service.load_playlists()
    assert data_service.playlist_database["DupCode"].name == "Winner"


def test_delete_user_playlist_refuses_bundled_code(monkeypatch, tmp_path):
    bundled_root, _user_root = _configure_roots(monkeypatch, tmp_path)
    bundled_file = bundled_root / "bundled.json"
    _write_playlist(bundled_file, _playlist("Bundled", "BundledCode"))
    data_service.load_playlists()

    result = data_service.delete_user_playlist("BundledCode")

    assert result is not None
    assert "cannot be deleted" in result
    assert bundled_file.exists()
    assert "BundledCode" in data_service.playlist_database


def test_delete_user_playlist_refuses_unknown_code(monkeypatch, tmp_path):
    _configure_roots(monkeypatch, tmp_path)
    data_service.load_playlists()

    result = data_service.delete_user_playlist("NopeCode")

    assert result is not None
    assert "cannot be deleted" in result


def test_delete_user_playlist_tolerates_already_missing_file(monkeypatch, tmp_path):
    _bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    user_file = user_root / "user.json"
    _write_playlist(user_file, _playlist("User", "UserCode"))
    data_service.load_playlists()
    user_file.unlink()  # vanished out from under us before delete

    result = data_service.delete_user_playlist("UserCode")

    assert result is None
    assert "UserCode" not in data_service.playlist_database
    assert "UserCode" not in data_service._user_root_playlist_files


def test_delete_user_playlist_reports_oserror_without_touching_store(
    monkeypatch,
    tmp_path,
):
    _bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    user_file = user_root / "user.json"
    _write_playlist(user_file, _playlist("User", "UserCode"))
    data_service.load_playlists()

    def locked_unlink(_self):
        raise PermissionError("file is locked")

    monkeypatch.setattr(data_service.Path, "unlink", locked_unlink)

    result = data_service.delete_user_playlist("UserCode")

    assert result is not None
    assert "Failed to delete playlist file" in result
    assert "UserCode" in data_service.playlist_database
    assert "UserCode" in data_service._user_root_playlist_files


def test_delete_superseded_user_playlist_files_removes_all_dead_copies(
    monkeypatch,
    tmp_path,
):
    bundled_root, user_root = _configure_roots(monkeypatch, tmp_path)
    _write_playlist(bundled_root / "bundled.json", _playlist("Bundled", "BundledCode"))
    superseded = user_root / "old-copy.json"
    _write_playlist(superseded, _playlist("Old Copy", "BundledCode"))
    data_service.load_playlists()
    assert superseded.exists()
    assert len(data_service.get_superseded_user_playlist_files()) == 1

    result = data_service.delete_superseded_user_playlist_files()

    assert result is None
    assert not superseded.exists()
    assert data_service.get_superseded_user_playlist_files() == []
    # The bundled winner never had a store entry touched.
    assert "BundledCode" in data_service.playlist_database


def test_committed_bundled_playlists_all_carry_rank_data():
    result = subprocess.run(
        ["git", "ls-files", "resources/benchmarks"],
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
