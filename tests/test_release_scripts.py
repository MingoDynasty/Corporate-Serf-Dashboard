"""Guard the release distribution scripts' packaging invariants.

The installer hardcodes ``versions/<tag>/scripts/launch_bootstrap.ps1`` and
the bootstrap delegates to ``versions/<tag>/scripts/launcher.ps1``, so
renaming or dropping any of these files breaks installs at runtime with no
other gate failing.
"""

import re
from pathlib import Path

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
