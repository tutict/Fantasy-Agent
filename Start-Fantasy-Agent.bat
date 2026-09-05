@echo off
setlocal
cd /d "%~dp0"

echo Starting Fantasy Agent Studio...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-fantasy-agent.ps1"

if errorlevel 1 (
  echo.
  echo Fantasy Agent failed to start. See the message above.
)
echo.
pause
