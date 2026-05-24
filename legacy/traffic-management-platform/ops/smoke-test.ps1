param(
    [string]$EnvFile = (Join-Path (Split-Path -Parent $PSScriptRoot) ".env"),
    [string]$BaseUrl,
    [int]$TimeoutSeconds = 90
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot/common.ps1"

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    Assert-FileExists -Path $EnvFile -Label ".env file"
    $envValues = Read-DotEnv -Path $EnvFile
    $serverPort = $envValues["SERVER_PORT"]
    if ([string]::IsNullOrWhiteSpace($serverPort)) {
        $serverPort = "8080"
    }
    $BaseUrl = "http://127.0.0.1:$serverPort"
}

$healthUrl = "$BaseUrl/actuator/health"
$infoUrl = "$BaseUrl/actuator/info"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$status = $null

Write-Host "Waiting for health endpoint: $healthUrl"

while ((Get-Date) -lt $deadline) {
    try {
        $response = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 5
        $status = $response.status
        if ($status -eq "UP") {
            break
        }
    }
    catch {
        Start-Sleep -Seconds 3
        continue
    }

    Start-Sleep -Seconds 3
}

if ($status -ne "UP") {
    throw "Smoke test failed: health status did not become UP within $TimeoutSeconds seconds"
}

$infoResponse = Invoke-RestMethod -Uri $infoUrl -Method Get -TimeoutSec 5
Write-Host "Health check passed with status UP"
Write-Host "Info endpoint responded with version: $($infoResponse.app.version)"
