function Get-ProjectRoot {
    return (Split-Path -Parent $PSScriptRoot)
}

function Assert-FileExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [string]$Label = "File"
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label not found: $Path"
    }
}

function Assert-CommandExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommandName
    )

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $CommandName"
    }
}

function Read-DotEnv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith("#")) {
            continue
        }

        $separatorIndex = $trimmed.IndexOf("=")
        if ($separatorIndex -lt 1) {
            continue
        }

        $key = $trimmed.Substring(0, $separatorIndex).Trim()
        $value = $trimmed.Substring($separatorIndex + 1).Trim()
        $values[$key] = $value
    }

    return $values
}

function Assert-EnvKeys {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Values,
        [Parameter(Mandatory = $true)]
        [string[]]$Keys
    )

    foreach ($key in $Keys) {
        if (-not $Values.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($Values[$key])) {
            throw "Missing required .env key: $key"
        }
    }
}

function Assert-Base64Secret {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value,
        [int]$MinimumBytes = 32
    )

    try {
        $bytes = [Convert]::FromBase64String($Value.Trim())
    }
    catch {
        throw "APP_JWT_SECRET_KEY must be a valid Base64 string"
    }

    if ($bytes.Length -lt $MinimumBytes) {
        throw "APP_JWT_SECRET_KEY must decode to at least $MinimumBytes bytes"
    }
}

function Get-ComposeBaseArgs {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot,
        [Parameter(Mandatory = $true)]
        [string]$EnvFile
    )

    return @(
        "compose",
        "--project-directory", $ProjectRoot,
        "-f", (Join-Path $ProjectRoot "compose.yaml"),
        "--env-file", $EnvFile
    )
}

function Invoke-DockerCompose {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot,
        [Parameter(Mandatory = $true)]
        [string]$EnvFile,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $composeArgs = Get-ComposeBaseArgs -ProjectRoot $ProjectRoot -EnvFile $EnvFile
    & docker @composeArgs @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose command failed: $($Arguments -join ' ')"
    }
}
