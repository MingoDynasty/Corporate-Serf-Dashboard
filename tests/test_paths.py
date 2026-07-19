"""State-root (``CSD_STATE_DIR``) and package-root path resolution."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from source.utilities.paths import STATE_DIR_ENV_VAR, package_root, state_dir

REPO_ROOT = Path(__file__).resolve().parents[1]

# Import-time path constants are resolved once per process, so the only honest
# way to check them under a different state root is a fresh interpreter.
PROBE_SCRIPT = """
import json

from source import app
from source.config.config_service import config_file_path
from source.kovaaks import api_service, data_service, playlist_visibility_service

print(
    json.dumps(
        {
            "config": str(config_file_path()),
            "logs": str(app.LOG_DIR),
            "cache": str(api_service.CACHE_DIR),
            "playlists": str(data_service.USER_PLAYLIST_DIRECTORY_PATH),
            "benchmarks": str(data_service.BUNDLED_PLAYLIST_DIRECTORY_PATH),
            "preferences": str(playlist_visibility_service.PREFERENCES_FILE_PATH),
        }
    )
)
"""


def _probe_paths(cwd: Path, state_dir_value: str | None) -> dict[str, Path]:
    """Resolve the app's path constants in a fresh interpreter."""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(REPO_ROOT), environment.get("PYTHONPATH")])
    )
    if state_dir_value is None:
        environment.pop(STATE_DIR_ENV_VAR, None)
    else:
        environment[STATE_DIR_ENV_VAR] = state_dir_value

    result = subprocess.run(
        [sys.executable, "-c", PROBE_SCRIPT],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return {key: Path(value) for key, value in json.loads(result.stdout).items()}


def test_state_dir_defaults_to_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(STATE_DIR_ENV_VAR, raising=False)
    assert state_dir() == Path.cwd().resolve()


def test_state_dir_uses_environment_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(STATE_DIR_ENV_VAR, str(tmp_path))
    assert state_dir() == tmp_path.resolve()


def test_empty_state_dir_falls_back_to_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(STATE_DIR_ENV_VAR, "")
    assert state_dir() == Path.cwd().resolve()


def test_package_root_is_independent_of_cwd(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert package_root() == REPO_ROOT
    assert (package_root() / "source" / "utilities" / "paths.py").is_file()


def test_state_paths_follow_the_state_root(tmp_path: Path) -> None:
    state_root = (tmp_path / "state").resolve()
    state_root.mkdir()
    working_dir = tmp_path / "cwd"
    working_dir.mkdir()

    paths = _probe_paths(working_dir, str(state_root))

    assert paths["config"] == state_root / "config.toml"
    assert paths["logs"] == state_root / "data" / "logs"
    assert paths["cache"] == state_root / "data" / "cache"
    assert paths["playlists"] == state_root / "data" / "playlists"
    assert paths["preferences"] == state_root / "data" / "preferences.json"
    # Bundled assets ship with the code, so they ignore the state root.
    assert paths["benchmarks"] == REPO_ROOT / "resources" / "benchmarks"


def test_unset_state_dir_keeps_cwd_relative_behavior(tmp_path: Path) -> None:
    tmp_path = tmp_path.resolve()
    paths = _probe_paths(tmp_path, None)

    assert paths["config"] == tmp_path / "config.toml"
    assert paths["logs"] == tmp_path / "data" / "logs"
    assert paths["cache"] == tmp_path / "data" / "cache"
    assert paths["playlists"] == tmp_path / "data" / "playlists"
    assert paths["preferences"] == tmp_path / "data" / "preferences.json"
    assert paths["benchmarks"] == REPO_ROOT / "resources" / "benchmarks"
