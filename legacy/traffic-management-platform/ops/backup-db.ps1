param(
    [string]$EnvFile = (Join-Path (Split-Path -Parent $PSScriptRoot) ".env"),
    [string]$OutputDirectory
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot/common.ps1"

$projectRoot = Get-ProjectRoot

Assert-CommandExists -CommandName "docker"
Assert-FileExists -Path $EnvFile -Label ".env file"
Assert-FileExists -Path (Join-Path $projectRoot "compose.yaml") -Label "compose file"

$envValues = Read-DotEnv -Path $EnvFile
$backupDirectory = $OutputDirectory
if ([string]::IsNullOrWhiteSpace($backupDirectory)) {
    $backupDirectory = $envValues["APP_OPERATIONS_BACKUP_DIRECTORY"]
}
if ([string]::IsNullOrWhiteSpace($backupDirectory)) {
    $backupDirectory = "./backups"
}
if (-not [System.IO.Path]::IsPathRooted($backupDirectory)) {
    $backupDirectory = Join-Path $projectRoot $backupDirectory
}
New-Item -ItemType Directory -Force -Path $backupDirectory | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = Join-Path $backupDirectory "traffic-$timestamp.sql"
$dumpCommand = 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers "$MYSQL_DATABASE"'
$composeArgs = Get-ComposeBaseArgs -ProjectRoot $projectRoot -EnvFile $EnvFile

try {
    & docker @composeArgs "exec" "-T" "mysql" "sh" "-lc" $dumpCommand | Set-Content -LiteralPath $backupFile -Encoding UTF8
    if ($LASTEXITCODE -ne 0) {
        throw "mysqldump failed"
    }
}
catch {
    if (Test-Path -LiteralPath $backupFile) {
        Remove-Item -LiteralPath $backupFile -Force
    }
    throw
}

Write-Host "Database backup created: $backupFile"
