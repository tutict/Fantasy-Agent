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

$envValues = Read-DotEnv -Path $EnvFile
$requiredKeys = @(
    "MYSQL_DATABASE",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_ROOT_PASSWORD",
    "APP_DB_URL",
    "APP_DB_USERNAME",
    "APP_DB_PASSWORD",
    "APP_JWT_SECRET_KEY"
)

Assert-EnvKeys -Values $envValues -Keys $requiredKeys
Assert-Base64Secret -Value $envValues["APP_JWT_SECRET_KEY"]

$backupDirectory = $envValues["APP_OPERATIONS_BACKUP_DIRECTORY"]
if ([string]::IsNullOrWhiteSpace($backupDirectory)) {
    $backupDirectory = "./backups"
}
if (-not [System.IO.Path]::IsPathRooted($backupDirectory)) {
    $backupDirectory = Join-Path $projectRoot $backupDirectory
}
New-Item -ItemType Directory -Force -Path $backupDirectory | Out-Null

Invoke-DockerCompose -ProjectRoot $projectRoot -EnvFile $EnvFile -Arguments @("config", "-q")

if (-not $SkipPull) {
    Invoke-DockerCompose -ProjectRoot $projectRoot -EnvFile $EnvFile -Arguments @("pull")
}

if (-not $SkipBuild) {
    Invoke-DockerCompose -ProjectRoot $projectRoot -EnvFile $EnvFile -Arguments @("build", "backend")
}

Invoke-DockerCompose -ProjectRoot $projectRoot -EnvFile $EnvFile -Arguments @("up", "-d", "--remove-orphans")
Invoke-DockerCompose -ProjectRoot $projectRoot -EnvFile $EnvFile -Arguments @("ps")

if (-not $SkipSmokeTest) {
    & (Join-Path $PSScriptRoot "smoke-test.ps1") -EnvFile $EnvFile
    if ($LASTEXITCODE -ne 0) {
        throw "Smoke test failed"
    }
}

Write-Host "Installation completed. Flyway migrations and standard seed will run when backend starts."
