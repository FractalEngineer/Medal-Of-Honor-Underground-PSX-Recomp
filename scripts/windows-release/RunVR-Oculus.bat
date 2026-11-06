@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch.ps1" -Runtime oculus %*
set "LAUNCH_EXIT=%ERRORLEVEL%"
if not "%LAUNCH_EXIT%"=="0" pause
exit /b %LAUNCH_EXIT%
