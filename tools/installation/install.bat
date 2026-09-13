@echo off
setlocal
set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..\..\

echo Rune Decrypter Prime V1 full installer
echo This installs or verifies the required LM3/LM4 release assets.
echo If automatic download fails, place rdp-v1-lm-large-part*.zip under downloads\ and run this again.
echo.

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3.11 "%REPO_ROOT%install.py" %*
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python "%REPO_ROOT%install.py" %*
  exit /b %ERRORLEVEL%
)

echo Python launcher not found. Install Python 3.11+ and retry.
exit /b 1
