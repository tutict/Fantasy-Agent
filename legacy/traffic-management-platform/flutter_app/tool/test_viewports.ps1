param(
    [switch]$SkipAnalyze,
    [switch]$NoPub = $true,
    [int]$Concurrency = 1,
    [string]$TestPath = "test/responsive_viewport_test.dart"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot

function Set-ProxyBypass {
    $script:proxyKeys = @(
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "no_proxy"
    )
    $script:originalEnv = @()
    foreach ($key in $script:proxyKeys) {
        $script:originalEnv += [pscustomobject]@{
            Key = $key
            Value = [Environment]::GetEnvironmentVariable($key)
        }
    }

    $env:HTTP_PROXY = ""
    $env:HTTPS_PROXY = ""
    $env:http_proxy = ""
    $env:https_proxy = ""
    $env:NO_PROXY = "127.0.0.1,localhost"
    $env:no_proxy = "127.0.0.1,localhost"
}

function Restore-ProxyEnv {
    foreach ($entry in $script:originalEnv) {
        if ([string]::IsNullOrEmpty($entry.Value)) {
            Remove-Item "Env:$($entry.Key)" -ErrorAction SilentlyContinue
        }
        else {
            Set-Item "Env:$($entry.Key)" $entry.Value
        }
    }
}

Push-Location $projectRoot
try {
    Set-ProxyBypass

    if (-not $SkipAnalyze) {
        Write-Host "==> flutter analyze"
        & flutter analyze
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }

    $testArgs = @("test")
    if ($NoPub) {
        $testArgs += "--no-pub"
    }
    $testArgs += "--concurrency=$Concurrency"
    $testArgs += $TestPath

    Write-Host "==> flutter $($testArgs -join ' ')"
    & flutter @testArgs
    exit $LASTEXITCODE
}
finally {
    Restore-ProxyEnv
    Pop-Location
}
