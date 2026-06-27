param(
    [string]$BundleConfig = "",
    [switch]$OpenOnly,
    [switch]$NoOpen,
    [switch]$SkipStartupFallback
)

$ErrorActionPreference = "Stop"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Resolve-FirstExistingPath {
    param([string[]]$Candidates)
    foreach ($candidate in $Candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path -LiteralPath $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return ""
}

function Resolve-SystemSyncWindowsDir {
    $candidates = @(
        (Join-Path $PSScriptRoot "windows"),
        $PSScriptRoot,
        (Join-Path $env:USERPROFILE "Sync\_tools\SystemSyncWindows"),
        (Join-Path $env:ProgramData "SystemSyncAgent")
    )
    foreach ($candidate in $candidates) {
        if ((Test-Path -LiteralPath (Join-Path $candidate "OpenDashboard.ps1")) -or
            (Test-Path -LiteralPath (Join-Path $candidate "install-agent.ps1"))) {
            return $candidate
        }
    }
    return ""
}

function Resolve-BundleConfig {
    if (-not [string]::IsNullOrWhiteSpace($BundleConfig)) {
        return (Resolve-Path -LiteralPath $BundleConfig).Path
    }

    return Resolve-FirstExistingPath @(
        (Join-Path $PSScriptRoot "windows\agent-config.generated.json"),
        (Join-Path $PSScriptRoot "agent-config.generated.json"),
        (Join-Path $env:USERPROFILE "Sync\_tools\SystemSyncWindows\agent-config.generated.json"),
        (Join-Path $env:ProgramData "SystemSyncAgent\agent-config.json")
    )
}

function Quote-ProcessArg {
    param([string]$Value)
    if ($Value -match '[\s"]') {
        return '"' + ($Value -replace '"', '\"') + '"'
    }
    return $Value
}

function Restart-AsAdministrator {
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", (Quote-ProcessArg $PSCommandPath)
    )
    if (-not [string]::IsNullOrWhiteSpace($BundleConfig)) {
        $args += @("-BundleConfig", (Quote-ProcessArg $BundleConfig))
    }
    if ($OpenOnly) {
        $args += "-OpenOnly"
    }
    if ($NoOpen) {
        $args += "-NoOpen"
    }
    if ($SkipStartupFallback) {
        $args += "-SkipStartupFallback"
    }
    Start-Process -FilePath "powershell.exe" -ArgumentList ($args -join " ") -Verb RunAs | Out-Null
}

function Open-SystemSyncDashboard {
    param(
        [string]$WindowsDir,
        [string]$ConfigPath
    )

    $launcher = Resolve-FirstExistingPath @(
        (Join-Path $env:ProgramData "SystemSyncAgent\OpenDashboard.ps1"),
        (Join-Path $WindowsDir "OpenDashboard.ps1")
    )
    if (-not $launcher) {
        throw "OpenDashboard.ps1 was not found."
    }

    $config = Resolve-FirstExistingPath @(
        $ConfigPath,
        (Join-Path $env:ProgramData "SystemSyncAgent\agent-config.json"),
        (Join-Path $WindowsDir "agent-config.generated.json")
    )
    if (-not $config) {
        throw "No SystemSync dashboard config was found."
    }

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $launcher -ConfigPath $config
}

if ($PSVersionTable.PSEdition -and $PSVersionTable.PSVersion.Major -lt 5) {
    throw "SystemSync requires Windows PowerShell 5 or newer."
}

$windowsDir = Resolve-SystemSyncWindowsDir
if (-not $windowsDir) {
    throw "SystemSync Windows tools were not found. Run this script from the repo root or the synced SystemSyncWindows folder."
}

$bundlePath = Resolve-BundleConfig
if ($OpenOnly) {
    Open-SystemSyncDashboard -WindowsDir $windowsDir -ConfigPath $bundlePath
    exit 0
}

if (-not $bundlePath) {
    $message = @"
Missing SystemSync pairing config.

Run this on the Mac controller first:
  ./setup.sh

Then wait for Syncthing to sync:
  <SyncRoot>\_tools\SystemSyncWindows\agent-config.generated.json

You can also pass it explicitly:
  .\setup.ps1 -BundleConfig C:\Path\agent-config.generated.json
"@
    throw $message
}

if (-not (Test-IsAdministrator)) {
    Write-Host "Requesting administrator permission for firewall, scheduled task, hosts, and shortcuts..."
    Restart-AsAdministrator
    exit 0
}

$installScript = Resolve-FirstExistingPath @(
    (Join-Path $windowsDir "install-agent.ps1"),
    (Join-Path $PSScriptRoot "windows\install-agent.ps1")
)
if (-not $installScript) {
    throw "install-agent.ps1 was not found."
}

$installArgs = @("-BundleConfig", $bundlePath)
if ($SkipStartupFallback) {
    $installArgs += "-SkipStartupFallback"
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installScript @installArgs

if (-not $NoOpen) {
    Open-SystemSyncDashboard -WindowsDir $windowsDir -ConfigPath (Join-Path $env:ProgramData "SystemSyncAgent\agent-config.json")
}

Write-Host ""
Write-Host "SystemSync Windows setup complete." -ForegroundColor Green
