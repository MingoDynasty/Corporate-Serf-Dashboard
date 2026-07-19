"""
Resolve the identity of the running build: release tag, commit SHA, and date.

Precedence, highest first:

1. ``install.json`` — the install manifest written by the installer/launcher
   into the state root. The only layer that can know the release tag. It is authoritative only
   when it *corroborates* the running code: its ``sha`` must equal the SHA in
   the expanded stamp beside the code. The manifest lives with the install's
   state, which during an update still describes the previous version while
   the new version is already running — an uncorroborated manifest would make
   the new build report the old identity, and the launcher would never
   promote it. A missing manifest is the normal development case, not an
   error.
2. ``version.txt`` — a git ``export-subst`` stamp expanded by ``git archive``,
   which is what GitHub's zip/release downloads run. It ships with the code,
   so it always describes the code actually running. Still holding the raw
   placeholders means this is a git checkout, so fall through.
3. ``git`` — ask the checkout directly.
4. ``unknown`` — nothing could identify the build.

Every user-visible build string (startup log line, header tooltip, browser
title, ``/health``) derives from this one reader.
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from source.utilities.paths import package_root, state_dir

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = "install.json"
MANIFEST_SCHEMA_VERSION = 1
VERSION_STAMP_FILENAME = "version.txt"

# An unexpanded export-subst placeholder still looks like "$Format:%H$".
_UNEXPANDED_PLACEHOLDER_MARKER = "$Format"
_GIT_TIMEOUT_SECONDS = 5
_SHORT_SHA_LENGTH = 7

# The stamp ships with the code, so it lives in the package root; the manifest
# belongs to the install's state root, which survives version swaps. In a dev
# checkout the two are the same directory.
_CODE_ROOT = package_root()


@dataclass(frozen=True)
class BuildInfo:
    """Identity of the running build, resolved once per process."""

    sha: str | None
    commit_date: str | None
    tag: str | None
    source: str

    @property
    def short_sha(self) -> str:
        """Abbreviate the SHA for display."""
        if not self.sha:
            return "unknown"
        return self.sha[:_SHORT_SHA_LENGTH]

    @property
    def short_description(self) -> str:
        """Format the identity as ``<short sha> (<commit date>)``."""
        return f"{self.short_sha} ({self.commit_date or 'unknown'})"

    @property
    def release_label(self) -> str:
        """Name the release this build came from: a tag, ``dev``, or unknown."""
        if self.tag:
            return self.tag
        if self.source == "git":
            return "dev"
        return "unknown"


def _optional_string(value: object) -> str | None:
    """Accept a non-empty string from untrusted JSON, else ``None``."""
    if isinstance(value, str) and value:
        return value
    return None


def _load_manifest(manifest_path: Path) -> dict[str, object] | None:
    """Read the manifest file, or ``None`` if it is absent or not an object."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None  # No manifest: a checkout, not an install.
    except OSError, UnicodeDecodeError, json.JSONDecodeError:
        logger.warning("Ignoring unreadable %s", manifest_path, exc_info=True)
        return None

    if not isinstance(manifest, dict):
        logger.warning("Ignoring %s: expected a JSON object", manifest_path)
        return None
    return manifest


def _from_manifest(stamped: BuildInfo | None) -> BuildInfo | None:
    """Read build identity from the manifest, if it describes the running code.

    ``stamped`` is the identity from the stamp beside the code, or ``None``
    when there is no expanded stamp to corroborate against.
    """
    manifest_path = state_dir() / MANIFEST_FILENAME
    manifest = _load_manifest(manifest_path)
    if manifest is None:
        return None

    schema_version = manifest.get("schema_version")
    if schema_version != MANIFEST_SCHEMA_VERSION:
        logger.warning(
            "Ignoring %s: unsupported schema_version %r",
            manifest_path,
            schema_version,
        )
        return None

    sha = _optional_string(manifest.get("sha"))
    if not sha:
        logger.warning("Ignoring %s: no sha", manifest_path)
        return None

    if stamped is None or stamped.sha != sha:
        # Expected during an update: the manifest still names the previous
        # version while this (new) code is on trial. The stamp is what
        # describes the running build, so let it answer.
        logger.info(
            "Ignoring %s: it describes %s, which is not the running code",
            manifest_path,
            sha,
        )
        return None

    return BuildInfo(
        sha=sha,
        commit_date=_optional_string(manifest.get("commit_date")),
        tag=_optional_string(manifest.get("tag")),
        source="manifest",
    )


def _parse_version_stamp(text: str) -> dict[str, str]:
    """Parse the stamp's ``key: value`` lines, ignoring comments and blanks."""
    values = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip()
    return values


def _from_version_stamp() -> BuildInfo | None:
    """Read build identity from the ``git archive``-expanded version stamp."""
    stamp_path = _CODE_ROOT / VERSION_STAMP_FILENAME
    try:
        text = stamp_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError, UnicodeDecodeError:
        logger.warning("Ignoring unreadable %s", stamp_path, exc_info=True)
        return None

    values = _parse_version_stamp(text)
    sha = values.get("sha")
    if not sha or _UNEXPANDED_PLACEHOLDER_MARKER in sha:
        return None  # Unexpanded: this is a checkout, so let git answer.

    return BuildInfo(
        sha=sha,
        commit_date=values.get("commit-date") or None,
        tag=None,  # An archive carries no tag; only the manifest knows it.
        source="archive",
    )


def _from_git() -> BuildInfo | None:
    """Read build identity from the surrounding git checkout, if there is one."""
    try:
        result = subprocess.run(
            ["git", "show", "--no-patch", "--format=%H%n%cs", "HEAD"],
            cwd=_CODE_ROOT,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except OSError, subprocess.SubprocessError:
        # No git on PATH, or it hung: not identifying the build is not fatal.
        return None

    if result.returncode != 0:
        return None

    lines = result.stdout.split()
    if len(lines) < 2:
        return None

    return BuildInfo(sha=lines[0], commit_date=lines[1], tag=None, source="git")


@cache
def get_build_info() -> BuildInfo:
    """Resolve the running build's identity, caching the result."""
    # The stamp is read first because the manifest is only trusted when the
    # stamp corroborates it, not because it outranks the manifest.
    stamped = _from_version_stamp()
    resolved = _from_manifest(stamped) or stamped or _from_git()
    if resolved is not None:
        return resolved
    return BuildInfo(sha=None, commit_date=None, tag=None, source="unknown")
