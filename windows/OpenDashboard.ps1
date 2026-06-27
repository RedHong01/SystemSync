param(
    [string]$ConfigPath = "$env:ProgramData\SystemSyncAgent\agent-config.json",
    [int]$TimeoutSeconds = 3
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Read-DashboardConfig {
    param([string]$Path)

    $candidates = @(
        $Path,
        "$env:ProgramData\SystemSyncAgent\agent-config.json",
        "$env:ProgramData\RedLanSyncAgent\agent-config.json",
        (Join-Path $PSScriptRoot "agent-config.json"),
        (Join-Path $PSScriptRoot "agent-config.generated.json")
    )
    foreach ($candidate in $candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path -LiteralPath $candidate)) {
            return Get-Content -LiteralPath $candidate -Raw | ConvertFrom-Json
        }
    }
    throw "No SystemSync agent config was found. Run windows/install-agent.ps1 first."
}

function Add-Candidate {
    param(
        [Parameter(Mandatory = $true)]$Items,
        [string]$Url,
        [string]$Label
    )

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return
    }
    $trimmed = $Url.TrimEnd("/")
    if (-not ($Items | Where-Object { $_.Url -eq $trimmed })) {
        $Items.Add([PSCustomObject]@{ Url = $trimmed; Label = $Label }) | Out-Null
    }
}

function Test-DashboardUrl {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$TimeoutSeconds = 3
    )

    try {
        $testUrl = $Url.TrimEnd("/") + "/api/config"
        $response = Invoke-WebRequest -Uri $testUrl -Method Get -UseBasicParsing -TimeoutSec $TimeoutSeconds -ErrorAction Stop
        if ([int]$response.StatusCode -lt 200 -or [int]$response.StatusCode -ge 300) {
            return $false
        }
        $json = $response.Content | ConvertFrom-Json
        return $null -ne $json.dashboard_urls
    }
    catch {
        return $false
    }
}

function Get-AuthUrl {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [Parameter(Mandatory = $true)][string]$Token
    )

    return $BaseUrl.TrimEnd("/") + "/auth?token=" + [Uri]::EscapeDataString($Token)
}

function Show-OpenDashboardError {
    param(
        [Parameter(Mandatory = $true)]$Candidates
    )

    $message = @(
        "SystemSync is not reachable.",
        "",
        "Tried:",
        (($Candidates | ForEach-Object { "- $($_.Url) [$($_.Label)]" }) -join "`n"),
        "",
        "Check that the Mac dashboard is running, both devices are on the same LAN, and the Mac IP in agent-config.json is current."
    ) -join "`n"

    try {
        $shell = New-Object -ComObject WScript.Shell
        [void]$shell.Popup($message, 0, "SystemSync", 48)
    }
    catch {
        Write-Host $message
    }
}

$config = Read-DashboardConfig -Path $ConfigPath
$candidates = [System.Collections.Generic.List[object]]::new()

Add-Candidate -Items $candidates -Url ([string]$config.DashboardUrl) -Label "Mac LAN URL"

if (-not [string]::IsNullOrWhiteSpace([string]$config.MacIp)) {
    $port = 8765
    try {
        $dashboardUri = [Uri]([string]$config.DashboardUrl)
        if ($dashboardUri.Port -gt 0) {
            $port = $dashboardUri.Port
        }
    }
    catch {
    }
    Add-Candidate -Items $candidates -Url ("http://{0}:{1}" -f [string]$config.MacIp, $port) -Label "Mac IP fallback"
}

Add-Candidate -Items $candidates -Url ([string]$config.DashboardAliasUrl) -Label "friendly alias"

$reachable = $null
foreach ($candidate in $candidates) {
    if (Test-DashboardUrl -Url $candidate.Url -TimeoutSeconds $TimeoutSeconds) {
        $reachable = $candidate
        break
    }
}

if ($reachable) {
    $target = $reachable.Url
    if (-not [string]::IsNullOrWhiteSpace([string]$config.Token)) {
        $target = Get-AuthUrl -BaseUrl $reachable.Url -Token ([string]$config.Token)
    }
    Start-Process $target
    exit 0
}

Show-OpenDashboardError -Candidates $candidates
exit 1
