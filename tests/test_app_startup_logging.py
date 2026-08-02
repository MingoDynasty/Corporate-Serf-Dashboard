"""Startup failures and crashes must leave a record in the app log files."""

import logging
import os
import subprocess
import sys
from pathlib import Path

from source.utilities.paths import STATE_DIR_ENV_VAR

REPO_ROOT = Path(__file__).resolve().parents[1]

# Crash both a worker thread and the main thread in one process: the two
# hooks are independent, and debug.log must show both tracebacks.
CRASH_SNIPPET = """
import threading

import source.app  # noqa: F401 -- importing installs the crash hooks


def boom():
    raise ValueError("thread boom")


thread = threading.Thread(target=boom, name="boom-thread")
thread.start()
thread.join()

raise RuntimeError("main boom")
"""


def _run_in_app(snippet: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a snippet against ``source.app`` in a child process.

    Importing ``source.app`` configures process-wide logging and creates
    ``data/logs``, so it stays out of the test process. ``cwd`` is the state
    root, so each test reads log files from its own temp directory.
    """
    environment = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    environment.pop(STATE_DIR_ENV_VAR, None)
    return subprocess.run(
        [sys.executable, "-c", snippet],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def _debug_log(state_root: Path) -> str:
    return (state_root / "data" / "logs" / "debug.log").read_text(encoding="utf-8")


def test_uncaught_crashes_reach_the_log_files(tmp_path: Path) -> None:
    result = _run_in_app(CRASH_SNIPPET, tmp_path)

    assert result.returncode == 1
    log_text = _debug_log(tmp_path)
    assert "Uncaught exception in thread boom-thread" in log_text
    assert "thread boom" in log_text
    assert "Uncaught exception" in log_text
    assert "main boom" in log_text
    # The hooks defer to the defaults, so stderr still shows both tracebacks
    # -- and only stderr: the console handler drops the marked records, so
    # the terminal is not shown each traceback twice.
    assert "thread boom" in result.stderr
    assert "main boom" in result.stderr
    assert "Uncaught exception" not in result.stdout


def test_unreadable_config_reaches_the_log_files(tmp_path: Path) -> None:
    result = _run_in_app("from source.app import main; main()", tmp_path)

    assert result.returncode == 1
    assert "Configuration error" in result.stderr
    assert "Configuration error" in _debug_log(tmp_path)


def test_missing_stats_dir_reaches_the_log_files(tmp_path: Path) -> None:
    missing = tmp_path / "missing-stats"
    (tmp_path / "config.toml").write_text(
        f'stats_dir = "{missing.as_posix()}"\nport = 0\n',
        encoding="utf-8",
    )

    result = _run_in_app("from source.app import main; main()", tmp_path)

    assert result.returncode == 1
    assert "is not an existing directory" in result.stderr
    assert "is not an existing directory" in _debug_log(tmp_path)


def test_urllib3_debug_is_silenced(tmp_path: Path) -> None:
    # The app's own per-attempt request records supersede urllib3's transport
    # chatter (~16% of a sampled debug.log); INFO keeps urllib3's warnings.
    result = _run_in_app(
        "import logging; import source.app;"
        " print(logging.getLogger('urllib3').getEffectiveLevel())",
        tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(logging.INFO)
