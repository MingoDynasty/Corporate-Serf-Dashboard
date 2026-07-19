import io
import json
import zipfile
from pathlib import Path

import pytest

from scripts.release_job import (
    archive_prefix,
    build_release_metadata,
    main,
    next_tag,
    parse_uv_version,
    read_python_version,
    read_uv_version,
    should_release,
    source_asset_name,
    validate_release,
)

SHA = "a32aa5b437a16315341074546dc900495787d642"
TAG = "v2026.07.18"
COMMIT_DATE = "2026-07-18"


def _stamp(sha: str = SHA, commit_date: str = COMMIT_DATE) -> str:
    return (
        "# Expanded by git archive (GitHub zip/release downloads). Unexpanded\n"
        "# placeholders mean you're reading a git checkout.\n"
        f"sha: {sha}\n"
        f"commit-date: {commit_date}\n"
    )


def _write_archive(path: Path, stamp: str, tag: str = TAG) -> Path:
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr(f"{archive_prefix(tag)}version.txt", stamp)
        bundle.writestr(f"{archive_prefix(tag)}source/app.py", "print('hi')\n")
    return path


def _write_metadata(path: Path, **overrides: object) -> Path:
    payload = build_release_metadata(
        tag=TAG,
        sha=SHA,
        commit_date=COMMIT_DATE,
        uv_version="0.11.29",
        python_version="3.14",
    )
    payload.update(overrides)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _valid_assets(tmp_path: Path) -> tuple[Path, Path]:
    return (
        _write_archive(tmp_path / source_asset_name(TAG), _stamp()),
        _write_metadata(tmp_path / "release.json"),
    )


def _problems(archive: Path, metadata: Path) -> list[str]:
    return validate_release(
        archive=archive,
        metadata_path=metadata,
        tag=TAG,
        sha=SHA,
        commit_date=COMMIT_DATE,
        uv_version="0.11.29",
        python_version="3.14",
    )


# --- skip gate ------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "docs/architecture.md",
        "docs/proposals/nested/thing.txt",
        "tests/test_release_job.py",
        ".github/workflows/ci.yml",
        "README.md",
        "source/notes.md",
        ".gitignore",
        ".pre-commit-config.yaml",
    ],
)
def test_blocked_paths_do_not_release(path: str) -> None:
    assert should_release([path]) is False


@pytest.mark.parametrize(
    "path",
    [
        "source/app.py",
        "pyproject.toml",
        "uv.lock",
        "example.toml",
        ".python-version",
        ".gitattributes",
        "version.txt",
        "install.ps1",
        "resources/benchmarks/thing.json",
        # A nested .gitignore is not the top-level file the blocklist names, so
        # it releases: "when in doubt, release".
        "source/.gitignore",
        "docsite/index.html",
        "testsuite/runner.py",
    ],
)
def test_runtime_paths_release(path: str) -> None:
    assert should_release([path]) is True


def test_one_runtime_path_outweighs_many_blocked_paths() -> None:
    assert (
        should_release(
            [
                "docs/a.md",
                "tests/test_x.py",
                ".github/workflows/ci.yml",
                "source/app.py",
            ]
        )
        is True
    )


def test_empty_and_blank_change_lists_release_conservatively() -> None:
    assert should_release([]) is True
    assert should_release(["", "   ", "\t"]) is True


def test_windows_separators_are_normalized() -> None:
    assert should_release(["docs\\architecture.md"]) is False
    assert should_release(["source\\app.py"]) is True


# --- tag computation ------------------------------------------------------


def test_first_release_of_the_day_takes_the_bare_date() -> None:
    assert next_tag([], "2026-07-18") == "v2026.07.18"


def test_same_day_repeats_take_the_next_serial() -> None:
    assert next_tag(["v2026.07.18"], "2026-07-18") == "v2026.07.18.1"
    assert next_tag(["v2026.07.18", "v2026.07.18.1"], "2026-07-18") == "v2026.07.18.2"


def test_serial_counts_from_the_highest_in_use_not_the_first_gap() -> None:
    tags = ["v2026.07.18", "v2026.07.18.1", "v2026.07.18.3"]
    assert next_tag(tags, "2026-07-18") == "v2026.07.18.4"


def test_serials_are_compared_numerically_not_lexically() -> None:
    tags = ["v2026.07.18", "v2026.07.18.9", "v2026.07.18.10"]
    assert next_tag(tags, "2026-07-18") == "v2026.07.18.11"


def test_other_days_and_unrelated_tags_are_ignored() -> None:
    tags = [
        "v2026.07.17",
        "v2026.07.17.4",
        "v2026.07.19",
        "v1.0.0",
        "release-2026.07.18",
        "v2026.07.18-rc1",
        "",
    ]
    assert next_tag(tags, "2026-07-18") == "v2026.07.18"


def test_surrounding_whitespace_on_tags_is_tolerated() -> None:
    assert next_tag(["  v2026.07.18\n"], "2026-07-18") == "v2026.07.18.1"


@pytest.mark.parametrize("today", ["2026-7-18", "20260718", "2026.07.18", ""])
def test_malformed_dates_are_rejected(today: str) -> None:
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        next_tag([], today)


# --- release.json ---------------------------------------------------------


def test_uv_pin_is_stripped_to_a_bare_version() -> None:
    assert parse_uv_version("==0.11.29") == "0.11.29"
    assert parse_uv_version("  == 0.11.29  ") == "0.11.29"


@pytest.mark.parametrize(
    "required",
    [">=0.11.29", "~=0.11.29", "0.11.29", "==0.11.29, <1", "", "==*"],
)
def test_non_exact_uv_pins_fail_the_release(required: str) -> None:
    with pytest.raises(ValueError, match="exact"):
        parse_uv_version(required)


def test_metadata_is_the_frozen_v1_field_set() -> None:
    payload = build_release_metadata(
        tag=TAG,
        sha=SHA,
        commit_date=COMMIT_DATE,
        uv_version="0.11.29",
        python_version="3.14",
    )
    assert payload == {
        "schema_version": 1,
        "tag": TAG,
        "sha": SHA,
        "commit_date": COMMIT_DATE,
        "uv_version": "0.11.29",
        "python_version": "3.14",
        "source_asset": "Corporate-Serf-Dashboard-v2026.07.18.zip",
    }


def test_asset_name_and_archive_prefix_agree() -> None:
    assert source_asset_name(TAG).removesuffix(".zip") == archive_prefix(TAG).rstrip(
        "/"
    )


def test_repo_pins_are_readable_and_exact() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assert read_uv_version(repo_root / "pyproject.toml")
    assert read_python_version(repo_root / ".python-version")


# --- pre-publish validation -----------------------------------------------


def test_valid_assets_have_no_problems(tmp_path: Path) -> None:
    archive, metadata = _valid_assets(tmp_path)
    assert _problems(archive, metadata) == []


def test_unexpanded_stamp_blocks_publication(tmp_path: Path) -> None:
    archive = _write_archive(
        tmp_path / source_asset_name(TAG),
        "sha: $Format:%H$\ncommit-date: $Format:%cs$\n",
    )
    metadata = _write_metadata(tmp_path / "release.json")
    assert any("$Format" in problem for problem in _problems(archive, metadata))


def test_stamp_from_the_wrong_commit_blocks_publication(tmp_path: Path) -> None:
    archive = _write_archive(tmp_path / source_asset_name(TAG), _stamp(sha="b" * 40))
    metadata = _write_metadata(tmp_path / "release.json")
    problems = _problems(archive, metadata)
    assert any("does not match the released commit" in problem for problem in problems)


def test_stamp_from_the_wrong_date_blocks_publication(tmp_path: Path) -> None:
    archive = _write_archive(
        tmp_path / source_asset_name(TAG), _stamp(commit_date="2026-07-01")
    )
    metadata = _write_metadata(tmp_path / "release.json")
    problems = _problems(archive, metadata)
    assert any("commit-date" in problem for problem in problems)


def test_archive_without_the_expected_prefix_blocks_publication(
    tmp_path: Path,
) -> None:
    archive = tmp_path / source_asset_name(TAG)
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("version.txt", _stamp())
    metadata = _write_metadata(tmp_path / "release.json")
    problems = _problems(archive, metadata)
    assert any("has no" in problem for problem in problems)


def test_archive_renamed_in_yaml_blocks_publication(tmp_path: Path) -> None:
    # The workflow mints the asset filename independently of this module. A
    # rename there that leaves the archive prefix alone passes every other
    # check, so release.json would name an asset the release does not carry.
    archive = _write_archive(tmp_path / "Renamed-In-Yaml.zip", _stamp())
    metadata = _write_metadata(tmp_path / "release.json")
    problems = _problems(archive, metadata)
    assert any(
        "archive is named Renamed-In-Yaml.zip" in problem for problem in problems
    )


def test_unreadable_archive_blocks_publication(tmp_path: Path) -> None:
    archive = tmp_path / source_asset_name(TAG)
    archive.write_bytes(b"not a zip")
    metadata = _write_metadata(tmp_path / "release.json")
    problems = _problems(archive, metadata)
    assert any("could not be read as a zip" in problem for problem in problems)


@pytest.mark.parametrize(
    "overrides",
    [
        {"schema_version": 2},
        {"tag": "v2026.07.17"},
        {"sha": "c" * 40},
        {"commit_date": "2026-07-01"},
        {"uv_version": "0.11.28"},
        {"python_version": "3.13"},
        {"source_asset": "wrong.zip"},
    ],
)
def test_metadata_drift_blocks_publication(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    archive = _write_archive(tmp_path / source_asset_name(TAG), _stamp())
    metadata = _write_metadata(tmp_path / "release.json", **overrides)
    problems = _problems(archive, metadata)
    assert any(next(iter(overrides)) in problem for problem in problems)


def test_missing_metadata_field_blocks_publication(tmp_path: Path) -> None:
    archive = _write_archive(tmp_path / source_asset_name(TAG), _stamp())
    metadata = tmp_path / "release.json"
    metadata.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    problems = _problems(archive, metadata)
    assert any("tag is None" in problem for problem in problems)


def test_unreadable_metadata_blocks_publication(tmp_path: Path) -> None:
    archive = _write_archive(tmp_path / source_asset_name(TAG), _stamp())
    metadata = tmp_path / "release.json"
    metadata.write_text("{not json", encoding="utf-8")
    problems = _problems(archive, metadata)
    assert any("could not be read as JSON" in problem for problem in problems)


# --- command line ---------------------------------------------------------


def test_should_release_command_prints_a_workflow_boolean(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    changed = tmp_path / "changed.txt"
    changed.write_text("docs/a.md\ntests/test_x.py\n", encoding="utf-8")
    assert main(["should-release", "--paths-from", str(changed)]) == 0
    assert capsys.readouterr().out.strip() == "false"

    changed.write_text("docs/a.md\nsource/app.py\n", encoding="utf-8")
    assert main(["should-release", "--paths-from", str(changed)]) == 0
    assert capsys.readouterr().out.strip() == "true"


def test_next_tag_command_reads_tags_from_stdin(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("v2026.07.18\n"))
    assert main(["next-tag", "--date", "2026-07-18"]) == 0
    assert capsys.readouterr().out.strip() == "v2026.07.18.1"


def test_release_json_command_writes_the_asset(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output = tmp_path / "release.json"
    exit_code = main(
        [
            "release-json",
            "--tag",
            TAG,
            "--sha",
            SHA,
            "--commit-date",
            COMMIT_DATE,
            "--output",
            str(output),
            "--repo-root",
            str(repo_root),
        ]
    )
    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["tag"] == TAG
    assert payload["sha"] == SHA
    assert payload["source_asset"] == source_asset_name(TAG)
    assert payload["uv_version"] == read_uv_version(repo_root / "pyproject.toml")
    assert payload["python_version"] == read_python_version(
        repo_root / ".python-version"
    )


def test_validate_command_round_trips_generated_assets(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    metadata = tmp_path / "release.json"
    common = [
        "--tag",
        TAG,
        "--sha",
        SHA,
        "--commit-date",
        COMMIT_DATE,
        "--repo-root",
        str(repo_root),
    ]
    assert main(["release-json", "--output", str(metadata), *common]) == 0
    archive = _write_archive(tmp_path / source_asset_name(TAG), _stamp())
    assert (
        main(
            [
                "validate",
                "--archive",
                str(archive),
                "--metadata",
                str(metadata),
                *common,
            ]
        )
        == 0
    )


def test_validate_command_exits_nonzero_on_a_bad_archive(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    metadata = tmp_path / "release.json"
    common = [
        "--tag",
        TAG,
        "--sha",
        SHA,
        "--commit-date",
        COMMIT_DATE,
        "--repo-root",
        str(repo_root),
    ]
    assert main(["release-json", "--output", str(metadata), *common]) == 0
    archive = _write_archive(
        tmp_path / source_asset_name(TAG), "sha: $Format:%H$\ncommit-date: x\n"
    )
    exit_code = main(
        ["validate", "--archive", str(archive), "--metadata", str(metadata), *common]
    )
    assert exit_code == 1
    assert "::error::" in capsys.readouterr().out
