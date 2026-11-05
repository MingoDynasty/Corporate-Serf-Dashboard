"""Guard the release distribution scripts' packaging invariants.

The installer hardcodes ``versions/<tag>/scripts/launch_bootstrap.ps1`` and
the bootstrap delegates to ``versions/<tag>/scripts/launcher.ps1``, so
renaming or dropping any of these files breaks installs at runtime with no
other gate failing.
"""

import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import zipfile
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import NamedTuple

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


def test_launcher_endpoint_capture_takes_stdout_only() -> None:
    """Merging stderr into the capture makes the parse a coin flip.

    The loader's warning and its print line travel on separate pipes, so the
    order they merge in is not guaranteed. Measured at roughly one run in
    sixty, the unknown-key warning arrived last, and a "last line wins" parse
    then read the warning and fell back to `8050` -- an intermittent
    wrong-port kill for anyone with a typo in `config.toml`. Nothing reads the
    stderr text, so it is discarded rather than ordered.
    """
    launcher = (REPO_ROOT / "scripts" / "launcher.ps1").read_text(encoding="utf-8")
    match = re.search(r"^\s*[$]endpointText = .*$", launcher, flags=re.MULTILINE)
    assert match is not None, "launcher.ps1 has no $endpointText capture"
    capture = match.group(0)
    assert "2>$null" in capture, capture
    assert "2>&1" not in capture, capture


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
    _link_this_venv(root / "versions" / "dev" / ".venv")

    output = _run_under_windows_powershell(tmp_path, _DRIVER, root)
    return output.strip().splitlines()[-1].strip()


def _link_this_venv(link: Path) -> None:
    """Make ``link`` a junction to the venv running the tests, or skip."""
    venv = Path(sys.executable).parent.parent
    if not (venv / "pyvenv.cfg").is_file():
        pytest.skip("not running from a virtual environment")
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(venv)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"cannot create a directory junction: {result.stderr.strip()}")


def _run_under_windows_powershell(
    tmp_path: Path,
    driver: str,
    root: Path,
    environment: dict[str, str] | None = None,
) -> str:
    """Run a driver script under Windows PowerShell 5.1 and return its stdout.

    The driver receives the install root and the path of ``launcher.ps1`` as
    its two arguments. ``environment`` replaces the one 5.1 would inherit.
    """
    result = _windows_powershell(
        tmp_path,
        driver,
        [str(root), str(REPO_ROOT / "scripts" / "launcher.ps1")],
        environment,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _windows_powershell(
    tmp_path: Path,
    driver: str,
    arguments: list[str],
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a driver script under Windows PowerShell 5.1 with ``arguments``."""
    driver_path = tmp_path / "driver.ps1"
    driver_path.write_text(driver, encoding="utf-8")
    return subprocess.run(
        [
            str(WINDOWS_POWERSHELL),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(driver_path),
            *arguments,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        env=environment,
    )


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


# Dot-sources the real Start-AppVersion and Show-AppFailure out of launcher.ps1,
# starts the stand-in app through the first, and prints what the second sends
# to the host as code points, one line per host line. The text itself cannot
# cross the pipe: 5.1 encodes piped output in the console's code page (437,
# measured on 2026-10-12), which turned a CJK character into a question mark.
# The two lines ahead of the tail say whether the start threw, and what the
# launcher's own PYTHONIOENCODING is once Start-AppVersion is done.
_START_AND_SHOW_DRIVER = """
$ErrorActionPreference = 'Stop'
$InstallRoot = $args[0]
$ast = [System.Management.Automation.Language.Parser]::ParseFile($args[1], [ref]$null, [ref]$null)
foreach ($name in 'Start-AppVersion', 'Show-AppFailure') {
    $function = $ast.FindAll({
        param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $n.Name -eq $name }, $true)[0]
    Invoke-Expression $function.Extent.Text
}
$started = 'started'
try {
    $process = Start-AppVersion (Join-Path (Join-Path $InstallRoot 'versions') 'dev') 'token'
    $process.WaitForExit()
} catch {
    $started = 'start failed'
}
$started
if (Test-Path Env:PYTHONIOENCODING) { "PYTHONIOENCODING=$env:PYTHONIOENCODING" } else { 'PYTHONIOENCODING unset' }
Show-AppFailure 'the dashboard failed to start (exited).' 6>&1 | ForEach-Object {
    (([string]$_).ToCharArray() | ForEach-Object { '{0:X4}' -f [int]$_ }) -join ' '
}
"""

# What a launcher can inherit that chooses the encoding of Python's standard
# streams in place of the interpreter's default.
_INHERITED_STREAM_SETTINGS = [
    pytest.param({}, id="no override"),
    pytest.param({"PYTHONIOENCODING": "cp1252"}, id="PYTHONIOENCODING=cp1252"),
    pytest.param({"PYTHONUTF8": "0"}, id="PYTHONUTF8=0"),
]


def _start_and_show(tmp_path: Path, root: Path, inherited: dict[str, str]) -> list[str]:
    """Run the start-and-show driver with only ``inherited`` set, and decode it.

    The session running the tests may carry either variable itself, so both
    are dropped before ``inherited`` is applied.
    """
    environment = {
        name: value
        for name, value in os.environ.items()
        if name not in {"PYTHONIOENCODING", "PYTHONUTF8"}
    }
    environment.update(inherited)
    output = _run_under_windows_powershell(
        tmp_path, _START_AND_SHOW_DRIVER, root, environment
    )
    started, launcher_setting, *shown = output.splitlines()
    return [
        started,
        launcher_setting,
        *("".join(chr(int(code, 16)) for code in line.split()) for line in shown),
    ]


def _launcher_setting(inherited: dict[str, str]) -> str:
    """Spell the driver's report of the launcher's own ``PYTHONIOENCODING``."""
    if "PYTHONIOENCODING" in inherited:
        return f"PYTHONIOENCODING={inherited['PYTHONIOENCODING']}"
    return "PYTHONIOENCODING unset"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
@pytest.mark.parametrize("inherited", _INHERITED_STREAM_SETTINGS)
def test_failure_tail_shows_what_the_app_wrote(
    tmp_path: Path, inherited: dict[str, str]
) -> None:
    """Hold the launcher's writer and its reader to one encoding.

    The launcher redirects the app's stderr to a file and prints its last 15
    lines when a start fails. Read with no encoding named, 5.1 took that file
    for the Windows code page, which stopped being true when Python 3.15 made
    UTF-8 the default: an accented letter in a path came out as two wrong
    characters. Reading it as UTF-8 was half a fix, because a
    ``PYTHONIOENCODING`` or a ``PYTHONUTF8=0`` that the launcher inherits puts
    the code page back. So the stand-in app here is started by the real
    ``Start-AppVersion`` and read back by the real ``Show-AppFailure``, under
    each of those settings, and the launcher's own setting must come out of
    the start unchanged.
    """
    if not WINDOWS_POWERSHELL.is_file():
        pytest.skip(f"{WINDOWS_POWERSHELL} not found")

    root = tmp_path / "install-root"
    version = root / "versions" / "dev"
    (version / "source").mkdir(parents=True)
    _link_this_venv(version / ".venv")
    lines = [
        f"line {number}: File: C:/Users/Zoë/config.toml 次" for number in range(20)
    ]
    text = "\n".join(lines) + "\n"
    (version / "source" / "app.py").write_text(
        f"import sys\nsys.stderr.write({ascii(text)})\n", encoding="utf-8"
    )

    started, launcher_setting, *shown = _start_and_show(tmp_path, root, inherited)

    assert started == "started"
    assert launcher_setting == _launcher_setting(inherited)
    assert shown[0] == "WARNING: the dashboard failed to start (exited)."
    assert shown[2:-1] == lines[-15:]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
@pytest.mark.parametrize("inherited", _INHERITED_STREAM_SETTINGS)
def test_a_failed_start_leaves_the_launcher_setting_alone(
    tmp_path: Path, inherited: dict[str, str]
) -> None:
    """A start that throws must not leave the launcher's environment pinned.

    ``Start-AppVersion`` sets the stream encoding for the app alone. Whatever
    the launcher starts next, such as the previous version after a failed
    update, must see what the launcher itself inherited.
    """
    if not WINDOWS_POWERSHELL.is_file():
        pytest.skip(f"{WINDOWS_POWERSHELL} not found")

    root = tmp_path / "install-root"
    scripts = root / "versions" / "dev" / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    # Present, so the launcher gets as far as starting it, and not a program,
    # so the start throws after the environment is set.
    (scripts / "python.exe").write_text("not a program", encoding="utf-8")

    started, launcher_setting, *_ = _start_and_show(tmp_path, root, inherited)

    assert started == "start failed"
    assert launcher_setting == _launcher_setting(inherited)


INSTALL_SCRIPT = REPO_ROOT / "install.ps1"

# Dot-sources the real New-DesktopShortcut out of install.ps1 and calls it with
# the Desktop folder the test names. With no folder named it passes '', which
# is what GetFolderPath returns for a Desktop folder that does not exist. A
# written shortcut is read back field by field.
_SHORTCUT_DRIVER = """
$ErrorActionPreference = 'Stop'
$InstallRoot = $args[0]
$ast = [System.Management.Automation.Language.Parser]::ParseFile($args[1], [ref]$null, [ref]$null)
$function = $ast.FindAll({
    param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $n.Name -eq 'New-DesktopShortcut' }, $true)[0]
Invoke-Expression $function.Extent.Text
$desktop = if ($args.Count -gt 2) { $args[2] } else { '' }
$written = New-DesktopShortcut $desktop
"written: $written"
if ($written) {
    $link = (New-Object -ComObject WScript.Shell).CreateShortcut(
        (Join-Path $desktop 'Corporate Serf Dashboard.lnk'))
    $link.TargetPath
    $link.Arguments
    $link.WorkingDirectory
}
"""


def _new_desktop_shortcut(tmp_path: Path, *desktop: Path) -> list[str]:
    """Run the real ``New-DesktopShortcut`` and return its output lines."""
    if not WINDOWS_POWERSHELL.is_file():
        pytest.skip(f"{WINDOWS_POWERSHELL} not found")
    root = tmp_path / "install-root"
    root.mkdir()
    result = _windows_powershell(
        tmp_path,
        _SHORTCUT_DRIVER,
        [str(root), str(INSTALL_SCRIPT), *(str(folder) for folder in desktop)],
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.splitlines()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
def test_desktop_shortcut_runs_the_root_launcher(tmp_path: Path) -> None:
    """The shortcut runs ``launch.ps1`` at the root, never a version directory."""
    desktop = tmp_path / "Desktop"
    desktop.mkdir()

    written, target, arguments, working_directory = _new_desktop_shortcut(
        tmp_path, desktop
    )

    root = tmp_path / "install-root"
    assert written == "written: True"
    assert target.lower() == str(WINDOWS_POWERSHELL).lower()
    assert arguments == (
        f'-NoProfile -ExecutionPolicy Bypass -File "{root / "launch.ps1"}"'
    )
    assert working_directory == str(root)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
@pytest.mark.parametrize("named", [False, True], ids=["path empty", "folder missing"])
def test_a_missing_desktop_folder_is_a_warning(tmp_path: Path, named: bool) -> None:
    """A shortcut that cannot be written must not fail a finished install.

    By the time the shortcut is written, ``launch.ps1`` and ``install.json``
    exist and the install works. The Desktop folder can still be missing, for
    example a OneDrive-redirected Desktop before its first sync. Then
    ``GetFolderPath`` returns an empty string, and ``Save()`` into a folder
    that is gone throws. Either one used to end the installer with a raw COM
    error and none of its closing lines.
    """
    desktop = tmp_path / "no-such-desktop"

    lines = _new_desktop_shortcut(tmp_path, *([desktop] if named else []))

    *warning, written = lines
    assert written == "written: False"
    assert len(warning) == 1
    assert warning[0].startswith("WARNING: could not create the desktop shortcut (")
    if not named:
        assert warning[0].endswith("(the Desktop folder does not exist).")
    assert not desktop.exists()


# Runs the real install.ps1 end to end, with no network and no shortcut. A
# function in the caller's scope shadows a cmdlet of the same name for the
# script it runs, so these stand in for the two download cmdlets and for the
# shortcut's COM object. The uv and python the install runs are stub programs.
# A shadow also reaches the modules the script loads, and the Archive module
# calls New-Object as it loads, so that shadow passes every other call on.
_INSTALL_DRIVER = """
$TestFixtures = $args[2]
function Invoke-WebRequest {
    param([string]$Uri, [string]$OutFile, [switch]$UseBasicParsing, [int]$TimeoutSec)
    $source = Join-Path $TestFixtures ($Uri -split '/')[-1]
    if (-not (Test-Path -LiteralPath $source)) { throw "unexpected download: $Uri" }
    if ($OutFile) { Copy-Item -LiteralPath $source -Destination $OutFile; return }
    [pscustomobject]@{ Content = [System.IO.File]::ReadAllBytes($source) }
}
function Invoke-RestMethod { throw 'unexpected request' }
# The Desktop is the real one of whoever runs the tests.
function New-Object {
    if ($args -contains 'WScript.Shell') { throw 'the test writes no desktop shortcut' }
    Microsoft.PowerShell.Utility\\New-Object @args
}
<refuse restore>
try {
    & $args[1] -LatestTag $args[3] -InstallRoot $args[0]
    exit $LASTEXITCODE
} catch {
    Write-Host "TEST: uncaught error: $($_.Exception.Message)"
    exit 99
}
"""

# Fails the move that returns a parked copy to its place, as a lingering
# handle on the replacement's partial tree can.
_REFUSE_RESTORE = r"""
function Move-Item {
    param([string]$LiteralPath, [string]$Destination)
    if ($LiteralPath -like '*\tmp\previous-*') { throw 'the test refuses the restore' }
    Microsoft.PowerShell.Management\Move-Item -LiteralPath $LiteralPath -Destination $Destination
}
"""

_TAG = "v2026.01.01"
_SHA = "0123456789abcdef" * 2 + "01234567"
_UV_VERSION = "0.0.0"


@pytest.fixture(scope="module")
def stub_programs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Build two console programs that ignore their arguments and exit 0 or 1.

    The installer runs ``uv.exe`` and the venv's ``python.exe`` as native
    commands and reads only their exit codes, so a stub must be a real
    program; a script would not run under those names.
    """
    if not WINDOWS_POWERSHELL.is_file():
        pytest.skip(f"{WINDOWS_POWERSHELL} not found")
    folder = tmp_path_factory.mktemp("stubs")
    programs = {f"exit{code}": folder / f"exit{code}.exe" for code in (0, 1)}
    build = "; ".join(
        f"Add-Type -OutputType ConsoleApplication -OutputAssembly '{path}'"
        f" -TypeDefinition 'public static class {name}"
        f" {{ public static int Main() {{ return {name[-1]}; }} }}'"
        for name, path in programs.items()
    )
    subprocess.run(
        [str(WINDOWS_POWERSHELL), "-NoProfile", "-Command", build],
        check=True,
        capture_output=True,
        timeout=120,
    )
    return programs


def _release_fixtures(
    tmp_path: Path, stubs: dict[str, Path], python: str | None, stamp: str
) -> Path:
    """Write the ``release.json`` and zip that the fake downloads serve.

    ``python`` names the stub the zip ships as its venv's ``python.exe``, which
    is what answers the config check; ``None`` ships no interpreter at all.
    """
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    release = {
        "schema_version": 1,
        "tag": _TAG,
        "sha": _SHA,
        "commit_date": "2026-01-01",
        "uv_version": _UV_VERSION,
        "source_asset": "csd.zip",
    }
    (fixtures / "release.json").write_text(json.dumps(release), encoding="utf-8")
    top = f"Corporate-Serf-Dashboard-{_TAG}/"
    with zipfile.ZipFile(fixtures / "csd.zip", "w") as archive:
        archive.writestr(top + "version.txt", f"sha: {stamp}\n")
        archive.writestr(top + "scripts/launch_bootstrap.ps1", "# stand-in\n")
        if python is not None:
            archive.write(stubs[python], top + ".venv/Scripts/python.exe")
    return fixtures


def _install_root(tmp_path: Path, stubs: dict[str, Path], uv: str) -> Path:
    """Lay out a root that already holds uv, so nothing downloads it."""
    root = tmp_path / "install-root"
    (root / "uv" / _UV_VERSION).mkdir(parents=True)
    shutil.copyfile(stubs[uv], root / "uv" / _UV_VERSION / "uv.exe")
    return root


def _reinstall_root(tmp_path: Path, stubs: dict[str, Path], uv: str) -> Path:
    """Lay out a root with the tag already installed and a config it rejects."""
    root = _install_root(tmp_path, stubs, uv)
    (root / "versions" / _TAG).mkdir(parents=True)
    (root / "versions" / _TAG / "previous.txt").write_text("", encoding="utf-8")
    (root / "config.toml").write_text('port = "not a port"\n', encoding="utf-8")
    return root


def _run_install(
    tmp_path: Path, root: Path, fixtures: Path, *, refuse_restore: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run the real ``install.ps1 -LatestTag`` against the fake release."""
    driver = _INSTALL_DRIVER.replace(
        "<refuse restore>", _REFUSE_RESTORE if refuse_restore else ""
    )
    return _windows_powershell(
        tmp_path, driver, [str(root), str(INSTALL_SCRIPT), str(fixtures), _TAG]
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
@pytest.mark.parametrize(
    ("uv", "python", "stamp", "expected", "installed"),
    [
        pytest.param(
            "exit0",
            "exit1",
            _SHA,
            "ERROR: the installed app cannot load",
            "version.txt",
            id="config check fails after the sync",
        ),
        pytest.param(
            "exit0",
            None,
            _SHA,
            "TEST: uncaught error:",
            "version.txt",
            id="uncaught error after the sync",
        ),
        pytest.param(
            "exit1",
            "exit0",
            _SHA,
            "the previously installed copy was restored.",
            "previous.txt",
            id="sync fails",
        ),
        pytest.param(
            "exit0",
            "exit0",
            "f" * 40,
            "does not carry the release SHA",
            "previous.txt",
            id="stamp check fails",
        ),
    ],
)
def test_a_failed_reinstall_leaves_no_tmp(
    tmp_path: Path,
    stub_programs: dict[str, Path],
    uv: str,
    python: str | None,
    stamp: str,
    expected: str,
    installed: str,
) -> None:
    r"""Every exit removes ``tmp\``, not only a successful one.

    Nothing else ever does: a later install clears it only by succeeding. The
    costly case is a reinstall onto the installed tag that stops after its
    sync, at the config check: the previous copy parked under ``tmp\`` is a
    second full venv. The other exits strand the download and the
    extraction. ``installed`` names the file that shows which copy ends up
    under ``versions\<tag>``.
    """
    root = _reinstall_root(tmp_path, stub_programs, uv)
    fixtures = _release_fixtures(tmp_path, stub_programs, python, stamp)

    result = _run_install(tmp_path, root, fixtures)

    assert result.returncode != 0
    assert expected in result.stdout, result.stdout
    assert not (root / "tmp").exists(), result.stdout
    assert (root / "versions" / _TAG / installed).is_file()
    assert not (root / "install.json").exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
def test_a_failed_restore_keeps_the_parked_copy(
    tmp_path: Path, stub_programs: dict[str, Path]
) -> None:
    r"""An exit that keeps ``tmp\``: it holds the only working copy.

    When the sync fails and the parked copy cannot be moved back, the error
    names where it is so it can be moved back by hand.
    """
    root = _reinstall_root(tmp_path, stub_programs, "exit1")
    fixtures = _release_fixtures(tmp_path, stub_programs, "exit0", _SHA)

    result = _run_install(tmp_path, root, fixtures, refuse_restore=True)

    parked = root / "tmp" / f"previous-{_TAG}"
    assert result.returncode == 1
    assert f"It is intact at {parked}" in result.stdout, result.stdout
    assert (parked / "previous.txt").is_file()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
@pytest.mark.parametrize(
    ("uv", "python", "download", "expected", "kept"),
    [
        pytest.param(
            "exit0",
            "exit0",
            False,
            "ERROR: download incomplete or failed (unexpected download:",
            True,
            id="retry download fails",
        ),
        pytest.param(
            "exit1",
            "exit0",
            True,
            f"ERROR: install of {_TAG} failed (uv sync failed",
            True,
            id="retry sync fails",
        ),
        pytest.param(
            "exit0",
            "exit1",
            True,
            "ERROR: the installed app cannot load",
            False,
            id="retry config check fails after the sync",
        ),
        pytest.param(
            "exit0",
            "exit0",
            True,
            f"Installed Corporate Serf Dashboard {_TAG}.",
            False,
            id="retry succeeds",
        ),
    ],
)
def test_a_retry_keeps_the_copy_an_earlier_run_parked(
    tmp_path: Path,
    stub_programs: dict[str, Path],
    uv: str,
    python: str,
    download: bool,
    expected: str,
    kept: bool,
) -> None:
    r"""A retry keeps ``tmp\`` while an earlier run's parked copy is needed.

    A failed restore leaves the only working copy parked, and its message
    says to move it back or to re-run the installer. The retry parks nothing
    itself, because ``versions\<tag>`` is gone, so a retry that fails before
    its own sync must still keep the earlier copy. Once the retry has synced
    a replacement for that version, the copy is no longer needed.
    """
    root = _reinstall_root(tmp_path, stub_programs, "exit1")
    fixtures = _release_fixtures(tmp_path, stub_programs, python, _SHA)
    parked = root / "tmp" / f"previous-{_TAG}"
    target = root / "versions" / _TAG

    first = _run_install(tmp_path, root, fixtures, refuse_restore=True)

    assert f"It is intact at {parked}" in first.stdout, first.stdout
    assert not target.exists()

    shutil.copyfile(stub_programs[uv], root / "uv" / _UV_VERSION / "uv.exe")
    if not download:
        (fixtures / "csd.zip").unlink()

    retry = _run_install(tmp_path, root, fixtures)

    assert expected in retry.stdout, retry.stdout
    if kept:
        assert retry.returncode != 0
        assert (parked / "previous.txt").is_file(), retry.stdout
        assert not target.exists()
    else:
        assert not (root / "tmp").exists(), retry.stdout
        assert (target / "version.txt").is_file()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
def test_an_install_without_a_shortcut_still_finishes(
    tmp_path: Path, stub_programs: dict[str, Path]
) -> None:
    """A shortcut that can't be written leaves a working install and says so."""
    root = _install_root(tmp_path, stub_programs, "exit0")
    fixtures = _release_fixtures(tmp_path, stub_programs, "exit0", _SHA)

    result = _run_install(tmp_path, root, fixtures)

    assert result.returncode == 0, result.stdout + result.stderr
    lines = result.stdout.splitlines()
    assert any(
        line.startswith("WARNING: could not create the desktop shortcut (")
        for line in lines
    ), result.stdout
    assert lines[-3:] == [
        f"Installed Corporate Serf Dashboard {_TAG}.",
        "Launch it with: powershell.exe -NoProfile -ExecutionPolicy Bypass"
        f' -File "{root / "launch.ps1"}"',
        f"To uninstall: delete the folder {root}",
    ]
    assert (root / "install.json").is_file()
    assert (root / "launch.ps1").is_file()
    assert not (root / "tmp").exists()


# Defines every function of the script named by the driver's second argument,
# in the driver's own scope, the way the script itself would.
_DEFINE_FUNCTIONS = """
$ast = [System.Management.Automation.Language.Parser]::ParseFile($args[1], [ref]$null, [ref]$null)
foreach ($function in $ast.FindAll({
        param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)) {
    Invoke-Expression $function.Extent.Text
}
"""

# Prunes the way a plain start does: no version was just replaced.
_PRUNE_DRIVER = f"""
$ErrorActionPreference = 'Stop'
$InstallRoot = $args[0]
{_DEFINE_FUNCTIONS}
Remove-PrunedVersions -ActiveTag $args[2] -PreviousTag ''
"""


def _lay_out_versions(root: Path, venvs: dict[str, bool]) -> None:
    r"""Create ``versions\<tag>`` oldest first, with or without a venv interpreter."""
    first_day = 1_767_225_600  # 2026-01-01 UTC
    for age, (tag, has_venv) in enumerate(venvs.items()):
        directory = root / "versions" / tag
        directory.mkdir(parents=True)
        if has_venv:
            interpreter = directory / ".venv" / "Scripts" / "python.exe"
            interpreter.parent.mkdir(parents=True)
            interpreter.write_bytes(b"")
        written = first_day + age * 86_400
        os.utime(directory, (written, written))


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
@pytest.mark.parametrize(
    ("venvs", "kept", "pruned"),
    [
        pytest.param(
            {"v2026.01.01": True, "v2026.01.02": True, "v2026.01.03": False},
            ["v2026.01.01", "v2026.01.02"],
            ["v2026.01.03"],
            id="last good version kept",
        ),
        pytest.param(
            {"v2026.01.01": False, "v2026.01.02": True, "v2026.01.03": False},
            ["v2026.01.02"],
            ["v2026.01.01", "v2026.01.03"],
            id="nothing runnable to keep",
        ),
    ],
)
def test_pruning_keeps_a_runnable_fallback(
    tmp_path: Path, venvs: dict[str, bool], kept: list[str], pruned: list[str]
) -> None:
    r"""A plain start keeps a fallback that can run, never a half-staged update.

    A failed update can leave its tag's directory under ``versions\`` without
    a synced environment, and that directory is newer than every version that
    ran. Chosen by date alone, it was the one kept, and the last version that
    started was pruned. Only a directory holding ``.venv\Scripts\python.exe``
    can be the fallback; ``v2026.01.02`` is the active version throughout.
    """
    if not WINDOWS_POWERSHELL.is_file():
        pytest.skip(f"{WINDOWS_POWERSHELL} not found")
    root = tmp_path / "install-root"
    _lay_out_versions(root, venvs)

    result = _windows_powershell(
        tmp_path,
        _PRUNE_DRIVER,
        [str(root), str(REPO_ROOT / "scripts" / "launcher.ps1"), "v2026.01.02"],
    )

    assert result.returncode == 0, result.stderr
    assert sorted(path.name for path in (root / "versions").iterdir()) == kept
    assert result.stdout.splitlines() == [
        f"Pruned old version {tag}." for tag in pruned
    ]


class _Reply(NamedTuple):
    """What the fake GitHub sends for one URL path.

    ``dropped`` announces the whole body, sends half of it, and closes the
    connection: a transfer that dies mid-download.
    """

    status: int
    body: bytes = b"{}"
    dropped: bool = False


class _ReplyHandler(BaseHTTPRequestHandler):
    """Answer a GET from the server's ``replies``; an unknown path is a 404."""

    def do_GET(self) -> None:
        assert isinstance(self.server, _FakeGitHub)
        reply = self.server.replies.get(self.path, _Reply(404))
        self.send_response(reply.status)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(reply.body)))
        self.end_headers()
        if reply.dropped:
            self.wfile.write(reply.body[: len(reply.body) // 2])
            self.wfile.flush()
            self.connection.shutdown(socket.SHUT_RDWR)
            self.close_connection = True
            return
        self.wfile.write(reply.body)

    def log_message(self, format: str, *args: object) -> None:
        """Keep the request log out of the test output."""


class _FakeGitHub(ThreadingHTTPServer):
    """A loopback HTTP server standing in for every host the scripts fetch from."""

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _ReplyHandler)
        self.replies: dict[str, _Reply] = {}
        self.url = f"http://127.0.0.1:{self.server_address[1]}"


@pytest.fixture
def fake_github() -> Iterator[_FakeGitHub]:
    """Serve ``replies`` on a free loopback port for the length of one test."""
    server = _FakeGitHub()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


_REPO = "MingoDynasty/Corporate-Serf-Dashboard"
_LATEST = f"/repos/{_REPO}/releases/latest"
_RAW_INSTALLER = f"/{_REPO}/{_TAG}/install.ps1"
_STAND_IN_INSTALLER = (
    b'param([string]$LatestTag)\nWrite-Host "TEST: the installer ran for $LatestTag"\n'
)

# Runs get.ps1 the way the one-liner does: through iex, in the caller's own
# scope, so whatever the shim leaves in that scope is still there afterwards.
# Its two GitHub hosts point at the fake server. The paths come in through
# the environment because the shim passes the caller's $args on to the
# installer, and a console's are empty.
_SHIM_DRIVER = """
$ErrorActionPreference = 'Continue'
$shim = [System.IO.File]::ReadAllText($env:CSD_TEST_SHIM)
foreach ($site in 'https://api.github.com', 'https://raw.githubusercontent.com') {
    if (-not $shim.Contains($site)) { throw "get.ps1 no longer fetches from $site" }
    $shim = $shim.Replace($site, $env:CSD_TEST_SERVER)
}
try {
    $shim | Invoke-Expression
} catch {
    Write-Host "TEST: uncaught error: $($_.Exception.Message)"
}
"TEST: preference $ErrorActionPreference"
"""


def _run_shim(tmp_path: Path, server: _FakeGitHub) -> list[str]:
    r"""Run ``get.ps1`` against ``server`` and return its output lines.

    ``%TEMP%`` is the test's, so the installer the shim writes lands there.
    """
    if not WINDOWS_POWERSHELL.is_file():
        pytest.skip(f"{WINDOWS_POWERSHELL} not found")
    temp = tmp_path / "temp"
    temp.mkdir(exist_ok=True)
    environment = os.environ.copy()
    environment.update(
        {
            "TEMP": str(temp),
            "TMP": str(temp),
            "CSD_TEST_SHIM": str(REPO_ROOT / "get.ps1"),
            "CSD_TEST_SERVER": server.url,
        }
    )
    result = _windows_powershell(tmp_path, _SHIM_DRIVER, [], environment)
    assert result.returncode == 0, result.stderr
    return result.stdout.splitlines()


_LATEST_REPLY = _Reply(200, json.dumps({"tag_name": _TAG}).encode())


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
@pytest.mark.parametrize(
    ("replies", "expected"),
    [
        pytest.param(
            {},
            "Corporate Serf Dashboard: the release is not ready yet -- try again"
            " shortly.",
            id="release not ready",
        ),
        pytest.param(
            {_LATEST: _LATEST_REPLY},
            "Corporate Serf Dashboard: the release is not ready yet -- try again"
            " shortly.",
            id="installer not ready",
        ),
        pytest.param(
            {_LATEST: _LATEST_REPLY, _RAW_INSTALLER: _Reply(200, _STAND_IN_INSTALLER)},
            f"TEST: the installer ran for {_TAG}",
            id="installer runs",
        ),
        pytest.param(
            {_LATEST: _Reply(500)},
            "Corporate Serf Dashboard: download incomplete or failed (HTTP 500).",
            id="fetch fails",
        ),
    ],
)
def test_the_shim_gives_the_console_its_preference_back(
    tmp_path: Path,
    fake_github: _FakeGitHub,
    replies: dict[str, _Reply],
    expected: str,
) -> None:
    """Every way out of ``get.ps1`` restores the caller's error preference.

    The one-liner runs the shim through iex in the user's own console, so the
    shim's ``$ErrorActionPreference = 'Stop'`` used to stay behind there. For
    the rest of that console session every error ended the command that hit
    it. The header forbids functions and ``exit``, so the shim restores the
    preference itself, on its ``return`` paths as much as at the end.
    """
    fake_github.replies.update(replies)

    lines = _run_shim(tmp_path, fake_github)

    assert expected in lines, lines
    assert lines[-1] == "TEST: preference Continue", lines


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
def test_an_error_the_shim_does_not_catch_gives_the_preference_back(
    tmp_path: Path, fake_github: _FakeGitHub
) -> None:
    r"""The preference comes back on the way out of an uncaught error too.

    A folder where the installer's temp file goes makes writing it throw.
    """
    fake_github.replies.update(
        {_LATEST: _LATEST_REPLY, _RAW_INSTALLER: _Reply(200, _STAND_IN_INSTALLER)}
    )
    (tmp_path / "temp" / f"csd-install-{_TAG}.ps1").mkdir(parents=True)

    lines = _run_shim(tmp_path, fake_github)

    assert lines[0].startswith("TEST: uncaught error: "), lines
    assert lines[-1] == "TEST: preference Continue", lines


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
@pytest.mark.parametrize(
    "replies",
    [
        pytest.param({_LATEST: _Reply(500)}, id="releases/latest"),
        pytest.param(
            {_LATEST: _LATEST_REPLY, _RAW_INSTALLER: _Reply(500)}, id="install.ps1"
        ),
    ],
)
def test_a_failed_shim_fetch_is_one_line(
    tmp_path: Path, fake_github: _FakeGitHub, replies: dict[str, _Reply]
) -> None:
    """A fetch that fails other than with a 404 says so in one line, with the status.

    The shim used to rethrow, and the console printed the error record, whose
    text is the response body: ``{}``, or GitHub's JSON error, with no status
    and no word of what failed.
    """
    fake_github.replies.update(replies)

    lines = _run_shim(tmp_path, fake_github)

    assert lines == [
        "Corporate Serf Dashboard: download incomplete or failed (HTTP 500).",
        "TEST: preference Continue",
    ]
    assert not list((tmp_path / "temp").iterdir())


_ASSET = f"/{_REPO}/releases/download/{_TAG}/csd.zip"
_ARCHIVE = f"/{_REPO}/archive/refs/tags/{_TAG}.zip"


def _release_zip() -> bytes:
    """Build a release zip whose stamp carries the release SHA."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        top = f"Corporate-Serf-Dashboard-{_TAG}/"
        archive.writestr(top + "version.txt", f"sha: {_SHA}\n")
        for number in range(20):
            archive.writestr(top + f"source/module{number}.py", "x = 1\n" * 200)
    return buffer.getvalue()


_RELEASE_ZIP = _release_zip()

# Stages the release through the real Install-ReleaseVersion of the script
# named by the second argument, downloading from the fake server named by the
# third. The fourth stands in for uv and fails, so a download that worked
# shows up as a failed sync.
_STAGING_DRIVER = f"""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$InstallRoot = $args[0]
$Repo = '{_REPO}'
$DownloadBase = $args[2]
{_DEFINE_FUNCTIONS}
$release = [pscustomobject]@{{
    tag = '{_TAG}'; sha = '{_SHA}'; source_asset = 'csd.zip' }}
try {{
    Install-ReleaseVersion $release ([byte[]]@()) $args[3] | Out-Null
    'TEST: staged'
}} catch {{
    "TEST: failed: $($_.Exception.Message)"
}}
"""

# How each script reports a failed stage: the installer stops with an ERROR
# line, and the launcher throws for its update path to print.
_STAGING_SCRIPTS = [
    pytest.param(REPO_ROOT / "install.ps1", "ERROR: {}.", id="installer"),
    pytest.param(
        REPO_ROOT / "scripts" / "launcher.ps1", "TEST: failed: {}", id="launcher"
    ),
]


def _stage(
    tmp_path: Path, server: _FakeGitHub, script: Path, uv: Path
) -> tuple[Path, str]:
    """Stage the release with ``script`` and return the root and the output."""
    if not WINDOWS_POWERSHELL.is_file():
        pytest.skip(f"{WINDOWS_POWERSHELL} not found")
    root = tmp_path / "install-root"
    root.mkdir()
    result = _windows_powershell(
        tmp_path,
        _STAGING_DRIVER,
        [str(root), str(script), server.url, str(uv)],
    )
    return root, result.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
@pytest.mark.parametrize(("script", "line"), _STAGING_SCRIPTS)
@pytest.mark.parametrize(
    ("replies", "reason"),
    [
        pytest.param({_ASSET: _Reply(500)}, "HTTP 500", id="asset fails"),
        pytest.param({}, "HTTP 404", id="asset and archive missing"),
        pytest.param(
            {_ASSET: _Reply(200, _RELEASE_ZIP, dropped=True)},
            "End of Central Directory record could not be found",
            id="transfer dropped",
        ),
        pytest.param(
            {_ASSET: _Reply(200, _RELEASE_ZIP[: len(_RELEASE_ZIP) // 2])},
            "End of Central Directory record could not be found",
            id="zip cut short",
        ),
    ],
)
def test_a_failed_download_is_one_line(
    tmp_path: Path,
    fake_github: _FakeGitHub,
    stub_programs: dict[str, Path],
    script: Path,
    line: str,
    replies: dict[str, _Reply],
    reason: str,
) -> None:
    r"""A download or extraction that fails says so in one line, and keeps no zip.

    These failures used to reach the user as the error record, whose text is
    the response body for an HTTP error, or as a .NET constructor call for a
    zip that would not open. A dropped transfer is the second kind:
    ``Invoke-WebRequest -OutFile`` keeps the partial file without an error, so
    it fails only at extraction, and the partial zip stayed under ``tmp\``.
    """
    fake_github.replies.update(replies)

    root, output = _stage(tmp_path, fake_github, script, stub_programs["exit1"])

    assert output.splitlines() == [
        f"Downloading {_TAG} ...",
        line.format(f"download incomplete or failed ({reason})"),
    ]
    assert not (root / "tmp" / f"{_TAG}.zip").exists()
    assert not (root / "versions" / _TAG).exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
@pytest.mark.parametrize(
    "script",
    [
        pytest.param(REPO_ROOT / "install.ps1", id="installer"),
        pytest.param(REPO_ROOT / "scripts" / "launcher.ps1", id="launcher"),
    ],
)
@pytest.mark.parametrize(
    "replies",
    [
        pytest.param({_ASSET: _Reply(200, _RELEASE_ZIP)}, id="asset"),
        pytest.param({_ARCHIVE: _Reply(200, _RELEASE_ZIP)}, id="archive fallback"),
    ],
)
def test_a_good_download_goes_on_to_the_sync(
    tmp_path: Path,
    fake_github: _FakeGitHub,
    stub_programs: dict[str, Path],
    script: Path,
    replies: dict[str, _Reply],
) -> None:
    """A download that works is extracted, checked, and handed to the sync."""
    fake_github.replies.update(replies)

    _, output = _stage(tmp_path, fake_github, script, stub_programs["exit1"])

    assert f"uv sync failed for {_TAG} (exit 1)" in output, output
    assert "download incomplete" not in output, output


# Runs the whole installer with no tag, so it looks up releases/latest itself,
# at the fake server named by the third argument.
_LOOKUP_DRIVER = r"""
$server = $args[2]
function Invoke-RestMethod {
    param([string]$Uri, [switch]$UseBasicParsing, [int]$TimeoutSec)
    $api = 'https://api.github.com'
    if (-not $Uri.StartsWith("$api/")) { throw "unexpected request: $Uri" }
    Microsoft.PowerShell.Utility\Invoke-RestMethod -UseBasicParsing `
        -TimeoutSec $TimeoutSec -Uri ($server + $Uri.Substring($api.Length))
}
& $args[1] -InstallRoot $args[0]
exit $LASTEXITCODE
"""


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell 5.1 only")
def test_a_failed_release_lookup_is_one_line(
    tmp_path: Path, fake_github: _FakeGitHub
) -> None:
    """The installer's own ``releases/latest`` lookup fails in one line too.

    Run without a tag, the installer resolves the latest release itself. A
    404 there already had its line; anything else was rethrown, and the
    console printed the response body as the error.
    """
    if not WINDOWS_POWERSHELL.is_file():
        pytest.skip(f"{WINDOWS_POWERSHELL} not found")
    fake_github.replies[_LATEST] = _Reply(500)
    root = tmp_path / "install-root"

    result = _windows_powershell(
        tmp_path,
        _LOOKUP_DRIVER,
        [str(root), str(REPO_ROOT / "install.ps1"), fake_github.url],
    )

    assert result.returncode == 1
    assert result.stdout.splitlines() == [
        "ERROR: download incomplete or failed (HTTP 500)."
    ]
    assert not root.exists()
