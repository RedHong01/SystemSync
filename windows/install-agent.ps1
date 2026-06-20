param(
    [string]$InstallDir = "$env:ProgramData\RedLanSyncAgent",
    [string]$BundleConfig = "$PSScriptRoot\agent-config.generated.json"
)

$ErrorActionPreference = "Stop"

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
Copy-Item -LiteralPath $BundleConfig -Destination "$InstallDir\agent-config.json" -Force

$ruleName = "Red LAN Sync Companion 8766"
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

$taskName = "Red LAN Sync Companion"
$scriptPath = "$InstallDir\LanSyncAgent.ps1"
$configPath = "$InstallDir\agent-config.json"
$arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`" -ConfigPath `"$configPath`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
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

$shortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Wake RedM3Max.url"
@"
[InternetShortcut]
URL=http://127.0.0.1:$($bundle.Port)/
IconFile=%SystemRoot%\System32\shell32.dll
IconIndex=27
"@ | Set-Content -LiteralPath $shortcutPath -Encoding ASCII

Write-Host ""
Write-Host "Red LAN Sync Companion 已安装并启动。" -ForegroundColor Green
Write-Host "安装目录: $InstallDir"
Write-Host "监听端口: $($bundle.Port)"
Write-Host "任务计划: $taskName"
Write-Host "桌面入口: $shortcutPath"
