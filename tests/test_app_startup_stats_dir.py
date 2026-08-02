"""Startup serves with or without a usable stats directory.

Driven in a child process, like the other whole-startup tests: importing
``source.app`` reconfigures process-wide logging and installs crash hooks, and
``main()`` would serve forever if the server were not stubbed out. The snippet
replaces only the two calls that would block -- everything before them, the
resolution of the pinned stats directory included, is the real startup path.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from source.utilities.paths import STATE_DIR_ENV_VAR

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def state_root(tmp_path: Path) -> Path:
    """Give the child process a state root of its own.

    Below ``tmp_path`` rather than at it, so nothing the test process's own
    fixtures leave in ``tmp_path`` can end up being read as the child's
    config, settings, or logs.
    """
    root = tmp_path / "state"
    root.mkdir()
    return root


STARTUP_SNIPPET = """
import source.app as app

app.bind_server_socket = lambda port: []
app.serve = lambda *args, **kwargs: None

app.main()
"""


def _run_startup(state_root: Path) -> subprocess.CompletedProcess[str]:
    """Run the app's startup to the point of serving, in ``state_root``."""
    environment = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    environment.pop(STATE_DIR_ENV_VAR, None)
    (state_root / "config.toml").write_text("port = 8050\n", encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-c", STARTUP_SNIPPET],
        cwd=state_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def _write_settings(state_root: Path, payload: dict[str, str]) -> None:
    settings_path = state_root / "data" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(payload), encoding="utf-8")


def _debug_log(state_root: Path) -> str:
    return (state_root / "data" / "logs" / "debug.log").read_text(encoding="utf-8")


def test_startup_scans_and_watches_a_usable_stats_dir(state_root: Path) -> None:
    stats_dir = state_root / "stats"
    stats_dir.mkdir()
    _write_settings(state_root, {"stats_dir": str(stats_dir)})

    result = _run_startup(state_root)

    assert result.returncode == 0, result.stderr
    log_text = _debug_log(state_root)
    assert "CSV startup load complete" in log_text
    assert f"Monitoring directory: {stats_dir}" in log_text


@pytest.mark.parametrize("configured", [None, "", "no-such-stats-dir"])
def test_startup_without_a_usable_stats_dir_serves_anyway(
    state_root: Path,
    configured: str | None,
) -> None:
    """Unset, cleared, and moved-away all skip the scan and the watchdog."""
    if configured is not None:
        _write_settings(state_root, {"stats_dir": configured})

    result = _run_startup(state_root)

    assert result.returncode == 0, result.stderr
    log_text = _debug_log(state_root)
    assert "No usable KovaaK's stats directory" in log_text
    # The two consumers the missing directory would have crashed.
    assert "CSV startup load complete" not in log_text
    assert "Monitoring directory" not in log_text
    # One line, naming what was configured so a moved library is diagnosable.
    if configured:
        assert f'"{configured}" is not an existing directory' in log_text
    else:
        assert "not configured" in log_text
