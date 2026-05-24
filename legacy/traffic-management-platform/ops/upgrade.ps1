param(
    [string]$EnvFile = (Join-Path (Split-Path -Parent $PSScriptRoot) ".env"),
    [switch]$SkipPull,
    [switch]$SkipBuild,
    [switch]$SkipSmokeTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot/common.ps1"

$projectRoot = Get-ProjectRoot

Assert-CommandExists -CommandName "docker"
Assert-FileExists -Path $EnvFile -Label ".env file"
Assert-FileExists -Path (Join-Path $projectRoot "compose.yaml") -Label "compose file"

Invoke-DockerCompose -ProjectRoot $projectRoot -EnvFile $EnvFile -Arguments @("config", "-q")

if (-not $SkipPull) {
    Invoke-DockerCompose -ProjectRoot $projectRoot -EnvFile $EnvFile -Arguments @("pull")
}

if (-not $SkipBuild) {
    Invoke-DockerCompose -ProjectRoot $projectRoot -EnvFile $EnvFile -Arguments @("build", "backend")
}

Invoke-DockerCompose -ProjectRoot $projectRoot -EnvFile $EnvFile -Arguments @("up", "-d", "--build", "--remove-orphans")
Invoke-DockerCompose -ProjectRoot $projectRoot -EnvFile $EnvFile -Arguments @("ps")

if (-not $SkipSmokeTest) {
    & (Join-Path $PSScriptRoot "smoke-test.ps1") -EnvFile $EnvFile
    if ($LASTEXITCODE -ne 0) {
        throw "Smoke test failed"
    }
}

Write-Host "Upgrade completed. Flyway has applied any pending schema changes during backend startup."
