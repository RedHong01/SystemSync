param(
    [string]$BundleConfig = "$PSScriptRoot\agent-config.generated.json",
    [switch]$NoOpen,
    [switch]$SkipStartupFallback
)

$ErrorActionPreference = "Stop"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Quote-ProcessArg {
    param([string]$Value)
    if ($Value -match '[\s"]') {
        return '"' + ($Value -replace '"', '\"') + '"'
    }
    return $Value
}

if (-not (Test-Path -LiteralPath $BundleConfig)) {
    throw "Missing pairing config: $BundleConfig. Run ./setup.sh on the Mac controller first, then sync or copy this Windows package again."
}

if (-not (Test-IsAdministrator)) {
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", (Quote-ProcessArg $PSCommandPath),
        "-BundleConfig", (Quote-ProcessArg $BundleConfig)
    )
    if ($NoOpen) {
        $args += "-NoOpen"
    }
    if ($SkipStartupFallback) {
        $args += "-SkipStartupFallback"
    }
    Start-Process -FilePath "powershell.exe" -ArgumentList ($args -join " ") -Verb RunAs | Out-Null
    exit 0
}

$installArgs = @("-BundleConfig", $BundleConfig)
if ($SkipStartupFallback) {
    $installArgs += "-SkipStartupFallback"
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\install-agent.ps1" @installArgs

if (-not $NoOpen) {
    $configPath = Join-Path $env:ProgramData "SystemSyncAgent\agent-config.json"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot\OpenDashboard.ps1" -ConfigPath $configPath
}

Write-Host ""
Write-Host "SystemSync Windows setup complete." -ForegroundColor Green
