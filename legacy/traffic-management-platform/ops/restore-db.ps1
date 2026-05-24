param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [string]$EnvFile = (Join-Path (Split-Path -Parent $PSScriptRoot) ".env"),
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot/common.ps1"

$projectRoot = Get-ProjectRoot

Assert-CommandExists -CommandName "docker"
Assert-FileExists -Path $EnvFile -Label ".env file"
Assert-FileExists -Path (Join-Path $projectRoot "compose.yaml") -Label "compose file"
Assert-FileExists -Path $BackupFile -Label "backup file"

if (-not $Force) {
    throw "Restore is destructive. Re-run with -Force after verifying the SQL dump."
}

$restoreCommand = 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'
$composeArgs = Get-ComposeBaseArgs -ProjectRoot $projectRoot -EnvFile $EnvFile

Get-Content -LiteralPath $BackupFile -Raw | & docker @composeArgs "exec" "-T" "mysql" "sh" "-lc" $restoreCommand
if ($LASTEXITCODE -ne 0) {
    throw "Database restore failed"
}

Write-Host "Database restore completed from: $BackupFile"
