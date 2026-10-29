@echo off
setlocal
rem VR launch pinned to the Virtual Desktop (VDXR) OpenXR runtime.
rem Normal production build. Experimental performance test requires -PerformanceTest.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0vr\run_vr.ps1" -Runtime vdxr -BuildDirectory build-release %*
set "VR_EXIT_CODE=%ERRORLEVEL%"
if not "%VR_EXIT_CODE%"=="0" (
    echo.
    echo VR launch failed. See the error above.
    pause
)
exit /b %VR_EXIT_CODE%
