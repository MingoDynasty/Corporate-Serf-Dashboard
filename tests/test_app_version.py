import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_in_app(snippet: str, cwd: Path) -> str:
    """Import the app in a child process and print something about it.

    Importing ``source.app`` configures process-wide logging and creates
    ``data/logs``, so it stays out of the test process.
    """
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        cwd=cwd,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_app_name_carries_no_version_without_a_release_tag() -> None:
    app_name = _run_in_app(
        "from source.app import APP_NAME; print(APP_NAME)", REPO_ROOT
    )

    assert app_name == "Corporate Serf Dashboard"


def test_app_name_carries_the_release_tag_when_installed(tmp_path: Path) -> None:
    (tmp_path / "install.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tag": "v2026.07.18",
                "sha": "a" * 40,
                "commit_date": "2026-07-18",
                "update_policy": "latest",
            }
        ),
        encoding="utf-8",
    )

    app_name = _run_in_app("from source.app import APP_NAME; print(APP_NAME)", tmp_path)

    assert app_name == "Corporate Serf Dashboard v2026.07.18"


def test_app_serves_the_health_endpoint() -> None:
    rules = _run_in_app(
        "from source.app import app;"
        " print([str(rule) for rule in app.server.url_map.iter_rules()])",
        REPO_ROOT,
    )

    assert "'/health'" in rules
