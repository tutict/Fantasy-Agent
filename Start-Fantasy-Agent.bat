@echo off
REM Fantasy Agent Studio - desktop launcher.
REM
REM Starts the backend and shows the Studio in a native window, with no console
REM left behind. The heavy lifting lives in apps/studio/desktop.py.
REM
REM If something goes wrong, pythonw.exe has no console to complain to, so this
REM launcher re-runs without redirection to show the message. Pass --console to
REM force a visible console for debugging.
REM
REM Note on style: the branches below use `goto` labels rather than nested
REM `if (...)` blocks on purpose. cmd expands %VARS% when it parses a whole
REM parenthesised block, so a variable assigned inside such a block reads back
REM empty on the next line of that same block.

setlocal
cd /d "%~dp0"

set "VENV_PYW=%~dp0.venv\Scripts\pythonw.exe"
set "VENV_PY=%~dp0.venv\Scripts\python.exe"
set "DESKTOP=%~dp0apps\studio\desktop.py"
set "LOGDIR=%~dp0generated\desktop"
set "LOG=%LOGDIR%\launcher.log"

if /i "%~1"=="--console" goto console_mode

if not exist "%VENV_PY%" goto no_venv

REM Prefer pythonw so double-clicking this file never leaves a console window.
set "LAUNCHER=%VENV_PY%"
if exist "%VENV_PYW%" set "LAUNCHER=%VENV_PYW%"

if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>&1

"%LAUNCHER%" "%DESKTOP%" 1>"%LOG%" 2>&1

REM 0 is the normal path (the user closed the window), so say nothing.
if not errorlevel 1 exit /b 0

REM Non-zero means startup failed. Re-run with output visible so the reason is
REM readable instead of stranded in a log file.
echo Fantasy Agent failed to start. Re-running with output visible...
echo.
"%VENV_PY%" -u "%DESKTOP%"
echo.
echo If nothing was printed above, see "%LOG%".
pause
exit /b 1

:console_mode
"%VENV_PY%" -u "%DESKTOP%"
exit /b %errorlevel%

:no_venv
echo Fantasy Agent needs a Python environment, but .venv was not found.
echo Create it once from the repo root:
echo.
echo     python -m venv .venv
echo     .venv\Scripts\python.exe -m pip install -e .[desktop]
echo.
pause
exit /b 1
