"""Startup removes the temp files that killed writes left beside their files.

Driven in a child process, like the other whole-startup tests: importing
``source.app`` reconfigures process-wide logging and installs crash hooks, and
``main()`` would serve forever if the server were not stubbed out. A startup
costs seconds, so one run serves every test that reads what it swept.
"""

import contextlib
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from source.kovaaks import api_service
from source.utilities import atomic_write, store_schema
from source.utilities.file_keys import safe_file_key
from source.utilities.paths import STATE_DIR_ENV_VAR

REPO_ROOT = Path(__file__).resolve().parents[1]

STARTUP_SNIPPET = """
import source.app as app
from source.config import stats_dir_detection

stats_dir_detection.detect_stats_dir = lambda: None

app.bind_server_socket = lambda port, host="127.0.0.1": []
app.serve = lambda *args, **kwargs: None

app.main()
"""

# One file per kind of folder the writers put temps in, named as the app names
# it, relative to the state root's ``data/``. The cache's lies two folders down.
DESTINATIONS = {
    "data": Path("settings.json"),
    "playlists": Path("playlists", "Audit Playlist [AuditCode].json"),
    "scenario_notes": Path(
        "scenario_notes", f"{safe_file_key('1wall 6targets small')}.json"
    ),
    "cache": Path(
        "cache", "leaderboard", "user_rank", safe_file_key("Audit"), "98765.json"
    ),
}

DAY_SECONDS = 24 * 60 * 60


def _left_by_a_kill(name: str) -> list[str]:
    """Name what a writer killed before its replace leaves beside ``name``."""
    return [f".{name}.4242.18236.tmp", f".{name}.corrupt.4242.18236.tmp"]


def _near_misses(name: str) -> list[str]:
    """Name files that look like a writer's temp and are not one."""
    stem = name.removesuffix(".json")
    return [
        f"{name}.4242.18238.tmp",
        f".{name}.4242.tmp",
        f".{name}.4242.x18239.tmp",
        f".{name}.4242.18240.TMP",
        f".{name}.4242.18241.tmp.bak",
        f".{stem}.txt.4242.18243.tmp",
    ]


def _set_mtime(path: Path, mtime: float) -> None:
    os.utime(path, (mtime, mtime))


def _plant(destination: Path) -> None:
    """Leave a killed write's temps beside ``destination``, with what must stay."""
    directory = destination.parent
    directory.mkdir(parents=True, exist_ok=True)
    name = destination.name
    stale = time.time() - DAY_SECONDS

    backup = directory / f"{name}.corrupt-1.bak"
    backup.write_bytes(b"the unusable incumbent")
    house_temp, claim_temp = (directory / temp for temp in _left_by_a_kill(name))
    house_temp.write_text("{}", encoding="utf-8")
    # A kill after the backup claim leaves the claim's temp as a second link to
    # the backup, so removing it must leave the backup's bytes in place.
    os.link(backup, claim_temp)
    for near_miss in _near_misses(name):
        (directory / near_miss).write_text("{}", encoding="utf-8")
    exact_name_directory = directory / f".{name}.4242.18242.tmp"
    exact_name_directory.mkdir()
    for path in (house_temp, backup, exact_name_directory):
        _set_mtime(path, stale)
    for near_miss in _near_misses(name):
        _set_mtime(directory / near_miss, stale)

    # Newer than the process: a write still in flight.
    fresh = directory / f".{name}.4242.18237.tmp"
    fresh.write_text("{}", encoding="utf-8")
    _set_mtime(fresh, time.time() + DAY_SECONDS)


@pytest.fixture(scope="module")
def swept_state_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Plant every folder kind's leftovers, then run startup once over them."""
    state_root = tmp_path_factory.mktemp("state")
    (state_root / "config.toml").write_text("port = 8050\n", encoding="utf-8")
    for destination in DESTINATIONS.values():
        _plant(state_root / "data" / destination)

    environment = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    environment.pop(STATE_DIR_ENV_VAR, None)
    result = subprocess.run(
        [sys.executable, "-c", STARTUP_SNIPPET],
        cwd=state_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return state_root


@pytest.mark.parametrize("kind", DESTINATIONS)
def test_startup_removes_only_the_stale_temps_a_killed_write_left(
    swept_state_root: Path,
    kind: str,
) -> None:
    destination = swept_state_root / "data" / DESTINATIONS[kind]
    directory = destination.parent
    name = destination.name

    for temp in _left_by_a_kill(name):
        assert not (directory / temp).exists(), temp
    assert (directory / f"{name}.corrupt-1.bak").read_bytes() == (
        b"the unusable incumbent"
    )
    assert (directory / f".{name}.4242.18237.tmp").is_file()
    assert (directory / f".{name}.4242.18242.tmp").is_dir()
    for near_miss in _near_misses(name):
        assert (directory / near_miss).is_file(), near_miss


def test_startup_logs_how_many_temps_it_removed(swept_state_root: Path) -> None:
    info_log = (swept_state_root / "data" / "logs" / "info.log").read_text(
        encoding="utf-8"
    )

    assert (
        f"Removed {2 * len(DESTINATIONS)} temp file(s) left by interrupted writes."
        in info_log
    )


def test_the_sweep_removes_the_temp_name_of_every_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each writer's own temp name, stale, is one the sweep removes.

    The sweep matches names rather than asking the writers, so a writer that
    renames its temp would otherwise leave its leftovers unswept in silence.
    """
    logger = logging.getLogger(__name__)
    destination = tmp_path / "settings.json"
    destination.write_text("not json", encoding="utf-8")
    temp_names: list[str] = []

    # The house temp exists while the replace hook runs.
    atomic_write.atomic_write_text(
        destination,
        "{}",
        logger=logger,
        before_replace=lambda: temp_names.extend(
            path.name for path in tmp_path.glob(".*.tmp")
        ),
    )

    real_link = os.link

    def record_the_claimed_temp(source: Path, target: Path) -> None:
        temp_names.append(Path(source).name)
        real_link(source, target)

    monkeypatch.setattr(store_schema.os, "link", record_the_claimed_temp)
    store_schema.back_up_unusable_store(destination)

    real_replace = api_service.replace_with_retry

    def record_the_replaced_temp(
        source: Path, target: Path, *, logger: logging.Logger
    ) -> None:
        temp_names.append(source.name)
        real_replace(source, target, logger=logger)

    monkeypatch.setattr(api_service, "replace_with_retry", record_the_replaced_temp)
    api_service._write_json(tmp_path / "page_1.json", {})

    assert len(set(temp_names)) == 3, temp_names
    for temp_name in temp_names:
        leftover = tmp_path / temp_name
        leftover.write_text("{}", encoding="utf-8")
        _set_mtime(leftover, time.time() - DAY_SECONDS)

    removed = atomic_write.remove_stale_temp_files(
        tmp_path, older_than=time.time(), logger=logger
    )

    assert removed == 3
    assert not list(tmp_path.glob(".*.tmp"))


def test_a_temp_that_cannot_be_removed_is_logged_and_left(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A temp held open, by the indexer say, must not stop startup or the sweep."""
    held, free = (tmp_path / temp for temp in _left_by_a_kill("settings.json"))
    for leftover in (held, free):
        leftover.write_text("{}", encoding="utf-8")
        _set_mtime(leftover, time.time() - DAY_SECONDS)
    real_unlink = os.unlink

    def refuse_the_held_temp(path: str) -> None:
        if Path(path) == held:
            raise PermissionError(32, "held open by the indexer")
        real_unlink(path)

    monkeypatch.setattr(atomic_write.os, "unlink", refuse_the_held_temp)

    with caplog.at_level(logging.WARNING):
        removed = atomic_write.remove_stale_temp_files(
            tmp_path, older_than=time.time(), logger=logging.getLogger(__name__)
        )

    assert removed == 1
    assert held.exists()
    assert not free.exists()
    assert f'Could not remove the stale temp "{held}"' in caplog.text


def _link_directory(kind: str, link: Path, target: Path) -> None:
    """Make ``link`` a directory junction or symbolic link to ``target``."""
    if kind == "junction":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"cannot create a directory symbolic link: {error}")


@pytest.mark.skipif(sys.platform != "win32", reason="junctions are Windows-only")
@pytest.mark.parametrize("kind", ["junction", "symlink"])
def test_the_sweep_never_follows_a_directory_link_out_of_its_tree(
    tmp_path: Path,
    kind: str,
) -> None:
    """A link under the cache can point anywhere, and nothing there is ours."""
    cache = tmp_path / "cache"
    nested = cache / "leaderboard"
    outside = tmp_path / "outside"
    nested.mkdir(parents=True)
    outside.mkdir()
    ours = nested / ".98765.json.123.456.tmp"
    not_ours = outside / ".settings.json.123.456.tmp"
    for leftover in (ours, not_ours):
        leftover.write_text("{}", encoding="utf-8")
        _set_mtime(leftover, time.time() - DAY_SECONDS)
    _link_directory(kind, cache / "linked", outside)

    removed = atomic_write.remove_stale_temp_files(
        cache,
        older_than=time.time(),
        logger=logging.getLogger(__name__),
        recursive=True,
    )

    assert removed == 1
    assert not ours.exists()
    assert not_ours.is_file()


class _TypeQueryFails:
    """A directory entry whose ``method`` raises, as a metadata query may."""

    def __init__(self, entry: os.DirEntry[str], method: str) -> None:
        self._entry = entry
        self._method = method

    def __getattr__(self, attribute: str) -> object:
        if attribute != self._method:
            return getattr(self._entry, attribute)

        def refuse(*args: object, **kwargs: object) -> bool:
            raise PermissionError(5, "Access is denied")

        return refuse


def test_an_entry_whose_type_cannot_be_read_is_logged_and_left(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A failed type query must not stop startup or the entries after it."""
    folder = tmp_path / "leaderboard"
    folder.mkdir()
    unread, free = (tmp_path / temp for temp in _left_by_a_kill("settings.json"))
    for leftover in (unread, free):
        leftover.write_text("{}", encoding="utf-8")
        _set_mtime(leftover, time.time() - DAY_SECONDS)
    failing = {folder.name: "is_dir", unread.name: "is_file"}
    real_scandir = os.scandir

    def scandir_whose_type_queries_fail(
        path: Path,
    ) -> contextlib.nullcontext[list[object]]:
        with real_scandir(path) as scan:
            # The failures come first, so the entry after them shows the
            # sweep carried on.
            entries = sorted(scan, key=lambda entry: entry.name not in failing)
        return contextlib.nullcontext(
            [
                _TypeQueryFails(entry, failing[entry.name])
                if entry.name in failing
                else entry
                for entry in entries
            ]
        )

    monkeypatch.setattr(atomic_write.os, "scandir", scandir_whose_type_queries_fail)

    with caplog.at_level(logging.WARNING):
        removed = atomic_write.remove_stale_temp_files(
            tmp_path,
            older_than=time.time(),
            logger=logging.getLogger(__name__),
            recursive=True,
        )

    assert removed == 1
    assert unread.exists()
    assert not free.exists()
    for path in (folder, unread):
        assert f'Could not check "{path}" for stale temp files' in caplog.text
