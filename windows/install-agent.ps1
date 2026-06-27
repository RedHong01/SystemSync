param(
    [string]$InstallDir = "$env:ProgramData\SystemSyncAgent",
    [string]$BundleConfig = "$PSScriptRoot\agent-config.generated.json",
    [switch]$SkipStartupFallback
)

$ErrorActionPreference = "Stop"

function Set-DashboardHostsAlias {
    param(
        [Parameter(Mandatory = $true)][string]$Alias,
        [Parameter(Mandatory = $true)][string]$IpAddress
    )

    if ($Alias -notmatch "^[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]$") {
        throw "Dashboard alias is not a valid local hostname: $Alias"
    }

    $parsedIp = $null
    if (-not [Net.IPAddress]::TryParse($IpAddress, [ref]$parsedIp)) {
        throw "Dashboard alias needs a valid Mac IPv4 address, got: $IpAddress"
    }
    if ($parsedIp.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork) {
        throw "Dashboard alias currently expects an IPv4 Mac address, got: $IpAddress"
    }

    $hostsPath = Join-Path $env:SystemRoot "System32\drivers\etc\hosts"
    $startMarker = "# SystemSync alias start"
    $endMarker = "# SystemSync alias end"
    $legacyStartMarker = "# Red LAN Sync Dashboard alias start"
    $legacyEndMarker = "# Red LAN Sync Dashboard alias end"
    $lines = if (Test-Path -LiteralPath $hostsPath) {
        @(Get-Content -LiteralPath $hostsPath)
    }
    else {
        @()
    }

    $filtered = [System.Collections.Generic.List[string]]::new()
    $insideManagedBlock = $false
    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if ($trimmed -eq $startMarker -or $trimmed -eq $legacyStartMarker) {
            $insideManagedBlock = $true
            continue
        }
        if ($trimmed -eq $endMarker -or $trimmed -eq $legacyEndMarker) {
            $insideManagedBlock = $false
            continue
        }
        if ($insideManagedBlock) {
            continue
        }

        $hostPart = ($line -split "#", 2)[0].Trim()
        $parts = @($hostPart -split "\s+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        if ($parts.Count -gt 1 -and (@($parts[1..($parts.Count - 1)]) -contains $Alias)) {
            continue
        }
        $filtered.Add($line)
    }

    if ($filtered.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($filtered[$filtered.Count - 1])) {
        $filtered.Add("")
    }
    $filtered.Add($startMarker)
    $filtered.Add("$IpAddress`t$Alias")
    $filtered.Add($endMarker)
    $filtered | Set-Content -LiteralPath $hostsPath -Encoding ASCII
    return "$Alias -> $IpAddress"
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "请右键 PowerShell，以管理员身份运行此安装脚本。"
}

if (-not (Test-Path -LiteralPath $BundleConfig)) {
    throw "缺少配对配置：$BundleConfig"
}

$bundle = Get-Content -LiteralPath $BundleConfig -Raw | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace([string]$bundle.Token)) {
    throw "配对配置中没有 Token"
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Copy-Item -LiteralPath "$PSScriptRoot\LanSyncAgent.ps1" -Destination "$InstallDir\LanSyncAgent.ps1" -Force
Copy-Item -LiteralPath "$PSScriptRoot\DependencyScan.ps1" -Destination "$InstallDir\DependencyScan.ps1" -Force
Copy-Item -LiteralPath "$PSScriptRoot\OpenDashboard.ps1" -Destination "$InstallDir\OpenDashboard.ps1" -Force
Copy-Item -LiteralPath $BundleConfig -Destination "$InstallDir\agent-config.json" -Force

$ruleName = "SystemSync Companion 8766"
if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule `
        -DisplayName $ruleName `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort ([int]$bundle.Port) `
        -Profile Any | Out-Null
}

foreach ($adapter in @(Get-NetAdapter -Physical -ErrorAction SilentlyContinue)) {
    try {
        Set-NetAdapterPowerManagement `
            -Name $adapter.Name `
            -WakeOnMagicPacket Enabled `
            -WakeOnPattern Enabled `
            -NoRestart `
            -ErrorAction Stop | Out-Null
    }
    catch {
        Write-Warning "无法自动启用 $($adapter.Name) 的 Wake-on-LAN；请在网卡属性中确认 Magic Packet 设置。"
    }
}

$scriptPath = "$InstallDir\LanSyncAgent.ps1"
$configPath = "$InstallDir\agent-config.json"
$arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`" -ConfigPath `"$configPath`""

$taskName = "SystemSync Companion"
$legacyTaskName = "Red LAN Sync Companion"
try {
    Stop-ScheduledTask -TaskName $legacyTaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $legacyTaskName -Confirm:$false -ErrorAction SilentlyContinue
}
catch {
}
$taskInstalled = $false
try {
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity.Name
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1)
    $taskPrincipal = New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType Interactive -RunLevel Highest

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $taskPrincipal `
        -Force | Out-Null

    Start-ScheduledTask -TaskName $taskName
    $taskInstalled = $true
}
catch {
    Write-Warning "计划任务创建或启动失败，将依赖当前用户 Startup 兜底启动项。错误：$($_.Exception.Message)"
}

$startupFallbackPath = ""
if (-not $SkipStartupFallback) {
    $startupDir = [Environment]::GetFolderPath("Startup")
    New-Item -ItemType Directory -Path $startupDir -Force | Out-Null
    $legacyStartupFallbackPath = Join-Path $startupDir "RedLanSyncCompanion.vbs"
    if (Test-Path -LiteralPath $legacyStartupFallbackPath) {
        Remove-Item -LiteralPath $legacyStartupFallbackPath -Force -ErrorAction SilentlyContinue
    }
    $startupFallbackPath = Join-Path $startupDir "SystemSyncCompanion.vbs"
    $startupCommand = "powershell.exe $arguments"
    $startupCommand = $startupCommand.Replace('"', '""')
    @"
Set WshShell = CreateObject(""WScript.Shell"")
WshShell.Run "$startupCommand", 0, False
"@ | Set-Content -LiteralPath $startupFallbackPath -Encoding ASCII
    try {
        icacls $startupFallbackPath /grant "$($identity.Name):RX" | Out-Null
    }
    catch {
        Write-Warning "无法调整 Startup 兜底启动项权限；如果登录后代理未启动，请手动检查：$startupFallbackPath"
    }
}

if (-not $taskInstalled) {
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList $arguments
}

$dashboardEntryUrl = ([string]$bundle.DashboardUrl).TrimEnd("/")
$hostsAlias = ""
if (-not [string]::IsNullOrWhiteSpace([string]$bundle.DashboardAliasUrl) -and
    -not [string]::IsNullOrWhiteSpace([string]$bundle.DashboardAlias) -and
    -not [string]::IsNullOrWhiteSpace([string]$bundle.MacIp)) {
    try {
        $hostsAlias = Set-DashboardHostsAlias -Alias ([string]$bundle.DashboardAlias) -IpAddress ([string]$bundle.MacIp)
    }
    catch {
        Write-Warning "无法写入网页管理端文字域名，将继续使用 IP 地址快捷方式。错误：$($_.Exception.Message)"
    }
}

$shortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Wake RedM3Max.url"
@"
[InternetShortcut]
URL=http://127.0.0.1:$($bundle.Port)/
IconFile=%SystemRoot%\System32\shell32.dll
IconIndex=27
"@ | Set-Content -LiteralPath $shortcutPath -Encoding ASCII

$launcherPath = "$InstallDir\OpenDashboard.ps1"
$dashboardShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "SystemSync.lnk"
try {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($dashboardShortcutPath)
    $shortcut.TargetPath = "powershell.exe"
    $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$launcherPath`" -ConfigPath `"$configPath`""
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,13"
    $shortcut.Save()
}
catch {
    Write-Warning "无法创建智能启动器快捷方式，将创建直接 URL 兜底入口。错误：$($_.Exception.Message)"
    $dashboardShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "SystemSync.url"
    @"
[InternetShortcut]
URL=$dashboardEntryUrl/
IconFile=%SystemRoot%\System32\shell32.dll
IconIndex=13
"@ | Set-Content -LiteralPath $dashboardShortcutPath -Encoding ASCII
}

$startMenuDir = Join-Path ([Environment]::GetFolderPath("Programs")) "SystemSync"
New-Item -ItemType Directory -Path $startMenuDir -Force | Out-Null
Copy-Item -LiteralPath $dashboardShortcutPath -Destination (Join-Path $startMenuDir (Split-Path -Leaf $dashboardShortcutPath)) -Force

Write-Host ""
Write-Host "SystemSync Companion 已安装并启动。" -ForegroundColor Green
Write-Host "安装目录: $InstallDir"
Write-Host "监听端口: $($bundle.Port)"
Write-Host "任务计划: $(if ($taskInstalled) { $taskName } else { '未创建，使用 Startup 兜底' })"
if ($hostsAlias) {
    Write-Host "网页管理域名: $hostsAlias"
}
if ($startupFallbackPath) {
    Write-Host "Startup 兜底: $startupFallbackPath"
}
Write-Host "桌面入口: $shortcutPath"
Write-Host "网页管理入口: $dashboardShortcutPath"
