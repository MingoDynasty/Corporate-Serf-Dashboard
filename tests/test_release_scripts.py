"""Guard the release distribution scripts' packaging invariants.

The installer hardcodes ``versions/<tag>/scripts/launch_bootstrap.ps1`` and
the bootstrap delegates to ``versions/<tag>/scripts/launcher.ps1``, so
renaming or dropping any of these files breaks installs at runtime with no
other gate failing.
"""

import json
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
    than a copy that could drift. It lives in a here-string, which is what
    lets it carry Python's single quotes with no escaping.
    """
    launcher = (REPO_ROOT / "scripts" / "launcher.ps1").read_text(encoding="utf-8")
    match = re.search(
        r"^[$]EndpointProbeSnippet = @'\r?\n(.*?)\r?\n'@$",
        launcher,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, "launcher.ps1 has no $EndpointProbeSnippet here-string"
    return match.group(1)


def test_launcher_endpoint_snippet_carries_no_double_quote() -> None:
    """Windows PowerShell 5.1 silently eats them, and the shortcut runs 5.1.

    5.1 re-quotes a native command's argument without escaping the double
    quotes inside it, so ``print(f"{c.port} {c.host}")`` reached python as
    ``print(f{c.port}`` and exited with a SyntaxError. The launcher then took
    its fallback and probed 8050 on 127.0.0.1 whatever the config said. The
    subprocess call below cannot catch this -- Python quotes its arguments
    properly -- so the shape of the snippet is asserted directly.
    """
    assert '"' not in _endpoint_probe_script()


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


WINDOWS_POWERSHELL = (
    Path(os.environ.get("SystemRoot", r"C:\Windows"))
    / "System32"
    / "WindowsPowerShell"
    / "v1.0"
    / "powershell.exe"
)

# Dot-sources the real Get-ConfiguredEndpoint out of launcher.ps1 and calls it,
# under the same $ErrorActionPreference = 'Stop' the launcher sets at line 29.
# The two bugs this guards against were both invisible to a Python-side
# subprocess test and both only appear in a real 5.1 process: 5.1 drops the
# double quotes inside a native command's argument, and it turns that
# command's redirected stderr into a terminating error while the preference is
# Stop.
_DRIVER = """
$ErrorActionPreference = 'Stop'
$InstallRoot = $args[0]
$DefaultPort = 8050
$DefaultHost = '127.0.0.1'
$ast = [System.Management.Automation.Language.Parser]::ParseFile($args[1], [ref]$null, [ref]$null)
$snippet = $ast.FindAll({
    param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and
        $n.Left.Extent.Text -eq '$EndpointProbeSnippet' }, $true)[0]
Invoke-Expression $snippet.Extent.Text
$function = $ast.FindAll({
    param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $n.Name -eq 'Get-ConfiguredEndpoint' }, $true)[0]
Invoke-Expression $function.Extent.Text
$result = Get-ConfiguredEndpoint
"$($result.Port) $($result.Host) $($result.OpenBrowser)"
"""


def _windows_powershell_endpoint(tmp_path: Path, config_body: str) -> str:
    r"""Build an install root around this venv and return the parsed endpoint.

    The junction is what lets the launcher's own
    ``versions\<tag>\.venv\Scripts\python.exe`` path reach a working
    interpreter; a copied ``python.exe`` would be a venv trampoline with no
    ``pyvenv.cfg`` above it.
    """
    venv = Path(sys.executable).parent.parent
    if not (venv / "pyvenv.cfg").is_file():
        pytest.skip("not running from a virtual environment")

    root = tmp_path / "install-root"
    (root / "versions" / "dev").mkdir(parents=True)
    (root / "config.toml").write_text(config_body, encoding="utf-8")
    (root / "install.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tag": "dev",
                "sha": "0" * 40,
                "commit_date": "2026-01-01",
                "update_policy": "pinned",
                "pinned_tag": "dev",
            }
        ),
        encoding="utf-8",
    )
    link = subprocess.run(
        [
            "cmd",
            "/c",
            "mklink",
            "/J",
            str(root / "versions" / "dev" / ".venv"),
            str(venv),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if link.returncode != 0:
        pytest.skip(f"cannot create a directory junction: {link.stderr.strip()}")

    driver = tmp_path / "driver.ps1"
    driver.write_text(_DRIVER, encoding="utf-8")
    result = subprocess.run(
        [
            str(WINDOWS_POWERSHELL),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(driver),
            str(root),
            str(REPO_ROOT / "scripts" / "launcher.ps1"),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip().splitlines()[-1].strip()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
@pytest.mark.parametrize(
    ("case", "config_body", "expected"),
    [
        (
            "knob off",
            "port = 8137\nopen_browser_on_launch = false\n",
            "8137 127.0.0.1 False",
        ),
        (
            "knob on",
            "port = 8137\nopen_browser_on_launch = true\n",
            "8137 127.0.0.1 True",
        ),
        ("key absent", "port = 8137\n", "8137 127.0.0.1 True"),
        # An unknown key makes the loader log a warning to stderr. Under
        # `$ErrorActionPreference = 'Stop'` that used to abort the capture, so
        # a single typo cost the configured port as well as the flag.
        (
            "unknown key",
            "port = 8137\nopen_browser_on_launch = false\nnot_a_key = 1\n",
            "8137 127.0.0.1 False",
        ),
        # Only an unreadable config may reach the fallback.
        ("unparseable", "port = \n", "8050 127.0.0.1 True"),
    ],
)
def test_get_configured_endpoint_under_windows_powershell(
    tmp_path: Path, case: str, config_body: str, expected: str
) -> None:
    """Exercise the launcher's endpoint probe in the shell the shortcut runs.

    ``install.ps1`` points the desktop shortcut at Windows PowerShell 5.1, and
    every gate in this repository runs under Python. Two 5.1-only defects in
    this one function reached ``main`` unseen, both of which sent every launch
    to the fallback defaults and would have killed a healthy app on a
    non-default port. ``windows-latest`` ships 5.1, so CI can hold the line.
    """
    if not WINDOWS_POWERSHELL.is_file():
        pytest.skip(f"{WINDOWS_POWERSHELL} not found")

    assert _windows_powershell_endpoint(tmp_path, config_body) == expected, case
