import os
import subprocess
import sys
from pathlib import Path

import pytest

CONFIG_ERROR_MESSAGE = (
    "Configuration error: copy example.toml to config.toml and set stats_dir."
)


@pytest.mark.parametrize(
    "config_contents",
    [
        None,
        "not valid toml",
        'stats_dir = "missing required fields"',
    ],
    ids=["missing", "invalid-toml", "invalid-schema"],
)
def test_startup_with_missing_or_invalid_config_exits_cleanly(
    tmp_path: Path,
    config_contents: str | None,
) -> None:
    if config_contents is not None:
        (tmp_path / "config.toml").write_text(config_contents, encoding="utf-8")

    repo_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(repo_root), environment.get("PYTHONPATH")])
    )

    result = subprocess.run(
        [sys.executable, "-m", "source.app"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == CONFIG_ERROR_MESSAGE
    assert "Traceback" not in result.stderr
