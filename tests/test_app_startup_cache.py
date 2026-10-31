"""Startup serves when the API cache can't be built or written.

Caches are disposable (AGENTS.md, Cache Conventions), so a cache path this boot
can't write costs the cache, never the start. Driven in a child process, like
the other whole-startup tests: importing ``source.app`` reconfigures
process-wide logging, and ``main()`` would serve forever if the server were not
stubbed out. The stub answers one ``/health`` request through the real Flask
app instead of binding a port, so a pass means startup reached serving and the
app answered.
"""

import os
import stat
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from source.utilities.paths import STATE_DIR_ENV_VAR

REPO_ROOT = Path(__file__).resolve().parents[1]

# Detection is stubbed so what a developer's machine has installed can't
# decide what startup does.
STARTUP_SNIPPET = """
import source.app as app
from source.config import stats_dir_detection

stats_dir_detection.detect_stats_dir = lambda: None


def serve(server, *args, **kwargs):
    print("health", server.test_client().get("/health").status_code)


app.bind_server_socket = lambda port, host="127.0.0.1": []
app.serve = serve

app.main()
"""

MAPPING_RELATIVE_PATH = Path(
    "data",
    "cache",
    "scenario_leaderboards",
    "scenario_name_to_leaderboard_id.json",
)
SEED_WARNING = (
    "Could not write the bundled leaderboard IDs to the mapping cache; "
    "serving without them: "
)
CACHE_TREE_WARNING = "Could not create the API cache folders; serving anyway: "


@pytest.fixture
def state_root(tmp_path: Path) -> Path:
    """Give the child process a state root of its own, below ``tmp_path``."""
    root = tmp_path / "state"
    root.mkdir()
    (root / "config.toml").write_text("port = 8050\n", encoding="utf-8")
    return root


def _run_startup(state_root: Path) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    environment.pop(STATE_DIR_ENV_VAR, None)
    return subprocess.run(
        [sys.executable, "-c", STARTUP_SNIPPET],
        cwd=state_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def _warning_lines(state_root: Path, message: str) -> list[str]:
    log_text = (state_root / "data" / "logs" / "debug.log").read_text(encoding="utf-8")
    return [
        line for line in log_text.splitlines() if "WARNING" in line and message in line
    ]


def _read_only_mapping(state_root: Path) -> Path:
    mapping = state_root / MAPPING_RELATIVE_PATH
    mapping.parent.mkdir(parents=True)
    # Empty, so the bundled corpus has IDs to add and the merge must write.
    mapping.write_text("{}\n", encoding="utf-8")
    mapping.chmod(stat.S_IREAD)
    return mapping


def _directory_at_mapping(state_root: Path) -> Path:
    mapping = state_root / MAPPING_RELATIVE_PATH
    mapping.mkdir(parents=True)
    return mapping


def _file_at_cache_directory(state_root: Path) -> Path:
    blocker = state_root / "data" / "cache" / "benchmarks"
    blocker.parent.mkdir(parents=True)
    blocker.write_text("not a directory\n", encoding="utf-8")
    return blocker


@pytest.mark.parametrize(
    ("break_cache", "warning"),
    [
        pytest.param(
            _read_only_mapping,
            SEED_WARNING,
            id="read-only-mapping",
            # POSIX replaces a read-only file whose directory is writable; only
            # Windows refuses, which is where the app ships.
            marks=pytest.mark.skipif(
                sys.platform != "win32", reason="Windows refuses the replace"
            ),
        ),
        pytest.param(_directory_at_mapping, SEED_WARNING, id="directory-at-mapping"),
        pytest.param(
            _file_at_cache_directory,
            CACHE_TREE_WARNING,
            id="file-at-cache-directory",
        ),
    ],
)
def test_startup_serves_when_the_cache_cannot_be_written(
    state_root: Path,
    break_cache: Callable[[Path], Path],
    warning: str,
) -> None:
    broken = break_cache(state_root)
    try:
        result = _run_startup(state_root)
    finally:
        # Let the temp-directory cleanup delete it.
        if broken.is_file():
            broken.chmod(stat.S_IREAD | stat.S_IWRITE)

    assert result.returncode == 0, result.stderr
    assert "health 200" in result.stdout.splitlines()
    # One line, naming the path that broke.
    [line] = _warning_lines(state_root, warning)
    assert broken.name in line
