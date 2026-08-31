@echo off
setlocal
set "SCRIPT_DIR=%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install_chatgpt_changes.ps1"
set "INSTALL_EXIT=%ERRORLEVEL%"

echo.
if not "%INSTALL_EXIT%"=="0" (
    echo Installation failed. Read the error above; no existing mod folder was permanently overwritten.
)
pause
exit /b %INSTALL_EXIT%
