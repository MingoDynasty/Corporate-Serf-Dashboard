import os
import subprocess
import sys
from pathlib import Path

import pytest

from source.utilities.paths import STATE_DIR_ENV_VAR

CONFIG_ERROR_MESSAGE = (
    "Configuration error: copy example.toml to config.toml and set stats_dir."
)


def _run_app(cwd: Path) -> subprocess.CompletedProcess[str]:
    """Start the app in ``cwd`` and return once it exits."""
    repo_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(repo_root), environment.get("PYTHONPATH")])
    )
    # These tests drive the app through the config file in ``cwd``. An
    # inherited state root would point it at a different config.toml -- and a
    # valid one would start the server and hang the suite.
    environment.pop(STATE_DIR_ENV_VAR, None)

    return subprocess.run(
        [sys.executable, "-m", "source.app"],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


@pytest.mark.parametrize(
    "config_contents",
    [
        None,
        "not valid toml",
        'stats_dir = "missing required fields"',
        'stats_dir = "x"\n'
        "polling_interval = 1000\n"
        "port = 8080\n"
        "sens_round_decimal_places = 1\n"
        "kovaaks_api_timeout_seconds = 0",
    ],
    ids=["missing", "invalid-toml", "invalid-schema", "non-positive-timeout"],
)
def test_startup_with_missing_or_invalid_config_exits_cleanly(
    tmp_path: Path,
    config_contents: str | None,
) -> None:
    if config_contents is not None:
        (tmp_path / "config.toml").write_text(config_contents, encoding="utf-8")

    result = _run_app(tmp_path)

    assert result.returncode == 1
    # The startup build-identity line is the only stdout a failed start emits;
    # a bug report about a broken config still says which build produced it.
    stdout_lines = result.stdout.splitlines()
    assert len(stdout_lines) == 1
    assert "| Build " in stdout_lines[0]
    assert result.stderr.strip() == CONFIG_ERROR_MESSAGE
    assert "Traceback" not in result.stderr


def test_startup_with_missing_stats_dir_exits_cleanly(tmp_path: Path) -> None:
    tmp_path = tmp_path.resolve()
    missing_stats_dir = tmp_path / "no-such-stats-dir"
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f'stats_dir = "{missing_stats_dir.as_posix()}"\n'
        "polling_interval = 1000\n"
        "port = 8080\n"
        "sens_round_decimal_places = 1\n",
        encoding="utf-8",
    )

    result = _run_app(tmp_path)

    assert result.returncode == 1
    # Same as above: the build-identity line is the only expected stdout.
    stdout_lines = result.stdout.splitlines()
    assert len(stdout_lines) == 1
    assert "| Build " in stdout_lines[0]
    assert "Traceback" not in result.stderr
    # One actionable line: what was configured, where to change it, what to set.
    assert "\n" not in result.stderr.strip()
    assert missing_stats_dir.as_posix() in result.stderr
    assert str(config_path) in result.stderr
    assert "FPSAimTrainer" in result.stderr
