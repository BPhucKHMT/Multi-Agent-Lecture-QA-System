#Requires -Version 5.1
[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidateSet('Install', 'Status', 'Uninstall')]
    [string]$Action = 'Install'
)

$ErrorActionPreference = 'Stop'

$isAdministrator = (
    New-Object Security.Principal.WindowsPrincipal(
        [Security.Principal.WindowsIdentity]::GetCurrent()
    )
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($Action -ne 'Status' -and -not $isAdministrator) {
    throw "Action $Action requires Administrator PowerShell."
}

$Version = '0.31.8'
$MsiName = "windows_exporter-$Version-amd64.msi"
$MsiUrl = "https://github.com/prometheus-community/windows_exporter/releases/download/v$Version/$MsiName"
$ExpectedSha256 = '0aadce6afb20182b678bfca9e8f2e8464ef48c469b28b4cf02e99d82158f5d40'
$DownloadDir = Join-Path $env:TEMP 'puq-windows-exporter'
$MsiPath = Join-Path $DownloadDir $MsiName
$ServiceName = 'windows_exporter'
$FirewallRuleName = 'PUQ windows_exporter 9182'

function Get-VerifiedMsi {
    New-Item -ItemType Directory -Path $DownloadDir -Force | Out-Null
    Invoke-WebRequest -Uri $MsiUrl -OutFile $MsiPath -UseBasicParsing
    $actual = (Get-FileHash -Algorithm SHA256 -Path $MsiPath).Hash.ToLowerInvariant()
    if ($actual -ne $ExpectedSha256) {
        Remove-Item $MsiPath -Force -ErrorAction SilentlyContinue
        throw "windows_exporter MSI checksum mismatch: $actual"
    }
    return $MsiPath
}

function Get-ExporterStatus {
    try {
        $service = Get-Service -Name $ServiceName -ErrorAction Stop
        $startMode = (Get-CimInstance Win32_Service -Filter "Name='$ServiceName'").StartMode
    } catch {
        Write-Warning "windows_exporter service is not installed."
        return 1
    }

    try {
        $response = Invoke-WebRequest `
            -Uri 'http://127.0.0.1:9182/metrics' `
            -UseBasicParsing `
            -TimeoutSec 5
        $metrics = $response.Content
    } catch {
        Write-Warning "windows_exporter metrics endpoint is unavailable on 127.0.0.1:9182."
        return 1
    }

    $hasCpu = $metrics.Contains('windows_cpu_time_total')
    $hasMemory = $metrics.Contains('windows_memory_')
    $hasGpu = @(
        'windows_gpu_info',
        'windows_gpu_engine_time_seconds',
        'windows_gpu_adapter_memory_dedicated_bytes'
    ) | ForEach-Object { $metrics.Contains($_) } | Where-Object { -not $_ } | Measure-Object | Select-Object -ExpandProperty Count

    Write-Host "Service: $($service.Status)"
    Write-Host "StartMode: $startMode"
    Write-Host "HTTP: $($response.StatusCode)"
    Write-Host "CPU metrics: $hasCpu"
    Write-Host "RAM metrics: $hasMemory"
    Write-Host "GPU metrics: $([int]($hasGpu -eq 0))"

    if ($service.Status -ne 'Running' -or $startMode -ne 'Auto' -or $response.StatusCode -ne 200) {
        Write-Warning 'windows_exporter service or HTTP health is not ready.'
        return 1
    }
    if (-not $hasCpu -or -not $hasMemory) {
        Write-Warning 'CPU/RAM metrics are missing from windows_exporter.'
        return 1
    }
    if ($hasGpu -ne 0) {
        Write-Warning 'CPU/RAM metrics work, but GPU counters are unavailable; inspect Windows GPU performance counters.'
        return 2
    }
    return 0
}

function Install-Exporter {
    $verifiedMsi = Get-VerifiedMsi
    if (-not $PSCmdlet.ShouldProcess($ServiceName, 'Install and start windows_exporter')) {
        return 0
    }

    $arguments = @(
        '/i', "`"$verifiedMsi`"",
        '/qn', '/norestart',
        'ENABLED_COLLECTORS=[defaults],gpu',
        'LISTEN_ADDR=0.0.0.0',
        'LISTEN_PORT=9182'
    )
    $process = Start-Process msiexec.exe -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -notin @(0, 3010)) {
        throw "windows_exporter MSI failed with exit code $($process.ExitCode)"
    }

    Set-Service -Name $ServiceName -StartupType Automatic
    Start-Service -Name $ServiceName
    Get-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule
    New-NetFirewallRule `
        -DisplayName $FirewallRuleName `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort 9182 `
        -RemoteAddress LocalSubnet | Out-Null

    Write-Host "Installed $ServiceName $Version with CPU, RAM, and GPU collectors."
    return Get-ExporterStatus
}

function Uninstall-Exporter {
    $verifiedMsi = Get-VerifiedMsi
    if (-not $PSCmdlet.ShouldProcess($ServiceName, 'Uninstall windows_exporter')) {
        return 0
    }

    $process = Start-Process msiexec.exe -ArgumentList @('/x', "`"$verifiedMsi`"", '/qn', '/norestart') -Wait -PassThru
    if ($process.ExitCode -notin @(0, 3010)) {
        throw "windows_exporter MSI uninstall failed with exit code $($process.ExitCode)"
    }

    Get-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule
    if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
        throw "windows_exporter service still exists after uninstall."
    }
    Write-Host "Uninstalled $ServiceName and removed only firewall rule '$FirewallRuleName'."
    return 0
}

switch ($Action) {
    'Status' { exit (Get-ExporterStatus) }
    'Install' { exit (Install-Exporter) }
    'Uninstall' { exit (Uninstall-Exporter) }
}
