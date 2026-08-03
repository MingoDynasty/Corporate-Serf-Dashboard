# Corporate Serf Dashboard launcher bootstrap.
# csd-bootstrap-version: 1
#
# The installer copies this file to the install root as launch.ps1, and the
# desktop shortcut targets that copy. Per-tag version directories get pruned,
# so the shortcut must never point into one; this file is the stable
# entrypoint that outlives version swaps.
#
# Deliberately trivial: read the install manifest, delegate to the selected
# version's launcher, nothing else. When a release ships a higher
# csd-bootstrap-version, the versioned launcher replaces the installed copy
# atomically (same-directory temp file, validate, rename) -- never edit the
# installed copy in place.
#
# Targets Windows PowerShell 5.1.

$ErrorActionPreference = 'Stop'

function Stop-WithMessage([string]$Message) {
    Write-Host "ERROR: $Message" -ForegroundColor Red
    Write-Host 'If this install is broken, re-run the install one-liner:'
    Write-Host '  irm https://raw.githubusercontent.com/MingoDynasty/Corporate-Serf-Dashboard/main/get.ps1 | iex'
    Read-Host 'Press Enter to close' | Out-Null
    exit 1
}

$manifestPath = Join-Path $PSScriptRoot 'install.json'
$manifest = $null
try {
    $manifest = [System.IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
} catch {
    Stop-WithMessage "cannot read $manifestPath ($($_.Exception.Message))"
}

$tag = [string]$manifest.tag
if ([string]$manifest.update_policy -eq 'pinned' -and $manifest.pinned_tag) {
    $tag = [string]$manifest.pinned_tag
}

$launcher = Join-Path $PSScriptRoot "versions\$tag\scripts\launcher.ps1"
if (-not (Test-Path -LiteralPath $launcher)) {
    Stop-WithMessage "launcher for version $tag not found at $launcher"
}

& $launcher -InstallRoot $PSScriptRoot
exit $LASTEXITCODE
