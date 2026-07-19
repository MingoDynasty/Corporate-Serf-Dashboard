import json
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from source.utilities import build_info
from source.utilities.build_info import BuildInfo, get_build_info

MANIFEST_SHA = "1" * 40
STAMP_SHA = "2" * 40
GIT_SHA = "3" * 40


@pytest.fixture(autouse=True)
def isolated_build_info(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Path]:
    """Resolve every layer inside a tmp dir, with no cached result carried in."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(build_info, "_CODE_ROOT", tmp_path)
    get_build_info.cache_clear()
    yield tmp_path
    get_build_info.cache_clear()


def _write_manifest(root: Path, **overrides: object) -> None:
    manifest = {
        "schema_version": 1,
        "tag": "v2026.07.18",
        "sha": MANIFEST_SHA,
        "commit_date": "2026-07-18",
        "update_policy": "latest",
    }
    manifest.update(overrides)
    (root / build_info.MANIFEST_FILENAME).write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def _write_stamp(root: Path, sha: str, commit_date: str = "2026-07-17") -> None:
    (root / build_info.VERSION_STAMP_FILENAME).write_text(
        f"# comment header\nsha: {sha}\ncommit-date: {commit_date}\n",
        encoding="utf-8",
    )


def _fake_git(
    monkeypatch: pytest.MonkeyPatch, stdout: str, returncode: int = 0
) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=""
        )

    monkeypatch.setattr(build_info.subprocess, "run", fake_run)


def _fail_git(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):
        raise OSError("git is not installed")

    monkeypatch.setattr(build_info.subprocess, "run", fake_run)


def test_manifest_wins_when_it_corroborates_the_stamp(
    isolated_build_info: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A settled install: the manifest describes the code that is running."""
    _write_manifest(isolated_build_info, sha=STAMP_SHA)
    _write_stamp(isolated_build_info, STAMP_SHA)
    _fake_git(monkeypatch, f"{GIT_SHA}\n2026-07-16\n")

    info = get_build_info()

    assert info == BuildInfo(
        sha=STAMP_SHA,
        commit_date="2026-07-18",
        tag="v2026.07.18",
        source="manifest",
    )
    assert info.short_sha == "2222222"
    assert info.release_label == "v2026.07.18"
    assert info.short_description == "2222222 (2026-07-18)"


def test_stale_manifest_loses_to_the_stamp_beside_the_code(
    isolated_build_info: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pending activation: new code, but the install's manifest is older.

    Regression test for the D2/D6 conflict found reviewing PR #154 — trusting
    the manifest here would make the new build report the previous version,
    and the launcher would never promote it.
    """
    _write_manifest(isolated_build_info, sha=MANIFEST_SHA)
    _write_stamp(isolated_build_info, STAMP_SHA)
    _fake_git(monkeypatch, f"{GIT_SHA}\n2026-07-16\n")

    info = get_build_info()

    assert info == BuildInfo(
        sha=STAMP_SHA, commit_date="2026-07-17", tag=None, source="archive"
    )


def test_manifest_without_a_stamp_is_ignored(
    isolated_build_info: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing corroborates the manifest, so it does not get to answer."""
    _write_manifest(isolated_build_info)
    _fake_git(monkeypatch, f"{GIT_SHA}\n2026-07-16\n")

    assert get_build_info() == BuildInfo(
        sha=GIT_SHA, commit_date="2026-07-16", tag=None, source="git"
    )


def test_manifest_with_an_unexpanded_stamp_is_ignored(
    isolated_build_info: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A checkout run against an install's state root still reports itself."""
    _write_manifest(isolated_build_info)
    _write_stamp(isolated_build_info, "$Format:%H$", commit_date="$Format:%cs$")
    _fake_git(monkeypatch, f"{GIT_SHA}\n2026-07-16\n")

    assert get_build_info().source == "git"


@pytest.mark.parametrize(
    "overrides",
    [
        # Both would otherwise corroborate the stamp, so the fall-through is
        # attributable to the field under test.
        {"schema_version": 2, "sha": STAMP_SHA},
        {"schema_version": 1, "sha": ""},
    ],
)
def test_unusable_manifest_falls_through_to_the_stamp(
    isolated_build_info: Path, overrides: dict[str, object]
) -> None:
    _write_manifest(isolated_build_info, **overrides)
    _write_stamp(isolated_build_info, STAMP_SHA)

    assert get_build_info().source == "archive"


def test_malformed_manifest_falls_through_to_the_stamp(
    isolated_build_info: Path,
) -> None:
    (isolated_build_info / build_info.MANIFEST_FILENAME).write_text(
        "not json", encoding="utf-8"
    )
    _write_stamp(isolated_build_info, STAMP_SHA)

    assert get_build_info().source == "archive"


def test_expanded_stamp_identifies_an_archive_download(
    isolated_build_info: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_stamp(isolated_build_info, STAMP_SHA)
    _fake_git(monkeypatch, f"{GIT_SHA}\n2026-07-16\n")

    info = get_build_info()

    assert info == BuildInfo(
        sha=STAMP_SHA, commit_date="2026-07-17", tag=None, source="archive"
    )
    assert info.release_label == "unknown"


def test_unexpanded_stamp_falls_through_to_git(
    isolated_build_info: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_stamp(isolated_build_info, "$Format:%H$", commit_date="$Format:%cs$")
    _fake_git(monkeypatch, f"{GIT_SHA}\n2026-07-16\n")

    info = get_build_info()

    assert info == BuildInfo(
        sha=GIT_SHA, commit_date="2026-07-16", tag=None, source="git"
    )
    assert info.release_label == "dev"


def test_git_failure_yields_unknown(
    isolated_build_info: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fail_git(monkeypatch)

    info = get_build_info()

    assert info == BuildInfo(sha=None, commit_date=None, tag=None, source="unknown")
    assert info.short_sha == "unknown"
    assert info.release_label == "unknown"
    assert info.short_description == "unknown (unknown)"


def test_nonzero_git_exit_yields_unknown(
    isolated_build_info: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_git(monkeypatch, "", returncode=128)

    assert get_build_info().source == "unknown"


def test_build_info_is_cached(
    isolated_build_info: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_git(monkeypatch, f"{GIT_SHA}\n2026-07-16\n")

    first = get_build_info()
    _write_manifest(isolated_build_info)

    assert get_build_info() is first


def test_checkout_of_this_repo_resolves_a_real_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The committed stamp is unexpanded here, so git answers for a checkout."""
    monkeypatch.setattr(build_info, "_CODE_ROOT", Path(__file__).resolve().parents[1])

    info = get_build_info()

    assert info.source == "git"
    assert info.sha is not None
    assert len(info.sha) == 40
