@echo off
setlocal
rem VR launch pinned to the SteamVR OpenXR runtime.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0vr\run_vr.ps1" -Runtime steamvr -BuildDirectory build-release %*
set "VR_EXIT_CODE=%ERRORLEVEL%"
if not "%VR_EXIT_CODE%"=="0" (
    echo.
    echo VR launch failed. See the error above.
    pause
)
exit /b %VR_EXIT_CODE%
