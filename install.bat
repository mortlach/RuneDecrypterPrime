@echo off
setlocal
set SCRIPT_DIR=%~dp0

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3.11 "%SCRIPT_DIR%install.py" %*
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python "%SCRIPT_DIR%install.py" %*
  exit /b %ERRORLEVEL%
)

echo Python launcher not found. Install Python 3.11+ and retry.
exit /b 1
