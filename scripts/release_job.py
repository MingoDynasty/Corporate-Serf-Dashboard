"""Decision helpers for the automated CalVer release job in CI.

The `release` job in `.github/workflows/ci.yml` is mostly `git` and `gh`
plumbing, but four pieces of it carry real decisions: whether a push is worth
releasing at all, what the next tag is, what the frozen `release.json` wire
contract contains, and whether the built assets are safe to publish. Those
live here rather than inline in YAML so they can be unit tested -- GitHub
releases are immutable once published, so a bad publish cannot be repaired.

Stdlib only: the release job runs this through `uv run --no-project`, without
syncing the application's dependencies.
"""

import argparse
import json
import re
import sys
import tomllib
import zipfile
from collections.abc import Iterable, Sequence
from pathlib import Path

#: `release.json` / `install.json` wire contract version. Changes within v1 are
#: additive-only; a breaking change bumps this and dual-publishes the envelope.
SCHEMA_VERSION = 1

#: Stem shared by the release asset and the directory inside it.
ASSET_STEM = "Corporate-Serf-Dashboard"

# Paths that cannot change what an installed copy runs. A push touching only
# these is skipped. Deliberately a blocklist rather than an allowlist: the
# failure directions are asymmetric, since a redundant release is only noise
# while a missed one strands distribution inputs (install.ps1, the launcher,
# example.toml, .python-version, .gitattributes) at an older tag.
_BLOCKED_DIRECTORIES = ("docs/", "tests/", ".github/", ".idea/")
_BLOCKED_FILES = (".gitignore", ".pre-commit-config.yaml")
_BLOCKED_SUFFIX = ".md"

# What the release zip must carry, and what it must not. Publication is
# irreversible, so a `.gitattributes` edit or a file move that silently drops
# an install-critical path has to fail the draft rather than surface as
# someone's broken install. Trailing slashes mark directories. Deliberately
# not a snapshot of today's tree: every entry is here because something reads
# it.
#
# A path that some component opens by name is listed by name. A directory
# entry only asserts that the tree holds at least one file, so it would still
# pass after the one file that mattered was renamed away -- use it only where
# no single member is the dependency.
REQUIRED_ARCHIVE_ENTRIES = (
    "source/app.py",  # what launcher.ps1 hands the interpreter
    "assets/",  # Dash's static asset directory, served at runtime
    "resources/",  # the bundled benchmark library, scanned in full at startup
    "scripts/launch_bootstrap.ps1",  # install.ps1 copies it to launch.ps1
    "scripts/launcher.ps1",  # what that bootstrap then runs
    "docs/example.png",  # the shipped README embeds it
    "docs/architecture.md",  # the shipped README links it
    "docs/product.md",  # the shipped README links it
    "docs/roadmap.md",  # the shipped README links it
    "install.ps1",  # the manual-install entry point README documents
    "pyproject.toml",  # dependency and uv pins the installer syncs against
    "uv.lock",  # the locked resolution `uv sync --locked` requires
    ".python-version",  # the interpreter the installer provisions
    "version.txt",  # the export-subst build identity
    "example.toml",  # the template config.toml is copied from
    "LICENSE",  # the terms the copy is distributed under
    "README.md",  # the zip's own front page
)

# Development-only trees pruned by `.gitattributes`. They must be absent
# outright: git archive emits directory entries, so a pattern that drops the
# files but keeps an empty directory has not done the job.
EXCLUDED_ARCHIVE_TREES = ("tests/", ".idea/", ".github/")

_TAG_PATTERN = re.compile(r"^v(?P<date>\d{4}\.\d{2}\.\d{2})(?:\.(?P<serial>\d+))?$")
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EXACT_PIN_PATTERN = re.compile(r"^==\s*(?P<version>[0-9][^\s,;]*)$")
_STAMP_SHA_PATTERN = re.compile(r"^sha:\s*(?P<sha>[0-9a-f]{40})\s*$", re.MULTILINE)
_STAMP_DATE_PATTERN = re.compile(
    r"^commit-date:\s*(?P<date>\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE
)


def is_release_worthy(path: str) -> bool:
    """Return True when a changed path can affect what an installed copy runs."""
    normalized = path.strip().replace("\\", "/")
    if not normalized:
        return False
    if normalized.endswith(_BLOCKED_SUFFIX):
        return False
    if normalized in _BLOCKED_FILES:
        return False
    return not normalized.startswith(_BLOCKED_DIRECTORIES)


def should_release(paths: Iterable[str]) -> bool:
    """Return True when any of the pushed paths is release-worthy.

    An empty change list also releases. The job cannot distinguish "this push
    changed nothing" from "the diff could not be computed", and the asymmetry
    above says a redundant release beats a missed one.
    """
    considered = [path for path in paths if path.strip()]
    if not considered:
        return True
    return any(is_release_worthy(path) for path in considered)


def next_tag(existing_tags: Iterable[str], today: str) -> str:
    """Return the next `vYYYY.MM.DD[.N]` tag for `today` (UTC, `YYYY-MM-DD`).

    The first release of a day takes the bare date; each repeat that day takes
    the next `.N`, counting up from the highest serial already in use so a tag
    name is never reissued.
    """
    if _DATE_PATTERN.match(today) is None:
        raise ValueError(f"expected a YYYY-MM-DD date, got {today!r}")
    date_part = today.replace("-", ".")
    highest: int | None = None
    for raw in existing_tags:
        match = _TAG_PATTERN.match(raw.strip())
        if match is None or match["date"] != date_part:
            continue
        serial = int(match["serial"]) if match["serial"] else 0
        if highest is None or serial > highest:
            highest = serial
    if highest is None:
        return f"v{date_part}"
    return f"v{date_part}.{highest + 1}"


def source_asset_name(tag: str) -> str:
    """Return the release zip's asset name for `tag`."""
    return f"{ASSET_STEM}-{tag}.zip"


def archive_prefix(tag: str) -> str:
    """Return the single top-level directory inside the release zip.

    Matching the asset name's stem keeps the shape of our asset identical to
    GitHub's own source archive, which is the documented fallback when the
    named asset is missing.
    """
    return f"{ASSET_STEM}-{tag}/"


def parse_uv_version(required_version: str) -> str:
    """Strip `tool.uv.required-version` down to the bare version it pins.

    The installer provisions this exact uv build before syncing a release, so
    anything other than an exact `==` pin has no correct answer here and must
    fail the release rather than ship a guess.
    """
    match = _EXACT_PIN_PATTERN.match(required_version.strip())
    if match is None:
        raise ValueError(
            "tool.uv.required-version must be an exact '==' pin to publish "
            f"release.json, got {required_version!r}"
        )
    return match["version"]


def read_uv_version(pyproject: Path) -> str:
    """Read the exact uv version pinned by `pyproject.toml`."""
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return parse_uv_version(data["tool"]["uv"]["required-version"])


def read_python_version(python_version_file: Path) -> str:
    """Read the interpreter version pinned by `.python-version`."""
    value = python_version_file.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"{python_version_file} is empty")
    return value


def build_release_metadata(
    *,
    tag: str,
    sha: str,
    commit_date: str,
    uv_version: str,
    python_version: str,
) -> dict[str, object]:
    """Build the v1 `release.json` payload published alongside the source zip."""
    return {
        "schema_version": SCHEMA_VERSION,
        "tag": tag,
        "sha": sha,
        "commit_date": commit_date,
        "uv_version": uv_version,
        "python_version": python_version,
        "source_asset": source_asset_name(tag),
    }


def _stamp_problems(stamp: str, sha: str, commit_date: str) -> list[str]:
    """Check the `version.txt` build stamp taken from the built archive."""
    if "$Format" in stamp:
        return [
            "version.txt still holds unexpanded $Format placeholders, so the "
            "archive was not produced by git archive"
        ]
    problems: list[str] = []
    sha_match = _STAMP_SHA_PATTERN.search(stamp)
    if sha_match is None:
        problems.append("version.txt has no usable sha line")
    elif sha_match["sha"] != sha:
        problems.append(
            f"version.txt sha {sha_match['sha']} does not match the released "
            f"commit {sha}"
        )
    date_match = _STAMP_DATE_PATTERN.search(stamp)
    if date_match is None:
        problems.append("version.txt has no usable commit-date line")
    elif date_match["date"] != commit_date:
        problems.append(
            f"version.txt commit-date {date_match['date']} does not match the "
            f"released commit date {commit_date}"
        )
    return problems


def _read_archive(
    archive: Path, tag: str
) -> tuple[str | None, list[str] | None, list[str]]:
    """Read the build stamp and the entry list out of the built archive.

    A `None` entry list means the zip could not be opened at all, which is a
    different failure from a zip that opened and turned out to be wrong.
    """
    member = f"{archive_prefix(tag)}version.txt"
    try:
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
            if member not in names:
                return None, names, [f"{archive.name} has no {member}"]
            return bundle.read(member).decode("utf-8"), names, []
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError) as error:
        return None, None, [f"{archive.name} could not be read as a zip: {error}"]


def _contents_problems(archive_name: str, names: Sequence[str], tag: str) -> list[str]:
    """Check the built archive against the required/excluded entry contract."""
    prefix = archive_prefix(tag)
    problems: list[str] = []
    for entry in REQUIRED_ARCHIVE_ENTRIES:
        wanted = f"{prefix}{entry}"
        # `name != wanted` matters for a directory: git archive emits an entry
        # for the directory itself, and a `/**` export-ignore rule leaves that
        # entry behind after removing every file under it. A tree that holds
        # only its own directory entry is empty, not present.
        present = (
            any(name.startswith(wanted) and name != wanted for name in names)
            if entry.endswith("/")
            else wanted in names
        )
        if not present:
            problems.append(f"{archive_name} is missing required entry {entry}")
    problems.extend(
        f"{archive_name} carries excluded tree {tree}"
        for tree in EXCLUDED_ARCHIVE_TREES
        if any(name.startswith(f"{prefix}{tree}") for name in names)
    )
    return problems


def _metadata_problems(metadata_path: Path, expected: dict[str, object]) -> list[str]:
    """Compare the generated `release.json` against what this job intended."""
    try:
        actual = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{metadata_path.name} could not be read as JSON: {error}"]
    if not isinstance(actual, dict):
        return [f"{metadata_path.name} is not a JSON object"]
    problems = [
        f"{metadata_path.name} {key} is {actual.get(key, None)!r}, expected {want!r}"
        for key, want in expected.items()
        if actual.get(key) != want
    ]
    problems.extend(
        f"{metadata_path.name} has unexpected field {key!r}"
        for key in sorted(set(actual) - set(expected))
    )
    return problems


def validate_release(
    *,
    archive: Path,
    metadata_path: Path,
    tag: str,
    sha: str,
    commit_date: str,
    uv_version: str,
    python_version: str,
) -> list[str]:
    """Return every reason the built assets must not be published (empty is safe).

    Publication is the point of no return: assets lock and the release cannot
    be deleted, so everything checkable is checked while the release is still
    a draft.
    """
    problems: list[str] = []
    # The uploaded asset's filename is minted in YAML, so it is the one input
    # here that is not derived from `tag`. Renaming it there without also
    # changing the archive prefix would otherwise pass every other check and
    # publish a release.json naming an asset that does not exist -- which the
    # launcher can only ever resolve through the source-archive fallback.
    if archive.name != source_asset_name(tag):
        problems.append(
            f"archive is named {archive.name}, expected {source_asset_name(tag)}"
        )
    stamp, names, archive_problems = _read_archive(archive, tag)
    problems.extend(archive_problems)
    if names is not None:
        problems.extend(_contents_problems(archive.name, names, tag))
    if stamp is not None:
        problems.extend(_stamp_problems(stamp, sha, commit_date))
    expected = build_release_metadata(
        tag=tag,
        sha=sha,
        commit_date=commit_date,
        uv_version=uv_version,
        python_version=python_version,
    )
    problems.extend(_metadata_problems(metadata_path, expected))
    return problems


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Release job decision helpers.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    gate = subcommands.add_parser(
        "should-release", help="decide whether a push warrants a release"
    )
    gate.add_argument(
        "--paths-from",
        type=Path,
        required=True,
        help="file holding one changed path per line",
    )

    tag = subcommands.add_parser(
        "next-tag", help="compute the next CalVer tag from existing tags on stdin"
    )
    tag.add_argument("--date", required=True, help="UTC date as YYYY-MM-DD")

    metadata = subcommands.add_parser(
        "release-json", help="write the v1 release.json asset"
    )
    metadata.add_argument("--tag", required=True)
    metadata.add_argument("--sha", required=True)
    metadata.add_argument("--commit-date", required=True)
    metadata.add_argument("--output", type=Path, required=True)
    metadata.add_argument("--repo-root", type=Path, default=Path())

    check = subcommands.add_parser(
        "validate", help="check the built assets before publishing"
    )
    check.add_argument("--archive", type=Path, required=True)
    check.add_argument("--metadata", type=Path, required=True)
    check.add_argument("--tag", required=True)
    check.add_argument("--sha", required=True)
    check.add_argument("--commit-date", required=True)
    check.add_argument("--repo-root", type=Path, default=Path())

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one subcommand; return the process exit code."""
    args = _build_parser().parse_args(argv)

    if args.command == "should-release":
        paths = args.paths_from.read_text(encoding="utf-8").splitlines()
        print("true" if should_release(paths) else "false")
        return 0

    if args.command == "next-tag":
        print(next_tag(sys.stdin.read().splitlines(), args.date))
        return 0

    uv_version = read_uv_version(args.repo_root / "pyproject.toml")
    python_version = read_python_version(args.repo_root / ".python-version")

    if args.command == "release-json":
        payload = build_release_metadata(
            tag=args.tag,
            sha=args.sha,
            commit_date=args.commit_date,
            uv_version=uv_version,
            python_version=python_version,
        )
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return 0

    problems = validate_release(
        archive=args.archive,
        metadata_path=args.metadata,
        tag=args.tag,
        sha=args.sha,
        commit_date=args.commit_date,
        uv_version=uv_version,
        python_version=python_version,
    )
    for problem in problems:
        print(f"::error::{problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
