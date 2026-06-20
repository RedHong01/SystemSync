param(
    [string]$ConfigPath = "$PSScriptRoot\agent-config.json"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Agent config not found: $ConfigPath"
}

$script:ConfigPath = (Resolve-Path -LiteralPath $ConfigPath).Path
$script:Config = Get-Content -LiteralPath $script:ConfigPath -Raw | ConvertFrom-Json
$script:LastHeartbeat = [DateTime]::MinValue

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class LanSyncIdleTime {
    [StructLayout(LayoutKind.Sequential)]
    private struct LASTINPUTINFO {
        public uint cbSize;
        public uint dwTime;
    }

    [DllImport("user32.dll")]
    private static extern bool GetLastInputInfo(ref LASTINPUTINFO plii);

    public static uint Seconds {
        get {
            LASTINPUTINFO info = new LASTINPUTINFO();
            info.cbSize = (uint)Marshal.SizeOf(info);
            GetLastInputInfo(ref info);
            return ((uint)Environment.TickCount - info.dwTime) / 1000;
        }
    }
}
"@

function Save-AgentConfig {
    $script:Config | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $script:ConfigPath -Encoding UTF8
}

function Write-JsonResponse {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)]$Value,
        [int]$StatusCode = 200
    )

    $json = $Value | ConvertTo-Json -Depth 20 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($json)
    $Context.Response.StatusCode = $StatusCode
    $Context.Response.ContentType = "application/json; charset=utf-8"
    $Context.Response.ContentLength64 = $bytes.Length
    $Context.Response.OutputStream.Write($bytes, 0, $bytes.Length)
    $Context.Response.OutputStream.Close()
}

function Write-HtmlResponse {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$Html
    )

    $bytes = [Text.Encoding]::UTF8.GetBytes($Html)
    $Context.Response.StatusCode = 200
    $Context.Response.ContentType = "text/html; charset=utf-8"
    $Context.Response.ContentLength64 = $bytes.Length
    $Context.Response.OutputStream.Write($bytes, 0, $bytes.Length)
    $Context.Response.OutputStream.Close()
}

function Get-LocalWakePage {
    return @"
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Red5090 Companion</title>
<style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f3f6f6;color:#172328;font-family:Segoe UI,sans-serif}.panel{width:min(420px,calc(100vw - 32px));padding:24px;border:1px solid #d7dfe1;border-radius:7px;background:#fff}.eyebrow{margin:0;color:#087c8c;font-size:11px;font-weight:800}h1{margin:6px 0 22px;font-size:22px}.status{display:flex;justify-content:space-between;padding:13px 0;border-top:1px solid #e1e6e7;font-size:13px}.status span{color:#657278}button{width:100%;height:42px;margin-top:18px;border:1px solid #a45d00;border-radius:5px;background:#fff2dc;color:#704100;font-weight:700;cursor:pointer}button:disabled{opacity:.5}#message{min-height:18px;margin:12px 0 0;color:#087f5b;font-size:12px}
</style>
</head>
<body>
<main class="panel">
<p class="eyebrow">WINDOWS COMPANION</p>
<h1>Red5090 / RedM3Max</h1>
<div class="status"><span>本机代理</span><strong>在线</strong></div>
<div class="status"><span>Mac 地址</span><strong>$($script:Config.MacIp)</strong></div>
<button id="wake" type="button">唤醒 RedM3Max</button>
<p id="message"></p>
</main>
<script>
const button=document.getElementById('wake');
const message=document.getElementById('message');
button.addEventListener('click',async()=>{button.disabled=true;message.textContent='正在发送唤醒包';try{const response=await fetch('/api/agent/wake',{method:'POST'});const data=await response.json();if(!response.ok)throw new Error(data.error||'发送失败');message.textContent='唤醒包已发送';}catch(error){message.textContent=error.message;}finally{button.disabled=false;}});
</script>
</body>
</html>
"@
}

function Read-JsonBody {
    param([Parameter(Mandatory = $true)]$Context)

    $reader = [IO.StreamReader]::new($Context.Request.InputStream, $Context.Request.ContentEncoding)
    try {
        $raw = $reader.ReadToEnd()
    }
    finally {
        $reader.Dispose()
    }
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return [PSCustomObject]@{}
    }
    return $raw | ConvertFrom-Json
}

function Test-AgentToken {
    param([Parameter(Mandatory = $true)]$Request)
    return $Request.Headers["X-LanSync-Token"] -eq [string]$script:Config.Token
}

function Get-FixedDisks {
    $items = foreach ($disk in Get-CimInstance Win32_LogicalDisk -Filter "DriveType = 3") {
        $total = [int64]$disk.Size
        $free = [int64]$disk.FreeSpace
        [PSCustomObject]@{
            name = [string]$disk.VolumeName
            mount = [string]$disk.DeviceID + "\"
            total = $total
            used = $total - $free
            free = $free
            percent = if ($total -gt 0) { [Math]::Round((($total - $free) / $total) * 100, 1) } else { 0 }
        }
    }
    return @($items)
}

function Get-AgentStatus {
    $idle = [int][LanSyncIdleTime]::Seconds
    return [PSCustomObject]@{
        hostname = $env:COMPUTERNAME
        os = (Get-CimInstance Win32_OperatingSystem).Caption
        power_state = if ($idle -gt 900) { "idle" } else { "online" }
        idle_seconds = $idle
        disks = Get-FixedDisks
        project_base = [string]$script:Config.ProjectBase
        timestamp = [DateTime]::Now.ToString("o")
    }
}

function Send-DashboardEvent {
    param([Parameter(Mandatory = $true)][string]$State)

    $uri = ([string]$script:Config.DashboardUrl).TrimEnd("/") + "/api/agent/event"
    $headers = @{ "X-LanSync-Token" = [string]$script:Config.Token }
    $body = @{
        state = $State
        hostname = $env:COMPUTERNAME
        timestamp = [DateTime]::Now.ToString("o")
    } | ConvertTo-Json
    try {
        Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -ContentType "application/json" -Body $body -TimeoutSec 3 | Out-Null
    }
    catch {
        # The Mac may be sleeping or temporarily unreachable.
    }
}

function Send-MagicPacket {
    param([Parameter(Mandatory = $true)][string]$MacAddress)

    $clean = $MacAddress -replace "[^0-9A-Fa-f]", ""
    if ($clean.Length -ne 12) {
        throw "Invalid MAC address"
    }
    $macBytes = for ($index = 0; $index -lt 12; $index += 2) {
        [Convert]::ToByte($clean.Substring($index, 2), 16)
    }
    [byte[]]$packet = (,0xFF * 6) + ($macBytes * 16)
    $client = [Net.Sockets.UdpClient]::new()
    try {
        $client.EnableBroadcast = $true
        [void]$client.Send($packet, $packet.Length, "255.255.255.255", 9)
    }
    finally {
        $client.Dispose()
    }
}

function Get-SyncthingApiKey {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Syncthing\config.xml"),
        (Join-Path $env:LOCALAPPDATA "Syncthing\config.xml.v0")
    )
    $configFile = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $configFile) {
        throw "Syncthing config.xml was not found under LOCALAPPDATA"
    }
    [xml]$xml = Get-Content -LiteralPath $configFile -Raw
    $key = [string]$xml.configuration.gui.apikey
    if ([string]::IsNullOrWhiteSpace($key)) {
        throw "Syncthing API key was not found"
    }
    return $key
}

function Invoke-Syncthing {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$Method = "Get",
        $Body = $null
    )

    $headers = @{ "X-API-Key" = Get-SyncthingApiKey }
    $uri = ([string]$script:Config.SyncthingGuiUrl).TrimEnd("/") + $Path
    if ($null -eq $Body) {
        return Invoke-RestMethod -Uri $uri -Method $Method -Headers $headers -TimeoutSec 10
    }
    return Invoke-RestMethod -Uri $uri -Method $Method -Headers $headers -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 30) -TimeoutSec 10
}

function Register-SyncthingFolder {
    param([Parameter(Mandatory = $true)]$Payload)

    $folderId = [string]$Payload.folder_id
    $label = [string]$Payload.label
    $path = [string]$Payload.path
    if ($folderId -notmatch "^[a-z0-9][a-z0-9-]*$") {
        throw "Folder ID must contain lowercase letters, numbers, and hyphens"
    }
    if ($path -notmatch "^[A-Za-z]:\\") {
        throw "Windows project path must be an absolute drive path"
    }
    New-Item -ItemType Directory -Path $path -Force | Out-Null

    $existing = @(Invoke-Syncthing -Path "/rest/config/folders")
    if ($existing | Where-Object { $_.id -eq $folderId }) {
        throw "Syncthing folder ID already exists on Windows"
    }

    $folder = Invoke-Syncthing -Path "/rest/config/defaults/folder"
    $folder.id = $folderId
    $folder.label = $label
    $folder.path = $path
    $folder.type = "sendreceive"
    $folder.paused = $false
    $folder.devices = @(
        @{
            deviceID = [string]$script:Config.WindowsDeviceId
            introducedBy = ""
            encryptionPassword = ""
        },
        @{
            deviceID = [string]$script:Config.MacDeviceId
            introducedBy = ""
            encryptionPassword = ""
        }
    )
    Invoke-Syncthing -Path "/rest/config/folders" -Method Post -Body $folder | Out-Null

    return @{
        ok = $true
        folder_id = $folderId
        path = $path
    }
}

function Resume-SyncthingSync {
    param([Parameter(Mandatory = $true)]$Payload)

    $folderId = [string]$Payload.folder_id
    $deviceId = [string]$Payload.device_id
    $actions = @()

    if (-not [string]::IsNullOrWhiteSpace($folderId)) {
        $encodedFolder = [System.Uri]::EscapeDataString($folderId)
        Invoke-Syncthing -Path "/rest/system/resume?folder=$encodedFolder" -Method Post | Out-Null
        $actions += "folder_resumed"
        Invoke-Syncthing -Path "/rest/db/scan?folder=$encodedFolder" -Method Post | Out-Null
        $actions += "folder_scan_requested"
    }

    if (-not [string]::IsNullOrWhiteSpace($deviceId)) {
        $encodedDevice = [System.Uri]::EscapeDataString($deviceId)
        Invoke-Syncthing -Path "/rest/system/resume?device=$encodedDevice" -Method Post | Out-Null
        $actions += "device_resumed"
    }

    return @{
        ok = $true
        folder_id = $folderId
        actions = $actions
    }
}

function Handle-Request {
    param([Parameter(Mandatory = $true)]$Context)

    try {
        $path = $Context.Request.Url.AbsolutePath
        $method = $Context.Request.HttpMethod
        $isLoopback = [Net.IPAddress]::IsLoopback($Context.Request.RemoteEndPoint.Address)

        if ($method -eq "GET" -and $path -eq "/" -and $isLoopback) {
            Write-HtmlResponse -Context $Context -Html (Get-LocalWakePage)
            return
        }

        if (-not $isLoopback -and -not (Test-AgentToken -Request $Context.Request)) {
            Write-JsonResponse -Context $Context -Value @{ error = "Invalid companion token" } -StatusCode 403
            return
        }

        if ($method -eq "GET" -and $path -eq "/api/agent/status") {
            Write-JsonResponse -Context $Context -Value (Get-AgentStatus)
            return
        }

        if ($method -eq "POST" -and $path -eq "/api/agent/target") {
            $payload = Read-JsonBody -Context $Context
            $target = [string]$payload.path
            if ($target -notmatch "^[A-Za-z]:\\") {
                throw "Target must be an absolute Windows drive path"
            }
            New-Item -ItemType Directory -Path $target -Force | Out-Null
            $script:Config.ProjectBase = $target
            Save-AgentConfig
            Write-JsonResponse -Context $Context -Value @{ ok = $true; path = $target }
            return
        }

        if ($method -eq "POST" -and $path -eq "/api/agent/register-folder") {
            $payload = Read-JsonBody -Context $Context
            Write-JsonResponse -Context $Context -Value (Register-SyncthingFolder -Payload $payload)
            return
        }

        if ($method -eq "POST" -and $path -eq "/api/agent/resume-sync") {
            $payload = Read-JsonBody -Context $Context
            Write-JsonResponse -Context $Context -Value (Resume-SyncthingSync -Payload $payload)
            return
        }

        if ($method -eq "POST" -and $path -eq "/api/agent/wake") {
            Send-MagicPacket -MacAddress ([string]$script:Config.MacMac)
            Write-JsonResponse -Context $Context -Value @{ ok = $true }
            return
        }

        Write-JsonResponse -Context $Context -Value @{ error = "Not found" } -StatusCode 404
    }
    catch {
        Write-JsonResponse -Context $Context -Value @{ error = $_.Exception.Message } -StatusCode 500
    }
}

$port = [int]$script:Config.Port
$listener = [Net.HttpListener]::new()
$listener.Prefixes.Add("http://+:$port/")
$listener.Start()

$powerWatcherRegistered = $false
$shutdownWatcherRegistered = $false
try {
    Register-WmiEvent -Class Win32_PowerManagementEvent -SourceIdentifier "LanSyncPower" | Out-Null
    $powerWatcherRegistered = $true
}
catch {
}
try {
    Register-WmiEvent -Class Win32_ComputerShutdownEvent -SourceIdentifier "LanSyncShutdown" | Out-Null
    $shutdownWatcherRegistered = $true
}
catch {
}
Send-DashboardEvent -State "online"

try {
    $contextTask = $listener.GetContextAsync()
    while ($listener.IsListening) {
        if ($contextTask.Wait(1000)) {
            Handle-Request -Context $contextTask.Result
            $contextTask = $listener.GetContextAsync()
        }

        if ($powerWatcherRegistered) {
            $powerEvent = Get-Event -SourceIdentifier "LanSyncPower" -ErrorAction SilentlyContinue
            foreach ($event in @($powerEvent)) {
                $eventType = [int]$event.SourceEventArgs.NewEvent.EventType
                if ($eventType -eq 4) {
                    Send-DashboardEvent -State "sleeping"
                }
                elseif ($eventType -eq 7 -or $eventType -eq 18) {
                    Send-DashboardEvent -State "online"
                }
                Remove-Event -EventIdentifier $event.EventIdentifier -ErrorAction SilentlyContinue
            }
        }

        if ($shutdownWatcherRegistered) {
            $shutdownEvent = Get-Event -SourceIdentifier "LanSyncShutdown" -ErrorAction SilentlyContinue
            foreach ($event in @($shutdownEvent)) {
                Send-DashboardEvent -State "shutting_down"
                Remove-Event -EventIdentifier $event.EventIdentifier -ErrorAction SilentlyContinue
            }
        }

        if (([DateTime]::Now - $script:LastHeartbeat).TotalSeconds -ge 30) {
            Send-DashboardEvent -State "online"
            $script:LastHeartbeat = [DateTime]::Now
        }
    }
}
finally {
    if ($powerWatcherRegistered) {
        Unregister-Event -SourceIdentifier "LanSyncPower" -ErrorAction SilentlyContinue
    }
    if ($shutdownWatcherRegistered) {
        Unregister-Event -SourceIdentifier "LanSyncShutdown" -ErrorAction SilentlyContinue
    }
    $listener.Stop()
    $listener.Close()
}
