"""Startup failures and crashes must leave a record in the app log files."""

import logging
import os
import subprocess
import sys
from pathlib import Path

from source.utilities.paths import STATE_DIR_ENV_VAR

REPO_ROOT = Path(__file__).resolve().parents[1]

UNSET_USERNAME_NOTICE = (
    "KovaaK's username not configured -- scenario position lookups "
    "disabled (set it in Settings)."
)

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


def _debug_log_if_written(state_root: Path) -> str:
    """Read debug.log, or "" when nothing was logged.

    The rotating handlers open lazily, so a run that logs nothing at all
    leaves no file behind -- which is itself a pass for absence assertions.
    """
    log_file = state_root / "data" / "logs" / "debug.log"
    return log_file.read_text(encoding="utf-8") if log_file.exists() else ""


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


def test_unset_username_is_reported_once_at_startup(tmp_path: Path) -> None:
    # Row 1's console half: an unset username is a supported state, so it is
    # said once at boot instead of on every scenario switch.
    result = _run_in_app(
        "from source.app import log_rank_lookup_availability;"
        " log_rank_lookup_availability()",
        tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert _debug_log(tmp_path).count(UNSET_USERNAME_NOTICE) == 1


def test_configured_username_is_not_reported_at_startup(tmp_path: Path) -> None:
    result = _run_in_app(
        "from source.app import log_rank_lookup_availability;"
        " from source.config.settings_service import"
        " KOVAAKS_USERNAME_KEY, save_settings;"
        " save_settings({KOVAAKS_USERNAME_KEY: 'MingoDynasty'});"
        " log_rank_lookup_availability()",
        tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert UNSET_USERNAME_NOTICE not in _debug_log_if_written(tmp_path)


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
