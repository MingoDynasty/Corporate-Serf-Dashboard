"""
Resolve the identity of the running build: release tag, commit SHA, and date.

Precedence, highest first:

1. ``install.json`` — the install manifest written by the installer/launcher.
   The only layer that can know the release tag. A missing manifest is the
   normal development case, not an error.
2. ``version.txt`` — a git ``export-subst`` stamp expanded by ``git archive``,
   which is what GitHub's zip/release downloads run. Still holding the raw
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

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = "install.json"
MANIFEST_SCHEMA_VERSION = 1
VERSION_STAMP_FILENAME = "version.txt"

# An unexpanded export-subst placeholder still looks like "$Format:%H$".
_UNEXPANDED_PLACEHOLDER_MARKER = "$Format"
_GIT_TIMEOUT_SECONDS = 5
_SHORT_SHA_LENGTH = 7

# The version stamp ships with the code, and in an installed layout the code
# directory is not the working directory — so resolve it from this file rather
# than the CWD. The manifest, by contrast, belongs to the install (state) root,
# which is the CWD until the state-root work lands.
_CODE_ROOT = Path(__file__).resolve().parents[2]


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


def _from_manifest() -> BuildInfo | None:
    """Read build identity from the installer-written manifest."""
    manifest_path = Path(MANIFEST_FILENAME)
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
    for read_layer in (_from_manifest, _from_version_stamp, _from_git):
        build_info = read_layer()
        if build_info is not None:
            return build_info
    return BuildInfo(sha=None, commit_date=None, tag=None, source="unknown")
