<#
Corporate Serf Dashboard installer.

Normally fetched and executed at a release tag by get.ps1, so it is always
the same age as the payload it installs; run standalone it resolves the
latest release itself. Installs the entire toolchain app-locally (uv,
managed CPython, cache) under the install root -- nothing on the machine
outside that root is used or disturbed, and uninstalling is deleting the
folder and the desktop shortcut.

`-Tag vX` installs that exact release and pins it (rollback): the manifest
records update_policy "pinned", which the launcher honors by skipping the
update check. Re-running the installer without -Tag restores "latest".

Serialization contract: every machine-readable file written here
(config.toml, install.json) is UTF-8 WITHOUT BOM with forward-slash paths --
the app's Python 3.14 tomllib rejects both a BOM and raw backslashes.

The release zip's top-level directory name is DISCOVERED after extraction,
never derived: the named asset and GitHub's source-archive fallback use
different prefixes for the same tag (the fallback strips the "v").

Targets Windows PowerShell 5.1.
#>
[CmdletBinding()]
param(
    # Install this exact release and pin it (rollback).
    [string]$Tag,
    # Install location; overridable for testing.
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'CorporateSerfDashboard'),
    # Internal, passed by get.ps1: the latest tag it resolved and fetched this
    # installer from. Installs that tag WITHOUT pinning, so the installer and
    # its payload can never skew even if a release publishes mid-install.
    [string]$LatestTag
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[System.Net.ServicePointManager]::SecurityProtocol = `
    [System.Net.ServicePointManager]::SecurityProtocol -bor `
    [System.Net.SecurityProtocolType]::Tls12

$Repo = 'MingoDynasty/Corporate-Serf-Dashboard'
$ApiBase = 'https://api.github.com'
$DownloadBase = 'https://github.com'
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$DefaultPort = 8050

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Stop-Fatal([string]$Message) {
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Get-HttpStatusCode($ErrorRecord) {
    try { return [int]$ErrorRecord.Exception.Response.StatusCode } catch { return 0 }
}

function Write-FileAtomic([string]$Path, [string]$Content) {
    $temp = "$Path.new"
    [System.IO.File]::WriteAllText($temp, $Content, $Utf8NoBom)
    if (Test-Path -LiteralPath $Path) {
        # [NullString]::Value, not $null: PowerShell binds $null as "" for
        # String parameters, and .NET Framework rejects the empty path.
        [System.IO.File]::Replace($temp, $Path, [NullString]::Value)
    } else {
        Move-Item -LiteralPath $temp -Destination $Path
    }
}

function Get-ReleaseInfo([string]$ReleaseTag) {
    # GitHub serves release assets as octet-stream, so .Content may be bytes.
    $raw = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 30 `
            -Uri "$DownloadBase/$Repo/releases/download/$ReleaseTag/release.json").Content
    if ($raw -is [byte[]]) { $raw = [System.Text.Encoding]::UTF8.GetString($raw) }
    return $raw | ConvertFrom-Json
}

function Install-UvVersion([string]$UvVersion) {
    # uv is per release, not per install: the exact pinned uv must be present
    # app-locally before syncing the release that pins it.
    $uvDir = Join-Path $InstallRoot "uv\$UvVersion"
    $uvExe = Join-Path $uvDir 'uv.exe'
    if (Test-Path -LiteralPath $uvExe) { return $uvExe }

    Write-Host "Provisioning uv $UvVersion ..."
    $tempDir = Join-Path $InstallRoot 'tmp'
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    $uvInstaller = Join-Path $tempDir 'uv-install.ps1'
    Invoke-WebRequest -UseBasicParsing -TimeoutSec 300 `
        -Uri "https://astral.sh/uv/$UvVersion/install.ps1" -OutFile $uvInstaller
    $env:UV_UNMANAGED_INSTALL = $uvDir
    try {
        & $uvInstaller
    } finally {
        Remove-Item Env:\UV_UNMANAGED_INSTALL -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path -LiteralPath $uvExe)) {
        Stop-Fatal "the uv $UvVersion installer did not produce $uvExe"
    }
    return $uvExe
}

function Install-ReleaseVersion($Release, [string]$UvExe) {
    # Download + extract the release into versions\<tag> and sync its venv.
    $releaseTag = [string]$Release.tag
    $versionsDir = Join-Path $InstallRoot 'versions'
    $targetDir = Join-Path $versionsDir $releaseTag
    $tempDir = Join-Path $InstallRoot 'tmp'
    New-Item -ItemType Directory -Force -Path $versionsDir, $tempDir | Out-Null

    Write-Host "Downloading $releaseTag ..."
    $zipPath = Join-Path $tempDir "$releaseTag.zip"
    try {
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 600 `
            -Uri "$DownloadBase/$Repo/releases/download/$releaseTag/$($Release.source_asset)" -OutFile $zipPath
    } catch {
        if ((Get-HttpStatusCode $_) -ne 404) { throw }
        # Named asset missing: fall back to the tag's source archive. Same
        # member set, different top-level directory name -- discovered below.
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 600 `
            -Uri "$DownloadBase/$Repo/archive/refs/tags/$releaseTag.zip" -OutFile $zipPath
    }

    $extractDir = Join-Path $tempDir "extract-$releaseTag"
    if (Test-Path -LiteralPath $extractDir) { Remove-Item -LiteralPath $extractDir -Recurse -Force }
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir
    $top = @(Get-ChildItem -LiteralPath $extractDir)
    if ($top.Count -ne 1 -or -not $top[0].PSIsContainer) {
        Stop-Fatal "expected exactly one top-level directory in the $releaseTag zip, found $($top.Count) entries"
    }

    # The identity stamp is what /health and the launcher's promotion gate
    # report and compare, so a mismatched zip must fail the install here.
    $stamp = [System.IO.File]::ReadAllText((Join-Path $top[0].FullName 'version.txt'))
    if ($stamp -notmatch [regex]::Escape([string]$Release.sha)) {
        Stop-Fatal "version.txt in the $releaseTag zip does not carry the release SHA $($Release.sha)"
    }

    # A reinstall may target the tag the install currently runs -- deleting
    # that directory before the replacement has synced would leave a bricked
    # install if the sync fails (network outage, resolver error). Park the
    # existing copy under tmp instead; a rename is same-volume and reversible,
    # and the venv stays valid because restore returns it to its original
    # path. On success the tmp cleanup at the end of the install removes it.
    $backupDir = $null
    if (Test-Path -LiteralPath $targetDir) {
        $backupDir = Join-Path $tempDir "previous-$releaseTag"
        if (Test-Path -LiteralPath $backupDir) { Remove-Item -LiteralPath $backupDir -Recurse -Force }
        Move-Item -LiteralPath $targetDir -Destination $backupDir
    }
    try {
        Move-Item -LiteralPath $top[0].FullName -Destination $targetDir
        Remove-Item -LiteralPath $extractDir -Recurse -Force
        Remove-Item -LiteralPath $zipPath -Force

        Write-Host "Installing dependencies for $releaseTag ..."
        & $UvExe sync --directory $targetDir --locked --no-dev --managed-python
        if ($LASTEXITCODE -ne 0) { throw "uv sync failed for $releaseTag (exit $LASTEXITCODE)" }
    } catch {
        $message = $_.Exception.Message
        # The restore itself can fail (a lingering handle on the partial
        # tree, AV holding a fresh DLL); never let that second failure
        # replace the first one's message or hide where the good copy is.
        try {
            if (Test-Path -LiteralPath $targetDir) { Remove-Item -LiteralPath $targetDir -Recurse -Force }
            if ($backupDir -and (Test-Path -LiteralPath $backupDir)) {
                Move-Item -LiteralPath $backupDir -Destination $targetDir
                Stop-Fatal "install of $releaseTag failed ($message); the previously installed copy was restored."
            }
        } catch {
            Stop-Fatal "install of $releaseTag failed ($message), and the previous copy could not be restored automatically. It is intact at $backupDir -- move it back to $targetDir, or re-run the install one-liner."
        }
        Stop-Fatal "install of $releaseTag failed ($message)."
    }
    return $targetDir
}

function Find-KovaaksStatsDir {
    # Steam's registry install path plus every library in libraryfolders.vdf.
    $steamRoots = @()
    $candidates = @(
        @{ Path = 'HKCU:\Software\Valve\Steam'; Name = 'SteamPath' },
        @{ Path = 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam'; Name = 'InstallPath' },
        @{ Path = 'HKLM:\SOFTWARE\Valve\Steam'; Name = 'InstallPath' }
    )
    foreach ($candidate in $candidates) {
        try {
            $value = (Get-ItemProperty -Path $candidate.Path -ErrorAction Stop).($candidate.Name)
            if ($value) { $steamRoots += [string]$value }
        } catch { }
    }

    $libraries = @($steamRoots)
    foreach ($root in $steamRoots) {
        $vdfPath = Join-Path $root 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdfPath) {
            $vdf = [System.IO.File]::ReadAllText($vdfPath)
            foreach ($match in [regex]::Matches($vdf, '"path"\s*"([^"]*)"')) {
                $libraries += $match.Groups[1].Value -replace '\\\\', '\'
            }
        }
    }

    foreach ($library in $libraries | Select-Object -Unique) {
        $stats = Join-Path $library 'steamapps\common\FPSAimTrainer\FPSAimTrainer\stats'
        if (Test-Path -LiteralPath $stats -PathType Container) {
            return (Resolve-Path -LiteralPath $stats).Path
        }
    }
    return $null
}

function Resolve-StatsDir {
    $detected = Find-KovaaksStatsDir
    if ($detected) {
        Write-Host "Detected KovaaK's stats directory:"
        Write-Host "  $detected"
        $answer = Read-Host 'Use it? [Y/n]'
        if ($answer -eq '' -or $answer -match '^[Yy]') { return $detected }
    } else {
        Write-Host "Could not find the KovaaK's stats directory automatically."
    }
    for ($attempt = 0; $attempt -lt 3; $attempt++) {
        $manual = Read-Host "Enter the full path to your KovaaK's stats folder (usually <Steam library>\steamapps\common\FPSAimTrainer\FPSAimTrainer\stats)"
        if ($manual -and (Test-Path -LiteralPath $manual -PathType Container)) {
            return (Resolve-Path -LiteralPath $manual).Path
        }
        Write-Host 'That directory does not exist.'
    }
    Stop-Fatal 'no valid stats directory provided; run the installer again once you know the path.'
}

function Write-FirstRunConfig([string]$StatsDir, [int]$Port) {
    $statsDirToml = $StatsDir.Replace('\', '/')
    $lines = @(
        '# Corporate Serf Dashboard configuration.',
        '# Written by the installer on first install; edit freely -- installs and',
        '# updates never touch an existing config.toml. See example.toml in the',
        '# installed version directory for all optional settings.',
        '',
        "# Directory where the KovaaK's stats files are stored.",
        "stats_dir = ""$statsDirToml""",
        '',
        '# How often to poll for updates (in milliseconds).',
        'polling_interval = 1000',
        '',
        '# Port for the local dashboard server. If another program already',
        '# uses it, the dashboard says so at startup -- pick a different port here.',
        "port = $Port",
        '',
        '# How many decimal places to round the Sensitivity.',
        'sens_round_decimal_places = 1'
    )
    Write-FileAtomic -Path (Join-Path $InstallRoot 'config.toml') -Content (($lines -join "`n") + "`n")
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# Resolve which release to install.
$pinned = $false
if ($Tag) {
    $targetTag = $Tag
    $pinned = $true
} elseif ($LatestTag) {
    $targetTag = $LatestTag
} else {
    try {
        $latest = Invoke-RestMethod -UseBasicParsing -TimeoutSec 30 -Uri "$ApiBase/repos/$Repo/releases/latest"
        $targetTag = [string]$latest.tag_name
    } catch {
        if ((Get-HttpStatusCode $_) -eq 404) {
            Stop-Fatal 'no release is published yet -- try again shortly.'
        }
        throw
    }
}

Write-Host "Installing Corporate Serf Dashboard $targetTag to $InstallRoot"

$release = $null
try {
    $release = Get-ReleaseInfo $targetTag
} catch {
    Stop-Fatal "cannot read release.json for $targetTag ($($_.Exception.Message))."
}
# Unknown schema: this installer is too old for the release it was pointed
# at. Loud abort -- get.ps1 always pairs a fresh installer with a fresh
# payload, so re-running the one-liner recovers.
if ([int]$release.schema_version -ne 1) {
    Stop-Fatal "release $targetTag has schema_version '$($release.schema_version)', which this installer does not understand. Re-run the install one-liner to get the matching installer."
}
foreach ($field in 'tag', 'sha', 'commit_date', 'uv_version', 'source_asset') {
    if (-not $release.$field) { Stop-Fatal "release.json for $targetTag is missing '$field'." }
}

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
$InstallRoot = (Resolve-Path -LiteralPath $InstallRoot).Path

# The whole toolchain lives under the install root.
$env:UV_PYTHON_INSTALL_DIR = Join-Path $InstallRoot 'python'
$env:UV_CACHE_DIR = Join-Path $InstallRoot 'uv-cache'

$uvExe = Install-UvVersion ([string]$release.uv_version)
$versionDir = Install-ReleaseVersion $release $uvExe

# First-run config. An existing config.toml (and data/) is never touched.
$configPath = Join-Path $InstallRoot 'config.toml'
if (Test-Path -LiteralPath $configPath) {
    Write-Host 'Keeping the existing config.toml.'
} else {
    $statsDir = Resolve-StatsDir
    Write-FirstRunConfig -StatsDir $statsDir -Port $DefaultPort
    Write-Host "Wrote $configPath (dashboard port $DefaultPort)."
}

# Round-trip the config through the installed app's own loader BEFORE the
# manifest or shortcut exist: a config the app cannot parse must fail the
# install loudly, never surface later as a broken first launch. Using
# load_config (tomllib underneath, plus the app's schema validation) rather
# than bare tomllib catches missing/mistyped required fields too -- the
# config is kept on reinstall, so a schema miss here would never self-heal.
$python = Join-Path $versionDir '.venv\Scripts\python.exe'
$env:CSD_STATE_DIR = $InstallRoot
try {
    & $python -c 'from source.config.config_service import load_config; load_config()'
} finally {
    Remove-Item Env:\CSD_STATE_DIR -ErrorAction SilentlyContinue
}
if ($LASTEXITCODE -ne 0) {
    Stop-Fatal "the installed app cannot load $configPath (details above) -- fix or delete it and run the installer again."
}

# Manifest (install.json, schema v1): the authoritative install identity.
$manifest = [ordered]@{
    schema_version = 1
    tag            = [string]$release.tag
    sha            = [string]$release.sha
    commit_date    = [string]$release.commit_date
    update_policy  = 'latest'
}
if ($pinned) {
    $manifest.update_policy = 'pinned'
    $manifest.pinned_tag = [string]$release.tag
}
Write-FileAtomic -Path (Join-Path $InstallRoot 'install.json') -Content (($manifest | ConvertTo-Json) + "`n")

# Stable bootstrap at the root; the shortcut must never point into a
# versioned directory, because those get pruned.
$bootstrapTemplate = Join-Path $versionDir 'scripts\launch_bootstrap.ps1'
if (-not (Test-Path -LiteralPath $bootstrapTemplate)) {
    Stop-Fatal "release $targetTag ships no scripts\launch_bootstrap.ps1; cannot write launch.ps1."
}
Write-FileAtomic -Path (Join-Path $InstallRoot 'launch.ps1') -Content ([System.IO.File]::ReadAllText($bootstrapTemplate))

# Desktop shortcut.
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Corporate Serf Dashboard.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File ""$(Join-Path $InstallRoot 'launch.ps1')"""
$shortcut.WorkingDirectory = $InstallRoot
$shortcut.Save()

Remove-Item -LiteralPath (Join-Path $InstallRoot 'tmp') -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ''
Write-Host "Installed Corporate Serf Dashboard $targetTag." -ForegroundColor Green
if ($pinned) {
    Write-Host "This install is PINNED to $targetTag and will not auto-update." -ForegroundColor Yellow
    Write-Host 'Re-run the installer without -Tag to return to automatic updates.'
}
Write-Host 'Launch it from the "Corporate Serf Dashboard" desktop shortcut.'
Write-Host "To uninstall: delete the shortcut and the folder $InstallRoot"
