"""Guard the release distribution scripts' packaging invariants.

The installer hardcodes ``versions/<tag>/scripts/launch_bootstrap.ps1`` and
the bootstrap delegates to ``versions/<tag>/scripts/launcher.ps1``, so
renaming or dropping any of these files breaks installs at runtime with no
other gate failing.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from source.utilities.paths import STATE_DIR_ENV_VAR

REPO_ROOT = Path(__file__).resolve().parents[1]

SCRIPT_PATHS = [
    REPO_ROOT / "get.ps1",
    REPO_ROOT / "install.ps1",
    REPO_ROOT / "scripts" / "launcher.ps1",
    REPO_ROOT / "scripts" / "launch_bootstrap.ps1",
]


def test_release_scripts_exist():
    for script in SCRIPT_PATHS:
        assert script.is_file(), f"missing release script {script.name}"


def test_release_scripts_are_bom_free():
    # Windows editors like to add a BOM on save; these files are fetched raw
    # and executed, and the serialization convention keeps every
    # machine-consumed file BOM-free.
    for script in SCRIPT_PATHS:
        head = script.read_bytes()[:3]
        assert head != b"\xef\xbb\xbf", f"{script.name} has a UTF-8 BOM"


def test_bootstrap_carries_version_marker():
    # The launcher replaces the installed bootstrap only on a higher marker;
    # a template without one (parsed as 0) could never ship a fix.
    text = (REPO_ROOT / "scripts" / "launch_bootstrap.ps1").read_text(encoding="utf-8")
    assert re.search(r"^# csd-bootstrap-version: \d+$", text, flags=re.MULTILINE)


def _endpoint_probe_script() -> str:
    """Return the one-liner ``Get-ConfiguredEndpoint`` runs as ``python -c``.

    The launcher's only parsing contract with the app is the last line this
    prints, so the test drives the real snippet out of the real script rather
    than a copy that could drift. The snippet quotes with double quotes only,
    which is what keeps it inside the PowerShell single-quoted argument and
    makes this regex sufficient.
    """
    launcher = (REPO_ROOT / "scripts" / "launcher.ps1").read_text(encoding="utf-8")
    matches = re.findall(r"-c '([^']*)'", launcher)
    assert len(matches) == 1, f"expected one `python -c` snippet, found {len(matches)}"
    return matches[0]


@pytest.mark.parametrize(
    ("config_body", "expected"),
    [
        ("port = 8050\n", ["8050", "127.0.0.1", "True"]),
        (
            "port = 8050\nopen_browser_on_launch = false\n",
            ["8050", "127.0.0.1", "False"],
        ),
    ],
)
def test_launcher_endpoint_snippet_prints_port_host_and_browser_flag(
    tmp_path: Path, config_body: str, expected: list[str]
) -> None:
    """Pin the launcher-app contract: three whitespace-separated fields.

    ``Get-ConfiguredEndpoint`` splits the last stdout line into exactly three
    fields and compares the third against the literal ``True``. A field count
    or a spelling that drifts here sends the launcher to its defaults, which
    is a healthy app probed on the wrong port.
    """
    (tmp_path / "config.toml").write_text(config_body, encoding="utf-8")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(REPO_ROOT), environment.get("PYTHONPATH")])
    )
    environment[STATE_DIR_ENV_VAR] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, "-c", _endpoint_probe_script()],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines()[-1].split() == expected
