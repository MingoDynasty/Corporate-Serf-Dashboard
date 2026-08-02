import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Bound here, before the autouse config fixture replaces the module attribute
# with a canned loader: these tests exercise the real file-reading loader.
from source.config.config_service import ConfigData, load_config
from source.utilities.paths import STATE_DIR_ENV_VAR


def _run_app(cwd: Path) -> subprocess.CompletedProcess[str]:
    """Start the app in ``cwd`` and return once it exits.

    Only startup paths that still exit can be driven this way. A config the app
    accepts makes it serve, and this call would then block until the timeout --
    which is why the stats-directory paths are covered by unit tests instead
    (``tests/test_app_startup_stats_dir.py``).
    """
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
        "polling_interval = 1000  # missing the required port",
        "polling_interval = 1000\n"
        "port = 8050\n"
        "sens_round_decimal_places = 1\n"
        "kovaaks_api_timeout_seconds = 0",
    ],
    ids=["missing", "invalid-toml", "missing-port", "non-positive-timeout"],
)
def test_startup_with_missing_or_invalid_config_exits_cleanly(
    tmp_path: Path,
    config_contents: str | None,
) -> None:
    # Resolved because the app names the config path it loaded, and
    # ``state_dir`` resolves the working directory before joining it.
    tmp_path = tmp_path.resolve()
    config_path = tmp_path / "config.toml"
    if config_contents is not None:
        config_path.write_text(config_contents, encoding="utf-8")

    result = _run_app(tmp_path)

    assert result.returncode == 1
    # The startup build-identity line is the only stdout a failed start emits;
    # a bug report about a broken config still says which build produced it.
    stdout_lines = result.stdout.splitlines()
    assert len(stdout_lines) == 1
    assert "| Build " in stdout_lines[0]
    assert "Traceback" not in result.stderr
    # One actionable line: which file failed to load, and what to do about it.
    assert "\n" not in result.stderr.strip()
    assert str(config_path) in result.stderr
    assert "copy example.toml to config.toml" in result.stderr


def test_unknown_config_keys_are_named_in_one_warning_and_ignored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Retired and misspelled keys warn but never block startup.

    Tolerating them is what keeps update and rollback boundaries safe, so a
    config still carrying the relocated identity keys has to load.
    """
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "port = 8050\n"
        'stats_dir = "S:/SteamLibrary/.../stats"\n'
        'kovaaks_username = "MingoDynasty"\n'
        'steam_id = "76561197986713986"\n'
        "polling_intervall = 1000\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(STATE_DIR_ENV_VAR, str(tmp_path))

    with caplog.at_level(logging.WARNING):
        config = load_config()

    assert config.port == 8050
    # Silently dropped by pydantic, so the warning is the only feedback.
    assert not hasattr(config, "kovaaks_username")
    assert not hasattr(config, "stats_dir")
    warnings = [
        record for record in caplog.records if record.levelno >= logging.WARNING
    ]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert "stats_dir" in message
    assert "kovaaks_username" in message
    assert "steam_id" in message
    assert "polling_intervall" in message


def test_tuning_fields_default_when_omitted() -> None:
    """port is the only required field; the tuning knobs default."""
    config = ConfigData(port=8050)

    assert config.polling_interval == 1000
    assert config.sens_round_decimal_places == 1
