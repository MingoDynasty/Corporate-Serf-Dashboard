<#
Corporate Serf Dashboard versioned launcher.

Ships inside every release zip and is invoked by the install root's
launch.ps1 bootstrap. Owns the whole launch transaction: single-instance
mutex, update check per the manifest policy, pending activation gated on the
/health identity probe, atomic promotion, version pruning, and bootstrap
self-update.

Wire contract (v1, frozen): this launcher may be the one executing any
future update, so everything it parses from a release -- release.json field
names and types, the release asset names and download paths, the uv/Python
provisioning inputs -- is versioned by release.json's schema_version. An
unknown schema_version or a parse failure runs the current install and tells
the user to re-run the install one-liner; it must never strand silently.

The release zip's top-level directory name is DISCOVERED after extraction,
never derived: the named asset and GitHub's source-archive fallback use
different prefixes for the same tag (the fallback strips the "v").

Targets Windows PowerShell 5.1.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InstallRoot
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[System.Net.ServicePointManager]::SecurityProtocol = `
    [System.Net.ServicePointManager]::SecurityProtocol -bor `
    [System.Net.SecurityProtocolType]::Tls12

$Repo = 'MingoDynasty/Corporate-Serf-Dashboard'
$ApiBase = 'https://api.github.com'
$DownloadBase = 'https://github.com'
$InstallOneLiner = 'irm https://raw.githubusercontent.com/MingoDynasty/Corporate-Serf-Dashboard/main/get.ps1 | iex'
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$UpdateCheckTimeoutSec = 5
$HealthTimeoutSec = 120
$DefaultPort = 8050
$DefaultHost = '127.0.0.1'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Stop-Fatal([string]$Message) {
    Write-Host "ERROR: $Message" -ForegroundColor Red
    Write-Host 'If this install is broken, re-run the install one-liner:'
    Write-Host "  $InstallOneLiner"
    Read-Host 'Press Enter to close' | Out-Null
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

function Write-Manifest([string]$Tag, [string]$Sha, [string]$CommitDate, [string]$Policy, [string]$PinnedTag) {
    $manifest = [ordered]@{
        schema_version = 1
        tag            = $Tag
        sha            = $Sha
        commit_date    = $CommitDate
        update_policy  = $Policy
    }
    if ($PinnedTag) { $manifest.pinned_tag = $PinnedTag }
    Write-FileAtomic -Path (Join-Path $InstallRoot 'install.json') -Content (($manifest | ConvertTo-Json) + "`n")
}

function Get-ConfiguredEndpoint {
    # One parsing contract with the app: config.toml is user-owned, and TOML
    # integer forms or pydantic coercions a regex would misread (8_051,
    # 0x1F73, "8051") must resolve to the port the server actually binds --
    # a divergence here polls the wrong port and kills a healthy app. Ask
    # the installed app's own loader; fall back to the defaults when anything
    # is unreadable, the same recovery as a missing config.
    #
    # Port and host come back on one line so that the "last line wins" parse
    # stays robust against a config warning the loader may log first.
    try {
        $manifest = [System.IO.File]::ReadAllText((Join-Path $InstallRoot 'install.json')) | ConvertFrom-Json
        $tag = [string]$manifest.tag
        if ([string]$manifest.update_policy -eq 'pinned' -and $manifest.pinned_tag) {
            $tag = [string]$manifest.pinned_tag
        }
        $python = Join-Path $InstallRoot "versions\$tag\.venv\Scripts\python.exe"
        $env:CSD_STATE_DIR = $InstallRoot
        try {
            $endpointText = @(& $python -c 'from source.config.config_service import load_config; c = load_config(); print(f"{c.port} {c.host}")' 2>&1)
        } finally {
            Remove-Item Env:\CSD_STATE_DIR -ErrorAction SilentlyContinue
        }
        if ($LASTEXITCODE -eq 0) {
            $fields = ([string]$endpointText[-1]).Trim() -split '\s+', 2
            if ($fields.Count -eq 2) {
                return @{ Port = [int]$fields[0]; Host = $fields[1] }
            }
        }
    } catch { }
    return @{ Port = $DefaultPort; Host = $DefaultHost }
}

function Format-UrlHost([string]$Address) {
    # IPv6 literals need brackets inside a URL; IPv4 and names must not have
    # them. A colon is only ever present in an IPv6 literal here.
    if ($Address.Contains(':')) { return "[$Address]" }
    return $Address
}

function Get-ProbeAddress([string]$BindHost) {
    # Machine-to-machine, so deliberately resolver-free. A wildcard bind
    # serves every address of its family, so probe that family's loopback;
    # any other host is served at exactly the address it names.
    if ($BindHost -eq '0.0.0.0') { return '127.0.0.1' }
    if ($BindHost -eq '::') { return '[::1]' }
    return (Format-UrlHost $BindHost)
}

function Get-BrowserAddress([string]$BindHost) {
    # `localhost` only on the default host, where the app holds BOTH loopback
    # faces -- so whichever one the resolver picks is ours. Under any other
    # host the app owns at most one face, and an unrelated process can hold
    # the other: an app on 0.0.0.0 plus a stranger on ::1 sends `localhost` to
    # the stranger, after the launcher's own IPv4 health check has already
    # passed. That is the wrong-face ambiguity the dual-loopback bind exists
    # to prevent, so every other host opens at the same literal address the
    # readiness probe already proved reachable.
    if ($BindHost -eq $DefaultHost) { return 'localhost' }
    return (Get-ProbeAddress $BindHost)
}

function Open-Dashboard([int]$Port, [string]$Address) {
    Start-Process "http://${Address}:$Port/"
}

function Get-LatestTag {
    $response = Invoke-RestMethod -UseBasicParsing -TimeoutSec $UpdateCheckTimeoutSec `
        -Uri "$ApiBase/repos/$Repo/releases/latest"
    $tag = [string]$response.tag_name
    if (-not $tag) { throw 'releases/latest returned no tag_name' }
    return $tag
}

function Get-ReleaseInfo([string]$Tag) {
    # Returns the parsed release plus the bytes it was parsed from:
    # Install-ReleaseVersion copies those bytes verbatim into the version
    # directory, and re-serializing the parsed object would not be verbatim.
    # GitHub serves release assets as octet-stream, so .Content may be bytes.
    $raw = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 30 `
            -Uri "$DownloadBase/$Repo/releases/download/$Tag/release.json").Content
    if ($raw -is [byte[]]) {
        $bytes = $raw
        $text = [System.Text.Encoding]::UTF8.GetString($raw)
    } else {
        $text = [string]$raw
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($text)
    }
    $release = $text | ConvertFrom-Json
    if ([int]$release.schema_version -ne 1) {
        throw "unsupported release schema_version '$($release.schema_version)'"
    }
    foreach ($field in 'tag', 'sha', 'commit_date', 'uv_version', 'source_asset') {
        if (-not $release.$field) { throw "release.json is missing '$field'" }
    }
    return [pscustomobject]@{ Release = $release; RawBytes = $bytes }
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
        throw "the uv $UvVersion installer did not produce $uvExe"
    }
    return $uvExe
}

function Install-ReleaseVersion($Release, [byte[]]$ReleaseBytes, [string]$UvExe) {
    # Download + extract the release into versions\<tag> and sync its venv.
    $tag = [string]$Release.tag
    $versionsDir = Join-Path $InstallRoot 'versions'
    $targetDir = Join-Path $versionsDir $tag
    $tempDir = Join-Path $InstallRoot 'tmp'
    New-Item -ItemType Directory -Force -Path $versionsDir, $tempDir | Out-Null

    Write-Host "Downloading $tag ..."
    $zipPath = Join-Path $tempDir "$tag.zip"
    try {
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 600 `
            -Uri "$DownloadBase/$Repo/releases/download/$tag/$($Release.source_asset)" -OutFile $zipPath
    } catch {
        if ((Get-HttpStatusCode $_) -ne 404) { throw }
        # Named asset missing: fall back to the tag's source archive. Same
        # member set, different top-level directory name -- discovered below.
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 600 `
            -Uri "$DownloadBase/$Repo/archive/refs/tags/$tag.zip" -OutFile $zipPath
    }

    $extractDir = Join-Path $tempDir "extract-$tag"
    if (Test-Path -LiteralPath $extractDir) { Remove-Item -LiteralPath $extractDir -Recurse -Force }
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir
    $top = @(Get-ChildItem -LiteralPath $extractDir)
    if ($top.Count -ne 1 -or -not $top[0].PSIsContainer) {
        throw "expected exactly one top-level directory in the $tag zip, found $($top.Count) entries"
    }

    # The /health promotion gate compares SHAs, so a zip whose identity stamp
    # does not match its release.json could never promote -- fail early.
    $stamp = [System.IO.File]::ReadAllText((Join-Path $top[0].FullName 'version.txt'))
    if ($stamp -notmatch [regex]::Escape([string]$Release.sha)) {
        throw "version.txt in the $tag zip does not carry the release SHA $($Release.sha)"
    }

    if (Test-Path -LiteralPath $targetDir) { Remove-Item -LiteralPath $targetDir -Recurse -Force }
    Move-Item -LiteralPath $top[0].FullName -Destination $targetDir
    Remove-Item -LiteralPath $extractDir -Recurse -Force
    Remove-Item -LiteralPath $zipPath -Force

    # Leave the release description beside the code it describes, so the trial
    # run can name its own tag -- the manifest still names the previous version
    # until this one is promoted. Byte-verbatim (never re-serialized): the app
    # reads it as the release published it, and the stamp check above
    # corroborates it right here.
    [System.IO.File]::WriteAllBytes((Join-Path $targetDir 'release.json'), $ReleaseBytes)

    Write-Host "Installing dependencies for $tag ..."
    & $UvExe sync --directory $targetDir --locked --no-dev --managed-python
    if ($LASTEXITCODE -ne 0) { throw "uv sync failed for $tag (exit $LASTEXITCODE)" }
    return $targetDir
}

function Start-AppVersion([string]$VersionDir, [string]$Token) {
    # Run the synced venv's own python directly: no wrapper process between
    # the launcher and the server, so the /health gate and any kill target
    # the real process, and starting the current version never needs the
    # network.
    $python = Join-Path $VersionDir '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        throw "no synced environment at $python"
    }
    $logDir = Join-Path $InstallRoot 'data\logs'
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $env:CSD_STATE_DIR = $InstallRoot
    $env:CSD_LAUNCH_TOKEN = $Token
    try {
        return Start-Process -FilePath $python -ArgumentList 'source/app.py' `
            -WorkingDirectory $VersionDir -PassThru -NoNewWindow `
            -RedirectStandardOutput (Join-Path $logDir 'launcher-app-stdout.log') `
            -RedirectStandardError (Join-Path $logDir 'launcher-app-stderr.log')
    } finally {
        Remove-Item Env:\CSD_LAUNCH_TOKEN -ErrorAction SilentlyContinue
    }
}

function Stop-AppProcess($Process) {
    if ($Process -and -not $Process.HasExited) {
        # /T kills the whole tree in case python spawned children.
        try { & "$env:SystemRoot\System32\taskkill.exe" /PID $Process.Id /T /F | Out-Null } catch { }
        $Process.WaitForExit(10000) | Out-Null
    }
}

function Wait-AppReady($Process, [int]$Port, [string]$ExpectedSha, [string]$Token, [string]$Address) {
    # A bare HTTP 200 is not proof of life: an already-running instance or an
    # unrelated service on the port can answer. Promotion requires the child
    # still alive AND the response carrying the expected full SHA and launch
    # token. Deliberately no tag check: an unpromoted build reports tag null.
    # A start this quick needs no narration, so the console stays silent until
    # the wait passes the gate; from there an elapsed counter distinguishes a
    # slow first-run scan from a hang.
    $heartbeatSec = 5
    $started = [DateTime]::UtcNow
    $deadline = $started.AddSeconds($HealthTimeoutSec)
    $nextHeartbeat = $started.AddSeconds($heartbeatSec)
    $heartbeatShown = $false
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($Process.HasExited) { return 'exited' }
        try {
            $health = Invoke-RestMethod -UseBasicParsing -TimeoutSec 2 -Uri "http://${Address}:$Port/health"
            if ([string]$health.sha -eq $ExpectedSha -and [string]$health.launch_token -eq $Token) {
                if ($heartbeatShown) {
                    $elapsed = [int][Math]::Round(([DateTime]::UtcNow - $started).TotalSeconds)
                    Write-Host "Corporate Serf Dashboard is ready after $elapsed seconds."
                }
                return 'ready'
            }
        } catch { }
        $now = [DateTime]::UtcNow
        if ($now -ge $nextHeartbeat) {
            $elapsed = [int][Math]::Round(($now - $started).TotalSeconds)
            Write-Host "Still starting Corporate Serf Dashboard. $elapsed seconds elapsed."
            $heartbeatShown = $true
            $nextHeartbeat = $now.AddSeconds($heartbeatSec)
        }
        Start-Sleep -Milliseconds 500
    }
    return 'timeout'
}

function Show-AppFailure([string]$Context) {
    Write-Host "WARNING: $Context" -ForegroundColor Yellow
    $errLog = Join-Path $InstallRoot 'data\logs\launcher-app-stderr.log'
    if (Test-Path -LiteralPath $errLog) {
        $tail = Get-Content -LiteralPath $errLog -Tail 15 -ErrorAction SilentlyContinue
        if ($tail) {
            Write-Host '--- app error output ---'
            $tail | ForEach-Object { Write-Host $_ }
            Write-Host '------------------------'
        }
    }
}

function Remove-PrunedVersions([string]$ActiveTag, [string]$PreviousTag) {
    # Keep the active version plus one fallback: the version just replaced
    # when known, otherwise the most recently written other directory.
    $versionsDir = Join-Path $InstallRoot 'versions'
    $others = @(Get-ChildItem -LiteralPath $versionsDir -Directory | Where-Object { $_.Name -ne $ActiveTag })
    $keep = @($ActiveTag)
    if ($PreviousTag -and ($others | Where-Object { $_.Name -eq $PreviousTag })) {
        $keep += $PreviousTag
    } elseif ($others.Count -gt 0) {
        $keep += ($others | Sort-Object LastWriteTime -Descending | Select-Object -First 1).Name
    }
    foreach ($dir in $others) {
        if ($keep -notcontains $dir.Name) {
            try {
                Remove-Item -LiteralPath $dir.FullName -Recurse -Force
                Write-Host "Pruned old version $($dir.Name)."
            } catch {
                Write-Host "WARNING: could not prune old version $($dir.Name): $($_.Exception.Message)"
            }
        }
    }
}

function Get-BootstrapMarker([string]$Path) {
    try { $text = [System.IO.File]::ReadAllText($Path) } catch { return 0 }
    if ($text -match '#\s*csd-bootstrap-version:\s*(\d+)') { return [int]$Matches[1] }
    return 0
}

function Update-Bootstrap([string]$VersionDir) {
    # Replace the root launch.ps1 when this release ships a higher bootstrap
    # marker. Atomic by contract: same-directory temp file, validate marker
    # and syntax, rename over. NEVER truncate the live file in place -- an
    # interrupted in-place write bricks every launch after this one.
    $template = Join-Path $VersionDir 'scripts\launch_bootstrap.ps1'
    $installed = Join-Path $InstallRoot 'launch.ps1'
    if (-not (Test-Path -LiteralPath $template)) { return }
    $templateVersion = Get-BootstrapMarker $template
    if ($templateVersion -le (Get-BootstrapMarker $installed)) { return }

    $temp = "$installed.new"
    [System.IO.File]::WriteAllText($temp, [System.IO.File]::ReadAllText($template), $Utf8NoBom)
    $valid = (Get-BootstrapMarker $temp) -eq $templateVersion
    if ($valid) {
        $parseErrors = $null
        [System.Management.Automation.Language.Parser]::ParseFile($temp, [ref]$null, [ref]$parseErrors) | Out-Null
        if ($parseErrors -and $parseErrors.Count -gt 0) { $valid = $false }
    }
    if (-not $valid) {
        Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
        Write-Host 'WARNING: new launch.ps1 bootstrap failed validation; keeping the current one.'
        return
    }
    if (Test-Path -LiteralPath $installed) {
        [System.IO.File]::Replace($temp, $installed, [NullString]::Value)
    } else {
        Move-Item -LiteralPath $temp -Destination $installed
    }
    Write-Host "Updated the launch.ps1 bootstrap to version $templateVersion."
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

$InstallRoot = (Resolve-Path -LiteralPath $InstallRoot).Path

# uv and its managed Python stay app-local (inherited by every uv call).
$env:UV_PYTHON_INSTALL_DIR = Join-Path $InstallRoot 'python'
$env:UV_CACHE_DIR = Join-Path $InstallRoot 'uv-cache'

# Single instance per install root, held for the launcher+app lifetime. A
# second double-click must not race the update transaction, the manifest, or
# the port: it opens the browser at the running instance and exits untouched.
$rootBytes = [System.Text.Encoding]::UTF8.GetBytes($InstallRoot.ToLowerInvariant())
$rootHash = -join ([System.Security.Cryptography.SHA256]::Create().ComputeHash($rootBytes)[0..7] |
        ForEach-Object { $_.ToString('x2') })
$mutex = New-Object System.Threading.Mutex($false, "Local\CorporateSerfDashboard-$rootHash")
$mutexAcquired = $false
try {
    $mutexAcquired = $mutex.WaitOne(0)
} catch [System.Threading.AbandonedMutexException] {
    # The previous holder died without releasing; we own the mutex now.
    $mutexAcquired = $true
}
if (-not $mutexAcquired) {
    Write-Host 'Corporate Serf Dashboard is already running; opening it in the browser.'
    $running = Get-ConfiguredEndpoint
    Open-Dashboard $running.Port (Get-BrowserAddress $running.Host)
    exit 0
}

try {
    $manifest = $null
    try {
        $manifest = [System.IO.File]::ReadAllText((Join-Path $InstallRoot 'install.json')) | ConvertFrom-Json
    } catch {
        Stop-Fatal "cannot read install.json ($($_.Exception.Message))."
    }
    if ([int]$manifest.schema_version -ne 1) {
        Stop-Fatal "install.json has unsupported schema_version '$($manifest.schema_version)'."
    }
    if (-not $manifest.tag -or -not $manifest.sha) {
        Stop-Fatal 'install.json is missing its tag or sha.'
    }

    $runTag = [string]$manifest.tag
    $runSha = [string]$manifest.sha
    $policy = [string]$manifest.update_policy
    $pinnedTag = [string]$manifest.pinned_tag
    if ($policy -eq 'pinned' -and $pinnedTag) { $runTag = $pinnedTag }
    $endpoint = Get-ConfiguredEndpoint
    $port = $endpoint.Port
    # The app binds $endpoint.Host; these are where that bind is reachable
    # from this machine, for the readiness probe and for the browser.
    $probeAddress = Get-ProbeAddress $endpoint.Host
    $browserAddress = Get-BrowserAddress $endpoint.Host

    $appProcess = $null

    if ($policy -ne 'pinned') {
        $latestTag = $null
        try {
            $latestTag = Get-LatestTag
        } catch {
            # Fail open, offline-safe: any network/API failure runs the
            # existing install unchanged.
            Write-Host "Update check failed ($($_.Exception.Message)); starting the installed version."
        }

        if ($latestTag -and $latestTag -ne $runTag) {
            Write-Host "Update available: $runTag -> $latestTag"
            $releaseInfo = $null
            try {
                $releaseInfo = Get-ReleaseInfo $latestTag
            } catch {
                # Wire-contract failure (unknown schema_version, parse error,
                # missing fields): fail open, but LOUDLY -- silent permanent
                # stranding is the one failure this design must never produce.
                Write-Host ('=' * 74) -ForegroundColor Yellow
                Write-Host "A new release ($latestTag) exists, but this installed launcher cannot" -ForegroundColor Yellow
                Write-Host "understand it ($($_.Exception.Message))." -ForegroundColor Yellow
                Write-Host 'Starting the installed version instead. Updating requires reinstalling:' -ForegroundColor Yellow
                Write-Host "  $InstallOneLiner" -ForegroundColor Yellow
                Write-Host '(Reinstalling keeps your config and data.)' -ForegroundColor Yellow
                Write-Host ('=' * 74) -ForegroundColor Yellow
            }

            if ($releaseInfo) {
                $release = $releaseInfo.Release
                $pending = $null
                try {
                    $uvExe = Install-UvVersion ([string]$release.uv_version)
                    $newDir = Install-ReleaseVersion $release $releaseInfo.RawBytes $uvExe

                    # Pending activation: the new version starts unpromoted;
                    # the manifest still names the previous version until the
                    # identity probe passes.
                    $token = [guid]::NewGuid().ToString('N')
                    Write-Host "Starting $latestTag (pending activation) ..."
                    $pending = Start-AppVersion $newDir $token
                    $state = Wait-AppReady $pending $port ([string]$release.sha) $token $probeAddress
                    if ($state -eq 'ready') {
                        Write-Manifest -Tag ([string]$release.tag) -Sha ([string]$release.sha) `
                            -CommitDate ([string]$release.commit_date) -Policy 'latest' -PinnedTag ''
                        $appProcess = $pending   # promoted: from here on, never kill it
                        Write-Host "Updated to $latestTag."
                        Open-Dashboard $port $browserAddress
                        Remove-PrunedVersions -ActiveTag $latestTag -PreviousTag $runTag
                        Update-Bootstrap $newDir
                    } else {
                        # Timeout or early exit: the crashing release never
                        # becomes the recorded install. Manifest untouched.
                        Stop-AppProcess $pending
                        Show-AppFailure "release $latestTag failed to start ($state); starting $runTag instead."
                    }
                } catch {
                    if ($appProcess) {
                        # Promotion already happened; only a cosmetic
                        # post-update step failed.
                        Write-Host "WARNING: a post-update step failed ($($_.Exception.Message)); the update itself succeeded." -ForegroundColor Yellow
                    } else {
                        # The unpromoted pending process must not survive, or
                        # it would hold the port against the fallback start.
                        Stop-AppProcess $pending
                        Write-Host "Update to $latestTag failed ($($_.Exception.Message)); starting the installed version." -ForegroundColor Yellow
                    }
                }
            }
        }
    }

    if (-not $appProcess) {
        $versionDir = Join-Path $InstallRoot "versions\$runTag"
        $token = [guid]::NewGuid().ToString('N')
        Write-Host "Starting Corporate Serf Dashboard $runTag ..."
        $current = $null
        try {
            $current = Start-AppVersion $versionDir $token
        } catch {
            Stop-Fatal "cannot start version ${runTag}: $($_.Exception.Message)"
        }
        $state = Wait-AppReady $current $port $runSha $token $probeAddress
        if ($state -ne 'ready') {
            Stop-AppProcess $current
            Show-AppFailure "the dashboard failed to start ($state)."
            Stop-Fatal "version $runTag did not become ready on port $port. A readiness failure can be config-caused: check config.toml in $InstallRoot and the app error output above."
        }
        $appProcess = $current
        try {
            Open-Dashboard $port $browserAddress
            Remove-PrunedVersions -ActiveTag $runTag -PreviousTag ''
            Update-Bootstrap $versionDir
        } catch {
            # Cosmetic post-start steps (no browser handler, a locked
            # launch.ps1) must never take down the running app -- the child
            # shares this console and dies with the window.
            Write-Host "WARNING: a post-start step failed ($($_.Exception.Message)); the dashboard is running." -ForegroundColor Yellow
        }
    }

    # Hold the mutex for the launcher+app lifetime.
    Write-Host "Dashboard running at http://${browserAddress}:$port/ -- close this window (or press Ctrl+C) to stop it."
    $appProcess.WaitForExit()
    exit $appProcess.ExitCode
} catch {
    # Last resort: an unexpected terminating error would otherwise close the
    # console window silently (taking the -NoNewWindow app child with it).
    # Stop-Fatal shows the message and pauses; `exit` is flow control, so
    # deliberate exits above never land here.
    Stop-Fatal "unexpected launcher failure: $($_.Exception.Message)"
} finally {
    if ($mutexAcquired) {
        try { $mutex.ReleaseMutex() } catch { }
    }
    $mutex.Dispose()
}
