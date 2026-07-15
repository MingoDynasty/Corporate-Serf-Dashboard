import subprocess
import sys
from importlib.metadata import version
from pathlib import Path


def test_app_name_uses_installed_project_version() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from source.app import APP_NAME; print(APP_NAME)",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == (
        f"Corporate Serf Dashboard v{version('Corporate-Serf-Dashboard')}"
    )
