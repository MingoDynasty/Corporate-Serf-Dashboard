r"""One-time conversion: stamp ``schema_version`` onto existing durable stores.

Part of the release that introduced the stamp. Every install created before it
holds an unstamped ``data/settings.json``, ``data/playlist_visibility.json``,
and ``data/playlists/*.json``, which the new readers treat as an error state
rather than as version 1 -- there is deliberately no missing-means-v1 rule.
This script retires that population in one pass, so no future reader has to
carry a grandfather case.

Run it exactly once, in this order:

1. Back up ``data/``.
2. Update the app to this release or newer.
3. **Close the app.**
4. Run the conversion (commands below).
5. Relaunch.

Both halves of the ordering matter. The app must be closed, because its
in-process caches would race these rewrites. And the app must already be
updated, because a stamped ``settings.json`` is rejected outright by the
pre-stamp reader, which then reads every setting as unset and lets the startup
bootstrap overwrite the file with a bare ``{"stats_dir": ...}``, destroying the
stored identity.

From a source checkout::

    uv run python scripts/stamp_schema_version.py

On an installed copy, neither uv nor Python is on ``PATH``, and the code lives
in a versioned directory while the state lives at the install root. Run the
release's own interpreter by absolute path::

    $root = Join-Path $env:LOCALAPPDATA 'CorporateSerfDashboard'
    $m = [System.IO.File]::ReadAllText("$root\install.json") | ConvertFrom-Json
    $tag = if ($m.update_policy -eq 'pinned') { $m.pinned_tag } else { $m.tag }
    & "$root\versions\$tag\.venv\Scripts\python.exe" `
        "$root\versions\$tag\scripts\stamp_schema_version.py"

**Which files get converted** is decided by the *state root*, resolved in this
order: ``--state-dir``, then ``CSD_STATE_DIR`` (which the launcher sets around
the app but not around a manual command), then the install root inferred from
this file's own location when it sits in a ``versions/<tag>/scripts`` tree, then
the working directory. The resolved root and how it was chosen are printed
before anything is touched, because converting the wrong tree is the one
mistake this script could make silently.

The per-file state machine is deliberately narrow:

- no stamp, payload valid for v1  -> stamped in place, atomically
- stamp 1, payload valid          -> left alone, so re-runs are no-ops
- anything else                   -> left alone and reported

In particular a file carrying a *different* stamp is never rewritten even if
its payload happens to satisfy v1. Pydantic ignores extra fields, so a looser
rule would let a second run years from now silently downgrade a file written by
a much later release.

The v1 definitions come from the app itself; this script owns no schema
knowledge of its own.
"""

import argparse
import json
import logging
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from source.kovaaks.data_service import validate_playlist_v1  # noqa: E402
from source.utilities.atomic_write import atomic_write_text  # noqa: E402
from source.utilities.paths import STATE_DIR_ENV_VAR  # noqa: E402
from source.utilities.store_schema import (  # noqa: E402
    SCHEMA_VERSION_KEY,
    SchemaPayloadError,
    has_schema_marker,
    is_current_schema_marker,
    stamped_payload,
    strip_schema_marker,
    validate_settings_v1,
    validate_visibility_v1,
)

logger = logging.getLogger("stamp_schema_version")

# The durable layout under a state root. Spelled here rather than imported from
# the services, because their module constants bound to *this* process's state
# root at import — which is exactly the bug that made a manual run on an
# installed copy convert the version directory instead of the install root.
# ``test_stamp_schema_version`` pins these against the services' own constants,
# so the two cannot drift.
SETTINGS_SUBPATH = Path("data/settings.json")
VISIBILITY_SUBPATH = Path("data/playlist_visibility.json")
USER_PLAYLIST_SUBPATH = Path("data/playlists")

# An installed copy runs code out of ``<install root>/versions/<tag>/`` while
# its state lives at the install root. This is the marker directory that tells
# the two layouts apart.
_VERSIONS_DIRECTORY_NAME = "versions"


@dataclass(frozen=True)
class Store:
    """One file to convert: where it is, how to read it, what v1 means."""

    path: Path
    encoding: str
    validate: Callable[[dict], object]


@dataclass
class Report:
    """What the run did, so the summary and the exit code can say it."""

    stamped: list[Path] = field(default_factory=list)
    already_stamped: list[Path] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)


def installed_state_root() -> Path | None:
    """Infer the install root when this file sits in a versioned release tree.

    ``<install root>/versions/<tag>/scripts/stamp_schema_version.py`` means the
    state root is the install root, four levels up. Whichever version directory
    the operator invoked is by construction the one they are running, so this
    needs no manifest read and is right for a pinned install too.
    """
    script = Path(__file__).resolve()
    try:
        version_directory = script.parents[2]
        install_root = script.parents[3]
    except IndexError:
        return None
    if version_directory.name != _VERSIONS_DIRECTORY_NAME:
        return None
    return install_root


def resolve_state_root(explicit: str | None) -> tuple[Path, str]:
    """Pick the state root to convert, and say which rule picked it."""
    if explicit:
        return Path(explicit).resolve(), "--state-dir"
    configured = os.environ.get(STATE_DIR_ENV_VAR)
    if configured:
        return Path(configured).resolve(), STATE_DIR_ENV_VAR
    installed = installed_state_root()
    if installed is not None:
        return installed, "installed layout"
    return Path.cwd().resolve(), "working directory"


def stores(state_root: Path) -> list[Store]:
    """List every file this conversion covers under a root, in a stable order."""
    playlist_directory = state_root / USER_PLAYLIST_SUBPATH
    found = [
        # utf-8-sig only for settings: a Windows-editor BOM is valid legacy
        # settings data (the app's own read contract). The machine-written
        # stores are plain UTF-8, where a BOM is invalid and stays reported.
        Store(state_root / SETTINGS_SUBPATH, "utf-8-sig", validate_settings_v1),
        Store(state_root / VISIBILITY_SUBPATH, "utf-8", validate_visibility_v1),
    ]
    if playlist_directory.is_dir():
        found.extend(
            Store(playlist_file, "utf-8", validate_playlist_v1)
            for playlist_file in sorted(playlist_directory.glob("*.json"))
        )
    return found


def convert(store: Store, report: Report) -> None:
    """Run the state machine over one file. Only one branch ever writes."""
    try:
        raw = store.path.read_text(encoding=store.encoding)
    except FileNotFoundError:
        # Nothing to convert: the app writes it on first use, already stamped.
        return
    except (OSError, UnicodeDecodeError) as exc:
        report.skipped.append((store.path, f"could not be read ({exc})"))
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        report.skipped.append((store.path, f"is not valid JSON ({exc})"))
        return
    if not isinstance(payload, dict):
        report.skipped.append((store.path, "does not hold a JSON object"))
        return

    if has_schema_marker(payload):
        marker = payload[SCHEMA_VERSION_KEY]
        if not is_current_schema_marker(marker):
            report.skipped.append(
                (store.path, f'carries "{SCHEMA_VERSION_KEY}": {marker!r}')
            )
            return
        try:
            store.validate(strip_schema_marker(payload))
        except SchemaPayloadError as exc:
            report.skipped.append((store.path, f"is stamped but {exc}"))
            return
        report.already_stamped.append(store.path)
        return

    try:
        store.validate(payload)
    except SchemaPayloadError as exc:
        report.skipped.append((store.path, str(exc)))
        return

    # Key order is preserved and the stamp goes first, so the diff against the
    # legacy file is one added line. A legacy BOM disappears here, because the
    # file is rewritten from the parsed payload as plain UTF-8, which is what
    # the app has always written.
    text = json.dumps(stamped_payload(payload), indent=2) + "\n"
    atomic_write_text(store.path, text, logger=logger)
    report.stamped.append(store.path)


def run(state_root: Path) -> Report:
    """Convert every store under a state root and return what happened."""
    report = Report()
    for store in stores(state_root):
        convert(store, report)
    return report


def main(argv: list[str] | None = None) -> int:
    """Convert, print the outcome per file, and fail if anything was skipped."""
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--state-dir",
        help=(
            "The install root holding data/. Defaults to CSD_STATE_DIR, then "
            "the install root inferred from this script's location, then the "
            "working directory."
        ),
    )
    arguments = parser.parse_args(argv)
    state_root, chosen_by = resolve_state_root(arguments.state_dir)
    # Printed before any file is touched: converting the wrong tree is the one
    # mistake this script could otherwise make silently.
    print(f"Converting stores under {state_root} (from {chosen_by}).\n")
    report = run(state_root)

    for path in report.stamped:
        print(f"stamped: {path}")
    for path in report.already_stamped:
        print(f"already stamped: {path}")
    for path, reason in report.skipped:
        print(f"NOT converted: {path} {reason}")

    print(
        f"\n{len(report.stamped)} stamped, "
        f"{len(report.already_stamped)} already stamped, "
        f"{len(report.skipped)} left alone."
    )
    if report.skipped:
        print(
            "Every file listed as NOT converted was left exactly as it is. "
            "Fix or delete it, then run this again."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
