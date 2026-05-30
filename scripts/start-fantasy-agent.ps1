param(
    [ValidateSet("studio", "web-console", "chatgpt-workbench", "godot-builder")]
    [string]$App = "studio",

    [int]$Port = 0,

    [switch]$NoOpen,

    [switch]$SkipInstall,

    [switch]$VerboseAccessLog,

    [switch]$SmokeTest
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[Fantasy Agent] $Message"
}

function Get-AppConfig {
    param([string]$Name)

    if ($Name -eq "studio") {
        return @{
            Title = "Fantasy Agent Studio"
            AppDir = "apps/studio"
            DefaultPort = 7860
            UrlPath = "/"
        }
    }

    if ($Name -eq "chatgpt-workbench") {
        return @{
            Title = "Fantasy Agent ChatGPT Workbench"
            AppDir = "apps/chatgpt-workbench"
            DefaultPort = 8787
            UrlPath = "/"
        }
    }

    if ($Name -eq "godot-builder") {
        return @{
            Title = "Fantasy Agent Godot Builder"
            AppDir = "apps/godot-builder"
            DefaultPort = 8790
            UrlPath = "/mcp"
        }
    }

    return @{
        Title = "Fantasy Agent Studio"
        AppDir = "apps/web-console"
        DefaultPort = 7860
        UrlPath = "/"
    }
}

function Test-HttpOk {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 1
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    } catch {
        return $false
    }
}

function Test-PortOpen {
    param([int]$PortNumber)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $result = $client.BeginConnect("127.0.0.1", $PortNumber, $null, $null)
        if (-not $result.AsyncWaitHandle.WaitOne(200)) {
            return $false
        }
        $client.EndConnect($result)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Get-FreePort {
    param([int]$PreferredPort)

    $candidate = $PreferredPort
    while ($candidate -lt ($PreferredPort + 50)) {
        if (-not (Test-PortOpen -PortNumber $candidate)) {
            return $candidate
        }
        $candidate += 1
    }

    throw "No free port found near $PreferredPort."
}

function Get-PythonCommand {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @($python.Source)
    }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @($py.Source, "-3")
    }

    throw "Python was not found. Install Python 3.11+ and try again."
}

function Invoke-Python {
    param(
        [string[]]$PythonCommand,
        [string[]]$Arguments
    )

    $pythonExe = $PythonCommand[0]
    $pythonArgs = @()
    if ($PythonCommand.Length -gt 1) {
        $pythonArgs = $PythonCommand[1..($PythonCommand.Length - 1)]
    }

    & $pythonExe @pythonArgs @Arguments
}

function Ensure-Venv {
    param([string]$RepoRoot)

    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }

    Write-Step "Creating Python virtual environment in .venv..."
    $pythonCommand = Get-PythonCommand
    Invoke-Python -PythonCommand $pythonCommand -Arguments @("-m", "venv", ".venv")

    if (-not (Test-Path $venvPython)) {
        throw "Virtual environment creation failed."
    }

    return $venvPython
}

function Ensure-Install {
    param(
        [string]$PythonExe,
        [switch]$SkipInstall
    )

    if ($SkipInstall) {
        return
    }

    & $PythonExe -c "import fastapi, uvicorn, fantasy_agent" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Step "Python environment already has Fantasy Agent dependencies."
        return
    }

    Write-Step "Installing Fantasy Agent in editable mode..."
    & $PythonExe -m pip install -e .
    if ($LASTEXITCODE -ne 0) {
        throw "pip install failed."
    }
}

function Open-Url {
    param([string]$Url)

    $info = [System.Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $Url
    $info.UseShellExecute = $true
    [System.Diagnostics.Process]::Start($info) | Out-Null
}

function Start-OpenBrowserJob {
    param(
        [string]$HealthUrl,
        [string]$OpenUrl
    )

    if ($NoOpen) {
        return $null
    }

    return Start-Job -ScriptBlock {
        param($HealthUrl, $OpenUrl)

        for ($i = 0; $i -lt 60; $i++) {
            try {
                $response = Invoke-WebRequest -UseBasicParsing -Uri $HealthUrl -TimeoutSec 1
                if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                    break
                }
            } catch {
                Start-Sleep -Seconds 1
            }
        }

        $info = [System.Diagnostics.ProcessStartInfo]::new()
        $info.FileName = $OpenUrl
        $info.UseShellExecute = $true
        [System.Diagnostics.Process]::Start($info) | Out-Null
    } -ArgumentList $HealthUrl, $OpenUrl
}

function Start-UvicornProcess {
    param(
        [string]$PythonExe,
        [string]$RepoRoot,
        [string]$AppDir,
        [int]$PortNumber
    )

    $info = [System.Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $PythonExe
    $quietArgs = "--no-access-log --log-level warning"
    if ($VerboseAccessLog) {
        $quietArgs = ""
    }
    $info.Arguments = "-m uvicorn app.main:app --app-dir $AppDir --host 127.0.0.1 --port $PortNumber $quietArgs".Trim()
    $info.WorkingDirectory = $RepoRoot
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    return [System.Diagnostics.Process]::Start($info)
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$config = Get-AppConfig -Name $App
$selectedPort = if ($Port -gt 0) { $Port } else { [int]$config.DefaultPort }
$healthUrl = "http://127.0.0.1:$selectedPort/health"

if (Test-HttpOk -Url $healthUrl) {
    $openUrl = "http://127.0.0.1:$selectedPort$($config.UrlPath)"
    Write-Step "$($config.Title) is already running at $openUrl"
    if (-not $NoOpen) {
        Open-Url -Url $openUrl
    }
    exit 0
}

if (Test-PortOpen -PortNumber $selectedPort) {
    $selectedPort = Get-FreePort -PreferredPort ($selectedPort + 1)
    Write-Step "Default port is busy. Using port $selectedPort instead."
}

$healthUrl = "http://127.0.0.1:$selectedPort/health"
$openUrl = "http://127.0.0.1:$selectedPort$($config.UrlPath)"
$pythonExe = Ensure-Venv -RepoRoot $repoRoot
Ensure-Install -PythonExe $pythonExe -SkipInstall:$SkipInstall

Write-Step "Panel: $openUrl"
Write-Step "Health: $healthUrl"

if ($SmokeTest) {
    $process = Start-UvicornProcess `
        -PythonExe $pythonExe `
        -RepoRoot $repoRoot `
        -AppDir $config.AppDir `
        -PortNumber $selectedPort
    try {
        for ($i = 0; $i -lt 30; $i++) {
            if (Test-HttpOk -Url $healthUrl) {
                Write-Step "Smoke test passed."
                exit 0
            }
            Start-Sleep -Seconds 1
        }
        throw "Smoke test failed: server did not respond at $healthUrl"
    } finally {
        if ($process -and -not $process.HasExited) {
            $process.Kill()
            $process.WaitForExit()
        }
    }
}

$browserJob = Start-OpenBrowserJob -HealthUrl $healthUrl -OpenUrl $openUrl
try {
    Write-Step "Starting $($config.Title). Press Ctrl+C to stop."
    if ($VerboseAccessLog) {
        & $pythonExe -m uvicorn app.main:app --app-dir $config.AppDir --host 127.0.0.1 --port $selectedPort
    } else {
        & $pythonExe -m uvicorn app.main:app --app-dir $config.AppDir --host 127.0.0.1 --port $selectedPort --no-access-log --log-level warning
    }
} finally {
    if ($browserJob) {
        Remove-Job $browserJob -Force -ErrorAction SilentlyContinue
    }
}
