# Corporate Serf Dashboard install shim.
#
# Fetched from main and piped to iex:
#   irm https://raw.githubusercontent.com/MingoDynasty/Corporate-Serf-Dashboard/main/get.ps1 | iex
#
# Deliberately trivial and permanently backward-compatible: resolve the
# latest release, fetch THAT release's installer, run it. Nothing else,
# ever. The installer is always the same age as the payload it installs, so
# this file never constrains what a future install.ps1 can change.
#
# Runs under iex, so: no param block, no functions (they would leak into the
# caller's session), and `return` -- never `exit`, which could close the
# user's console.
#
# Targets Windows PowerShell 5.1.

$ErrorActionPreference = 'Stop'
[System.Net.ServicePointManager]::SecurityProtocol = `
    [System.Net.ServicePointManager]::SecurityProtocol -bor `
    [System.Net.SecurityProtocolType]::Tls12

$csdRepo = 'MingoDynasty/Corporate-Serf-Dashboard'
$csdNotReady = 'Corporate Serf Dashboard: the release is not ready yet -- try again shortly.'

$csdRelease = $null
try {
    $csdRelease = Invoke-RestMethod -UseBasicParsing -TimeoutSec 30 `
        -Uri "https://api.github.com/repos/$csdRepo/releases/latest"
} catch {
    $csdStatus = 0
    try { $csdStatus = [int]$_.Exception.Response.StatusCode } catch { }
    if ($csdStatus -eq 404) { Write-Host $csdNotReady; return }
    throw
}
$csdTag = [string]$csdRelease.tag_name

$csdInstaller = $null
try {
    $csdInstaller = Invoke-WebRequest -UseBasicParsing -TimeoutSec 30 `
        -Uri "https://raw.githubusercontent.com/$csdRepo/$csdTag/install.ps1"
} catch {
    $csdStatus = 0
    try { $csdStatus = [int]$_.Exception.Response.StatusCode } catch { }
    if ($csdStatus -eq 404) { Write-Host $csdNotReady; return }
    throw
}

# Run from a file rather than iex so the installer's param block works and
# its `exit` cannot close the user's console. The file runs in a child
# Windows PowerShell with a process-scoped Bypass: stock clients default to
# the Restricted execution policy, which runs piped iex content but refuses
# script FILES -- invoking the temp file directly would die with "running
# scripts is disabled". The child also guarantees 5.1 semantics even when
# the one-liner was pasted into pwsh.
$csdContent = $csdInstaller.Content
if ($csdContent -is [byte[]]) { $csdContent = [System.Text.Encoding]::UTF8.GetString($csdContent) }
$csdInstallerPath = Join-Path $env:TEMP "csd-install-$csdTag.ps1"
[System.IO.File]::WriteAllText($csdInstallerPath, [string]$csdContent, `
        [System.Text.UTF8Encoding]::new($false))
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile `
    -ExecutionPolicy Bypass -File $csdInstallerPath -LatestTag $csdTag @args
