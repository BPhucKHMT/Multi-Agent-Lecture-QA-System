param(
    [Parameter(Position = 0)]
    [ValidateSet('up', 'down', 'logs', 'status', 'config', 'restart')]
    [string]$Action = 'up',

    [Parameter(Position = 1)]
    [string]$Service,

    [switch]$Gpu,
    [switch]$NoMonitoring,
    [switch]$NoFrontend,
    [switch]$ExternalRedis,
    [switch]$Build
)

$ErrorActionPreference = 'Stop'
$device = if ($Gpu) { 'gpu' } else { 'cpu' }
$api = if ($Gpu) { 'api-gpu' } else { 'api-cpu' }

function Test-WindowsExporter {
    try {
        $response = Invoke-WebRequest `
            -Uri 'http://127.0.0.1:9182/health' `
            -UseBasicParsing `
            -TimeoutSec 2
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

# Dung duong dan tuyet doi de lenh chay duoc tu moi thu muc.
Push-Location $PSScriptRoot
try {
    if ($Action -eq 'down') {
        # Bat tat ca profile app de "down" dung ca service da chay truoc do;
        # --remove-orphans dung Prometheus/Grafana cua cung Compose project.
        # Khong can mat khau Grafana de dung stack.
        $composeArgs = @('-f', 'docker-compose.yaml',
            '--profile', 'cpu', '--profile', 'gpu', '--profile', 'frontend',
            '--profile', 'redis', '--profile', 'pipeline', '--profile', 'pipeline-gpu',
            'down', '--remove-orphans')
    } else {
        $composeArgs = @('-f', 'docker-compose.yaml')
        if (-not $NoMonitoring) {
            $composeArgs += @('-f', 'docker-compose.observability.yaml')
        }
        $composeArgs += @('--profile', $device)
        if (-not $NoFrontend) {
            $composeArgs += @('--profile', 'frontend')
        }
        if (-not $NoMonitoring) {
            $composeArgs += @('--profile', 'monitoring')
        }

        switch ($Action) {
            'up' {
                $composeArgs += @('up', '-d')
                if ($Build) {
                    $composeArgs += '--build'
                }
                if ($ExternalRedis) {
                    $composeArgs += @('--no-deps', $api)
                    if (-not $NoFrontend) {
                        $composeArgs += 'frontend'
                    }
                    if (-not $NoMonitoring) {
                        $composeArgs += @('prometheus', 'grafana')
                    }
                }
            }
            'logs' {
                $composeArgs += @('logs', '-f')
                if ($Service) {
                    $composeArgs += $Service
                }
            }
            'restart' {
                $composeArgs += @('restart', $(if ($Service) { $Service } else { $api }))
            }
            'status' { $composeArgs += 'ps' }
            'config' { $composeArgs += @('config', '--services') }
        }
    }

    & docker compose @composeArgs
    $code = $LASTEXITCODE

    $prometheusConfig = if ($env:PUQ_PROMETHEUS_CONFIG) {
        $env:PUQ_PROMETHEUS_CONFIG
    } else {
        'prometheus.yml'
    }
    if (
        $Action -in @('up', 'status') -and
        -not $NoMonitoring -and
        $prometheusConfig -ieq 'prometheus-windows.yml'
    ) {
        if (Test-WindowsExporter) {
            Write-Host '[OK] windows_exporter: http://127.0.0.1:9182'
        } else {
            Write-Host '[WARN] windows_exporter is unavailable; Grafana CPU/RAM/GPU panels will be empty.' -ForegroundColor Yellow
            Write-Host 'Run once from Administrator PowerShell:' -ForegroundColor Yellow
            Write-Host '  .\scripts\setup-windows-exporter.ps1 -Action Install' -ForegroundColor Yellow
        }
    }
} finally {
    Pop-Location
}
exit $code
